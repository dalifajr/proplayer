"""AutoPipeline — 10-step automation orchestrator."""
import os
import random
import time
from typing import Callable, Dict, List, Optional

from .config import (
    BASE_DIR, DEFAULT_COORDS, DEFAULT_DOCUMENT_LABEL,
    SCHOOL_SEARCH_URL, load_settings, generate_indo_name, logger,
    generate_student_bio, generate_repo_name, generate_repo_description,
    INDO_CITIES, add_history_entry, get_random_default_address,
)
from .auth import get_username_from_cookies, get_profile_details
from .totp import check_2fa_status, setup_2fa
from .school import (
    parse_schools, school_qualifies, sort_schools_by_proximity,
    search_schools, get_all_queries, save_school_list,
    load_school_list_file, school_list_file_exists, geocode, get_school_address,
)
from .github import (
    scrape_profile_form, submit_profile_form,
    scrape_billing_form, submit_billing, submit_edu_app,
    get_benefits, create_repository,
)
from .idcard import generate_student_id


class AutoPipeline:
    """10-step automation pipeline — decoupled from GUI.

    Steps:
    1.  Account check
    2.  Profile name
    3.  Bio & location
    4.  Create repository
    5.  Billing info
    6.  Setup 2FA
    7.  School selection
    8.  Select school
    9.  Generate Student ID
    10. Submit application

    Parameters
    ----------
    session          : requests.Session
    spoof_lat        : str
    spoof_lon        : str
    manual_school    : dict | None  — skip search & use this school directly.
    on_step          : callable(step_no, label) | None
    on_log           : callable(msg, tag) | None
    on_sub           : callable(msg) | None
    stop             : callable() -> bool | None
    ask_use_existing : callable(count) -> bool | None
    cam_filter       : None | True | False
    on_tfa_done      : callable(result_dict, clip_text_str) | None
    """

    def __init__(self, session, *, spoof_lat=None, spoof_lon=None,
                 manual_school=None, on_step=None, on_log=None,
                 on_sub=None, stop=None, ask_use_existing=None,
                 cam_filter=None, on_tfa_done=None, ask_confirm_submit=None):
        self.s = session
        self.lat = spoof_lat or DEFAULT_COORDS["lat"]
        self.lon = spoof_lon or DEFAULT_COORDS["lon"]
        self._user_coords = bool(spoof_lat and spoof_lon)
        self.manual_school = manual_school
        # cam_filter: None=all, True=cam-only, False=upload-only
        self.cam_filter = cam_filter
        self._step = on_step or (lambda n, t: None)
        self._log = on_log or (lambda m, t="": None)
        self._sub = on_sub or (lambda m: None)
        self._stop = stop or (lambda: False)
        self._ask = ask_use_existing
        self._on_tfa_done = on_tfa_done  # callable(result_dict, clip_text_str)
        # callable() -> bool: called before submit. None=auto-proceed
        self._ask_confirm_submit = ask_confirm_submit

    def _stopped(self):
        return self._stop()

    def run(self):
        # 1 — Account check
        fname, lname, full_name = self._s1_account()

        # 2 — Profile name
        fname, lname, full_name = self._s2_name_profile(fname, lname, full_name)
        if self._stopped():
            return

        # 3 — Bio & location
        self._s3_bio()

        # 4 — Create repository
        self._s4_repo()

        # 5 — Billing info (default address; school not known yet)
        self._s5_billing(fname, lname)

        # 6 — Setup 2FA
        self._s6_2fa()
        if self._stopped():
            return

        # 7 — School selection (cam filter applied here)
        qualified = self._s7_schools()
        if not qualified:
            return

        # 8 — Select school
        chosen = self._s8_select(qualified)

        # 9 — Generate Student ID
        id_path = self._s9_id(full_name, chosen["name"])

        # 10 — Submit application (includes address geocoding)
        addr, slat, slon = self._s10_submit(chosen, id_path)
        self._post(chosen["name"], full_name, addr, slat, slon)

    # ── Step 1 — Account check ────────────────────────────────────────────
    def _s1_account(self):
        self._step(1, "Account check")
        fname, lname, full_name = "", "", ""
        try:
            info = get_profile_details(self.s)
            username = info.get("username", "?")
            age_days = info.get("age_days", 0)
            name = info.get("name", "").strip()
            age_tag = "ok" if age_days >= 7 else ("warn" if age_days >= 3 else "err")
            self._log(f"\u2714 @{username} \u00b7 {age_days}d", age_tag)
            if name:
                parts = name.split()
                fname = parts[0]
                lname = " ".join(parts[1:]) if len(parts) > 1 else ""
                full_name = name
        except Exception as e:
            self._log(f"\u26A0 Account check failed: {e}", "warn")
        return fname, lname, full_name

    # ── Step 2 — Profile name ─────────────────────────────────────────────
    def _s2_name_profile(self, fname, lname, full_name):
        self._step(2, "Profile name")
        if self._stopped():
            return fname, lname, full_name
        fn, ln, src = fname, lname, "account"
        try:
            pn = scrape_profile_form(self.s).get("name", "").strip()
            if pn:
                parts = pn.split()
                fn = parts[0]
                ln = " ".join(parts[1:]) if len(parts) > 1 else ""
                src = "profile"
                self._log(f"\u2714 Profile name: {fn} {ln}", "ok")
        except Exception:
            pass
        if not fn:
            fn, ln = generate_indo_name()
            src = "generated"
            self._log(f"\u26A0 Generated name: {fn} {ln}", "warn")
        full = f"{fn} {ln}".strip()
        if src != "profile":
            try:
                submit_profile_form(self.s, {"name": full})
                self._log(f"\u2714 Profile updated: {full}", "ok")
            except Exception as e:
                self._log(f"\u26A0 Profile update failed: {e}", "warn")
        else:
            self._log(f"\u2714 Profile already set: {full}", "ok")
        return fn, ln, full

    # ── Step 3 — Bio & location ───────────────────────────────────────────
    def _s3_bio(self):
        self._step(3, "Bio & Location")
        if self._stopped():
            return
        try:
            bio = generate_student_bio()
            location = random.choice(INDO_CITIES) + ", Indonesia"
            submit_profile_form(self.s, {"bio": bio, "location": location})
            self._log(f"\u2714 Bio: {bio[:50]}...", "ok")
            self._log(f"\u2714 Location: {location}", "ok")
        except Exception as e:
            self._log(f"\u26A0 Bio/Location update failed: {e}", "warn")

    # ── Step 4 — Create repository ────────────────────────────────────────
    def _s4_repo(self):
        self._step(4, "Create Repository")
        if self._stopped():
            return
        try:
            self._sub("Generating repo info...")
            repo_name = generate_repo_name()
            repo_desc = generate_repo_description()
            self._sub(f"Creating: {repo_name}")
            self._log(f"   Repo name: {repo_name}", "info")
            success = create_repository(
                self.s, name=repo_name, description=repo_desc,
                add_readme=True, private=False)
            if success:
                self._log(f"\u2714 Repository created: {repo_name}", "ok")
            else:
                self._log(f"\u26A0 Repository creation skipped (check _debug/ for details)", "warn")
        except Exception as e:
            self._log(f"\u26A0 Repository creation failed: {e}", "warn")

    # ── Step 5 — Billing info ─────────────────────────────────────────────
    def _s5_billing(self, fn, ln):
        self._step(5, "Billing info")
        if self._stopped():
            return
        try:
            eb = scrape_billing_form(self.s)
        except Exception:
            eb = {}
        cfg = load_settings()
        from .config import DEFAULT_ADDRESS
        ai = {
            "address": cfg.get("default_address", DEFAULT_ADDRESS["address"]),
            "city": cfg.get("default_city", DEFAULT_ADDRESS["city"]),
            "region": cfg.get("default_region", DEFAULT_ADDRESS["region"]),
            "postal_code": cfg.get("default_postal", DEFAULT_ADDRESS["postal_code"]),
            "country_code": cfg.get("default_country", DEFAULT_ADDRESS["country_code"]),
        }
        bill = {f"billing_contact[{k}]": v for k, v in [
            ("first_name", fn), ("last_name", ln),
            ("address1", ai.get("address", "")[:80] or eb.get("address1", "")),
            ("address2", eb.get("address2", "")),
            ("city", ai.get("city", "") or eb.get("city", "")),
            ("country_code", ai.get("country_code", "ID") or eb.get("country_code", "")),
            ("region", ai.get("region", "") or eb.get("region", "")),
            ("postal_code", ai.get("postal_code", "") or eb.get("postal_code", "")),
        ]}
        submit_billing(self.s, bill)
        self._log(f"\u2714 Billing submitted ({ai.get('city', 'default')})", "ok")

    # ── Step 6 — Setup 2FA ────────────────────────────────────────────────
    def _s6_2fa(self):
        self._step(6, "Setup 2FA")
        if self._stopped():
            return
        try:
            enabled = check_2fa_status(self.s)
        except Exception:
            enabled = False
        if enabled:
            self._log("\u2714 2FA already active", "ok")
            return
        self._log("\u26A0 2FA not active \u2014 setting up...", "warn")
        try:
            result = setup_2fa(self.s, on_log=lambda m: self._sub(m))
            self._log("\u2714 2FA setup complete", "ok")
            if self._on_tfa_done:
                username = get_username_from_cookies(self.s) or "?"
                codes = result.get("recovery_codes", [])
                codes_text = "\n".join(codes) if codes else "(not available)"
                clip_text = (
                    f"*GitHub Students Dev Pack*\n"
                    f"Username: {username}\n"
                    f"Password: \n"
                    f"F2A: {result['setup_key']}\n"
                    f"\nRecovery Codes:\n{codes_text}"
                )
                self._on_tfa_done(result, clip_text)
        except RuntimeError as e:
            if "already enabled" in str(e).lower():
                self._log("\u2714 2FA already enabled", "ok")
            else:
                self._log(f"\u26A0 2FA setup failed: {e}", "warn")
        except Exception as e:
            self._log(f"\u26A0 2FA setup error: {e}", "warn")

    # ── Step 7 — School selection ─────────────────────────────────────────
    def _s7_schools(self):
        self._step(7, "School selection")
        if self.manual_school:
            self._log(f"\u2714 Using selected: {self.manual_school['name']}", "ok")
            q = self._apply_cam_filter([self.manual_school])
            return q
        use_ex = False
        if school_list_file_exists():
            ex = load_school_list_file()
            if ex and self._ask:
                use_ex = self._ask(len(ex))
        if use_ex:
            q = load_school_list_file()
            self._log(f"\u2714 Loaded {len(q)} schools from file", "ok")
        else:
            self._log("\U0001F50D Searching schools...", "info")
            queries = get_all_queries()
            af = {}
            for i, qr in enumerate(queries):
                if self._stopped():
                    self._log("\u2B1B Stopped.", "warn")
                    return []
                self._sub(f"[{i + 1}/{len(queries)}] {qr}")
                try:
                    r = self.s.get(SCHOOL_SEARCH_URL, params={"q": qr}, timeout=20)
                    r.raise_for_status()
                    for sc in parse_schools(r.text):
                        if sc.get("id") and sc["id"] not in af:
                            af[sc["id"]] = sc
                    time.sleep(0.4)
                except Exception:
                    pass
            q = [sc for sc in af.values() if school_qualifies(sc)]
            nq = [sc for sc in af.values() if not school_qualifies(sc)]
            save_school_list(q, nq)
            cam_true = sum(1 for s in q if s.get('camera_required') != 'false')
            self._log(
                f"\u2714 Found {len(af)} total, {len(q)} qualified (cam-only: {cam_true})",
                "ok")
        if not q:
            self._log("\u2718 No qualifying schools!", "err")
            return []
        if self._stopped():
            return []
        # Apply cam filter
        q = self._apply_cam_filter(q)
        if not q:
            self._log("\u2718 No schools after cam filter!", "err")
            return []
        # Sort by proximity
        try:
            ulat = float(self.lat)
            ulon = float(self.lon)
            self._sub("Sorting schools by proximity...")
            sample = q[:min(30, len(q))]
            q_sorted = sort_schools_by_proximity(sample, ulat, ulon)
            remaining_ids = {s['id'] for s in q_sorted}
            for s in q:
                if s['id'] not in remaining_ids:
                    q_sorted.append(s)
            q = q_sorted
            self._log(f"\u2714 Schools sorted by proximity", "ok")
        except Exception:
            pass
        return q

    # ── Step 8 — Select school ────────────────────────────────────────────
    def _s8_select(self, qualified):
        self._step(8, "Selecting school")
        if self.manual_school:
            c = self.manual_school
            cam = "cam" if c.get('camera_required') != 'false' else "upload"
            self._log(f"\u2714 Picked: {c['name']} (ID: {c.get('id', '')}, {cam})", "ok")
            return c
        top_n = min(5, len(qualified))
        c = random.choice(qualified[:top_n])
        cam = "cam" if c.get('camera_required') != 'false' else "upload"
        self._log(f"\u2714 Auto-pick: {c['name']} (ID: {c.get('id', '')}, {cam})", "ok")
        return c

    # ── Step 9 — Generate Student ID ──────────────────────────────────────
    def _s9_id(self, full_name, school_name):
        self._step(9, "Generating Student ID")
        if self._stopped():
            return ""
        p = generate_student_id(full_name, school_name)
        self._log(f"\u2714 ID Card: {os.path.basename(p)}", "ok")
        return p

    # ── Step 10 — Submit application ──────────────────────────────────────
    def _s10_submit(self, chosen, id_path):
        self._step(10, "Submitting application")
        if self._stopped():
            return {}, self.lat, self.lon
        # Resolve address & geocode from school name
        ai = get_school_address(chosen["name"])
        if ai and ai.get("city"):
            self._log(f"\u2714 Address: {ai.get('display', '')[:70]}", "ok")
        else:
            ai = get_random_default_address()
            self._log(f"\u26A0 Using random default: {ai['city']}", "warn")
        if self._user_coords:
            self._log(f"\U0001F4CD Spoof coords: {self.lat}, {self.lon}", "ok")
            slat, slon = self.lat, self.lon
        else:
            slat, slon = geocode(chosen["name"])
            if slat:
                self._log(f"\u2714 Geocoded: {slat:.4f}, {slon:.4f}", "ok")
                slat, slon = str(slat), str(slon)
            else:
                self._log(f"\u26A0 Geocode failed \u2192 default: {self.lat}, {self.lon}", "warn")
                slat, slon = self.lat, self.lon
        # ── Confirm before submit ────────────────────────────────────
        if self._ask_confirm_submit:
            self._log(f"\u2139 Ready to submit \u2014 School: {chosen['name']}", "info")
            self._log(f"\u2139 Address: {ai.get('city', '')}, {ai.get('region', '')}", "info")
            self._log(f"\u2139 Coords: {slat}, {slon}", "info")
            confirmed = self._ask_confirm_submit(chosen, ai, slat, slon)
            if not confirmed:
                self._log("\u2B1B Submit cancelled by user.", "warn")
                return ai, slat, slon
        camera = chosen.get("camera_required", "false") != "false"
        if camera:
            self._log("\U0001F4F7 Camera school detected \u2192 simulating webcam capture", "info")
        submit_edu_app(self.s, chosen["name"], id_path,
                       DEFAULT_DOCUMENT_LABEL,
                       lat=slat, lon=slon,
                       school_id=chosen.get("id", ""),
                       camera_mode=camera)
        self._log("\u2714 Application submitted!", "ok")
        try:
            if id_path and os.path.isfile(id_path):
                os.remove(id_path)
                self._log(f"\U0001F5D1 ID card deleted: {os.path.basename(id_path)}", "info")
        except Exception:
            pass
        return ai, slat, slon

    # ── Utility ───────────────────────────────────────────────────────────
    def _apply_cam_filter(self, schools):
        """Filter schools by camera_required based on self.cam_filter."""
        if self.cam_filter is None:
            return schools
        if self.cam_filter:
            filtered = [s for s in schools if s.get('camera_required') != 'false']
            label = "cam:true"
        else:
            filtered = [s for s in schools if s.get('camera_required') == 'false']
            label = "cam:false"
        self._log(f"\u2714 Filtered {label}: {len(filtered)}/{len(schools)} schools", "ok")
        return filtered

    def _post(self, school, full_name, ai, slat, slon):
        self._log(f"\n{'=' * 50}", "info")
        self._log(f"  School : {school}", "info")
        self._log(f"  Name   : {full_name}", "info")
        self._log(f"  Coords : {slat}, {slon}", "info")
        self._log(f"  City   : {ai.get('city', '') if isinstance(ai, dict) else ''}", "info")
        self._log(f"{'=' * 50}", "info")
        self._sub("\u23F3 Checking application status...")
        time.sleep(2)
        status_text = "submitted"
        try:
            apps = get_benefits(self.s)
            if apps:
                st = apps[0].get("status", "Unknown")
                status_text = st
                if "approved" in st.lower():
                    self._log(f"\u2705 Status: {st}", "ok")
                elif "pending" in st.lower():
                    self._log(f"\u23F3 Status: {st}", "warn")
                else:
                    self._log(f"\u274C Status: {st}", "err")
                if apps[0].get("expires"):
                    self._log(f"  Expires: {apps[0]['expires']}", "info")
            else:
                self._log("\u26A0 Could not retrieve status", "warn")
        except Exception:
            self._log("\u26A0 Status check failed", "warn")
        self._sub("\u2714 Completed!")
        try:
            username = get_username_from_cookies(self.s) or "?"
            add_history_entry(username, school, full_name, status_text)
        except Exception:
            pass


    def _s1_schools(self):
        self._step(1, "School selection")
        if self.manual_school:
            self._log(f"\u2714 Using selected: {self.manual_school['name']}", "ok")
            return [self.manual_school]
        use_ex = False
        if school_list_file_exists():
            ex = load_school_list_file()
            if ex and self._ask:
                use_ex = self._ask(len(ex))
        if use_ex:
            q = load_school_list_file()
            self._log(f"\u2714 Loaded {len(q)} schools from file", "ok")
        else:
            self._log("\U0001F50D Searching schools...", "info")
            queries = get_all_queries()
            af = {}
            for i, qr in enumerate(queries):
                if self._stopped():
                    self._log("\u2B1B Stopped.", "warn")
                    return []
                self._sub(f"[{i + 1}/{len(queries)}] {qr}")
                try:
                    r = self.s.get(SCHOOL_SEARCH_URL, params={"q": qr}, timeout=20)
                    r.raise_for_status()
                    for sc in parse_schools(r.text):
                        if sc.get("id") and sc["id"] not in af:
                            af[sc["id"]] = sc
                    time.sleep(0.4)
                except Exception:
                    pass
            q = [sc for sc in af.values() if school_qualifies(sc)]
            nq = [sc for sc in af.values() if not school_qualifies(sc)]
            save_school_list(q, nq)
            cam_true = sum(1 for s in q if s.get('camera_required') != 'false')
            self._log(
                f"\u2714 Found {len(af)} total, {len(q)} qualified (cam-only: {cam_true})",
                "ok")
        # ── Apply camera filter ────────────────────────────────────
        q = self._apply_cam_filter(q)
        if not q:
            self._log("\u2718 No qualifying schools!", "err")
            return []
        if self._stopped():
            return []

        try:
            ulat = float(self.lat)
            ulon = float(self.lon)
            self._sub("Sorting schools by proximity...")
            sample = q[:min(30, len(q))]
            q_sorted = sort_schools_by_proximity(sample, ulat, ulon)
            remaining_ids = {s['id'] for s in q_sorted}
            for s in q:
                if s['id'] not in remaining_ids:
                    q_sorted.append(s)
            q = q_sorted
            self._log(f"\u2714 Schools sorted by proximity", "ok")
        except Exception:
            pass
        return q

    def _apply_cam_filter(self, schools):
        """Filter schools by camera_required based on self.cam_filter."""
        if self.cam_filter is None:
            return schools
        if self.cam_filter:
            filtered = [s for s in schools if s.get('camera_required') != 'false']
            label = "cam:true"
        else:
            filtered = [s for s in schools if s.get('camera_required') == 'false']
            label = "cam:false"
        self._log(f"\u2714 Filtered {label}: {len(filtered)}/{len(schools)} schools", "ok")
        return filtered

    def _s2_select(self, qualified):
        self._step(2, "Selecting school")
        if self.manual_school:
            c = self.manual_school
            cam = "cam" if c.get('camera_required') != 'false' else "upload"
            self._log(f"\u2714 Picked: {c['name']} (ID: {c.get('id', '')}, {cam})", "ok")
            return c
        top_n = min(5, len(qualified))
        c = random.choice(qualified[:top_n])
        cam = "cam" if c.get('camera_required') != 'false' else "upload"
        self._log(f"\u2714 Auto-pick: {c['name']} (ID: {c.get('id', '')}, {cam})", "ok")
        return c

    def _s3_name(self):
        self._step(3, "Resolving name")
        if self._stopped():
            return "", "", "", ""
        fn, ln, src = "", "", ""
        try:
            pn = scrape_profile_form(self.s).get("name", "").strip()
        except Exception:
            pn = ""
        if pn:
            parts = pn.split()
            fn = parts[0] if parts else ""
            ln = " ".join(parts[1:]) if len(parts) > 1 else ""
            src = "profile"
            self._log(f"\u2714 Profile name: {fn} {ln}", "ok")
        if not fn:
            fn, ln = generate_indo_name()
            src = "generated"
            self._log(f"\u26A0 Generated name: {fn} {ln}", "warn")
        return fn, ln, f"{fn} {ln}".strip(), src

    def _s4_profile(self, fn, ln, full, src):
        self._step(4, "Updating profile")
        if self._stopped():
            return
        if src != "profile":
            try:
                submit_profile_form(self.s, {"name": full})
                self._log(f"\u2714 Profile updated: {full}", "ok")
            except Exception as e:
                self._log(f"\u26A0 Profile update failed: {e}", "warn")
        else:
            self._log(f"\u2714 Profile already set: {full}", "ok")

    def _s5_bio_location(self):
        self._step(5, "Bio & Location")
        if self._stopped():
            return
        try:
            # Generate random student bio
            bio = generate_student_bio()
            # Pick random Indonesian city for location
            location = random.choice(INDO_CITIES) + ", Indonesia"
            
            # Update profile with bio and location
            submit_profile_form(self.s, {"bio": bio, "location": location})
            self._log(f"\u2714 Bio: {bio[:50]}...", "ok")
            self._log(f"\u2714 Location: {location}", "ok")
        except Exception as e:
            self._log(f"\u26A0 Bio/Location update failed: {e}", "warn")

    def _s6_create_repo(self):
        self._step(6, "Create Repository")
        if self._stopped():
            return
        try:
            self._sub("Generating repo info...")
            repo_name = generate_repo_name()
            repo_desc = generate_repo_description()
            
            self._sub(f"Creating: {repo_name}")
            self._log(f"   Repo name: {repo_name}", "info")
            
            success = create_repository(
                self.s,
                name=repo_name,
                description=repo_desc,
                add_readme=True,
                private=False
            )
            
            if success:
                self._log(f"\u2714 Repository created: {repo_name}", "ok")
            else:
                self._log(f"\u26A0 Repository creation skipped (check _debug/ for details)", "warn")
        except Exception as e:
            import traceback
            self._log(f"\u26A0 Repository creation failed: {e}", "warn")

    def _s7_address(self, school_name):
        self._step(7, "Address & coordinates")
        if self._stopped():
            return {}, self.lat, self.lon
        ai = get_school_address(school_name)
        if ai and ai.get("city"):
            self._log(f"\u2714 Address: {ai.get('display', '')[:70]}", "ok")
        else:
            cfg = load_settings()
            from .config import DEFAULT_ADDRESS
            ai = {
                "address": cfg.get("default_address", DEFAULT_ADDRESS["address"]),
                "city": cfg.get("default_city", DEFAULT_ADDRESS["city"]),
                "region": cfg.get("default_region", DEFAULT_ADDRESS["region"]),
                "postal_code": cfg.get("default_postal", DEFAULT_ADDRESS["postal_code"]),
                "country_code": cfg.get("default_country", DEFAULT_ADDRESS["country_code"]),
            }
            self._log(f"\u26A0 Using default: {ai['city']}", "warn")
        
        # If user explicitly provided spoof coordinates, use them directly
        if self._user_coords:
            self._log(f"\U0001F4CD Spoof coords: {self.lat}, {self.lon}", "ok")
            sl, sn = self.lat, self.lon
        else:
            # Try geocoding the school name
            sl, sn = geocode(school_name)
            if sl:
                self._log(f"\u2714 Geocoded: {sl:.4f}, {sn:.4f}", "ok")
                sl, sn = str(sl), str(sn)
            else:
                self._log(f"\u26A0 Geocode failed \u2192 default: {self.lat}, {self.lon}", "warn")
                sl, sn = self.lat, self.lon
        return ai, sl, sn

    def _s8_billing(self, fn, ln, ai):
        self._step(8, "Setting billing")
        if self._stopped():
            return
        try:
            eb = scrape_billing_form(self.s)
        except Exception:
            eb = {}
        bill = {f"billing_contact[{k}]": v for k, v in [
            ("first_name", fn), ("last_name", ln),
            ("address1", ai.get("address", "")[:80] or eb.get("address1", "")),
            ("address2", eb.get("address2", "")),
            ("city", ai.get("city", "") or eb.get("city", "")),
            ("country_code", ai.get("country_code", "ID") or eb.get("country_code", "")),
            ("region", ai.get("region", "") or eb.get("region", "")),
            ("postal_code", ai.get("postal_code", "") or eb.get("postal_code", "")),
        ]}
        submit_billing(self.s, bill)
        self._log("\u2714 Billing submitted!", "ok")

    def _s9_id(self, full_name, school_name):
        self._step(9, "Generating Student ID")
        if self._stopped():
            return ""
        p = generate_student_id(full_name, school_name)
        self._log(f"\u2714 ID Card: {os.path.basename(p)}", "ok")
        return p

    def _s10_submit(self, chosen, slat, slon, id_path):
        self._step(10, "Submitting application")
        if self._stopped():
            return
        camera = chosen.get("camera_required", "false") != "false"
        if camera:
            self._log("\U0001F4F7 Camera school detected → simulating webcam capture", "info")
        submit_edu_app(self.s, chosen["name"], id_path,
                       DEFAULT_DOCUMENT_LABEL,
                       lat=slat, lon=slon,
                       school_id=chosen.get("id", ""),
                       camera_mode=camera)
        self._log("\u2714 Application submitted!", "ok")
        try:
            if id_path and os.path.isfile(id_path):
                os.remove(id_path)
                self._log(f"\U0001F5D1 ID card deleted: {os.path.basename(id_path)}", "info")
        except Exception:
            pass

    def _post(self, school, full_name, ai, slat, slon):
        self._log(f"\n{'=' * 50}", "info")
        self._log(f"  School : {school}", "info")
        self._log(f"  Name   : {full_name}", "info")
        self._log(f"  Coords : {slat}, {slon}", "info")
        self._log(f"  City   : {ai.get('city', '')}", "info")
        self._log(f"{'=' * 50}", "info")
        self._sub("\u23F3 Checking application status...")
        time.sleep(2)
        status_text = "submitted"
        try:
            apps = get_benefits(self.s)
            if apps:
                st = apps[0].get("status", "Unknown")
                status_text = st
                if "approved" in st.lower():
                    self._log(f"\u2705 Status: {st}", "ok")
                elif "pending" in st.lower():
                    self._log(f"\u23F3 Status: {st}", "warn")
                else:
                    self._log(f"\u274C Status: {st}", "err")
                if apps[0].get("expires"):
                    self._log(f"  Expires: {apps[0]['expires']}", "info")
            else:
                self._log("\u26A0 Could not retrieve status", "warn")
        except Exception:
            self._log("\u26A0 Status check failed", "warn")
        self._sub("\u2714 Completed!")
        # ── Save to submission history ───────────────────────────────────
        try:
            username = get_username_from_cookies(self.s) or "?"
            add_history_entry(username, school, full_name, status_text)
        except Exception:
            pass
