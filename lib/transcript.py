"""Academic transcript image generator — Pillow-based renderer.

Produces a realistic 'Laporan Hasil Studi Mahasiswa' PNG image
that matches the format of Indonesian university transcripts.
School name, faculty, program, student name, etc. are customised
based on the selected school.
"""
import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .config import BASE_DIR, PHOTOS_DIR, load_settings, logger


# ── Font Helpers ──────────────────────────────────────────────────────────
_FONTS_DIR = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")

def _font(name, size):
    """Try loading a TrueType font, fall back to default."""
    for candidate in (
        os.path.join(_FONTS_DIR, name),
        os.path.join("/usr/share/fonts/truetype/dejavu", name),
        name,
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


# ── University Data Pool ──────────────────────────────────────────────────
# Each entry maps a keyword pattern to faculty / program / course data
# so we can match the selected school and produce realistic content.

_UNIVERSITY_PROFILES = [
    {
        "keywords": ["raden fatah", "uin", "islam negeri"],
        "ministry": "KEMENTERIAN AGAMA REPUBLIK INDONESIA",
        "full_name": "UNIVERSITAS ISLAM NEGERI RADEN FATAH PALEMBANG",
        "faculty": "FAKULTAS SAINS DAN TEKNOLOGI",
        "program": "S1 Sistem Informasi",
        "address": "Jln Prof. KH Zainal Abidin Fikri KM 3,5 Telp. (0711) 353347, Fax. (0711) 354668",
        "website": "http://radenfatah.ac.id",
        "email": "saintek@radenfatah.ac.id",
        "dean": "Dr. Delima Engga Maretha, M.Kes.,AIFO",
        "nip": "198203032011012010",
        "course_prefix": "SIN",
    },
    {
        "keywords": ["sriwijaya", "unsri"],
        "ministry": "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET DAN TEKNOLOGI",
        "full_name": "UNIVERSITAS SRIWIJAYA",
        "faculty": "FAKULTAS ILMU KOMPUTER",
        "program": "S1 Teknik Informatika",
        "address": "Jl. Srijaya Negara, Bukit Besar, Palembang, 30139",
        "website": "http://unsri.ac.id",
        "email": "fasilkom@unsri.ac.id",
        "dean": "Dr. Endang Lestari, M.T.",
        "nip": "197805152006042001",
        "course_prefix": "TIF",
    },
    {
        "keywords": ["bina darma"],
        "ministry": "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET DAN TEKNOLOGI",
        "full_name": "UNIVERSITAS BINA DARMA PALEMBANG",
        "faculty": "FAKULTAS ILMU KOMPUTER",
        "program": "S1 Teknik Informatika",
        "address": "Jl. Jenderal Ahmad Yani No.3, Palembang, 30264",
        "website": "http://binadarma.ac.id",
        "email": "info@binadarma.ac.id",
        "dean": "Dr. Sunda Ariana, M.Pd., M.M.",
        "nip": "196802152000032001",
        "course_prefix": "TIF",
    },
    {
        "keywords": ["indo global mandiri", "igm"],
        "ministry": "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET DAN TEKNOLOGI",
        "full_name": "UNIVERSITAS INDO GLOBAL MANDIRI",
        "faculty": "FAKULTAS ILMU KOMPUTER",
        "program": "S1 Sistem Informasi",
        "address": "Jl. Jenderal Sudirman No.629, Palembang, 30129",
        "website": "http://uigm.ac.id",
        "email": "info@uigm.ac.id",
        "dean": "Dr. Muhamad Akbar, M.IT.",
        "nip": "197607182008011011",
        "course_prefix": "SIF",
    },
    {
        "keywords": ["muhammadiyah palembang"],
        "ministry": "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET DAN TEKNOLOGI",
        "full_name": "UNIVERSITAS MUHAMMADIYAH PALEMBANG",
        "faculty": "FAKULTAS TEKNIK",
        "program": "S1 Teknik Informatika",
        "address": "Jl. Jenderal Ahmad Yani 13 Ulu, Palembang, 30263",
        "website": "http://um-palembang.ac.id",
        "email": "info@um-palembang.ac.id",
        "dean": "Dr. Abid Djazuli, S.E., M.M.",
        "nip": "197106151999031002",
        "course_prefix": "TIF",
    },
    {
        "keywords": ["prabumulih"],
        "ministry": "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET DAN TEKNOLOGI",
        "full_name": "UNIVERSITAS PRABUMULIH",
        "faculty": "FAKULTAS TEKNIK",
        "program": "S1 Teknik Informatika",
        "address": "Jl. Jend. Sudirman No.KM 32, Prabumulih, Sumatera Selatan 31121",
        "website": "http://umpri.ac.id",
        "email": "info@umpri.ac.id",
        "dean": "Dr. Ir. Ahmad Bastari, M.T.",
        "nip": "197809122006041005",
        "course_prefix": "TIF",
    },
]

# Generic fallback for unmatched schools
_GENERIC_PROFILE = {
    "ministry": "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET DAN TEKNOLOGI",
    "faculty": "FAKULTAS ILMU KOMPUTER",
    "program": "S1 Sistem Informasi",
    "address": "",
    "website": "",
    "email": "",
    "dean": "",
    "nip": "",
    "course_prefix": "MKU",
}

# ── Course Pool ───────────────────────────────────────────────────────────
_COURSES_POOL = [
    # (code_suffix, name, sks)
    ("3032", "ALJABAR LINIER", 2),
    ("3054", "STATISTIKA TERAPAN", 4),
    ("3084", "PEMROGRAMAN BERORIENTASI OBYEK", 4),
    ("3094", "PERANCANGAN DAN PEMROGRAMAN WEB", 4),
    ("3154", "JARINGAN DAN KOMUNIKASI DATA", 4),
    ("3162", "MANAJEMEN PROSES BISNIS", 2),
    ("3362", "BASIS DATA LANJUT", 2),
    ("1012", "PENDIDIKAN AGAMA", 2),
    ("1022", "BAHASA INGGRIS", 2),
    ("2034", "ALGORITMA DAN PEMROGRAMAN", 4),
    ("2044", "STRUKTUR DATA", 4),
    ("2052", "KALKULUS I", 2),
    ("2062", "MATEMATIKA DISKRIT", 2),
    ("2074", "SISTEM OPERASI", 4),
    ("2082", "PENGANTAR TEKNOLOGI INFORMASI", 2),
    ("3104", "REKAYASA PERANGKAT LUNAK", 4),
    ("3112", "INTERAKSI MANUSIA DAN KOMPUTER", 2),
    ("3124", "KECERDASAN BUATAN", 4),
    ("3132", "ETIKA PROFESI", 2),
    ("3144", "PEMROGRAMAN MOBILE", 4),
    ("3174", "KEAMANAN SISTEM INFORMASI", 4),
    ("3182", "DATA MINING", 2),
    ("3194", "CLOUD COMPUTING", 4),
    ("3202", "MANAJEMEN PROYEK TI", 2),
    ("3214", "SISTEM TERDISTRIBUSI", 4),
]

_GRADES =  ["A",  "A",  "A",  "B",  "B",  "B",  "B",  "C",  "C"]
_BOBOT  = {"A": 4.00, "B": 3.00, "C": 2.00, "D": 1.00, "E": 0.00}

# ── Dean Name Pool ────────────────────────────────────────────────────────
_DEAN_NAMES = [
    "Dr. Delima Engga Maretha, M.Kes.,AIFO",
    "Prof. Dr. Ahmad Syarifuddin, M.Pd.",
    "Dr. Endang Lestari, M.T.",
    "Dr. Ir. Muhammad Hasan, M.Kom.",
    "Dr. Siti Nurjanah, M.Si.",
    "Prof. Dr. Bambang Suryadi, M.T.",
    "Dr. Rina Octaviana, S.Kom., M.T.I.",
    "Dr. Hendra Kurniawan, M.Kom.",
    "Dr. Yuli Anggraini, M.Pd.",
    "Prof. Dr. Ir. Agus Prasetyo, M.Eng.",
]

_NIP_POOL = [
    "198203032011012010",
    "197605142003121001",
    "197805152006042001",
    "198001032005011003",
    "197502282001122001",
    "196908152000031002",
    "198107242008012015",
    "197311162000121001",
    "198504012010122004",
    "197009301998031003",
]


def _match_profile(school_name: str) -> dict:
    """Find the best university profile for the given school name."""
    lower = school_name.lower()
    for p in _UNIVERSITY_PROFILES:
        if any(kw in lower for kw in p["keywords"]):
            return p
    # Build a generic profile from the school name
    profile = dict(_GENERIC_PROFILE)
    profile["full_name"] = school_name.upper()
    profile["dean"] = random.choice(_DEAN_NAMES)
    profile["nip"] = random.choice(_NIP_POOL)
    return profile


def _generate_courses(prefix: str, count: int = 7):
    """Generate a random set of courses with grades."""
    chosen = random.sample(_COURSES_POOL, min(count, len(_COURSES_POOL)))
    rows = []
    for i, (suffix, name, sks) in enumerate(chosen, 1):
        code = f"{prefix}{suffix}"
        grade = random.choice(_GRADES)
        bobot = _BOBOT[grade]
        bxk = bobot * sks
        rows.append({
            "no": str(i),
            "code": code,
            "name": name,
            "sks": str(sks),
            "grade": grade,
            "bobot": f"{bobot:.2f}",
            "bxk": f"{bxk:.2f}",
        })
    return rows


def _generate_nim(year: int = None) -> str:
    """Generate a realistic NIM (Nomor Induk Mahasiswa)."""
    if not year:
        year = datetime.now().year - random.randint(0, 2)
    yy = str(year)[-2:]
    digits = "".join(random.choices(string.digits, k=9))
    return f"{yy}{digits}"


# ── Main Generator ────────────────────────────────────────────────────────

def generate_transcript(name: str, school_name: str,
                        nim: str = None,
                        semester: str = None,
                        logo_path: str = None) -> str:
    """Generate an academic transcript PNG image.

    Parameters
    ----------
    name        : Student's full name.
    school_name : Name of the school/university.
    nim         : Student ID number (auto-generated if None).
    semester    : e.g. "Semester Ganjil 2025/2026" (auto if None).
    logo_path   : Path to the school logo image (auto-resolved if None).

    Returns
    -------
    str : Path to the generated PNG file.
    """
    profile = _match_profile(school_name)
    if not nim:
        nim = _generate_nim()

    now = datetime.now()
    if not semester:
        if now.month <= 6:
            semester = f"Semester Genap {now.year - 1}/{now.year}"
        else:
            semester = f"Semester Ganjil {now.year}/{now.year + 1}"

    courses = _generate_courses(profile.get("course_prefix", "MKU"), count=7)

    # Compute totals
    total_sks = sum(int(c["sks"]) for c in courses)
    total_bxk = sum(float(c["bxk"]) for c in courses)
    ips = total_bxk / total_sks if total_sks else 0
    # IPK slightly different from IPS for realism
    ipk = round(ips + random.uniform(-0.15, 0.20), 2)
    ipk = max(2.00, min(4.00, ipk))
    total_sks_lulus = total_sks + random.randint(14, 36)
    max_sks_next = 22 if ips >= 2.50 else 20

    date_str = now.strftime("%-d %b %Y") if os.name != "nt" else now.strftime("%d %b %Y").lstrip("0")

    # ── Canvas Setup ──────────────────────────────────────────────────
    W, H = 900, 1050
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # Fonts
    f_title = _font("timesbd.ttf", 16)
    f_header = _font("timesbd.ttf", 13)
    f_small = _font("times.ttf", 11)
    f_body = _font("times.ttf", 12)
    f_body_bold = _font("timesbd.ttf", 12)
    f_table = _font("times.ttf", 11)
    f_table_bold = _font("timesbd.ttf", 11)

    # Colours
    BLACK = (0, 0, 0)
    DARK = (30, 30, 30)
    GREY = (80, 80, 80)
    HEADER_GREEN = (0, 100, 50)

    y = 30  # current y cursor

    # ── Logo placeholder (left side) ──────────────────────────────────
    # Try: 1) provided logo_path, 2) template logo fallback
    actual_logo = logo_path
    if not actual_logo or not os.path.isfile(actual_logo):
        actual_logo = os.path.join(BASE_DIR, "_template_logo.png")
    logo_x, logo_y = 50, y
    logo_size = 70
    if os.path.isfile(actual_logo):
        try:
            logo = Image.open(actual_logo).convert("RGBA")
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            img.paste(logo, (logo_x, logo_y), logo)
        except Exception:
            # Draw placeholder circle
            draw.ellipse([logo_x, logo_y, logo_x + logo_size, logo_y + logo_size],
                         outline=HEADER_GREEN, width=2)
    else:
        draw.ellipse([logo_x, logo_y, logo_x + logo_size, logo_y + logo_size],
                     outline=HEADER_GREEN, width=2)
        draw.text((logo_x + 15, logo_y + 25), "LOGO", fill=GREY, font=f_small)

    # ── Header Text ───────────────────────────────────────────────────
    header_x = 140
    ministry = profile.get("ministry", "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET DAN TEKNOLOGI")
    uni_name = profile.get("full_name", school_name.upper())
    faculty = profile.get("faculty", "FAKULTAS ILMU KOMPUTER")
    address = profile.get("address", "")
    website = profile.get("website", "")
    email = profile.get("email", "")

    draw.text((header_x, y), ministry, fill=BLACK, font=f_header)
    y += 18
    draw.text((header_x, y), uni_name, fill=HEADER_GREEN, font=f_title)
    y += 22
    draw.text((header_x, y), faculty, fill=BLACK, font=f_header)
    y += 20
    if address:
        draw.text((header_x, y), address, fill=GREY, font=f_small)
        y += 16
    if website or email:
        we_line = ""
        if website:
            we_line += f"Website: {website}"
        if email:
            if we_line:
                we_line += " | "
            we_line += f"Email: {email}"
        draw.text((header_x, y), we_line, fill=GREY, font=f_small)
        y += 16

    # ── Separator line ────────────────────────────────────────────────
    y += 8
    draw.line([(40, y), (W - 40, y)], fill=BLACK, width=2)
    y += 3
    draw.line([(40, y), (W - 40, y)], fill=BLACK, width=1)
    y += 15

    # ── Title ─────────────────────────────────────────────────────────
    title = "Laporan Hasil Studi Mahasiswa"
    bbox = draw.textbbox((0, 0), title, font=f_title)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), title, fill=BLACK, font=f_title)
    y += 30

    # ── Student Info Table ────────────────────────────────────────────
    info_left_x = 60
    info_right_x = 480
    program = profile.get("program", "S1 Sistem Informasi")

    draw.text((info_left_x, y), "Nama", fill=BLACK, font=f_body)
    draw.text((info_left_x + 120, y), f":   {name.upper()}", fill=BLACK, font=f_body_bold)
    draw.text((info_right_x, y), "Tahun Akademik", fill=BLACK, font=f_body)
    draw.text((info_right_x + 140, y), f":   {semester}", fill=BLACK, font=f_body)
    y += 20

    draw.text((info_left_x, y), "NIM", fill=BLACK, font=f_body)
    draw.text((info_left_x + 120, y), f":   {nim}", fill=BLACK, font=f_body_bold)
    draw.text((info_right_x, y), "Program Studi", fill=BLACK, font=f_body)
    draw.text((info_right_x + 140, y), f":   {program}", fill=BLACK, font=f_body)
    y += 30

    # ── Course Table ──────────────────────────────────────────────────
    col_x = [60, 90, 170, 490, 560, 620, 690, 760]
    col_headers = ["No", "Kode MK", "Mata Kuliah", "SKS", "Nilai", "Bobot", "BxK"]
    row_h = 22
    table_top = y

    # Header row background
    draw.rectangle([col_x[0] - 5, y - 2, col_x[-1] + 50, y + row_h - 2],
                   fill=(230, 240, 230))

    for ci, header in enumerate(col_headers):
        draw.text((col_x[ci], y), header, fill=BLACK, font=f_table_bold)
    y += row_h

    # Draw header separator
    draw.line([(col_x[0] - 5, y - 2), (col_x[-1] + 50, y - 2)], fill=BLACK, width=1)

    # Course rows
    for c in courses:
        vals = [c["no"], c["code"], c["name"], c["sks"], c["grade"], c["bobot"], c["bxk"]]
        for ci, val in enumerate(vals):
            draw.text((col_x[ci], y), val, fill=DARK, font=f_table)
        y += row_h

    # Totals row
    draw.line([(col_x[0] - 5, y - 2), (col_x[-1] + 50, y - 2)], fill=BLACK, width=1)
    draw.text((col_x[0], y), "Jumlah :", fill=BLACK, font=f_table_bold)
    draw.text((col_x[3], y), str(total_sks), fill=BLACK, font=f_table_bold)
    draw.text((col_x[6], y), f"{total_bxk:.2f}", fill=BLACK, font=f_table_bold)
    y += row_h

    # Table borders
    draw.line([(col_x[0] - 5, table_top - 2), (col_x[-1] + 50, table_top - 2)], fill=BLACK, width=1)
    draw.line([(col_x[0] - 5, y - 2), (col_x[-1] + 50, y - 2)], fill=BLACK, width=1)

    y += 25

    # ── Summary Section ───────────────────────────────────────────────
    sum_x = 60
    sign_x = 560

    draw.text((sum_x, y), "Index Prestasi Semester", fill=BLACK, font=f_body)
    draw.text((sum_x + 280, y), f":   {ips:.2f}", fill=BLACK, font=f_body_bold)
    # Date + city on the right
    city = "Palembang"
    if profile.get("address"):
        for c in ["Palembang", "Jakarta", "Bandung", "Surabaya", "Yogyakarta",
                   "Semarang", "Malang", "Medan", "Makassar", "Denpasar"]:
            if c.lower() in profile["address"].lower():
                city = c
                break
    draw.text((sign_x, y), f"{city}, {date_str}", fill=BLACK, font=f_body)
    y += 20

    draw.text((sum_x, y), "Index Prestasi Kumulatif", fill=BLACK, font=f_body)
    draw.text((sum_x + 280, y), f":   {ipk:.2f}", fill=BLACK, font=f_body_bold)
    draw.text((sign_x, y), "Mengetahui,", fill=BLACK, font=f_body)
    y += 20

    draw.text((sum_x, y), "Total SKS Lulus", fill=BLACK, font=f_body)
    draw.text((sum_x + 280, y), f":   {total_sks_lulus}", fill=BLACK, font=f_body_bold)
    y += 20

    draw.text((sum_x, y), "Total SKS Perolehan", fill=BLACK, font=f_body)
    draw.text((sum_x + 280, y), f":   {total_sks}", fill=BLACK, font=f_body_bold)
    y += 20

    draw.text((sum_x, y), "Max SKS Sem. Depan", fill=BLACK, font=f_body)
    draw.text((sum_x + 280, y), f":   {max_sks_next}", fill=BLACK, font=f_body_bold)
    y += 40

    # ── Dean Signature ────────────────────────────────────────────────
    dean = profile.get("dean") or random.choice(_DEAN_NAMES)
    nip = profile.get("nip") or random.choice(_NIP_POOL)

    draw.text((sign_x, y), dean, fill=BLACK, font=f_body_bold)
    y += 18
    draw.text((sign_x, y), f"NIP. {nip}", fill=GREY, font=f_small)

    # ── Save ──────────────────────────────────────────────────────────
    out_dir = os.path.join(BASE_DIR, "outputs", "transcripts")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "Transcript_Academic.png")
    img.save(out, "PNG")
    logger.info("Transcript generated: %s (%dx%d)", out, W, H)
    return out
