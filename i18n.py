#!/usr/bin/env python3
"""Internationalization (i18n) module for GitHub Edu Pro.

Supports Indonesian (id) and English (en) with easy extensibility.
Usage:
    from i18n import t, set_language, get_language

    set_language("id")
    print(t("login_title"))        # "LOGIN VIA COOKIE"
    print(t("login_failed"))       # "Login gagal — cookie invalid atau expired."
"""

import json
import os
from typing import Dict, Optional

# ── Language Strings ──────────────────────────────────────────────────────
_STRINGS: Dict[str, Dict[str, str]] = {
    # ══════════════════════════════════════════════════════════════════
    #  CLI strings
    # ══════════════════════════════════════════════════════════════════

    # ── Login ──
    "login_title":          {"id": "LOGIN VIA COOKIE",                        "en": "LOGIN VIA COOKIE"},
    "login_paste_hint":     {"id": "Paste cookie string dari browser (user_session, dll)",
                             "en": "Paste cookie string from browser (user_session, etc)"},
    "login_quit_hint":      {"id": "Ketik 'quit' untuk keluar",              "en": "Type 'quit' to exit"},
    "login_empty":          {"id": "Cookie kosong! Coba lagi.",              "en": "Cookie is empty! Try again."},
    "login_authenticating": {"id": "Authenticating...",                       "en": "Authenticating..."},
    "login_success":        {"id": "Login berhasil!",                        "en": "Login successful!"},
    "login_failed":         {"id": "Login gagal — cookie invalid atau expired.",
                             "en": "Login failed — cookies invalid or expired."},
    "login_error":          {"id": "Login error: {error}",                   "en": "Login error: {error}"},
    "bye":                  {"id": "Bye! 👋",                                "en": "Bye! 👋"},

    # ── Account Details ──
    "account_title":        {"id": "ACCOUNT DETAILS",                        "en": "ACCOUNT DETAILS"},
    "fetching_profile":     {"id": "Fetching profile...",                    "en": "Fetching profile..."},
    "account_new_warn":     {"id": "Akun baru {days} hari — kemungkinan ditolak!",
                             "en": "Account only {days} days old — likely to be rejected!"},

    # ── 2FA ──
    "tfa_title":            {"id": "TWO-FACTOR AUTH (2FA)",                  "en": "TWO-FACTOR AUTH (2FA)"},
    "tfa_checking":         {"id": "Checking 2FA status...",                 "en": "Checking 2FA status..."},
    "tfa_check_failed":     {"id": "Gagal cek 2FA: {error}",                "en": "Failed to check 2FA: {error}"},
    "tfa_already_active":   {"id": "2FA sudah aktif  ✅",                   "en": "2FA already active  ✅"},
    "tfa_not_active":       {"id": "2FA belum aktif — setup otomatis...",    "en": "2FA not active — auto setup..."},
    "tfa_setup_complete":   {"id": "2FA berhasil diaktifkan!",               "en": "2FA successfully enabled!"},
    "tfa_setup_failed":     {"id": "2FA setup gagal: {error}",              "en": "2FA setup failed: {error}"},
    "tfa_setup_error":      {"id": "2FA error: {error}",                    "en": "2FA error: {error}"},
    "tfa_detected":         {"id": "2FA sudah aktif (terdeteksi saat setup).",
                             "en": "2FA already active (detected during setup)."},
    "tfa_clipboard":        {"id": "Setup key → clipboard 📋",             "en": "Setup key → clipboard 📋"},
    "tfa_notepad":          {"id": "Detail 2FA dibuka di Notepad 📝",       "en": "2FA details opened in Notepad 📝"},
    "tfa_codes_na":         {"id": "(tidak tersedia)",                       "en": "(not available)"},
    "tfa_failed_continue":  {"id": "2FA gagal, lanjut tanpa 2FA…",          "en": "2FA failed, continuing without 2FA..."},

    # ── Pipeline ──
    "pipeline_title":       {"id": "FULL AUTO PIPELINE",                     "en": "FULL AUTO PIPELINE"},
    "pipeline_school_found":{"id": "Ditemukan {count} sekolah → menggunakan list yang ada.",
                             "en": "Found {count} schools → using existing list."},
    "pipeline_not_eligible":{"id": "❌ AKUN TIDAK MEMENUHI SYARAT!\n   GitHub redirect ke /pricing.\n   Kemungkinan: akun terlalu baru, email belum verifikasi, atau sudah pernah apply.",
                             "en": "❌ ACCOUNT NOT ELIGIBLE!\n   GitHub redirected to /pricing.\n   Possible reasons: account too new, email not verified, or already applied."},
    "pipeline_not_eligible_short": {"id": "Akun tidak memenuhi syarat untuk GitHub Education",
                                    "en": "Account is not eligible for GitHub Education"},
    "pipeline_step_bio":    {"id": "Bio & Lokasi",                           "en": "Bio & Location"},
    "pipeline_step_repo":   {"id": "Buat Repository",                        "en": "Create Repository"},
    "pipeline_bio_updated": {"id": "Bio dan lokasi diperbarui",              "en": "Bio and location updated"},
    "pipeline_repo_created":{"id": "Repository berhasil dibuat: {name}",     "en": "Repository created: {name}"},
    "pipeline_repo_failed": {"id": "Pembuatan repository gagal",             "en": "Repository creation failed"},

    # ── Monitor ──
    "monitor_title":        {"id": "STATUS MONITORING",                      "en": "STATUS MONITORING"},
    "monitor_watching":     {"id": "Memantau status aplikasi (refresh /5 s)",
                             "en": "Monitoring application status (refresh /5 s)"},
    "monitor_ctrlc":        {"id": "Tekan Ctrl+C untuk kembali ke login.",
                             "en": "Press Ctrl+C to return to login."},
    "monitor_no_data":      {"id": "Belum ada data.",                        "en": "No data yet."},
    "monitor_stopped":      {"id": "Monitoring dihentikan.",                 "en": "Monitoring stopped."},
    "monitor_rejected_reason": {"id": "Alasan: {reason}",                   "en": "Reason: {reason}"},

    # ── General ──
    "cancelled":            {"id": "Dibatalkan.",                            "en": "Cancelled."},
    "stopped":              {"id": "Dihentikan.",                            "en": "Stopped."},
    "submit_failed":        {"id": "Submit gagal.",                          "en": "Submit failed."},
    "done_label":           {"id": "SELESAI",                                "en": "DONE"},
    "back_to_login":        {"id": "↩  Kembali ke login…",                  "en": "↩  Returning to login..."},
    "press_enter":          {"id": "Enter untuk lanjut…",                    "en": "Press Enter to continue..."},
    "press_enter_exit":     {"id": "Enter untuk keluar…",                    "en": "Press Enter to exit..."},
    "fatal_error":          {"id": "Fatal: {error}",                        "en": "Fatal: {error}"},
    "failed_generic":       {"id": "Gagal: {error}",                        "en": "Failed: {error}"},

    # ══════════════════════════════════════════════════════════════════
    #  GUI / Web UI strings
    # ══════════════════════════════════════════════════════════════════
    
    # ── General ──
    "ui_sign_in":           {"id": "Masuk",                                  "en": "Sign In"},
    "ui_logout":            {"id": "Keluar",                                 "en": "Logout"},
    "ui_back":              {"id": "Kembali",                                "en": "Back"},
    "ui_not_logged_in":     {"id": "Belum login",                            "en": "Not logged in"},
    "ui_loading":           {"id": "Memuat...",                              "en": "Loading..."},
    "ui_save":              {"id": "Simpan",                                 "en": "Save"},
    "ui_refresh":           {"id": "Muat Ulang",                             "en": "Refresh"},
    "ui_start":             {"id": "Mulai",                                  "en": "Start"},
    "ui_stop":              {"id": "Berhenti",                               "en": "Stop"},
    "ui_cancel":            {"id": "Batal",                                  "en": "Cancel"},
    "ui_ok":                {"id": "OK",                                     "en": "OK"},
    "ui_confirm":           {"id": "Konfirmasi",                             "en": "Confirm"},
    "ui_ready":             {"id": "Siap",                                   "en": "Ready"},
    "ui_done":              {"id": "Selesai",                                "en": "Done"},
    "ui_error":             {"id": "Kesalahan",                              "en": "Error"},
    
    # ── Navigation ──
    "ui_dashboard":         {"id": "Dasbor",                                 "en": "Dashboard"},
    "ui_settings":          {"id": "Pengaturan",                             "en": "Settings"},
    "ui_search":            {"id": "Cari Sekolah",                           "en": "Search Schools"},
    "ui_full_auto":         {"id": "Mode Otomatis Penuh",                    "en": "Full Auto Mode"},
    "ui_benefits":          {"id": "Daftar Manfaat",                         "en": "Benefit Applications"},
    "ui_sessions":          {"id": "Sesi Tersimpan",                         "en": "Saved Sessions"},
    "ui_billing":           {"id": "Alamat Penagihan",                       "en": "Billing Address"},
    "ui_profile":           {"id": "Profil",                                 "en": "Profile"},
    "ui_edit_profile":      {"id": "Edit Profil",                            "en": "Edit Profile"},
    "ui_logs":              {"id": "Log Aplikasi",                           "en": "Application Log"},
    "ui_tfa_setup":         {"id": "Setup 2FA",                              "en": "2FA Setup"},
    
    # ── Login Page ──
    "ui_login_cookie":      {"id": "Login dengan Cookie",                    "en": "Login with Cookies"},
    "ui_login_password":    {"id": "Login dengan Password",                  "en": "Login with Password"},
    "ui_paste_cookie":      {"id": "Paste string cookie (a=b; c=d)",         "en": "Paste cookie string (a=b; c=d)"},
    "ui_username_email":    {"id": "Username atau Email",                    "en": "Username or Email"},
    "ui_password":          {"id": "Password",                               "en": "Password"},
    "ui_login_btn":         {"id": "LOGIN",                                  "en": "LOGIN"},
    "ui_session_manager":   {"id": "Buka Session Manager",                   "en": "Open Session Manager"},
    
    # ── Dashboard ──
    "ui_account_overview":  {"id": "Ringkasan Akun",                         "en": "Account Overview"},
    "ui_username":          {"id": "Username",                               "en": "Username"},
    "ui_name":              {"id": "Nama",                                   "en": "Name"},
    "ui_email":             {"id": "Email",                                  "en": "Email"},
    "ui_account_age":       {"id": "Umur Akun",                              "en": "Account Age"},
    "ui_tfa":               {"id": "2FA",                                    "en": "2FA"},
    "ui_quick_actions":     {"id": "Aksi Cepat",                             "en": "Quick Actions"},
    "ui_account_detail":    {"id": "Detail Akun",                            "en": "Account Detail"},
    "ui_benefits_list":     {"id": "Daftar Benefit",                         "en": "Benefits List"},
    "ui_view_logs":         {"id": "Lihat Log",                              "en": "View Logs"},
    
    # ── Search ──
    "ui_school_search":     {"id": "Pencarian Sekolah",                      "en": "School Search"},
    "ui_search_options":    {"id": "Opsi Pencarian",                         "en": "Search Options"},
    "ui_manual_keyword":    {"id": "Keyword manual (kosongkan untuk otomatis)", "en": "Manual keyword (leave empty for auto)"},
    "ui_manual":            {"id": "MANUAL",                                 "en": "MANUAL"},
    "ui_auto_all":          {"id": "OTOMATIS SEMUA",                         "en": "AUTO ALL"},
    "ui_progress":          {"id": "Progres",                                "en": "Progress"},
    "ui_qualifying":        {"id": "Sekolah Memenuhi Syarat",                "en": "Qualifying Schools"},
    "ui_found":             {"id": "Ditemukan",                              "en": "Found"},
    "ui_qualified":         {"id": "Memenuhi Syarat",                        "en": "Qualified"},
    
    # ── Auto Mode ──
    "ui_spoof_coords":      {"id": "Spoof Koordinat",                        "en": "Spoof Coordinates"},
    "ui_school_selection":  {"id": "Pilihan Sekolah",                        "en": "School Selection"},
    "ui_auto_random":       {"id": "Otomatis (acak)",                        "en": "Auto (random)"},
    "ui_activity_log":      {"id": "Log Aktivitas",                          "en": "Activity Log"},
    "ui_force_stop":        {"id": "PAKSA BERHENTI",                         "en": "FORCE STOP"},
    
    # ── Sessions ──
    "ui_saved_sessions":    {"id": "Sesi Tersimpan",                         "en": "Saved Sessions"},
    "ui_use_selected":      {"id": "GUNAKAN TERPILIH",                       "en": "USE SELECTED"},
    "ui_delete":            {"id": "HAPUS",                                  "en": "DELETE"},
    "ui_no_sessions":       {"id": "Tidak ada sesi tersimpan",               "en": "No saved sessions"},
    
    # ── Billing ──
    "ui_edit_billing":      {"id": "Edit Alamat Penagihan",                  "en": "Edit Billing Address"},
    "ui_billing_details":   {"id": "Detail Penagihan",                       "en": "Billing Details"},
    "ui_first_name":        {"id": "Nama Depan",                             "en": "First Name"},
    "ui_last_name":         {"id": "Nama Belakang",                          "en": "Last Name"},
    "ui_address1":          {"id": "Alamat Baris 1",                         "en": "Address Line 1"},
    "ui_address2":          {"id": "Alamat Baris 2",                         "en": "Address Line 2"},
    "ui_city":              {"id": "Kota",                                   "en": "City"},
    "ui_region":            {"id": "Wilayah / Provinsi",                     "en": "Region / Province"},
    "ui_postal_code":       {"id": "Kode Pos",                               "en": "Postal Code"},
    "ui_country_code":      {"id": "Kode Negara",                            "en": "Country Code"},
    "ui_save_billing":      {"id": "SIMPAN TAGIHAN",                         "en": "SAVE BILLING"},
    "ui_reload":            {"id": "MUAT ULANG",                             "en": "RELOAD"},
    
    # ── Profile ──
    "ui_profile_info":      {"id": "Informasi Profil",                       "en": "Profile Information"},
    "ui_created":           {"id": "Dibuat",                                 "en": "Created"},
    "ui_bio":               {"id": "Bio",                                    "en": "Bio"},
    "ui_company":           {"id": "Perusahaan",                             "en": "Company"},
    "ui_location":          {"id": "Lokasi",                                 "en": "Location"},
    "ui_website":           {"id": "Website",                                "en": "Website"},
    "ui_public_repos":      {"id": "Repo Publik",                            "en": "Public Repos"},
    "ui_followers":         {"id": "Pengikut",                               "en": "Followers"},
    "ui_following":         {"id": "Mengikuti",                              "en": "Following"},
    "ui_profile_details":   {"id": "Detail Profil",                          "en": "Profile Details"},
    "ui_display_name":      {"id": "Nama Tampilan",                          "en": "Display Name"},
    "ui_public_email":      {"id": "Email Publik",                           "en": "Public Email"},
    "ui_pronouns":          {"id": "Kata Ganti",                             "en": "Pronouns"},
    "ui_update_profile":    {"id": "UPDATE PROFIL",                          "en": "UPDATE PROFILE"},
    
    # ── Benefits ──
    "ui_summary":           {"id": "Ringkasan",                              "en": "Summary"},
    "ui_applications":      {"id": "Aplikasi",                               "en": "Applications"},
    "ui_detail":            {"id": "Detail",                                 "en": "Detail"},
    "ui_total":             {"id": "Total",                                  "en": "Total"},
    "ui_approved":          {"id": "Disetujui",                              "en": "Approved"},
    "ui_pending":           {"id": "Pending",                                "en": "Pending"},
    "ui_rejected":          {"id": "Ditolak",                                "en": "Rejected"},
    
    # ── 2FA ──
    "ui_tfa_status":        {"id": "Status",                                 "en": "Status"},
    "ui_setup_log":         {"id": "Log Setup",                              "en": "Setup Log"},
    "ui_results":           {"id": "Hasil",                                  "en": "Results"},
    "ui_setup_key":         {"id": "Kunci Setup",                            "en": "Setup Key"},
    "ui_recovery_codes":    {"id": "Kode Pemulihan",                         "en": "Recovery Codes"},
    "ui_auto_setup_2fa":    {"id": "AUTO SETUP 2FA",                         "en": "AUTO SETUP 2FA"},
    "ui_open_file":         {"id": "Buka File",                              "en": "Open File"},
    "ui_copy_again":        {"id": "Salin Lagi",                             "en": "Copy Again"},
    "ui_tfa_enabled":       {"id": "2FA sudah aktif",                        "en": "2FA is already enabled"},
    "ui_tfa_not_enabled":   {"id": "Belum Aktif — Siap untuk setup",         "en": "Not Enabled — Ready to setup"},
    "ui_tfa_complete":      {"id": "Setup 2FA Selesai!",                     "en": "2FA Setup Complete!"},
    
    # ── Settings ──
    "ui_default_address":   {"id": "Alamat Default",                         "en": "Default Address"},
    "ui_default_coords":    {"id": "Koordinat Default",                      "en": "Default Coordinates"},
    "ui_latitude":          {"id": "Latitude",                               "en": "Latitude"},
    "ui_longitude":         {"id": "Longitude",                              "en": "Longitude"},
    "ui_automation":        {"id": "Otomatisasi",                            "en": "Automation"},
    "ui_document_label":    {"id": "Label Dokumen",                          "en": "Document Label"},
    "ui_search_delay":      {"id": "Delay Pencarian (detik)",                "en": "Search Delay (sec)"},
    "ui_id_validity":       {"id": "Validitas ID (hari)",                    "en": "ID Validity (days)"},
    "ui_appearance":        {"id": "Tampilan",                               "en": "Appearance"},
    "ui_theme":             {"id": "Tema",                                   "en": "Theme"},
    "ui_theme_light":       {"id": "Terang",                                 "en": "Light"},
    "ui_theme_dark":        {"id": "Gelap",                                  "en": "Dark"},
    "ui_language":          {"id": "Bahasa",                                 "en": "Language"},
    "ui_data_files":        {"id": "File Data",                              "en": "Data Files"},
    "ui_school_list":       {"id": "Daftar Sekolah",                         "en": "School List"},
    "ui_keywords":          {"id": "Kata Kunci",                             "en": "Keywords"},
    "ui_upload":            {"id": "Unggah",                                 "en": "Upload"},
    "ui_save_settings":     {"id": "SIMPAN PENGATURAN",                      "en": "SAVE SETTINGS"},
    
    # ── Validation ──
    "ui_required_field":    {"id": "Field wajib diisi",                      "en": "This field is required"},
    "ui_invalid_email":     {"id": "Format email tidak valid",               "en": "Invalid email format"},
    "ui_validation_error":  {"id": "Mohon perbaiki kesalahan di form",       "en": "Please fix the errors in the form"},
    
    # ── Toasts / Messages ──
    "ui_login_success":     {"id": "Login berhasil!",                        "en": "Login successful!"},
    "ui_login_failed":      {"id": "Login gagal",                            "en": "Login failed"},
    "ui_session_saved":     {"id": "Sesi tersimpan!",                        "en": "Session saved!"},
    "ui_session_deleted":   {"id": "Sesi dihapus",                           "en": "Session deleted"},
    "ui_session_expired":   {"id": "Sesi kedaluwarsa",                       "en": "Session expired"},
    "ui_billing_saved":     {"id": "Tagihan tersimpan!",                     "en": "Billing saved!"},
    "ui_profile_updated":   {"id": "Profil diperbarui!",                     "en": "Profile updated!"},
    "ui_settings_saved":    {"id": "Pengaturan tersimpan!",                  "en": "Settings saved!"},
    "ui_copied":            {"id": "Disalin ke clipboard!",                  "en": "Copied to clipboard!"},
    "ui_log_cleared":       {"id": "Log dihapus",                            "en": "Log cleared"},
    "ui_stop_signal":       {"id": "Sinyal stop terkirim",                   "en": "Stop signal sent"},
    "ui_cookie_empty":      {"id": "Cookie kosong",                          "en": "Cookie is empty"},
    "ui_enter_keyword":     {"id": "Masukkan kata kunci",                    "en": "Enter a keyword"},
    "ui_select_session":    {"id": "Pilih sesi terlebih dahulu",             "en": "Select a session first"},
}

