#!/usr/bin/env python3
"""
GitHub Edu Pro — CLI Full-Auto Mode
Modern & Clean terminal UI with Rich support.
"""

import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime

# ── Fix working directory ─────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

import core
from i18n import t, set_language, get_language

# ── Rich integration (optional) ───────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


# ══════════════════════════════════════════════════════════════════════════
#  ANSI PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════
class S:
    """Minimal ANSI style tokens."""
    R      = "\033[0m"          # reset
    B      = "\033[1m"          # bold
    D      = "\033[2m"          # dim
    I      = "\033[3m"          # italic
    U      = "\033[4m"          # underline
    # palette — muted / modern
    FG     = "\033[38;5;252m"   # default text (off-white)
    ACC    = "\033[38;5;75m"    # accent  (soft blue)
    ACC2   = "\033[38;5;117m"   # accent2 (light cyan)
    OK     = "\033[38;5;114m"   # green
    WARN   = "\033[38;5;221m"   # yellow
    ERR    = "\033[38;5;203m"   # red
    MUTED  = "\033[38;5;243m"   # gray
    FAINT  = "\033[38;5;238m"   # darker gray
    LABEL  = "\033[38;5;248m"   # label gray
    VAL    = "\033[38;5;255m"   # value white
    LIME   = "\033[38;5;156m"
    TEAL   = "\033[38;5;73m"
    ORANGE = "\033[38;5;215m"
    PINK   = "\033[38;5;211m"
    # backgrounds
    BG_BAR = "\033[48;5;236m"
    BG_OK  = "\033[48;5;22m"
    BG_ERR = "\033[48;5;52m"
    BG_WRN = "\033[48;5;58m"
    BG_ACC = "\033[48;5;24m"
    # control
    EL     = "\033[2K"          # erase line
    HIDE   = "\033[?25l"
    SHOW   = "\033[?25h"


# ── helpers ───────────────────────────────────────────────────────────────
def W():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80


def enable_ansi():
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            pass


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def _vlen(text):
    """Visible length (strip ANSI)."""
    return len(re.sub(r'\033\[[0-9;]*m', '', text))


def _wr(text):
    """Write inline (overwrite current line)."""
    w = W()
    if _vlen(text) > w - 1:
        text = text[:w - 4] + S.D + "…" + S.R
    sys.stdout.write(f"\r{S.EL}{text}")
    sys.stdout.flush()


def _clr():
    sys.stdout.write(f"\r{S.EL}")
    sys.stdout.flush()


def _censor(name):
    if not name or len(name) <= 3:
        return "***"
    return name[:3] + "·" * min(len(name) - 3, 10)


def _censor_text(text, names):
    for n in names:
        if n and n in text:
            text = text.replace(n, _censor(n))
    return text


# ══════════════════════════════════════════════════════════════════════════
#  UI COMPONENTS
# ══════════════════════════════════════════════════════════════════════════

# ── gradient ─────────────────────────────────────────────────────────────
_GRAD = [
    (66, 165, 245), (56, 152, 238), (46, 139, 232), (42, 130, 218),
    (56, 142, 226), (66, 155, 235), (76, 168, 244), (86, 180, 252),
    (76, 168, 244), (66, 155, 235),
]


def _grad(text, palette=None):
    """Apply an RGB gradient to text."""
    pal = palette or _GRAD
    out = []
    for i, ch in enumerate(text):
        r, g, b = pal[i % len(pal)]
        out.append(f"\033[38;2;{r};{g};{b}m{ch}")
    out.append(S.R)
    return "".join(out)


