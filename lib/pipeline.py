"""AutoPipeline — 10-step automation orchestrator."""
import os
import random
import time
from typing import Callable, Dict, List, Optional

from .config import (
    BASE_DIR, DEFAULT_COORDS, DEFAULT_DOCUMENT_LABEL,
    SCHOOL_SEARCH_URL, load_settings, generate_indo_name, logger,
    generate_student_bio, generate_repo_name, generate_repo_description,
    INDO_CITIES, add_history_entry,
)
from .auth import get_username_from_cookies
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
    1. School selection
    2. Select school
    3. Resolve name
    4. Update profile
    5. Update bio & location
    6. Create repository
    7. Address & coordinates
    8. Billing info
    9. Generate Student ID
    10. Submit application

    Parameters
    ----------
    session : requests.Session
    spoof_lat, spoof_lon : str
    manual_school : dict | None  — skip search & use this school directly.
    on_step  : callable(step_no, label) | None
    on_log   : callable(msg, tag) | None
    on_sub   : callable(msg) | None
    stop     : callable() -> bool | None
    ask_use_existing : callable(count) -> bool | None
    """

    def __init__(self, session, *, spoof_lat=None, spoof_lon=None,
                 manual_school=None, on_step=None, on_log=None,
                 on_sub=None, stop=None, ask_use_existing=None,
                 cam_filter=None):
        self.s = session
        self.lat = spoof_lat or DEFAULT_COORDS["lat"]
        self.lon = spoof_lon or DEFAULT_COORDS["lon"]
        # Track if user explicitly provided coordinates (for spoofing)
        self._user_coords = bool(spoof_lat and spoof_lon)
        self.manual_school = manual_school
        # cam_filter: None=all, True=cam-only, False=upload-only
        self.cam_filter = cam_filter
        self._step = on_step or (lambda n, t: None)
        self._log = on_log or (lambda m, t="": None)
        self._sub = on_sub or (lambda m: None)
        self._stop = stop or (lambda: False)
        self._ask = ask_use_existing

    def _stopped(self):
        return self._stop()

    def run(self):
        qualified = self._s1_schools()
        if not qualified:
            return
        chosen = self._s2_select(qualified)
        fname, lname, full_name, src = self._s3_name()
        if self._stopped():
            return
        self._s4_profile(fname, lname, full_name, src)
        self._s5_bio_location()
        self._s6_create_repo()
        addr, slat, slon = self._s7_address(chosen["name"])
        self._s8_billing(fname, lname, addr)
        id_path = self._s9_id(full_name, chosen["name"])
        self._s10_submit(chosen, slat, slon, id_path)
        self._post(chosen["name"], full_name, addr, slat, slon)

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
