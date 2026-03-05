"""School/university logo fetcher and cache manager.

Downloads logos for qualifying schools and caches them in logos/ directory.
Logos are keyed by school ID for consistent retrieval.
"""
import hashlib
import json
import os
import re
import time
from typing import Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageFont

from .config import BASE_DIR, _UA_POOL, logger

LOGOS_DIR = os.path.join(BASE_DIR, "logos")
_LOGO_INDEX_FILE = os.path.join(LOGOS_DIR, "_index.json")

# ── Known Domain Mappings ─────────────────────────────────────────────────
# Maps school name patterns to known website domains for logo fetching.
_KNOWN_DOMAINS = {
    "raden fatah": "radenfatah.ac.id",
    "sriwijaya": "unsri.ac.id",
    "bina darma": "binadarma.ac.id",
    "indo global mandiri": "uigm.ac.id",
    "muhammadiyah palembang": "um-palembang.ac.id",
    "muhammadiyah university of palembang": "um-palembang.ac.id",
    "pgri university palembang": "univpgri-palembang.ac.id",
    "pgri palembang": "univpgri-palembang.ac.id",
    "tridinanti": "univ-tridinanti.ac.id",
    "stmik mdp": "mdp.ac.id",
    "stie mdp": "mdp.ac.id",
    "palcomtech": "palcomtech.ac.id",
    "poltekkes.*palembang": "poltekkespalembang.ac.id",
    "politeknik pariwisata palembang": "poltekpar-palembang.ac.id",
    "prabumulih university": "universitas-prabumulih.ac.id",
    "universitas prabumulih": "universitas-prabumulih.ac.id",
    "open university": "ut.ac.id",
    "universitas terbuka": "ut.ac.id",
    "amity university": "amity.edu",
    "bengkulu": "unib.ac.id",
    "university of bengkulu": "unib.ac.id",
    "fatmawati soekarno.*bengkulu": "iainbengkulu.ac.id",
    "bandar lampung university": "ubl.ac.id",
    "american public university": "apus.edu",
    "ipeka": "ipeka.sch.id",
    "xaverius": "xaverius.sch.id",
    "kusuma bangsa": "kumbang.sch.id",
    "methodist": "methodist2.sch.id",
    "ignatius global": "ignatiusglobal.sch.id",
}

# ── Logo Source URLs (order of preference) ────────────────────────────────
_LOGO_SOURCES = [
    "https://logo.clearbit.com/{domain}?size=200",
    "https://www.google.com/s2/favicons?domain={domain}&sz=128",
    "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=128",
]


def _ensure_logos_dir():
    os.makedirs(LOGOS_DIR, exist_ok=True)


