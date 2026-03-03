"""GitHub API interactions — profile, billing, benefits, and edu app submission."""
import base64
import html
import json
import mimetypes
import os
import random
import re
import urllib.parse
from typing import Dict, List

import requests


# ── Custom Exceptions ─────────────────────────────────────────────────────
class AccountNotEligibleError(Exception):
    """Raised when GitHub redirects to /pricing, indicating account is not eligible."""
    pass


from .config import (
    BASE_DIR, PROFILE_URL, PAYMENT_INFO_URL, CONTACT_UPDATE_URL,
    EMAILS_URL, BENEFITS_URL, DEV_PACK_NEW_URL, SCHOOL_SEARCH_URL,
    DEFAULT_COORDS, DEFAULT_DOCUMENT_LABEL,
    _UA_POOL, _CAMERA_DEVICES, _CAMERA_FILENAMES,
    _save_debug_file, _debug_files, logger,
)
from .auth import get_username_from_cookies, get_profile_details
from .htmlparse import (
    _extract_token, _extract_form, _extract_form_body, _parse_hidden,
    _tag_attrs, _get_input_val, _find_select_first, _find_select_names,
    _find_select_option_label, _action_menu_by_label, _action_menu_first,
)
from .school import parse_schools


# ── Profile ───────────────────────────────────────────────────────────────
def scrape_profile_form(s) -> Dict[str, str]:
    """Scrape the profile settings page for all editable fields."""
    fields = {}
    try:
        r = s.get(PROFILE_URL, timeout=20)
        r.raise_for_status()
        t = r.text
        field_map = {
            "name": "user[profile_name]",
            "email": "user[profile_email]",
            "bio": "user[profile_bio]",
            "pronouns": "user[profile_pronouns]",
            "website": "user[profile_blog]",
            "company": "user[profile_company]",
            "location": "user[profile_location]",
        }
        for key, form_name in field_map.items():
            fields[key] = _get_input_val(t, form_name)
    except Exception as e:
        logger.warning("Failed to scrape profile form: %s", e)
    return fields


def submit_profile_form(s, fields: Dict[str, str]):
    """Submit updated profile fields to GitHub."""
    page = s.get(PROFILE_URL, timeout=20)
    page.raise_for_status()
    _save_debug_file("profile_page.html", page.text)
    username = get_username_from_cookies(s)
    
    # Try multiple ways to find the profile form
    form = None
    
    # Method 1: Direct action match
    if username:
        form = _extract_form(page.text, f"/users/{username}")
    
    # Method 2: Try settings/profile action
    if not form:
        form = _extract_form(page.text, "/settings/profile")
    
    # Method 3: Find form by class
    if not form:
        m = re.search(
            r'(<form[^>]+class="[^"]*edit_user[^"]*"[^>]*>)(.*?)</form>',
            page.text, re.S | re.I)
        if m:
            form = {"tag": m.group(1), "body": m.group(2)}
    
    # Method 4: Any form with user[ fields
    if not form:
        m = re.search(
            r'(<form[^>]*>)(.*?user\[profile_.*?)</form>',
            page.text, re.S | re.I)
        if m:
            form = {"tag": m.group(1), "body": m.group(2)}
    
    # Method 5: Use API approach - GitHub now uses React for profile editing
    if not form:
        token = _extract_token(page.text)
        if token and username:
            # Try the API endpoint
            api_payload = {}
            field_api_map = {
                "name": "name",
                "bio": "bio", 
                "company": "company",
                "location": "location",
                "blog": "blog",
            }
            for key, api_key in field_api_map.items():
                if key in fields:
                    api_payload[api_key] = fields[key]
            if "website" in fields:
                api_payload["blog"] = fields["website"]
            
            if api_payload:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRF-Token": token,
                    "Origin": "https://github.com",
                    "Referer": PROFILE_URL,
                }
                try:
                    r = s.patch(f"https://github.com/users/{username}", 
                               json={"user": api_payload}, headers=headers, timeout=20)
                    if r.status_code < 400:
                        logger.info("Profile updated via API")
                        return
                except Exception as e:
                    logger.debug("API profile update failed: %s", e)
        
        # If all else fails, raise error
        raise RuntimeError("Profile form not found.")
    
    fa = _tag_attrs(form["tag"])
    action = fa.get("action", f"/users/{username}" if username else "/settings/profile")
    action_url = urllib.parse.urljoin("https://github.com", action)
    payload = _parse_hidden(form["body"])
    if "authenticity_token" not in payload:
        tok = _extract_token(form["body"]) or _extract_token(page.text)
        if tok:
            payload["authenticity_token"] = tok
    field_map = {
        "name": "user[profile_name]",
        "email": "user[profile_email]",
        "bio": "user[profile_bio]",
        "company": "user[profile_company]",
        "location": "user[profile_location]",
        "website": "user[profile_blog]",
        "pronouns": "user[profile_pronouns]",
    }
    for key, form_name in field_map.items():
        if key in fields:
            payload[form_name] = fields[key]
    r = s.post(action_url, data=payload, timeout=20, allow_redirects=True)
    if r.status_code >= 400:
        raise RuntimeError(f"Profile update failed ({r.status_code}).")


