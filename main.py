"""
VaultGuard - Main GUI Application
Beautiful dark-themed Tkinter UI for the password manager.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import pyperclip_fallback as clipboard
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from analyzer import analyze
from generator import generate_password, generate_passphrase, generate_pin
from rotate import get_rotation_status, engine as rotation_engine
import vault as db

# ─── Color Palette ────────────────────────────────────────────────────────────
BG_DARK    = "#0D1117"   # Main background (GitHub dark)
BG_PANEL   = "#161B22"   # Sidebar / panel background
BG_CARD    = "#1C2128"   # Card / entry background
BG_HOVER   = "#21262D"   # Hover state
ACCENT     = "#58A6FF"   # Blue accent
ACCENT2    = "#3FB950"   # Green accent
WARN       = "#D29922"   # Yellow warning
DANGER     = "#F85149"   # Red danger
TEXT_PRI   = "#E6EDF3"   # Primary text
TEXT_SEC   = "#8B949E"   # Secondary text
TEXT_DIM   = "#484F58"   # Dimmed text
BORDER     = "#30363D"   # Border color
PURPLE     = "#BC8CFF"   # Purple accent
CYAN       = "#39D353"   # Cyan

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_HEAD   = ("Segoe UI", 14, "bold")
FONT_BODY   = ("Segoe UI", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 12)
FONT_MONO_S = ("Consolas", 10)

# ─── Utility Widgets ──────────────────────────────────────────────────────────

class RoundedFrame(tk.Frame):
    def __init__(self, parent, bg=BG_CARD, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)


def make_label(parent, text, font=FONT_BODY, fg=TEXT_PRI, bg=BG_DARK, **kwargs):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kwargs)


def make_button(parent, text, command, bg=ACCENT, fg="white",
                font=FONT_BODY, padx=16, pady=8, **kwargs):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, font=font,
        relief="flat", cursor="hand2",
        activebackground=BG_HOVER, activeforeground=TEXT_PRI,
        padx=padx, pady=pady, bd=0, **kwargs
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=_lighten(bg)))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _lighten(hex_color: str) -> str:
    """Slightly lighten a hex color for hover effect."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = min(255, r + 25)
    g = min(255, g + 25)
    b = min(255, b + 25)
    return f"#{r:02x}{g:02x}{b:02x}"


def make_entry(parent, show=None, font=FONT_MONO, width=30, **kwargs):
    e = tk.Entry(
        parent, font=font, bg=BG_CARD, fg=TEXT_PRI,
        insertbackground=ACCENT, relief="flat",
        highlightthickness=1, highlightcolor=ACCENT,
        highlightbackground=BORDER, show=show, width=width, **kwargs
    )
    return e


def separator(parent, bg=BORDER, height=1):
    return tk.Frame(parent, bg=bg, height=height)


# ─── Setup / Login Screen ─────────────────────────────────────────────────────

