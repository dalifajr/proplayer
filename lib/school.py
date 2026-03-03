"""School search, filtering, geocoding, and proximity sorting."""
import math
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, List, Tuple

import requests

from .config import (
    BASE_DIR, SCHOOL_LIST_FILE, SCHOOL_SEARCH_URL,
    INDO_CITIES, _UA_POOL, load_keywords, logger,
)
from .htmlparse import _tag_attrs


# ── School Parsing ────────────────────────────────────────────────────────
def parse_schools(t):
    schools = []
    for m in re.finditer(
            r'<div[^>]+class="[^"]*js-school-autocomplete-result-selection[^"]*"[^>]*>', t, re.I):
        a = _tag_attrs(m.group(0))
        schools.append({
            "id": a.get("data-selected-school-id", a.get("data-school-id", "")),
            "name": a.get("data-school-name", a.get("data-autocomplete-value", "")),
            "camera_required": a.get("data-camera-required", ""),
            "email_domains": a.get("data-email-domains", "[]"),
            "too_far": a.get("data-user-too-far-from-school", "true"),
            "override_dist": a.get("data-override-distance-limit", "false"),
        })
    return schools


def school_qualifies(s):
    """A school qualifies if:
    1. User is near (too_far='false') OR distance override is active
    2. Email domains are empty or all DENYLISTED"""
    if s.get("too_far", "true") == "true":
        return False
    domains = s.get("email_domains", "")
    if domains == "[]":
        return True
    if "ALLOWLISTED" in domains:
        return False
    if "DENYLISTED" in domains:
        return True
    return False


# ── Haversine Distance ────────────────────────────────────────────────────
def _haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Nominatim Rate Limiter ────────────────────────────────────────────────
_nominatim_lock = Lock()
_nominatim_last_call = 0.0


def _nominatim_throttle():
    """Ensure at least 1.1 seconds between Nominatim requests."""
    global _nominatim_last_call
    with _nominatim_lock:
        now = time.monotonic()
        elapsed = now - _nominatim_last_call
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        _nominatim_last_call = time.monotonic()


def geocode(name):
    _nominatim_throttle()
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": name, "format": "json", "limit": 1},
                         headers={"User-Agent": random.choice(_UA_POOL)}, timeout=15)
        d = r.json()
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"])
    except Exception:
        pass
    return None, None


def get_school_address(name):
    _nominatim_throttle()
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": name, "format": "json", "limit": 1,
                                 "addressdetails": "1"},
                         headers={"User-Agent": random.choice(_UA_POOL)}, timeout=15)
        d = r.json()
        if d and "address" in d[0]:
            a = d[0]["address"]
            road = a.get("road", a.get("pedestrian", a.get("suburb", "")))
            city = a.get("city", a.get("town", a.get("county", a.get("village", ""))))
            return {
                "address": f"{road}, {a.get('suburb', '')}".strip(", "),
                "city": city, "region": a.get("state", ""),
                "postal_code": a.get("postcode", ""),
                "country_code": a.get("country_code", "id").upper(),
                "display": d[0].get("display_name", ""),
            }
    except Exception:
        pass
    return {}


# ── Proximity Sorting ────────────────────────────────────────────────────
def sort_schools_by_proximity(schools, user_lat, user_lon):
    """Sort schools by proximity using parallel geocoding."""

    def _geocode_school(school):
        if school.get("_lat") and school.get("_lon"):
            dist = _haversine(user_lat, user_lon, school["_lat"], school["_lon"])
            return dist, school
        try:
            slat, slon = geocode(school["name"])
            if slat and slon:
                school["_lat"], school["_lon"] = slat, slon
                dist = _haversine(user_lat, user_lon, slat, slon)
                return dist, school
        except Exception:
            pass
        return 99999, school

    already = [(s, _haversine(user_lat, user_lon, s["_lat"], s["_lon"]))
               for s in schools if s.get("_lat") and s.get("_lon")]
    needs = [s for s in schools if not (s.get("_lat") and s.get("_lon"))]

    scored = [(d, s) for s, d in already]

    if needs:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_geocode_school, s): s for s in needs}
            for future in as_completed(futures):
                try:
                    dist, school = future.result(timeout=20)
                    scored.append((dist, school))
                except Exception:
                    scored.append((99999, futures[future]))

    scored.sort(key=lambda x: x[0])
    return [s for _, s in scored]


# ── Search ────────────────────────────────────────────────────────────────
def search_schools(session, queries, on_progress=None, stop_flag=None):
    all_found = {}
    total = len(queries)
    for i, q in enumerate(queries):
        if stop_flag and stop_flag():
            break
        if on_progress:
            on_progress(i + 1, total, q)
        try:
            r = session.get(SCHOOL_SEARCH_URL, params={"q": q}, timeout=20)
            r.raise_for_status()
            for sc in parse_schools(r.text):
                if sc.get("id") and sc["id"] not in all_found:
                    all_found[sc["id"]] = sc
            time.sleep(0.4)
        except Exception:
            pass
    all_list = list(all_found.values())
    qualified = [s for s in all_list if school_qualifies(s)]
    non_qual = [s for s in all_list if not school_qualifies(s)]
    return all_list, qualified, non_qual


def get_all_queries():
    return list(INDO_CITIES) + load_keywords()


# ── File Storage ──────────────────────────────────────────────────────────
def save_school_list(qualified, non_qual):
    lines = ["=== MEMENUHI SYARAT ==="]
    for i, s in enumerate(qualified):
        cam = s.get('camera_required', 'false')
        far = s.get('too_far', 'false')
        lines.append(f"{i + 1}. {s['name']} (ID: {s['id']}, cam:{cam}, far:{far})")
    lines.append(f"\n=== TIDAK MEMENUHI ({len(non_qual)}) ===")
    for i, s in enumerate(non_qual[:200]):
        lines.append(f"{i + 1}. {s['name']} (cam:{s.get('camera_required')}, "
                     f"far:{s.get('too_far', '?')}, "
                     f"email:{s.get('email_domains')})")
    with open(SCHOOL_LIST_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def load_school_list_file() -> List[Dict[str, str]]:
    """Load qualifying schools from daftar_sekolah.txt."""
    if not os.path.exists(SCHOOL_LIST_FILE):
        return []
    schools = []
    try:
        with open(SCHOOL_LIST_FILE, "r", encoding="utf-8") as f:
            in_qualified = False
            for line in f:
                line = line.strip()
                if "MEMENUHI SYARAT" in line:
                    in_qualified = True
                    continue
                if "TIDAK MEMENUHI" in line:
                    in_qualified = False
                    continue
                if in_qualified and line and line[0].isdigit():
                    m = re.match(
                        r'\d+\.\s*(.+?)\s*\(ID:\s*(\d+)'
                        r'(?:,\s*cam:(\w+))?(?:,\s*far:(\w+))?\)', line)
                    if m:
                        cam = m.group(3) or "false"
                        far = m.group(4) or "false"
                        schools.append({
                            "name": m.group(1), "id": m.group(2),
                            "camera_required": cam, "too_far": far,
                            "override_dist": "false", "email_domains": "[]",
                        })
    except (IOError, OSError):
        pass
    return schools


def school_list_file_exists() -> bool:
    return os.path.exists(SCHOOL_LIST_FILE) and os.path.getsize(SCHOOL_LIST_FILE) > 10
