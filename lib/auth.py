"""Authentication — session storage, login, and cookie management."""
import json
import os
from datetime import datetime
from typing import Dict, List

from .config import (
    SESSION_FILE, LOGIN_URL, SESSION_URL, TWO_FACTOR_URL,
    PROFILE_URL, EMAILS_URL, _build_session, _UA_POOL, logger,
)
from .htmlparse import _extract_token

import html
import random
import re
import requests


# ── Session Storage ───────────────────────────────────────────────────────
def load_sessions() -> List[Dict]:
    if not os.path.exists(SESSION_FILE):
        return []
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sessions(data: List[Dict]):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_session(label, cookie_str):
    ss = load_sessions()
    ss.append({"label": label, "cookies": cookie_str, "created": datetime.now().isoformat()})
    save_sessions(ss)


def remove_session(index):
    ss = load_sessions()
    if 0 <= index < len(ss):
        rm = ss.pop(index)
        save_sessions(ss)
        return rm.get("label", "?")
    return None


def session_from_stored(index):
    ss = load_sessions()
    if not (0 <= index < len(ss)):
        raise ValueError("Invalid index")
    return login_with_cookie_str(ss[index]["cookies"])


# ── Login ─────────────────────────────────────────────────────────────────
def _make_expiry_hook():
    """Returns a requests response hook that logs when session is redirected to login."""
    def _hook(r, *args, **kwargs):
        if r.is_redirect:
            loc = r.headers.get("location", "")
            if "github.com/login" in loc or "login?return_to" in loc:
                logger.warning("Session expired – redirected to login (%s)", loc)
    return _hook


def login_with_cookie_str(cookie_str):
    s = _build_session()
    for chunk in cookie_str.split(";"):
        if "=" not in chunk:
            continue
        k, v = chunk.split("=", 1)
        k, v = k.strip(), v.strip()
        if k:
            s.cookies.set(k, v)
    s.hooks["response"].append(_make_expiry_hook())
    return s


def login_with_password(username, password):
    s = _build_session()
    page = s.get(LOGIN_URL, timeout=20)
    token = _extract_token(page.text)
    if not token:
        raise RuntimeError("Login token not found.")
    resp = s.post(SESSION_URL, data={
        "login": username, "password": password,
        "authenticity_token": token, "commit": "Sign in",
    }, timeout=20, allow_redirects=True)
    if "two-factor" in resp.url:
        return s, resp
    return s, None


def submit_2fa(session, resp_text, otp):
    tok = _extract_token(resp_text)
    if not tok:
        raise RuntimeError("2FA token not found.")
    session.post(TWO_FACTOR_URL, data={"authenticity_token": tok, "otp": otp},
                 timeout=20, allow_redirects=True)


def is_logged_in(s):
    r = s.get(PROFILE_URL, allow_redirects=True, timeout=20)
    return r.status_code == 200 and "/login" not in r.url


# ── User Info ─────────────────────────────────────────────────────────────
def get_username_from_cookies(s) -> str:
    """Get username from dotcom_user cookie."""
    for c in s.cookies:
        if c.name == "dotcom_user":
            return c.value
    return ""


def get_profile_details(s) -> Dict[str, str]:
    """Get name, username, email, account age from profile page + API."""
    info = {"username": "", "name": "", "email": "", "created": "", "age_days": 0}
    info["username"] = get_username_from_cookies(s)
    try:
        r = s.get(PROFILE_URL, timeout=20)
        r.raise_for_status()
        m = re.search(r'name="user\[profile_name\]"[^>]*value="([^"]*)"', r.text, re.I)
        if not m:
            m = re.search(r'id="user_profile_name"[^>]*value="([^"]*)"', r.text, re.I)
        if m:
            info["name"] = html.unescape(m.group(1)).strip()
        m_email = re.search(r'name="user\[profile_email\]"[^>]*value="([^"]*)"', r.text, re.I)
        if m_email:
            info["email"] = html.unescape(m_email.group(1)).strip()
    except Exception:
        pass
    if not info["email"]:
        try:
            r2 = s.get(EMAILS_URL, timeout=20)
            r2.raise_for_status()
            m_em = re.search(
                r'<li[^>]*class="[^"]*primary[^"]*"[^>]*>.*?'
                r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
                r2.text, re.S | re.I)
            if m_em:
                info["email"] = m_em.group(1).strip()
            else:
                m_em2 = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r2.text)
                if m_em2:
                    info["email"] = m_em2.group(1).strip()
        except Exception:
            pass
    if info["username"]:
        try:
            r3 = requests.get(
                f"https://api.github.com/users/{info['username']}",
                headers={"User-Agent": random.choice(_UA_POOL)}, timeout=10)
            if r3.status_code == 200:
                d = r3.json()
                created = d.get("created_at", "")
                if created:
                    info["created"] = created
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    info["age_days"] = (datetime.now(dt.tzinfo) - dt).days
                if not info["name"] and d.get("name"):
                    info["name"] = d["name"]
                if not info["email"] and d.get("email"):
                    info["email"] = d["email"]
        except Exception:
            pass
    return info