# ── Billing ───────────────────────────────────────────────────────────────
def scrape_billing_form(s) -> Dict[str, str]:
    """Scrape the billing/payment page for all editable billing fields."""
    fields = {}
    try:
        r = s.get(PAYMENT_INFO_URL, timeout=20)
        r.raise_for_status()
        t = r.text
        for field in ["first_name", "last_name", "address1", "address2",
                      "city", "country_code", "region", "postal_code"]:
            fields[field] = _get_input_val(t, f"billing_contact[{field}]")
    except Exception as e:
        logger.warning("Failed to scrape billing form: %s", e)
    return fields


def submit_billing(s, addr):
    page = s.get(PAYMENT_INFO_URL, timeout=20)
    page.raise_for_status()
    _save_debug_file("billing_page.html", page.text)
    
    # Get CSRF token early for all methods
    token = _extract_token(page.text)
    
    # Try multiple form extraction methods
    form = _extract_form(page.text, "/account/contact")
    if not form:
        form = _extract_form(page.text, "/settings/billing/contact")
    if not form:
        form = _extract_form(page.text, "contact")
    if not form:
        # Try finding any form with billing_contact fields
        m = re.search(
            r'(<form[^>]*>)(.*?billing_contact\[.*?)</form>',
            page.text, re.S | re.I)
        if m:
            form = {"tag": m.group(1), "body": m.group(2)}
    
    if not form:
        fb = _extract_form_body(page.text, "/account/contact")
        if fb:
            payload = _parse_hidden(fb)
            if "authenticity_token" not in payload and token:
                payload["authenticity_token"] = token
            payload.update(addr)
            r = s.post(CONTACT_UPDATE_URL, data=payload, timeout=20, allow_redirects=True)
            if r.status_code < 400:
                return
            _save_debug_file("billing_error.html", r.text)
        
        # Try API approach as fallback
        if token:
            api_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": token,
                "Origin": "https://github.com",
                "Referer": PAYMENT_INFO_URL,
            }
            try:
                # Convert form field names to API format
                api_addr = {}
                for k, v in addr.items():
                    # billing_contact[first_name] -> first_name
                    clean_key = k.replace("billing_contact[", "").replace("]", "")
                    api_addr[clean_key] = v
                
                r = s.post("https://github.com/settings/billing/contact",
                          json={"billing_contact": api_addr}, headers=api_headers, timeout=20)
                if r.status_code < 400:
                    logger.info("Billing updated via API")
                    return
            except Exception as e:
                logger.debug("API billing update failed: %s", e)
        
        raise RuntimeError("Billing form not found. See billing_page.html")
    
    fa = _tag_attrs(form["tag"])
    action = fa.get("action", "/account/contact")
    action_url = urllib.parse.urljoin("https://github.com", action)
    method = fa.get("method", "post").upper()
    payload = _parse_hidden(form["body"])
    if "authenticity_token" not in payload and token:
        payload["authenticity_token"] = token
    payload.update(addr)
    if method == "POST":
        r = s.post(action_url, data=payload, timeout=20, allow_redirects=True)
    else:
        r = s.patch(action_url, data=payload, timeout=20, allow_redirects=True)
    if r.status_code >= 400:
        _save_debug_file("billing_error.html", r.text)
        raise RuntimeError(f"Billing failed ({r.status_code}). See billing_error.html")