def _load_index() -> Dict:
    """Load the logo index mapping school_id -> logo filename."""
    if os.path.isfile(_LOGO_INDEX_FILE):
        try:
            with open(_LOGO_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_index(index: Dict):
    _ensure_logos_dir()
    with open(_LOGO_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _domain_from_school(school: Dict) -> Optional[str]:
    """Extract a usable domain from school data."""
    name_lower = school.get("name", "").lower()

    # 1. Check known domain mappings
    for pattern, domain in _KNOWN_DOMAINS.items():
        if re.search(pattern, name_lower):
            return domain

    # 2. Extract from email_domains field
    email_str = school.get("email_domains", "[]")
    if email_str and email_str not in ("[]", "ALLOWLISTED", "DENYLISTED"):
        try:
            domains = json.loads(email_str) if isinstance(email_str, str) else email_str
            if isinstance(domains, list):
                for entry in domains:
                    if isinstance(entry, list) and len(entry) >= 1:
                        d = entry[0]
                        # Prefer non-student domains
                        if not d.startswith("student.") and not d.startswith("mhs."):
                            return d
                # Fallback: any domain
                for entry in domains:
                    if isinstance(entry, list) and len(entry) >= 1:
                        return entry[0]
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _download_logo(domain: str, school_id: str) -> Optional[str]:
    """Try downloading a logo from multiple sources. Returns saved path or None."""
    _ensure_logos_dir()
    headers = {"User-Agent": _UA_POOL[0] if _UA_POOL else "Mozilla/5.0"}

    for url_template in _LOGO_SOURCES:
        url = url_template.format(domain=domain)
        try:
            r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if r.status_code != 200:
                continue
            ct = r.headers.get("Content-Type", "")
            if "image" not in ct and len(r.content) < 100:
                continue
            # Validate it's a real image
            if len(r.content) < 100:
                continue

            ext = "png"
            if "jpeg" in ct or "jpg" in ct:
                ext = "jpg"
            elif "svg" in ct:
                continue  # skip SVG, not embeddable easily
            elif "ico" in ct:
                ext = "ico"

            fname = f"logo_{school_id}.{ext}"
            fpath = os.path.join(LOGOS_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(r.content)

            # Validate with Pillow and convert to PNG if needed
            try:
                with Image.open(fpath) as img:
                    if img.width < 16 or img.height < 16:
                        os.remove(fpath)
                        continue
                    # Convert to PNG for consistency
                    png_fname = f"logo_{school_id}.png"
                    png_path = os.path.join(LOGOS_DIR, png_fname)
                    if fpath != png_path:
                        img_rgba = img.convert("RGBA")
                        img_rgba.save(png_path, "PNG")
                        if fpath != png_path:
                            os.remove(fpath)
                    logger.info("Logo downloaded: %s → %s (%dx%d)",
                                domain, png_fname, img.width, img.height)
                    return png_path
            except Exception:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                continue

        except requests.RequestException:
            continue

    return None


def _generate_placeholder_logo(school_name: str, school_id: str) -> str:
    """Generate a colored placeholder logo with school initials."""
    _ensure_logos_dir()
    # Extract initials (up to 3 chars)
    words = re.findall(r'[A-Z]', school_name.upper())
    if not words:
        words = [school_name[0].upper()] if school_name else ["?"]
    initials = "".join(words[:3])

    # Deterministic color from school_id
    h = int(hashlib.md5(school_id.encode()).hexdigest()[:6], 16)
    r_bg = 40 + (h % 160)
    g_bg = 40 + ((h >> 8) % 160)
    b_bg = 60 + ((h >> 16) % 140)

    size = 200
    img = Image.new("RGBA", (size, size), (r_bg, g_bg, b_bg, 255))
    draw = ImageDraw.Draw(img)

    # Draw circle background
    draw.ellipse([10, 10, size - 10, size - 10], fill=(r_bg, g_bg, b_bg))
    draw.ellipse([14, 14, size - 14, size - 14], fill=(255, 255, 255, 40))

    # Draw initials
    fonts_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    try:
        font = ImageFont.truetype(os.path.join(fonts_dir, "arialbd.ttf"), 60)
    except (IOError, OSError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - 5), initials,
              fill=(255, 255, 255), font=font)

    fname = f"logo_{school_id}.png"
    fpath = os.path.join(LOGOS_DIR, fname)
    img.save(fpath, "PNG")
    return fpath


# ── Public API ────────────────────────────────────────────────────────────

def _is_placeholder_cached(school_id: str) -> bool:
    """Check whether cached logo is marked as placeholder in index."""
    idx = _load_index()
    meta = idx.get(school_id, {})
    return bool(meta.get("placeholder"))


def get_logo_path(school: Dict, real_only: bool = False) -> Optional[str]:
    """Get cached logo path for a school.

    Parameters
    ----------
    real_only : if True, reject cached placeholders.
    """
    school_id = str(school.get("id", ""))
    if not school_id:
        return None
    fpath = os.path.join(LOGOS_DIR, f"logo_{school_id}.png")
    if os.path.isfile(fpath):
        if real_only and _is_placeholder_cached(school_id):
            return None
        return fpath
    return None


def fetch_logo(
    school: Dict,
    on_log=None,
    allow_placeholder: bool = True,
    force_refresh: bool = False,
) -> Optional[str]:
    """Fetch logo for a single school. Downloads if not cached.
    Returns a path, or None when strict mode is enabled and download fails."""
    school_id = str(school.get("id", ""))
    school_name = school.get("name", "Unknown")

    if not school_id:
        return _generate_placeholder_logo(school_name, "0") if allow_placeholder else None

    # Check cache
    cached = get_logo_path(school, real_only=not allow_placeholder)
    if cached and not force_refresh:
        return cached

    # Try download
    domain = _domain_from_school(school)
    if domain:
        if on_log:
            on_log(f"  Fetching logo: {domain}", "info")
        path = _download_logo(domain, school_id)
        if path:
            # Update index
            idx = _load_index()
            idx[school_id] = {"name": school_name, "domain": domain,
                              "file": os.path.basename(path)}
            _save_index(idx)
            return path

    if not allow_placeholder:
        logger.warning("Logo real-only mode: no logo found for %s (ID: %s)", school_name, school_id)
        return None

    # Fallback to placeholder
    logger.info("Logo: generating placeholder for %s (ID: %s)", school_name, school_id)
    path = _generate_placeholder_logo(school_name, school_id)
    idx = _load_index()
    idx[school_id] = {"name": school_name, "domain": domain or "",
                      "file": os.path.basename(path), "placeholder": True}
    _save_index(idx)
    return path


def fetch_logos_bulk(
    schools: List[Dict],
    on_log=None,
    on_sub=None,
    allow_placeholder: bool = True,
    force_refresh: bool = False,
) -> int:
    """Fetch logos for a list of schools (qualifying ones).
    Returns number of logos fetched/cached."""
    count = 0
    total = len(schools)
    for i, school in enumerate(schools):
        if on_sub:
            on_sub(f"[{i+1}/{total}] Logo: {school.get('name', '')[:40]}")
        try:
            path = fetch_logo(
                school,
                on_log=on_log,
                allow_placeholder=allow_placeholder,
                force_refresh=force_refresh,
            )
            if path:
                count += 1
        except Exception as e:
            logger.warning("Logo fetch failed for %s: %s", school.get("name"), e)
        # Small delay to avoid rate limiting
        time.sleep(0.3)
    return count