# ── banner ───────────────────────────────────────────────────────────────
def banner():
    w = W()
    iw = min(w - 4, 62)

    if RICH_AVAILABLE:
        # Rich version with styled panel
        from rich.text import Text
        art_lines = [
            "╔═╗╦╔╦╗╦ ╦╦ ╦╔╗   ╔═╗╔╦╗╦ ╦  ╔═╗╦═╗╔═╗",
            "║ ╦║ ║ ╠═╣║ ║╠╩╗  ║╣  ║║║ ║  ╠═╝╠╦╝║ ║",
            "╚═╝╩ ╩ ╩ ╩╚═╝╚═╝  ╚═╝═╩╝╚═╝  ╩  ╩╚═╚═╝",
        ]
        text = Text()
        for i, line in enumerate(art_lines):
            text.append(line, style="bold cyan")
            if i < len(art_lines) - 1:
                text.append("\n")
        text.append("\n\n[dim]Full-Auto CLI  │  by Dzul[/dim]")
        console.print()
        console.print(Panel(text, border_style="blue", box=box.DOUBLE))
        console.print()
        return

    print()
    print(f"  {S.FAINT}{'─' * iw}{S.R}")

    if w >= 60:
        art = [
            " ╔═╗╦╔╦╗╦ ╦╦ ╦╔╗   ╔═╗╔╦╗╦ ╦  ╔═╗╦═╗╔═╗ ",
            " ║ ╦║ ║ ╠═╣║ ║╠╩╗  ║╣  ║║║ ║  ╠═╝╠╦╝║ ║ ",
            " ╚═╝╩ ╩ ╩ ╩╚═╝╚═╝  ╚═╝═╩╝╚═╝  ╩  ╩╚═╚═╝ ",
        ]
        for line in art:
            pad = (iw - len(line)) // 2
            print(f"  {' ' * pad}{_grad(line)}")
    else:
        title = "GITHUB EDU PRO"
        pad = (iw - len(title)) // 2
        print(f"  {' ' * pad}{S.B}{_grad(title)}{S.R}")

    print()
    sub = "Full-Auto CLI"
    pad = (iw - len(sub) - 11) // 2
    print(f"  {' ' * pad}{S.MUTED}{sub}  {S.FAINT}│  by Dzul{S.R}")
    print(f"  {S.FAINT}{'─' * iw}{S.R}")
    print()


# ── section header ───────────────────────────────────────────────────────
def header(title, icon=""):
    w = W()
    iw = min(w - 4, 60)
    full_label = f" {icon}  {title} "
    vl = _vlen(full_label)
    line_l = 2
    line_r = max(2, iw - vl - line_l)
    print()
    print(
        f"  {S.FAINT}{'─' * line_l}{S.R}"
        f"{S.BG_BAR}{S.B}{S.ACC}{full_label}{S.R}"
        f"{S.FAINT}{'─' * line_r}{S.R}"
    )


# ── status line ──────────────────────────────────────────────────────────
_ICO = {
    "ok":   (S.OK,   "✓"),
    "err":  (S.ERR,  "✗"),
    "warn": (S.WARN, "!"),
    "info": (S.ACC,  "·"),
    "wait": (S.ACC2, "⟳"),
}


def status(msg, tag="info", inline=False):
    c, ico = _ICO.get(tag, _ICO["info"])
    line = f"  {c}{ico}{S.R}  {msg}"
    if inline:
        _wr(line)
    else:
        print(line)


# ── card (left-border style) ─────────────────────────────────────────────
def card_start():
    print(f"  {S.FAINT}┌{'─' * 4}{S.R}")


def card_row(text, indent=1):
    print(f"  {S.FAINT}│{S.R}{' ' * indent} {text}")


def card_end():
    print(f"  {S.FAINT}└{'─' * 4}{S.R}")


# ── step indicator ───────────────────────────────────────────────────────
_SPIN = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def step(num, total, title):
    _clr()
    for i in range(6):
        ch = _SPIN[i % len(_SPIN)]
        _wr(f"  {S.ACC}{ch}{S.R}  {S.D}[{num}/{total}] {title}…{S.R}")
        time.sleep(0.06)
    _clr()

    filled  = f"{S.ACC}{'━' * num}{S.R}"
    remain  = f"{S.FAINT}{'╌' * (total - num)}{S.R}"
    counter = f"{S.MUTED}{num}/{total}{S.R}"
    print(f"  {S.ACC}▸{S.R}  {filled}{remain}  {S.B}{title}{S.R}  {counter}")


