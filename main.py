#!/usr/bin/env python3
"""GitHub Education Benefits Tool — CustomTkinter Modern GUI."""
import os, sys, threading, time, tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import datetime

import customtkinter as ctk

import core

# ── Theme Setup ───────────────────────────────────────────────────────────
_cfg = core.load_settings()
_mode = "dark" if _cfg.get("theme") == "dark" else "light"
ctk.set_appearance_mode(_mode)
ctk.set_default_color_theme("blue")

FNT = "Segoe UI"
TAG_COLORS = {
    "ok": "#22c55e", "err": "#ef4444", "warn": "#f59e0b", "info": "#6366f1",
    "approved": "#22c55e", "pending": "#f59e0b", "rejected": "#ef4444",
    "hdr": "#6366f1", "dim": "#9ca3af", "body": None,
}


# ══════════════════════════════════════════════════════════════════════════
# Spinner Widget — animated Material-style arc
# ══════════════════════════════════════════════════════════════════════════
class Spinner(ctk.CTkFrame):
    """Lightweight canvas-based spinning arc that lives inside a CTkFrame."""

    def __init__(self, master, size=24, width=3, color=None, **kw):
        super().__init__(master, width=size, height=size,
                         fg_color="transparent", **kw)
        self._c = tk.Canvas(self, width=size, height=size,
                            highlightthickness=0, bd=0)
        self._c.pack()
        self._size = size
        self._lw = width
        self._color = color or "#3b82f6"
        self._angle = 0
        self._running = False
        self._sync_bg()

    def _sync_bg(self):
        try:
            bg = self.master.cget("bg")
        except Exception:
            bg = "#2b2b2b"
        self._c.configure(bg=bg)

    def start(self):
        if not self._running:
            self._running = True
            self._sync_bg()
            self._tick()

    def stop(self):
        self._running = False
        self._c.delete("all")

    def _tick(self):
        if not self._running:
            return
        self._c.delete("all")
        pad = self._lw + 1
        self._c.create_arc(pad, pad, self._size - pad, self._size - pad,
                           start=self._angle, extent=80,
                           outline=self._color, width=self._lw, style="arc")
        self._angle = (self._angle + 12) % 360
        self.after(30, self._tick)


