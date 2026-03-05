"""Shared configuration, constants, file paths, and settings management."""
import atexit
import json
import logging
import os
import random
import sys
from datetime import datetime
from typing import Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── Logger ────────────────────────────────────────────────────────────────
logger = logging.getLogger("gh_edu")

# When frozen (PyInstaller), use the directory where the .exe lives for writable files.
# sys._MEIPASS is the temp extraction dir (read-only bundled data).
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    _BUNDLE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _BUNDLE_DIR = BASE_DIR

_log_path = os.path.join(BASE_DIR, "gh_edu.log")
_fh = logging.FileHandler(_log_path, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                   datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(_fh)
logger.setLevel(logging.INFO)

# ── URLs ──────────────────────────────────────────────────────────────────
LOGIN_URL = "https://github.com/login"
SESSION_URL = "https://github.com/session"
TWO_FACTOR_URL = "https://github.com/sessions/two-factor"
PROFILE_URL = "https://github.com/settings/profile"
SCHOOL_SEARCH_URL = "https://github.com/settings/education/developer_pack_applications/schools"
DEV_PACK_NEW_URL = "https://github.com/settings/education/developer_pack_applications/new"
PAYMENT_INFO_URL = "https://github.com/settings/billing/payment_information"
CONTACT_UPDATE_URL = "https://github.com/account/contact"
EMAILS_URL = "https://github.com/settings/emails"
BENEFITS_URL = "https://github.com/settings/education/benefits"
SECURITY_URL = "https://github.com/settings/security"
TFA_SETUP_URL = "https://github.com/settings/two_factor_authentication/setup/intro"
TFA_VERIFY_URL = "https://github.com/settings/two_factor_authentication/verify_app"
TFA_ENABLE_URL = "https://github.com/settings/two_factor_authentication"
TFA_RECOVERY_URL = "https://github.com/settings/two_factor_authentication/recovery_codes"

# ── File Paths ────────────────────────────────────────────────────────────
SESSION_FILE = os.path.join(BASE_DIR, "sessions.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
SCHOOL_LIST_FILE = os.path.join(BASE_DIR, "daftar_sekolah.txt")
KEYWORDS_FILE = os.path.join(BASE_DIR, "keywords.txt")
_BUNDLED_KEYWORDS = os.path.join(_BUNDLE_DIR, "keywords.txt")
DEFAULT_DOCUMENT_LABEL = "Dated school ID"
TRANSCRIPT_DOCUMENT_LABEL = "Dated official/unofficial transcript"
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")

# ── Defaults ──────────────────────────────────────────────────────────────
# Large pool of real addresses in Palembang and surrounding areas
_PALEMBANG_ADDRESS_POOL = [
    # ── Palembang Kota ──────────────────────────────────────────────────
    {"address": "Jl. Jenderal Ahmad Yani No.3, 9/10 Ulu, Kec. Seberang Ulu I",        "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30111"},
    {"address": "Jl. Sudirman No.45, Sungai Pangeran, Kec. Ilir Timur I",              "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30127"},
    {"address": "Jl. Kapten Abdul Halim No.10, Lorok Pakjo, Kec. Ilir Barat I",        "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30152"},
    {"address": "Jl. Demang Lebar Daun No.89, Bukit Lama, Kec. Ilir Barat I",          "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30137"},
    {"address": "Jl. Radial No.12, Suka Maju, Kec. Sako",                              "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30163"},
    {"address": "Jl. Basuki Rahmat No.22, Talang Aman, Kec. Kemuning",                 "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30151"},
    {"address": "Jl. Kolonel H. Barlian No.58, Srijaya, Kec. Alang-Alang Lebar",       "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30155"},
    {"address": "Jl. Mayor Ruslan No.15, 20 Ilir D. III, Kec. Ilir Timur I",           "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30126"},
    {"address": "Jl. R. Sukamto No.4, 8 Ilir, Kec. Ilir Timur II",                    "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30114"},
    {"address": "Jl. Veteran No.37, 1 Ulu, Kec. Seberang Ulu I",                       "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30258"},
    {"address": "Jl. Ki Gede Ing Suro No.8, 5 Ilir, Kec. Ilir Timur II",              "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30113"},
    {"address": "Jl. Tasik No.6, Talang Betutu, Kec. Sukarami",                        "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30153"},
    {"address": "Jl. Angkatan 45 No.22, Pahlawan, Kec. Kemuning",                      "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30128"},
    {"address": "Jl. Inspektur Marzuki No.5, Ario Kemuning, Kec. Kemuning",            "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30151"},
    {"address": "Jl. T. Nyak Arief No.65, Kec. Alang-Alang Lebar",                     "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30155"},
    {"address": "Jl. Parameswara No.10, Talang Ratu, Kec. Alang-Alang Lebar",          "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30154"},
    {"address": "Jl. POM IX No.18, Kemas Rindo, Kec. Kertapati",                       "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30259"},
    {"address": "Jl. RE Martadinata No.3, Tanjung Batu, Kec. Plaju",                   "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30268"},
    {"address": "Jl. Jenderal Sudirman No.2710, Kec. Ilir Barat II",                   "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30141"},
    {"address": "Jl. Sei Selayur No.7, Kalidoni, Kec. Kalidoni",                       "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30119"},
    {"address": "Jl. Abdul Rozak No.30, Sako, Kec. Sako",                              "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30163"},
    {"address": "Jl. Perintis Kemerdekaan No.1, 7 Ulu, Kec. Seberang Ulu I",           "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30252"},
    {"address": "Jl. Residen Abdul Rozak No.17, Bukit Besar, Kec. Ilir Barat I",       "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30139"},
    {"address": "Jl. MP Mangkunegara No.9, Suka Bangun, Kec. Sukarami",                "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30153"},
    {"address": "Jl. Letnan Murod No.6, Talang Semut, Kec. Bukit Kecil",               "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30113"},
    {"address": "Jl. Gubernur H. Ahmad Bastari No.12, Jakabaring, Kec. Seberang Ulu II", "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30267"},
    {"address": "Jl. Soekarno Hatta No.8, Lebong Gajah, Kec. Sematang Borang",         "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30164"},
    {"address": "Jl. Pangeran Ratu No.14, 10 Ulu, Kec. Seberang Ulu I",                "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30254"},
    {"address": "Jl. Merdeka No.28, Talang Aman, Kec. Kemuning",                       "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30151"},
    {"address": "Jl. Rajawali No.11, Sungai Buah, Kec. Ilir Timur II",                 "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30115"},
    {"address": "Jl. Ogan No.5, 14 Ulu, Kec. Seberang Ulu II",                         "city": "Palembang", "region": "Sumatera Selatan", "postal_code": "30262"},
    # ── Prabumulih ──────────────────────────────────────────────────────
    {"address": "Jl. Jenderal Sudirman No.17, Gunung Ibul, Kec. Prabumulih Timur",     "city": "Prabumulih",  "region": "Sumatera Selatan", "postal_code": "31111"},
    {"address": "Jl. Lingkar No.9, Muara Dua, Kec. Prabumulih Selatan",                "city": "Prabumulih",  "region": "Sumatera Selatan", "postal_code": "31114"},
    {"address": "Jl. Mayor Ruslan No.5, Sindur, Kec. Prabumulih Barat",               "city": "Prabumulih",  "region": "Sumatera Selatan", "postal_code": "31113"},
    # ── Banyuasin / Palembang Sekitarnya ──────────────────────────────
    {"address": "Jl. Raya Palembang-Betung KM 18, Sukajadi, Kec. Talang Kelapa",       "city": "Banyuasin",   "region": "Sumatera Selatan", "postal_code": "30761"},
    {"address": "Jl. Merdeka No.3, Mariana, Kec. Banyuasin I",                          "city": "Banyuasin",   "region": "Sumatera Selatan", "postal_code": "30751"},
    {"address": "Jl. Palembang-Betung No.35, Pangkalan Balai, Kec. Banyuasin III",     "city": "Banyuasin",   "region": "Sumatera Selatan", "postal_code": "30762"},
    # ── Ogan Ilir ──────────────────────────────────────────────────────
    {"address": "Jl. Lintas Timur Sumatera No.12, Indralaya, Kec. Indralaya",           "city": "Ogan Ilir",   "region": "Sumatera Selatan", "postal_code": "30662"},
    {"address": "Jl. Palembang-Prabumulih KM 32, Tanjung Raja, Kec. Tanjung Raja",      "city": "Ogan Ilir",   "region": "Sumatera Selatan", "postal_code": "30651"},
    # ── Muara Enim ─────────────────────────────────────────────────────
    {"address": "Jl. Sudirman No.100, Muara Enim, Kec. Muara Enim",                     "city": "Muara Enim",  "region": "Sumatera Selatan", "postal_code": "31312"},
    # ── Lahat ──────────────────────────────────────────────────────────
    {"address": "Jl. Mayor Ruslan No.7, Lahat, Kec. Lahat",                             "city": "Lahat",       "region": "Sumatera Selatan", "postal_code": "31411"},
]

def get_random_default_address() -> dict:
    """Return a random address from the Palembang area pool."""
    entry = random.choice(_PALEMBANG_ADDRESS_POOL)
    return {
        "address": entry["address"],
        "city": entry["city"],
        "region": entry["region"],
        "postal_code": entry["postal_code"],
        "country_code": "ID",
    }

# Keep DEFAULT_ADDRESS pointing to first entry for backwards compat
DEFAULT_ADDRESS = dict(_PALEMBANG_ADDRESS_POOL[0], country_code="ID")
DEFAULT_COORDS = {"lat": "-2.999171", "lon": "104.771125"}

# ── User-Agent Pool (dynamic generation) ──────────────────────────────────
def _generate_ua_pool() -> list:
    """Generate a dynamic pool of realistic, up-to-date User-Agent strings.
    Chrome/Edge/Firefox versions are derived from the current date so they never go stale."""
    now = datetime.now()
    _anchor_ver = 132
    _anchor_month = 1
    _anchor_year = 2025
    months_elapsed = max(0, (now.year - _anchor_year) * 12 + (now.month - _anchor_month))

    chrome_major = _anchor_ver + months_elapsed
    prev = max(120, chrome_major - 1)
    prev2 = max(119, chrome_major - 2)
    prev3 = max(118, chrome_major - 3)

    ff_anchor = 134
    ff_major = ff_anchor + months_elapsed
    ff_prev = max(120, ff_major - 1)
    ff_prev2 = max(119, ff_major - 2)

    edge_major = chrome_major
    edge_prev = prev

    safari_minor = 1 + (months_elapsed // 6)
    safari_ver = f"18.{safari_minor}"
    ios_safari_ver = f"18_{safari_minor}"

    android_build_now = f"{chrome_major}.0.0.0"
    android_build_prev = f"{prev}.0.0.0"
    android_build_prev2 = f"{prev2}.0.0.0"

    pool = [
        # ── Desktop: Windows Chrome/Edge/Firefox ─────────────────────
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_major}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_major}.0.0.0 Safari/537.36 Edg/{edge_major}.0.0.0",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ff_major}.0) Gecko/20100101 Firefox/{ff_major}.0",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev}.0.0.0 Safari/537.36 Edg/{edge_prev}.0.0.0",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ff_prev}.0) Gecko/20100101 Firefox/{ff_prev}.0",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev2}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev3}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_major}.0.0.0 Safari/537.36 OPR/{max(95, chrome_major - 14)}.0.0.0",
        # ── Desktop: macOS (Intel + Apple Silicon) ───────────────────
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_major}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Safari/605.1.15",
        f"Mozilla/5.0 (Macintosh; ARM Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_major}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Macintosh; ARM Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Safari/605.1.15",
        f"Mozilla/5.0 (Macintosh; ARM Mac OS X 14_5; rv:{ff_major}.0) Gecko/20100101 Firefox/{ff_major}.0",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev}.0.0.0 Safari/537.36",
        # ── Desktop: Linux ────────────────────────────────────────────
        f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_major}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:{ff_major}.0) Gecko/20100101 Firefox/{ff_major}.0",
        f"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:{ff_prev}.0) Gecko/20100101 Firefox/{ff_prev}.0",
        # ── Smartphone: Android Chrome/Firefox/Edge ──────────────────
        f"Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_now} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 15; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_now} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; SM-A556E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev2} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; CPH2609) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; V2332) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev2} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; 23113RKC6G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; CPH2527) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev2} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; Infinix X6851) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev} Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; TECNO KL7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev2} Mobile Safari/537.36",
        f"Mozilla/5.0 (Android 15; Mobile; rv:{ff_major}.0) Gecko/{ff_major}.0 Firefox/{ff_major}.0",
        f"Mozilla/5.0 (Android 14; Mobile; rv:{ff_prev}.0) Gecko/{ff_prev}.0 Firefox/{ff_prev}.0",
        f"Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_now} Mobile Safari/537.36 EdgA/{edge_major}.0.0.0",
        # ── Smartphone: iPhone/iPad Safari/Chrome/Edge ───────────────
        f"Mozilla/5.0 (iPhone; CPU iPhone OS {ios_safari_ver} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/{chrome_major}.0.0.0 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/{edge_major}.0.0 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.7 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (iPad; CPU OS {ios_safari_ver} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (iPad; CPU OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/{prev}.0.0.0 Mobile/15E148 Safari/604.1",
        # ── Tablet Android ────────────────────────────────────────────
        f"Mozilla/5.0 (Linux; Android 14; SM-X210) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev} Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; Lenovo TB370FU) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev2} Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; Redmi Pad Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{android_build_prev} Safari/537.36",
        # ── Legacy entries for compatibility spread ───────────────────
        f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{prev2}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ff_prev2}.0) Gecko/20100101 Firefox/{ff_prev2}.0",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    ]
    return pool