# ── separator ────────────────────────────────────────────────────────────
def sep(label=""):
    w = W()
    iw = min(w - 4, 60)
    if label:
        side = max(2, (iw - len(label) - 4) // 2)
        print(f"  {S.FAINT}{'─' * side}{S.R} {S.MUTED}{label}{S.R} {S.FAINT}{'─' * side}{S.R}")
    else:
        print(f"  {S.FAINT}{'─' * iw}{S.R}")


# ══════════════════════════════════════════════════════════════════════════
#  RICH-ENHANCED DISPLAY HELPERS
# ══════════════════════════════════════════════════════════════════════════
def rich_panel(title, content, style="blue"):
    """Display content in a Rich panel if available, fallback to card."""
    if RICH_AVAILABLE:
        console.print(Panel(content, title=title, border_style=style, box=box.ROUNDED))
    else:
        sep(title)
        print(f"  {content}")
        sep()


def rich_table(title, rows, columns=None):
    """Display a Rich table if available, fallback to simple rows."""
    if RICH_AVAILABLE:
        table = Table(title=title, box=box.ROUNDED, show_header=bool(columns))
        if columns:
            for col in columns:
                table.add_column(col, style="cyan")
        for row in rows:
            if isinstance(row, (list, tuple)):
                table.add_row(*[str(c) for c in row])
            else:
                table.add_row(str(row))
        console.print(table)
    else:
        if title:
            sep(title)
        for row in rows:
            if isinstance(row, (list, tuple)):
                print(f"  {' | '.join(str(c) for c in row)}")
            else:
                print(f"  {row}")


def rich_status(message, status_type="info"):
    """Display status with Rich styling if available."""
    if RICH_AVAILABLE:
        style_map = {
            "ok": "green",
            "err": "red",
            "warn": "yellow",
            "info": "blue",
        }
        style = style_map.get(status_type, "blue")
        icon_map = {"ok": "✓", "err": "✗", "warn": "!", "info": "·"}
        icon = icon_map.get(status_type, "·")
        console.print(f"  [{style}]{icon}[/{style}]  {message}")
    else:
        status(message, status_type)


def rich_prompt(message, default=None, password=False):
    """Get input with Rich prompt if available."""
    if RICH_AVAILABLE:
        return Prompt.ask(f"  [cyan]❯[/cyan] {message}", default=default, password=password)
    else:
        prompt_text = f"  {S.ACC}❯{S.R} {message}"
        if default:
            prompt_text += f" [{default}]"
        prompt_text += ": "
        return input(prompt_text).strip() or default


def rich_confirm(message, default=True):
    """Get yes/no confirmation with Rich if available."""
    if RICH_AVAILABLE:
        return Confirm.ask(f"  {message}", default=default)
    else:
        yn = "Y/n" if default else "y/N"
        result = input(f"  {message} [{yn}]: ").strip().lower()
        if not result:
            return default
        return result in ("y", "yes")


# ── open notepad ─────────────────────────────────────────────────────────
def _open_notepad(username, setup_key, codes):
    codes_txt = "\n".join(codes) if codes else t("tfa_codes_na")
    content = (
        f"*GitHub Students Dev Pack*\n"
        f"Username: {username}\n"
        f"Password: \n"
        f"F2A: {setup_key}\n\n"
        f"Recovery Codes:\n{codes_txt}\n\n"
        f"_dzulfikrialifajri store_\n"
    )
    try:
        fd, path = tempfile.mkstemp(suffix=".txt", prefix=f"{username}_2fa_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        if os.name == "nt":
            subprocess.Popen(
                ["notepad.exe", path],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        elif _is_termux():
            # Termux: try termux-open, fallback to printing content
            try:
                subprocess.Popen(["termux-open", path])
            except FileNotFoundError:
                print(f"\n  {S.ACC}{'─' * 40}{S.R}")
                print(f"  {S.B}{S.ACC}📄 2FA Info:{S.R}")
                print(f"  {S.FAINT}{'─' * 40}{S.R}")
                for line in content.strip().split("\n"):
                    print(f"  {S.FG}{line}{S.R}")
                print(f"  {S.FAINT}{'─' * 40}{S.R}")
                print(f"  {S.MUTED}Saved: {path}{S.R}\n")
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _is_termux():
    """Detect if running inside Termux on Android."""
    return os.path.isdir("/data/data/com.termux") or "TERMUX_VERSION" in os.environ


# ══════════════════════════════════════════════════════════════════════════
#  STEP 1 — LOGIN
# ══════════════════════════════════════════════════════════════════════════
def do_login():
    while True:
        header(t("login_title"), "🔐")
        print()
        print(f"  {S.MUTED}{t('login_paste_hint')}{S.R}")
        print(f"  {S.FAINT}{t('login_quit_hint')}{S.R}")
        print()

        try:
            cookie = input(f"  {S.ACC}❯{S.R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {S.MUTED}{t('bye')}{S.R}")
            sys.exit(0)

        if cookie.lower() in ("quit", "exit", "q"):
            print(f"\n  {S.MUTED}{t('bye')}{S.R}")
            sys.exit(0)

        if not cookie:
            status(t("login_empty"), "err")
            continue

        _wr(f"  {S.ACC}⟳{S.R}  {t('login_authenticating')}")
        try:
            session = core.login_with_cookie_str(cookie)
            ok = core.is_logged_in(session)
            _clr()
            if ok:
                status(t("login_success"), "ok")
                return session, cookie
            else:
                status(t("login_failed"), "err")
                print()
        except Exception as e:
            _clr()
            status(t("login_error", error=e), "err")
            print()


# ══════════════════════════════════════════════════════════════════════════
#  STEP 2 — ACCOUNT DETAILS
# ══════════════════════════════════════════════════════════════════════════
def check_user_details(session):
    header(t("account_title"), "👤")
    _wr(f"  {S.ACC}⟳{S.R}  {t('fetching_profile')}")

    info = core.get_profile_details(session)
    _clr()

    username = info.get("username", "?")
    name     = info.get("name", "—") or "—"
    email    = info.get("email", "—") or "—"
    age_days = info.get("age_days", 0)
    created  = info.get("created", "")[:10]

    print()
    card_start()
    card_row(f"{S.B}{S.ACC}@{username}{S.R}")
    card_row(f"{S.FAINT}{'─' * 30}{S.R}")
    card_row(f"{S.LABEL}Name     {S.R} {name}")
    card_row(f"{S.LABEL}Email    {S.R} {email}")

    if age_days < 3:
        age_c = S.ERR
    elif age_days < 7:
        age_c = S.WARN
    else:
        age_c = S.OK
    age_txt = f"{age_days}d" + (f"  {S.FAINT}({created}){S.R}" if created else "")
    card_row(f"{S.LABEL}Age      {S.R} {age_c}{age_txt}{S.R}")
    card_end()
    print()

    if age_days < 3:
        status(t("account_new_warn", days=age_days), "warn")

    return info


# ══════════════════════════════════════════════════════════════════════════
#  STEP 3 — 2FA
# ══════════════════════════════════════════════════════════════════════════
def check_and_setup_2fa(session, username="unknown"):
    header(t("tfa_title"), "🔒")
    _wr(f"  {S.ACC}⟳{S.R}  {t('tfa_checking')}")

    tfa = False
    try:
        tfa = core.check_2fa_status(session)
    except Exception as e:
        _clr()
        status(t("tfa_check_failed", error=e), "err")

    if tfa:
        _clr()
        status(t("tfa_already_active"), "ok")
        return True

    _clr()
    status(t("tfa_not_active"), "warn")
    print()

    def on_log(msg):
        important = any(k in msg for k in ("✅", "🔑", "💾", "⚠", "❌"))
        if important:
            _clr()
            print(f"    {S.MUTED}▸{S.R} {msg}")
        else:
            _wr(f"    {S.MUTED}▸{S.R} {msg}")

    try:
        result = core.setup_2fa(session, on_log=on_log)
        _clr()

        setup_key = result.get("setup_key", "")
        recovery  = result.get("recovery_codes", [])
        saved_to  = result.get("saved_to", "")

        print()
        card_start()
        card_row(f"{S.B}{S.OK}2FA SETUP COMPLETE{S.R}")
        card_row(f"{S.FAINT}{'─' * 34}{S.R}")
        card_row(f"{S.LABEL}Key    {S.R} {S.B}{S.LIME}{setup_key}{S.R}")
        if recovery:
            card_row(f"{S.LABEL}Codes{S.R}")
            for i, code in enumerate(recovery, 1):
                card_row(f"  {S.MUTED}{i:2d}.{S.R} {code}")
        if saved_to:
            card_row(f"{S.LABEL}File   {S.R} {S.TEAL}{os.path.basename(saved_to)}{S.R}")
        card_end()
        print()

        status(t("tfa_setup_complete"), "ok")

        # clipboard
        try:
            if os.name == "nt":
                subprocess.run(
                    ["clip"], input=setup_key.encode(), check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                status(t("tfa_clipboard"), "ok")
            elif _is_termux():
                subprocess.run(
                    ["termux-clipboard-set"], input=setup_key.encode(), check=True,
                )
                status(t("tfa_clipboard"), "ok")
        except Exception:
            pass

        _open_notepad(username, setup_key, recovery)
        status(t("tfa_notepad"), "ok")
        return True

    except RuntimeError as e:
        _clr()
        if "already enabled" in str(e).lower():
            status(t("tfa_detected"), "ok")
            return True
        status(t("tfa_setup_failed", error=e), "err")
        return False
    except Exception as e:
        _clr()
        status(t("tfa_setup_error", error=e), "err")
        return False


# ══════════════════════════════════════════════════════════════════════════
#  STEP 4 — PIPELINE
# ══════════════════════════════════════════════════════════════════════════
def _ask_cam_filter():
    """Prompt user to choose camera filter for school list."""
    print()
    print(f"  {S.ACC}📷  Camera Filter{S.R}")
    print(f"  {S.FAINT}{'─' * 40}{S.R}")
    print(f"    {S.VAL}1{S.R}  {S.FG}All schools (no filter){S.R}")
    print(f"    {S.VAL}2{S.R}  {S.OK}cam:true  — camera required{S.R}")
    print(f"    {S.VAL}3{S.R}  {S.WARN}cam:false — upload only{S.R}")
    print(f"  {S.FAINT}{'─' * 40}{S.R}")
    choice = input(f"  {S.ACC}>{S.R} Choose [1/2/3] (default=1): ").strip()
    if choice == "2":
        return True
    elif choice == "3":
        return False
    return None


def run_full_auto(session):
    header(t("pipeline_title"), "🚀")
    print()

    cam_filter = _ask_cam_filter()
    print()

    submit_ok = False
    _schools = []

    def on_step(n, title):
        step(n, 10, title)

    def on_log(msg, tag=""):
        tag_clr = {"ok": S.OK, "warn": S.WARN, "err": S.ERR, "info": S.ACC}
        color = tag_clr.get(tag, S.FG)

        for pat in [
            r'(?:Using selected|Auto-random|Auto-pick|Picked):\s*(.+?)(?:\s*\(ID:|$)',
            r'School\s*:\s*(.+)',
            r':\s*(.+?)\s*\(ID:\s*\d+',
        ]:
            m = re.search(pat, msg)
            if m:
                sn = m.group(1).strip().strip('\u2714').strip()
                if sn and len(sn) > 3 and sn not in _schools:
                    _schools.append(sn)

        censored = _censor_text(msg, _schools)

        is_result = tag in ("ok", "err", "warn") or msg.startswith("\n")
        if is_result:
            _clr()
            marker = {
                "ok": f"{S.OK}✓", "warn": f"{S.WARN}!",
                "err": f"{S.ERR}✗",
            }.get(tag, f"{S.ACC}·")
            print(f"    {marker}{S.R}  {color}{censored}{S.R}")
        else:
            _wr(f"    {S.MUTED}·{S.R}  {color}{censored}{S.R}")

    def on_sub(msg):
        _wr(f"    {S.FAINT}›{S.R}  {S.D}{_censor_text(msg, _schools)}{S.R}")

    def ask_existing(count):
        _clr()
        status(t("pipeline_school_found", count=count), "ok")
        return True

    try:
        pipe = core.AutoPipeline(
            session,
            on_step=on_step, on_log=on_log,
            on_sub=on_sub, stop=lambda: False,
            ask_use_existing=ask_existing,
            cam_filter=cam_filter,
        )
        pipe.run()
        submit_ok = True
    except core.AccountNotEligibleError as e:
        _clr()
        print()
        # Display special error for ineligible accounts
        print(f"  {S.BG_ERR}{S.B} {t('pipeline_not_eligible_short')} {S.R}")
        print()
        for line in t("pipeline_not_eligible").split("\n"):
            print(f"  {S.ERR}{line}{S.R}")
        print()
    except Exception as e:
        _clr()
        print()
        status(f"ERROR: {e}", "err")

    return submit_ok


# ══════════════════════════════════════════════════════════════════════════
#  STEP 5 — MONITOR
# ══════════════════════════════════════════════════════════════════════════
def monitor_status(session):
    header(t("monitor_title"), "📊")
    status(t("monitor_watching"), "wait")
    print(f"  {S.FAINT}{t('monitor_ctrlc')}{S.R}")
    print()

    CARD = 8
    first = True
    n = 0

    while True:
        n += 1
        now = datetime.now().strftime("%H:%M:%S")
        _wr(f"  {S.ACC}⟳{S.R}  {S.D}Fetching… #{n}{S.R}")

        try:
            apps = core.get_benefits(session)
        except Exception as e:
            _wr(f"  {S.ERR}✗{S.R}  Error: {e}")
            time.sleep(5)
            continue

        if not apps:
            _wr(f"  {S.WARN}·{S.R}  #{n} — {t('monitor_no_data')}")
            time.sleep(5)
            continue

        app = apps[0]
        st       = app.get("status", "Unknown")
        subm     = app.get("submitted", "—")
        atype    = app.get("type", "—")
        appr_on  = app.get("approved_on", "")
        expires  = app.get("expires", "")
        message  = app.get("message", "")
        progress = app.get("progress", "")

        sl = st.lower()
        if "approved" in sl:
            sc, si, sb = S.OK, "✓", S.BG_OK
        elif "pending" in sl or "review" in sl:
            sc, si, sb = S.WARN, "⟳", S.BG_WRN
        elif "rejected" in sl or "denied" in sl:
            sc, si, sb = S.ERR, "✗", S.BG_ERR
        else:
            sc, si, sb = S.FG, "?", S.BG_BAR

        card_lines = []
        card_lines.append(f"  {S.FAINT}{'─' * 44}{S.R}")
        card_lines.append(f"  {S.ACC}⟳{S.R}  {now}  {S.FAINT}#{n}{S.R}")
        card_lines.append(f"  {sb} {sc}{S.B} {si}  {st} {S.R}")
        card_lines.append(f"     {S.LABEL}Submitted {S.R}  {subm}")
        card_lines.append(f"     {S.LABEL}Type      {S.R}  {atype}")
        if appr_on:
            card_lines.append(f"     {S.LABEL}Approved  {S.R}  {appr_on}")
        if expires:
            card_lines.append(f"     {S.LABEL}Expires   {S.R}  {expires}")
        if progress:
            card_lines.append(f"     {S.LABEL}Progress  {S.R}  {progress}")

        while len(card_lines) < CARD:
            card_lines.append("")

        if not first:
            sys.stdout.write(f"\033[{CARD + 1}A")
        first = False

        for line in card_lines:
            sys.stdout.write(f"\r{S.EL}{line}\n")
        sys.stdout.write(f"\r{S.EL}")
        sys.stdout.flush()

        # final status
        if "approved" in sl:
            print()
            iw = min(W() - 4, 60)
            msg_line = "A P P R O V E D"
            print(f"  {_grad('━' * iw)}")
            pad_ = (iw - len(msg_line) - 6) // 2
            print(f"  {' ' * pad_}{S.B}{_grad('🎉 ' + msg_line + ' 🎉')}{S.R}")
            print(f"  {_grad('━' * iw)}")
            print()
            return True

        if "rejected" in sl or "denied" in sl:
            print()
            iw = min(W() - 4, 60)
            print(f"  {S.ERR}{'━' * iw}{S.R}")
            print(f"  {S.ERR}{S.B}✗  REJECTED{S.R}")
            if message:
                print(f"  {S.MUTED}{t('monitor_rejected_reason', reason=message[:100])}{S.R}")
            print(f"  {S.ERR}{'━' * iw}{S.R}")
            print()
            return True

        # countdown
        try:
            for r in range(5, 0, -1):
                bar = f"{S.ACC}{'━' * r}{S.FAINT}{'╌' * (5 - r)}{S.R}"
                _wr(f"  {bar}  {S.MUTED}{r}s{S.R}")
                time.sleep(1)
        except KeyboardInterrupt:
            _clr()
            print(f"  {S.WARN}{t('monitor_stopped')}{S.R}")
            return True


# ══════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════
def main():
    enable_ansi()

    try:
        cfg = core.load_settings()
        set_language(cfg.get("language", "id"))
    except Exception:
        pass

    while True:
        cls()
        banner()

        # 1 — Login
        try:
            session, cookie = do_login()
        except KeyboardInterrupt:
            print(f"\n\n  {S.MUTED}{t('bye')}{S.R}\n")
            break

        # 2 — Account
        try:
            info = check_user_details(session)
        except Exception as e:
            status(t("failed_generic", error=e), "err")
            input(f"\n  {S.FAINT}{t('press_enter')}{S.R}")
            continue

        # 3 — 2FA
        try:
            ok2 = check_and_setup_2fa(
                session, username=info.get("username", "unknown"),
            )
            if not ok2:
                status(t("tfa_failed_continue"), "warn")
        except KeyboardInterrupt:
            print(f"\n  {S.WARN}{t('cancelled')}{S.R}")
            input(f"\n  {S.FAINT}{t('press_enter')}{S.R}")
            continue

        # 4 — Pipeline
        try:
            sok = run_full_auto(session)
        except KeyboardInterrupt:
            print(f"\n  {S.WARN}{t('stopped')}{S.R}")
            input(f"\n  {S.FAINT}{t('press_enter')}{S.R}")
            continue

        # 5 — Monitor
        if sok:
            try:
                monitor_status(session)
            except KeyboardInterrupt:
                print(f"\n  {S.WARN}{t('monitor_stopped')}{S.R}")
        else:
            print()
            status(t("submit_failed"), "err")

        # loop back
        print()
        sep(t("done_label"))
        print(f"  {S.ACC}{t('back_to_login')}{S.R}")
        sep()
        input(f"\n  {S.FAINT}{t('press_enter')}{S.R}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {S.MUTED}{t('bye')}{S.R}\n")
    except Exception as e:
        print(f"\n  {S.ERR}{t('fatal_error', error=e)}{S.R}")
        input(f"\n  {t('press_enter_exit')}")