class SetupScreen(tk.Frame):
    def __init__(self, parent, on_complete):
        super().__init__(parent, bg=BG_DARK)
        self.on_complete = on_complete
        self._build()

    def _build(self):
        # Center content
        center = tk.Frame(self, bg=BG_DARK)
        center.place(relx=0.5, rely=0.5, anchor="center")

        # Logo area
        tk.Label(center, text="🔐", font=("Segoe UI", 48), bg=BG_DARK, fg=ACCENT).pack(pady=(0, 8))
        tk.Label(center, text="VaultGuard", font=("Segoe UI", 32, "bold"),
                 bg=BG_DARK, fg=TEXT_PRI).pack()
        tk.Label(center, text="Your encrypted password fortress",
                 font=FONT_BODY, bg=BG_DARK, fg=TEXT_SEC).pack(pady=(4, 32))

        # Card
        card = tk.Frame(center, bg=BG_PANEL, padx=40, pady=36)
        card.pack(ipadx=10)
        card.config(highlightthickness=1, highlightbackground=BORDER)

        is_new = not db.is_vault_initialized()
        title_text = "Create Master Password" if is_new else "Unlock Your Vault"
        tk.Label(card, text=title_text, font=FONT_HEAD, bg=BG_PANEL, fg=TEXT_PRI).pack(anchor="w")
        tk.Label(card, text="This password encrypts all your stored passwords.",
                 font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_SEC).pack(anchor="w", pady=(4, 20))

        # Password field
        pw_frame = tk.Frame(card, bg=BG_PANEL)
        pw_frame.pack(fill="x")
        tk.Label(pw_frame, text="Master Password", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_SEC).pack(anchor="w")
        self.pw_var = tk.StringVar()
        self.pw_entry = make_entry(pw_frame, show="●", width=32, textvariable=self.pw_var)
        self.pw_entry.pack(fill="x", ipady=8, pady=(4, 16))
        self.pw_entry.bind("<Return>", lambda e: self._submit())

        if is_new:
            tk.Label(pw_frame, text="Confirm Password", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_SEC).pack(anchor="w")
            self.confirm_var = tk.StringVar()
            self.confirm_entry = make_entry(pw_frame, show="●", width=32, textvariable=self.confirm_var)
            self.confirm_entry.pack(fill="x", ipady=8, pady=(4, 0))
            self.confirm_entry.bind("<Return>", lambda e: self._submit())

            # Strength bar for master pw
            self.strength_frame = tk.Frame(pw_frame, bg=BG_PANEL)
            self.strength_frame.pack(fill="x", pady=(8, 0))
            self.strength_label = tk.Label(self.strength_frame, text="", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_SEC)
            self.strength_label.pack(anchor="w")
            self.strength_bar = tk.Canvas(self.strength_frame, height=4, bg=BG_CARD, highlightthickness=0)
            self.strength_bar.pack(fill="x", pady=(4, 0))
            self.pw_var.trace("w", self._update_strength)
        else:
            self.confirm_var = None

        self.error_label = tk.Label(card, text="", font=FONT_SMALL, bg=BG_PANEL, fg=DANGER)
        self.error_label.pack(pady=(12, 0))

        btn_text = "Create Vault" if is_new else "Unlock Vault"
        btn = make_button(card, btn_text, self._submit, bg=ACCENT, pady=10)
        btn.pack(fill="x", pady=(16, 0))
        btn.config(font=("Segoe UI", 12, "bold"))

        tk.Label(card, text="AES-256 encrypted · PBKDF2 key derivation · Local only",
                 font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack(pady=(16, 0))

        self.pw_entry.focus_set()

    def _update_strength(self, *_):
        pw = self.pw_var.get()
        if not pw:
            self.strength_label.config(text="")
            self.strength_bar.delete("all")
            return
        result = analyze(pw)
        width = self.strength_bar.winfo_width() or 300
        self.strength_bar.delete("all")
        fill_w = int(width * result.score / 100)
        self.strength_bar.create_rectangle(0, 0, fill_w, 4, fill=result.color, outline="")
        self.strength_label.config(text=f"Strength: {result.strength}  ({result.score}/100)", fg=result.color)

    def _submit(self):
        pw = self.pw_var.get()
        if not pw:
            self.error_label.config(text="Password cannot be empty")
            return

        is_new = not db.is_vault_initialized()

        if is_new:
            confirm = self.confirm_var.get()
            if pw != confirm:
                self.error_label.config(text="Passwords do not match")
                return
            result = analyze(pw)
            if result.score < 30:
                self.error_label.config(text="Master password is too weak. Please use a stronger one.")
                return
            db.init_db()
            db.setup_master_password(pw)
            self.on_complete(pw)
        else:
            if db.unlock_vault(pw):
                self.on_complete(pw)
            else:
                self.error_label.config(text="Incorrect master password")
                self.pw_entry.delete(0, tk.END)


# ─── Main Application ─────────────────────────────────────────────────────────

class VaultGuardApp(tk.Frame):
    def __init__(self, parent, master_password: str):
        super().__init__(parent, bg=BG_DARK)
        self.master_password = master_password
        self.entries = []
        self.selected_entry = None
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._filter_entries)
        self._build()
        self._load_entries()
        self._start_rotation_engine()

    def _build(self):
        self.pack(fill="both", expand=True)

        # ── Sidebar ──
        self.sidebar = tk.Frame(self, bg=BG_PANEL, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # ── Main content ──
        self.content = tk.Frame(self, bg=BG_DARK)
        self.content.pack(side="left", fill="both", expand=True)

        # Top bar
        self._build_topbar()

        # Notebook pages
        self.notebook = ttk.Notebook(self.content)
        self._style_notebook()
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # Tabs
        self.tab_vault     = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_generator = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_analyzer  = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_rotation  = tk.Frame(self.notebook, bg=BG_DARK)

        self.notebook.add(self.tab_vault,     text="  🗄  Vault  ")
        self.notebook.add(self.tab_generator, text="  ⚡  Generator  ")
        self.notebook.add(self.tab_analyzer,  text="  🔍  Analyzer  ")
        self.notebook.add(self.tab_rotation,  text="  🔄  Rotation  ")

        self._build_vault_tab()
        self._build_generator_tab()
        self._build_analyzer_tab()
        self._build_rotation_tab()

    def _style_notebook(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=TEXT_SEC,
                        padding=[16, 8], font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_DARK)],
                  foreground=[("selected", ACCENT)])

    def _build_sidebar(self):
        sb = self.sidebar

        # Logo
        logo_frame = tk.Frame(sb, bg=BG_PANEL, pady=20)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="🔐 VaultGuard", font=("Segoe UI", 14, "bold"),
                 bg=BG_PANEL, fg=ACCENT).pack()
        tk.Label(logo_frame, text="Password Manager", font=FONT_SMALL,
                 bg=BG_PANEL, fg=TEXT_DIM).pack()

        separator(sb).pack(fill="x")

        # Stats dashboard
        self.stat_frame = tk.Frame(sb, bg=BG_PANEL, pady=12, padx=14)
        self.stat_frame.pack(fill="x")
        tk.Label(self.stat_frame, text="VAULT SUMMARY", font=("Segoe UI", 8, "bold"),
                 bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w")

        self.stat_total = self._stat_row(self.stat_frame, "Total Entries", "0", TEXT_PRI)
        self.stat_strong = self._stat_row(self.stat_frame, "Strong", "0", ACCENT2)
        self.stat_weak = self._stat_row(self.stat_frame, "Weak", "0", DANGER)
        self.stat_overdue = self._stat_row(self.stat_frame, "Rotation Due", "0", WARN)

        separator(sb).pack(fill="x")

        # Category filter
        filter_frame = tk.Frame(sb, bg=BG_PANEL, pady=12, padx=14)
        filter_frame.pack(fill="x")
        tk.Label(filter_frame, text="CATEGORIES", font=("Segoe UI", 8, "bold"),
                 bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w", pady=(0, 8))

        self.category_var = tk.StringVar(value="All")
        categories = ["All", "General", "Social", "Work", "Finance", "Email", "Other"]
        for cat in categories:
            btn = tk.Button(
                filter_frame, text=f"  {cat}", font=FONT_SMALL,
                bg=BG_PANEL, fg=TEXT_SEC, relief="flat",
                anchor="w", cursor="hand2",
                command=lambda c=cat: self._filter_by_category(c)
            )
            btn.pack(fill="x", ipady=4)
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=ACCENT))
            btn.bind("<Leave>", lambda e, b=btn: b.config(fg=TEXT_SEC))

        separator(sb).pack(fill="x", side="bottom")
        tk.Label(sb, text="🔒 All data encrypted locally",
                 font=("Segoe UI", 8), bg=BG_PANEL, fg=TEXT_DIM,
                 pady=8).pack(side="bottom")

    def _stat_row(self, parent, label, value, color):
        f = tk.Frame(parent, bg=BG_PANEL)
        f.pack(fill="x", pady=2)
        tk.Label(f, text=label, font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_SEC).pack(side="left")
        lbl = tk.Label(f, text=value, font=("Segoe UI", 10, "bold"), bg=BG_PANEL, fg=color)
        lbl.pack(side="right")
        return lbl

    def _build_topbar(self):
        bar = tk.Frame(self.content, bg=BG_PANEL, pady=10, padx=16)
        bar.pack(fill="x")

        # Search
        search_frame = tk.Frame(bar, bg=BG_CARD, padx=8)
        search_frame.pack(side="left")
        search_frame.config(highlightthickness=1, highlightbackground=BORDER)
        tk.Label(search_frame, text="🔍", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_SEC).pack(side="left")
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                font=FONT_BODY, bg=BG_CARD, fg=TEXT_PRI,
                                insertbackground=ACCENT, relief="flat",
                                width=28)
        search_entry.pack(side="left", ipady=6, padx=4)
        tk.Label(search_frame, text="Search vault...", font=FONT_SMALL,
                 bg=BG_CARD, fg=TEXT_DIM).pack(side="left")
        search_entry.bind("<FocusIn>", lambda e: search_frame.config(highlightbackground=ACCENT))
        search_entry.bind("<FocusOut>", lambda e: search_frame.config(highlightbackground=BORDER))

        # Right side buttons
        make_button(bar, "+ Add Password", self._open_add_dialog, bg=ACCENT,
                    padx=14, pady=6).pack(side="right", padx=4)
        make_button(bar, "⟳ Refresh", self._load_entries, bg=BG_CARD,
                    fg=TEXT_SEC, padx=10, pady=6).pack(side="right", padx=4)

    # ── Vault Tab ──────────────────────────────────────────────────────────────

    def _build_vault_tab(self):
        tab = self.tab_vault

        # Table header
        header = tk.Frame(tab, bg=BG_PANEL)
        header.pack(fill="x", padx=16, pady=(12, 0))
        cols = [("Title", 200), ("Username", 180), ("Category", 120),
                ("Strength", 120), ("Last Rotated", 160), ("Actions", 140)]
        for col, w in cols:
            tk.Label(header, text=col, font=("Segoe UI", 9, "bold"),
                     bg=BG_PANEL, fg=TEXT_DIM, width=w//8).pack(side="left", padx=4)

        separator(tab, height=1).pack(fill="x", padx=16, pady=4)

        # Scrollable entry list
        container = tk.Frame(tab, bg=BG_DARK)
        container.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        canvas = tk.Canvas(container, bg=BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.entry_list_frame = tk.Frame(canvas, bg=BG_DARK)

        self.entry_list_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.entry_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        self.vault_canvas = canvas

    def _render_entries(self, entries):
        for widget in self.entry_list_frame.winfo_children():
            widget.destroy()

        if not entries:
            tk.Label(self.entry_list_frame, text="No entries found",
                     font=FONT_BODY, bg=BG_DARK, fg=TEXT_DIM).pack(pady=40)
            return

        for entry in entries:
            self._render_entry_row(entry)

    def _render_entry_row(self, entry):
        frame = tk.Frame(self.entry_list_frame, bg=BG_CARD, pady=10, padx=12)
        frame.pack(fill="x", pady=3)
        frame.config(highlightthickness=1, highlightbackground=BORDER)

        def on_enter(e): frame.config(bg=BG_HOVER, highlightbackground=ACCENT)
        def on_leave(e): frame.config(bg=BG_CARD, highlightbackground=BORDER)
        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)

        score = entry.get("strength_score", 0)
        if score >= 65:
            strength_color, strength_label = ACCENT2, "Strong"
        elif score >= 40:
            strength_color, strength_label = WARN, "Fair"
        else:
            strength_color, strength_label = DANGER, "Weak"

        # Left: icon + title + username
        left = tk.Frame(frame, bg=BG_CARD)
        left.pack(side="left", fill="x", expand=True)
        left.bind("<Enter>", on_enter); left.bind("<Leave>", on_leave)

        cat_icons = {"Social": "👥", "Work": "💼", "Finance": "💰",
                     "Email": "📧", "General": "🔑", "Other": "📦"}
        icon = cat_icons.get(entry.get("category", "General"), "🔑")
        tk.Label(left, text=icon, font=("Segoe UI", 14), bg=BG_CARD, fg=TEXT_PRI).pack(side="left", padx=(0,8))
        left.bind("<Enter>", on_enter); left.bind("<Leave>", on_leave)

        info = tk.Frame(left, bg=BG_CARD)
        info.pack(side="left")
        info.bind("<Enter>", on_enter); info.bind("<Leave>", on_leave)
        tk.Label(info, text=entry["title"], font=("Segoe UI", 11, "bold"),
                 bg=BG_CARD, fg=TEXT_PRI, anchor="w").pack(anchor="w")
        tk.Label(info, text=entry.get("username", ""), font=FONT_SMALL,
                 bg=BG_CARD, fg=TEXT_SEC, anchor="w").pack(anchor="w")

        # Category
        cat_frame = tk.Frame(frame, bg=BG_CARD, width=100)
        cat_frame.pack(side="left", padx=12)
        cat_frame.pack_propagate(False)
        tk.Label(cat_frame, text=entry.get("category", "General"),
                 font=FONT_SMALL, bg=BG_CARD, fg=TEXT_SEC).pack(anchor="center")

        # Strength badge
        badge_frame = tk.Frame(frame, bg=BG_CARD, width=100)
        badge_frame.pack(side="left", padx=4)
        badge_frame.pack_propagate(False)
        tk.Label(badge_frame, text=f"● {strength_label}",
                 font=FONT_SMALL, bg=BG_CARD, fg=strength_color).pack(anchor="center")

        # Last rotated
        rot_frame = tk.Frame(frame, bg=BG_CARD, width=150)
        rot_frame.pack(side="left", padx=4)
        rot_frame.pack_propagate(False)
        rot_status = entry.get("rotation_status_label", "")
        rot_color = {"overdue": DANGER, "warning": WARN, "ok": TEXT_SEC}.get(
            entry.get("rotation_status", "ok"), TEXT_SEC)
        tk.Label(rot_frame, text=rot_status, font=FONT_SMALL,
                 bg=BG_CARD, fg=rot_color).pack(anchor="center")

        # Action buttons
        btn_frame = tk.Frame(frame, bg=BG_CARD)
        btn_frame.pack(side="right")

        entry_id = entry["id"]
        pw = entry["password"]

        def copy_pw(eid=entry_id, p=pw):
            try:
                self.clipboard_clear()
                self.clipboard_append(p)
                self.update()
                self._flash_status("✓ Password copied to clipboard")
            except Exception:
                self._flash_status("Copy failed — see details view")

        def edit_entry(e=entry):
            self._open_edit_dialog(e)

        def del_entry(eid=entry_id, title=entry["title"]):
            if messagebox.askyesno("Delete Entry",
                                   f"Delete '{title}'?\nThis cannot be undone."):
                db.delete_entry(eid)
                self._load_entries()

        def view_entry(e=entry):
            self._open_view_dialog(e)

        tk.Button(btn_frame, text="👁", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_SEC,
                  relief="flat", cursor="hand2", command=view_entry).pack(side="left", padx=2)
        tk.Button(btn_frame, text="📋", font=FONT_SMALL, bg=BG_CARD, fg=ACCENT,
                  relief="flat", cursor="hand2", command=copy_pw).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏", font=FONT_SMALL, bg=BG_CARD, fg=WARN,
                  relief="flat", cursor="hand2", command=edit_entry).pack(side="left", padx=2)
        tk.Button(btn_frame, text="🗑", font=FONT_SMALL, bg=BG_CARD, fg=DANGER,
                  relief="flat", cursor="hand2", command=del_entry).pack(side="left", padx=2)

    # ── Generator Tab ──────────────────────────────────────────────────────────

    def _build_generator_tab(self):
        tab = self.tab_generator
        outer = tk.Frame(tab, bg=BG_DARK)
        outer.pack(fill="both", expand=True, padx=32, pady=24)

        tk.Label(outer, text="Password Generator", font=FONT_TITLE,
                 bg=BG_DARK, fg=TEXT_PRI).pack(anchor="w")
        tk.Label(outer, text="Generate cryptographically secure passwords",
                 font=FONT_BODY, bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w", pady=(2, 20))

        # Two column layout
        cols = tk.Frame(outer, bg=BG_DARK)
        cols.pack(fill="both", expand=True)

        # Left: settings
        left = tk.Frame(cols, bg=BG_PANEL, padx=24, pady=20)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.config(highlightthickness=1, highlightbackground=BORDER)

        tk.Label(left, text="Type", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w")
        self.gen_type = tk.StringVar(value="random")
        types = [("Random", "random"), ("Passphrase", "passphrase"),
                 ("Memorable", "memorable"), ("PIN", "pin")]
        for label, val in types:
            tk.Radiobutton(left, text=label, variable=self.gen_type, value=val,
                           bg=BG_PANEL, fg=TEXT_PRI, selectcolor=BG_CARD,
                           activebackground=BG_PANEL, font=FONT_BODY).pack(anchor="w")

        separator(left).pack(fill="x", pady=12)

        tk.Label(left, text="Length", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w")
        self.length_var = tk.IntVar(value=18)
        length_frame = tk.Frame(left, bg=BG_PANEL)
        length_frame.pack(fill="x")
        self.length_label = tk.Label(length_frame, text="18", font=("Segoe UI", 12, "bold"),
                                     bg=BG_PANEL, fg=ACCENT, width=3)
        self.length_label.pack(side="right")
        length_scale = tk.Scale(length_frame, variable=self.length_var, from_=6, to=64,
                                orient="horizontal", bg=BG_PANEL, fg=TEXT_PRI,
                                troughcolor=BG_CARD, highlightthickness=0, showvalue=False,
                                command=lambda v: self.length_label.config(text=str(int(float(v)))))
        length_scale.pack(side="left", fill="x", expand=True)

        separator(left).pack(fill="x", pady=12)
        tk.Label(left, text="Options", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w", pady=(0,4))

        self.opt_upper   = tk.BooleanVar(value=True)
        self.opt_lower   = tk.BooleanVar(value=True)
        self.opt_digits  = tk.BooleanVar(value=True)
        self.opt_special = tk.BooleanVar(value=True)
        self.opt_noambig = tk.BooleanVar(value=False)

        opts = [("Uppercase (A-Z)", self.opt_upper), ("Lowercase (a-z)", self.opt_lower),
                ("Digits (0-9)", self.opt_digits), ("Symbols (!@#...)", self.opt_special),
                ("Exclude ambiguous (I,l,1,O)", self.opt_noambig)]
        for lbl, var in opts:
            tk.Checkbutton(left, text=lbl, variable=var, bg=BG_PANEL, fg=TEXT_PRI,
                           selectcolor=BG_CARD, activebackground=BG_PANEL,
                           font=FONT_SMALL).pack(anchor="w")

        make_button(left, "⚡ Generate", self._do_generate, bg=ACCENT,
                    pady=10).pack(fill="x", pady=(20, 0))

        # Right: output
        right = tk.Frame(cols, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True)

        # Generated password display
        pw_card = tk.Frame(right, bg=BG_PANEL, padx=20, pady=20)
        pw_card.pack(fill="x")
        pw_card.config(highlightthickness=1, highlightbackground=BORDER)

        tk.Label(pw_card, text="Generated Password", font=FONT_SMALL,
                 bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w")

        self.gen_result_var = tk.StringVar(value="Click Generate to create a password")
        gen_display = tk.Entry(pw_card, textvariable=self.gen_result_var,
                               font=("Consolas", 16), bg=BG_CARD, fg=ACCENT,
                               insertbackground=ACCENT, relief="flat", state="readonly",
                               readonlybackground=BG_CARD, width=30)
        gen_display.pack(fill="x", ipady=12, pady=(8, 0))

        btn_row = tk.Frame(pw_card, bg=BG_PANEL)
        btn_row.pack(fill="x", pady=(12, 0))
        make_button(btn_row, "📋 Copy", self._copy_generated, bg=ACCENT, pady=6).pack(side="left", padx=(0,8))
        make_button(btn_row, "💾 Save to Vault", self._save_generated, bg=ACCENT2, pady=6).pack(side="left")
        make_button(btn_row, "⟳ Regenerate", self._do_generate, bg=BG_CARD,
                    fg=TEXT_SEC, pady=6).pack(side="right")

        # Strength display
        self.gen_strength_frame = tk.Frame(right, bg=BG_DARK, pady=16)
        self.gen_strength_frame.pack(fill="x")
        self.gen_strength_label = tk.Label(self.gen_strength_frame, text="",
                                           font=FONT_BODY, bg=BG_DARK, fg=TEXT_PRI)
        self.gen_strength_label.pack(anchor="w")

        self.gen_bar_canvas = tk.Canvas(self.gen_strength_frame, height=8, bg=BG_CARD,
                                        highlightthickness=0)
        self.gen_bar_canvas.pack(fill="x", pady=(4, 12))

        self.gen_details_frame = tk.Frame(self.gen_strength_frame, bg=BG_DARK)
        self.gen_details_frame.pack(fill="x")

        # History
        tk.Label(right, text="Recent", font=FONT_SMALL, bg=BG_DARK, fg=TEXT_DIM).pack(anchor="w", pady=(8,2))
        self.gen_history = tk.Listbox(right, font=FONT_MONO_S, bg=BG_CARD, fg=TEXT_PRI,
                                       relief="flat", height=5, selectbackground=BG_HOVER,
                                       selectforeground=ACCENT, highlightthickness=0)
        self.gen_history.pack(fill="x")
        self.gen_history_data = []

    def _do_generate(self):
        gen_type = self.gen_type.get()
        length = self.length_var.get()

        if gen_type == "random":
            pw = generate_password(
                length=length,
                use_upper=self.opt_upper.get(),
                use_lower=self.opt_lower.get(),
                use_digits=self.opt_digits.get(),
                use_special=self.opt_special.get(),
                exclude_ambiguous=self.opt_noambig.get()
            )
        elif gen_type == "passphrase":
            pw = generate_passphrase(word_count=max(3, length // 5))
        elif gen_type == "memorable":
            from generator import generate_memorable
            pw = generate_memorable(length=length)
        else:
            from generator import generate_pin
            pw = generate_pin(length=min(length, 12))

        self.gen_result_var.set(pw)
        self._update_gen_strength(pw)

        # Update history
        self.gen_history_data.insert(0, pw)
        self.gen_history_data = self.gen_history_data[:10]
        self.gen_history.delete(0, tk.END)
        for h in self.gen_history_data:
            self.gen_history.insert(tk.END, h)

    def _update_gen_strength(self, pw):
        result = analyze(pw)
        self.gen_strength_label.config(
            text=f"Strength: {result.strength}  |  Score: {result.score}/100  |  "
                 f"Entropy: {result.entropy} bits  |  Crack time: {result.crack_time}",
            fg=result.color
        )
        self.gen_bar_canvas.update_idletasks()
        w = self.gen_bar_canvas.winfo_width() or 400
        self.gen_bar_canvas.delete("all")
        fill_w = int(w * result.score / 100)
        self.gen_bar_canvas.create_rectangle(0, 0, fill_w, 8, fill=result.color, outline="")

        for widget in self.gen_details_frame.winfo_children():
            widget.destroy()

    def _copy_generated(self):
        pw = self.gen_result_var.get()
        if pw and pw != "Click Generate to create a password":
            self.clipboard_clear()
            self.clipboard_append(pw)
            self.update()
            self._flash_status("✓ Password copied")

    def _save_generated(self):
        pw = self.gen_result_var.get()
        if not pw or pw == "Click Generate to create a password":
            messagebox.showwarning("No Password", "Generate a password first.")
            return
        self._open_add_dialog(prefill_password=pw)

    # ── Analyzer Tab ───────────────────────────────────────────────────────────

    def _build_analyzer_tab(self):
        tab = self.tab_analyzer
        outer = tk.Frame(tab, bg=BG_DARK)
        outer.pack(fill="both", expand=True, padx=32, pady=24)

        tk.Label(outer, text="Password Analyzer", font=FONT_TITLE,
                 bg=BG_DARK, fg=TEXT_PRI).pack(anchor="w")
        tk.Label(outer, text="Check the strength of any password in real-time",
                 font=FONT_BODY, bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w", pady=(2, 20))

        # Input
        input_card = tk.Frame(outer, bg=BG_PANEL, padx=24, pady=20)
        input_card.pack(fill="x")
        input_card.config(highlightthickness=1, highlightbackground=BORDER)

        tk.Label(input_card, text="Enter Password to Analyze", font=FONT_SMALL,
                 bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w")

        input_row = tk.Frame(input_card, bg=BG_PANEL)
        input_row.pack(fill="x", pady=(8, 0))

        self.analyzer_var = tk.StringVar()
        self.analyzer_show = tk.BooleanVar(value=False)

        self.analyzer_entry = tk.Entry(input_row, textvariable=self.analyzer_var,
                                       font=("Consolas", 16), bg=BG_CARD, fg=TEXT_PRI,
                                       insertbackground=ACCENT, relief="flat",
                                       highlightthickness=1, highlightbackground=BORDER,
                                       show="●", width=40)
        self.analyzer_entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.analyzer_var.trace("w", lambda *_: self._do_analyze())

        def toggle_show():
            current = self.analyzer_entry.cget("show")
            self.analyzer_entry.config(show="" if current == "●" else "●")
            toggle_btn.config(text="🙈" if current == "●" else "👁")

        toggle_btn = tk.Button(input_row, text="👁", font=FONT_BODY,
                               bg=BG_CARD, fg=TEXT_SEC, relief="flat",
                               cursor="hand2", command=toggle_show, padx=12, pady=10)
        toggle_btn.pack(side="left", padx=(4, 0))

        # Strength bar
        bar_frame = tk.Frame(outer, bg=BG_DARK, pady=12)
        bar_frame.pack(fill="x")
        self.anlz_strength_label = tk.Label(bar_frame, text="Enter a password above",
                                            font=("Segoe UI", 13, "bold"), bg=BG_DARK, fg=TEXT_DIM)
        self.anlz_strength_label.pack(anchor="w")
        self.anlz_bar = tk.Canvas(bar_frame, height=12, bg=BG_CARD, highlightthickness=0)
        self.anlz_bar.pack(fill="x", pady=(6, 0))

        # Details grid
        details = tk.Frame(outer, bg=BG_DARK)
        details.pack(fill="both", expand=True, pady=(16, 0))

        # Left: metrics
        self.anlz_metrics_frame = tk.Frame(details, bg=BG_PANEL, padx=20, pady=16)
        self.anlz_metrics_frame.pack(side="left", fill="both", padx=(0, 12))
        self.anlz_metrics_frame.config(highlightthickness=1, highlightbackground=BORDER)
        tk.Label(self.anlz_metrics_frame, text="METRICS", font=("Segoe UI", 8, "bold"),
                 bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w", pady=(0, 8))

        self.anlz_metric_labels = {}
        for key in ["Score", "Entropy", "Crack Time", "Length"]:
            row = tk.Frame(self.anlz_metrics_frame, bg=BG_PANEL)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=key, font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_SEC).pack(side="left")
            lbl = tk.Label(row, text="—", font=("Segoe UI", 10, "bold"),
                           bg=BG_PANEL, fg=TEXT_PRI)
            lbl.pack(side="right")
            self.anlz_metric_labels[key] = lbl

        # Right: issues and suggestions
        right_details = tk.Frame(details, bg=BG_DARK)
        right_details.pack(side="left", fill="both", expand=True)

        issues_card = tk.Frame(right_details, bg=BG_PANEL, padx=20, pady=16)
        issues_card.pack(fill="both", expand=True, pady=(0, 8))
        issues_card.config(highlightthickness=1, highlightbackground=BORDER)
        tk.Label(issues_card, text="ISSUES & SUGGESTIONS", font=("Segoe UI", 8, "bold"),
                 bg=BG_PANEL, fg=TEXT_DIM).pack(anchor="w", pady=(0, 8))
        self.anlz_issues_frame = tk.Frame(issues_card, bg=BG_PANEL)
        self.anlz_issues_frame.pack(fill="both", expand=True)

    def _do_analyze(self):
        pw = self.analyzer_var.get()
        if not pw:
            self.anlz_strength_label.config(text="Enter a password above", fg=TEXT_DIM)
            self.anlz_bar.delete("all")
            for key in self.anlz_metric_labels:
                self.anlz_metric_labels[key].config(text="—", fg=TEXT_PRI)
            for w in self.anlz_issues_frame.winfo_children():
                w.destroy()
            return

        result = analyze(pw)

        self.anlz_strength_label.config(
            text=f"  {result.strength}  —  {result.score}/100",
            fg=result.color
        )

        self.anlz_bar.update_idletasks()
        w = self.anlz_bar.winfo_width() or 500
        self.anlz_bar.delete("all")
        fill_w = int(w * result.score / 100)
        self.anlz_bar.create_rectangle(0, 0, fill_w, 12, fill=result.color, outline="")

        self.anlz_metric_labels["Score"].config(text=f"{result.score}/100", fg=result.color)
        self.anlz_metric_labels["Entropy"].config(text=f"{result.entropy} bits")
        self.anlz_metric_labels["Crack Time"].config(text=result.crack_time)
        self.anlz_metric_labels["Length"].config(text=f"{len(pw)} chars")

        for w in self.anlz_issues_frame.winfo_children():
            w.destroy()

        for issue in result.issues:
            row = tk.Frame(self.anlz_issues_frame, bg=BG_PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(row, text="✗", fg=DANGER, bg=BG_PANEL, font=FONT_SMALL).pack(side="left", padx=(0,6))
            tk.Label(row, text=issue, fg=DANGER, bg=BG_PANEL, font=FONT_SMALL).pack(side="left")

        for sug in result.suggestions:
            row = tk.Frame(self.anlz_issues_frame, bg=BG_PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(row, text="→", fg=ACCENT, bg=BG_PANEL, font=FONT_SMALL).pack(side="left", padx=(0,6))
            tk.Label(row, text=sug, fg=TEXT_SEC, bg=BG_PANEL, font=FONT_SMALL).pack(side="left")

        if not result.issues:
            tk.Label(self.anlz_issues_frame, text="✓ No issues found!",
                     font=FONT_SMALL, fg=ACCENT2, bg=BG_PANEL).pack(anchor="w")

    # ── Rotation Tab ───────────────────────────────────────────────────────────

    def _build_rotation_tab(self):
        tab = self.tab_rotation
        outer = tk.Frame(tab, bg=BG_DARK)
        outer.pack(fill="both", expand=True, padx=32, pady=24)

        tk.Label(outer, text="Password Rotation", font=FONT_TITLE,
                 bg=BG_DARK, fg=TEXT_PRI).pack(anchor="w")
        tk.Label(outer, text="Monitor and rotate passwords on schedule",
                 font=FONT_BODY, bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w", pady=(2, 16))

        # Action bar
        action_bar = tk.Frame(outer, bg=BG_DARK)
        action_bar.pack(fill="x", pady=(0, 16))
        make_button(action_bar, "⟳ Refresh Status", self._load_rotation_data,
                    bg=BG_PANEL, fg=TEXT_PRI, pady=6).pack(side="left", padx=(0, 8))
        make_button(action_bar, "🔄 Auto-Rotate Overdue", self._auto_rotate_overdue,
                    bg=DANGER, pady=6).pack(side="left")

        # Rotation table
        header = tk.Frame(outer, bg=BG_PANEL, pady=8, padx=12)
        header.pack(fill="x")
        for col in ["Entry", "Status", "Days Since Rotation", "Interval", "Action"]:
            tk.Label(header, text=col, font=("Segoe UI", 9, "bold"),
                     bg=BG_PANEL, fg=TEXT_DIM).pack(side="left", expand=True)

        self.rotation_list_frame = tk.Frame(outer, bg=BG_DARK)
        self.rotation_list_frame.pack(fill="both", expand=True, pady=(4, 0))

        # Log section
        separator(outer).pack(fill="x", pady=12)
        tk.Label(outer, text="Rotation History", font=FONT_HEAD,
                 bg=BG_DARK, fg=TEXT_PRI).pack(anchor="w")

        self.rotation_log_frame = tk.Frame(outer, bg=BG_DARK)
        self.rotation_log_frame.pack(fill="x", pady=(8, 0))

        self._load_rotation_data()

    def _load_rotation_data(self):
        for w in self.rotation_list_frame.winfo_children():
            w.destroy()

        all_entries = db.get_all_entries(self.master_password)
        annotated = get_rotation_status(all_entries)

        for entry in annotated:
            row = tk.Frame(self.rotation_list_frame, bg=BG_CARD, pady=8, padx=12)
            row.pack(fill="x", pady=2)
            row.config(highlightthickness=1, highlightbackground=BORDER)

            status = entry.get("rotation_status", "ok")
            status_label = entry.get("rotation_status_label", "")
            status_color = {"overdue": DANGER, "warning": WARN, "ok": ACCENT2}.get(status, TEXT_SEC)

            tk.Label(row, text=entry["title"], font=("Segoe UI", 10, "bold"),
                     bg=BG_CARD, fg=TEXT_PRI, width=20, anchor="w").pack(side="left")
            tk.Label(row, text=status_label, font=FONT_SMALL,
                     bg=BG_CARD, fg=status_color, width=22, anchor="w").pack(side="left")
            tk.Label(row, text=f"{entry.get('days_since_rotation',0)} days",
                     font=FONT_SMALL, bg=BG_CARD, fg=TEXT_SEC, width=16, anchor="w").pack(side="left")
            tk.Label(row, text=f"Every {entry.get('rotation_interval_days',90)}d",
                     font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM, width=12, anchor="w").pack(side="left")

            def rotate_now(eid=entry["id"], title=entry["title"]):
                self._manual_rotate(eid, title)

            make_button(row, "Rotate Now", rotate_now, bg=ACCENT, pady=3,
                        padx=8).pack(side="right")

        # Rotation log
        for w in self.rotation_log_frame.winfo_children():
            w.destroy()

        logs = db.get_rotation_log()[:5]
        for log in logs:
            row = tk.Frame(self.rotation_log_frame, bg=BG_PANEL, pady=4, padx=12)
            row.pack(fill="x", pady=1)
            rotated_at = log.get("rotated_at", "")[:19].replace("T", " ")
            tk.Label(row, text=log.get("title", ""), font=("Segoe UI", 10, "bold"),
                     bg=BG_PANEL, fg=TEXT_PRI, width=20, anchor="w").pack(side="left")
            tk.Label(row, text=rotated_at, font=FONT_SMALL,
                     bg=BG_PANEL, fg=TEXT_SEC, width=20, anchor="w").pack(side="left")
            tk.Label(row, text=log.get("reason", ""), font=FONT_SMALL,
                     bg=BG_PANEL, fg=TEXT_DIM).pack(side="left")
            strength_change = f"{log.get('old_strength',0)} → {log.get('new_strength',0)}"
            tk.Label(row, text=strength_change, font=FONT_SMALL,
                     bg=BG_PANEL, fg=ACCENT).pack(side="right")

    def _manual_rotate(self, entry_id, title):
        new_pw = generate_password(length=20)
        result = analyze(new_pw)
        if messagebox.askyesno("Rotate Password",
                               f"Generate a new strong password for '{title}'?\n\n"
                               f"New password strength: {result.strength} ({result.score}/100)\n"
                               f"Crack time: {result.crack_time}"):
            db.rotate_password(self.master_password, entry_id, new_pw, result.score, "Manual rotation")
            # Show new password
            self._show_new_password_dialog(title, new_pw)
            self._load_entries()
            self._load_rotation_data()

    def _auto_rotate_overdue(self):
        overdue = db.get_entries_due_for_rotation()
        if not overdue:
            messagebox.showinfo("No Rotation Needed", "All passwords are within their rotation schedule.")
            return
        count = len(overdue)
        if messagebox.askyesno("Auto-Rotate",
                               f"{count} password(s) are overdue for rotation.\n"
                               f"Auto-rotate all with new strong passwords?"):
            from rotate import engine
            entry_ids = [e["id"] for e in overdue]
            results = engine.auto_rotate(self.master_password, entry_ids)
            self._load_entries()
            self._load_rotation_data()
            messagebox.showinfo("Done", f"Rotated {len(results)} password(s) successfully.")

    def _show_new_password_dialog(self, title, new_pw):
        dlg = tk.Toplevel(self)
        dlg.title("New Password")
        dlg.configure(bg=BG_DARK)
        dlg.geometry("480x220")
        dlg.grab_set()

        tk.Label(dlg, text=f"'{title}' password rotated!", font=FONT_HEAD,
                 bg=BG_DARK, fg=ACCENT2).pack(pady=(20, 4))
        tk.Label(dlg, text="Save this password before closing:",
                 font=FONT_SMALL, bg=BG_DARK, fg=TEXT_SEC).pack()

        pw_entry = tk.Entry(dlg, font=("Consolas", 14), bg=BG_CARD, fg=ACCENT,
                            relief="flat", justify="center", width=36,
                            readonlybackground=BG_CARD, state="readonly")
        pw_entry.pack(pady=12, ipady=10)
        pw_entry.config(state="normal")
        pw_entry.insert(0, new_pw)
        pw_entry.config(state="readonly")

        def copy():
            dlg.clipboard_clear()
            dlg.clipboard_append(new_pw)
            dlg.update()

        make_button(dlg, "📋 Copy & Close", lambda: [copy(), dlg.destroy()],
                    bg=ACCENT, pady=8).pack()

    # ── Add / Edit Dialogs ─────────────────────────────────────────────────────

    def _open_add_dialog(self, prefill_password=""):
        self._open_entry_dialog("Add New Entry", prefill_password=prefill_password)

    def _open_edit_dialog(self, entry):
        self._open_entry_dialog("Edit Entry", entry=entry)

    def _open_entry_dialog(self, title_text, entry=None, prefill_password=""):
        dlg = tk.Toplevel(self)
        dlg.title(title_text)
        dlg.configure(bg=BG_DARK)
        dlg.geometry("560x620")
        dlg.grab_set()

        outer = tk.Frame(dlg, bg=BG_DARK, padx=28, pady=24)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text=title_text, font=FONT_HEAD, bg=BG_DARK, fg=TEXT_PRI).pack(anchor="w")
        separator(outer).pack(fill="x", pady=12)

        def field(label, var, show=None, width=36):
            tk.Label(outer, text=label, font=FONT_SMALL, bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w", pady=(6,0))
            e = make_entry(outer, show=show, width=width)
            e.config(textvariable=var)
            e.pack(fill="x", ipady=7)
            return e

        title_var    = tk.StringVar(value=entry["title"] if entry else "")
        username_var = tk.StringVar(value=entry.get("username","") if entry else "")
        pw_var       = tk.StringVar(value=entry["password"] if entry else prefill_password)
        url_var      = tk.StringVar(value=entry.get("url","") if entry else "")
        notes_var    = tk.StringVar(value=entry.get("notes","") if entry else "")

        field("Title *", title_var)
        field("Username / Email", username_var)

        tk.Label(outer, text="Password *", font=FONT_SMALL, bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w", pady=(6,0))
        pw_row = tk.Frame(outer, bg=BG_DARK)
        pw_row.pack(fill="x")
        pw_entry_widget = make_entry(pw_row, show="●", width=28)
        pw_entry_widget.config(textvariable=pw_var)
        pw_entry_widget.pack(side="left", fill="x", expand=True, ipady=7)

        def gen_pw():
            new_pw = generate_password(length=18)
            pw_var.set(new_pw)

        make_button(pw_row, "⚡", gen_pw, bg=ACCENT, padx=10, pady=7).pack(side="left", padx=(4,0))

        # Mini strength bar
        mini_bar = tk.Canvas(outer, height=4, bg=BG_CARD, highlightthickness=0)
        mini_bar.pack(fill="x", pady=(3,0))
        mini_label = tk.Label(outer, text="", font=FONT_SMALL, bg=BG_DARK, fg=TEXT_SEC)
        mini_label.pack(anchor="w")

        def on_pw_change(*_):
            pw = pw_var.get()
            if not pw:
                mini_bar.delete("all")
                mini_label.config(text="")
                return
            r = analyze(pw)
            mini_bar.update_idletasks()
            w = mini_bar.winfo_width() or 400
            mini_bar.delete("all")
            mini_bar.create_rectangle(0, 0, int(w * r.score/100), 4, fill=r.color, outline="")
            mini_label.config(text=f"{r.strength} ({r.score}/100)", fg=r.color)

        pw_var.trace("w", on_pw_change)
        on_pw_change()

        field("URL / Website", url_var)

        tk.Label(outer, text="Category", font=FONT_SMALL, bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w", pady=(6,0))
        cat_var = tk.StringVar(value=entry.get("category","General") if entry else "General")
        cat_combo = ttk.Combobox(outer, textvariable=cat_var,
                                 values=["General","Social","Work","Finance","Email","Other"],
                                 state="readonly", font=FONT_BODY)
        cat_combo.pack(fill="x", ipady=4)

        tk.Label(outer, text="Rotation Interval (days)", font=FONT_SMALL,
                 bg=BG_DARK, fg=TEXT_SEC).pack(anchor="w", pady=(6,0))
        rot_var = tk.IntVar(value=entry.get("rotation_interval_days",90) if entry else 90)
        rot_scale = tk.Scale(outer, variable=rot_var, from_=7, to=365, orient="horizontal",
                             bg=BG_DARK, fg=TEXT_PRI, troughcolor=BG_CARD, highlightthickness=0)
        rot_scale.pack(fill="x")

        error_lbl = tk.Label(outer, text="", font=FONT_SMALL, bg=BG_DARK, fg=DANGER)
        error_lbl.pack(anchor="w")

        def save():
            t = title_var.get().strip()
            pw = pw_var.get().strip()
            if not t:
                error_lbl.config(text="Title is required")
                return
            if not pw:
                error_lbl.config(text="Password is required")
                return

            result = analyze(pw)
            if entry:
                db.update_entry(
                    self.master_password, entry["id"],
                    title=t, username=username_var.get(), password=pw,
                    url=url_var.get(), category=cat_var.get(),
                    notes=notes_var.get(), rotation_interval_days=rot_var.get(),
                    strength_score=result.score
                )
            else:
                db.add_entry(
                    self.master_password, t, username_var.get(), pw,
                    url=url_var.get(), category=cat_var.get(),
                    notes=notes_var.get(), rotation_interval=rot_var.get(),
                    strength_score=result.score
                )
            dlg.destroy()
            self._load_entries()

        make_button(outer, "💾 Save Entry", save, bg=ACCENT, pady=10).pack(fill="x", pady=(12,0))

    def _open_view_dialog(self, entry):
        dlg = tk.Toplevel(self)
        dlg.title(f"View — {entry['title']}")
        dlg.configure(bg=BG_DARK)
        dlg.geometry("500x420")
        dlg.grab_set()

        outer = tk.Frame(dlg, bg=BG_DARK, padx=28, pady=24)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text=entry["title"], font=FONT_TITLE, bg=BG_DARK, fg=TEXT_PRI).pack(anchor="w")
        tk.Label(outer, text=entry.get("category","General"), font=FONT_SMALL,
                 bg=BG_DARK, fg=ACCENT).pack(anchor="w")
        separator(outer).pack(fill="x", pady=12)

        def detail_row(label, value, mono=False):
            if not value:
                return
            f = tk.Frame(outer, bg=BG_DARK)
            f.pack(fill="x", pady=4)
            tk.Label(f, text=label, font=FONT_SMALL, bg=BG_DARK, fg=TEXT_DIM, width=14, anchor="w").pack(side="left")
            tk.Label(f, text=value, font=FONT_MONO if mono else FONT_BODY,
                     bg=BG_DARK, fg=TEXT_PRI, anchor="w").pack(side="left")

        detail_row("Username", entry.get("username",""))
        detail_row("URL", entry.get("url",""))
        detail_row("Category", entry.get("category",""))
        detail_row("Created", entry.get("created_at","")[:19].replace("T"," "))
        detail_row("Updated", entry.get("updated_at","")[:19].replace("T"," "))

        result = analyze(entry["password"])
        detail_row("Strength", f"{result.strength} ({result.score}/100)")
        detail_row("Crack Time", result.crack_time)

        separator(outer).pack(fill="x", pady=12)

        pw_frame = tk.Frame(outer, bg=BG_CARD, padx=12, pady=10)
        pw_frame.pack(fill="x")
        pw_frame.config(highlightthickness=1, highlightbackground=BORDER)

        pw_var = tk.StringVar(value="●" * len(entry["password"]))
        show_state = [False]

        pw_label = tk.Label(pw_frame, textvariable=pw_var, font=FONT_MONO,
                            bg=BG_CARD, fg=ACCENT)
        pw_label.pack(side="left")

        def toggle():
            show_state[0] = not show_state[0]
            pw_var.set(entry["password"] if show_state[0] else "●" * len(entry["password"]))
            toggle_btn.config(text="🙈" if show_state[0] else "👁")

        toggle_btn = tk.Button(pw_frame, text="👁", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_SEC,
                               relief="flat", cursor="hand2", command=toggle)
        toggle_btn.pack(side="right")

        def copy():
            dlg.clipboard_clear()
            dlg.clipboard_append(entry["password"])
            dlg.update()
            self._flash_status("✓ Password copied")

        make_button(outer, "📋 Copy Password", copy, bg=ACCENT, pady=8).pack(fill="x", pady=(12,0))

    # ── Data loading ───────────────────────────────────────────────────────────

    def _load_entries(self):
        def _load():
            all_entries = db.get_all_entries(self.master_password)
            annotated = get_rotation_status(all_entries)
            self.entries = annotated
            self.after(0, lambda: self._apply_filters())
            self.after(0, lambda: self._update_stats())

        threading.Thread(target=_load, daemon=True).start()

    def _apply_filters(self):
        query = self.search_var.get().lower()
        cat = getattr(self, '_active_category', 'All')

        filtered = self.entries
        if query:
            filtered = [e for e in filtered if
                        query in e["title"].lower() or
                        query in (e.get("username") or "").lower() or
                        query in (e.get("url") or "").lower()]
        if cat and cat != "All":
            filtered = [e for e in filtered if e.get("category") == cat]

        self._render_entries(filtered)

    def _filter_entries(self, *_):
        self._apply_filters()

    def _filter_by_category(self, cat):
        self._active_category = cat
        self._apply_filters()

    def _update_stats(self):
        stats = db.get_vault_stats()
        self.stat_total.config(text=str(stats["total"]))
        self.stat_strong.config(text=str(stats["strong"]))
        self.stat_weak.config(text=str(stats["weak"]))
        self.stat_overdue.config(text=str(stats["overdue_rotation"]))

    def _flash_status(self, msg):
        # Status flash (title bar)
        original = self.winfo_toplevel().title()
        self.winfo_toplevel().title(f"✓  {msg}  —  VaultGuard")
        self.after(2500, lambda: self.winfo_toplevel().title(original))

    def _start_rotation_engine(self):
        def on_rotation_needed(overdue):
            count = len(overdue)
            self.after(0, lambda: self._flash_status(
                f"⚠ {count} password(s) need rotation"
            ))
        rotation_engine.start(self.master_password, on_rotation_needed)


# ─── App Bootstrap ─────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VaultGuard — Password Manager")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=BG_DARK)

        # Style scrollbars
        style = ttk.Style()
        style.configure("Vertical.TScrollbar", background=BG_CARD, troughcolor=BG_DARK,
                        bordercolor=BG_DARK, arrowcolor=TEXT_DIM)

        self._current_screen = None
        self._show_setup()

    def _show_setup(self):
        if self._current_screen:
            self._current_screen.destroy()
        screen = SetupScreen(self, self._on_unlock)
        screen.pack(fill="both", expand=True)
        self._current_screen = screen

    def _on_unlock(self, master_password: str):
        if self._current_screen:
            self._current_screen.destroy()
        app = VaultGuardApp(self, master_password)
        app.pack(fill="both", expand=True)
        self._current_screen = app
        self.title("VaultGuard — Password Manager")


if __name__ == "__main__":
    db.init_db()
    app = App()
    app.mainloop()
