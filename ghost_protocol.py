#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import random
import threading
import json
import ssl
import urllib.request
import tempfile
import atexit
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
COLORS = {
    "bg_deepest":   "#06060A",
    "bg_deep":      "#0B0B12",
    "bg_card":      "#10111A",
    "bg_card_hover":"#151621",
    "bg_elevated":  "#1A1B28",
    "bg_input":     "#0D0E16",
    "border":       "#1E1F30",
    "border_focus": "#2A2B42",
    "text_primary": "#E8E9F0",
    "text_secondary":"#8B8D9E",
    "text_dim":     "#555770",
    "accent_green": "#00E676",
    "accent_green_dim": "#00B85C",
    "accent_cyan":  "#00D4FF",
    "accent_red":   "#FF3B5C",
    "accent_red_dim":"#CC2F4A",
    "accent_orange":"#FF9F0A",
    "accent_purple":"#A78BFA",
    "success":      "#34D399",
    "warning":      "#FBBF24",
    "knob_off":     "#6B6D80",
    "track_off":    "#2A2B3D",
}

FONTS = {
    "title":        ("SF Pro Display", 22, "bold"),
    "subtitle":     ("SF Mono", 10),
    "section":      ("SF Pro Display", 11, "bold"),
    "body":         ("SF Pro Text", 12),
    "body_small":   ("SF Pro Text", 11),
    "mono":         ("SF Mono", 11),
    "mono_small":   ("SF Mono", 10),
    "button":       ("SF Pro Display", 11, "bold"),
    "button_large": ("SF Pro Display", 13, "bold"),
    "status":       ("SF Mono", 9),
}