# ── Benefits ──────────────────────────────────────────────────────────────
def get_benefits(s) -> List[Dict[str, str]]:
    """Parse education benefits applications from the benefits page."""
    apps = []
    try:
        r = s.get(BENEFITS_URL, timeout=20)
        r.raise_for_status()
        for dm in re.finditer(
                r'<details[^>]+class="[^"]*billing-box-accordion[^"]*"[^>]*>(.*?)</details>',
                r.text, re.S | re.I):
            block = dm.group(1)
            app = {"status": "", "submitted": "", "approved_on": "", "type": "",
                   "message": "", "expires": "", "progress": ""}
            sm = re.search(r'<span[^>]+text-bold\s+f6[^>]*>\s*([^<]+)', block, re.I)
            if not sm:
                sm = re.search(r'text-bold\s+f6">\s*([^<]+)', block, re.I)
            if sm:
                app["status"] = html.unescape(sm.group(1)).strip()
            tm = re.search(r'text-right">\s*([^<]+)', block, re.I)
            if tm:
                app["submitted"] = html.unescape(tm.group(1)).strip()
            am = re.search(r'<strong>\s*\w+\s*</strong>\s*on\s+([^<]+)', block, re.I)
            if am:
                app["approved_on"] = html.unescape(am.group(1)).strip()
            atm = re.search(r'Application Type:</strong>\s*([^<]+)', block, re.I)
            if atm:
                app["type"] = html.unescape(atm.group(1)).strip()
            em = re.search(r'expire on\s*<strong>\s*([^<]+)', block, re.I)
            if em:
                app["expires"] = html.unescape(em.group(1)).strip()
            bm = re.search(r'<div[^>]+Box-body[^>]*>(.*?)</div>', block, re.S | re.I)
            if bm:
                msg = re.sub(r'<[^>]+>', '', bm.group(1))
                app["message"] = html.unescape(msg).strip()[:200]
            pm = re.search(r'style="width:\s*(\d+)%', block, re.I)
            if pm:
                app["progress"] = pm.group(1) + "%"
            apps.append(app)
    except Exception as e:
        logger.warning("Failed to fetch benefits: %s", e)
    return apps


def get_full_profile(s) -> Dict[str, str]:
    """Get extended profile details including bio, company, location, etc."""
    info = get_profile_details(s)
    try:
        r = s.get(PROFILE_URL, timeout=20)
        r.raise_for_status()
        bm = re.search(r'name="user\[profile_bio\]"[^>]*>([^<]*)', r.text, re.I)
        if bm:
            info["bio"] = html.unescape(bm.group(1)).strip()
        cm = re.search(r'name="user\[profile_company\]"[^>]*value="([^"]*)"', r.text, re.I)
        if cm:
            info["company"] = html.unescape(cm.group(1)).strip()
        lm = re.search(r'name="user\[profile_location\]"[^>]*value="([^"]*)"', r.text, re.I)
        if lm:
            info["location"] = html.unescape(lm.group(1)).strip()
        um = re.search(r'name="user\[profile_blog\]"[^>]*value="([^"]*)"', r.text, re.I)
        if um:
            info["website"] = html.unescape(um.group(1)).strip()
    except Exception:
        pass
    uname = info.get("username", "")
    if uname:
        try:
            r2 = requests.get(f"https://api.github.com/users/{uname}",
                              headers={"User-Agent": random.choice(_UA_POOL)}, timeout=10)
            if r2.status_code == 200:
                d = r2.json()
                info["public_repos"] = str(d.get("public_repos", 0))
                info["followers"] = str(d.get("followers", 0))
                info["following"] = str(d.get("following", 0))
                info["avatar_url"] = d.get("avatar_url", "")
                if not info.get("bio"):
                    info["bio"] = d.get("bio", "") or ""
                if not info.get("company"):
                    info["company"] = d.get("company", "") or ""
                if not info.get("location"):
                    info["location"] = d.get("location", "") or ""
        except Exception:
            pass
    return info


# ── Photo Proof ───────────────────────────────────────────────────────────
def _build_photo_proof(dp, camera_mode=False):
    """Build the photo_proof JSON payload."""
    mime, _ = mimetypes.guess_type(dp)
    if not mime:
        mime = "image/png"
    with open(dp, "rb") as f:
        enc = base64.b64encode(f.read()).decode()

    if camera_mode:
        meta = {
            "filename": random.choice(_CAMERA_FILENAMES),
            "type": "camera",
            "mimeType": mime,
            "deviceLabel": random.choice(_CAMERA_DEVICES),
        }
    else:
        meta = {
            "filename": os.path.basename(dp),
            "type": "upload",
            "mimeType": mime,
            "deviceLabel": None,
        }

    return json.dumps({"image": f"data:{mime};base64,{enc}",
                       "metadata": meta}, separators=(",", ":"))


