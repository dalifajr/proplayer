"""JS API Bridge — exposes core.py functions to the pywebview frontend."""
import json, os, threading, time, traceback
from datetime import datetime

import webview

import core
from i18n import t

class Api:
    """Every public method here is callable from JS via window.pywebview.api.<method>(...)"""

    def __init__(self):
        self.session = None
        self.user_info = {}
        self._stop_flag = False
        self._window = None          # set by app.py after window creation
        self._2fa_resp = None        # stashed 2FA response for submit_2fa
        self._confirm_result = None  # stashed answer for ask_confirm_submit

    # ── helpers ───────────────────────────────────────────────────────
    def _ok(self, data=None):
        return json.dumps({"ok": True, "data": data})

    def _err(self, msg):
        return json.dumps({"ok": False, "error": str(msg)})

    def _js(self, code):
        """Evaluate JS in the frontend (thread-safe)."""
        if self._window:
            self._window.evaluate_js(code)

    # ── Auth ──────────────────────────────────────────────────────────
    def login_cookie(self, cookie_str):
        try:
            s = core.login_with_cookie_str(cookie_str)
            if core.is_logged_in(s):
                self.session = s
                info = core.get_profile_details(s)
                self.user_info = info
                tfa = False
                try: tfa = core.check_2fa_status(s)
                except: pass
                info["tfa"] = tfa
                return self._ok(info)
            return self._err("Login failed — cookies invalid or expired.")
        except Exception as e:
            return self._err(e)

    def login_password(self, username, password):
        try:
            s, resp = core.login_with_password(username, password)
            if resp:
                # 2FA required
                self.session = s
                self._2fa_resp = resp
                return json.dumps({"ok": True, "data": {"needs_2fa": True}})
            self.session = s
            if core.is_logged_in(s):
                info = core.get_profile_details(s)
                self.user_info = info
                tfa = False
                try: tfa = core.check_2fa_status(s)
                except: pass
                info["tfa"] = tfa
                return self._ok(info)
            return self._err("Login failed.")
        except Exception as e:
            return self._err(e)

    def submit_2fa(self, otp):
        try:
            if not self.session or not self._2fa_resp:
                return self._err("No pending 2FA session.")
            core.submit_2fa(self.session, self._2fa_resp.text, otp)
            self._2fa_resp = None
            if core.is_logged_in(self.session):
                info = core.get_profile_details(self.session)
                self.user_info = info
                tfa = False
                try: tfa = core.check_2fa_status(self.session)
                except: pass
                info["tfa"] = tfa
                return self._ok(info)
            return self._err("Login failed after 2FA.")
        except Exception as e:
            return self._err(e)

    def logout(self):
        self.session = None
        self.user_info = {}
        self._2fa_resp = None
        return self._ok()

    def is_authenticated(self):
        return self._ok(self.session is not None and bool(self.user_info))

    # ── Profile ───────────────────────────────────────────────────────
    def get_profile(self):
        if not self.session: return self._err("Not logged in.")
        try:
            info = core.get_profile_details(self.session)
            self.user_info = info
            tfa = False
            try: tfa = core.check_2fa_status(self.session)
            except: pass
            info["tfa"] = tfa
            return self._ok(info)
        except Exception as e:
            return self._err(e)

    def get_full_profile(self):
        if not self.session: return self._err("Not logged in.")
        try:
            info = core.get_full_profile(self.session)
            self.user_info = info
            billing = {}
            try: billing = core.scrape_billing_form(self.session)
            except: pass
            tfa = False
            try: tfa = core.check_2fa_status(self.session)
            except: pass
            return self._ok({"profile": info, "billing": billing, "tfa": tfa})
        except Exception as e:
            return self._err(e)

    def get_profile_form(self):
        if not self.session: return self._err("Not logged in.")
        try:
            data = core.scrape_profile_form(self.session)
            return self._ok(data)
        except Exception as e:
            return self._err(e)

    def update_profile(self, fields_json):
        if not self.session: return self._err("Not logged in.")
        try:
            fields = json.loads(fields_json) if isinstance(fields_json, str) else fields_json
            core.submit_profile_form(self.session, fields)
            self.user_info["name"] = fields.get("name", "")
            return self._ok()
        except Exception as e:
            return self._err(e)

    # ── Billing ───────────────────────────────────────────────────────
    def get_billing(self):
        if not self.session: return self._err("Not logged in.")
        try:
            data = core.scrape_billing_form(self.session)
            return self._ok(data)
        except Exception as e:
            return self._err(e)

    def save_billing(self, fields_json):
        if not self.session: return self._err("Not logged in.")
        try:
            fields = json.loads(fields_json) if isinstance(fields_json, str) else fields_json
            addr = {f"billing_contact[{k}]": v for k, v in fields.items()}
            core.submit_billing(self.session, addr)
            return self._ok()
        except Exception as e:
            return self._err(e)

    # ── Sessions ──────────────────────────────────────────────────────
    def get_sessions(self):
        try:
            ss = core.load_sessions()
            return self._ok(ss)
        except Exception as e:
            return self._err(e)

    def use_session(self, index):
        try:
            s = core.session_from_stored(int(index))
            if core.is_logged_in(s):
                self.session = s
                info = core.get_profile_details(s)
                self.user_info = info
                tfa = False
                try: tfa = core.check_2fa_status(s)
                except: pass
                info["tfa"] = tfa
                return self._ok(info)
            return self._err("Session expired.")
        except Exception as e:
            return self._err(e)

    def delete_session(self, index):
        try:
            core.remove_session(int(index))
            return self._ok()
        except Exception as e:
            return self._err(e)

    def save_current_session(self, label, cookie_str):
        try:
            core.add_session(label, cookie_str)
            return self._ok()
        except Exception as e:
            return self._err(e)

    # ── Schools / Search ──────────────────────────────────────────────
    def get_school_list(self):
        try:
            if core.school_list_file_exists():
                schools = core.load_school_list_file()
                return self._ok(schools)
            return self._ok([])
        except Exception as e:
            return self._err(e)

    def search_manual(self, keyword):
        """Run school search in background, stream results to JS."""
        if not self.session: return self._err("Not logged in.")
        self._stop_flag = False
        threading.Thread(target=self._search_worker, args=([keyword],), daemon=True).start()
        return self._ok("started")

    def search_auto(self):
        if not self.session: return self._err("Not logged in.")
        self._stop_flag = False
        queries = core.get_all_queries()
        threading.Thread(target=self._search_worker, args=(queries,), daemon=True).start()
        return self._ok("started")

    def stop(self):
        self._stop_flag = True
        return self._ok()

    def _search_worker(self, queries):
        def on_prog(i, t, q):
            self._js(f"onSearchProgress({i},{t},{json.dumps(q)})")

        try:
            af, ql, nq = core.search_schools(
                self.session, queries,
                on_progress=on_prog,
                stop_flag=lambda: self._stop_flag)
            core.save_school_list(ql, nq)
            self._js(f"onSearchDone({json.dumps(ql)},{len(af)},{json.dumps(self._stop_flag)})")
        except Exception as e:
            self._js(f"onSearchError({json.dumps(str(e))})")

    # ── Auto Pipeline ────────────────────────────────────────────────
    def run_full_auto(self, lat=None, lon=None, school_json=None, cam_filter=None, proof_type=None):
        """Full pipeline: 2FA check/setup → AutoPipeline (mirrors cli.py flow)."""
        if not self.session: return self._err("Not logged in.")
        self._stop_flag = False
        manual = json.loads(school_json) if school_json else None
        # cam_filter: None=all, 'true'=cam-only, 'false'=upload-only
        if cam_filter == 'true':
            cf = True
        elif cam_filter == 'false':
            cf = False
        else:
            cf = None
        pt = proof_type if proof_type in ("id_card", "transcript") else "id_card"
        threading.Thread(target=self._full_auto_worker,
                         args=(lat, lon, manual, cf, pt), daemon=True).start()
        return self._ok("started")

    def _full_auto_worker(self, lat, lon, manual, cam_filter=None, proof_type="id_card"):
        def on_step(n, title):
            self._js(f"onAutoStep({n},{json.dumps(title)})")

        def on_log(msg, tag=""):
            self._js(f"onAutoLog({json.dumps(msg)},{json.dumps(tag)})")

        def on_sub(msg):
            self._js(f"onAutoSub({json.dumps(msg)})")

        def ask_use_existing(count):
            self._js(f"onAutoAskExisting({count})")
            self._ask_result = None
            for _ in range(600):  # max 30s
                if self._ask_result is not None:
                    return self._ask_result
                if self._stop_flag:
                    return False
                time.sleep(0.05)
            return False

        def on_tfa_done(result, clip_text):
            self._js(f"onAutoTfaDone({json.dumps(result)},{json.dumps(clip_text)})")

        def ask_confirm_submit(chosen, ai, slat, slon):
            info = {
                "school": chosen["name"],
                "city":   ai.get("city", ""),
                "region": ai.get("region", ""),
                "lat":    slat,
                "lon":    slon,
            }
            self._confirm_result = None
            self._js(f"onAutoConfirmSubmit({json.dumps(info)})")
            for _ in range(1200):  # max 60 s
                if self._confirm_result is not None:
                    return self._confirm_result
                if self._stop_flag:
                    return False
                time.sleep(0.05)
            return False  # timeout → cancel

        try:
            # ── Pipeline (all 10 steps handled inside) ───────────────
            pipe = core.AutoPipeline(
                self.session,
                spoof_lat=lat or None, spoof_lon=lon or None,
                manual_school=manual,
                on_step=on_step,
                on_log=on_log,
                on_sub=on_sub,
                stop=lambda: self._stop_flag,
                ask_use_existing=ask_use_existing,
                cam_filter=cam_filter,
                proof_type=proof_type,
                on_tfa_done=on_tfa_done,
                ask_confirm_submit=ask_confirm_submit,
            )
            pipe.run()
            self._js("onAutoDone()")

        except core.SubmitCancelledError:
            on_log("⊘ Submit dibatalkan oleh pengguna.", "warn")
            self._js("onAutoDone()")
        except core.AccountNotEligibleError:
            on_log("", "")
            on_log("━" * 45, "err")
            on_log(t("pipeline_not_eligible_short"), "err")
            on_log("━" * 45, "err")
            for line in t("pipeline_not_eligible").split("\n"):
                on_log(line.strip(), "err")
            on_log("", "")
            self._js("onAutoDone()")
        except Exception as e:
            on_log(f"\u2718 ERROR: {e}", "err")
            self._js("onAutoDone()")

    def answer_existing(self, use_existing):
        """Called from JS to answer the ask_use_existing dialog."""
        self._ask_result = bool(use_existing)
        return self._ok()

    def answer_confirm_submit(self, confirmed):
        """Called from JS to answer the confirm-before-submit dialog."""
        self._confirm_result = bool(confirmed)
        return self._ok()

    # ── 2FA ───────────────────────────────────────────────────────────
    def check_2fa(self):
        if not self.session: return self._err("Not logged in.")
        try:
            enabled = core.check_2fa_status(self.session)
            return self._ok(enabled)
        except Exception as e:
            return self._err(e)

    def setup_2fa(self):
        if not self.session: return self._err("Not logged in.")
        self._stop_flag = False
        threading.Thread(target=self._2fa_worker, daemon=True).start()
        return self._ok("started")

    def _2fa_worker(self):
        def log_msg(msg):
            self._js(f"onTfaLog({json.dumps(msg)})")

        try:
            result = core.setup_2fa(self.session, on_log=log_msg)
            username = self.user_info.get("username", "?")
            # Build clipboard text
            codes = result.get("recovery_codes", [])
            codes_text = "\n".join(codes) if codes else "(not available)"
            clip_text = (
                f"*GitHub Students Dev Pack*\n"
                f"Username: {username}\n"
                f"Password: \n"
                f"F2A: {result['setup_key']}\n"
                f"\nRecovery Codes:\n{codes_text}"
            )
            self._js(f"onTfaDone({json.dumps(result)},{json.dumps(clip_text)})")
        except Exception as e:
            self._js(f"onTfaError({json.dumps(str(e))})")
    # ── Application Status (for monitor polling) ────────────────────────
    def get_app_status(self):
        """Return the latest benefit application status (for live monitor)."""
        if not self.session: return self._err("Not logged in.")
        try:
            apps = core.get_benefits(self.session)
            if not apps:
                return self._ok(None)
            return self._ok(apps[0])
        except Exception as e:
            return self._err(e)

    # ── History ────────────────────────────────────────────────────
    def get_history(self):
        try:
            return self._ok(core.load_history())
        except Exception as e:
            return self._err(e)

    def clear_history(self):
        try:
            core.clear_history()
            return self._ok()
        except Exception as e:
            return self._err(e)
    # ── Benefits ──────────────────────────────────────────────────────
    def get_benefits(self):
        if not self.session: return self._err("Not logged in.")
        try:
            apps = core.get_benefits(self.session)
            return self._ok(apps)
        except Exception as e:
            return self._err(e)

    # ── Settings ──────────────────────────────────────────────────────
    def get_settings(self):
        try:
            return self._ok(core.load_settings())
        except Exception as e:
            return self._err(e)

    def save_settings(self, settings_json):
        try:
            cfg = json.loads(settings_json) if isinstance(settings_json, str) else settings_json
            core.save_settings(cfg)
            return self._ok()
        except Exception as e:
            return self._err(e)

    # ── i18n ──────────────────────────────────────────────────────────
    def get_translations(self, lang=None):
        """Return all UI translations for the given language."""
        try:
            import i18n
            translations = i18n.get_all_translations(lang)
            return self._ok(translations)
        except Exception as e:
            return self._err(e)

    def set_language(self, lang):
        """Set the active language (id or en)."""
        try:
            import i18n
            i18n.set_language(lang)
            return self._ok()
        except Exception as e:
            return self._err(e)

    # ── Logs ──────────────────────────────────────────────────────────
    def get_log(self):
        try:
            return self._ok(core.read_log_file())
        except Exception as e:
            return self._err(e)

    def clear_log(self):
        try:
            core.clear_log_file()
            return self._ok()
        except Exception as e:
            return self._err(e)

    # ── File Upload (Settings) ─────────────────────────────────────
    def upload_school_list(self):
        """Open file dialog, copy selected file to daftar_sekolah.txt."""
        try:
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=('Text files (*.txt)',),
                allow_multiple=False
            )
            if not result:
                return self._ok({"uploaded": False})
            src = result[0] if isinstance(result, (list, tuple)) else result
            import shutil
            shutil.copy2(src, core.SCHOOL_LIST_FILE)
            count = 0
            try:
                schools = core.load_school_list_file()
                count = len(schools)
            except Exception:
                pass
            return self._ok({"uploaded": True, "path": src, "count": count})
        except Exception as e:
            return self._err(e)

    def upload_keywords(self):
        """Open file dialog, copy selected file to keywords.txt."""
        try:
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=('Text files (*.txt)',),
                allow_multiple=False
            )
            if not result:
                return self._ok({"uploaded": False})
            src = result[0] if isinstance(result, (list, tuple)) else result
            import shutil
            shutil.copy2(src, core.KEYWORDS_FILE)
            kws = core.load_keywords()
            return self._ok({"uploaded": True, "path": src, "count": len(kws)})
        except Exception as e:
            return self._err(e)

    def get_file_info(self):
        """Return info about current daftar_sekolah.txt and keywords.txt."""
        try:
            school_count = 0
            school_exists = core.school_list_file_exists()
            if school_exists:
                school_count = len(core.load_school_list_file())
            kw_count = len(core.load_keywords())
            kw_exists = os.path.exists(core.KEYWORDS_FILE)
            return self._ok({
                "school_exists": school_exists,
                "school_count": school_count,
                "kw_exists": kw_exists,
                "kw_count": kw_count,
            })
        except Exception as e:
            return self._err(e)

    # ── Misc ──────────────────────────────────────────────────────────
    def get_default_coords(self):
        return self._ok(core.DEFAULT_COORDS)

    def open_file(self, path):
        try:
            if os.path.exists(path):
                os.startfile(path)
            return self._ok()
        except Exception as e:
            return self._err(e)
