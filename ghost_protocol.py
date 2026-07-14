#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import random
import threading
import json
import urllib.request
import tempfile
import atexit
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Custom Colored High-Contrast Button for macOS compatibility with Disable support
class CyberButton(tk.Label):
    def __init__(self, parent, text, command=None, bg="#161722", fg="#00E676", active_bg="#00E676", active_fg="#000000", font=('Courier New', 11, 'bold'), height=1, pady=6):
        self.command = command
        self.default_bg = bg
        self.default_fg = fg
        self.active_bg = active_bg
        self.active_fg = active_fg
        self.is_disabled = False
        
        super().__init__(
            parent, 
            text=text, 
            bg=bg, 
            fg=fg, 
            font=font, 
            relief="flat", 
            bd=1,
            highlightbackground=fg,
            highlightthickness=1,
            cursor="hand2",
            height=height,
            pady=pady
        )
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def on_enter(self, event=None):
        if not self.is_disabled:
            self.config(bg=self.active_bg, fg=self.active_fg, highlightbackground=self.active_fg)

    def on_leave(self, event=None):
        if not self.is_disabled:
            self.config(bg=self.default_bg, fg=self.default_fg, highlightbackground=self.default_fg)

    def on_click(self, event=None):
        if not self.is_disabled and self.command:
            # Short flash effect
            self.config(bg="#FFFFFF", fg="#000000")
            self.after(80, lambda: self.config(bg=self.active_bg, fg=self.active_fg) if not self.is_disabled else None)
            self.command()

    def set_disabled(self, disabled=True):
        self.is_disabled = disabled
        if disabled:
            self.config(bg="#333333", fg="#666666", highlightbackground="#444444", cursor="arrow")
        else:
            self.config(bg=self.default_bg, fg=self.default_fg, highlightbackground=self.default_fg, cursor="hand2")

# Custom Animated Canvas Toggle Switch
class CanvasToggle(tk.Canvas):
    def __init__(self, parent, default_state=False, command=None, width=54, height=26):
        self.is_on = default_state
        self.command = command
        self.width = width
        self.height = height
        
        bg_color = parent.cget("bg") if hasattr(parent, "cget") else "#0A0A0E"
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, cursor="hand2")
        
        self.left_x = 13
        self.right_x = width - 13
        self.current_x = self.right_x if self.is_on else self.left_x
        
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def draw(self):
        self.delete("all")
        track_color = "#00E676" if self.is_on else "#2C2C35"
        knob_color = "#FFFFFF" if self.is_on else "#90909A"
        
        self.create_line(13, self.height/2, self.width - 13, self.height/2, width=self.height, capstyle="round", fill=track_color)
        r = (self.height - 6) / 2
        self.create_oval(self.current_x - r, self.height/2 - r, self.current_x + r, self.height/2 + r, fill=knob_color, outline="")

    def toggle(self, event=None):
        self.is_on = not self.is_on
        self.animate()
        if self.command:
            self.command(self.is_on)

    def animate(self):
        target_x = self.right_x if self.is_on else self.left_x
        steps = 6
        dx = (target_x - self.current_x) / steps
        
        def step(count):
            if count < steps:
                self.current_x += dx
                self.draw()
                self.after(15, lambda: step(count + 1))
            else:
                self.current_x = target_x
                self.draw()
        step(0)