# ── Education Application ────────────────────────────────────────────────
def submit_edu_app(s, school_name, doc_path, doc_label, lat=None, lon=None,
                   school_id=None, camera_mode=False):
    """Submit education application in 2 steps."""
    if not lat:
        lat = DEFAULT_COORDS["lat"]
    if not lon:
        lon = DEFAULT_COORDS["lon"]

    # ── Step 1: Get initial form from /new ──
    page = s.get(DEV_PACK_NEW_URL, timeout=20, allow_redirects=True)
    page.raise_for_status()
    
    # Check if redirected to pricing (account not eligible)
    final_url = page.url.lower()
    if "/pricing" in final_url or "github.com/pricing" in final_url:
        _save_debug_file("pricing_redirect.html", page.text)
        raise AccountNotEligibleError(
            "Account redirected to /pricing. This account is not eligible for GitHub Education. "
            "Possible reasons: account age too new, email not verified, or already applied."
        )
    
    _save_debug_file("edu_form_page.html", page.text)

    form = _extract_form(page.text, "/settings/education/developer_pack_applications")
    if not form:
        raise RuntimeError("Edu form not found. See edu_form_page.html")

    fa = _tag_attrs(form["tag"])
    action_url = urllib.parse.urljoin("https://github.com", fa.get("action", DEV_PACK_NEW_URL))
    payload = _parse_hidden(form["body"])
    tok = (payload.get("authenticity_token") or
           _extract_token(form["body"]) or _extract_token(page.text))
    if tok:
        payload["authenticity_token"] = tok

    payload["dev_pack_form[application_type]"] = "student"
    payload["dev_pack_form[school_name]"] = school_name

    if school_id:
        payload["dev_pack_form[selected_school_id]"] = str(school_id)
    else:
        sr = s.get(SCHOOL_SEARCH_URL, params={"q": school_name}, timeout=20)
        schs = parse_schools(sr.text)
        if schs:
            payload["dev_pack_form[selected_school_id]"] = schs[0]["id"]

    em = "dev_pack_form[school_email]"
    if em not in payload or not payload.get(em):
        ev = _find_select_first(form["body"], em)
        if ev:
            payload[em] = ev

    for en in _find_select_names(form["body"], "enrollment"):
        if en in payload and not payload[en]:
            payload.pop(en)
        if en not in payload:
            ev = _find_select_first(form["body"], en)
            if ev:
                payload[en] = ev

    payload["dev_pack_form[latitude]"] = str(lat)
    payload["dev_pack_form[longitude]"] = str(lon)
    payload["dev_pack_form[browser_location]"] = f"{lat},{lon}"
    payload["dev_pack_form[location_shared]"] = "true"
    payload["dev_pack_form[form_variant]"] = "initial_form"
    payload["continue"] = "Continue"
    payload.pop("submit", None)

    s2 = s.post(action_url, data=payload, timeout=30, allow_redirects=True)
    if s2.status_code >= 400:
        _save_debug_file("benefits_step1_error.html", s2.text)
        raise RuntimeError(f"Step1 fail ({s2.status_code}). See benefits_step1_error.html")
    _save_debug_file("benefits_continue.html", s2.text)

    # ── Step 2: Upload proof form ──
    f2 = _extract_form(s2.text, "/settings/education/developer_pack_applications")
    if not f2:
        _save_debug_file("benefits_step2_error.html", s2.text)
        raise RuntimeError("Upload form not found after Continue. See benefits_continue.html")

    p2 = _parse_hidden(f2["body"])
    t2 = p2.get("authenticity_token") or _extract_token(f2["body"]) or _extract_token(s2.text)
    if t2:
        p2["authenticity_token"] = t2

    pk = "dev_pack_form[proof_type]"
    pv = _action_menu_by_label(s2.text, pk, doc_label)
    if pv:
        p2[pk] = pv
    else:
        do = _find_select_option_label(f2["body"], doc_label)
        if do:
            p2[do["name"]] = do["value"]
        else:
            fv = _action_menu_first(s2.text, pk)
            if fv:
                p2[pk] = fv

    pfn = "dev_pack_form[photo_proof]"
    p2[pfn] = _build_photo_proof(doc_path, camera_mode=camera_mode)
    p2["dev_pack_form[form_variant]"] = "upload_proof_form"
    p2["submit"] = "Submit Application"
    p2.pop("continue", None)

    fa2 = _tag_attrs(f2["tag"])
    action_url2 = urllib.parse.urljoin("https://github.com", fa2.get("action", action_url))
    r = s.post(action_url2, data=p2, timeout=60, allow_redirects=True)
    if r.status_code >= 400:
        _save_debug_file("benefits_submit_error.html", r.text)
        raise RuntimeError(f"Submit fail ({r.status_code}). See benefits_submit_error.html")
    _save_debug_file("benefits_submit.html", r.text)


