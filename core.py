#!/usr/bin/env python3
"""Backend logic for GitHub Education Benefits Tool.

This module is a backward-compatible facade that re-exports everything
from the ``lib`` sub-package.  Existing callers (api.py, cli.py, main.py)
can continue to ``import core`` and use ``core.function()`` as before.

The actual implementation now lives under:
    lib/config.py    — constants, settings, UA pool, helpers
    lib/htmlparse.py — regex-based HTML parsing helpers
    lib/auth.py      — session storage, login, 2FA submission
    lib/totp.py      — TOTP generation & full 2FA setup flow
    lib/school.py    — school search, geocoding, proximity sort
    lib/idcard.py    — student ID card PNG generation
    lib/github.py    — profile, billing, benefits, edu-app submission
    lib/pipeline.py  — AutoPipeline orchestrator
"""

# ── Re-export everything from sub-modules ────────────────────────────────
# Config / constants
from lib.config import (
    logger, BASE_DIR, _BUNDLE_DIR, _UA_POOL,
    LOGIN_URL, SESSION_URL, TWO_FACTOR_URL, PROFILE_URL,
    SCHOOL_SEARCH_URL, DEV_PACK_NEW_URL, PAYMENT_INFO_URL,
    CONTACT_UPDATE_URL, EMAILS_URL, BENEFITS_URL,
    SECURITY_URL, TFA_SETUP_URL, TFA_VERIFY_URL, TFA_ENABLE_URL,
    TFA_RECOVERY_URL,
    SESSION_FILE, SETTINGS_FILE, HISTORY_FILE,
    SCHOOL_LIST_FILE, KEYWORDS_FILE,
    DEFAULT_DOCUMENT_LABEL, TRANSCRIPT_DOCUMENT_LABEL, PHOTOS_DIR,
    DEFAULT_ADDRESS, DEFAULT_COORDS,
    INDO_CITIES, INDO_FIRST, INDO_LAST,
    _CAMERA_DEVICES, _CAMERA_FILENAMES,
    _debug_files, _DEBUG_HTML_NAMES,
    load_keywords, load_settings, save_settings,
    _build_session, _save_debug, _save_debug_file,
    read_log_file, clear_log_file, generate_indo_name,
    _generate_ua_pool,
    generate_student_bio, generate_repo_name, generate_repo_description,
    load_history, add_history_entry, clear_history,
)

# HTML parsing helpers
from lib.htmlparse import (
    _extract_token, _extract_form_body, _extract_form,
    _parse_hidden, _tag_attrs,
    _find_select_first, _find_select_names, _find_select_option_label,
    _get_input_val,
    _action_menu_vals, _action_menu_by_label, _action_menu_first,
    _get_scoped_csrf, _get_fetch_nonce, _get_release_version, _api_headers,
)

# Auth / session
from lib.auth import (
    load_sessions, save_sessions, add_session, remove_session,
    session_from_stored,
    login_with_cookie_str, login_with_password, submit_2fa,
    is_logged_in, get_username_from_cookies, get_profile_details,
)

# TOTP / 2FA
from lib.totp import generate_totp, check_2fa_status, setup_2fa

# School
from lib.school import (
    parse_schools, school_qualifies, _haversine,
    sort_schools_by_proximity, search_schools, get_all_queries,
    save_school_list, load_school_list_file, school_list_file_exists,
    geocode, get_school_address,
    _nominatim_throttle,
)

# ID card
from lib.idcard import (
    _make_png, _rect, FONT5x7, _bmp_text,
    _load_random_photo_png, _embed_photo_on_card,
    _ID_TEMPLATES, generate_student_id,
)

# Transcript
from lib.transcript import generate_transcript

# Logo
from lib.logo import fetch_logo, fetch_logos_bulk, get_logo_path

# GitHub actions
from lib.github import (
    scrape_profile_form, submit_profile_form,
    scrape_billing_form, submit_billing,
    get_benefits, get_full_profile,
    _build_photo_proof, submit_edu_app,
    AccountNotEligibleError,
    create_repository,
)
from lib.pipeline import SubmitCancelledError

# Pipeline
from lib.pipeline import AutoPipeline