# ── Active language ──
_current_lang: str = "id"  # default Indonesian


def set_language(lang: str):
    """Set the active language. Supported: 'id', 'en'."""
    global _current_lang
    if lang in ("id", "en"):
        _current_lang = lang
    else:
        raise ValueError(f"Unsupported language: {lang}. Use 'id' or 'en'.")


def get_language() -> str:
    """Return the current active language code."""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Translate a string key to the current language.

    Supports format placeholders:
        t("login_error", error="timeout")  →  "Login error: timeout"
    """
    entry = _STRINGS.get(key)
    if not entry:
        return key  # fallback: return the key itself
    text = entry.get(_current_lang) or entry.get("id") or entry.get("en") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass  # return unformatted if placeholder mismatch
    return text


def available_languages() -> list:
    """Return list of supported language codes."""
    return ["id", "en"]


def all_keys() -> list:
    """Return all registered translation keys."""
    return list(_STRINGS.keys())


def register(key: str, translations: Dict[str, str]):
    """Register or override a translation key at runtime.

    Example:
        register("custom_msg", {"id": "Pesan kustom", "en": "Custom message"})
    """
    _STRINGS[key] = translations


def get_all_translations(lang: Optional[str] = None) -> Dict[str, str]:
    """Return all translations for a language as {key: translated_text}.
    
    If lang is None, uses current language.
    """
    target = lang if lang in ("id", "en") else _current_lang
    result = {}
    for key, entry in _STRINGS.items():
        result[key] = entry.get(target) or entry.get("id") or entry.get("en") or key
    return result
