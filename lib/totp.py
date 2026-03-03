"""TOTP generation and 2FA setup automation."""
import base64
import hashlib
import hmac
import os
import re
import struct
import time
from datetime import datetime
from typing import Dict

import requests

from .config import (
    BASE_DIR, SECURITY_URL, TFA_SETUP_URL, _save_debug, logger,
)
from .auth import get_username_from_cookies
from .htmlparse import (
    _extract_form_body, _extract_token, _get_scoped_csrf,
    _get_fetch_nonce, _get_release_version, _api_headers, _parse_hidden,
)


def generate_totp(secret_b32: str, period: int = 30) -> str:
    """Generate a 6-digit TOTP code from a base32 secret (RFC 6238)."""
    key = base64.b32decode(secret_b32.upper().replace(' ', '').replace('-', ''), casefold=True)
    counter = int(time.time()) // period
    msg = struct.pack('>Q', counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack('>I', h[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1000000:06d}"


def check_2fa_status(s) -> bool:
    """Check if 2FA is already enabled by looking for 'Configured' label on security page."""
    try:
        r = s.get(SECURITY_URL, timeout=20)
        r.raise_for_status()
        if re.search(r'<span[^>]+Label--success[^>]*>\s*Configured\s*</span>', r.text, re.I):
            return True
        if re.search(r'Authenticator\s+app.*?Configured', r.text, re.S | re.I):
            return True
    except Exception:
        pass
    return False


def setup_2fa(s, on_log=None) -> Dict[str, str]:
    """Fully automated 2FA TOTP setup via GitHub's internal JSON API.

    Flow (mimics browser):
    1. GET /settings/security → validate session, check 2FA status
    2. GET /setup/intro → extract CSRF tokens, nonce, release
    3. POST /setup/initiate (JSON API) → get mashed_secret + recovery codes
    4. Generate TOTP from mashed_secret
    5. POST /setup/verify (JSON API) → verify OTP
    6. Re-fetch setup page → get fresh CSRF tokens
    7. POST /setup/recovery_download → download recovery codes
    8. POST /setup/enable → finalize 2FA
    9. Save setup key + recovery codes to file

    Returns dict with: setup_key, totp, recovery_codes, saved_to
    """
    result = {"setup_key": "", "totp": "", "recovery_codes": [], "saved_to": ""}
    log = on_log or (lambda msg: None)

    INITIATE_URL = "https://github.com/settings/two_factor_authentication/setup/initiate"
    VERIFY_URL = "https://github.com/settings/two_factor_authentication/setup/verify"
    ENABLE_URL = "https://github.com/settings/two_factor_authentication/setup/enable"

    # ── Step 1: GET /settings/security ────────────────────────────────
    log("🔍 Loading security page...")
    try:
        sec_r = s.get(SECURITY_URL, timeout=20, allow_redirects=True)
        sec_r.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Timeout loading security page. Check your connection.")
    except Exception as e:
        raise RuntimeError(f"Failed to load security page: {e}")

    _save_debug("00_security", sec_r.text)

    if "/login" in sec_r.url:
        raise RuntimeError("Session expired — please login again.")

    if re.search(r'<span[^>]+Label--success[^>]*>\s*Configured\s*</span>',
                 sec_r.text, re.I):
        raise RuntimeError("2FA is already enabled on this account.")
    if re.search(r'Authenticator\s+app.*?Configured', sec_r.text, re.S | re.I):
        raise RuntimeError("2FA is already enabled on this account.")

    if 'not enabled yet' in sec_r.text.lower():
        log("✅ Security page loaded — 2FA not enabled")
    else:
        log("✅ Security page loaded")

    # ── Step 2: GET /setup/intro ──────────────────────────────────────
    log("⏳ Loading 2FA setup page...")
    logger.info("setup_2fa: GET %s", TFA_SETUP_URL)
    try:
        r = s.get(TFA_SETUP_URL, timeout=20, allow_redirects=True,
                  headers={"Referer": SECURITY_URL})
    except requests.exceptions.Timeout:
        raise RuntimeError("Timeout loading 2FA setup page. Try again.")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Connection error: {e}")

    _save_debug("01_setup_intro", r.text)
    logger.info("setup_2fa: status=%d, url=%s, len=%d",
                r.status_code, r.url, len(r.text))

    if r.status_code != 200:
        raise RuntimeError(f"Setup page returned HTTP {r.status_code}. URL: {r.url}")

    if 'two-factor' not in r.text.lower() and 'two_factor' not in r.text.lower():
        _save_debug("01b_wrong_page", r.text)
        raise RuntimeError(f"Did not land on 2FA setup page. URL: {r.url}")

    log(f"✅ Setup page loaded ({len(r.text)} bytes)")
    page_html = r.text

    nonce = _get_fetch_nonce(page_html)
    release = _get_release_version(page_html)
    log(f"  nonce={'yes' if nonce else 'no'}, release={'yes' if release else 'no'}")

    csrf_initiate = _get_scoped_csrf(page_html, "/setup/initiate")
    if not csrf_initiate:
        for fm in re.finditer(r'<input[^>]+>', page_html, re.I):
            tag = fm.group(0)
            if 'js-data-url-csrf' in tag:
                vm = re.search(r'value="([^"]+)"', tag)
                if vm:
                    csrf_initiate = vm.group(1)
                    log("⚠ Used fallback CSRF extraction")
                    break
    if not csrf_initiate:
        _save_debug("01c_no_csrf", page_html)
        raise RuntimeError("Could not find CSRF token for initiate form.")
    log("✅ Tokens extracted (CSRF + nonce)")

    # ── Step 3: POST /setup/initiate (JSON API) ──────────────────────
    log("⏳ Calling initiate API...")
    headers_init = _api_headers(csrf_initiate, nonce, release)

    try:
        init_resp = s.post(INITIATE_URL, data={"type": "app"},
                           headers=headers_init, timeout=20, allow_redirects=False)
    except requests.exceptions.Timeout:
        raise RuntimeError("Timeout on initiate request.")

    _save_debug("02_initiate_resp", init_resp.text, "json")
    log(f"  Initiate HTTP {init_resp.status_code}")

    if init_resp.status_code not in (200, 201):
        _save_debug("02b_initiate_error", init_resp.text)
        raise RuntimeError(
            f"Initiate failed (HTTP {init_resp.status_code}): {init_resp.text[:300]}")

    try:
        init_data = init_resp.json()
    except Exception:
        raise RuntimeError(f"Initiate did not return JSON: {init_resp.text[:300]}")

    setup_key = init_data.get("mashed_secret", "").strip()
    if not setup_key:
        raise RuntimeError(f"No mashed_secret in response. Keys: {list(init_data.keys())}")
    result["setup_key"] = setup_key
    log(f"🔑 Setup key: {setup_key}")

    recovery_codes = init_data.get("formatted_recovery_codes", [])
    if isinstance(recovery_codes, list):
        recovery_codes = [c.strip() for c in recovery_codes if c.strip()]
    result["recovery_codes"] = recovery_codes
    if recovery_codes:
        log(f"✅ Got {len(recovery_codes)} recovery codes")

    # ── Step 4: Generate TOTP ─────────────────────────────────────────
    totp = generate_totp(setup_key)
    result["totp"] = totp
    log(f"🔑 Generated TOTP: {totp}")

    # ── Step 5: POST /setup/verify (JSON API) ────────────────────────
    log("⏳ Verifying TOTP code...")

    csrf_verify = _get_scoped_csrf(page_html, "/setup/verify")
    if not csrf_verify:
        log("⚠ Verify CSRF not found, re-fetching page...")
        r2 = s.get(TFA_SETUP_URL, timeout=20, allow_redirects=True)
        csrf_verify = _get_scoped_csrf(r2.text, "/setup/verify")
    if not csrf_verify:
        raise RuntimeError("Could not find CSRF token for verify form.")

    headers_verify = _api_headers(csrf_verify, nonce, release)
    try:
        verify_resp = s.post(VERIFY_URL, data={"type": "app", "otp": totp},
                             headers=headers_verify, timeout=20, allow_redirects=False)
    except requests.exceptions.Timeout:
        raise RuntimeError("Timeout on verify request.")

    _save_debug("03_verify_resp", verify_resp.text, "json")
    log(f"  Verify HTTP {verify_resp.status_code}")

    if verify_resp.status_code == 200:
        log("✅ TOTP verified!")
    elif verify_resp.status_code in (422, 429):
        log("⚠ First TOTP rejected, waiting for next period...")
        time.sleep(max(2, 30 - int(time.time()) % 30 + 1))
        totp = generate_totp(setup_key)
        result["totp"] = totp
        log(f"  Retrying with TOTP: {totp}")
        verify_resp2 = s.post(VERIFY_URL, data={"type": "app", "otp": totp},
                              headers=headers_verify, timeout=20, allow_redirects=False)
        _save_debug("04_verify_retry", verify_resp2.text, "json")
        if verify_resp2.status_code != 200:
            err_msg = ""
            try:
                err_msg = verify_resp2.json().get("error", "")
            except Exception:
                err_msg = verify_resp2.text[:200]
            raise RuntimeError(f"TOTP verification failed: {err_msg}")
        log("✅ TOTP verified on retry!")
    else:
        raise RuntimeError(
            f"TOTP verification failed (HTTP {verify_resp.status_code}): "
            f"{verify_resp.text[:200]}")

    # ── Step 6: Re-fetch setup page for fresh tokens ───────────────────
    log("⏳ Refreshing page tokens...")
    try:
        r_fresh = s.get(TFA_SETUP_URL, timeout=20, allow_redirects=True,
                        headers={"Referer": SECURITY_URL})
        _save_debug("04b_fresh_page", r_fresh.text)
        fresh_html = r_fresh.text
        log(f"  Fresh page HTTP {r_fresh.status_code} ({len(fresh_html)} bytes)")
        nonce_fresh = _get_fetch_nonce(fresh_html) or nonce
        release_fresh = _get_release_version(fresh_html) or release
    except Exception as e:
        log(f"⚠ Re-fetch failed ({e}), using original tokens")
        fresh_html = page_html
        nonce_fresh = nonce
        release_fresh = release

    # ── Step 7: POST /setup/recovery_download ─────────────────────────
    RECOVERY_DL_URL = "https://github.com/settings/two_factor_authentication/setup/recovery_download"
    log("⏳ Downloading recovery codes...")

    dl_form_body = _extract_form_body(fresh_html, "/setup/recovery_download")
    if not dl_form_body:
        dl_form_body = _extract_form_body(page_html, "/setup/recovery_download")

    if dl_form_body:
        dl_data = _parse_hidden("<form>" + dl_form_body + "</form>")
        log(f"  Download form fields: {list(dl_data.keys())}")
        dl_resp = s.post(RECOVERY_DL_URL, data=dl_data, timeout=20, allow_redirects=True)
        _save_debug("05_recovery_dl", dl_resp.text, "txt")
        log(f"  Recovery download HTTP {dl_resp.status_code}")
        if dl_resp.status_code not in (200, 201, 302):
            log("⚠ Standard POST failed, trying JSON API...")
            csrf_dl = _get_scoped_csrf(fresh_html, "/setup/recovery_download")
            if csrf_dl:
                headers_dl = _api_headers(csrf_dl, nonce_fresh, release_fresh)
                dl_resp2 = s.post(RECOVERY_DL_URL, data=dl_data, headers=headers_dl,
                                  timeout=20, allow_redirects=True)
                _save_debug("05b_recovery_dl_api", dl_resp2.text, "txt")
                log(f"  Recovery download (API) HTTP {dl_resp2.status_code}")
    else:
        log("⚠ Could not find recovery download form — skipping")

    # ── Step 8: POST /setup/enable ────────────────────────────────────
    log("⏳ Enabling 2FA...")

    enable_form_body = _extract_form_body(fresh_html, "/setup/enable")
    if not enable_form_body:
        enable_form_body = _extract_form_body(page_html, "/setup/enable")

    if enable_form_body:
        enable_data = _parse_hidden("<form>" + enable_form_body + "</form>")
        enable_data["type"] = "app"
        log(f"  Enable form fields: {list(enable_data.keys())}")
        csrf_en = _get_scoped_csrf(fresh_html, "/setup/enable")
        if not csrf_en:
            csrf_en = _get_scoped_csrf(page_html, "/setup/enable")

        if csrf_en:
            headers_en = _api_headers(csrf_en, nonce_fresh, release_fresh)
            enable_resp = s.post(ENABLE_URL, data=enable_data, headers=headers_en,
                                 timeout=20, allow_redirects=True)
        else:
            log("⚠ No enable CSRF, trying standard POST...")
            enable_resp = s.post(ENABLE_URL, data=enable_data, timeout=20,
                                 allow_redirects=True)
        _save_debug("06_enable_resp", enable_resp.text)

        if enable_resp.status_code in (200, 201, 302):
            if 'Configured' in enable_resp.text or '/settings/security' in enable_resp.url:
                log("✅ 2FA enabled successfully!")
            else:
                log(f"✅ 2FA enable returned HTTP {enable_resp.status_code}")
        else:
            log(f"⚠ Enable HTTP {enable_resp.status_code}")
            _save_debug("06b_enable_error", enable_resp.text)
            if csrf_en:
                log("  Retrying without API headers...")
                enable_resp2 = s.post(ENABLE_URL, data=enable_data, timeout=20,
                                      allow_redirects=True)
                _save_debug("06c_enable_fallback", enable_resp2.text)
                if enable_resp2.status_code in (200, 201, 302):
                    log("✅ 2FA enabled (fallback)!")
                else:
                    log(f"⚠ Enable fallback HTTP {enable_resp2.status_code}")
    else:
        log("⚠ No enable form found — re-fetching page...")
        r3 = s.get(TFA_SETUP_URL, timeout=20, allow_redirects=True)
        _save_debug("06d_enable_refetch", r3.text)
        enable_fb = _extract_form_body(r3.text, "/setup/enable")
        if enable_fb:
            enable_data = _parse_hidden("<form>" + enable_fb + "</form>")
            enable_data["type"] = "app"
            csrf_re = _get_scoped_csrf(r3.text, "/setup/enable")
            if csrf_re:
                headers_re = _api_headers(csrf_re,
                                          _get_fetch_nonce(r3.text) or nonce,
                                          _get_release_version(r3.text) or release)
                enable_resp = s.post(ENABLE_URL, data=enable_data, headers=headers_re,
                                     timeout=20, allow_redirects=True)
            else:
                enable_resp = s.post(ENABLE_URL, data=enable_data, timeout=20,
                                     allow_redirects=True)
            _save_debug("06e_enable_refetch_resp", enable_resp.text)
            log(f"  Enable (refetch) HTTP {enable_resp.status_code}")
        else:
            raise RuntimeError("Could not find enable form in any page.")

    # ── Step 9: Save to file ──────────────────────────────────────────
    username = get_username_from_cookies(s) or "unknown"
    save_path = os.path.join(BASE_DIR, f"{username}_2fa.txt")
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(f"GitHub 2FA Setup - {username}\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"{'=' * 50}\n\n")
        f.write(f"Setup Key (TOTP Secret): {setup_key}\n\n")
        if recovery_codes:
            f.write("Recovery Codes:\n")
            for i, code in enumerate(recovery_codes, 1):
                f.write(f"  {i:2d}. {code}\n")
            f.write("\n")
        else:
            f.write("Recovery Codes: (not extracted - check GitHub settings)\n\n")
        f.write(f"{'=' * 50}\n")
    result["saved_to"] = save_path
    log(f"💾 Saved to: {os.path.basename(save_path)}")
    return result