# Fallback fonts for systems without SF Pro
def _verify_fonts():
    """Replace SF fonts with available alternatives."""
    try:
        test = tk.Tk()
        test.withdraw()
        available = list(tk.font.families())
        test.destroy()
    except Exception:
        available = []

    replacements = {
        "SF Pro Display": "Helvetica Neue",
        "SF Pro Text": "Helvetica",
        "SF Mono": "Menlo",
    }
    for key in FONTS:
        fam = FONTS[key][0]
        if fam in replacements and fam not in available:
            FONTS[key] = (replacements[fam],) + FONTS[key][1:]


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM WIDGET: Rounded-Feel Button with Glow Hover
# ══════════════════════════════════════════════════════════════════════════════
class GhostButton(tk.Canvas):
    def __init__(self, parent, text, command=None, 
                 bg=COLORS["bg_elevated"], fg=COLORS["accent_green"],
                 hover_bg=None, hover_fg=None,
                 font=FONTS["button"], width=None, height=36, padx=18, corner=6):
        self._text = text
        self._cmd = command
        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg or fg
        self._hover_fg = hover_fg or COLORS["bg_deepest"]
        self._font = font
        self._padx = padx
        self._corner = corner
        self._disabled = False
        self._btn_height = height

        w = width or 160
        super().__init__(parent, width=w, height=height, 
                         bg=parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg_deep"],
                         highlightthickness=0, cursor="hand2")

        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._hovered = False
        self.after(10, self._redraw)

    def _redraw(self, event=None):
        self.delete("all")
        w = self.winfo_width() or int(self.cget("width"))
        h = self._btn_height
        r = self._corner
        bg = self._hover_bg if self._hovered else self._bg
        fg = self._hover_fg if self._hovered else self._fg

        if self._disabled:
            bg = COLORS["bg_card"]
            fg = COLORS["text_dim"]

        # Draw rounded rectangle
        self.create_round_rect(1, 1, w-1, h-1, r, fill=bg, outline=fg if not self._hovered else bg, width=1)
        # Draw text
        self.create_text(w/2, h/2, text=self._text, fill=fg, font=self._font, anchor="center")

    def create_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1, x2-r, y1,
            x2, y1, x2, y1+r,
            x2, y2-r, x2, y2,
            x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r,
            x1, y1+r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, e=None):
        if not self._disabled:
            self._hovered = True
            self._redraw()

    def _on_leave(self, e=None):
        self._hovered = False
        self._redraw()

    def _on_click(self, e=None):
        if not self._disabled and self._cmd:
            self._cmd()

    def set_disabled(self, disabled=True):
        self._disabled = disabled
        self.config(cursor="arrow" if disabled else "hand2")
        self._redraw()

    def config(self, **kwargs):
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            self._redraw()
        super().config(**kwargs)

    def configure(self, **kwargs):
        self.config(**kwargs)


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM WIDGET: Smooth Animated Toggle Switch
# ══════════════════════════════════════════════════════════════════════════════
class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, default_state=False, command=None, width=48, height=24):
        self.is_on = default_state
        self.command = command
        self._width_val = width
        self._height_val = height

        bg_color = parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg_deep"]
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, cursor="hand2")

        self._left_x = height // 2
        self._right_x = width - height // 2
        self._current_x = float(self._right_x if self.is_on else self._left_x)

        self.bind("<Button-1>", self.toggle)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self._width_val, self._height_val
        r = h // 2

        # Interpolate color
        progress = (self._current_x - self._left_x) / max(1, self._right_x - self._left_x)
        
        if progress > 0.5:
            track_color = COLORS["accent_green"]
        else:
            track_color = COLORS["track_off"]

        knob_color = "#FFFFFF" if progress > 0.5 else COLORS["knob_off"]

        # Track (rounded pill)
        self.create_round_rect(0, 0, w, h, r, fill=track_color, outline="")
        # Knob
        kr = (h - 6) / 2
        cx = self._current_x
        cy = h / 2
        self.create_oval(cx - kr, cy - kr, cx + kr, cy + kr, fill=knob_color, outline="")

    def create_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def toggle(self, event=None):
        self.is_on = not self.is_on
        self._animate()
        if self.command:
            self.command(self.is_on)

    def _animate(self):
        target = float(self._right_x if self.is_on else self._left_x)
        steps = 8
        dx = (target - self._current_x) / steps
        def step(n):
            if n < steps:
                self._current_x += dx
                self._draw()
                self.after(12, lambda: step(n + 1))
            else:
                self._current_x = target
                self._draw()
        step(0)


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS INDICATOR DOT (pulsing circle)
# ══════════════════════════════════════════════════════════════════════════════
class StatusDot(tk.Canvas):
    def __init__(self, parent, color=COLORS["accent_red"], size=10):
        bg = parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg_deep"]
        super().__init__(parent, width=size+4, height=size+4, bg=bg, highlightthickness=0)
        self._color = color
        self._size = size
        self._pulse_state = 0
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        c = s // 2 + 2
        self.create_oval(c - s//2, c - s//2, c + s//2, c + s//2, fill=self._color, outline="")

    def set_color(self, color):
        self._color = color
        self._draw()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class GhostProtocolUnified:
    def __init__(self, root):
        self.root = root
        self.root.title("Ghost Protocol")
        self.root.geometry("1280x920")
        self.root.configure(bg=COLORS["bg_deepest"])
        self.root.resizable(True, True)
        self.root.minsize(1100, 780)

        self.tor_process = None
        self.shred_list = []
        self.fetched_relays = {}

        # Panic hotkey
        self.root.bind("<Escape>", lambda e: self.trigger_panic())

        atexit.register(self.force_safe_shutdown)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        try:
            import tkinter.font
            _verify_fonts()
        except Exception:
            pass

        self._setup_styles()
        self._build_ui()

        self.log("SYSTEM INITIALIZED — PANIC KEY [ESC] REGISTERED", "success")
        self.log(f"Platform: {sys.platform.upper()}", "info")
        self.detect_tor_binary()

    # ─── Style Configuration ─────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Scrollbar
        style.configure("Dark.Vertical.TScrollbar",
            gripcount=0, background=COLORS["bg_elevated"],
            darkcolor=COLORS["bg_deep"], lightcolor=COLORS["bg_card"],
            troughcolor=COLORS["bg_deep"], bordercolor=COLORS["bg_elevated"],
            arrowcolor=COLORS["text_dim"])
        style.map("Dark.Vertical.TScrollbar",
            background=[("active", COLORS["border_focus"]), ("pressed", COLORS["accent_green"])])

        # Combobox
        style.configure("Ghost.TCombobox",
            fieldbackground=COLORS["bg_input"], background=COLORS["bg_elevated"],
            foreground=COLORS["text_primary"], bordercolor=COLORS["border"],
            arrowcolor=COLORS["accent_green"], selectbackground=COLORS["bg_elevated"],
            selectforeground=COLORS["accent_green"])
        style.map("Ghost.TCombobox",
            fieldbackground=[("readonly", COLORS["bg_input"])],
            selectbackground=[("readonly", COLORS["bg_elevated"])],
            selectforeground=[("readonly", COLORS["accent_green"])])

        # Progress bar
        style.configure("Ghost.Horizontal.TProgressbar",
            troughcolor=COLORS["bg_card"], background=COLORS["accent_green"],
            darkcolor=COLORS["accent_green"], lightcolor=COLORS["accent_green_dim"],
            bordercolor=COLORS["border"], thickness=6)

    # ─── Main UI Build ───────────────────────────────────────────────────
    def _build_ui(self):
        root_frame = tk.Frame(self.root, bg=COLORS["bg_deepest"])
        root_frame.pack(fill=tk.BOTH, expand=True)

        # ── TOP BAR ──────────────────────────────────────────────────────
        topbar = tk.Frame(root_frame, bg=COLORS["bg_deep"], height=56)
        topbar.pack(fill=tk.X)
        topbar.pack_propagate(False)

        # Accent line
        tk.Frame(root_frame, bg=COLORS["accent_green"], height=1).pack(fill=tk.X)

        # Left: Logo + Title
        logo_frame = tk.Frame(topbar, bg=COLORS["bg_deep"])
        logo_frame.pack(side=tk.LEFT, padx=20, pady=8)

        # Ghost icon (unicode)
        tk.Label(logo_frame, text="👻", font=("Apple Color Emoji", 20), bg=COLORS["bg_deep"]).pack(side=tk.LEFT, padx=(0, 10))
        
        title_block = tk.Frame(logo_frame, bg=COLORS["bg_deep"])
        title_block.pack(side=tk.LEFT)
        tk.Label(title_block, text="GHOST PROTOCOL", font=FONTS["title"], fg=COLORS["text_primary"], bg=COLORS["bg_deep"]).pack(anchor="w")
        tk.Label(title_block, text="ABSOLUTE PRIVACY SUITE", font=FONTS["status"], fg=COLORS["text_dim"], bg=COLORS["bg_deep"]).pack(anchor="w")

        # Right: Status indicators + Panic
        right_bar = tk.Frame(topbar, bg=COLORS["bg_deep"])
        right_bar.pack(side=tk.RIGHT, padx=16, pady=8)

        # Panic button
        self.btn_panic = GhostButton(right_bar, "⚡ PANIC", command=self.trigger_panic,
            bg=COLORS["accent_red"], fg="#FFFFFF",
            hover_bg=COLORS["accent_red_dim"], hover_fg="#FFFFFF",
            font=FONTS["button"], height=32, width=100, corner=4)
        self.btn_panic.pack(side=tk.RIGHT, padx=(12, 0))

        # Status indicators
        status_frame = tk.Frame(right_bar, bg=COLORS["bg_deep"])
        status_frame.pack(side=tk.RIGHT, padx=8)

        self.tor_status_dot = StatusDot(status_frame, COLORS["accent_red"], 8)
        self.tor_status_dot.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(status_frame, text="TOR", font=FONTS["status"], fg=COLORS["text_dim"], bg=COLORS["bg_deep"]).pack(side=tk.LEFT, padx=(0, 12))

        self.sys_status_dot = StatusDot(status_frame, COLORS["accent_green"], 8)
        self.sys_status_dot.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(status_frame, text="SYS", font=FONTS["status"], fg=COLORS["text_dim"], bg=COLORS["bg_deep"]).pack(side=tk.LEFT)

        # ── MAIN CONTENT ─────────────────────────────────────────────────
        content = tk.Frame(root_frame, bg=COLORS["bg_deepest"])
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 2-column paned window
        paned = tk.PanedWindow(content, orient=tk.HORIZONTAL, bg=COLORS["bg_deepest"],
                               bd=0, sashwidth=6, sashpad=1, sashrelief=tk.FLAT)
        paned.pack(fill=tk.BOTH, expand=True)

        left_col = tk.Frame(paned, bg=COLORS["bg_deepest"])
        right_col = tk.Frame(paned, bg=COLORS["bg_deepest"])

        paned.add(left_col, minsize=440, stretch="always")
        paned.add(right_col, minsize=560, stretch="always")

        # ── LEFT: Toggle Modules ─────────────────────────────────────────
        self._build_toggle_panel(left_col)

        # ── RIGHT: Tabbed Panel ──────────────────────────────────────────
        self._build_right_panel(right_col)

    # ─── Left Panel: Scrollable Toggle Modules ───────────────────────────
    def _build_toggle_panel(self, parent):
        # Card container
        card = tk.Frame(parent, bg=COLORS["bg_card"], bd=0)
        card.pack(fill=tk.BOTH, expand=True, padx=(0, 6))

        # Card header
        header = tk.Frame(card, bg=COLORS["bg_card"], height=36)
        header.pack(fill=tk.X, padx=16, pady=(14, 0))
        header.pack_propagate(False)
        tk.Label(header, text="PRIVACY MODULES", font=FONTS["section"],
                 fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(side=tk.LEFT)

        tk.Frame(card, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=(8, 0))

        # Scrollable area
        canvas = tk.Canvas(card, bg=COLORS["bg_card"], highlightthickness=0)
        scroll = ttk.Scrollbar(card, orient="vertical", command=canvas.yview, style="Dark.Vertical.TScrollbar")

        self.toggles_frame = tk.Frame(canvas, bg=COLORS["bg_card"])
        self.toggles_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * event.delta), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        self.toggles_frame.bind("<MouseWheel>", _on_mousewheel)
        self._left_scroll_handler = _on_mousewheel

        canvas.create_window((0, 0), window=self.toggles_frame, anchor="nw", tags="frame")
        canvas.configure(yscrollcommand=scroll.set)

        # Resize inner frame to match canvas width
        def _resize_frame(event):
            canvas.itemconfig("frame", width=event.width)
        canvas.bind("<Configure>", _resize_frame)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 2), pady=4)

        self.toggles = {}

        # ── Sections ──
        self._add_section("ANONYMOUS ROUTING", "🌐")
        self._add_toggle("tor", "Enforce Traffic via Tor Proxy (SOCKS5)", False, self.on_tor_toggle)
        self._add_toggle("dns", "Flush DNS Cache & Resolver Config", True)

        self._add_section("METADATA & FOOTPRINT CLEANUP", "🧹")
        self._add_toggle("term", "Purge Shell command history buffers", True)
        self._add_toggle("clip", "Securely erase clipboard memory buffer", True)
        self._add_toggle("state", "Wipe OS saved app states & recents", True)

        self._add_section("TELEMETRY & SINKHOLING", "🛡")
        self._add_toggle("hosts", "Sinkhole Apple Diagnostics (/etc/hosts)", False)
        self._add_toggle("spotlight", "Disable local Spotlight Indexing", False)
        self._add_toggle("telem", "Kill active crash reporting processes", True)

        self._add_section("FILE SYSTEM HYGIENE", "🗑")
        self._add_toggle("caches", "Purge system cache directories", False)
        self._add_toggle("logs", "Nuke log directories and events", False)
        self._add_toggle("temp", "Purge temporary storage directory", False)
        self._add_toggle("browsers", "Nuke browser cookies & history DBs", True)

        # Bottom spacer
        tk.Frame(self.toggles_frame, bg=COLORS["bg_card"], height=20).pack()

    def _add_section(self, title, icon=""):
        frame = tk.Frame(self.toggles_frame, bg=COLORS["bg_card"])
        frame.pack(fill=tk.X, padx=12, pady=(18, 4))
        label_text = f"{icon}  {title}" if icon else title
        lbl = tk.Label(frame, text=label_text, font=FONTS["section"],
                fg=COLORS["accent_green"], bg=COLORS["bg_card"], anchor="w")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Bind scroll
        if hasattr(self, "_left_scroll_handler"):
            frame.bind("<MouseWheel>", self._left_scroll_handler)
            lbl.bind("<MouseWheel>", self._left_scroll_handler)

    def _add_toggle(self, key, label_text, default, command=None):
        row = tk.Frame(self.toggles_frame, bg=COLORS["bg_card"])
        row.pack(fill=tk.X, padx=20, pady=5)

        lbl = tk.Label(row, text=label_text, font=FONTS["body_small"],
                        fg=COLORS["text_primary"], bg=COLORS["bg_card"], anchor="w")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        toggle = ToggleSwitch(row, default_state=default, command=command, width=44, height=22)
        toggle.pack(side=tk.RIGHT, padx=(10, 0))
        self.toggles[key] = toggle

        # Propagate mousewheel
        if hasattr(self, "_left_scroll_handler"):
            row.bind("<MouseWheel>", self._left_scroll_handler)
            lbl.bind("<MouseWheel>", self._left_scroll_handler)
            toggle.bind("<MouseWheel>", self._left_scroll_handler)

    # ─── Right Panel: Tabbed interface ───────────────────────────────────
    def _build_right_panel(self, parent):
        # Tab buttons bar
        tab_bar = tk.Frame(parent, bg=COLORS["bg_deepest"], height=36)
        tab_bar.pack(fill=tk.X, padx=(6, 0), pady=(0, 0))

        self._tab_frames = {}
        self._tab_buttons = {}
        self._active_tab = None

        tabs = [
            ("console", "📋 CONSOLE"),
            ("tor_config", "🧅 TOR CONFIG"),
            ("shredder", "🔥 ANTI-FORENSICS"),
        ]

        for tab_key, tab_label in tabs:
            btn = tk.Label(tab_bar, text=tab_label, font=FONTS["mono_small"],
                           fg=COLORS["text_dim"], bg=COLORS["bg_deepest"],
                           padx=14, pady=8, cursor="hand2")
            btn.pack(side=tk.LEFT)
            btn.bind("<Button-1>", lambda e, k=tab_key: self._switch_tab(k))
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=COLORS["text_primary"]) if b != self._tab_buttons.get(self._active_tab) else None)
            btn.bind("<Leave>", lambda e, b=btn, k=tab_key: b.config(fg=COLORS["text_dim"]) if k != self._active_tab else None)
            self._tab_buttons[tab_key] = btn

        # Content area
        self._tab_container = tk.Frame(parent, bg=COLORS["bg_card"])
        self._tab_container.pack(fill=tk.BOTH, expand=True, padx=(6, 0))

        # Build each tab
        self._build_console_tab()
        self._build_tor_tab()
        self._build_shredder_tab()

        # Actions bar (always visible)
        self._build_actions_bar(parent)

        # Default tab
        self._switch_tab("console")

    def _switch_tab(self, tab_key):
        if self._active_tab == tab_key:
            return
        self._active_tab = tab_key

        # Update tab button styles
        for k, btn in self._tab_buttons.items():
            if k == tab_key:
                btn.config(fg=COLORS["accent_green"], bg=COLORS["bg_card"])
            else:
                btn.config(fg=COLORS["text_dim"], bg=COLORS["bg_deepest"])

        # Show/hide frames
        for k, frame in self._tab_frames.items():
            if k == tab_key:
                frame.pack(fill=tk.BOTH, expand=True)
            else:
                frame.pack_forget()

    # ─── Console Tab ─────────────────────────────────────────────────────
    def _build_console_tab(self):
        frame = tk.Frame(self._tab_container, bg=COLORS["bg_card"])
        self._tab_frames["console"] = frame

        # Header
        hdr = tk.Frame(frame, bg=COLORS["bg_card"])
        hdr.pack(fill=tk.X, padx=16, pady=(12, 0))
        tk.Label(hdr, text="AUDIT TRAIL", font=FONTS["section"],
                 fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(side=tk.LEFT)

        tk.Frame(frame, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=(8, 0))

        # Console text
        console_frame = tk.Frame(frame, bg=COLORS["bg_deepest"], bd=0)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.log_text = tk.Text(console_frame, bg=COLORS["bg_deepest"],
                                fg=COLORS["accent_green"], font=FONTS["mono"],
                                bd=0, highlightthickness=0, padx=12, pady=10,
                                insertbackground=COLORS["accent_green"],
                                selectbackground=COLORS["bg_elevated"])
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        console_scroll = ttk.Scrollbar(console_frame, orient="vertical",
                                        command=self.log_text.yview, style="Dark.Vertical.TScrollbar")
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=console_scroll.set)

        # Tags
        self.log_text.tag_config("tag_info",    foreground=COLORS["accent_cyan"])
        self.log_text.tag_config("tag_success", foreground=COLORS["success"])
        self.log_text.tag_config("tag_warning", foreground=COLORS["warning"])
        self.log_text.tag_config("tag_error",   foreground=COLORS["accent_red"])
        self.log_text.tag_config("tag_system",  foreground=COLORS["text_dim"])
        self.log_text.tag_config("tag_ts",      foreground=COLORS["text_dim"])

    # ─── Tor Config Tab ──────────────────────────────────────────────────
    def _build_tor_tab(self):
        frame = tk.Frame(self._tab_container, bg=COLORS["bg_card"])
        self._tab_frames["tor_config"] = frame

        # Scrollable content
        canvas = tk.Canvas(frame, bg=COLORS["bg_card"], highlightthickness=0)
        inner = tk.Frame(canvas, bg=COLORS["bg_card"])
        canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        def resize_inner(e):
            canvas.itemconfig("inner", width=e.width)
        canvas.bind("<Configure>", resize_inner)
        canvas.pack(fill=tk.BOTH, expand=True)

        pad = {"padx": 16, "pady": 6}

        # Header
        tk.Label(inner, text="TOR ROUTING CONFIGURATION", font=FONTS["section"],
                 fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=(0, 10))

        # Settings grid
        settings = tk.Frame(inner, bg=COLORS["bg_card"])
        settings.pack(fill=tk.X, **pad)
        settings.columnconfigure(0, weight=1)
        settings.columnconfigure(1, weight=2)

        row = 0
        def add_label(text, r):
            tk.Label(settings, text=text, font=FONTS["body_small"],
                     fg=COLORS["text_secondary"], bg=COLORS["bg_card"], anchor="w").grid(
                row=r, column=0, sticky="ew", padx=(4, 10), pady=6)

        # Exit Country
        add_label("Exit Country", row)
        self.exit_country_var = tk.StringVar(value="Any (Default)")
        exit_menu = ttk.Combobox(settings, textvariable=self.exit_country_var,
            values=["Any (Default)", "United States {us}", "Germany {de}", "Switzerland {ch}", "Iceland {is}", "Custom"],
            state="readonly", style="Ghost.TCombobox")
        exit_menu.grid(row=row, column=1, sticky="ew", padx=4, pady=6)
        row += 1

        # Custom Exit Nodes
        add_label("Custom Exit Nodes", row)
        self.custom_exit_entry = tk.Entry(settings, bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], font=FONTS["mono_small"],
            insertbackground=COLORS["text_primary"], bd=0, relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_green"])
        self.custom_exit_entry.grid(row=row, column=1, sticky="ew", padx=4, pady=6)
        row += 1

        # Toggle rows
        def add_toggle_row(label, r, default=False):
            add_label(label, r)
            tf = tk.Frame(settings, bg=COLORS["bg_card"])
            tf.grid(row=r, column=1, sticky="w", padx=4, pady=6)
            t = ToggleSwitch(tf, default_state=default, width=44, height=22)
            t.pack()
            return t

        self.strict_nodes_toggle = add_toggle_row("Enforce Strict Nodes", row, False)
        row += 1
        self.exclude_five_eyes_toggle = add_toggle_row("Exclude 5-Eyes (US/UK/CA/AU/NZ)", row, True)
        row += 1
        self.safe_socks_toggle = add_toggle_row("Enforce Safe SOCKS", row, True)
        row += 1
        self.daemon_hardening_toggle = add_toggle_row("Advanced Daemon Hardening", row, True)
        row += 1

        # Divider
        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=(10, 10))

        # Specific Exit Node
        node_section = tk.Frame(inner, bg=COLORS["bg_card"])
        node_section.pack(fill=tk.X, padx=16, pady=4)
        node_section.columnconfigure(0, weight=1)

        tk.Label(node_section, text="LIVE EXIT NODE SELECTOR", font=FONTS["section"],
                 fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.exit_node_var = tk.StringVar(value="None (Use country settings)")
        self.exit_node_menu = ttk.Combobox(node_section, textvariable=self.exit_node_var,
            values=["None (Use country settings)"], state="readonly", style="Ghost.TCombobox")
        self.exit_node_menu.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        self.btn_refresh_nodes = GhostButton(node_section, "↻ Refresh",
            command=self.refresh_tor_nodes, height=30, width=100,
            font=FONTS["mono_small"], corner=4)
        self.btn_refresh_nodes.grid(row=1, column=1, sticky="e")

        # Divider
        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=(14, 10))

        # Tor action buttons
        tor_ops = tk.Frame(inner, bg=COLORS["bg_card"])
        tor_ops.pack(fill=tk.X, padx=16, pady=(0, 14))
        tor_ops.columnconfigure(0, weight=1)
        tor_ops.columnconfigure(1, weight=1)
        tor_ops.columnconfigure(2, weight=1)

        self.btn_tor_run = GhostButton(tor_ops, "▶ START TOR",
            command=lambda: threading.Thread(target=self.enable_tor, daemon=True).start(),
            height=34, font=FONTS["button"], corner=4)
        self.btn_tor_run.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_tor_stop = GhostButton(tor_ops, "■ STOP TOR",
            command=lambda: threading.Thread(target=self.stop_tor, daemon=True).start(),
            bg=COLORS["bg_elevated"], fg=COLORS["accent_orange"],
            hover_bg=COLORS["accent_orange"], hover_fg=COLORS["bg_deepest"],
            height=34, font=FONTS["button"], corner=4)
        self.btn_tor_stop.grid(row=0, column=1, sticky="ew", padx=4)

        self.btn_tor_test = GhostButton(tor_ops, "⚡ TEST",
            command=lambda: threading.Thread(target=self.test_tor, daemon=True).start(),
            bg=COLORS["bg_elevated"], fg=COLORS["accent_cyan"],
            hover_bg=COLORS["accent_cyan"], hover_fg=COLORS["bg_deepest"],
            height=34, font=FONTS["button"], corner=4)
        self.btn_tor_test.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        # Bind events
        exit_menu.bind("<<ComboboxSelected>>", self.on_exit_country_change)
        self.on_exit_country_change()

    # ─── Shredder Tab ────────────────────────────────────────────────────
    def _build_shredder_tab(self):
        frame = tk.Frame(self._tab_container, bg=COLORS["bg_card"])
        self._tab_frames["shredder"] = frame

        # Header
        hdr = tk.Frame(frame, bg=COLORS["bg_card"])
        hdr.pack(fill=tk.X, padx=16, pady=(12, 0))
        tk.Label(hdr, text="FILE SHREDDER & EXIF ERASER", font=FONTS["section"],
                 fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(side=tk.LEFT)
        tk.Frame(frame, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=16, pady=(8, 0))

        # Body: list + controls
        body = tk.Frame(frame, bg=COLORS["bg_card"])
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # File list
        list_frame = tk.Frame(body, bg=COLORS["bg_deepest"], bd=0)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.shred_listbox = tk.Listbox(list_frame, bg=COLORS["bg_deepest"],
            fg=COLORS["text_primary"], font=FONTS["mono_small"],
            selectbackground=COLORS["accent_red"], selectforeground="#FFFFFF",
            bd=0, highlightthickness=0, activestyle="none")
        self.shred_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)

        list_scroll = ttk.Scrollbar(list_frame, orient="vertical",
            command=self.shred_listbox.yview, style="Dark.Vertical.TScrollbar")
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.shred_listbox.configure(yscrollcommand=list_scroll.set)

        # Controls
        ctrls = tk.Frame(body, bg=COLORS["bg_card"])
        ctrls.grid(row=0, column=1, sticky="nsew")

        tk.Label(ctrls, text="Shred passes:", font=FONTS["body_small"],
                 fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(anchor="w", pady=(0, 4))

        self.passes_var = tk.StringVar(value="3 (DoD Standard)")
        passes_menu = ttk.Combobox(ctrls, textvariable=self.passes_var,
            values=["1 (Fast)", "3 (DoD Standard)", "7 (Gutmann)", "35 (Maximum)"],
            state="readonly", style="Ghost.TCombobox")
        passes_menu.pack(fill=tk.X, pady=(0, 12))

        buttons = [
            ("📂 Add Files",       self.shred_add_files,    COLORS["accent_green"]),
            ("📁 Add Directory",   self.shred_add_directory, COLORS["accent_green"]),
            ("✕ Remove Selected", self.shred_remove_selected, COLORS["accent_red"]),
            ("🧲 Strip EXIF",      lambda: threading.Thread(target=self.strip_exif_data, daemon=True).start(), COLORS["accent_orange"]),
            ("Clear Queue",       self.shred_clear_queue,   COLORS["text_dim"]),
        ]

        for text, cmd, color in buttons:
            b = GhostButton(ctrls, text, command=cmd,
                bg=COLORS["bg_elevated"], fg=color,
                hover_bg=color, hover_fg=COLORS["bg_deepest"],
                font=FONTS["mono_small"], height=30, corner=4)
            b.pack(fill=tk.X, pady=3)

    # ─── Actions Bar (always visible below tabs) ─────────────────────────
    def _build_actions_bar(self, parent):
        bar = tk.Frame(parent, bg=COLORS["bg_deep"])
        bar.pack(fill=tk.X, padx=(6, 0), pady=(8, 0))

        # Quick action buttons
        quick = tk.Frame(bar, bg=COLORS["bg_deep"])
        quick.pack(fill=tk.X, pady=(8, 6), padx=8)
        quick.columnconfigure(0, weight=1)
        quick.columnconfigure(1, weight=1)

        self.btn_ram_purge = GhostButton(quick, "🧠 RAM PURGE",
            command=lambda: threading.Thread(target=self.ram_purge, daemon=True).start(),
            bg=COLORS["bg_elevated"], fg=COLORS["accent_cyan"],
            hover_bg=COLORS["accent_cyan"], hover_fg=COLORS["bg_deepest"],
            height=32, font=FONTS["button"], corner=4)
        self.btn_ram_purge.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_wifi_kill = GhostButton(quick, "📡 DROP WI-FI",
            command=self.wifi_drop,
            bg=COLORS["bg_elevated"], fg=COLORS["accent_orange"],
            hover_bg=COLORS["accent_orange"], hover_fg=COLORS["bg_deepest"],
            height=32, font=FONTS["button"], corner=4)
        self.btn_wifi_kill.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Progress bar
        self.progress_bar = ttk.Progressbar(bar, orient="horizontal",
            mode="determinate", style="Ghost.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, padx=8, pady=(4, 6))

        # Execute button
        self.btn_execute = GhostButton(bar, "⚡ EXECUTE PRIVACY PROTOCOL",
            command=self.start_protocol_execution,
            bg=COLORS["accent_red"], fg="#FFFFFF",
            hover_bg=COLORS["accent_red_dim"], hover_fg="#FFFFFF",
            font=FONTS["button_large"], height=42, corner=6)
        self.btn_execute.pack(fill=tk.X, padx=8, pady=(0, 10))

    # ══════════════════════════════════════════════════════════════════════
    #  LOGGING
    # ══════════════════════════════════════════════════════════════════════
    def log(self, msg, msg_type="info"):
        tags = {
            "info":    ("tag_info",    "INFO"),
            "success": ("tag_success", " OK "),
            "warning": ("tag_warning", "WARN"),
            "error":   ("tag_error",   "FAIL"),
            "system":  ("tag_system",  " SYS"),
        }
        tag_name, prefix = tags.get(msg_type, ("tag_info", "INFO"))
        timestamp = time.strftime("%H:%M:%S")

        def write():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f" {timestamp} ", "tag_ts")
            self.log_text.insert(tk.END, f" {prefix} ", tag_name)
            self.log_text.insert(tk.END, f"  {msg}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, write)

    # ══════════════════════════════════════════════════════════════════════
    #  SYSTEM OPERATIONS (all backend logic preserved from original)
    # ══════════════════════════════════════════════════════════════════════
    def run_as_admin(self, command):
        """Runs a shell command with elevated root privileges via AppleScript dialog."""
        if os.geteuid() == 0:
            try:
                res = subprocess.run(command, shell=True, capture_output=True, text=True)
                return res.returncode, res.stdout, res.stderr
            except Exception as e:
                return 1, "", str(e)
        else:
            escaped_cmd = command.replace('"', '\\"')
            applescript = f'do shell script "{escaped_cmd}" with administrator privileges'
            try:
                res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
                return res.returncode, res.stdout, res.stderr
            except Exception as e:
                return 1, "", str(e)

    def on_exit_country_change(self, event=None):
        if self.exit_country_var.get() == "Custom":
            self.custom_exit_entry.config(state="normal")
        else:
            self.custom_exit_entry.delete(0, tk.END)
            self.custom_exit_entry.config(state="disabled")

    def refresh_tor_nodes(self):
        self.log("Fetching active exit nodes from Tor Metrics API...", "info")
        self.btn_refresh_nodes.set_disabled(True)
        self.exit_node_menu.config(state="disabled")

        def run():
            url = "https://onionoo.torproject.org/details?type=relay&running=true&flag=Exit&order=-consensus_weight&limit=50&fields=nickname,fingerprint,country,country_name"
            try:
                context = ssl._create_unverified_context()
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, context=context, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))

                relays = data.get("relays", [])
                options = ["None (Use country settings)"]
                for r in relays:
                    name = r.get("nickname", "Unnamed")
                    country = r.get("country_name", "Unknown")
                    fingerprint = r.get("fingerprint", "")
                    if fingerprint:
                        options.append(f"{name} ({country}) [{fingerprint[:12]}...{fingerprint[-12:]}]")

                self.fetched_relays = {
                    f"{r.get('nickname', 'Unnamed')} ({r.get('country_name', 'Unknown')}) [{r.get('fingerprint', '')[:12]}...{r.get('fingerprint', '')[-12:]}]": r.get("fingerprint")
                    for r in relays if r.get("fingerprint")
                }

                def update_ui():
                    self.exit_node_menu.config(values=options)
                    self.btn_refresh_nodes.set_disabled(False)
                    self.exit_node_menu.config(state="readonly")
                    self.log(f"Retrieved {len(relays)} active exit nodes.", "success")
                self.root.after(0, update_ui)

            except Exception as e:
                def on_error():
                    self.btn_refresh_nodes.set_disabled(False)
                    self.exit_node_menu.config(state="readonly")
                    self.log(f"Failed to fetch exit nodes: {e}", "error")
                self.root.after(0, on_error)

        threading.Thread(target=run, daemon=True).start()

    def ram_purge(self):
        self.log("Flushing RAM cache and purgeable memory...", "info")
        try:
            res = subprocess.run(["purge"], capture_output=True, text=True)
            if res.returncode == 0:
                self.log("RAM purge completed successfully.", "success")
            else:
                self.log(f"RAM purge failed: {res.stderr.strip()}", "error")
        except FileNotFoundError:
            self.log("'purge' binary not found. Requires Xcode CLI Tools.", "warning")
        except Exception as e:
            self.log(f"Unexpected RAM clean error: {e}", "error")

    def wifi_drop(self):
        self.log("Severing active Wi-Fi connection...", "warning")
        success = False
        try:
            res = subprocess.run(["wdutil", "disassociate"], capture_output=True)
            if res.returncode == 0:
                success = True
        except Exception:
            pass

        if not success:
            try:
                airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
                if os.path.exists(airport_path):
                    res2 = subprocess.run([airport_path, "-z"], capture_output=True)
                    if res2.returncode == 0:
                        success = True
            except Exception:
                pass

        if success:
            self.log("Wi-Fi connection severed.", "success")
        else:
            self.log("Wi-Fi disassociate failed.", "error")

    def strip_exif_data(self):
        if not self.shred_list:
            self.log("Shred queue is empty. Add files first.", "warning")
            return

        self.log(f"Scanning {len(self.shred_list)} files for metadata...", "info")
        stripped = 0
        for fp in list(self.shred_list):
            if not os.path.exists(fp):
                continue
            if not (fp.lower().endswith(".jpg") or fp.lower().endswith(".jpeg") or fp.lower().endswith(".png")):
                self.log(f"Skipping non-image: {os.path.basename(fp)}", "warning")
                continue

            try:
                with open(fp, "rb") as f:
                    data = f.read()

                cleaned_data = bytearray(data)

                if cleaned_data[:2] == b'\xff\xd8':
                    pos = 2
                    out = bytearray(b'\xff\xd8')
                    while pos < len(cleaned_data) - 1:
                        marker = cleaned_data[pos:pos+2]
                        if marker == b'\xff\xd9':
                            out.extend(cleaned_data[pos:])
                            break
                        if marker[0] == 0xff and 0xe0 <= marker[1] <= 0xef:
                            if pos + 4 > len(cleaned_data):
                                out.extend(cleaned_data[pos:])
                                break
                            length = int.from_bytes(cleaned_data[pos+2:pos+4], "big")
                            if length < 2 or pos + 2 + length > len(cleaned_data):
                                out.extend(cleaned_data[pos:])
                                break
                            pos += 2 + length
                        elif marker[0] == 0xff:
                            if pos + 4 > len(cleaned_data):
                                out.extend(cleaned_data[pos:])
                                break
                            length = int.from_bytes(cleaned_data[pos+2:pos+4], "big")
                            if length < 2 or pos + 2 + length > len(cleaned_data):
                                out.extend(cleaned_data[pos:])
                                break
                            out.extend(cleaned_data[pos:pos+2+length])
                            pos += 2 + length
                        else:
                            out.append(cleaned_data[pos])
                            pos += 1
                    cleaned_data = out

                with open(fp, "wb") as f:
                    f.write(cleaned_data)

                self.log(f"Stripped EXIF from {os.path.basename(fp)}", "success")
                stripped += 1
            except Exception as e:
                self.log(f"EXIF error on {os.path.basename(fp)}: {e}", "error")

        self.log(f"Metadata sanitization done. Cleaned {stripped} images.", "success")

    def trigger_panic(self):
        """Instant emergency shutdown."""
        self.log("!!! EMERGENCY PANIC !!!", "error")
        try:
            self.root.clipboard_clear()
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(input=b"")
        except Exception:
            pass

        self.force_safe_shutdown()

        if self.tor_process:
            try:
                self.tor_process.kill()
            except Exception:
                pass

        self.root.destroy()
        sys.exit(0)

    # ── Tor Management ────────────────────────────────────────────────────
    def detect_tor_binary(self):
        paths = ["/opt/homebrew/bin/tor", "/usr/local/bin/tor", "/usr/bin/tor"]
        self.tor_bin = None
        for path in paths:
            if os.path.exists(path):
                self.tor_bin = path
                break
        if not self.tor_bin:
            self.tor_bin = shutil.which("tor")
        if self.tor_bin:
            self.log(f"Tor binary: {self.tor_bin}", "success")
        else:
            self.log("Tor not found. Run 'brew install tor'.", "warning")

    def generate_temp_torrc(self):
        exit_val = ""

        selected_node = self.exit_node_var.get()
        if selected_node != "None (Use country settings)" and hasattr(self, "fetched_relays") and selected_node in self.fetched_relays:
            exit_val = "$" + self.fetched_relays[selected_node]
        else:
            country_sel = self.exit_country_var.get()
            if "United States" in country_sel:
                exit_val = "{us}"
            elif "Germany" in country_sel:
                exit_val = "{de}"
            elif "Switzerland" in country_sel:
                exit_val = "{ch}"
            elif "Iceland" in country_sel:
                exit_val = "{is}"
            elif "Custom" in country_sel:
                exit_val = self.custom_exit_entry.get().strip()

        strict_val = "1" if self.strict_nodes_toggle.is_on else "0"

        torrc_lines = [
            "SocksPort 127.0.0.1:9050",
            "ControlPort 127.0.0.1:9051",
            "CookieAuthentication 1"
        ]

        if hasattr(self, "exclude_five_eyes_toggle") and self.exclude_five_eyes_toggle.is_on:
            five_eyes = "{us},{gb},{ca},{au},{nz}"
            torrc_lines.append(f"ExcludeNodes {five_eyes}")
            torrc_lines.append(f"ExcludeExitNodes {five_eyes}")

        if hasattr(self, "safe_socks_toggle") and self.safe_socks_toggle.is_on:
            torrc_lines.append("SafeSocks 1")
            torrc_lines.append("TestSocks 1")

        if hasattr(self, "daemon_hardening_toggle") and self.daemon_hardening_toggle.is_on:
            torrc_lines.append("SafeLogging 1")
            torrc_lines.append("DisableDebuggerAttachment 1")
            torrc_lines.append("ClientRejectInternalAddresses 1")
            torrc_lines.append("ClientDNSRejectInternalAddresses 1")
            if sys.platform.startswith("linux"):
                torrc_lines.append("Sandbox 1")

        if exit_val:
            torrc_lines.append(f"ExitNodes {exit_val}")
            torrc_lines.append(f"StrictNodes {strict_val}")

        temp_dir = tempfile.gettempdir()
        torrc_path = os.path.join(temp_dir, "ghost_protocol_torrc")

        with open(torrc_path, "w") as f:
            f.write("\n".join(torrc_lines) + "\n")

        self.log(f"Generated torrc: {torrc_path}", "system")
        if exit_val:
            self.log(f"Exit nodes: {exit_val} (Strict: {'ON' if strict_val == '1' else 'OFF'})", "info")

        return torrc_path

    def enable_tor(self):
        if self.tor_process and self.tor_process.poll() is None:
            self.log("Tor is already active.", "warning")
            return
        if not self.tor_bin:
            self.log("Tor binary path missing.", "error")
            return

        torrc_path = self.generate_temp_torrc()

        self.log("Launching Tor daemon...", "info")
        try:
            self.tor_process = subprocess.Popen(
                [self.tor_bin, "-f", torrc_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(2.5)
            if self.tor_process.poll() is None:
                self.log(f"Tor running (PID: {self.tor_process.pid})", "success")
                self.root.after(0, lambda: self.tor_status_dot.set_color(COLORS["accent_green"]))
                if self.toggles["tor"].is_on:
                    self.configure_tor_proxies(True)
            else:
                self.log("Tor process exited immediately. Check config.", "error")
        except Exception as e:
            self.log(f"Error starting Tor: {e}", "error")

    def stop_tor(self):
        self.configure_tor_proxies(False)
        if self.tor_process:
            self.log("Stopping Tor daemon...", "info")
            try:
                self.tor_process.terminate()
                self.tor_process.wait(timeout=2.5)
                self.log("Tor stopped.", "success")
            except subprocess.TimeoutExpired:
                self.tor_process.kill()
                self.log("Tor killed.", "warning")
            except Exception as e:
                self.log(f"Tor stop error: {e}", "error")
            self.tor_process = None
            self.root.after(0, lambda: self.tor_status_dot.set_color(COLORS["accent_red"]))
        else:
            self.log("Tor is not running.", "info")

    def configure_tor_proxies(self, enabled):
        action = "Enabling" if enabled else "Disabling"
        self.log(f"{action} SOCKS proxies...", "info")
        try:
            res = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True, check=True)
            services = [s.strip() for s in res.stdout.split("\n")[1:] if s.strip() and "*" not in s]
        except Exception:
            services = ["Wi-Fi", "Ethernet"]

        success = 0
        for svc in services:
            try:
                if enabled:
                    subprocess.run(["networksetup", "-setsocksfirewallproxy", svc, "127.0.0.1", "9050"], capture_output=True, check=True)
                    subprocess.run(["networksetup", "-setsocksfirewallproxystate", svc, "on"], capture_output=True, check=True)
                else:
                    subprocess.run(["networksetup", "-setsocksfirewallproxystate", svc, "off"], capture_output=True, check=True)
                success += 1
            except Exception:
                pass
        self.log(f"Proxies updated on {success}/{len(services)} adapters.", "success")
        self.flush_dns()

    def test_tor(self):
        self.log("Testing Tor connectivity...", "info")
        try:
            curl_cmd = ["curl", "-s", "--socks5-hostname", "127.0.0.1:9050", "https://check.torproject.org/api/ip"]
            res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    if data.get("IsTor", False):
                        self.log(f"Tor ACTIVE — IP: {data.get('IP', '?')}", "success")
                    else:
                        self.log("Proxy responded but traffic not Tor-routed.", "warning")
                except json.JSONDecodeError:
                    self.log("Proxy responded with non-JSON data.", "warning")
            else:
                self.log("Tor proxy port unresponsive.", "error")
        except Exception as e:
            self.log(f"Connectivity check failed: {e}", "error")

    def on_tor_toggle(self, is_on):
        if not is_on:
            self.configure_tor_proxies(False)

    # ── Shredder Operations ──────────────────────────────────────────────
    def shred_add_files(self):
        files = filedialog.askopenfilenames(title="Select Files to Shred")
        if files:
            for f in files:
                if f not in self.shred_list:
                    self.shred_list.append(f)
                    self.shred_listbox.insert(tk.END, f)
            self.log(f"Added {len(files)} files to queue.", "info")

    def shred_add_directory(self):
        directory = filedialog.askdirectory(title="Select Directory to Shred")
        if directory:
            added = 0
            for root_dir, _, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(root_dir, filename)
                    if filepath not in self.shred_list:
                        self.shred_list.append(filepath)
                        self.shred_listbox.insert(tk.END, filepath)
                        added += 1
            self.log(f"Scanned dir. Added {added} items.", "info")

    def shred_remove_selected(self):
        selected_indices = self.shred_listbox.curselection()
        if not selected_indices:
            self.log("No files selected to remove.", "warning")
            return
        for idx in sorted(selected_indices, reverse=True):
            file_path = self.shred_listbox.get(idx)
            if file_path in self.shred_list:
                self.shred_list.remove(file_path)
            self.shred_listbox.delete(idx)
        self.log("Removed selected items.", "info")

    def shred_clear_queue(self):
        self.shred_list.clear()
        self.shred_listbox.delete(0, tk.END)
        self.log("Queue cleared.", "info")

    def execute_shredder(self, passes=3):
        if not self.shred_list:
            return
        total = len(self.shred_list)
        self.log(f"Shredding {total} files ({passes} passes)...", "warning")
        for filepath in list(self.shred_list):
            if not os.path.exists(filepath):
                continue
            try:
                size = os.path.getsize(filepath)
                if size == 0:
                    os.remove(filepath)
                    self.log(f"Removed empty: {os.path.basename(filepath)}", "success")
                    def remove_first_empty():
                        if self.shred_listbox.size() > 0:
                            self.shred_listbox.delete(0)
                    self.root.after(0, remove_first_empty)
                    continue
                with open(filepath, "wb+") as f:
                    for p in range(passes):
                        f.seek(0)
                        if p % 3 == 0:
                            f.write(b'\x00' * size)
                        elif p % 3 == 1:
                            f.write(b'\xFF' * size)
                        else:
                            f.write(os.urandom(size))
                        f.flush()
                        os.fsync(f.fileno())
                parent = os.path.dirname(filepath)
                rand = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=12))
                obscured = os.path.join(parent, rand)
                os.rename(filepath, obscured)
                os.remove(obscured)
                self.log(f"Shredded: {os.path.basename(filepath)}", "success")

                def remove_first():
                    if self.shred_listbox.size() > 0:
                        self.shred_listbox.delete(0)
                self.root.after(0, remove_first)
            except Exception as e:
                self.log(f"Failed to shred {filepath}: {e}", "error")
        self.shred_list.clear()

    # ── Clean & Privacy System Actions ───────────────────────────────────
    def flush_dns(self):
        self.log("Flushing DNS caches...", "info")
        try:
            subprocess.run(["dscacheutil", "-flushcache"], capture_output=True, check=True)
            subprocess.run(["killall", "-HUP", "mDNSResponder"], capture_output=True)
            self.log("DNS flushed.", "success")
        except Exception as e:
            self.log(f"DNS flush failed: {e}", "error")

    def scrub_terminals(self):
        self.log("Sanitizing terminal histories...", "info")
        home = os.path.expanduser("~")
        history = [".zsh_history", ".bash_history", ".sh_history", ".python_history", ".sqlite_history"]
        cleared = 0
        for h in history:
            path = os.path.join(home, h)
            if os.path.exists(path):
                try:
                    with open(path, "w") as f:
                        f.write("")
                    cleared += 1
                except Exception:
                    pass
        self.log(f"Scrubbed {cleared} history stores.", "success")

    def wipe_app_states(self):
        self.log("Purging saved app states & recents...", "info")
        home = os.path.expanduser("~")
        paths = [
            os.path.join(home, "Library/Saved Application State"),
            os.path.join(home, "Library/RecentDocuments"),
            os.path.join(home, "Library/Application Support/Apple/Finder/RecentFolders")
        ]
        wiped = 0
        for path in paths:
            if os.path.exists(path):
                try:
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path, ignore_errors=True)
                        else:
                            os.remove(item_path)
                    wiped += 1
                except Exception:
                    pass
        self.log(f"Cleaned {wiped} app state subsystems.", "success")

    def sinkhole_telemetry(self):
        self.log("Applying telemetry sinkholes to /etc/hosts...", "info")
        block_domains = [
            "telemetry.apple.com", "configuration.apple.com",
            "radars.apple.com", "securemetrics.apple.com",
            "metrics.apple.com", "xp.apple.com", "iphonesubmissions.apple.com",
            "diagnostics.apple.com"
        ]
        try:
            with open("/etc/hosts", "r") as f:
                content = f.read()
        except PermissionError:
            self.log("Permission denied reading /etc/hosts.", "error")
            return

        to_add = [d for d in block_domains if d not in content]
        if not to_add:
            self.log("Sinkholes already established.", "success")
            return

        hosts_append = "\\n# GHOST PROTOCOL SINKHOLE\\n"
        for d in to_add:
            hosts_append += f"0.0.0.0 {d}\\n"

        self.log("Requesting authorization for /etc/hosts...", "warning")
        append_cmd = f'printf "{hosts_append}" >> /etc/hosts'

        ret, stdout, stderr = self.run_as_admin(append_cmd)
        if ret == 0:
            self.log(f"Blocked {len(to_add)} telemetry servers.", "success")
        elif "User canceled" in stderr:
            self.log("Auth canceled by user.", "warning")
        else:
            self.log(f"Hosts update failed: {stderr.strip()}", "error")

    def toggle_spotlight(self, enable=False):
        status = "on" if enable else "off"
        self.log(f"Setting Spotlight to {status.upper()}...", "info")
        ret, stdout, stderr = self.run_as_admin(f"mdutil -i {status} /")
        if ret == 0:
            self.log(f"Spotlight set to {status.upper()}.", "success")
        elif "User canceled" in stderr:
            self.log("Auth canceled.", "warning")
        else:
            self.log(f"Spotlight config failed: {stderr.strip()}", "error")

    def kill_crashreporter(self):
        self.log("Killing crash reporters...", "info")
        try:
            subprocess.run(["killall", "-9", "CrashReporter"], capture_output=True)
            self.log("CrashReporter halted.", "success")
        except Exception:
            pass

    def purge_caches_logs(self, target_type):
        self.log(f"Wiping {target_type}...", "info")
        home = os.path.expanduser("~")
        if target_type == "caches":
            targets = [os.path.join(home, "Library/Caches"), "/Library/Caches"]
        else:
            targets = [os.path.join(home, "Library/Logs"), "/Library/Logs", "/var/log"]

        purged = 0
        for target in targets:
            if not os.path.exists(target):
                continue
            for root_dir, _, files in os.walk(target):
                for file in files:
                    fp = os.path.join(root_dir, file)
                    if "com.apple." in fp:
                        continue
                    try:
                        os.remove(fp)
                        purged += 1
                    except Exception:
                        pass
        self.log(f"Purged {purged} files from {target_type}.", "success")

    def purge_temp_files(self):
        self.log("Cleaning temp directories...", "info")
        paths = [tempfile.gettempdir(), "/tmp"]
        purged = 0
        for p in paths:
            if not os.path.exists(p):
                continue
            for item in os.listdir(p):
                item_path = os.path.join(p, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                    else:
                        os.remove(item_path)
                    purged += 1
                except Exception:
                    pass
        self.log(f"Cleaned {purged} temp items.", "success")

    def verify_active_browsers(self):
        """Returns list of running browser names."""
        running = []
        browsers = ["Safari", "Google Chrome", "Firefox", "Brave Browser"]
        for browser in browsers:
            try:
                res = subprocess.run(
                    ["osascript", "-e", f'application "{browser}" is running'],
                    capture_output=True, text=True
                )
                if res.stdout.strip() == "true":
                    running.append(browser)
            except Exception:
                pass
        return running

    def nuke_browsers(self):
        self.log("Scanning for active browsers...", "info")
        running_list = self.verify_active_browsers()
        if running_list:
            self.log(f"Active browsers: {', '.join(running_list)}", "error")
            self.log("Close browsers before sanitizing.", "warning")
            return

        self.log("Sanitizing browser data...", "info")
        home = os.path.expanduser("~")
        paths = {
            "Safari History": os.path.join(home, "Library/Safari/History.db"),
            "Safari LocalStorage": os.path.join(home, "Library/Safari/LocalStorage"),
            "Safari Cookies": os.path.join(home, "Library/Cookies"),
            "Safari Sandboxed Cookies": os.path.join(home, "Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies"),
            "Safari Sandboxed LS": os.path.join(home, "Library/Containers/com.apple.Safari/Data/Library/WebKit/WebsiteData/LocalStorage"),
            "Safari Sandboxed Cache": os.path.join(home, "Library/Containers/com.apple.Safari/Data/Library/Caches")
        }

        # Chrome profiles
        chrome_dir = os.path.join(home, "Library/Application Support/Google/Chrome")
        if os.path.exists(chrome_dir):
            try:
                for item in os.listdir(chrome_dir):
                    item_path = os.path.join(chrome_dir, item)
                    if os.path.isdir(item_path) and (item == "Default" or item.startswith("Profile ")):
                        paths[f"Chrome History ({item})"] = os.path.join(item_path, "History")
                        paths[f"Chrome Cookies ({item})"] = os.path.join(item_path, "Cookies")
                        paths[f"Chrome Login ({item})"] = os.path.join(item_path, "Login Data")
            except Exception:
                pass

        # Firefox profiles
        ff = os.path.join(home, "Library/Application Support/Firefox/Profiles")
        if os.path.exists(ff):
            try:
                for p_dir in os.listdir(ff):
                    p_path = os.path.join(ff, p_dir)
                    if os.path.isdir(p_path):
                        paths[f"Firefox Cookies ({p_dir[:8]})"] = os.path.join(p_path, "cookies.sqlite")
                        paths[f"Firefox History ({p_dir[:8]})"] = os.path.join(p_path, "places.sqlite")
            except Exception:
                pass

        # Brave profiles
        brave_dir = os.path.join(home, "Library/Application Support/BraveSoftware/Brave-Browser")
        if os.path.exists(brave_dir):
            try:
                for item in os.listdir(brave_dir):
                    item_path = os.path.join(brave_dir, item)
                    if os.path.isdir(item_path) and (item == "Default" or item.startswith("Profile ")):
                        paths[f"Brave History ({item})"] = os.path.join(item_path, "History")
                        paths[f"Brave Cookies ({item})"] = os.path.join(item_path, "Cookies")
                        paths[f"Brave Login ({item})"] = os.path.join(item_path, "Login Data")
            except Exception:
                pass

        cleaned = 0
        for label, db in paths.items():
            if os.path.exists(db):
                try:
                    if os.path.isdir(db):
                        shutil.rmtree(db, ignore_errors=True)
                    else:
                        os.remove(db)
                    self.log(f"Cleaned: {label}", "success")
                    cleaned += 1
                except Exception as e:
                    self.log(f"Failed: {label}: {e}", "warning")
        self.log(f"Browser purge done. Wiped {cleaned} items.", "success")

    def erase_clipboard(self):
        self.log("Erasing clipboard...", "info")
        try:
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(input=b"")
            self.root.clipboard_clear()
            self.log("Clipboard cleared.", "success")
        except Exception as e:
            self.log(f"Clipboard error: {e}", "error")

    # ── Protocol Execution Runner ────────────────────────────────────────
    def start_protocol_execution(self):
        if self.toggles["browsers"].is_on:
            running_list = self.verify_active_browsers()
            if running_list:
                ans = messagebox.askyesno("Active Browsers Detected", 
                                         f"The following browsers are running: {', '.join(running_list)}.\n\nWould you like Ghost Protocol to close them and proceed with cleaning?")
                if ans:
                    self.log("Attempting to close active browsers gracefully...", "info")
                    for browser in running_list:
                        subprocess.run(["osascript", "-e", f'tell application "{browser}" to quit'])
                    
                    # Wait up to 5 seconds
                    closed_all = False
                    for _ in range(10):
                        self.root.update()
                        time.sleep(0.5)
                        still_running = self.verify_active_browsers()
                        if not still_running:
                            closed_all = True
                            break
                    
                    if not closed_all:
                        still_running = self.verify_active_browsers()
                        ans_force = messagebox.askyesno("Force Close Browsers?", 
                                                         f"Some browsers failed to close: {', '.join(still_running)}.\n\nWould you like to force close them? Warning: Unsaved changes will be lost.")
                        if ans_force:
                            self.log("Force closing browsers...", "warning")
                            browser_map = {
                                "Safari": "Safari",
                                "Google Chrome": "Google Chrome",
                                "Firefox": "firefox",
                                "Brave Browser": "Brave Browser"
                             }
                            for browser in still_running:
                                proc = browser_map.get(browser)
                                if proc:
                                    subprocess.run(["killall", "-9", proc], capture_output=True)
                            time.sleep(1)
                            still_running = self.verify_active_browsers()
                            if still_running:
                                messagebox.showerror("Error", f"Failed to close browsers: {', '.join(still_running)}")
                                return
                        else:
                            self.log("Protocol aborted by user due to active browsers.", "warning")
                            return
                else:
                    self.log("Protocol aborted by user.", "warning")
                    return

        self.btn_execute.set_disabled(True)
        self.btn_execute._text = "⏳ EXECUTING..."
        self.btn_execute._redraw()
        self.root.after(0, lambda: self.progress_bar.config(value=0))
        threading.Thread(target=self._run_protocol_thread, daemon=True).start()

    def _run_protocol_thread(self):
        self.log("STARTING HARDENING PROTOCOLS...", "system")
        active = [key for key, toggle in self.toggles.items() if toggle.is_on]
        has_shred = len(self.shred_list) > 0
        total = len(active) + (1 if has_shred else 0)

        if total == 0:
            self.log("No modules toggled.", "warning")
            self.root.after(0, lambda: self.progress_bar.config(value=100))
            self.root.after(0, lambda: self.btn_execute.set_disabled(False))
            def reset_text():
                self.btn_execute._text = "⚡ EXECUTE PRIVACY PROTOCOL"
                self.btn_execute._redraw()
            self.root.after(0, reset_text)
            return

        task_map = {
            "tor": lambda: self.configure_tor_proxies(True),
            "dns": self.flush_dns,
            "term": self.scrub_terminals,
            "clip": self.erase_clipboard,
            "state": self.wipe_app_states,
            "hosts": self.sinkhole_telemetry,
            "spotlight": lambda: self.toggle_spotlight(False),
            "telem": self.kill_crashreporter,
            "caches": lambda: self.purge_caches_logs("caches"),
            "logs": lambda: self.purge_caches_logs("logs"),
            "temp": self.purge_temp_files,
            "browsers": self.nuke_browsers,
        }

        done = 0
        for task in active:
            self.log(f"Running: {task.upper()}", "system")
            handler = task_map.get(task)
            if handler:
                handler()
            done += 1
            pct = int((done / total) * 100)
            self.root.after(0, lambda v=pct: self.progress_bar.config(value=v))
            time.sleep(0.3)

        if has_shred:
            pass_str = self.passes_var.get()
            try:
                passes = int(pass_str.split()[0])
            except (ValueError, IndexError):
                passes = 3
            self.execute_shredder(passes=passes)
            self.root.after(0, lambda: self.progress_bar.config(value=100))

        self.log("ALL PROTOCOLS COMPLETED.", "success")
        self.root.after(0, lambda: self.btn_execute.set_disabled(False))
        def reset_text():
            self.btn_execute._text = "⚡ EXECUTE PRIVACY PROTOCOL"
            self.btn_execute._redraw()
        self.root.after(0, reset_text)

    # ── Shutdown & Cleanup ───────────────────────────────────────────────
    def force_safe_shutdown(self):
        try:
            _subprocess = subprocess
            if _subprocess is None:
                return
            res = _subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True)
            services = [s.strip() for s in res.stdout.split("\n")[1:] if s.strip() and "*" not in s]
        except Exception:
            services = ["Wi-Fi", "Ethernet"]

        try:
            for svc in services:
                try:
                    subprocess.run(["networksetup", "-setsocksfirewallproxystate", svc, "off"], capture_output=True)
                except Exception:
                    pass
            subprocess.run(["dscacheutil", "-flushcache"], capture_output=True)
        except Exception:
            pass

    def on_window_close(self):
        self.log("Restoring network defaults...", "info")
        if self.tor_process:
            self.stop_tor()
        self.force_safe_shutdown()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GhostProtocolUnified(root)
    root.mainloop()