# ══════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GitHub Edu Pro Tool \U0001F680 by Dzul")
        self.geometry("820x900")
        self.minsize(720, 620)

        self.session = None
        self.user_info = {}
        self._stop_flag = False
        self._page_history = []
        self._current_page = None
        self._search_qualified = []
        self._ben_apps = []
        self._auto_school_map = {}

        self._build_ui()
        self._show_page("login")

    # ── Reusable helpers ──────────────────────────────────────────────────
    def _card(self, parent, title=None, icon=None):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.pack(fill="x", padx=16, pady=6)
        if title:
            t = f"{icon}  {title}" if icon else title
            ctk.CTkLabel(frame, text=t, font=(FNT, 14, "bold"),
                         anchor="w").pack(fill="x", padx=16, pady=(12, 4))
            sep = ctk.CTkFrame(frame, height=1, fg_color="gray50")
            sep.pack(fill="x", padx=16, pady=(0, 8))
        return frame

    def _entry(self, parent, label, show=None):
        ctk.CTkLabel(parent, text=label, font=(FNT, 11),
                     anchor="w").pack(fill="x", padx=16, pady=(6, 0))
        e = ctk.CTkEntry(parent, font=(FNT, 12), height=38,
                         show=show or "")
        e.pack(fill="x", padx=16, pady=(2, 4))
        return e

    def _info_row(self, parent, label, value="\u2014"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=1)
        ctk.CTkLabel(row, text=f"{label}:", font=(FNT, 11, "bold"),
                     width=120, anchor="w").pack(side="left")
        lbl = ctk.CTkLabel(row, text=value, font=(FNT, 11), anchor="w",
                           wraplength=450)
        lbl.pack(side="left", fill="x", expand=True)
        return lbl

    def _section_title(self, parent, text, icon=None):
        t = f"{icon}  {text}" if icon else text
        ctk.CTkLabel(parent, text=t, font=(FNT, 20, "bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(20, 6))

    def _spinner_row(self, parent, text="Loading..."):
        """Row with spinner + status label.  Returns (frame, spinner, label)."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        sp = Spinner(row, size=22, width=2)
        sp.pack(side="left", padx=(0, 8))
        lbl = ctk.CTkLabel(row, text=text, font=(FNT, 11), anchor="w")
        lbl.pack(side="left", fill="x", expand=True)
        return row, sp, lbl

    def _scrollable(self, parent):
        sf = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        sf.pack(fill="both", expand=True)
        return sf

    # ── Navigation ────────────────────────────────────────────────────────
    def _show_page(self, name):
        if self._current_page and self._current_page != name:
            self._page_history.append(self._current_page)
        self._current_page = name
        for p in self.pages.values():
            p.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        # per-page refresh
        if name == "sessions":
            self._refresh_sessions()
        elif name == "billing":
            self._load_billing_form()
        elif name == "edit_profile":
            self._load_profile_form()
        elif name == "settings":
            self._load_settings_form()
        elif name == "auto":
            self._refresh_school_dropdown()
        elif name == "logs":
            self._refresh_log_view()
        # toolbar buttons
        is_root = name in ("login", "action")
        if is_root:
            self.back_btn.pack_forget()
        else:
            self.back_btn.pack(side="left", padx=(0, 8))
        self.logout_btn.pack_forget()
        if name != "login" and self.session:
            self.logout_btn.pack(side="right", padx=(8, 0))

    def _go_back(self):
        if self._page_history:
            self._current_page = None
            self._show_page(self._page_history.pop())
        else:
            self._show_page("action" if self.session else "login")

    def _logout(self):
        if messagebox.askyesno("Logout", "Logout and return to login page?"):
            self.session = None
            self.user_info = {}
            self._page_history = []
            self.status_lbl.configure(text="Not logged in",
                                       text_color="orange")
            self._show_page("login")

    # ══ Build UI ══════════════════════════════════════════════════════════
    def _build_ui(self):
        # ── Top bar ──
        top = ctk.CTkFrame(self, height=50, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)
        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left", padx=12)
        self.back_btn = ctk.CTkButton(left, text="\u25C2 Back", width=70,
                                       height=32, command=self._go_back,
                                       fg_color="transparent",
                                       text_color=("gray10", "gray90"),
                                       hover_color=("gray80", "gray30"))
        ctk.CTkLabel(top, text="GitHub Edu Pro",
                     font=(FNT, 15, "bold")).pack(side="left", padx=8)
        right = ctk.CTkFrame(top, fg_color="transparent")
        right.pack(side="right", padx=12)
        self.status_lbl = ctk.CTkLabel(right, text="Not logged in",
                                        font=(FNT, 11),
                                        text_color="orange")
        self.status_lbl.pack(side="left", padx=(0, 8))
        self.logout_btn = ctk.CTkButton(right, text="\u23FB Logout", width=80,
                                         height=30, fg_color="#dc2626",
                                         hover_color="#b91c1c",
                                         command=self._logout)

        # ── Page frames ──
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        page_names = ("login", "action", "search", "auto", "sessions",
                      "billing", "profile", "edit_profile", "benefits",
                      "tfa", "settings", "logs")
        self.pages = {}
        for n in page_names:
            self.pages[n] = ctk.CTkFrame(self.container, fg_color="transparent")

        self._build_login()
        self._build_action()
        self._build_search()
        self._build_auto()
        self._build_sessions()
        self._build_billing()
        self._build_profile()
        self._build_edit_profile()
        self._build_benefits()
        self._build_tfa()
        self._build_settings()
        self._build_logs()

    # ── Login Page ────────────────────────────────────────────────────────
    def _build_login(self):
        p = self._scrollable(self.pages["login"])
        self._section_title(p, "Sign In", "\U0001F510")

        c1 = self._card(p, "Login with Cookies", "\U0001F36A")
        self.cookie_entry = self._entry(c1, "Paste cookie string (a=b; c=d)")
        ctk.CTkButton(c1, text="LOGIN WITH COOKIES",
                       command=self._login_cookie, height=40
                       ).pack(padx=16, pady=(4, 12), anchor="w")

        c2 = self._card(p, "Login with Password", "\U0001F511")
        self.user_entry = self._entry(c2, "Username or Email")
        self.pass_entry = self._entry(c2, "Password", show="\u25CF")
        ctk.CTkButton(c2, text="LOGIN WITH PASSWORD",
                       command=self._login_password, height=40
                       ).pack(padx=16, pady=(4, 12), anchor="w")

        c3 = self._card(p, "Saved Sessions", "\U0001F4C1")
        ctk.CTkButton(c3, text="OPEN SESSION MANAGER",
                       command=lambda: self._show_page("sessions"),
                       fg_color="gray40", hover_color="gray50", height=40
                       ).pack(padx=16, pady=(4, 12), anchor="w")

    # ── Dashboard ─────────────────────────────────────────────────────────
    def _build_action(self):
        p = self._scrollable(self.pages["action"])
        self._section_title(p, "Dashboard", "\u26A1")

        ac = self._card(p, "Account Overview", "\U0001F464")
        self.info_labels = {}
        for k, lbl in [("username", "Username"), ("name", "Name"),
                        ("email", "Email"), ("age", "Account Age")]:
            self.info_labels[k] = self._info_row(ac, lbl)
        tfa_row = ctk.CTkFrame(ac, fg_color="transparent")
        tfa_row.pack(fill="x", padx=16, pady=2)
        ctk.CTkLabel(tfa_row, text="2FA:", font=(FNT, 11, "bold"),
                     width=120, anchor="w").pack(side="left")
        self.tfa_status_lbl = ctk.CTkLabel(tfa_row, text="\u2014",
                                            font=(FNT, 11, "bold"), anchor="w")
        self.tfa_status_lbl.pack(side="left")
        ctk.CTkFrame(ac, height=8, fg_color="transparent").pack()

        qc = self._card(p, "Quick Actions", "\U0001F3AF")
        grid = ctk.CTkFrame(qc, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(4, 12))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        buttons = [
            ("\U0001F680 Full Auto",       self._start_full_auto,                   None,      0, 0),
            ("\U0001F50D Search Schools",   lambda: self._show_page("search"),       "gray40",  0, 1),
            ("\u270F\uFE0F Edit Profile",   lambda: self._show_page("edit_profile"), "gray40",  1, 0),
            ("\U0001F4B3 Edit Billing",     lambda: self._show_page("billing"),      "gray40",  1, 1),
            ("\U0001F464 Account Detail",   self._open_profile,                      "gray40",  2, 0),
            ("\U0001F4CB Benefits List",    self._open_benefits,                     "gray40",  2, 1),
            ("\U0001F510 Setup 2FA",        self._open_tfa,                          "gray40",  3, 0),
            ("\U0001F4C1 Sessions",         lambda: self._show_page("sessions"),     "gray40",  3, 1),
            ("\U0001F504 Refresh",          self._refresh_dashboard,                 "gray40",  4, 0),
            ("\u2699\uFE0F Settings",       lambda: self._show_page("settings"),     "gray40",  4, 1),
            ("\U0001F4DC View Logs",        lambda: self._show_page("logs"),         "gray40",  5, 0),
        ]
        for text, cmd, color, row, col in buttons:
            kw = {"fg_color": color, "hover_color": "gray50"} if color else {}
            ctk.CTkButton(grid, text=text, command=cmd, height=44,
                          **kw).grid(row=row, column=col, padx=4,
                                     pady=4, sticky="ew")

    # ── Edit Billing ──────────────────────────────────────────────────────
    def _build_billing(self):
        p = self._scrollable(self.pages["billing"])
        self._section_title(p, "Edit Billing Address", "\U0001F4B3")

        sc = self._card(p, "Status", "\U0001F4E1")
        _, self._bill_spinner, self.bill_status = self._spinner_row(sc, "Loading...")

        c = self._card(p, "Billing Details", "\U0001F4DD")
        self.bill = {}
        for k, lbl in [("first_name", "First Name"), ("last_name", "Last Name"),
                        ("address1", "Address Line 1"), ("address2", "Address Line 2"),
                        ("city", "City"), ("region", "Region / Province"),
                        ("postal_code", "Postal Code"), ("country_code", "Country Code")]:
            self.bill[k] = self._entry(c, lbl)

        br = ctk.CTkFrame(c, fg_color="transparent")
        br.pack(fill="x", padx=16, pady=(8, 12))
        ctk.CTkButton(br, text="\U0001F4BE SAVE BILLING",
                       command=self._submit_billing, width=200, height=42,
                       fg_color="#16a34a", hover_color="#15803d"
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(br, text="\U0001F504 RELOAD",
                       command=self._load_billing_form, width=120, height=42,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left")

    def _load_billing_form(self):
        if not self.session:
            self.bill_status.configure(text="\u26A0 Login first",
                                        text_color="red")
            return
        self.bill_status.configure(text="Loading...", text_color="orange")
        self._bill_spinner.start()

        def worker():
            try:
                data = core.scrape_billing_form(self.session)

                def fill():
                    self._bill_spinner.stop()
                    for k, e in self.bill.items():
                        e.delete(0, "end")
                        v = data.get(k, "")
                        if v:
                            e.insert(0, v)
                    has = any(data.values())
                    txt = "\u2714 Loaded" if has else "\u26A0 No data \u2014 fill manually"
                    clr = "#22c55e" if has else "orange"
                    self.bill_status.configure(text=txt, text_color=clr)

                self.after(0, fill)
            except Exception as exc:
                self.after(0, lambda: [
                    self._bill_spinner.stop(),
                    self.bill_status.configure(
                        text=f"\u2718 {exc}", text_color="red")])

        threading.Thread(target=worker, daemon=True).start()

    def _submit_billing(self):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        addr = {f"billing_contact[{k}]": e.get().strip()
                for k, e in self.bill.items()}

        def worker():
            try:
                core.submit_billing(self.session, addr)
                self.after(0, lambda: [
                    messagebox.showinfo("Success", "Billing address saved!"),
                    self.bill_status.configure(
                        text="\u2714 Saved!", text_color="#22c55e")])
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    # ── Edit Profile ──────────────────────────────────────────────────────
    def _build_edit_profile(self):
        p = self._scrollable(self.pages["edit_profile"])
        self._section_title(p, "Edit Profile", "\u270F\uFE0F")

        sc = self._card(p, "Status", "\U0001F4E1")
        _, self._prof_spinner, self.prof_edit_status = \
            self._spinner_row(sc, "Loading...")

        c = self._card(p, "Profile Details", "\U0001F464")
        self.prof_fields = {}
        for k, lbl in [("name", "Display Name"), ("email", "Public Email"),
                        ("bio", "Bio"), ("pronouns", "Pronouns"),
                        ("website", "Website / URL"),
                        ("company", "Company"), ("location", "Location")]:
            self.prof_fields[k] = self._entry(c, lbl)

        br = ctk.CTkFrame(c, fg_color="transparent")
        br.pack(fill="x", padx=16, pady=(8, 12))
        ctk.CTkButton(br, text="\U0001F4BE UPDATE PROFILE",
                       command=self._submit_profile_edit, width=200, height=42,
                       fg_color="#16a34a", hover_color="#15803d"
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(br, text="\U0001F504 RELOAD",
                       command=self._load_profile_form, width=120, height=42,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left")

    def _load_profile_form(self):
        if not self.session:
            self.prof_edit_status.configure(
                text="\u26A0 Login first", text_color="red")
            return
        self.prof_edit_status.configure(text="Loading...", text_color="orange")
        self._prof_spinner.start()

        def worker():
            try:
                data = core.scrape_profile_form(self.session)

                def fill():
                    self._prof_spinner.stop()
                    for k, e in self.prof_fields.items():
                        e.delete(0, "end")
                        v = data.get(k, "")
                        if v:
                            e.insert(0, v)
                    has = any(data.values())
                    txt = "\u2714 Loaded" if has else "\u26A0 No data"
                    clr = "#22c55e" if has else "orange"
                    self.prof_edit_status.configure(text=txt, text_color=clr)

                self.after(0, fill)
            except Exception as exc:
                self.after(0, lambda: [
                    self._prof_spinner.stop(),
                    self.prof_edit_status.configure(
                        text=f"\u2718 {exc}", text_color="red")])

        threading.Thread(target=worker, daemon=True).start()

    def _submit_profile_edit(self):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        fields = {k: e.get().strip() for k, e in self.prof_fields.items()}

        def worker():
            try:
                core.submit_profile_form(self.session, fields)
                self.user_info["name"] = fields.get("name", "")
                self.after(0, lambda: [
                    messagebox.showinfo("Success", "Profile updated!"),
                    self.prof_edit_status.configure(
                        text="\u2714 Saved", text_color="#22c55e")])
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    # ── Search Page ───────────────────────────────────────────────────────
    def _build_search(self):
        p = self._scrollable(self.pages["search"])
        self._section_title(p, "School Search", "\U0001F50D")

        c1 = self._card(p, "Search Options", "\u2699\uFE0F")
        self.manual_q = self._entry(c1, "Manual keyword (leave empty for auto)")
        r = ctk.CTkFrame(c1, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(r, text="\U0001F50D MANUAL",
                       command=self._manual_search,
                       width=140, height=40).pack(side="left", padx=(0, 6))
        ctk.CTkButton(r, text="\u26A1 AUTO ALL",
                       command=self._auto_search,
                       width=160, height=40, fg_color="gray40",
                       hover_color="gray50").pack(side="left", padx=(0, 6))
        ctk.CTkButton(r, text="\u2B1B STOP", command=self._stop,
                       width=80, height=40, fg_color="#dc2626",
                       hover_color="#b91c1c").pack(side="right")

        pc = self._card(p, "Progress", "\U0001F4CA")
        self.s_status = ctk.CTkLabel(pc, text="Ready", font=(FNT, 11),
                                      anchor="w")
        self.s_status.pack(fill="x", padx=16, pady=2)
        self.s_prog = ctk.CTkProgressBar(pc)
        self.s_prog.pack(fill="x", padx=16, pady=4)
        self.s_prog.set(0)
        self.s_count = ctk.CTkLabel(pc, text="Found: 0 | Qualified: 0",
                                     font=(FNT, 12, "bold"), anchor="w")
        self.s_count.pack(fill="x", padx=16, pady=(2, 8))

        rc = self._card(p, "Qualifying Schools  (click to copy)", "\U0001F3EB")
        self.s_results_list = tk.Listbox(
            rc, height=10, font=(FNT, 10), relief="flat", bd=0,
            activestyle="none")
        self.s_results_list.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        self.s_results_list.bind("<<ListboxSelect>>", self._on_school_click)
        self.s_results_info = ctk.CTkLabel(rc, text="", font=(FNT, 10),
                                            anchor="w")
        self.s_results_info.pack(fill="x", padx=16, pady=(0, 8))

    # ── Auto Page ─────────────────────────────────────────────────────────
    def _build_auto(self):
        p = self._scrollable(self.pages["auto"])
        self._section_title(p, "Full Auto Mode", "\U0001F680")

        # Coordinates
        cc = self._card(p, "Spoof Coordinates", "\U0001F4CD")
        coord_row = ctk.CTkFrame(cc, fg_color="transparent")
        coord_row.pack(fill="x", padx=16, pady=(4, 8))
        ctk.CTkLabel(coord_row, text="Lat:", font=(FNT, 11)).pack(side="left")
        self.auto_lat = ctk.CTkEntry(coord_row, width=140, height=34)
        self.auto_lat.pack(side="left", padx=(4, 12))
        self.auto_lat.insert(0, core.DEFAULT_COORDS["lat"])
        ctk.CTkLabel(coord_row, text="Lon:", font=(FNT, 11)).pack(side="left")
        self.auto_lon = ctk.CTkEntry(coord_row, width=140, height=34)
        self.auto_lon.pack(side="left", padx=(4, 0))
        self.auto_lon.insert(0, core.DEFAULT_COORDS["lon"])
        ctk.CTkLabel(
            cc,
            text="Default: Palembang. Change for custom spoofing.",
            font=(FNT, 10), text_color="gray50"
        ).pack(padx=16, anchor="w", pady=(0, 8))

        # School dropdown
        schc = self._card(p, "School Selection", "\U0001F3EB")
        self._auto_school_var = ctk.StringVar(value="\u26A1 Auto (random)")
        sch_row = ctk.CTkFrame(schc, fg_color="transparent")
        sch_row.pack(fill="x", padx=16, pady=(4, 4))
        self.auto_school_cb = ctk.CTkComboBox(
            sch_row, variable=self._auto_school_var,
            font=(FNT, 11), state="readonly", width=480, height=36)
        self.auto_school_cb.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(sch_row, text="\U0001F504", width=38, height=36,
                       command=self._refresh_school_dropdown,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="right", padx=(8, 0))
        ctk.CTkLabel(
            schc,
            text='Refresh loads schools from daftar_sekolah.txt. '
                 '"Auto" picks randomly.',
            font=(FNT, 10), text_color="gray50", wraplength=500, anchor="w"
        ).pack(padx=16, anchor="w", pady=(0, 8))
        self._refresh_school_dropdown()

        # Progress
        sc = self._card(p, "Progress", "\U0001F4CA")
        self.a_step = ctk.CTkLabel(sc, text="Ready",
                                    font=(FNT, 14, "bold"), anchor="w")
        self.a_step.pack(fill="x", padx=16, pady=(4, 2))
        self.a_prog = ctk.CTkProgressBar(sc, mode="determinate")
        self.a_prog.pack(fill="x", padx=16, pady=4)
        self.a_prog.set(0)
        self.a_sub = ctk.CTkLabel(sc, text="", font=(FNT, 11), anchor="w")
        self.a_sub.pack(fill="x", padx=16, pady=(2, 8))

        # Activity log
        lc = self._card(p, "Activity Log", "\U0001F4DC")
        self.a_log = ctk.CTkTextbox(lc, height=280, font=(FNT, 10),
                                     activate_scrollbars=True)
        self.a_log.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        self.a_log.configure(state="disabled")
        for tag, clr in TAG_COLORS.items():
            if clr:
                self.a_log.tag_config(tag, foreground=clr)

        r = ctk.CTkFrame(lc, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(4, 12))
        self.a_start_btn = ctk.CTkButton(
            r, text="\u25B6 START", command=self._run_auto,
            width=130, height=42,
            fg_color="#16a34a", hover_color="#15803d")
        self.a_start_btn.pack(side="right")
        self.a_stop_btn = ctk.CTkButton(
            r, text="\u2B1B FORCE STOP", command=self._stop,
            width=160, height=42,
            fg_color="#dc2626", hover_color="#b91c1c")
        self.a_stop_btn.pack(side="right", padx=(0, 8))

    # ── Sessions Page ─────────────────────────────────────────────────────
    def _build_sessions(self):
        p = self._scrollable(self.pages["sessions"])
        self._section_title(p, "Session Manager", "\U0001F4C1")

        c = self._card(p, "Saved Sessions", "\U0001F4BE")
        self.sess_list = tk.Listbox(c, height=8, font=(FNT, 10),
                                     relief="flat", bd=0, activestyle="none")
        self.sess_list.pack(fill="x", padx=16, pady=6)
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(r, text="\u2714 USE SELECTED",
                       command=self._use_session,
                       width=170, height=40).pack(side="left", padx=(0, 8))
        ctk.CTkButton(r, text="\U0001F5D1 DELETE",
                       command=self._del_session,
                       width=120, height=40,
                       fg_color="#dc2626", hover_color="#b91c1c"
                       ).pack(side="left")

    def _refresh_sessions(self):
        self.sess_list.delete(0, "end")
        for s in core.load_sessions():
            self.sess_list.insert(
                "end",
                f"  {s['label']}  \u2014  {s.get('created', '?')[:16]}")

    # ── Account Detail ────────────────────────────────────────────────────
    def _build_profile(self):
        p = self._scrollable(self.pages["profile"])
        self._section_title(p, "Account Detail", "\U0001F464")

        c = self._card(p, "Profile Information", "\U0001F4CB")
        self.prof_labels = {}
        for k, lbl in [("username", "Username"), ("name", "Display Name"),
                        ("email", "Email"), ("age", "Account Age"),
                        ("created", "Created"), ("bio", "Bio"),
                        ("company", "Company"), ("location", "Location"),
                        ("website", "Website"), ("public_repos", "Public Repos"),
                        ("followers", "Followers"), ("following", "Following")]:
            self.prof_labels[k] = self._info_row(c, lbl)

        bc = self._card(p, "Billing Address", "\U0001F4B3")
        self.bill_labels = {}
        for k, lbl in [("first_name", "First Name"), ("last_name", "Last Name"),
                        ("address1", "Address"), ("address2", "Address 2"),
                        ("city", "City"), ("region", "Region"),
                        ("postal_code", "Postal Code"),
                        ("country_code", "Country")]:
            self.bill_labels[k] = self._info_row(bc, lbl)

        fc = self._card(p, "Two-Factor Authentication", "\U0001F510")
        self.prof_2fa_lbl = ctk.CTkLabel(fc, text="Checking...",
                                          font=(FNT, 12, "bold"), anchor="w")
        self.prof_2fa_lbl.pack(fill="x", padx=16, pady=4)
        ar = ctk.CTkFrame(fc, fg_color="transparent")
        ar.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(ar, text="\U0001F504 REFRESH",
                       command=self._open_profile,
                       width=120, height=38,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ar, text="\u270F\uFE0F EDIT PROFILE",
                       command=lambda: self._show_page("edit_profile"),
                       width=150, height=38,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(ar, text="\U0001F4B3 EDIT BILLING",
                       command=lambda: self._show_page("billing"),
                       width=150, height=38,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left")

    # ── Benefits Page ─────────────────────────────────────────────────────
    def _build_benefits(self):
        p = self._scrollable(self.pages["benefits"])
        self._section_title(p, "Benefit Applications", "\U0001F4CB")

        sc = self._card(p, "Summary", "\U0001F4CA")
        self.ben_summary = ctk.CTkLabel(sc, text="Loading...",
                                         font=(FNT, 12, "bold"), anchor="w")
        self.ben_summary.pack(fill="x", padx=16, pady=(4, 8))

        lc = self._card(p, "Applications", "\U0001F4E6")
        self.ben_listbox = tk.Listbox(lc, height=8, font=(FNT, 10),
                                       relief="flat", bd=0, activestyle="none")
        self.ben_listbox.pack(fill="x", padx=16, pady=6)
        self.ben_listbox.bind("<<ListboxSelect>>", self._on_benefit_click)

        dc = self._card(p, "Application Detail", "\U0001F4C4")
        self.ben_detail = ctk.CTkTextbox(dc, height=180, font=(FNT, 10),
                                          activate_scrollbars=True)
        self.ben_detail.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        self.ben_detail.configure(state="disabled")
        for tag, clr in TAG_COLORS.items():
            if clr:
                self.ben_detail.tag_config(tag, foreground=clr)
        rb = ctk.CTkFrame(dc, fg_color="transparent")
        rb.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(rb, text="\U0001F504 REFRESH",
                       command=self._open_benefits,
                       width=120, height=38,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left")

    # ── 2FA Page ──────────────────────────────────────────────────────────
    def _build_tfa(self):
        p = self._scrollable(self.pages["tfa"])
        self._section_title(p, "2FA Setup", "\U0001F510")

        sc = self._card(p, "Status", "\U0001F4E1")
        self.tfa_page_status = ctk.CTkLabel(
            sc, text="Checking...", font=(FNT, 13, "bold"), anchor="w")
        self.tfa_page_status.pack(fill="x", padx=16, pady=(4, 8))

        lc = self._card(p, "Setup Log", "\U0001F4DC")
        self.tfa_log = ctk.CTkTextbox(lc, height=200, font=(FNT, 10),
                                       activate_scrollbars=True)
        self.tfa_log.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        self.tfa_log.configure(state="disabled")
        for tag, clr in TAG_COLORS.items():
            if clr:
                self.tfa_log.tag_config(tag, foreground=clr)

        r = ctk.CTkFrame(lc, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(4, 12))
        self.tfa_start_btn = ctk.CTkButton(
            r, text="\u25B6 AUTO SETUP 2FA", command=self._run_tfa_setup,
            width=200, height=42,
            fg_color="#16a34a", hover_color="#15803d")
        self.tfa_start_btn.pack(side="right")

        # ── Results card (setup key + recovery codes) ─────────────────
        rc = self._card(p, "Results", "\U0001F4CB")
        self.tfa_key_lbl = ctk.CTkLabel(
            rc, text="Setup Key: \u2014", font=(FNT, 12, "bold"),
            anchor="w", wraplength=500)
        self.tfa_key_lbl.pack(fill="x", padx=16, pady=(4, 2))

        ctk.CTkLabel(rc, text="Recovery Codes:",
                     font=(FNT, 11, "bold"), anchor="w"
                     ).pack(fill="x", padx=16, pady=(8, 2))
        self.tfa_codes_box = ctk.CTkTextbox(
            rc, height=160, font=("Consolas", 12),
            activate_scrollbars=True)
        self.tfa_codes_box.pack(fill="both", expand=True, padx=16, pady=(2, 4))
        self.tfa_codes_box.insert("1.0", "No data yet \u2014 run setup first.")
        self.tfa_codes_box.configure(state="disabled")

        self.tfa_file_lbl = ctk.CTkLabel(
            rc, text="", font=(FNT, 10), text_color="gray50", anchor="w")
        self.tfa_file_lbl.pack(fill="x", padx=16, pady=(2, 4))

        btn_row = ctk.CTkFrame(rc, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(2, 12))
        self.tfa_open_file_btn = ctk.CTkButton(
            btn_row, text="\U0001F4C2 Open File",
            command=self._open_tfa_file, width=140, height=36,
            state="disabled", fg_color="gray40", hover_color="gray30")
        self.tfa_open_file_btn.pack(side="left")
        self.tfa_saved_path = ""

    # ── Settings Page ─────────────────────────────────────────────────────
    def _build_settings(self):
        p = self._scrollable(self.pages["settings"])
        self._section_title(p, "Settings", "\u2699\uFE0F")

        sc = self._card(p, "Status", "\U0001F4E1")
        self.settings_status = ctk.CTkLabel(sc, text="", font=(FNT, 11),
                                             anchor="w")
        self.settings_status.pack(fill="x", padx=16, pady=(4, 8))

        c1 = self._card(p, "Default Address", "\U0001F4CD")
        self.sett = {}
        for k, lbl in [("default_address", "Address"),
                        ("default_city", "City"),
                        ("default_region", "Region"),
                        ("default_postal", "Postal Code"),
                        ("default_country", "Country Code")]:
            self.sett[k] = self._entry(c1, lbl)
        ctk.CTkFrame(c1, height=6, fg_color="transparent").pack()

        c2 = self._card(p, "Default Coordinates", "\U0001F30D")
        for k, lbl in [("default_lat", "Latitude"),
                        ("default_lon", "Longitude")]:
            self.sett[k] = self._entry(c2, lbl)
        ctk.CTkFrame(c2, height=6, fg_color="transparent").pack()

        c3 = self._card(p, "Automation", "\u26A1")
        for k, lbl in [("document_label", "Document Label"),
                        ("search_delay", "Search Delay (sec)"),
                        ("id_validity_days", "ID Validity (days)")]:
            self.sett[k] = self._entry(c3, lbl)
        ctk.CTkFrame(c3, height=6, fg_color="transparent").pack()

        c4 = self._card(p, "Network", "\U0001F310")
        self.sett_ua_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(c4, text="Rotate User-Agent on each session",
                       variable=self.sett_ua_var, font=(FNT, 12)
                       ).pack(padx=16, pady=(4, 8), anchor="w")

        c5 = self._card(p, "Appearance", "\U0001F3A8")
        self.sett_theme_var = ctk.StringVar(value="light")
        theme_row = ctk.CTkFrame(c5, fg_color="transparent")
        theme_row.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(theme_row, text="Theme:",
                     font=(FNT, 12)).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(theme_row, text="\u2600 Light",
                            variable=self.sett_theme_var, value="light",
                            font=(FNT, 12)).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(theme_row, text="\U0001F319 Dark",
                            variable=self.sett_theme_var, value="dark",
                            font=(FNT, 12)).pack(side="left")
        ctk.CTkLabel(
            c5, text="Theme change takes effect after restart.",
            font=(FNT, 10), text_color="gray50"
        ).pack(padx=16, anchor="w", pady=(0, 8))

        br = ctk.CTkFrame(c5, fg_color="transparent")
        br.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(br, text="\U0001F4BE SAVE SETTINGS",
                       command=self._save_settings, width=200, height=42,
                       fg_color="#16a34a", hover_color="#15803d"
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(br, text="\U0001F504 RELOAD",
                       command=self._load_settings_form, width=120, height=42,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left")

    def _load_settings_form(self):
        cfg = core.load_settings()
        for k, e in self.sett.items():
            e.delete(0, "end")
            v = cfg.get(k, "")
            if v:
                e.insert(0, str(v))
        self.sett_ua_var.set(cfg.get("ua_rotate", True))
        self.sett_theme_var.set(cfg.get("theme", "light"))
        self.settings_status.configure(
            text="\u2714 Settings loaded", text_color="#22c55e")

    def _save_settings(self):
        cfg = core.load_settings()
        for k, e in self.sett.items():
            cfg[k] = e.get().strip()
        cfg["ua_rotate"] = self.sett_ua_var.get()
        cfg["theme"] = self.sett_theme_var.get()
        core.save_settings(cfg)
        self.settings_status.configure(
            text="\u2714 Settings saved!", text_color="#22c55e")
        messagebox.showinfo("Settings", "Settings saved successfully!")

    # ── Log Viewer Page ───────────────────────────────────────────────────
    def _build_logs(self):
        p = self._scrollable(self.pages["logs"])
        self._section_title(p, "Application Log", "\U0001F4DC")

        c = self._card(p, "gh_edu.log", "\U0001F4C4")
        self.log_textbox = ctk.CTkTextbox(
            c, height=500, font=("Consolas", 10), activate_scrollbars=True)
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        self.log_textbox.configure(state="disabled")

        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(r, text="\U0001F504 Refresh",
                       command=self._refresh_log_view,
                       width=120, height=38,
                       fg_color="gray40", hover_color="gray50"
                       ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(r, text="\U0001F5D1 Clear Log",
                       command=self._clear_log,
                       width=120, height=38,
                       fg_color="#dc2626", hover_color="#b91c1c"
                       ).pack(side="left")

    def _refresh_log_view(self):
        content = core.read_log_file()
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.insert("1.0", content)
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def _clear_log(self):
        if messagebox.askyesno("Clear Log", "Clear the log file?"):
            core.clear_log_file()
            self._refresh_log_view()

    # ══ Login Logic ═══════════════════════════════════════════════════════
    def _login_cookie(self):
        ck = self.cookie_entry.get().strip()
        if not ck:
            messagebox.showwarning("Warning", "Cookie empty.")
            return
        self._do_login(lambda: core.login_with_cookie_str(ck), ck)

    def _login_password(self):
        u = self.user_entry.get().strip()
        pw = self.pass_entry.get().strip()
        if not u or not pw:
            messagebox.showwarning("Warning",
                                    "Username and password required.")
            return

        def do():
            s, resp = core.login_with_password(u, pw)
            if resp:
                self.after(0, lambda: self._ask_2fa(s, resp.text))
                return None
            return s

        self.status_lbl.configure(text="Logging in...", text_color="orange")
        threading.Thread(target=self._login_worker, args=(do, None),
                         daemon=True).start()

    def _ask_2fa(self, session, resp_text):
        otp = simpledialog.askstring("2FA Required",
                                      "Enter OTP code:", parent=self)
        if otp:
            core.submit_2fa(session, resp_text, otp)
            self.session = session
            if core.is_logged_in(session):
                self._on_login_ok(None)
            else:
                messagebox.showerror("Error", "Login failed after 2FA.")

    def _do_login(self, fn, cookie_str=None):
        self.status_lbl.configure(text="Logging in...", text_color="orange")
        threading.Thread(target=self._login_worker, args=(fn, cookie_str),
                         daemon=True).start()

    def _login_worker(self, fn, cookie_str):
        try:
            s = fn()
            if s is None:
                return
            self.session = s
            if core.is_logged_in(s):
                self.after(0, lambda: self._on_login_ok(cookie_str))
            else:
                self.after(0, lambda: [
                    messagebox.showerror("Error", "Login failed."),
                    self.status_lbl.configure(
                        text="Login failed", text_color="red")])
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Error", str(exc)))

    def _on_login_ok(self, cookie_str):
        self.status_lbl.configure(
            text="\u2714 Fetching profile...", text_color="#22c55e")

        def fetch():
            info = core.get_profile_details(self.session)
            self.user_info = info
            tfa = False
            try:
                tfa = core.check_2fa_status(self.session)
            except Exception:
                pass
            self.after(0, lambda: self._show_user_info(info, cookie_str, tfa))

        threading.Thread(target=fetch, daemon=True).start()

    def _show_user_info(self, info, cookie_str, tfa):
        uname = info.get("username", "?")
        self.status_lbl.configure(text=f"\u2714 {uname}",
                                   text_color="#22c55e")
        self.info_labels["username"].configure(text=uname)
        self.info_labels["name"].configure(
            text=info.get("name", "\u2014") or "\u2014")
        self.info_labels["email"].configure(
            text=info.get("email", "\u2014") or "\u2014")
        age = info.get("age_days", 0)
        created = info.get("created", "")[:10]
        self.info_labels["age"].configure(
            text=f"{age} days ({created})" if created else f"{age} days")
        if tfa:
            self.tfa_status_lbl.configure(
                text="\u2705 Enabled", text_color="#22c55e")
        else:
            self.tfa_status_lbl.configure(
                text="\u274C Not Enabled", text_color="red")
        if cookie_str:
            if messagebox.askyesno("Save Session",
                                    f"Save session for '{uname}'?"):
                core.add_session(
                    uname or f"session_{datetime.now().strftime('%m%d_%H%M')}",
                    cookie_str)
        self._page_history = []
        self._show_page("action")

    def _refresh_dashboard(self):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        for lbl in self.info_labels.values():
            lbl.configure(text="Loading...")
        self.tfa_status_lbl.configure(text="Checking...",
                                       text_color="gray50")

        def worker():
            try:
                info = core.get_profile_details(self.session)
                self.user_info = info
                tfa = False
                try:
                    tfa = core.check_2fa_status(self.session)
                except Exception:
                    pass

                def update():
                    u = info.get("username", "?")
                    self.info_labels["username"].configure(text=u)
                    self.info_labels["name"].configure(
                        text=info.get("name", "\u2014") or "\u2014")
                    self.info_labels["email"].configure(
                        text=info.get("email", "\u2014") or "\u2014")
                    age = info.get("age_days", 0)
                    c = info.get("created", "")[:10]
                    self.info_labels["age"].configure(
                        text=f"{age} days ({c})" if c else f"{age} days")
                    if tfa:
                        self.tfa_status_lbl.configure(
                            text="\u2705 Enabled", text_color="#22c55e")
                    else:
                        self.tfa_status_lbl.configure(
                            text="\u274C Not Enabled", text_color="red")
                    self.status_lbl.configure(
                        text=f"\u2714 {u} (refreshed)",
                        text_color="#22c55e")

                self.after(0, update)
            except Exception as exc:
                self.after(0, lambda: self.status_lbl.configure(
                    text=f"\u2718 Refresh failed: {exc}", text_color="red"))

        threading.Thread(target=worker, daemon=True).start()

    def _use_session(self):
        sel = self.sess_list.curselection()
        if not sel:
            messagebox.showwarning("Warning", "Select a session.")
            return
        self.status_lbl.configure(text="Verifying...", text_color="orange")

        def worker():
            try:
                s = core.session_from_stored(sel[0])
                self.session = s
                if core.is_logged_in(s):
                    self.after(0, lambda: self._on_login_ok(None))
                else:
                    self.after(0, lambda: messagebox.showerror(
                        "Error", "Session expired."))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror(
                    "Error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _del_session(self):
        sel = self.sess_list.curselection()
        if not sel:
            return
        if messagebox.askyesno("Confirm", "Delete this session?"):
            core.remove_session(sel[0])
            self._refresh_sessions()

    # ── Stop flag ─────────────────────────────────────────────────────────
    def _stop(self):
        self._stop_flag = True

    # ── Search Logic ──────────────────────────────────────────────────────
    def _manual_search(self):
        q = self.manual_q.get().strip()
        if not q:
            messagebox.showwarning("Warning", "Enter a keyword.")
            return
        self._run_search([q])

    def _auto_search(self):
        self._run_search(core.get_all_queries())

    def _run_search(self, queries):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        self._stop_flag = False
        self.s_results_list.delete(0, "end")
        self._search_qualified = []
        self.s_prog.set(0)

        def on_prog(i, t, q):
            self.after(0, lambda: [
                self.s_prog.set(i / t),
                self.s_status.configure(text=f"[{i}/{t}] {q}")])

        def worker():
            af, ql, nq = core.search_schools(
                self.session, queries,
                on_progress=on_prog,
                stop_flag=lambda: self._stop_flag)
            core.save_school_list(ql, nq)
            self.after(0, lambda: self._show_search_done(af, ql))

        threading.Thread(target=worker, daemon=True).start()

    def _show_search_done(self, af, ql):
        self.s_status.configure(
            text="Done!" + (" (stopped)" if self._stop_flag else ""))
        self.s_count.configure(
            text=f"Found: {len(af)} | Qualified: {len(ql)}")
        self.s_results_list.delete(0, "end")
        self._search_qualified = ql
        for i, s in enumerate(ql):
            self.s_results_list.insert(
                "end", f"  {i+1}. {s['name']}  (ID: {s['id']})")
        if not ql:
            self.s_results_list.insert(
                "end", "  No qualifying schools found.")
        self.s_results_info.configure(text="Saved to daftar_sekolah.txt")

    def _on_school_click(self, event):
        sel = self.s_results_list.curselection()
        if not sel or not self._search_qualified:
            return
        idx = sel[0]
        if idx < len(self._search_qualified):
            school = self._search_qualified[idx]
            text = f"{school['name']} (ID: {school['id']})"
            self.clipboard_clear()
            self.clipboard_append(text)
            self.s_results_info.configure(
                text=f"\u2714 Copied: {school['name']}",
                text_color="#22c55e")

    # ══ Auto Flow  (delegates to core.AutoPipeline) ═══════════════════════
    def _alog(self, msg, tag=""):
        def do():
            self.a_log.configure(state="normal")
            self.a_log.insert("end", msg + "\n", tag if tag else ())
            self.a_log.see("end")
            self.a_log.configure(state="disabled")
        self.after(0, do)

    def _astep(self, n, t):
        self.after(0, lambda: [
            self.a_step.configure(text=f"Step {n}/10 \u00B7 {t}"),
            self.a_prog.set(n / 10)])

    def _asub(self, t):
        self.after(0, lambda: self.a_sub.configure(text=t))

    def _refresh_school_dropdown(self):
        auto_label = "\u26A1 Auto (random)"
        self._auto_school_map.clear()
        schools = (core.load_school_list_file()
                   if core.school_list_file_exists() else [])
        values = [auto_label]
        for s in schools:
            display = f"{s['name']}  (ID: {s['id']})"
            values.append(display)
            self._auto_school_map[display] = s
        self.auto_school_cb.configure(values=values)
        self._auto_school_var.set(auto_label)

    def _start_full_auto(self):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        age = self.user_info.get("age_days", 999)
        if age < 3:
            if not messagebox.askyesno(
                    "\u26A0\uFE0F Warning",
                    f"Account is only {age} day(s) old!\n"
                    f"May get rejected.\n\nContinue?"):
                return
        self._show_page("auto")

    def _run_auto(self):
        if not self.session:
            return
        self.a_log.configure(state="normal")
        self.a_log.delete("1.0", "end")
        self.a_log.configure(state="disabled")
        self.a_prog.set(0)
        self._stop_flag = False
        self.a_start_btn.configure(state="disabled")
        threading.Thread(target=self._auto_worker, daemon=True).start()

    def _auto_worker(self):
        try:
            sel_text = self._auto_school_var.get()
            manual = self._auto_school_map.get(sel_text)
            slat = self.auto_lat.get().strip() or None
            slon = self.auto_lon.get().strip() or None

            def ask_use_existing(count):
                result = [None]
                evt = threading.Event()

                def do():
                    result[0] = messagebox.askyesno(
                        "School List",
                        f"Found {count} qualifying schools in file.\n\n"
                        f"Use existing list?")
                    evt.set()

                self.after(0, do)
                while not evt.is_set():
                    if self._stop_flag:
                        evt.set()
                        return False
                    time.sleep(0.05)
                return result[0]

            pipe = core.AutoPipeline(
                self.session,
                spoof_lat=slat, spoof_lon=slon,
                manual_school=manual,
                on_step=self._astep,
                on_log=self._alog,
                on_sub=self._asub,
                stop=lambda: self._stop_flag,
                ask_use_existing=ask_use_existing,
            )
            pipe.run()
        except Exception as exc:
            self._alog(f"\u2718 ERROR: {exc}", "err")
        finally:
            self.after(0, lambda: self.a_start_btn.configure(state="normal"))

    # ══ Profile Logic (read-only view) ════════════════════════════════════
    def _open_profile(self):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        self._show_page("profile")
        for lbl in self.prof_labels.values():
            lbl.configure(text="Loading...")
        for lbl in self.bill_labels.values():
            lbl.configure(text="Loading...")
        self.prof_2fa_lbl.configure(text="Checking...", text_color="gray50")

        def worker():
            try:
                info = core.get_full_profile(self.session)
                self.user_info = info
            except Exception:
                info = {}
            try:
                billing = core.scrape_billing_form(self.session)
            except Exception:
                billing = {}
            try:
                tfa = core.check_2fa_status(self.session)
            except Exception:
                tfa = False

            def update():
                for k, lbl in self.prof_labels.items():
                    v = info.get(k, "\u2014")
                    if k == "age":
                        v = f"{info.get('age_days', 0)} days"
                    elif k == "created":
                        v = info.get("created", "\u2014")[:10]
                    lbl.configure(text=v if v else "\u2014")
                for k, lbl in self.bill_labels.items():
                    lbl.configure(
                        text=billing.get(k, "\u2014") or "\u2014")
                self.prof_2fa_lbl.configure(
                    text=("\u2705 Enabled" if tfa
                          else "\u274C Not Enabled"),
                    text_color="#22c55e" if tfa else "red")

            self.after(0, update)

        threading.Thread(target=worker, daemon=True).start()

    # ══ Benefits Logic ════════════════════════════════════════════════════
    def _open_benefits(self):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        self._show_page("benefits")
        self.ben_summary.configure(text="Loading...")
        self.ben_listbox.delete(0, "end")
        self.ben_detail.configure(state="normal")
        self.ben_detail.delete("1.0", "end")
        self.ben_detail.configure(state="disabled")

        def worker():
            apps = core.get_benefits(self.session)
            self.after(0, lambda: self._display_benefits(apps))

        threading.Thread(target=worker, daemon=True).start()

    def _display_benefits(self, apps):
        self._ben_apps = apps
        self.ben_listbox.delete(0, "end")
        if not apps:
            self.ben_summary.configure(text="No applications found.")
            return
        ap = sum(1 for a in apps if "approved" in a["status"].lower())
        pn = sum(1 for a in apps if "pending" in a["status"].lower())
        rj = sum(1 for a in apps
                 if "rejected" in a["status"].lower()
                 or "denied" in a["status"].lower())
        self.ben_summary.configure(
            text=f"Total: {len(apps)}  \u00B7  \u2714 {ap}  \u00B7  "
                 f"\u23F3 {pn}  \u00B7  \u2718 {rj}")
        for i, app in enumerate(apps):
            st = app["status"]
            icon = ("\u2705" if "approved" in st.lower()
                    else ("\u274C" if "rejected" in st.lower()
                          or "denied" in st.lower() else "\u23F3"))
            self.ben_listbox.insert(
                "end",
                f"  {icon}  #{i+1}  {st}  \u2014  {app.get('submitted', '')}")

    def _on_benefit_click(self, event):
        sel = self.ben_listbox.curselection()
        if not sel or not self._ben_apps:
            return
        app = self._ben_apps[sel[0]]
        self.ben_detail.configure(state="normal")
        self.ben_detail.delete("1.0", "end")
        st = app["status"]
        tag = ("approved" if "approved" in st.lower()
               else ("rejected" if "rejected" in st.lower()
                     or "denied" in st.lower() else "pending"))
        self.ben_detail.insert("end", f"{st}\n", tag)
        self.ben_detail.insert("end", f"{'=' * 45}\n\n", "dim")
        for key, label in [("submitted", "Submitted"), ("type", "Type"),
                           ("approved_on", "Date"), ("expires", "Expires")]:
            if app.get(key):
                self.ben_detail.insert("end", f"{label}: ", "hdr")
                self.ben_detail.insert("end", f"{app[key]}\n")
        if app.get("message"):
            self.ben_detail.insert("end", f"\n{chr(0x2500) * 45}\n", "dim")
            self.ben_detail.insert("end", f"{app['message']}\n")
        self.ben_detail.configure(state="disabled")

    # ══ 2FA Logic ═════════════════════════════════════════════════════════
    def _open_tfa(self):
        if not self.session:
            messagebox.showwarning("Warning", "Login first!")
            return
        self.tfa_log.configure(state="normal")
        self.tfa_log.delete("1.0", "end")
        self.tfa_log.configure(state="disabled")
        self.tfa_page_status.configure(text="Checking...",
                                        text_color="gray50")

        def worker():
            enabled = core.check_2fa_status(self.session)
            if enabled:
                self.after(0, lambda: [
                    messagebox.showinfo("2FA", "2FA is already enabled."),
                    self.tfa_status_lbl.configure(
                        text="\u2705 Enabled", text_color="#22c55e")])
            else:
                self.after(0, lambda: [
                    self._show_page("tfa"),
                    self.tfa_page_status.configure(
                        text="\u274C Not Enabled \u2014 Ready to setup",
                        text_color="orange"),
                    self._tfa_log_write(
                        "Click START SETUP to begin.\n", "warn")])

        threading.Thread(target=worker, daemon=True).start()

    def _tfa_log_write(self, msg, tag=""):
        self.tfa_log.configure(state="normal")
        self.tfa_log.insert("end", msg + "\n", tag if tag else ())
        self.tfa_log.see("end")
        self.tfa_log.configure(state="disabled")

    def _run_tfa_setup(self):
        if not self.session:
            return
        self.tfa_start_btn.configure(state="disabled")
        self.tfa_log.configure(state="normal")
        self.tfa_log.delete("1.0", "end")
        self.tfa_log.configure(state="disabled")

        def log_msg(msg):
            self.after(0, lambda: self._tfa_log_write(msg, "info"))

        def worker():
            try:
                result = core.setup_2fa(
                    self.session, on_log=log_msg)

                def done():
                    self.tfa_page_status.configure(
                        text="\u2705 2FA Setup Complete!",
                        text_color="#22c55e")
                    # Update action page status
                    self.tfa_status_lbl.configure(
                        text="\u2705 Enabled", text_color="#22c55e")

                    # Show results
                    self.tfa_key_lbl.configure(
                        text=f"Setup Key: {result['setup_key']}")
                    self.tfa_codes_box.configure(state="normal")
                    self.tfa_codes_box.delete("1.0", "end")
                    codes = result.get("recovery_codes", [])
                    if codes:
                        for i, code in enumerate(codes, 1):
                            self.tfa_codes_box.insert(
                                "end", f"  {i:2d}. {code}\n")
                    else:
                        self.tfa_codes_box.insert(
                            "1.0",
                            "Recovery codes not extracted.\n"
                            "Check GitHub Settings > Security\n"
                            "to view your recovery codes.")
                    self.tfa_codes_box.configure(state="disabled")

                    # File path
                    saved = result.get("saved_to", "")
                    if saved:
                        self.tfa_saved_path = saved
                        self.tfa_file_lbl.configure(
                            text=f"\U0001F4BE Saved: {os.path.basename(saved)}")
                        self.tfa_open_file_btn.configure(
                            state="normal",
                            fg_color="#2563eb",
                            hover_color="#1d4ed8")

                    # Summary log
                    self._tfa_log_write("\n" + "=" * 45, "ok")
                    self._tfa_log_write(
                        f"  Setup Key : {result['setup_key']}", "ok")
                    if codes:
                        self._tfa_log_write(
                            f"  Recovery  : {len(codes)} codes saved", "ok")
                    self._tfa_log_write(
                        f"  File      : "
                        f"{os.path.basename(saved)}", "ok")
                    self._tfa_log_write("=" * 45, "ok")

                    # Copy to clipboard in formatted text
                    username = self.user_info.get("username", "?")
                    codes_text = "\n".join(codes) if codes else "(not available)"
                    clip_text = (
                        f"*GitHub Students Dev Pack*\n"
                        f"Username: {username}\n"
                        f"Password: \n"
                        f"F2A: {result['setup_key']}\n"
                        f"\n"
                        f"Recovery Codes:\n"
                        f"{codes_text}"
                    )
                    self.clipboard_clear()
                    self.clipboard_append(clip_text)
                    self._tfa_log_write(
                        "\n📋 Copied to clipboard!", "ok")

                    messagebox.showinfo(
                        "2FA Setup Complete",
                        f"\u2705 2FA has been enabled!\n\n"
                        f"Setup Key: {result['setup_key']}\n"
                        f"Recovery Codes: {len(codes)} saved\n\n"
                        f"File: {os.path.basename(saved)}\n\n"
                        f"📋 Copied to clipboard — ready to paste!")

                self.after(0, done)
            except Exception as exc:
                self.after(0, lambda: [
                    self._tfa_log_write(f"\u2718 ERROR: {exc}", "err"),
                    self.tfa_page_status.configure(
                        text="\u274C Failed", text_color="red")])
            finally:
                self.after(0, lambda: self.tfa_start_btn.configure(
                    state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _open_tfa_file(self):
        """Open the saved 2FA file with the default text editor."""
        if self.tfa_saved_path and os.path.exists(self.tfa_saved_path):
            os.startfile(self.tfa_saved_path)


# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
