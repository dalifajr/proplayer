"""Student ID card generation — pure-Python PNG renderer with Pillow photo embedding."""
import os
import random
import string
import struct
import zlib
from datetime import datetime, timedelta
from typing import Optional

from .config import BASE_DIR, PHOTOS_DIR, load_settings, logger


# ── Low-level PNG ─────────────────────────────────────────────────────────
def _make_png(w, h, px):
    def chunk(ct, data):
        c = ct + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    raw = b""
    for y in range(h):
        raw += b"\x00" + px[y * w * 4:(y + 1) * w * 4]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(raw)) +
            chunk(b"IEND", b""))


def _rect(px, w, h, x1, y1, x2, y2, r, g, b):
    for y in range(max(0, y1), min(h, y2)):
        for x in range(max(0, x1), min(w, x2)):
            o = (y * w + x) * 4
            px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255


# ── Bitmap Font ───────────────────────────────────────────────────────────
FONT5x7 = {
    'A': [0x04, 0x0A, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'B': [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    'C': [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    'D': [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    'E': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    'F': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    'G': [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0E],
    'H': [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'I': [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    'J': [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    'K': [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    'L': [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    'M': [0x11, 0x1B, 0x15, 0x11, 0x11, 0x11, 0x11],
    'N': [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    'O': [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'P': [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    'Q': [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    'R': [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    'S': [0x0E, 0x11, 0x10, 0x0E, 0x01, 0x11, 0x0E],
    'T': [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    'U': [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'V': [0x11, 0x11, 0x11, 0x11, 0x0A, 0x0A, 0x04],
    'W': [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    'X': [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    'Y': [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    'Z': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    '0': [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    '1': [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    '2': [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
    '3': [0x0E, 0x11, 0x01, 0x06, 0x01, 0x11, 0x0E],
    '4': [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    '5': [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    '6': [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    '7': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    '8': [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    '9': [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    ' ': [0] * 7, '-': [0, 0, 0, 0x0E, 0, 0, 0], '.': [0, 0, 0, 0, 0, 0, 0x04],
    ':': [0, 0x04, 0, 0, 0, 0x04, 0], ',': [0, 0, 0, 0, 0, 0x04, 0x08],
    '/': [0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10],
    '(': [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02],
    ')': [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
    '@': [0x0E, 0x11, 0x17, 0x15, 0x17, 0x10, 0x0E],
}


def _bmp_text(px, w, h, x0, y0, text, r, g, b, sc=1):
    cx = x0
    for ch in text.upper():
        gl = FONT5x7.get(ch, FONT5x7.get(' ', [0] * 7))
        for ri, rb in enumerate(gl):
            for col in range(5):
                if rb & (0x10 >> col):
                    for dy in range(sc):
                        for dx in range(sc):
                            px_x = cx + col * sc + dx
                            px_y = y0 + ri * sc + dy
                            if 0 <= px_x < w and 0 <= px_y < h:
                                o = (px_y * w + px_x) * 4
                                px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255
        cx += 6 * sc


# ── Photo Loading & Embedding ────────────────────────────────────────────
def _load_random_photo_png():
    """Load a random student photo from photos/ directory.
    Returns (path, width, height) or None."""
    if not os.path.exists(PHOTOS_DIR):
        return None
    photos = [f for f in os.listdir(PHOTOS_DIR)
              if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not photos:
        return None
    chosen = os.path.join(PHOTOS_DIR, random.choice(photos))
    try:
        from PIL import Image
        with Image.open(chosen) as img:
            return chosen, img.width, img.height
    except ImportError:
        pass
    except Exception:
        pass
    try:
        with open(chosen, "rb") as f:
            data = f.read(24)
        if data[:4] == b'\x89PNG':
            w = struct.unpack('>I', data[16:20])[0]
            h = struct.unpack('>I', data[20:24])[0]
            return chosen, w, h
        return chosen, 0, 0
    except Exception:
        return None


def _embed_photo_on_card(px, card_w, card_h, photo_path, x1, y1, x2, y2):
    """Embed a photo file into the card pixel buffer area.
    Uses Pillow to decode and resize; falls back to styled placeholder."""
    target_w = x2 - x1
    target_h = y2 - y1
    embedded = False

    if photo_path and os.path.isfile(photo_path):
        try:
            from PIL import Image
            with Image.open(photo_path) as img:
                img = img.convert("RGBA")
                img_ratio = img.width / img.height
                target_ratio = target_w / target_h
                if img_ratio > target_ratio:
                    new_h = img.height
                    new_w = int(new_h * target_ratio)
                    left = (img.width - new_w) // 2
                    img = img.crop((left, 0, left + new_w, new_h))
                else:
                    new_w = img.width
                    new_h = int(new_w / target_ratio)
                    top = (img.height - new_h) // 2
                    img = img.crop((0, top, new_w, top + new_h))
                img = img.resize((target_w, target_h), Image.LANCZOS)
                photo_pixels = img.tobytes()
                for py_off in range(target_h):
                    for px_off in range(target_w):
                        src_idx = (py_off * target_w + px_off) * 4
                        dst_x = x1 + px_off
                        dst_y = y1 + py_off
                        if 0 <= dst_x < card_w and 0 <= dst_y < card_h:
                            dst_idx = (dst_y * card_w + dst_x) * 4
                            alpha = photo_pixels[src_idx + 3]
                            if alpha == 255:
                                px[dst_idx] = photo_pixels[src_idx]
                                px[dst_idx + 1] = photo_pixels[src_idx + 1]
                                px[dst_idx + 2] = photo_pixels[src_idx + 2]
                                px[dst_idx + 3] = 255
                            elif alpha > 0:
                                a = alpha / 255.0
                                px[dst_idx] = int(photo_pixels[src_idx] * a + px[dst_idx] * (1 - a))
                                px[dst_idx + 1] = int(photo_pixels[src_idx + 1] * a + px[dst_idx + 1] * (1 - a))
                                px[dst_idx + 2] = int(photo_pixels[src_idx + 2] * a + px[dst_idx + 2] * (1 - a))
                                px[dst_idx + 3] = 255
                embedded = True
                logger.info("Photo embedded: %s (%dx%d → %dx%d)",
                            photo_path, img.width, img.height, target_w, target_h)
        except ImportError:
            logger.warning("Pillow not installed — using photo placeholder")
        except Exception as e:
            logger.warning("Photo embed failed: %s", e)

    if not embedded:
        accent_r = random.randint(60, 180)
        accent_g = random.randint(60, 180)
        accent_b = random.randint(120, 200)
        _rect(px, card_w, card_h, x1, y1, x2, y2, accent_r, accent_g, accent_b)
        _rect(px, card_w, card_h, x1 + 3, y1 + 3, x2 - 3, y2 - 3, 220, 225, 235)
        mid_x = x1 + (x2 - x1) // 2 - 18
        mid_y = y1 + (y2 - y1) // 2 - 4
        _bmp_text(px, card_w, card_h, mid_x, mid_y, "PHOTO", 140, 140, 160, sc=2)


# ── ID Card Templates ────────────────────────────────────────────────────
_ID_TEMPLATES = [
    {
        "name": "formal_blue",
        "bg": (255, 255, 255), "header_bg": (25, 60, 140),
        "header_text": (255, 255, 255), "accent": (200, 220, 255),
        "footer_bg": (25, 60, 140), "footer_text": (255, 255, 255),
        "title": "STUDENT IDENTITY CARD", "label_color": (100, 100, 100),
        "value_color": (0, 0, 0), "status_color": (0, 120, 0),
    },
    {
        "name": "campus_teal",
        "bg": (245, 250, 250), "header_bg": (0, 128, 128),
        "header_text": (255, 255, 255), "accent": (180, 230, 230),
        "footer_bg": (0, 100, 100), "footer_text": (220, 255, 255),
        "title": "STUDENT CARD", "label_color": (80, 120, 120),
        "value_color": (20, 20, 20), "status_color": (0, 140, 80),
    },
    {
        "name": "elegant_maroon",
        "bg": (255, 252, 248), "header_bg": (128, 0, 32),
        "header_text": (255, 220, 200), "accent": (220, 180, 180),
        "footer_bg": (100, 0, 25), "footer_text": (255, 230, 210),
        "title": "STUDENT ID", "label_color": (120, 80, 80),
        "value_color": (40, 0, 0), "status_color": (0, 100, 50),
    },
    {
        "name": "campus_green",
        "bg": (248, 255, 248), "header_bg": (34, 100, 34),
        "header_text": (230, 255, 230), "accent": (180, 220, 180),
        "footer_bg": (20, 80, 20), "footer_text": (200, 255, 200),
        "title": "STUDENT IDENTITY CARD", "label_color": (80, 110, 80),
        "value_color": (10, 30, 10), "status_color": (0, 120, 0),
    },
    {
        "name": "academic_navy",
        "bg": (252, 248, 255), "header_bg": (72, 30, 120),
        "header_text": (230, 210, 255), "accent": (200, 180, 230),
        "footer_bg": (55, 20, 100), "footer_text": (220, 200, 255),
        "title": "KARTU MAHASISWA", "label_color": (100, 80, 130),
        "value_color": (30, 10, 50), "status_color": (60, 120, 0),
    },
]


def generate_student_id(name, school_name, student_id=None, logo_path=None, template_name=None):
    """Generate an ID card using a random template and optional photo + logo."""
    if not student_id:
        student_id = "STU" + "".join(random.choices(string.digits, k=8))

    tmpl = None
    if template_name:
        for candidate in _ID_TEMPLATES:
            if candidate.get("name") == template_name:
                tmpl = candidate
                break
    if tmpl is None:
        tmpl = random.choice(_ID_TEMPLATES)
    W, H = 420, 640
    px = bytearray(W * H * 4)

    # Base layers: outer border, inner canvas, and structured header zones.
    _rect(px, W, H, 0, 0, W, H, 20, 24, 32)
    _rect(px, W, H, 6, 6, W - 6, H - 6, *tmpl["bg"])
    _rect(px, W, H, 6, 6, W - 6, 132, *tmpl["header_bg"])
    _rect(px, W, H, 6, 132, W - 6, 148, *tmpl["accent"])

    # Logo container in header.
    _rect(px, W, H, 18, 18, 108, 108, 245, 247, 252)
    _rect(px, W, H, 22, 22, 104, 104, 255, 255, 255)

    # ── Logo in header (left side for portrait layout) ───────────────
    logo_w = 0
    if logo_path and os.path.isfile(logo_path):
        try:
            from PIL import Image
            with Image.open(logo_path) as logo:
                logo = logo.convert("RGBA")
                lh = 70
                lw = int(logo.width * lh / logo.height)
                lw = min(lw, 78)
                logo = logo.resize((lw, lh), Image.LANCZOS)
                logo_x = 24 + (78 - lw) // 2
                logo_y = 28
                logo_pixels = logo.tobytes()
                for py_off in range(lh):
                    for px_off in range(lw):
                        src_idx = (py_off * lw + px_off) * 4
                        dst_x = logo_x + px_off
                        dst_y = logo_y + py_off
                        if 0 <= dst_x < W and 0 <= dst_y < H:
                            dst_idx = (dst_y * W + dst_x) * 4
                            alpha = logo_pixels[src_idx + 3]
                            if alpha > 128:
                                px[dst_idx] = logo_pixels[src_idx]
                                px[dst_idx + 1] = logo_pixels[src_idx + 1]
                                px[dst_idx + 2] = logo_pixels[src_idx + 2]
                                px[dst_idx + 3] = 255
                logo_w = 104
                logger.info("Logo embedded on ID card: %s (%dx%d)", logo_path, lw, lh)
        except Exception as e:
            logger.warning("Logo embed failed on ID card: %s", e)

    text_x = 24 + logo_w
    _bmp_text(px, W, H, text_x, 24, "OFFICIAL STUDENT CARD", *tmpl["accent"], sc=2)
    _bmp_text(px, W, H, text_x, 54, school_name[:26], *tmpl["header_text"], sc=2)
    _bmp_text(px, W, H, text_x, 84, "ACADEMIC YEAR 2025/2026", *tmpl["accent"], sc=1)

    # Photo panel with double frame.
    _rect(px, W, H, 92, 164, 328, 408, 220, 225, 235)
    _rect(px, W, H, 98, 170, 322, 402, 255, 255, 255)

    photo_info = _load_random_photo_png()
    _embed_photo_on_card(px, W, H,
                         photo_info[0] if photo_info else "",
                         110, 182, 310, 390)

    # Info panel background.
    _rect(px, W, H, 24, 420, W - 24, 590, 248, 250, 255)
    _rect(px, W, H, 24, 452, W - 24, 454, 225, 230, 240)
    _rect(px, W, H, 24, 484, W - 24, 486, 225, 230, 240)
    _rect(px, W, H, 24, 516, W - 24, 518, 225, 230, 240)

    _bmp_text(px, W, H, 36, 430, "NAME", *tmpl["label_color"], sc=1)
    _bmp_text(px, W, H, 36, 460, "STUDENT ID", *tmpl["label_color"], sc=1)
    _bmp_text(px, W, H, 36, 492, "PROGRAM", *tmpl["label_color"], sc=1)
    _bmp_text(px, W, H, 36, 524, "STATUS", *tmpl["label_color"], sc=1)

    _bmp_text(px, W, H, 138, 428, name[:26], *tmpl["value_color"], sc=2)
    _bmp_text(px, W, H, 138, 460, student_id[:20], *tmpl["value_color"], sc=2)
    _bmp_text(px, W, H, 138, 492, "INFORMATION SYSTEM", *tmpl["value_color"], sc=1)
    _bmp_text(px, W, H, 138, 524, "ACTIVE", *tmpl["status_color"], sc=2)

    issued = datetime.now().strftime("%Y/%m/%d")
    _validity = int(load_settings().get("id_validity_days", 730))
    valid = (datetime.now() + timedelta(days=_validity)).strftime("%Y/%m/%d")
    _bmp_text(px, W, H, 36, 556, f"ISSUED {issued}", 80, 80, 80, sc=1)
    _bmp_text(px, W, H, 196, 556, f"VALID {valid}", 80, 80, 80, sc=1)

    # Security pattern block to emulate barcode/serial strip.
    sec_x = 296
    for i in range(16):
        bar_h = 10 + (i % 3) * 3
        color = 55 if i % 2 == 0 else 130
        _rect(px, W, H, sec_x + i * 5, 548, sec_x + i * 5 + 2, 548 + bar_h, color, color, color)

    _rect(px, W, H, 6, 598, W - 6, 634, *tmpl["footer_bg"])
    _bmp_text(px, W, H, 18, 610, school_name[:24], *tmpl["footer_text"], sc=1)
    _bmp_text(px, W, H, 250, 610, f"CARD NO {student_id[-8:]}", *tmpl["footer_text"], sc=1)

    out_dir = os.path.join(BASE_DIR, "outputs", "id_cards")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "Student_ID_Front.png")
    with open(out, "wb") as f:
        f.write(_make_png(W, H, bytes(px)))
    return out