# ── Repository Creation ───────────────────────────────────────────────────

def _extract_fetch_nonce(text):
    """Extract fetch-nonce from GitHub page for React API calls."""
    m = re.search(r'<meta\s+name="fetch-nonce"\s+content="([^"]+)"', text)
    return m.group(1) if m else None



def create_repository(s, name: str, description: str = "",
                      add_readme: bool = True, private: bool = False) -> bool:
    """Create a new GitHub repository using the React app's verified-fetch API."""
    from .auth import get_username_from_cookies

    try:
        username = get_username_from_cookies(s)
        if not username:
            logger.warning("Failed to get username for repo creation")
            return False

        logger.info("Creating repo '%s' for user '%s'", name, username)

        # Fetch /new page for fetch-nonce (no CSRF token needed for React API)
        new_page = s.get("https://github.com/new", timeout=20)
        fetch_nonce = _extract_fetch_nonce(new_page.text)
        if not fetch_nonce:
            _save_debug_file("repo_new_page.html", new_page.text)
            logger.warning(
                "fetch-nonce missing from /new page – GitHub may have changed the "
                "<meta name='fetch-nonce'> tag. Check _debug/repo_new_page.html."
            )
            return False

        # Exact payload structure from GitHub's React repo-creation bundle (tW function)
        payload = {
            "owner": username,
            "template_repository_id": "",
            "include_all_branches": "0",
            "repository": {
                "name": name,
                "visibility": "private" if private else "public",
                "description": description,
                "auto_init": "1" if add_readme else "0",
                "license_template": "",
                "gitignore_template": "",
            },
            "metrics": {"submitted_using_v2": True},
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "GitHub-Verified-Fetch": "true",
            "X-Fetch-Nonce": fetch_nonce,
            "Origin": "https://github.com",
            "Referer": "https://github.com/new",
        }

        # Must NOT follow redirects — response is JSON {"data": {"redirect": "/user/repo"}}
        r = s.post("https://github.com/repositories", json=payload,
                   headers=headers, timeout=30, allow_redirects=False)
        _save_debug_file("repo_response.txt", f"Status: {r.status_code}\nBody:\n{r.text}")

        if r.status_code == 200:
            try:
                data = r.json()
                redirect = (data.get("data") or {}).get("redirect")
                if redirect:
                    logger.info("Repository created: %s", redirect)
                    return True
                error = (data.get("data") or {}).get("error")
                if error:
                    logger.warning("Repository server error: %s", error)
                    _save_debug_file("repo_error.txt", str(data))
            except Exception as e:
                logger.warning("Repository JSON parse error: %s", e)
        elif r.status_code == 422:
            try:
                logger.warning("Repository 422: %s", r.json())
            except Exception:
                logger.warning("Repository 422: %s", r.text[:300])
        else:
            logger.warning(
                "Repository POST /repositories returned unexpected status %s – "
                "GitHub may have changed the endpoint or payload format. "
                "Check _debug/repo_response.txt.",
                r.status_code
            )

        # Final existence check
        check = s.get(f"https://github.com/{username}/{name}", timeout=10)
        if check.status_code == 200 and name.lower() in check.url.lower():
            logger.info("Repository verified exists: %s/%s", username, name)
            return True

        logger.warning("Repository creation failed")
        return False

    except Exception as e:
        logger.warning("Failed to create repository: %s", e)
        _save_debug_file("repo_exception.txt", f"Exception: {e}")
        return False




