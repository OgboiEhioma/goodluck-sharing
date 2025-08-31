#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goodluck Sharing - Enhanced Edition with Duplicate Detection
Features:
 - SHA-256 integrity checks
 - Transfer speed & ETA
 - Transfer history (persisted)
 - Desktop notifications (win10toast / plyer fallback)
 - Local ironman.ico or ironman.png icon support
 - Simultaneous file transfers (queue-based)
 - Dark theme toggle
 - File overwrite handling
 - Interactive history with file access
 - Modern UI with hover effects and Iron Man-themed elements
 - Duplicate detection and prevention
"""

import os
import socket
import json
import struct
import hashlib
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from collections import deque, defaultdict
import tkinter.font as tkfont

# Optional notification libs
NOTIFY_BACKEND = None
try:
    from win10toast import ToastNotifier
    NOTIFY_BACKEND = "win10toast"
except Exception:
    try:
        from plyer import notification
        NOTIFY_BACKEND = "plyer"
    except Exception:
        NOTIFY_BACKEND = None

APP_NAME = "Goodluck Sharing"
APP_VERSION = "v2.1"
HISTORY_FILE = Path.home() / ".goodluck_sharing_history.json"
CONFIG_FILE = Path.home() / ".goodluck_sharing_config.json"
DUPLICATES_FILE = Path.home() / ".goodluck_sharing_duplicates.json"
MAX_CONCURRENT_TRANSFERS = 2

def human_size(n):
    """Convert bytes to human readable format"""
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    i = 0
    while f >= 1024.0 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    return f"{f:.1f} {units[i]}"

def fmt_eta(seconds):
    """Format ETA in human readable format"""
    if seconds is None:
        return "ETA: —"
    sec = int(max(0, seconds))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"ETA: {h}h {m}m"
    if m:
        return f"ETA: {m}m {s}s"
    return f"ETA: {s}s"

class DuplicateManager:
    """Manages duplicate detection and prevention"""
    
    def __init__(self):
        self.file_hashes = self._load_duplicates()
    
    def _load_duplicates(self):
        """Load previously transferred file hashes"""
        try:
            if DUPLICATES_FILE.exists():
                with open(DUPLICATES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return defaultdict(list, data)
        except Exception:
            pass
        return defaultdict(list)
    
    def _save_duplicates(self):
        """Save file hashes to disk"""
        try:
            with open(DUPLICATES_FILE, "w", encoding="utf-8") as f:
                json.dump(dict(self.file_hashes), f, indent=2)
        except Exception:
            pass
    
    def add_file_hash(self, file_path, file_hash, peer_ip):
        """Add a file hash to the duplicate detection database"""
        key = f"{file_hash}_{os.path.basename(file_path)}"
        entry = {
            "path": file_path,
            "hash": file_hash,
            "peer": peer_ip,
            "timestamp": datetime.now().isoformat()
        }
        
        # Keep only recent entries (last 1000 per hash+name combo)
        self.file_hashes[key].append(entry)
        if len(self.file_hashes[key]) > 1000:
            self.file_hashes[key] = self.file_hashes[key][-1000:]
        
        self._save_duplicates()
    
    def is_duplicate(self, file_path, file_hash, peer_ip):
        """Check if file is a duplicate based on hash and peer"""
        key = f"{file_hash}_{os.path.basename(file_path)}"
        
        # Check for exact matches (same hash, name, and peer)
        for entry in self.file_hashes.get(key, []):
            if (entry["hash"] == file_hash and 
                entry["peer"] == peer_ip):
                return True, entry
        
        return False, None
    
    def get_duplicate_info(self, file_path, file_hash):
        """Get information about potential duplicates"""
        key = f"{file_hash}_{os.path.basename(file_path)}"
        return self.file_hashes.get(key, [])
    
    def clear_duplicates(self):
        """Clear all duplicate detection data"""
        self.file_hashes.clear()
        self._save_duplicates()

class Notifier:
    """Handle desktop notifications across platforms"""
    
    def __init__(self):
        self.backend = NOTIFY_BACKEND
        if self.backend == "win10toast":
            try:
                self.toaster = ToastNotifier()
            except Exception:
                self.backend = None

    def notify(self, title, msg, duration=5):
        """Send desktop notification"""
        try:
            if self.backend == "win10toast":
                self.toaster.show_toast(title, msg, duration=duration, threaded=True)
            elif self.backend == "plyer":
                notification.notify(title=title, message=msg, timeout=duration)
            else:
                def _show_messagebox():
                    try:
                        messagebox.showinfo(title, msg)
                    except Exception:
                        pass
                
                try:
                    root = tk._default_root
                    if root:
                        root.after(100, _show_messagebox)
                    else:
                        _show_messagebox()
                except Exception:
                    pass
        except Exception:
            pass

class GoodluckSharingApp:
    """Main application class"""
    
    def __init__(self):
        self._init_variables()
        self._init_ui()
        self._start_discovery_listener()

    def _init_variables(self):
        """Initialize core application variables"""
        # Network configuration
        self.discovery_port = 5000
        self.transfer_port = 5001
        self.device_name = f"PC-{os.getenv('USERNAME') or os.getenv('USER') or 'Unknown'}"
        
        # Device discovery
        self.discovered_devices = {}
        self.is_listening = False
        self.is_discovering = False
        
        # File selection and transfers
        self.selected_paths = []
        self.current_transfers = []
        self.transfer_queue = []
        self.queue_lock = threading.Lock()
        self.transfer_paused = False
        self.transfer_cancelled = False
        
        # Directories and data
        self.download_dir = Path.home() / "Desktop" / "Goodluck Received"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()
        
        # Components
        self.notifier = Notifier()
        self.duplicate_manager = DuplicateManager()
        
        # UI theming
        self.themes = {
            "light": {"bg": "#f7f7f8", "card": "#ffffff", "accent": "#c21807", 
                     "muted": "#666666", "hover": "#b71c1c"},
            "dark": {"bg": "#121212", "card": "#1e1e1e", "accent": "#ff5252", 
                    "muted": "#bbbbbb", "hover": "#ff8a80"}
        }
        self.current_theme = self.themes[self._load_theme()]

    def _init_ui(self):
        """Initialize the user interface"""
        # Create root window
        self.root = tk.Tk()
        self.root.title(f"✨ {APP_NAME} - {APP_VERSION} ✨")
        self.root.geometry("980x760")
        self.root.minsize(880, 640)
        self.root.configure(bg=self.current_theme["bg"])
        self._set_icon()
        
        # Load arc reactor image for buttons
        self.arc_reactor_img = self._load_arc_reactor_image()
        
        # Setup UI components
        self._setup_styles_and_fonts()
        self._create_main_layout()
        self._create_tabs()
        self._setup_tab_content()
        
        # Initialize UI state
        self._refresh_history_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_arc_reactor_image(self):
        """Load arc reactor image for UI elements"""
        try:
            return tk.PhotoImage(file=Path(__file__).parent / "arc_reactor.png")
        except Exception:
            return None

    def _set_icon(self):
        """Set application icon"""
        try:
            here = Path(__file__).parent
            ico_path = here / "ironman.ico"
            png_path = here / "ironman.png"
            
            if ico_path.exists():
                self.root.iconbitmap(str(ico_path))
            elif png_path.exists():
                img = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(False, img)
        except Exception:
            pass

    def _load_theme(self):
        """Load theme preference from config"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("theme", "light")
        except Exception:
            pass
        return "light"

    def _save_theme(self):
        """Save current theme to config"""
        try:
            theme_name = "dark" if self.current_theme == self.themes["dark"] else "light"
            config = {"theme": theme_name}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f)
        except Exception:
            pass

    def _setup_styles_and_fonts(self):
        """Configure UI styles and fonts"""
        # Fonts
        self.font_bold = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.font_normal = tkfont.Font(family="Segoe UI", size=10)
        self.font_title = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.font_subtitle = tkfont.Font(family="Segoe UI", size=10)
        
        # Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

    def _configure_styles(self):
        """Configure TTK styles based on current theme"""
        theme = self.current_theme
        
        self.style.configure("Accent.TButton", 
                           background=theme["accent"], 
                           foreground="white", 
                           font=("Segoe UI", 10, "bold"), 
                           padding=8, 
                           borderwidth=0)
        
        self.style.map("Accent.TButton", 
                      background=[("active", theme["hover"]), ("pressed", theme["hover"])])
        
        self.style.configure("Success.TButton", 
                           background="#2e7d32", 
                           foreground="white", 
                           font=("Segoe UI", 10, "bold"), 
                           padding=8, 
                           borderwidth=0)
        
        self.style.configure("Danger.TButton", 
                           background="#d32f2f", 
                           foreground="white", 
                           font=("Segoe UI", 10, "bold"), 
                           padding=8, 
                           borderwidth=0)
        
        self.style.configure("Modern.Horizontal.TProgressbar", 
                           background=theme["accent"], 
                           troughcolor=theme["card"], 
                           borderwidth=0)
        
        self.style.configure("TNotebook", 
                           background=theme["bg"], 
                           borderwidth=0)
        
        self.style.configure("TNotebook.Tab", 
                           background=theme["card"], 
                           foreground=theme["muted"], 
                           padding=(10, 5), 
                           font=("Segoe UI", 10))
        
        self.style.map("TNotebook.Tab", 
                      background=[("selected", theme["accent"])], 
                      foreground=[("selected", "white")])

    def _create_main_layout(self):
        """Create main application layout"""
        main_frame = tk.Frame(self.root, bg=self.current_theme["bg"], padx=16, pady=16)
        main_frame.pack(fill="both", expand=True)
        
        # Title section
        title_frame = tk.Frame(main_frame, bg=self.current_theme["bg"])
        title_frame.pack(fill="x")
        
        title_label = tk.Label(title_frame, 
                              text=f"{APP_NAME} {APP_VERSION}", 
                              font=self.font_title, 
                              bg=self.current_theme["bg"], 
                              fg=self.current_theme["accent"])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, 
                                 text="Iron Man-inspired file sharing with SHA-256 integrity & duplicate detection", 
                                 font=self.font_subtitle, 
                                 bg=self.current_theme["bg"], 
                                 fg=self.current_theme["muted"])
        subtitle_label.pack(pady=(2, 12))
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=8)

    def _create_tabs(self):
        """Create tab frames"""
        self.send_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=12, pady=12)
        self.recv_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=12, pady=12)
        self.hist_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=12, pady=12)
        self.settings_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=12, pady=12)
        
        self.notebook.add(self.send_tab, text="Send")
        self.notebook.add(self.recv_tab, text="Receive")
        self.notebook.add(self.hist_tab, text="History")
        self.notebook.add(self.settings_tab, text="Settings")

    def _setup_tab_content(self):
        """Setup content for all tabs"""
        self._setup_send_tab()
        self._setup_receive_tab()
        self._setup_history_tab()
        self._setup_settings_tab()

    def _setup_send_tab(self):
        """Setup send tab content"""
        # Device discovery section
        discovery_frame = self._create_section_frame(self.send_tab, "Discover Devices")
        
        control_frame = tk.Frame(discovery_frame, bg=self.current_theme["card"])
        control_frame.pack(fill="x", pady=6)
        
        self.discovery_status = tk.Label(control_frame, 
                                        text="Ready to scan", 
                                        bg=self.current_theme["card"], 
                                        fg=self.current_theme["muted"], 
                                        font=self.font_normal)
        self.discovery_status.pack(side="left", padx=(0, 10))
        
        scan_btn = ttk.Button(control_frame, 
                             text="Scan", 
                             style="Accent.TButton", 
                             command=self.start_discovery, 
                             image=self.arc_reactor_img, 
                             compound="left")
        scan_btn.pack(side="right")
        self._add_button_effects(scan_btn)
        
        # File selection section
        tk.Label(self.send_tab, 
                text="Selected files & folders:", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(anchor="w", pady=(8, 0))
        
        self.sel_text = scrolledtext.ScrolledText(self.send_tab, 
                                                 height=8, 
                                                 bg="#f2f2f2", 
                                                 font=("Segoe UI", 9), 
                                                 wrap="word")
        self.sel_text.pack(fill="both", expand=False, pady=(4, 8))
        self.sel_text.config(state="disabled")
        
        # File selection buttons
        button_frame = tk.Frame(self.send_tab, bg=self.current_theme["card"])
        button_frame.pack(fill="x")
        
        self._create_button(button_frame, "Add Files", self.select_files, "#2e7d32").pack(side="left", padx=4)
        self._create_button(button_frame, "Add Folder", self.select_folder, "#2e7d32").pack(side="left", padx=4)
        self._create_button(button_frame, "Clear", self.clear_selection, "#d32f2f").pack(side="left", padx=4)
        self._create_button(button_frame, "Check Duplicates", self.check_duplicates, "#ff9800").pack(side="left", padx=4)
        
        # Target selection section
        tk.Label(self.send_tab, 
                text="Target (choose or enter IP):", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(anchor="w", pady=(10, 0))
        
        target_frame = tk.Frame(self.send_tab, bg=self.current_theme["card"])
        target_frame.pack(fill="x", pady=(4, 8))
        
        self.devices_listbox = tk.Listbox(target_frame, 
                                         height=4, 
                                         font=self.font_normal, 
                                         selectbackground=self.current_theme["accent"], 
                                         selectforeground="white")
        self.devices_listbox.pack(side="left", fill="x", expand=True)
        
        self.manual_ip = ttk.Entry(target_frame, font=self.font_normal)
        self.manual_ip.pack(side="right", fill="x", padx=(8, 0), expand=False)
        
        # Transfer control section
        transfer_control_frame = tk.Frame(self.send_tab, bg=self.current_theme["card"])
        transfer_control_frame.pack(fill="x", pady=8)
        
        start_btn = ttk.Button(transfer_control_frame, 
                              text="Start Transfer", 
                              style="Success.TButton", 
                              command=self.start_transfer, 
                              image=self.arc_reactor_img, 
                              compound="left")
        start_btn.pack(side="left", padx=6)
        self._add_button_effects(start_btn)
        
        self._create_button(transfer_control_frame, "Pause", self.pause_transfer).pack(side="left", padx=4)
        self._create_button(transfer_control_frame, "Resume", self.resume_transfer).pack(side="left", padx=4)
        self._create_button(transfer_control_frame, "Cancel", self.cancel_transfer, "#d32f2f").pack(side="left", padx=4)
        
        # Transfer status section
        self.queue_status = tk.Label(self.send_tab, 
                                    text="No transfers queued", 
                                    bg=self.current_theme["card"], 
                                    fg=self.current_theme["muted"], 
                                    font=self.font_normal)
        self.queue_status.pack(anchor="w", pady=(4, 4))
        
        self.send_progress = ttk.Progressbar(self.send_tab, style="Modern.Horizontal.TProgressbar")
        self.send_progress.pack(fill="x", pady=6)
        
        self.send_status = tk.Label(self.send_tab, 
                                   text="Ready to send", 
                                   bg=self.current_theme["card"], 
                                   fg=self.current_theme["muted"], 
                                   font=self.font_normal)
        self.send_status.pack(anchor="w")
        
        self.send_metrics = tk.Label(self.send_tab, 
                                    text="Speed: — • ETA: —", 
                                    bg=self.current_theme["card"], 
                                    fg=self.current_theme["muted"], 
                                    font=self.font_normal)
        self.send_metrics.pack(anchor="w", pady=(0, 6))

    def _setup_receive_tab(self):
        """Setup receive tab content"""
        # Receiver section
        receiver_frame = self._create_section_frame(self.recv_tab, "Receiver")
        
        receiver_control_frame = tk.Frame(receiver_frame, bg=self.current_theme["card"])
        receiver_control_frame.pack(fill="x", pady=6)
        
        self.listen_status = tk.Label(receiver_control_frame, 
                                     text="Not listening", 
                                     bg=self.current_theme["card"], 
                                     fg=self.current_theme["muted"], 
                                     font=self.font_normal)
        self.listen_status.pack(side="left", padx=(0, 10))
        
        listen_btn = ttk.Button(receiver_control_frame, 
                               text="Start Listening", 
                               style="Success.TButton", 
                               command=self.start_listening, 
                               image=self.arc_reactor_img, 
                               compound="left")
        listen_btn.pack(side="right")
        self._add_button_effects(listen_btn)
        
        # Download folder section
        tk.Label(self.recv_tab, 
                text="Download folder:", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(anchor="w", pady=(8, 0))
        
        download_frame = tk.Frame(self.recv_tab, bg=self.current_theme["card"])
        download_frame.pack(fill="x", pady=(2, 8))
        
        self.download_path_var = tk.StringVar(value=str(self.download_dir))
        ttk.Entry(download_frame, 
                 textvariable=self.download_path_var, 
                 state="readonly", 
                 font=self.font_normal).pack(side="left", fill="x", expand=True)
        
        ttk.Button(download_frame, 
                  text="Change", 
                  style="Accent.TButton", 
                  command=self.change_download_location).pack(side="right")
        
        # Receive log section
        self.recv_log = scrolledtext.ScrolledText(self.recv_tab, 
                                                 height=12, 
                                                 bg="#f2f2f2", 
                                                 font=("Segoe UI", 9), 
                                                 wrap="word")
        self.recv_log.pack(fill="both", expand=True, pady=(4, 6))
        self.recv_log.config(state="disabled")
        
        self.recv_progress = ttk.Progressbar(self.recv_tab, style="Modern.Horizontal.TProgressbar")
        self.recv_progress.pack(fill="x", pady=(4, 6))
        
        self.recv_metrics = tk.Label(self.recv_tab, 
                                    text="Speed: — • ETA: —", 
                                    bg=self.current_theme["card"], 
                                    fg=self.current_theme["muted"], 
                                    font=self.font_normal)
        self.recv_metrics.pack(anchor="w")

    def _setup_history_tab(self):
        """Setup history tab content"""
        self._create_section_frame(self.hist_tab, "Transfer History")
        
        self.hist_list = scrolledtext.ScrolledText(self.hist_tab, 
                                                  height=20, 
                                                  bg="#f2f2f2", 
                                                  font=("Segoe UI", 9), 
                                                  wrap="word")
        self.hist_list.pack(fill="both", expand=True, pady=6)
        self.hist_list.config(state="disabled")
        
        # Context menu for history
        self.hist_menu = tk.Menu(self.hist_list, tearoff=0)
        self.hist_menu.add_command(label="Open Folder", command=self._open_history_folder)
        self.hist_menu.add_command(label="Copy Details", command=self._copy_history_details)
        self.hist_list.bind("<Button-3>", self._show_history_menu)
        
        # History control buttons
        history_button_frame = tk.Frame(self.hist_tab, bg=self.current_theme["card"])
        history_button_frame.pack(fill="x", pady=(4, 4))
        
        ttk.Button(history_button_frame, 
                  text="Refresh History", 
                  style="Accent.TButton", 
                  command=self._refresh_history_ui).pack(side="left", padx=4)
        
        ttk.Button(history_button_frame, 
                  text="Clear History", 
                  style="Danger.TButton", 
                  command=self._clear_history_prompt).pack(side="left", padx=4)

    def _setup_settings_tab(self):
        """Setup settings tab content"""
        # Device name setting
        tk.Label(self.settings_tab, 
                text="Device Name:", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(anchor="w")
        
        self.device_name_var = tk.StringVar(value=self.device_name)
        ttk.Entry(self.settings_tab, 
                 textvariable=self.device_name_var, 
                 font=self.font_normal).pack(fill="x", pady=(2, 8))
        
        ttk.Button(self.settings_tab, 
                  text="Save Device Name", 
                  style="Success.TButton", 
                  command=self.save_device_name).pack(pady=4)
        
        # Theme toggle
        ttk.Button(self.settings_tab, 
                  text="Toggle Theme", 
                  style="Accent.TButton", 
                  command=self.toggle_theme).pack(pady=4)
        
        # Duplicate management
        duplicate_frame = self._create_section_frame(self.settings_tab, "Duplicate Detection")
        
        ttk.Button(duplicate_frame, 
                  text="View Duplicate Database", 
                  style="Accent.TButton", 
                  command=self.view_duplicates).pack(pady=4)
        
        ttk.Button(duplicate_frame, 
                  text="Clear Duplicate Database", 
                  style="Danger.TButton", 
                  command=self.clear_duplicate_database).pack(pady=4)

    def _create_section_frame(self, parent, title):
        """Create a section frame with title"""
        frame = tk.Frame(parent, bg=self.current_theme["card"], bd=1, relief="flat")
        frame.pack(fill="x", pady=(0, 8))
        
        tk.Label(frame, 
                text=title, 
                bg=self.current_theme["card"], 
                fg=self.current_theme["accent"], 
                font=self.font_bold).pack(anchor="w")
        
        return frame

    def _create_button(self, parent, text, command, bg_color=None):
        """Create a styled button"""
        if bg_color is None:
            bg_color = self.current_theme["accent"]
        
        return tk.Button(parent, 
                        text=text, 
                        command=command, 
                        width=12, 
                        bg=bg_color, 
                        fg="white", 
                        font=self.font_normal)

    def _add_button_effects(self, button):
        """Add hover effects to buttons"""
        button.bind("<Enter>", lambda e: button.configure(cursor="hand2"))
        button.bind("<Leave>", lambda e: button.configure(cursor=""))

    def _start_discovery_listener(self):
        """Start UDP discovery listener thread"""
        threading.Thread(target=self.udp_discovery_listener, daemon=True).start()

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        self.current_theme = self.themes["dark" if self.current_theme == self.themes["light"] else "light"]
        self._save_theme()
        self._update_theme()

    def _update_theme(self):
        """Update UI elements to match current theme"""
        theme = self.current_theme
        self.root.configure(bg=theme["bg"])
        
        # Update tab backgrounds
        for frame in [self.send_tab, self.recv_tab, self.hist_tab, self.settings_tab]:
            frame.configure(bg=theme["card"])
            self._update_frame_theme(frame, theme)
        
        # Update status labels
        status_labels = [
            self.discovery_status, self.send_status, self.send_metrics,
            self.listen_status, self.recv_metrics, self.queue_status
        ]
        for label in status_labels:
            label.configure(bg=theme["card"], fg=theme["muted"])
        
        self._configure_styles()
        self._refresh_history_ui()

    def _update_frame_theme(self, frame, theme):
        """Recursively update frame theme"""
        for widget in frame.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=theme["card"])
                self._update_frame_theme(widget, theme)
            elif isinstance(widget, tk.Label):
                current_fg = widget["foreground"]
                if "title" in widget["text"].lower() or current_fg == self.themes["light"]["accent"] or current_fg == self.themes["dark"]["accent"]:
                    widget.configure(bg=theme["card"], fg=theme["accent"])
                else:
                    widget.configure(bg=theme["card"], fg=theme["muted"])
            elif isinstance(widget, tk.Button) and not isinstance(widget, ttk.Button):
                if "Add" in widget["text"] or "Clear" not in widget["text"]:
                    widget.configure(bg=theme["accent"], fg="white")
                else:
                    widget.configure(bg="#d32f2f", fg="white")

    # Text display methods
    def _append_sel_text(self, text):
        """Append text to selection display"""
        self.sel_text.config(state="normal")
        self.sel_text.insert("end", text + "\n")
        self.sel_text.see("end")
        self.sel_text.config(state="disabled")

    def _append_recv_log(self, text):
        """Append text to receive log"""
        self.recv_log.config(state="normal")
        self.recv_log.insert("end", text + "\n")
        self.recv_log.see("end")
        self.recv_log.config(state="disabled")

    def _append_history(self, rec):
        """Append record to history display"""
        self.hist_list.config(state="normal")
        tag = f"entry_{len(self.history)-1}"
        line = f"{rec['time']} • {rec['direction']} • {rec['peer']} • {rec['files']} files • {human_size(rec['size'])} • {int(rec['duration'])}s • verified {rec['verified']} • {rec['status']}"
        self.hist_list.insert("end", line + "\n", tag)
        fg = "#d32f2f" if rec['status'] != "OK" else self.current_theme["muted"]
        self.hist_list.tag_configure(tag, foreground=fg)
        self.hist_list.tag_bind(tag, "<Button-1>", lambda e: self._open_history_folder(rec))
        self.hist_list.see("end")
        self.hist_list.config(state="disabled")

    # File selection methods
    def select_files(self):
        """Select files to transfer"""
        files = filedialog.askopenfilenames(title="Select files")
        added_count = 0
        duplicate_count = 0
        
        for file_path in files:
            if file_path not in self.selected_paths:
                self.selected_paths.append(file_path)
                self._append_sel_text(file_path)
                added_count += 1
            else:
                duplicate_count += 1
        
        if duplicate_count > 0:
            messagebox.showinfo("Duplicates Skipped", 
                              f"Skipped {duplicate_count} files already in selection")
        
        if added_count > 0:
            messagebox.showinfo("Files Added", f"Added {added_count} files to selection")

    def select_folder(self):
        """Select folder to transfer"""
        folder = filedialog.askdirectory(title="Select folder")
        if not folder:
            return
        
        added_count = 0
        duplicate_count = 0
        
        for root, _, files in os.walk(folder):
            for filename in files:
                file_path = os.path.join(root, filename)
                if file_path not in self.selected_paths:
                    self.selected_paths.append(file_path)
                    self._append_sel_text(file_path)
                    added_count += 1
                else:
                    duplicate_count += 1
        
        if duplicate_count > 0:
            messagebox.showinfo("Duplicates Skipped", 
                              f"Skipped {duplicate_count} files already in selection")
        
        if added_count > 0:
            messagebox.showinfo("Files Added", f"Added {added_count} files from folder")

    def clear_selection(self):
        """Clear all selected files"""
        self.selected_paths.clear()
        self.sel_text.config(state="normal")
        self.sel_text.delete("1.0", "end")
        self.sel_text.config(state="disabled")

    def check_duplicates(self):
        """Check selected files for duplicates in database"""
        if not self.selected_paths:
            messagebox.showwarning("No Selection", "No files selected to check")
            return
        
        duplicates_found = []
        for file_path in self.selected_paths:
            try:
                if Path(file_path).is_file():
                    file_hash = self._sha256_of_file(Path(file_path))
                    duplicate_info = self.duplicate_manager.get_duplicate_info(file_path, file_hash)
                    if duplicate_info:
                        duplicates_found.append({
                            'path': file_path,
                            'hash': file_hash,
                            'history': duplicate_info
                        })
            except Exception:
                continue
        
        if duplicates_found:
            self._show_duplicate_dialog(duplicates_found)
        else:
            messagebox.showinfo("No Duplicates", "No duplicate files found in database")

    def _show_duplicate_dialog(self, duplicates):
        """Show dialog with duplicate information"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Duplicate Files Found")
        dialog.geometry("600x400")
        dialog.configure(bg=self.current_theme["card"])
        
        tk.Label(dialog, 
                text=f"Found {len(duplicates)} files with transfer history:", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["accent"], 
                font=self.font_bold).pack(pady=10)
        
        text_widget = scrolledtext.ScrolledText(dialog, 
                                               height=15, 
                                               bg="#f2f2f2", 
                                               font=("Segoe UI", 9), 
                                               wrap="word")
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        for dup in duplicates:
            text_widget.insert("end", f"File: {os.path.basename(dup['path'])}\n")
            text_widget.insert("end", f"Full Path: {dup['path']}\n")
            text_widget.insert("end", f"Hash: {dup['hash'][:16]}...\n")
            text_widget.insert("end", "Transfer History:\n")
            
            for entry in dup['history'][-5:]:  # Show last 5 transfers
                text_widget.insert("end", f"  • {entry['timestamp'][:19]} to/from {entry['peer']}\n")
            
            text_widget.insert("end", "-" * 50 + "\n\n")
        
        text_widget.config(state="disabled")
        
        ttk.Button(dialog, 
                  text="Close", 
                  command=dialog.destroy).pack(pady=10)

    # Discovery methods
    def udp_discovery_listener(self):
        """Listen for UDP discovery messages"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.discovery_port))
            sock.settimeout(2.0)
            
            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                except Exception:
                    break
                
                try:
                    msg = data.decode('utf-8', errors='ignore')
                    if msg.startswith("GOODLUCK_DISCOVERY:"):
                        info = json.loads(msg.split(":", 1)[1])
                        device_name = info.get('name', 'Unknown')
                        
                        if addr[0] != self.get_local_ip():
                            self.discovered_devices[addr[0]] = device_name
                            self._refresh_devices_ui()
                        
                        response = f"GOODLUCK_RESPONSE:{json.dumps({'name': self.device_name})}"
                        sock.sendto(response.encode('utf-8'), addr)
                    
                    elif msg.startswith("GOODLUCK_RESPONSE:"):
                        info = json.loads(msg.split(":", 1)[1])
                        device_name = info.get('name', 'Unknown')
                        
                        if addr[0] != self.get_local_ip():
                            self.discovered_devices[addr[0]] = device_name
                            self._refresh_devices_ui()
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print("Discovery listener error:", e)

    def start_discovery(self):
        """Start device discovery process"""
        if self.is_discovering:
            return
        
        self.is_discovering = True
        self.discovery_status.config(text="Scanning...", fg=self.current_theme["accent"])
        self.discovered_devices.clear()
        self._refresh_devices_ui()
        
        threading.Thread(target=self._broadcast_discovery, daemon=True).start()
        self.root.after(4000, self._stop_discovery)

    def _broadcast_discovery(self):
        """Broadcast discovery message"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            message = f"GOODLUCK_DISCOVERY:{json.dumps({'name': self.device_name})}"
            
            addresses = ['255.255.255.255']
            for _ in range(3):
                for addr in addresses:
                    try:
                        sock.sendto(message.encode('utf-8'), (addr, self.discovery_port))
                    except Exception:
                        pass
                time.sleep(0.5)
            
            sock.close()
        except Exception as e:
            print("Discovery broadcast error:", e)

    def _stop_discovery(self):
        """Stop discovery process and update status"""
        self.is_discovering = False
        device_count = len(self.discovered_devices)
        
        if device_count:
            self.discovery_status.config(text=f"Found {device_count} device(s)", fg="#2e7d32")
        else:
            self.discovery_status.config(text="No devices found", fg="#d32f2f")

    def _refresh_devices_ui(self):
        """Refresh devices listbox"""
        self.devices_listbox.delete(0, tk.END)
        for ip, name in sorted(self.discovered_devices.items()):
            self.devices_listbox.insert(tk.END, f"{name} ({ip})")

    # File hash calculation
    def _sha256_of_file(self, path: Path, chunk_size=1024*1024):
        """Calculate SHA-256 hash of file"""
        hash_obj = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                hash_obj.update(data)
        return hash_obj.hexdigest()

    def _gather_files_for_send(self):
        """Gather files and calculate metadata for sending"""
        files = []
        total_size = 0
        
        for file_path in self.selected_paths:
            path_obj = Path(file_path)
            if path_obj.is_file():
                size = path_obj.stat().st_size
                sha_hash = self._sha256_of_file(path_obj)
                
                files.append({
                    'path': str(path_obj),
                    'rel': path_obj.name,
                    'size': size,
                    'sha256': sha_hash
                })
                total_size += size
        
        return files, total_size

    # Transfer methods
    def start_transfer(self):
        """Start file transfer"""
        # Get target IP
        target_ip = self._get_target_ip()
        if not target_ip:
            messagebox.showwarning("No Target", "Select a discovered device or enter an IP")
            return
        
        # Gather files
        files, total_size = self._gather_files_for_send()
        if not files:
            messagebox.showwarning("No Files", "Select files to send first")
            return
        
        # Check for duplicates
        if self._check_send_duplicates(files, target_ip):
            return
        
        # Add to queue
        with self.queue_lock:
            self.transfer_queue.append((target_ip, files, total_size))
        
        self._update_queue_status()
        self._process_queue()

    def _get_target_ip(self):
        """Get target IP from selection or manual entry"""
        selection = self.devices_listbox.curselection()
        if selection:
            text = self.devices_listbox.get(selection[0])
            return text.split("(")[1].split(")")[0]
        elif self.manual_ip.get().strip():
            return self.manual_ip.get().strip()
        return None

    def _check_send_duplicates(self, files, target_ip):
        """Check for duplicates before sending and ask user"""
        duplicates = []
        for file_info in files:
            is_dup, dup_info = self.duplicate_manager.is_duplicate(
                file_info['path'], file_info['sha256'], target_ip
            )
            if is_dup:
                duplicates.append((file_info, dup_info))
        
        if duplicates:
            response = messagebox.askyesno(
                "Duplicates Found", 
                f"Found {len(duplicates)} files already sent to this device. Send anyway?"
            )
            return not response  # Return True to cancel transfer
        
        return False

    def _process_queue(self):
        """Process transfer queue"""
        with self.queue_lock:
            if len(self.current_transfers) >= MAX_CONCURRENT_TRANSFERS or not self.transfer_queue:
                return
            
            target_ip, files, total_size = self.transfer_queue.pop(0)
        
        transfer_thread = threading.Thread(
            target=self._perform_send, 
            args=(target_ip, files, total_size), 
            daemon=True
        )
        self.current_transfers.append(transfer_thread)
        transfer_thread.start()
        
        self.root.after(100, self._check_transfers)

    def _check_transfers(self):
        """Check transfer status and process queue"""
        with self.queue_lock:
            self.current_transfers = [t for t in self.current_transfers if t.is_alive()]
            self._update_queue_status()
        
        if self.transfer_queue and len(self.current_transfers) < MAX_CONCURRENT_TRANSFERS:
            self._process_queue()
        elif self.transfer_queue or self.current_transfers:
            self.root.after(100, self._check_transfers)

    def _update_queue_status(self):
        """Update queue status display"""
        total_count = len(self.transfer_queue) + len(self.current_transfers)
        status_text = f"{total_count} transfer(s) active/queued" if total_count else "No transfers queued"
        self.queue_status.config(text=status_text)

    def _perform_send(self, target_ip, files, total_size):
        """Perform file sending operation"""
        start_time = time.time()
        sock = None
        
        try:
            # Connect to target
            self._ui_set_send_status(f"Connecting to {target_ip}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(8)
            sock.connect((target_ip, self.transfer_port))
            
            # Send metadata
            self._ui_set_send_status("Connected — sending metadata...")
            metadata = {
                'file_count': len(files),
                'files': [{'rel': f['rel'], 'size': f['size'], 'sha256': f['sha256']} for f in files]
            }
            
            metadata_bytes = json.dumps(metadata).encode('utf-8')
            sock.send(struct.pack('!I', len(metadata_bytes)))
            sock.sendall(metadata_bytes)
            
            # Initialize progress tracking
            self.root.after(0, lambda: self.send_progress.configure(maximum=total_size, value=0))
            total_sent = 0
            recent_data = deque(maxlen=30)
            last_ui_update = time.time()
            
            # Send files
            for file_info in files:
                if self.transfer_cancelled:
                    break
                
                file_path = Path(file_info['path'])
                file_size = file_info['size']
                relative_name = file_info['rel']
                
                self._ui_set_send_status(f"Sending {relative_name} ({human_size(file_size)})")
                
                # Send file data
                with open(file_path, "rb") as file_handle:
                    while True:
                        if self.transfer_cancelled:
                            break
                        
                        # Handle pause
                        while self.transfer_paused:
                            time.sleep(0.1)
                        
                        chunk = file_handle.read(128 * 1024)
                        if not chunk:
                            break
                        
                        sock.sendall(chunk)
                        chunk_size = len(chunk)
                        total_sent += chunk_size
                        recent_data.append((time.time(), chunk_size))
                        
                        # Update UI periodically
                        current_time = time.time()
                        if current_time - last_ui_update >= 0.2:
                            speed = self._calculate_speed(recent_data)
                            eta = self._calculate_eta(speed, total_size - total_sent)
                            self._update_send_ui(total_sent, speed, eta)
                            last_ui_update = current_time
                
                # Update duplicate database
                self.duplicate_manager.add_file_hash(
                    file_info['path'], file_info['sha256'], target_ip
                )
            
            # Handle completion
            duration = time.time() - start_time
            if not self.transfer_cancelled:
                self._ui_set_send_status("Transfer completed")
                messagebox.showinfo("Success", f"Sent {len(files)} file(s) to {target_ip}")
                self.notifier.notify("Transfer Complete", f"Sent {len(files)} files to {target_ip}")
                self._add_history("Send", target_ip, len(files), total_size, duration, 
                                f"{len(files)}/{len(files)}", "OK")
            else:
                self._ui_set_send_status("Transfer cancelled", error=True)
                self._add_history("Send", target_ip, len(files), total_size, duration, 
                                "—", "Cancelled")
                
        except Exception as e:
            self._ui_set_send_status("Transfer failed", error=True)
            messagebox.showerror("Network Error", f"Send failed: {e}")
            self._add_history("Send", target_ip or "?", 0, 0, 0, "—", "Error")
            
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
            
            # Reset UI
            self.root.after(0, lambda: self.send_progress.configure(value=0))
            self.root.after(0, lambda: self.send_metrics.config(text="Speed: — • ETA: —"))

    def _calculate_speed(self, recent_data):
        """Calculate transfer speed from recent data"""
        if not recent_data:
            return 0.0
        
        current_time = time.time()
        window_size = 2.0
        total_bytes = 0
        earliest_time = current_time - window_size
        
        for timestamp, byte_count in recent_data:
            if timestamp >= earliest_time:
                total_bytes += byte_count
        
        return total_bytes / window_size

    def _calculate_eta(self, speed, bytes_remaining):
        """Calculate estimated time of arrival"""
        if speed <= 1e-6:
            return None
        return bytes_remaining / speed

    def _ui_set_send_status(self, text, error=False):
        """Update send status in UI"""
        color = "#d32f2f" if error else self.current_theme["muted"]
        self.root.after(0, lambda: self.send_status.config(text=text, fg=color))

    def _update_send_ui(self, progress_value, speed, eta):
        """Update send progress UI"""
        self.root.after(0, lambda: self.send_progress.configure(value=progress_value))
        
        speed_text = f"{human_size(speed)}/s" if speed else "—"
        eta_text = fmt_eta(eta)
        metrics_text = f"Speed: {speed_text} • {eta_text}"
        
        self.root.after(0, lambda: self.send_metrics.config(text=metrics_text))

    # Transfer control methods
    def pause_transfer(self):
        """Pause current transfer"""
        self.transfer_paused = True
        self._ui_set_send_status("Transfer paused")

    def resume_transfer(self):
        """Resume paused transfer"""
        self.transfer_paused = False
        self._ui_set_send_status("Resuming transfer...")

    def cancel_transfer(self):
        """Cancel current transfer"""
        self.transfer_cancelled = True
        self._ui_set_send_status("Cancelling transfer...", error=True)

    # Receive methods
    def start_listening(self):
        """Start listening for incoming transfers"""
        if self.is_listening:
            return
        
        self.is_listening = True
        self.listen_status.config(text=f"Listening on {self.transfer_port}...", fg="#2e7d32")
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        """Main listening thread for incoming connections"""
        server_socket = None
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('', self.transfer_port))
            server_socket.listen(5)
            server_socket.settimeout(1.0)
            
            while self.is_listening:
                try:
                    connection, address = server_socket.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break
                
                threading.Thread(
                    target=self._handle_incoming_transfer, 
                    args=(connection, address), 
                    daemon=True
                ).start()
                
        except Exception as e:
            messagebox.showerror("Listen Error", f"Failed to listen: {e}")
            self.listen_status.config(text="Not listening", fg=self.current_theme["muted"])
            self.is_listening = False
            
        finally:
            if server_socket:
                try:
                    server_socket.close()
                except:
                    pass

    def _receive_all(self, connection, num_bytes):
        """Receive exactly num_bytes from connection"""
        data = bytearray()
        while len(data) < num_bytes:
            packet = connection.recv(num_bytes - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)

    def _handle_incoming_transfer(self, connection, address):
        """Handle incoming file transfer"""
        start_time = time.time()
        peer_ip = address[0]
        total_received = 0
        verified_count = 0
        total_files = 0
        total_size = 0
        overwrite_all = None
        
        try:
            # Receive metadata
            header = self._receive_all(connection, 4)
            if not header:
                raise RuntimeError("No metadata received")
            
            metadata_length = struct.unpack('!I', header)[0]
            metadata_json = self._receive_all(connection, metadata_length)
            metadata = json.loads(metadata_json.decode('utf-8'))
            
            files = metadata.get('files', [])
            total_files = metadata.get('file_count', len(files))
            total_size = sum(f.get('size', 0) for f in files)
            
            # Initialize progress tracking
            self.root.after(0, lambda: self.recv_progress.configure(maximum=total_size, value=0))
            self._append_recv_log(f"Receiving {total_files} files from {peer_ip} ...")
            
            recent_data = deque(maxlen=30)
            last_ui_update = time.time()
            bytes_completed = 0
            
            # Process each file
            for file_info in files:
                relative_path = (file_info.get('rel') or 
                               file_info.get('relative_path') or 
                               file_info.get('name'))
                file_size = file_info.get('size', 0)
                expected_hash = file_info.get('sha256')
                
                save_path = Path(self.download_path_var.get()) / relative_path
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Handle existing files
                if save_path.exists() and overwrite_all is None:
                    response = messagebox.askyesnocancel(
                        "File Exists", 
                        f"{relative_path} exists. Overwrite?", 
                        default="no"
                    )
                    if response is None:  # Cancel
                        self.is_listening = False
                        break
                    elif response is False:  # No
                        self._append_recv_log(f"Skipped {relative_path} (exists)")
                        continue
                    
                    overwrite_all = response
                
                if save_path.exists() and not overwrite_all:
                    self._append_recv_log(f"Skipped {relative_path} (exists)")
                    continue
                
                # Check for duplicates
                if expected_hash:
                    is_duplicate, dup_info = self.duplicate_manager.is_duplicate(
                        str(save_path), expected_hash, peer_ip
                    )
                    if is_duplicate:
                        self._append_recv_log(f"⚠ Duplicate detected: {relative_path}")
                
                # Receive file
                self._append_recv_log(f"Receiving {relative_path} ({human_size(file_size)})")
                hash_obj = hashlib.sha256()
                received_for_file = 0
                
                with open(save_path, "wb") as output_file:
                    while received_for_file < file_size:
                        chunk = connection.recv(min(128*1024, file_size - received_for_file))
                        if not chunk:
                            break
                        
                        output_file.write(chunk)
                        hash_obj.update(chunk)
                        
                        chunk_length = len(chunk)
                        received_for_file += chunk_length
                        bytes_completed += chunk_length
                        recent_data.append((time.time(), chunk_length))
                        
                        # Update UI periodically
                        current_time = time.time()
                        if current_time - last_ui_update >= 0.2:
                            speed = self._calculate_speed(recent_data)
                            eta = self._calculate_eta(speed, total_size - bytes_completed)
                            
                            self.root.after(0, lambda v=bytes_completed: 
                                          self.recv_progress.configure(value=v))
                            self.root.after(0, lambda s=speed, e=eta: 
                                          self.recv_metrics.config(
                                              text=f"Speed: {human_size(s)}/s • {fmt_eta(e)}"
                                          ))
                            last_ui_update = current_time
                
                # Verify file integrity
                actual_hash = hash_obj.hexdigest()
                if expected_hash and actual_hash.lower() == expected_hash.lower():
                    verified_count += 1
                    self._append_recv_log(f"✓ Verified {relative_path}")
                    
                    # Add to duplicate database
                    self.duplicate_manager.add_file_hash(
                        str(save_path), actual_hash, peer_ip
                    )
                else:
                    self._append_recv_log(f"⚠ FAILED integrity for {relative_path}")
            
            # Handle completion
            duration = time.time() - start_time
            self.root.after(0, lambda: self.recv_progress.configure(value=0))
            
            if self.is_listening:
                self._append_recv_log("Transfer completed.")
                messagebox.showinfo("Received", f"Received {total_files} files from {peer_ip}")
                self.notifier.notify(
                    "Transfer Received", 
                    f"{total_files} files from {peer_ip} • Verified {verified_count}/{total_files}"
                )
                self._add_history("Receive", peer_ip, total_files, total_size, duration, 
                                f"{verified_count}/{total_files}", "OK")
            else:
                self._append_recv_log("Transfer cancelled.")
                self._add_history("Receive", peer_ip, total_files, total_size, duration, 
                                "—", "Cancelled")
                
        except Exception as e:
            self._append_recv_log(f"Error during receive: {e}")
            self._add_history("Receive", peer_ip if 'peer_ip' in locals() else "?", 
                            0, 0, 0, "—", "Error")
            
        finally:
            try:
                connection.close()
            except:
                pass

    # History methods
    def _load_history(self):
        """Load transfer history from file"""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_history(self):
        """Save transfer history to file"""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass

    def _add_history(self, direction, peer, files, size, duration, verified, status):
        """Add entry to transfer history"""
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "direction": direction,
            "peer": peer,
            "files": files,
            "size": size,
            "duration": duration,
            "verified": verified,
            "status": status
        }
        
        self.history.append(record)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        
        self._save_history()
        self._append_history(record)

    def _refresh_history_ui(self):
        """Refresh history display"""
        self.hist_list.config(state="normal")
        self.hist_list.delete("1.0", "end")
        
        for record in reversed(self.history[-500:]):  # Show last 500 entries
            self._append_history(record)
        
        self.hist_list.config(state="disabled")

    def _clear_history_prompt(self):
        """Prompt user to clear history"""
        if messagebox.askyesno("Clear History", "Clear transfer history?"):
            self.history = []
            self._save_history()
            self._refresh_history_ui()

    # History context menu methods
    def _show_history_menu(self, event):
        """Show context menu for history"""
        try:
            self.hist_list.tag_ranges(tk.SEL)
            has_history = bool(self.history)
            
            self.hist_menu.entryconfigure("Open Folder", 
                                        state="normal" if has_history else "disabled")
            self.hist_menu.entryconfigure("Copy Details", 
                                        state="normal" if has_history else "disabled")
            
            self.hist_menu.post(event.x_root, event.y_root)
        except Exception:
            pass

    def _open_history_folder(self, record=None):
        """Open folder from history record"""
        if record and record['direction'] == "Receive" and record['status'] == "OK":
            folder_path = Path(self.download_path_var.get())
            try:
                os.startfile(str(folder_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {e}")

    def _copy_history_details(self):
        """Copy history details to clipboard"""
        if self.history:
            record = self.history[-1]  # Most recent for simplicity
            details = (f"{record['time']} | {record['direction']} | {record['peer']} | "
                      f"{record['files']} files | {human_size(record['size'])} | "
                      f"{int(record['duration'])}s | {record['verified']} | {record['status']}")
            
            self.root.clipboard_clear()
            self.root.clipboard_append(details)
            self.notifier.notify("Copied", "History details copied to clipboard")

    # Settings methods
    def change_download_location(self):
        """Change download directory"""
        new_directory = filedialog.askdirectory(title="Select download folder")
        if new_directory:
            self.download_path_var.set(new_directory)

    def save_device_name(self):
        """Save device name"""
        name = self.device_name_var.get().strip()
        if name:
            self.device_name = name
            messagebox.showinfo("Saved", "Device name updated")

    def view_duplicates(self):
        """View duplicate database"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Duplicate Database")
        dialog.geometry("700x500")
        dialog.configure(bg=self.current_theme["card"])
        
        tk.Label(dialog, 
                text="Duplicate Detection Database", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["accent"], 
                font=self.font_bold).pack(pady=10)
        
        text_widget = scrolledtext.ScrolledText(dialog, 
                                               height=20, 
                                               bg="#f2f2f2", 
                                               font=("Segoe UI", 9), 
                                               wrap="word")
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        if not self.duplicate_manager.file_hashes:
            text_widget.insert("end", "No duplicate data found.\n")
        else:
            for key, entries in self.duplicate_manager.file_hashes.items():
                text_widget.insert("end", f"File Pattern: {key}\n")
                text_widget.insert("end", f"Transfer Count: {len(entries)}\n")
                
                for entry in entries[-3:]:  # Show last 3 entries
                    text_widget.insert("end", f"  • {entry['timestamp'][:19]} - {entry['peer']}\n")
                    text_widget.insert("end", f"    Path: {entry['path']}\n")
                
                text_widget.insert("end", "-" * 60 + "\n\n")
        
        text_widget.config(state="disabled")
        
        button_frame = tk.Frame(dialog, bg=self.current_theme["card"])
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Refresh", 
                  command=lambda: self._refresh_duplicate_view(text_widget)).pack(side="right", padx=5)

    def _refresh_duplicate_view(self, text_widget):
        """Refresh duplicate view"""
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")
        
        if not self.duplicate_manager.file_hashes:
            text_widget.insert("end", "No duplicate data found.\n")
        else:
            for key, entries in self.duplicate_manager.file_hashes.items():
                text_widget.insert("end", f"File Pattern: {key}\n")
                text_widget.insert("end", f"Transfer Count: {len(entries)}\n")
                
                for entry in entries[-3:]:
                    text_widget.insert("end", f"  • {entry['timestamp'][:19]} - {entry['peer']}\n")
                    text_widget.insert("end", f"    Path: {entry['path']}\n")
                
                text_widget.insert("end", "-" * 60 + "\n\n")
        
        text_widget.config(state="disabled")

    def clear_duplicate_database(self):
        """Clear duplicate detection database"""
        if messagebox.askyesno("Clear Database", 
                              "Clear duplicate detection database? This cannot be undone."):
            self.duplicate_manager.clear_duplicates()
            messagebox.showinfo("Cleared", "Duplicate database cleared")

    # Utility methods
    def get_local_ip(self):
        """Get local IP address"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _on_close(self):
        """Handle application close"""
        self.is_listening = False
        self.transfer_cancelled = True
        self.root.destroy()

    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = GoodluckSharingApp()
    app.run()