class GhostProtocolUnified:
    def __init__(self, root):
        self.root = root
        self.root.title("Ghost Protocol - Absolute Privacy")
        self.root.geometry("1200x950")
        self.root.configure(bg="#050507")
        self.root.resizable(True, True)
        self.root.minsize(1100, 800)
        
        self.tor_process = None
        self.shred_list = []
        
        # Panic self-destruct hotkey
        self.root.bind("<Escape>", lambda e: self.trigger_panic())
        
        atexit.register(self.force_safe_shutdown)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        self.setup_styles()
        self.build_ui()
        
        self.log("SYSTEM INITIALIZED - PANIC KEY [ESC] REGISTERED", "success")
        self.log(f"OS Platform: {sys.platform.upper()}", "info")
        self.detect_tor_binary()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Vertical.TScrollbar", gripcount=0, background="#12121A", darkcolor="#050507", lightcolor="#1A1A24", troughcolor="#050507", bordercolor="#12121A")
        style.map("Vertical.TScrollbar", background=[('active', '#1A1A24'), ('pressed', '#00E676')])
        style.configure("TCombobox", fieldbackground="#0E0F16", background="#161722", foreground="#FFFFFF", bordercolor="#1F2937", arrowcolor="#00E676")
        style.map("TCombobox", fieldbackground=[('readonly', '#0E0F16')], selectbackground=[('readonly', '#161722')], selectforeground=[('readonly', '#00E676')])

    def build_ui(self):
        main_container = tk.Frame(self.root, bg="#050507")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title Header
        header_frame = tk.Frame(main_container, bg="#050507")
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(header_frame, text="GHOST PROTOCOL", font=('Helvetica Neue', 26, 'bold'), fg="#FFFFFF", bg="#050507")
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(header_frame, text="// GHOST OPERATION PROFILE // PANIC PRESS [ESC]", font=('Courier New', 11, 'bold'), fg="#FF375F", bg="#050507")
        subtitle_label.pack(side=tk.LEFT, padx=20, pady=(10, 0))
        
        # PANIC self-destruct button in header
        panic_btn = CyberButton(header_frame, " PANIC SHUTDOWN ", command=self.trigger_panic, bg="#FF375F", fg="#FFFFFF", active_bg="#FF6B8B", active_fg="#FFFFFF", font=('Courier New', 11, 'bold'), pady=2)
        panic_btn.pack(side=tk.RIGHT)
        
        # 2-Column Split Pane
        paned = tk.PanedWindow(main_container, orient=tk.HORIZONTAL, bg="#111115", bd=0, sashwidth=4, sashpad=2)
        paned.pack(fill=tk.BOTH, expand=True)
        
        left_scrollable_container = tk.Frame(paned, bg="#0A0A0F")
        right_frame = tk.Frame(paned, bg="#050507")
        
        paned.add(left_scrollable_container, minsize=480, stretch="always")
        paned.add(right_frame, minsize=520, stretch="always")
        
        # LEFT COLUMN: Scrollable Toggles
        canvas = tk.Canvas(left_scrollable_container, bg="#0A0A0F", highlightthickness=0)
        scroll = ttk.Scrollbar(left_scrollable_container, orient="vertical", command=canvas.yview)
        
        self.toggles_frame = tk.Frame(canvas, bg="#0A0A0F")
        self.toggles_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.create_window((0, 0), window=self.toggles_frame, anchor="nw", width=460)
        canvas.configure(yscrollcommand=scroll.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.toggles = {}
        
        # Network
        self.add_section_header("ANONYMOUS ROUTING")
        self.add_toggle("tor", "Enforce Traffic via Tor Proxy (SOCKS5)", False, self.on_tor_toggle)
        self.add_toggle("dns", "Flush DNS Cache & Resolver Configuration", True)
        
        # Clean
        self.add_section_header("METADATA & FOOTPRINT CLEANUP")
        self.add_toggle("term", "Purge Shell command history buffers", True)
        self.add_toggle("clip", "Securely erase clipboard memory buffer", True)
        self.add_toggle("state", "Wipe OS Saved application states & recents", True)
        
        # Hardening
        self.add_section_header("TELEMETRY & SINKHOLING")
        self.add_toggle("hosts", "Sinkhole Apple Diagnostics (/etc/hosts)", False)
        self.add_toggle("spotlight", "Disable local Spotlight Indexing (mdutil)", False)
        self.add_toggle("telem", "Kill active crash reporting processes", True)
        
        # Cleaning
        self.add_section_header("FILE SYSTEM HYGIENE")
        self.add_toggle("caches", "Purge system cache directories", False)
        self.add_toggle("logs", "Nuke log directories and events", False)
        self.add_toggle("temp", "Purge temporary storage directory lists", False)
        self.add_toggle("browsers", "Nuke browser local cookies and history DBs", True)
        
        tk.Frame(self.toggles_frame, bg="#0A0A0F", height=15).pack()
        
        # RIGHT COLUMN: Console, Shredder & Operations
        right_frame.grid_rowconfigure(0, weight=3)
        right_frame.grid_rowconfigure(1, weight=2)
        right_frame.grid_rowconfigure(2, weight=0)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # 1. Console
        console_wrapper = tk.LabelFrame(right_frame, text=" AUDIT TRAIL LOG ", font=('Courier New', 11, 'bold'), bg="#050507", fg="#00E676", bd=1, labelanchor="nw")
        console_wrapper.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.log_text = tk.Text(console_wrapper, bg="#000000", fg="#00E676", font=('Courier New', 11), bd=0, highlightthickness=0, padx=10, pady=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        console_scroll = ttk.Scrollbar(console_wrapper, orient="vertical", command=self.log_text.yview)
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=console_scroll.set)
        
        self.log_text.tag_config("tag_info", foreground="#00F0FF")
        self.log_text.tag_config("tag_success", foreground="#39FF14")
        self.log_text.tag_config("tag_warning", foreground="#FF9F0A")
        self.log_text.tag_config("tag_error", foreground="#FF375F")
        self.log_text.tag_config("tag_system", foreground="#8E8E93")
        
        # 2. File Shredder & EXIF Cleaner
        shredder_wrapper = tk.LabelFrame(right_frame, text=" ANTI-FORENSICS / FILE SHREDDER & EXIF ERASER ", font=('Courier New', 11, 'bold'), bg="#050507", fg="#FF375F", bd=1, labelanchor="nw")
        shredder_wrapper.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        shredder_wrapper.grid_rowconfigure(0, weight=1)
        shredder_wrapper.grid_columnconfigure(0, weight=2)
        shredder_wrapper.grid_columnconfigure(1, weight=1)
        
        list_container = tk.Frame(shredder_wrapper, bg="#0A0A0F", bd=1, relief="sunken")
        list_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.shred_listbox = tk.Listbox(list_container, bg="#0A0A0F", fg="#E2E8F0", font=('Helvetica', 11), selectbackground="#FF375F", selectforeground="#FFFFFF", bd=0, highlightthickness=0)
        self.shred_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        list_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.shred_listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.shred_listbox.configure(yscrollcommand=list_scroll.set)
        
        # Shredder Controls Panel
        shred_ctrls = tk.Frame(shredder_wrapper, bg="#050507")
        shred_ctrls.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        
        tk.Label(shred_ctrls, text="Shred passes:", font=('Helvetica', 11), fg="#9CA3AF", bg="#050507").pack(anchor="w", pady=(0, 2))
        
        self.passes_var = tk.StringVar(value="3 (DoD Standard)")
        passes_menu = ttk.Combobox(shred_ctrls, textvariable=self.passes_var, values=["1 (Fast)", "3 (DoD Standard)", "7 (Gutmann)", "35 (Maximum)"], state="readonly")
        passes_menu.pack(fill=tk.X, pady=(0, 10))
        
        btn_add = CyberButton(shred_ctrls, " Add Files... ", command=self.shred_add_files)
        btn_add.pack(fill=tk.X, pady=3)
        
        btn_add_dir = CyberButton(shred_ctrls, " Add Directory... ", command=self.shred_add_directory)
        btn_add_dir.pack(fill=tk.X, pady=3)
        
        btn_remove = CyberButton(shred_ctrls, " Remove Selected ", command=self.shred_remove_selected, bg="#111115", fg="#FF375F")
        btn_remove.pack(fill=tk.X, pady=3)
        
        btn_strip_exif = CyberButton(shred_ctrls, " Strip Image EXIF ", command=lambda: threading.Thread(target=self.strip_exif_data, daemon=True).start(), bg="#FF9F0A", fg="#000000", active_bg="#FFAA33", active_fg="#000000")
        btn_strip_exif.pack(fill=tk.X, pady=3)
        
        btn_clear_list = CyberButton(shred_ctrls, " Clear Queue ", command=self.shred_clear_queue, bg="#111115", fg="#9CA3AF")
        btn_clear_list.pack(fill=tk.X, pady=3)
        
        # 3. Main Launch Actions & Progress Row
        actions_panel = tk.Frame(right_frame, bg="#050507")
        actions_panel.grid(row=2, column=0, sticky="ew", padx=5, pady=(5, 0))
        
        # Tor Settings Wrapper Frame
        tor_config_wrapper = tk.LabelFrame(actions_panel, text=" TOR ROUTING SETTINGS ", font=('Courier New', 11, 'bold'), bg="#050507", fg="#00E676", bd=1, labelanchor="nw")
        tor_config_wrapper.pack(fill=tk.X, pady=(5, 5))
        
        tor_config_wrapper.columnconfigure(0, weight=1)
        tor_config_wrapper.columnconfigure(1, weight=2)
        
        # Exit Country Selection
        tk.Label(tor_config_wrapper, text="Exit Country:", font=('Helvetica', 11), fg="#9CA3AF", bg="#050507", anchor="w").grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.exit_country_var = tk.StringVar(value="Any (Default)")
        exit_menu = ttk.Combobox(tor_config_wrapper, textvariable=self.exit_country_var, values=["Any (Default)", "United States {us}", "Germany {de}", "Switzerland {ch}", "Iceland {is}", "Custom"], state="readonly")
        exit_menu.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # Custom Exit Nodes (IP / Country / Fingerprint)
        tk.Label(tor_config_wrapper, text="Custom Exit Nodes:", font=('Helvetica', 11), fg="#9CA3AF", bg="#050507", anchor="w").grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.custom_exit_entry = tk.Entry(tor_config_wrapper, bg="#0E0F16", fg="#FFFFFF", font=('Courier New', 11), insertbackground="#FFFFFF", bd=1, relief="solid", highlightthickness=0)
        self.custom_exit_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        # Enforce Strict Exit Nodes
        tk.Label(tor_config_wrapper, text="Enforce Strict Nodes:", font=('Helvetica', 11), fg="#9CA3AF", bg="#050507", anchor="w").grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        strict_toggle_frame = tk.Frame(tor_config_wrapper, bg="#050507")
        strict_toggle_frame.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self.strict_nodes_toggle = CanvasToggle(strict_toggle_frame, default_state=False, width=50, height=22)
        self.strict_nodes_toggle.pack()
        
        # Bind Selector Event
        exit_menu.bind("<<ComboboxSelected>>", self.on_exit_country_change)
        self.on_exit_country_change()
        
        # Advanced Professional Actions
        pro_ops = tk.Frame(actions_panel, bg="#050507")
        pro_ops.pack(fill=tk.X, pady=3)
        
        self.btn_ram_purge = CyberButton(pro_ops, " RAM PURGE ", command=lambda: threading.Thread(target=self.ram_purge, daemon=True).start(), bg="#111115", fg="#00F0FF")
        self.btn_ram_purge.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.btn_wifi_kill = CyberButton(pro_ops, " DROP WI-FI ", command=self.wifi_drop, bg="#111115", fg="#FF9F0A")
        self.btn_wifi_kill.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Tor Operations Row
        tor_ops = tk.Frame(actions_panel, bg="#050507")
        tor_ops.pack(fill=tk.X, pady=2)
        
        self.btn_tor_run = CyberButton(tor_ops, " START TOR ", command=lambda: threading.Thread(target=self.enable_tor, daemon=True).start())
        self.btn_tor_run.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.btn_tor_stop = CyberButton(tor_ops, " STOP TOR ", command=lambda: threading.Thread(target=self.stop_tor, daemon=True).start())
        self.btn_tor_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.btn_tor_test = CyberButton(tor_ops, " TEST TOR ", command=lambda: threading.Thread(target=self.test_tor, daemon=True).start())
        self.btn_tor_test.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Progress Bar & Executive Run Button
        self.progress_bar = ttk.Progressbar(actions_panel, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))
        
        self.btn_execute = CyberButton(actions_panel, " EXECUTE PRIVACY PROTOCOL ", command=self.start_protocol_execution, bg="#FF375F", fg="#FFFFFF", active_bg="#FF6B8B", active_fg="#FFFFFF", font=('Helvetica', 14, 'bold'))
        self.btn_execute.pack(fill=tk.X, pady=(0, 5))

    def add_section_header(self, title):
        header_frame = tk.Frame(self.toggles_frame, bg="#111118", height=24)
        header_frame.pack(fill=tk.X, pady=(15, 6))
        label = tk.Label(header_frame, text=f"■ {title}", font=('Courier New', 11, 'bold'), fg="#00E676", bg="#111118", anchor="w", padx=10)
        label.pack(fill=tk.BOTH, expand=True)

    def add_toggle(self, key, label_text, default, command=None):
        row = tk.Frame(self.toggles_frame, bg="#0A0A0F")
        row.pack(fill=tk.X, padx=15, pady=6)
        lbl = tk.Label(row, text=label_text, font=('Helvetica', 12), fg="#E2E8F0", bg="#0A0A0F", anchor="w")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        toggle = CanvasToggle(row, default_state=default, command=command)
        toggle.pack(side=tk.RIGHT, padx=(10, 0))
        self.toggles[key] = toggle

    def log(self, msg, msg_type="info"):
        tags = {
            "info": ("tag_info", "[INFO]"),
            "success": ("tag_success", "[OK]  "),
            "warning": ("tag_warning", "[WARN]"),
            "error": ("tag_error", "[FAIL]"),
            "system": ("tag_system", "[SYS] ")
        }
        tag_name, prefix = tags.get(msg_type, ("tag_info", "[*]  "))
        timestamp = time.strftime("%H:%M:%S")
        
        def write():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"{timestamp} ")
            self.log_text.insert(tk.END, prefix + " ", tag_name)
            self.log_text.insert(tk.END, f"{msg}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, write)

    # ==================== ADVANCED GHOST FEATURES ====================
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
            self.custom_exit_entry.config(state="normal", bg="#0E0F16", fg="#FFFFFF")
        else:
            self.custom_exit_entry.delete(0, tk.END)
            self.custom_exit_entry.config(state="disabled", bg="#222228", fg="#888888")

    def ram_purge(self):
        self.log("Flushing disk dynamic cache buffer and purgeable memory...", "info")
        try:
            res = subprocess.run(["purge"], capture_output=True, text=True)
            if res.returncode == 0:
                self.log("RAM cache memory purge completed successfully.", "success")
            else:
                self.log(f"RAM purge failed: {res.stderr.strip()}", "error")
        except FileNotFoundError:
            self.log("System 'purge' binary not found. Requires Xcode Command Line Tools.", "warning")
        except Exception as e:
            self.log(f"Unexpected RAM clean error: {e}", "error")

    def wifi_drop(self):
        self.log("Severing active Wi-Fi radio connection...", "warning")
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
            self.log("Wi-Fi network connection closed.", "success")
        else:
            self.log("Wi-Fi disassociate failed or network utilities not available.", "error")


    def strip_exif_data(self):
        if not self.shred_list:
            self.log("Shred queue is empty. Drag or add files first.", "warning")
            return
            
        self.log(f"Scanning {len(self.shred_list)} files for metadata fields...", "info")
        stripped = 0
        for fp in list(self.shred_list):
            if not os.path.exists(fp):
                continue
            if not (fp.lower().endswith(".jpg") or fp.lower().endswith(".jpeg") or fp.lower().endswith(".png")):
                self.log(f"Skipping non-image file: {os.path.basename(fp)}", "warning")
                continue
                
            try:
                with open(fp, "rb") as f:
                    data = f.read()
                
                cleaned_data = bytearray(data)
                
                # Check for JPEG Start of Image (SOI) header
                if cleaned_data[:2] == b'\xff\xd8':
                    pos = 2
                    out = bytearray(b'\xff\xd8')
                    while pos < len(cleaned_data) - 1:
                        marker = cleaned_data[pos:pos+2]
                        if marker == b'\xff\xd9': # EOI
                            out.extend(b'\xff\xd9')
                            break
                        if marker[0] == 0xff and marker[1] >= 0xe0 and marker[1] <= 0xef:
                            length = int.from_bytes(cleaned_data[pos+2:pos+4], "big")
                            pos += 2 + length
                        else:
                            if marker[0] == 0xff:
                                length = int.from_bytes(cleaned_data[pos+2:pos+4], "big")
                                out.extend(cleaned_data[pos:pos+2+length])
                                pos += 2 + length
                            else:
                                out.append(cleaned_data[pos])
                                pos += 1
                    cleaned_data = out
                
                with open(fp, "wb") as f:
                    f.write(cleaned_data)
                
                self.log(f"Stripped EXIF metadata segments from {os.path.basename(fp)}", "success")
                stripped += 1
            except Exception as e:
                self.log(f"EXIF cleaner error on {os.path.basename(fp)}: {e}", "error")
                
        self.log(f"Metadata sanitization finished. Wiped data headers on {stripped} images.", "success")

    def trigger_panic(self):
        """Instant emergency self destruct program shutdown."""
        self.log("!!! EMERGENCY PANIC ACTION RECEIVED !!!", "error")
        self.log("Scrubbing volatile memory buffers...", "warning")
        
        # 1. Clear clipboard immediately
        try:
            self.root.clipboard_clear()
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(input=b'')
        except Exception:
            pass
            
        # 2. Reset Proxy Routing
        self.force_safe_shutdown()
        
        # 3. Kill Tor process instantly
        if self.tor_process:
            try:
                self.tor_process.kill()
            except Exception:
                pass
                
        self.log("Anti-forensics handshakes complete. Destroying UI thread.", "success")
        self.root.destroy()
        sys.exit(0)

    # ==================== TOR MANAGEMENT ====================
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
            self.log(f"Tor binary detected: {self.tor_bin}", "success")
        else:
            self.log("Tor binary not found. Run 'brew install tor' to support Tor Routing.", "warning")

    def generate_temp_torrc(self):
        exit_val = ""
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
            "SocksPort 9050",
            "ControlPort 9051",
            "CookieAuthentication 1"
        ]
        
        if exit_val:
            torrc_lines.append(f"ExitNodes {exit_val}")
            torrc_lines.append(f"StrictNodes {strict_val}")
            
        temp_dir = tempfile.gettempdir()
        torrc_path = os.path.join(temp_dir, "ghost_protocol_torrc")
        
        with open(torrc_path, "w") as f:
            f.write("\n".join(torrc_lines) + "\n")
            
        self.log(f"Generated dynamic torrc at: {torrc_path}", "system")
        if exit_val:
            self.log(f"Configured exit nodes: {exit_val} (Strict: {'ON' if strict_val == '1' else 'OFF'})", "info")
            
        return torrc_path

    def enable_tor(self):
        if self.tor_process and self.tor_process.poll() is None:
            self.log("Tor is already active.", "warning")
            return
        if not self.tor_bin:
            self.log("Tor binary path missing.", "error")
            return
            
        # Write config template dynamically
        torrc_path = self.generate_temp_torrc()
        
        self.log("Launching Tor background process daemon...", "info")
        try:
            self.tor_process = subprocess.Popen(
                [self.tor_bin, "-f", torrc_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(2.5)
            if self.tor_process.poll() is None:
                self.log(f"Tor process running successfully (PID: {self.tor_process.pid})", "success")
                if self.toggles["tor"].is_on:
                    self.configure_tor_proxies(True)
            else:
                self.log("Tor process halted instantly on execution. Check exit node inputs.", "error")
        except Exception as e:
            self.log(f"Error starting Tor process: {e}", "error")

    def stop_tor(self):
        self.configure_tor_proxies(False)
        if self.tor_process:
            self.log("Halting Tor daemon...", "info")
            try:
                self.tor_process.terminate()
                self.tor_process.wait(timeout=2.5)
                self.log("Tor process stopped.", "success")
            except subprocess.TimeoutExpired:
                self.tor_process.kill()
                self.log("Tor process killed.", "warning")
            except Exception as e:
                self.log(f"Tor stop error: {e}", "error")
            self.tor_process = None
        else:
            self.log("Tor daemon is not running.", "info")

    def configure_tor_proxies(self, enabled):
        action = "Enabling" if enabled else "Disabling"
        self.log(f"{action} proxy interfaces...", "info")
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
        self.log("Checking proxy connectivity status...", "info")
        try:
            curl_cmd = ["curl", "-s", "--socks5-hostname", "127.0.0.1:9050", "https://check.torproject.org/api/ip"]
            res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    if data.get("IsTor", False):
                        self.log(f"Tor Routing Active. Verified IP: {data.get('IP', 'Unknown')}", "success")
                    else:
                        self.log("Local proxy connection responded, but traffic route is not marked as Tor.", "warning")
                except json.JSONDecodeError:
                    self.log(f"Local proxy responded, but connection check returned non-JSON format.", "warning")
            else:
                self.log("Local Tor proxy port is unresponsive.", "error")
        except Exception as e:
            self.log(f"Connectivity check failed: {e}", "error")

    def on_tor_toggle(self, is_on):
        if not is_on:
            self.configure_tor_proxies(False)

    # ==================== SHREDDER OPERATIONS ====================
    def shred_add_files(self):
        files = filedialog.askopenfilenames(title="Select Files to Shred")
        if files:
            for f in files:
                if f not in self.shred_list:
                    self.shred_list.append(f)
                    self.shred_listbox.insert(tk.END, f)
            self.log(f"Added {len(files)} files to sanitization queue.", "info")

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
            self.log("No files selected in queue to remove.", "warning")
            return
        for idx in sorted(selected_indices, reverse=True):
            file_path = self.shred_listbox.get(idx)
            if file_path in self.shred_list:
                self.shred_list.remove(file_path)
            self.shred_listbox.delete(idx)
        self.log("Removed selected items from the queue.", "info")

    def shred_clear_queue(self):
        self.shred_list.clear()
        self.shred_listbox.delete(0, tk.END)
        self.log("Sanitization queue cleared.", "info")

    def execute_shredder(self, passes=3):
        if not self.shred_list:
            return
        total = len(self.shred_list)
        self.log(f"Executing secure shredder on {total} files (Passes: {passes})...", "warning")
        for filepath in list(self.shred_list):
            if not os.path.exists(filepath):
                continue
            try:
                size = os.path.getsize(filepath)
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

    # ==================== CLEAN & PRIVACY SYSTEM ACTIONS ====================
    def flush_dns(self):
        self.log("Flushing DNS caches...", "info")
        try:
            subprocess.run(["dscacheutil", "-flushcache"], capture_output=True, check=True)
            subprocess.run(["killall", "-HUP", "mDNSResponder"], capture_output=True)
            self.log("DNS Flush successful.", "success")
        except Exception as e:
            self.log(f"Failed to flush DNS caches: {e}", "error")

    def scrub_terminals(self):
        self.log("Sanitizing Terminal history databases...", "info")
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
        self.log(f"Scrubbed {cleared} command history stores.", "success")

    def wipe_app_states(self):
        self.log("Purging saved OS application configurations and recent documents...", "info")
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
        self.log(f"App states and recents cleaned across {wiped} subsystems.", "success")

    def sinkhole_telemetry(self):
        self.log("Applying Apple Analytics server blocks to hosts configuration...", "info")
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
            self.log("Read permission denied for /etc/hosts.", "error")
            return
            
        to_add = [d for d in block_domains if d not in content]
        if not to_add:
            self.log("Telemetry sinkholes already established in hosts.", "success")
            return
            
        hosts_append = "\\n# GHOST PROTOCOL SINKHOLE\\n"
        for d in to_add:
            hosts_append += f"0.0.0.0 {d}\\n"
            
        self.log("Requesting system authorization to write /etc/hosts...", "warning")
        append_cmd = f'printf "{hosts_append}" >> /etc/hosts'
        
        ret, stdout, stderr = self.run_as_admin(append_cmd)
        if ret == 0:
            self.log(f"Blocked {len(to_add)} diagnostics servers in /etc/hosts successfully.", "success")
        elif "User canceled" in stderr:
            self.log("Hosts configuration aborted: Authentication canceled by user.", "warning")
        else:
            self.log(f"Hosts update failed: {stderr.strip()}", "error")

    def toggle_spotlight(self, enable=False):
        status = "on" if enable else "off"
        self.log(f"Disabling Spotlight metadata compilation...", "info")
        
        spotlight_cmd = f"mdutil -i {status} /"
        self.log(f"Requesting system authorization to toggle Spotlight {status.upper()}...", "warning")
        
        ret, stdout, stderr = self.run_as_admin(spotlight_cmd)
        if ret == 0:
            self.log(f"Spotlight Indexing set to: {status.upper()}", "success")
        elif "User canceled" in stderr:
            self.log("Spotlight toggle aborted: Authentication canceled by user.", "warning")
        else:
            self.log(f"Spotlight configuration failed: {stderr.strip()}", "error")

    def kill_crashreporter(self):
        self.log("Killing tracking log diagnostics services...", "info")
        try:
            subprocess.run(["killall", "-9", "CrashReporter"], capture_output=True)
            self.log("CrashReporter process instances halted.", "success")
        except Exception:
            pass

    def purge_caches_logs(self, target_type):
        self.log(f"Wiping {target_type} log and cache segments...", "info")
        home = os.path.expanduser("~")
        targets = []
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
        self.log(f"Successfully purged {purged} log files under {target_type}.", "success")

    def purge_temp_files(self):
        self.log("Cleaning temporary folders...", "info")
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
        self.log(f"Cleaned {purged} items from temp assets directories.", "success")

    def verify_active_browsers(self):
        """Verifies if browsers are running. Returns list of running browser names."""
        running = []
        browsers_pcmd = {
            "Safari": "Safari",
            "Google Chrome": "Google Chrome",
            "Firefox": "firefox"
        }
        for name, proc in browsers_pcmd.items():
            try:
                res = subprocess.run(["pgrep", "-x", proc], capture_output=True)
                if res.returncode != 0:
                    res = subprocess.run(["pgrep", "-f", proc], capture_output=True)
                if res.returncode == 0:
                    running.append(name)
            except Exception:
                pass
        return running

    def nuke_browsers(self):
        self.log("Scanning system for active browser operations...", "info")
        running_list = self.verify_active_browsers()
        if running_list:
            self.log(f"Active browser processes detected: {', '.join(running_list)}", "error")
            self.log("[REQUIRED ACTION] Please close running browsers before sanitizing database files.", "warning")
            return

        self.log("Sanitizing browser traces and tracking cookie files...", "info")
        home = os.path.expanduser("~")
        paths = {
            "Safari History": os.path.join(home, "Library/Safari/History.db"),
            "Safari LocalStorage": os.path.join(home, "Library/Safari/LocalStorage"),
            "Safari Binary Cookies Folder": os.path.join(home, "Library/Cookies"),
            "Safari Sandboxed Cookies": os.path.join(home, "Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies"),
            "Safari Sandboxed LocalStorage": os.path.join(home, "Library/Containers/com.apple.Safari/Data/Library/WebKit/WebsiteData/LocalStorage"),
            "Safari Sandboxed Cache Folder": os.path.join(home, "Library/Containers/com.apple.Safari/Data/Library/Caches")
        }
        
        # Chrome profiles scanning
        chrome_dir = os.path.join(home, "Library/Application Support/Google/Chrome")
        if os.path.exists(chrome_dir):
            try:
                for item in os.listdir(chrome_dir):
                    item_path = os.path.join(chrome_dir, item)
                    if os.path.isdir(item_path) and (item == "Default" or item.startswith("Profile ")):
                        paths[f"Chrome History ({item})"] = os.path.join(item_path, "History")
                        paths[f"Chrome Cookies ({item})"] = os.path.join(item_path, "Cookies")
                        paths[f"Chrome Login Data ({item})"] = os.path.join(item_path, "Login Data")
            except Exception:
                pass
        
        # Firefox profiles scanning
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
                
        cleaned = 0
        for label, db in paths.items():
            if os.path.exists(db):
                try:
                    if os.path.isdir(db):
                        shutil.rmtree(db, ignore_errors=True)
                    else:
                        os.remove(db)
                    self.log(f"Cleaned Browser DB: {label}", "success")
                    cleaned += 1
                except Exception as e:
                    self.log(f"Failed to scrub {label}: {e}", "warning")
        self.log(f"Browser history purge finished. Wiped {cleaned} DB elements.", "success")

    def erase_clipboard(self):
        self.log("Sanitizing clipboard memory...", "info")
        try:
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(input=b'')
            self.root.clipboard_clear()
            self.log("Volatile clipboard memory cleared.", "success")
        except Exception as e:
            self.log(f"Error wiping clipboard buffer: {e}", "error")

    # ==================== RUNNER THREAD ====================
    def start_protocol_execution(self):
        self.btn_execute.set_disabled(True)
        self.btn_execute.config(text=" EXECUTING ACTIONS... ")
        self.progress_bar.config(value=0)
        threading.Thread(target=self._run_protocol_thread, daemon=True).start()

    def _run_protocol_thread(self):
        self.log("STARTING HARDENING PROTOCOLS...", "system")
        active = []
        for key, toggle in self.toggles.items():
            if toggle.is_on:
                active.append(key)
        has_shred = len(self.shred_list) > 0
        total = len(active) + (1 if has_shred else 0)
        
        if total == 0:
            self.log("No modules toggled.", "warning")
            self.progress_bar.config(value=100)
            self.root.after(0, lambda: self.btn_execute.set_disabled(False))
            self.root.after(0, lambda: self.btn_execute.config(text=" EXECUTE PRIVACY PROTOCOL "))
            return
            
        done = 0
        for task in active:
            self.log(f"Running Module: {task.upper()}", "system")
            if task == "tor":
                self.configure_tor_proxies(True)
            elif task == "dns":
                self.flush_dns()
            elif task == "term":
                self.scrub_terminals()
            elif task == "clip":
                self.erase_clipboard()
            elif task == "state":
                self.wipe_app_states()
            elif task == "hosts":
                self.sinkhole_telemetry()
            elif task == "spotlight":
                self.toggle_spotlight(False)
            elif task == "telem":
                self.kill_crashreporter()
            elif task == "caches":
                self.purge_caches_logs("caches")
            elif task == "logs":
                self.purge_caches_logs("logs")
            elif task == "temp":
                self.purge_temp_files()
            elif task == "browsers":
                self.nuke_browsers()
            done += 1
            self.progress_bar.config(value=int((done / total) * 100))
            time.sleep(0.4)
            
        if has_shred:
            pass_str = self.passes_var.get()
            passes = 3
            if "1" in pass_str: passes = 1
            elif "7" in pass_str: passes = 7
            elif "35" in pass_str: passes = 35
            self.execute_shredder(passes=passes)
            self.progress_bar.config(value=100)
            
        self.log("ALL ROUTINES COMPLETED SUCCESSFULLY.", "success")
        self.root.after(0, lambda: self.btn_execute.set_disabled(False))
        self.root.after(0, lambda: self.btn_execute.config(text=" EXECUTE PRIVACY PROTOCOL "))

    # ==================== HANDSHAKES AND CLEANUP ON SHUTDOWN ====================
    def force_safe_shutdown(self):
        try:
            res = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True)
            services = [s.strip() for s in res.stdout.split("\n")[1:] if s.strip() and "*" not in s]
        except Exception:
            services = ["Wi-Fi", "Ethernet"]

        for svc in services:
            try:
                subprocess.run(["networksetup", "-setsocksfirewallproxystate", svc, "off"], capture_output=True)
            except Exception:
                pass
        try:
            subprocess.run(["dscacheutil", "-flushcache"], capture_output=True)
        except Exception:
            pass

    def on_window_close(self):
        self.log("Exiting, restoring network card defaults...", "info")
        if self.tor_process:
            self.stop_tor()
        self.force_safe_shutdown()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GhostProtocolUnified(root)
    root.mainloop()