_UA_POOL = _generate_ua_pool()

# ── Indonesian Names ──────────────────────────────────────────────────────
INDO_CITIES = [
    "Sabang","Banda Aceh","Lhokseumawe","Medan","Padang","Pekanbaru","Jambi",
    "Palembang","Bengkulu","Bandar Lampung","Pangkal Pinang","Tanjung Pinang",
    "Batam","Jakarta","Bandung","Semarang","Yogyakarta","Surabaya","Serang",
    "Denpasar","Mataram","Kupang","Pontianak","Palangkaraya","Banjarmasin",
    "Samarinda","Balikpapan","Tarakan","Manado","Palu","Makassar","Kendari",
    "Gorontalo","Mamuju","Ambon","Ternate","Jayapura","Sorong","Manokwari",
    "Merauke","Malang","Solo","Bogor","Depok","Tangerang","Bekasi","Cirebon",
    "Tasikmalaya","Purwokerto","Tegal","Magelang","Kediri","Jember","Blitar",
    "Probolinggo","Mojokerto","Batu","Madiun","Surakarta","Pekalongan",
]
INDO_FIRST = [
    "Adi","Agus","Ahmad","Aldi","Andi","Angga","Arif","Bagas","Bagus","Bambang",
    "Bima","Budi","Cahya","Dani","Dedi","Dimas","Dwi","Eko","Fajar","Farhan",
    "Fauzan","Galang","Galih","Gilang","Hadi","Hafiz","Hari","Hendra","Ilham","Imam",
    "Indra","Irfan","Ivan","Joko","Kevin","Krisna","Lukman","Maulana","Muhamad","Muhammad",
    "Nanda","Naufal","Nugroho","Omar","Pandu","Putra","Qori","Raden","Radit","Raffi",
    "Rama","Rangga","Reza","Ridho","Rio","Rizki","Rudi","Satria","Sigit","Surya",
    "Taufik","Teguh","Tri","Umar","Wahyu","Wawan","Yandi","Yoga","Yusuf","Zaki",
    "Amelia","Ayu","Bella","Citra","Devi","Dewi","Dian","Ela","Erna",
    "Farah","Fatimah","Fitri","Gita","Hana","Ika","Indah","Intan","Kartika","Laras",
    "Lestari","Linda","Maya","Mega","Melani","Mira","Nadia","Nadya","Nisa","Novi",
    "Nur","Nurul","Putri","Rahma","Ratna","Rina","Rini","Rizka","Sari","Sekar",
    "Sinta","Siti","Sri","Suci","Tika","Tiara","Umi","Vina","Wulan",
    "Yanti","Yuli","Zahra","Zulfa",
]
INDO_LAST = [
    "Pratama","Saputra","Wibowo","Susanto","Hidayat","Nugroho","Kurniawan",
    "Setiawan","Permadi","Handoko","Purnama","Wijaya","Utama","Ramadhan",
    "Hakim","Santoso","Darmawan","Firmansyah","Syahputra","Putra",
    "Aditya","Anggara","Ardiansyah","Budiman","Cahyadi","Cahyono",
    "Gunawan","Hartono","Hermawan","Irawan","Iskandar","Kusumo",
    "Laksono","Mahendra","Maulana","Mulyadi","Nurfadilah","Pangestu",
    "Prasetyo","Prastyo","Purnomo","Raharjo","Rahmadi","Ramadhani",
    "Sanjaya","Setiono","Siagian","Simanjuntak","Sinaga","Sirait",
    "Sitompul","Sitorus","Sihombing","Siregar","Tampubolon","Manurung",
    "Napitupulu","Hutapea","Panjaitan","Pardede","Hutabarat","Nainggolan",
    "Lubis","Nasution","Harahap","Dalimunthe","Daulay","Ritonga",
    "Pohan","Rangkuti","Matondang","Batubara","Tanjung","Pulungan",
    "Suryadi","Hadiyanto","Wahyudi","Wicaksono","Yulianto","Zulkarnain",
    "Abdullah","Firdaus","Hamzah","Ibrahim","Ismail","Kusuma",
    "Maulani","Nurdiyanto","Oktavian","Perdana","Rachman","Saifullah",
    "Supriyadi","Utami","Wardani","Wulandari","Anggraeni","Handayani",
    "Kartini","Lestari","Maharani","Permatasari","Puspitasari","Rahayu",
    "Safitri","Septiani","Sulistyowati","Triwahyuni","Widyaningsih",
]

# ── Debug ─────────────────────────────────────────────────────────────────
_debug_files: List[str] = []
_DEBUG_HTML_NAMES = [
    "billing_page.html", "billing_error.html",
    "edu_form_page.html", "benefits_continue.html",
    "benefits_step1_error.html", "benefits_step2_error.html",
    "benefits_submit.html", "benefits_submit_error.html",
]

def _cleanup():
    for p in _debug_files:
        try:
            if os.path.exists(p): os.remove(p)
        except OSError:
            pass

def _cleanup_stale_debug():
    for name in _DEBUG_HTML_NAMES:
        p = os.path.join(BASE_DIR, name)
        try:
            if os.path.exists(p):
                os.remove(p)
                logger.info("Cleaned stale debug file: %s", name)
        except OSError:
            pass

_cleanup_stale_debug()
atexit.register(_cleanup)

# ── Keywords ──────────────────────────────────────────────────────────────
def load_keywords() -> List[str]:
    builtin = ["university","school","institut","sekolah","universitas",
               "vocational","islamic","politeknik","akademi","college",
               "polytechnic","madrasah","pesantren","smk","sma","smp"]
    kw_path = KEYWORDS_FILE if os.path.exists(KEYWORDS_FILE) else _BUNDLED_KEYWORDS
    if not os.path.exists(kw_path): return builtin
    try:
        with open(kw_path,"r",encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
        return lines if lines else builtin
    except (IOError, OSError):
        return builtin

# ── Settings ──────────────────────────────────────────────────────────────
_DEFAULT_SETTINGS = {
    "default_lat": DEFAULT_COORDS["lat"],
    "default_lon": DEFAULT_COORDS["lon"],
    "default_address": DEFAULT_ADDRESS["address"],
    "default_city": DEFAULT_ADDRESS["city"],
    "default_region": DEFAULT_ADDRESS["region"],
    "default_postal": DEFAULT_ADDRESS["postal_code"],
    "default_country": DEFAULT_ADDRESS["country_code"],
    "document_label": DEFAULT_DOCUMENT_LABEL,
    "search_delay": "0.4",
    "id_validity_days": "730",
    "ua_rotate": True,
    "theme": "light",
    "language": "id",
}

def load_settings() -> Dict[str, str]:
    settings = dict(_DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings.update(json.load(f))
        except (IOError, json.JSONDecodeError):
            pass
    return settings

def save_settings(settings: Dict[str, str]):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

# ── Session Builder ───────────────────────────────────────────────────────
def _build_session() -> requests.Session:
    s = requests.Session()
    cfg = load_settings()
    if cfg.get("ua_rotate", True):
        s.headers["User-Agent"] = random.choice(_UA_POOL)
    else:
        s.headers["User-Agent"] = _UA_POOL[0]
    retry = Retry(total=3, backoff_factor=1,
                  status_forcelist=[429,500,502,503,504],
                  allowed_methods=["GET","POST"])
    a = HTTPAdapter(max_retries=retry)
    s.mount("https://", a); s.mount("http://", a)
    return s

# ── Debug Helpers ─────────────────────────────────────────────────────────
def _save_debug(label: str, text: str, ext: str = "html"):
    try:
        dbg = os.path.join(BASE_DIR, "_debug")
        os.makedirs(dbg, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        fp = os.path.join(dbg, f"{ts}_{label}.{ext}")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass

def _save_debug_file(n, c):
    try:
        dbg = os.path.join(BASE_DIR, "_debug")
        os.makedirs(dbg, exist_ok=True)
        p = os.path.join(dbg, n)
        with open(p, "w", encoding="utf-8") as f: 
            f.write(c)
        _debug_files.append(p)
        return p
    except Exception as e:
        logger.warning("Failed to save debug file %s: %s", n, e)
        return None

# ── Log File ──────────────────────────────────────────────────────────────
def read_log_file(max_lines: int = 500) -> str:
    if not os.path.exists(_log_path):
        return "(No log file found)"
    try:
        with open(_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-max_lines:])
    except (IOError, OSError):
        return "(Error reading log)"

def clear_log_file():
    try:
        with open(_log_path, "w", encoding="utf-8") as f:
            f.write("")
    except (IOError, OSError):
        pass

# ── Camera Device Labels ─────────────────────────────────────────────────
_CAMERA_DEVICES = [
    "camera2 1, facing front (Google Pixel 9 Pro)",
    "camera2 0, facing back (Google Pixel 9 Pro)",
    "camera2 1, facing front (Google Pixel 8a)",
    "camera2 0, facing back (Google Pixel 8a)",
    "camera2 1, facing front (samsung SM-S928B Galaxy S24 Ultra)",
    "camera2 0, facing back (samsung SM-S928B Galaxy S24 Ultra)",
    "camera2 1, facing front (samsung SM-S921B Galaxy S24)",
    "camera2 0, facing back (samsung SM-S921B Galaxy S24)",
    "camera2 1, facing front (samsung SM-A556E Galaxy A55 5G)",
    "camera2 0, facing back (samsung SM-A556E Galaxy A55 5G)",
    "camera2 1, facing front (Xiaomi 14T Pro)",
    "camera2 0, facing back (Xiaomi 14T Pro)",
    "camera2 1, facing front (Redmi Note 13 Pro 5G)",
    "camera2 0, facing back (Redmi Note 13 Pro 5G)",
    "camera2 1, facing front (POCO X6 Pro)",
    "camera2 0, facing back (POCO X6 Pro)",
    "camera2 1, facing front (vivo V2332 V30)",
    "camera2 0, facing back (vivo V2332 V30)",
    "camera2 1, facing front (OPPO CPH2609 Reno11 F 5G)",
    "camera2 0, facing back (OPPO CPH2609 Reno11 F 5G)",
    "camera2 1, facing front (Realme RMX3996 12+ 5G)",
    "camera2 0, facing back (Realme RMX3996 12+ 5G)",
    "camera2 1, facing front (Infinix X6851 NOTE 40)",
    "camera2 0, facing back (Infinix X6851 NOTE 40)",
    "camera2 1, facing front (TECNO KL7 CAMON 30 5G)",
    "camera2 0, facing back (TECNO KL7 CAMON 30 5G)",
    "camera2 1, facing front (iPhone 15 Pro)",
    "camera2 0, facing back (iPhone 15 Pro)",
    "camera2 1, facing front (iPhone 14)",
    "camera2 0, facing back (iPhone 14)",
    "camera2 1, facing front (OnePlus 12R)",
    "camera2 0, facing back (OnePlus 12R)",
    "camera2 1, facing front (Nothing Phone (2a))",
    "camera2 0, facing back (Nothing Phone (2a))",
    "camera2 1, facing front (Honor 200)",
    "camera2 0, facing back (Honor 200)",
    "camera2 1, facing front (ASUS Zenfone 11 Ultra)",
    "camera2 0, facing back (ASUS Zenfone 11 Ultra)",
    "camera2 1, facing front (Lenovo TB370FU Tab P12)",
    "camera2 0, facing back (Lenovo TB370FU Tab P12)",
    "camera2 1, facing front (samsung SM-X210 Galaxy Tab A9+)",
    "camera2 0, facing back (samsung SM-X210 Galaxy Tab A9+)",
    "camera2 1, facing front (Xiaomi Redmi Pad Pro)",
    "camera2 0, facing back (Xiaomi Redmi Pad Pro)",
    "Logitech BRIO 500 (046d:0943)",
    "Logitech MX Brio 4K (046d:094c)",
    "Logitech C920 HD Pro Webcam (046d:082d)",
    "Razer Kiyo Pro (1532:0e03)",
    "Insta360 Link 4K (2e1a:4c01)",
    "Elgato Facecam Pro (0fd9:008e)",
    "OBSBOT Tiny 2 (345f:50a2)",
    "AVerMedia PW513 4K (07ca:0588)",
    "Dell UltraSharp Webcam WB7022 (413c:c015)",
    "HP 965 4K Streaming Webcam (03f0:1061)",
    "Lenovo Performance FHD Webcam (17ef:483a)",
    "Integrated Camera (SunplusIT)",
    "Integrated Camera (Chicony)",
    "Integrated IR Camera (Windows Hello)",
    "camera2 1, facing front (Infinix X6831 HOT 30i)",
    "camera2 1, facing front (Infinix X6711 NOTE 30 VIP)",
    "camera2 0, facing back (Infinix X6831 HOT 30i)",
    "camera2 1, facing front (Tecno CK7n SPARK 10 Pro)",
    "camera2 1, facing front (Tecno CK6n CAMON 20)",
    "camera2 0, facing back (Tecno CK7n SPARK 10 Pro)",
    "camera2 1, facing front (itel S665L S23+)",
    "camera2 1, facing front (itel A663L A60s)",
    "camera2 1, facing front (Realme RMX3710 C55)",
    "camera2 1, facing front (Realme RMX3782 Narzo 60x)",
    "camera2 0, facing back (Realme RMX3710 C55)",
    "camera2 1, facing front (vivo V2249 Y27 5G)",
    "camera2 1, facing front (vivo V2248 Y36)",
    "camera2 0, facing back (vivo V2249 Y27 5G)",
    "camera2 1, facing front (OPPO CPH2495 A78 5G)",
    "camera2 1, facing front (OPPO CPH2577 A58)",
    "camera2 0, facing back (OPPO CPH2495 A78 5G)",
    "camera2 1, facing front (Nokia TA-1581 G42 5G)",
    "camera2 1, facing front (Nokia TA-1564 C32)",
    "camera2 1, facing front (motorola XT2343-3 moto g54 5G)",
    "camera2 1, facing front (motorola XT2337-2 moto e13)",
    "camera2 0, facing back (motorola XT2343-3 moto g54 5G)",
    "camera2 1, facing front (ZTE 8050 Blade V50 Design)",
    "camera2 1, facing front (ZTE A7056 Blade A73 5G)",
    "camera2 1, facing front (Lava LZX408 Blaze 2 5G)",
    "camera2 1, facing front (Lava LZX503 Agni 2 5G)",
    "camera2 1, facing front (Wiko W-V900 T3)",
    "camera2 0, facing back (Wiko W-P860 Power U30)",
    "camera2 1, facing front (Coolpad CP12S Cool 5)",
    "camera2 1, facing front (Coolpad CP03 COOL 20s)",
    "camera2 1, facing front (Cubot J20 Note 50)",
    "camera2 0, facing back (Cubot K3 KingKong Star)",
    "camera2 1, facing front (Doogee DG601 V30 Pro)",
    "camera2 0, facing back (Doogee DG590 S100 Pro)",
    "camera2 1, facing front (Ulefone Armor_22 IP69K)",
    "camera2 1, facing front (Ulefone Note_16_Pro)",
    "camera2 1, facing front (OUKITEL WP28)",
    "camera2 0, facing back (OUKITEL C35)",
    "camera2 1, facing front (Blackview BV9300 Pro)",
    "camera2 1, facing front (Blackview A96)",
    "camera2 1, facing front (UMIDIGI A15 Tab)",
    "camera2 0, facing back (UMIDIGI G5_Mecha)",
    "AUKEY PC-LM1E FHD Webcam (2ce5:032c)",
    "AUKEY PC-W1 StreamCam (2ce5:0532)",
    "Anker PowerConf C200 2K (291a:1221)",
    "Anker PowerConf C300 (291a:1231)",
    "HD Webcam C270 (046d:0825)",
    "Webcam C505 HD (046d:0867)",
    "Logitech BRIO 101 (046d:0896)",
    "Logitech C922 Pro Stream (046d:085c)",
    "Microsoft® LifeCam HD-3000 (045e:0779)",
    "Microsoft® Modern Webcam (045e:09ae)",
    "Microsoft® LifeCam Cinema™ (045e:075d)",
    "Razer Kiyo X (1532:0e05)",
    "Razer Kiyo Pro Ultra (1532:0e13)",
    "Creative Live! Cam Sync V3 2K (041e:4088)",
    "Creative Live! Cam Sync 1080p V2 (041e:4095)",
    "PAPALOOK PA452 PRO FHD (1bcf:2883)",
    "PAPALOOK AF925 Autofocus (1bcf:2895)",
    "NexiGo N660 FHD Webcam (345f:2253)",
    "NexiGo N930AF Autofocus (345f:2265)",
    "NexiGo N60 HD (345f:2241)",
    "EMEET SmartCam C960 4K (3524:0160)",
    "EMEET Nova Webcam (3524:0220)",
    "Vitade 960A Pro HD (1bcf:2c87)",
    "Vitade 928A FHD (1bcf:2c99)",
    "Adesso CyberTrack H4 1080P (040b:2053)",
    "Adesso CyberTrack H6 4K (040b:2067)",
    "j5create JVCU100 HD Webcam (1bcf:2a01)",
    "j5create JVCU435 4K AI (1bcf:2a15)",
    "AVerMedia PW310P FHD (07ca:0570)",
    "AVerMedia PW315 1080p (07ca:0581)",
    "Elgato Facecam MK.2 (0fd9:008a)",
    "Elgato Facecam (0fd9:0083)",
    "USB2.0 HD UVC WebCam (5986:2113)",
    "Integrated Webcam HD (0c45:6a13)",
    "HD Camera (0bda:5689)",
    "USB Camera (534d:2109)",
    "Integrated IR Camera (5986:2122)",
    "camera2 1, facing front (Lenovo TB-X606F Tab M10 Plus)",
    "camera2 0, facing back (Lenovo TB-X606F Tab M10 Plus)",
    "camera2 1, facing front (samsung SM-X200 Galaxy Tab A8)",
    "camera2 0, facing back (samsung SM-X200 Galaxy Tab A8)",
    "camera2 1, facing front (TCL 9461G1 Tab 10L Gen 2)",
    "camera2 1, facing front (ALLDOCUBE iPlay_50 Pro)",
    "camera2 0, facing back (Teclast T50 Plus 4G)",
    "camera2 1, facing front (Headwolf FPad3 WPad3)",
]

_CAMERA_FILENAMES = [
    "camera_photo.png", "photo_capture.png", "webcam_shot.png",
    "camera_image.png", "captured_photo.png", "cam_photo.png",
    "snapshot.png", "camera_capture.png", "photo.png",
    "live_capture.png", "webcam_photo.png", "cam_capture.png",
]

def generate_indo_name():
    return random.choice(INDO_FIRST), random.choice(INDO_LAST)


# ── Bio Generation (Student Context) ──────────────────────────────────────
_BIO_TEMPLATES = [
    "Computer Science student passionate about {topic}. Currently learning {skill}. Building projects to sharpen my skills.",
    "{year} student exploring {topic} and {skill}. Love coding and creating meaningful applications.",
    "Aspiring developer studying {major}. Interested in {topic} and {skill}. Always eager to learn new technologies.",
    "IT student focused on {topic}. Currently diving deep into {skill}. Open to collaboration and learning.",
    "Software engineering student | {topic} enthusiast | Learning {skill} | Building cool stuff",
    "Tech enthusiast studying {major}. Passionate about {topic}. Working on projects using {skill}.",
    "Future developer learning {topic} and {skill}. Student at heart, coder by passion.",
    "{major} student | Exploring {topic} | {skill} learner | Code is my canvas",
    "Studying {major}, passionate about {topic}. Currently focused on {skill}. Let's connect!",
    "Student developer interested in {topic}. Learning {skill} to build amazing things.",
]

_BIO_TOPICS = [
    "web development", "mobile apps", "machine learning", "data science",
    "cloud computing", "cybersecurity", "AI", "software engineering",
    "full-stack development", "backend systems", "frontend design",
    "DevOps", "open source", "automation", "game development",
]

_BIO_SKILLS = [
    "Python", "JavaScript", "React", "Node.js", "Java", "Go", "TypeScript",
    "Flutter", "Docker", "Kubernetes", "AWS", "TensorFlow", "Vue.js",
    "Next.js", "MongoDB", "PostgreSQL", "GraphQL", "FastAPI", "Django",
]

_BIO_MAJORS = [
    "Computer Science", "Information Technology", "Software Engineering",
    "Informatics", "Information Systems", "Computer Engineering",
    "Data Science", "Cyber Security", "Network Engineering",
]

_BIO_YEARS = ["Freshman", "Sophomore", "Junior", "Senior", "CS", "IT"]

def generate_student_bio() -> str:
    """Generate a random bio with student/college context (max ~50 words)."""
    template = random.choice(_BIO_TEMPLATES)
    bio = template.format(
        topic=random.choice(_BIO_TOPICS),
        skill=random.choice(_BIO_SKILLS),
        major=random.choice(_BIO_MAJORS),
        year=random.choice(_BIO_YEARS),
    )
    return bio


# ── Repository Name/Description Generation ────────────────────────────────
_REPO_ADJECTIVES = [
    "awesome", "cool", "simple", "smart", "fast", "tiny", "easy", "clean",
    "mini", "quick", "basic", "modern", "fresh", "handy", "lite", "super",
]

_REPO_NOUNS = [
    "project", "app", "tool", "demo", "lab", "code", "starter", "template",
    "notes", "study", "practice", "learning", "playground", "sandbox",
    "portfolio", "showcase", "helper", "utils", "scripts", "experiments",
]

_REPO_DESC_TEMPLATES = [
    "A simple {noun} for learning and experimentation",
    "My personal {noun} repository for {topic}",
    "Collection of {topic} {noun} and examples",
    "Learning {topic} with practical {noun}",
    "{topic} practice {noun} and exercises",
    "Simple {noun} to explore {topic}",
    "Personal {noun} for studying {topic}",
    "A {adj} {noun} for {topic} development",
]

def generate_repo_name() -> str:
    """Generate a random repository name with timestamp to avoid conflicts."""
    from datetime import datetime
    adj = random.choice(_REPO_ADJECTIVES)
    noun = random.choice(_REPO_NOUNS)
    # Use timestamp to ensure unique name
    ts = datetime.now().strftime("%m%d%H%M")
    patterns = [
        f"{adj}-{noun}-{ts}",
        f"my-{noun}-{ts}",
        f"learn-{random.choice(_BIO_SKILLS).lower().replace('.', '').replace(' ', '-')[:10]}-{ts}",
        f"{noun}-project-{ts}",
    ]
    return random.choice(patterns)


def generate_repo_description() -> str:
    """Generate a random repository description."""
    template = random.choice(_REPO_DESC_TEMPLATES)
    desc = template.format(
        noun=random.choice(_REPO_NOUNS),
        topic=random.choice(_BIO_TOPICS),
        adj=random.choice(_REPO_ADJECTIVES),
    )
    return desc


# ── Submission History ────────────────────────────────────────────────────────────
_MAX_HISTORY = 500


def load_history() -> List[Dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return []


def add_history_entry(username: str, school: str, full_name: str, status: str = ""):
    """Append one submission record to history.json (capped at _MAX_HISTORY)."""
    entries = load_history()
    entries.append({
        "username": username,
        "school": school,
        "full_name": full_name,
        "status": status,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    if len(entries) > _MAX_HISTORY:
        entries = entries[-_MAX_HISTORY:]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except (IOError, OSError) as e:
        logger.warning("Failed to save history: %s", e)


def clear_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    except (IOError, OSError):
        pass
