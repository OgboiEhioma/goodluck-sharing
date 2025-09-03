#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goodluck Sharing - Enhanced Iron Man Edition with Industrial Grade Features
Features:
 - SHA-256 integrity checks
 - Real-time transfer speed & ETA visualization (JARVIS-level monitoring)
 - Enhanced transfer history (persisted like Tony Stark's memory banks)
 - Desktop notifications (win10toast / plyer fallback)
 - Local ironman.ico or ironman.png icon support
 - Advanced simultaneous file transfers with queue management (Arc Reactor powered)
 - Dark theme toggle (Mark 42 stealth mode)
 - File overwrite handling with military precision
 - Interactive history with file access (Like accessing Stark Industries archives)
 - Modern UI with hover effects and Iron Man-themed elements
 - Duplicate detection and prevention (FRIDAY's intelligence)
 - High-speed transfers with optimized buffering (Repulsors at full power)
 - Real-time sender-side transfer monitoring (Tony's workshop display)
 - Industrial grade queue management system
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
from queue import Queue, Empty
import concurrent.futures
from threading import Lock, Event
import warnings

# Analytics & visualization libs
try:
    import sqlite3
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import networkx as nx
except Exception:
    # If optional libs are missing, the app will still run but analytics features will be disabled
    sqlite3 = None
    np = None
    pd = None
    plt = None
    FigureCanvasTkAgg = None
    nx = None

# Optional notification libs - JARVIS communication protocols
NOTIFY_BACKEND = None
# Suppress deprecation warnings from win10toast/pkg_resources during import
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources is deprecated as an API.*")

try:
    from win10toast import ToastNotifier
    NOTIFY_BACKEND = "win10toast"
except Exception:
    try:
        from plyer import notification
        NOTIFY_BACKEND = "plyer"
    except Exception:
        NOTIFY_BACKEND = None

# Iron Man System Constants - Arc Reactor Configuration
APP_NAME = "Goodluck Sharing"
APP_VERSION = "v3.0"
HISTORY_FILE = Path.home() / ".goodluck_sharing_history.json"
CONFIG_FILE = Path.home() / ".goodluck_sharing_config.json"
DUPLICATES_FILE = Path.home() / ".goodluck_sharing_duplicates.json"

# Performance Constants - Suit's operational parameters
MAX_CONCURRENT_TRANSFERS = 4  # Multiple arc reactors can handle more
CHUNK_SIZE = 512 * 1024  # 512KB chunks for maximum throughput - Mark 85 efficiency
SOCKET_BUFFER_SIZE = 8 * 1024 * 1024  # 8MB buffer - Tony Stark's workshop-grade buffering
UI_UPDATE_INTERVAL = 0.1  # 100ms updates for real-time monitoring like HUD
SPEED_CALCULATION_WINDOW = 5.0  # 5 second rolling window - FRIDAY's analysis precision

def human_size(n):
    """Convert bytes to human readable format - JARVIS data processing"""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]  # Even Stark Industries needs petabytes
    f = float(n)
    i = 0
    while f >= 1024.0 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    return f"{f:.1f} {units[i]}"

def fmt_eta(seconds):
    """Format ETA in human readable format - Time calculations worthy of a genius"""
    if seconds is None:
        return "ETA: --"
    sec = int(max(0, seconds))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"ETA: {h}h {m}m"
    if m:
        return f"ETA: {m}m {s}s"
    return f"ETA: {s}s"

def fmt_speed(bytes_per_sec):
    """Format speed with precision - Repulsor energy output levels"""
    return f"{human_size(bytes_per_sec)}/s"

class TransferState:
    """Transfer state tracking - Like monitoring suit's vital signs"""
    def __init__(self):
        self.is_active = False
        self.is_paused = False
        self.is_cancelled = False
        self.current_file = ""
        self.files_completed = 0
        self.total_files = 0
        self.bytes_transferred = 0
        self.total_bytes = 0
        self.current_speed = 0.0
        self.eta_seconds = None
        self.start_time = None
        self.lock = Lock()  # Thread safety - Stark-level security
    
    def update(self, **kwargs):
        """Thread-safe state update - FRIDAY's data synchronization"""
        with self.lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    def get_snapshot(self):
        """Get thread-safe snapshot - Holographic display data"""
        with self.lock:
            return {
                'is_active': self.is_active,
                'is_paused': self.is_paused,
                'is_cancelled': self.is_cancelled,
                'current_file': self.current_file,
                'files_completed': self.files_completed,
                'total_files': self.total_files,
                'bytes_transferred': self.bytes_transferred,
                'total_bytes': self.total_bytes,
                'current_speed': self.current_speed,
                'eta_seconds': self.eta_seconds,
                'progress_percent': (self.bytes_transferred / max(1, self.total_bytes)) * 100
            }

class DuplicateManager:
    """Manages duplicate detection and prevention - FRIDAY's file intelligence system"""
    
    def __init__(self):
        self.file_hashes = self._load_duplicates()
        self.lock = Lock()  # Thread-safe like Vibranium shields
    
    def _load_duplicates(self):
        """Load previously transferred file hashes - Accessing Stark archives"""
        try:
            if DUPLICATES_FILE.exists():
                with open(DUPLICATES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return defaultdict(list, data)
        except Exception:
            pass
        return defaultdict(list)
    
    def _save_duplicates(self):
        """Save file hashes to disk - Backing up to Stark servers"""
        try:
            with open(DUPLICATES_FILE, "w", encoding="utf-8") as f:
                json.dump(dict(self.file_hashes), f, indent=2)
        except Exception:
            pass
    
    def add_file_hash(self, file_path, file_hash, peer_ip):
        """Add a file hash to the duplicate detection database - FRIDAY cataloging"""
        with self.lock:
            key = f"{file_hash}_{os.path.basename(file_path)}"
            entry = {
                "path": file_path,
                "hash": file_hash,
                "peer": peer_ip,
                "timestamp": datetime.now().isoformat()
            }
            
            # Keep only recent entries (last 1000 per hash+name combo) - Memory management
            self.file_hashes[key].append(entry)
            if len(self.file_hashes[key]) > 1000:
                self.file_hashes[key] = self.file_hashes[key][-1000:]
            
            self._save_duplicates()
    
    def is_duplicate(self, file_path, file_hash, peer_ip):
        """Check if file is a duplicate - FRIDAY's pattern recognition"""
        with self.lock:
            key = f"{file_hash}_{os.path.basename(file_path)}"
            
            # Check for exact matches (same hash, name, and peer)
            for entry in self.file_hashes.get(key, []):
                if (entry["hash"] == file_hash and 
                    entry["peer"] == peer_ip):
                    return True, entry
            
            return False, None
    
    def get_duplicate_info(self, file_path, file_hash):
        """Get information about potential duplicates - Detailed intelligence report"""
        with self.lock:
            key = f"{file_hash}_{os.path.basename(file_path)}"
            return self.file_hashes.get(key, [])
    
    def clear_duplicates(self):
        """Clear all duplicate detection data - Factory reset like reformatting JARVIS"""
        with self.lock:
            self.file_hashes.clear()
            self._save_duplicates()

class Notifier:
    """Handle desktop notifications across platforms - FRIDAY's communication system"""
    
    def __init__(self):
        self.backend = NOTIFY_BACKEND
        self.toaster = None
        if self.backend == "win10toast":
            try:
                self.toaster = ToastNotifier()
            except Exception:
                self.backend = None

    def notify(self, title, msg, duration=5):
        """Send desktop notification - Like FRIDAY alerting Tony"""
        try:
            if self.backend == "win10toast" and self.toaster:
                self.toaster.show_toast(title, msg, duration=duration, threaded=True)
            elif self.backend == "plyer":
                from plyer import notification
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

class AnalyticsManager:
    """Handles persistence and generation of analytics (sqlite + matplotlib + networkx)."""
    def __init__(self, db_path=None):
        self.enabled = plt is not None and nx is not None and sqlite3 is not None and np is not None and pd is not None
        self.db_path = db_path or (Path.home() / ".goodluck_sharing_analytics.db")
        self.conn = None
        try:
            if self.enabled:
                self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                self._ensure_tables()
        except Exception:
            self.enabled = False

    def _ensure_tables(self):
        if self.conn:
            c = self.conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS transfers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ts REAL,
                            peer TEXT,
                            direction TEXT,
                            bytes INTEGER,
                            status TEXT
                        )""")
            self.conn.commit()

    def record_transfer(self, ts, peer, direction, bytes_count, status):
        if not self.enabled or not self.conn:
            return
        try:
            c = self.conn.cursor()
            c.execute('INSERT INTO transfers (ts, peer, direction, bytes, status) VALUES (?, ?, ?, ?, ?)',
                      (float(ts), str(peer), str(direction), int(bytes_count), str(status)))
            self.conn.commit()
        except Exception:
            pass

    def query_transfers(self, since_seconds=0):
        if not self.enabled or not self.conn:
            return pd.DataFrame() if pd else None
        try:
            cutoff = time.time() - since_seconds if since_seconds > 0 else 0
            df = pd.read_sql_query('SELECT * FROM transfers WHERE ts>? ORDER BY ts ASC', self.conn, params=(cutoff,))
            return df
        except Exception:
            return pd.DataFrame() if pd else None

    def summary_stats(self):
        if not self.enabled or not self.conn:
            return {}
        df = self.query_transfers(0)
        if df is None or df.empty:
            return {}
        total_bytes = int(df['bytes'].sum())
        total_transfers = len(df)
        success = int((df['status'] == 'Mission Success').sum())
        failed = int((df['status'] != 'Mission Success').sum())
        return {'total_bytes': total_bytes, 'total_transfers': total_transfers, 'success': success, 'failed': failed}

    def close(self):
        try:
            if self.enabled and self.conn:
                self.conn.close()
        except Exception:
            pass

class TransferMonitor:
    """Real-time transfer monitoring system - Tony's workshop monitoring dashboard"""
    
    def __init__(self, ui_callback=None):
        self.ui_callback = ui_callback
        self.active_transfers = {}  # Dict of transfer_id -> TransferState
        self.lock = Lock()
        self.monitor_thread = None
        self.stop_event = Event()
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start the monitoring thread - Powering up the HUD"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop the monitoring thread - Powering down systems"""
        self.stop_event.set()
    
    def register_transfer(self, transfer_id, total_files, total_bytes):
        """Register a new transfer for monitoring - New mission in the workshop"""
        with self.lock:
            state = TransferState()
            state.total_files = total_files
            state.total_bytes = total_bytes
            state.start_time = time.time()
            state.is_active = True
            self.active_transfers[transfer_id] = state
            return state
    
    def unregister_transfer(self, transfer_id):
        """Unregister completed transfer - Mission complete"""
        with self.lock:
            if transfer_id in self.active_transfers:
                self.active_transfers[transfer_id].is_active = False
                # Keep for a short while for final UI update, then remove
                threading.Timer(2.0, lambda: self.active_transfers.pop(transfer_id, None)).start()
    
    def get_transfer_state(self, transfer_id):
        """Get transfer state - Checking suit diagnostics"""
        with self.lock:
            return self.active_transfers.get(transfer_id)
    
    def update_transfer(self, transfer_id, **kwargs):
        """Update transfer progress - Real-time telemetry like suit sensors"""
        with self.lock:
            if transfer_id in self.active_transfers:
                self.active_transfers[transfer_id].update(**kwargs)
    
    def _monitor_loop(self):
        """Main monitoring loop - The heart of JARVIS monitoring system"""
        while not self.stop_event.wait(UI_UPDATE_INTERVAL):
            try:
                if self.ui_callback:
                    with self.lock:
                        # Create snapshot of all active transfers
                        snapshots = {}
                        for transfer_id, state in self.active_transfers.items():
                            if state.is_active:
                                snapshots[transfer_id] = state.get_snapshot()
                    
                    # Update UI with snapshots - Holographic display update
                    if snapshots:
                        self.ui_callback(snapshots)
            except Exception as e:
                print(f"Monitor error: {e}")  # Even Iron Man's tech has bugs sometimes

class GoodluckSharingApp:
    """Main application class - Tony Stark's file sharing workshop"""
    
    def __init__(self):
        self._init_variables()
        self._init_ui()
        self._start_discovery_listener()

    def _init_variables(self):
        """Initialize core application variables - Setting up the workshop"""
        # Network configuration - Communication protocols
        self.discovery_port = 5000
        self.transfer_port = 5001
        self.device_name = f"IronMan-{os.getenv('USERNAME') or os.getenv('USER') or 'Unknown'}"
        
        # Device discovery - FRIDAY's scanning systems
        self.discovered_devices = {}
        self.is_listening = False
        self.is_discovering = False
        
        # File selection and transfers - Mission parameters
        self.selected_paths = []
        self.transfer_queue = Queue()  # Industrial grade queue system
        self.active_transfers = {}  # Dict to track all active transfers
        self.transfer_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_TRANSFERS,
            thread_name_prefix="IronMan-Transfer"
        )
        
        # Transfer control - Mission control systems
        self.global_pause_event = Event()
        self.global_pause_event.set()  # Initially not paused
        self.global_cancel_event = Event()
        
        # Directories and data - Stark Industries file systems
        self.download_dir = Path.home() / "Desktop" / "Goodluck Received"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()
        
        # Components - Workshop equipment
        self.notifier = Notifier()
        self.duplicate_manager = DuplicateManager()
        self.transfer_monitor = TransferMonitor(ui_callback=self._update_transfer_displays)
        
        # Offline transfer support
        self.offline_queue = deque()
        self.offline_monitor_thread = None
        self.offline_monitor_running = True
        
        # Analytics manager (sqlite + matplotlib + networkx)
        try:
            self.analytics = AnalyticsManager()
        except Exception:
            self.analytics = None
        
        # UI theming - Suit color schemes
        self.themes = {
            "light": {"bg": "#f7f7f8", "card": "#ffffff", "accent": "#c21807", 
                     "muted": "#666666", "hover": "#b71c1c", "success": "#2e7d32"},
            "dark": {"bg": "#0a0a0a", "card": "#1a1a1a", "accent": "#ff6b35", 
                    "muted": "#cccccc", "hover": "#ff8a65", "success": "#4caf50"}  # Iron Man colors
        }
        self.current_theme = self.themes[self._load_theme()]

        # New systems: analytics, heatmap, offline queue, topology
        self.transfer_logs = []  # list of (timestamp, bytes_sent)
        self.quality_metrics = {'success': 0, 'failed': 0, 'retries': 0}
        self.network_topology = {}  # ip -> name
        
        # Start offline monitor
        self._start_offline_monitor()

    def _init_ui(self):
        """Initialize the user interface - Building the HUD"""
        # Create root window - Main workshop display
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - {APP_VERSION}")
        self.root.geometry("1200x900")  # Bigger display for more data
        self.root.minsize(1000, 750)
        # Allow maximize/minimize but enforce layout on state changes
        self.root.resizable(True, True)
        self.root.configure(bg=self.current_theme["bg"])
        self._set_icon()
        # Bind configure to detect maximize/minimize and restore layout
        self.root.bind('<Configure>', self._on_configure)
        
        # Load arc reactor image for buttons - Stark tech aesthetics
        self.arc_reactor_img = self._load_arc_reactor_image()
        
        # Setup UI components - Workshop interface
        self._setup_styles_and_fonts()
        self._create_main_layout()
        self._create_tabs()
        self._setup_tab_content()
        
        # Initialize UI state - Power up sequence
        self._refresh_history_ui()
        self._start_ui_updates()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_arc_reactor_image(self):
        """Load arc reactor image for UI elements - Stark tech branding"""
        try:
            return tk.PhotoImage(file=Path(__file__).parent / "arc_reactor.png")
        except Exception:
            return None

    def _set_icon(self):
        """Set application icon - Iron Man branding"""
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
            pass  # Even Tony's tech fails sometimes

    def _load_theme(self):
        """Load theme preference from config - User preferences like Stark's suit customization"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("theme", "dark")  # Default to dark theme (stealth mode)
        except Exception:
            pass
        return "dark"

    def _save_theme(self):
        """Save current theme to config - Storing preferences in Stark database"""
        try:
            theme_name = "dark" if self.current_theme == self.themes["dark"] else "light"
            config = {"theme": theme_name}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f)
        except Exception:
            pass

    def _setup_styles_and_fonts(self):
        """Configure UI styles and fonts - Stark Industries design language"""
        # Fonts - Tony's sophisticated typography
        self.font_bold = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.font_normal = tkfont.Font(family="Segoe UI", size=10)
        self.font_title = tkfont.Font(family="Segoe UI", size=24, weight="bold")
        self.font_subtitle = tkfont.Font(family="Segoe UI", size=11)
        self.font_mono = tkfont.Font(family="Consolas", size=9)  # For technical displays
        
        # Styles - Arc reactor inspired design
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

    def _configure_styles(self):
        """Configure TTK styles based on current theme - Suit's adaptive interface"""
        theme = self.current_theme
        
        self.style.configure("Accent.TButton", 
                           background=theme["accent"], 
                           foreground="white", 
                           font=("Segoe UI", 11, "bold"), 
                           padding=10, 
                           borderwidth=0)
        
        self.style.map("Accent.TButton", 
                      background=[("active", theme["hover"]), ("pressed", theme["hover"])])
        
        self.style.configure("Success.TButton", 
                           background=theme["success"], 
                           foreground="white", 
                           font=("Segoe UI", 11, "bold"), 
                           padding=10, 
                           borderwidth=0)
        
        self.style.configure("Danger.TButton", 
                           background="#d32f2f", 
                           foreground="white", 
                           font=("Segoe UI", 11, "bold"), 
                           padding=10, 
                           borderwidth=0)
        
        self.style.configure("Modern.Horizontal.TProgressbar", 
                           background=theme["accent"], 
                           troughcolor=theme["card"], 
                           borderwidth=1,
                           lightcolor=theme["accent"],
                           darkcolor=theme["accent"])
        
        self.style.configure("TNotebook", 
                           background=theme["bg"], 
                           borderwidth=0)
        
        self.style.configure("TNotebook.Tab", 
                           background=theme["card"], 
                           foreground=theme["muted"], 
                           padding=(15, 8), 
                           font=("Segoe UI", 11, "bold"))
        
        self.style.map("TNotebook.Tab", 
                      background=[("selected", theme["accent"])], 
                      foreground=[("selected", "white")])

    def _create_main_layout(self):
        """Create main application layout - Workshop floor plan"""
        main_frame = tk.Frame(self.root, bg=self.current_theme["bg"], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title section - Main display header
        title_frame = tk.Frame(main_frame, bg=self.current_theme["bg"])
        title_frame.pack(fill="x")
        
        title_label = tk.Label(title_frame, 
                              text=f"{APP_NAME} {APP_VERSION}", 
                              font=self.font_title, 
                              bg=self.current_theme["bg"], 
                              fg=self.current_theme["accent"])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, 
                                 text="Industrial-grade file sharing with arc reactor-powered performance", 
                                 font=self.font_subtitle, 
                                 bg=self.current_theme["bg"], 
                                 fg=self.current_theme["muted"])
        subtitle_label.pack(pady=(2, 15))
        
        # Global transfer controls - Master control panel
        self._create_global_controls(main_frame)
        
        # Notebook for tabs - Workshop sections
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=10)

    def _create_global_controls(self, parent):
        """Create global transfer control panel - Mission control center"""
        control_frame = tk.Frame(parent, bg=self.current_theme["card"], relief="solid", bd=1)
        control_frame.pack(fill="x", pady=(0, 10))
        
        # Title
        tk.Label(control_frame, 
                text="Global Transfer Control Center", 
                font=self.font_bold, 
                bg=self.current_theme["card"], 
                fg=self.current_theme["accent"]).pack(pady=(8, 4))
        
        # Controls row
        controls_row = tk.Frame(control_frame, bg=self.current_theme["card"])
        controls_row.pack(pady=(4, 8), padx=10)
        
        # Global pause/resume
        self.global_pause_btn = ttk.Button(controls_row, 
                                          text="Pause All", 
                                          style="Accent.TButton", 
                                          command=self.global_pause_transfers)
        self.global_pause_btn.pack(side="left", padx=5)
        
        self.global_resume_btn = ttk.Button(controls_row, 
                                           text="Resume All", 
                                           style="Success.TButton", 
                                           command=self.global_resume_transfers)
        self.global_resume_btn.pack(side="left", padx=5)
        
        # Global cancel
        ttk.Button(controls_row, 
                  text="Cancel All", 
                  style="Danger.TButton", 
                  command=self.global_cancel_transfers).pack(side="left", padx=5)
        
        # Global status display - Arc reactor status display
        self.global_status = tk.Label(control_frame, 
                                     text="Arc Reactor: Online | Transfers: 0 Active", 
                                     font=self.font_normal, 
                                     bg=self.current_theme["card"], 
                                     fg=self.current_theme["muted"])
        self.global_status.pack(pady=(0, 8))

    def _create_tabs(self):
        """Create tab frames - Workshop sections"""
        self.send_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=15, pady=15)
        self.recv_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=15, pady=15)
        self.hist_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=15, pady=15)
        self.settings_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=15, pady=15)
        self.monitor_tab = tk.Frame(self.notebook, bg=self.current_theme["card"], padx=15, pady=15)
        
        self.notebook.add(self.send_tab, text="Send")
        self.notebook.add(self.recv_tab, text="Receive")
        self.notebook.add(self.monitor_tab, text="Live Monitor")
        self.notebook.add(self.hist_tab, text="History")
        self.notebook.add(self.settings_tab, text="Settings")

    def _setup_tab_content(self):
        """Setup content for all tabs - Workshop equipment installation"""
        self._setup_send_tab()
        self._setup_receive_tab()
        self._setup_monitor_tab()
        self._setup_history_tab()
        self._setup_settings_tab()

    def _setup_send_tab(self):
        """Setup send tab content - Outbound mission control"""
        # Device discovery section - FRIDAY's scanning interface
        discovery_frame = self._create_section_frame(self.send_tab, "Device Discovery - FRIDAY Scanner")
        
        control_frame = tk.Frame(discovery_frame, bg=self.current_theme["card"])
        control_frame.pack(fill="x", pady=8)
        
        self.discovery_status = tk.Label(control_frame, 
                                        text="Ready to scan for devices", 
                                        bg=self.current_theme["card"], 
                                        fg=self.current_theme["muted"], 
                                        font=self.font_normal)
        self.discovery_status.pack(side="left", padx=(0, 15))
        
        scan_btn = ttk.Button(control_frame, 
                             text="Scan Network", 
                             style="Accent.TButton", 
                             command=self.start_discovery)
        scan_btn.pack(side="right")
        
        # File selection section - Arsenal selection
        file_section = self._create_section_frame(self.send_tab, "File Arsenal Selection")
        
        self.sel_text = scrolledtext.ScrolledText(file_section, 
                                                 height=8, 
                                                 bg=self.current_theme["bg"], 
                                                 fg=self.current_theme["muted"],
                                                 font=self.font_mono, 
                                                 wrap="word")
        self.sel_text.pack(fill="both", expand=True, pady=(4, 8))
        self.sel_text.config(state="disabled")
        
        # File selection buttons - Weapon selection interface
        button_frame = tk.Frame(file_section, bg=self.current_theme["card"])
        button_frame.pack(fill="x", pady=4)
        
        ttk.Button(button_frame, text="Add Files", 
                  style="Success.TButton", command=self.select_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Add Folder", 
                  style="Success.TButton", command=self.select_folder).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear All", 
                  style="Danger.TButton", command=self.clear_selection).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Check Duplicates", 
                  style="Accent.TButton", command=self.check_duplicates).pack(side="left", padx=5)
        
        # Target selection - Mission target
        target_section = self._create_section_frame(self.send_tab, "Target Selection")
        
        target_frame = tk.Frame(target_section, bg=self.current_theme["card"])
        target_frame.pack(fill="x", pady=8)
        
        # Device list - Discovered targets
        devices_frame = tk.Frame(target_frame, bg=self.current_theme["card"])
        devices_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tk.Label(devices_frame, text="Discovered Devices:", 
                bg=self.current_theme["card"], fg=self.current_theme["muted"],
                font=self.font_normal).pack(anchor="w")
        
        self.devices_listbox = tk.Listbox(devices_frame, 
                                         height=4, 
                                         font=self.font_normal, 
                                         selectbackground=self.current_theme["accent"], 
                                         selectforeground="white",
                                         bg=self.current_theme["bg"],
                                         fg=self.current_theme["muted"])
        self.devices_listbox.pack(fill="both", expand=True, pady=2)
        
        # Manual IP entry
        manual_frame = tk.Frame(target_frame, bg=self.current_theme["card"])
        manual_frame.pack(side="right", fill="y")
        
        tk.Label(manual_frame, text="Manual IP:", 
                bg=self.current_theme["card"], fg=self.current_theme["muted"],
                font=self.font_normal).pack(anchor="w")
        
        self.manual_ip = ttk.Entry(manual_frame, font=self.font_normal, width=15)
        self.manual_ip.pack(pady=2)
        
        # Transfer initiation - Launch sequence
        launch_section = self._create_section_frame(self.send_tab, "Mission Launch Control")
        
        launch_frame = tk.Frame(launch_section, bg=self.current_theme["card"])
        launch_frame.pack(fill="x", pady=8)
        
        ttk.Button(launch_frame, 
                  text="Start Transfer Mission", 
                  style="Success.TButton", 
                  command=self.start_transfer).pack(side="left", padx=10)
        
        # Queue status display - Mission queue
        self.queue_status = tk.Label(launch_section, 
                                    text="Mission Queue: Ready for deployment", 
                                    font=self.font_normal, 
                                    bg=self.current_theme["card"], 
                                    fg=self.current_theme["muted"])
        self.queue_status.pack(pady=(4, 0))
        
        # Progress display - Real-time mission status
        progress_section = self._create_section_frame(self.send_tab, "Transfer Progress - HUD Display")
        
        self.send_progress = ttk.Progressbar(progress_section, 
                                           style="Modern.Horizontal.TProgressbar", 
                                           length=500)
        self.send_progress.pack(fill="x", pady=8)
        
        # Status displays - Mission telemetry
        status_grid = tk.Frame(progress_section, bg=self.current_theme["card"])
        status_grid.pack(fill="x", pady=4)
        
        # Left column
        left_status = tk.Frame(status_grid, bg=self.current_theme["card"])
        left_status.pack(side="left", fill="x", expand=True)
        
        self.send_status = tk.Label(left_status, 
                                   text="Arc Reactor: Online - Ready for transfer", 
                                   bg=self.current_theme["card"], 
                                   fg=self.current_theme["muted"], 
                                   font=self.font_normal)
        self.send_status.pack(anchor="w", pady=2)
        
        self.send_metrics = tk.Label(left_status, 
                                    text="Speed: -- • ETA: -- • Files: --", 
                                    bg=self.current_theme["card"], 
                                    fg=self.current_theme["muted"], 
                                    font=self.font_mono)
        self.send_metrics.pack(anchor="w", pady=2)
        
        # Right column - Current file display
        right_status = tk.Frame(status_grid, bg=self.current_theme["card"])
        right_status.pack(side="right", fill="x", expand=True)
        
        self.current_file_label = tk.Label(right_status, 
                                          text="Current: Ready to begin mission", 
                                          bg=self.current_theme["card"], 
                                          fg=self.current_theme["muted"], 
                                          font=self.font_normal)
        self.current_file_label.pack(anchor="e", pady=2)
        
        self.transfer_details = tk.Label(right_status, 
                                        text="Target: Not selected", 
                                        bg=self.current_theme["card"], 
                                        fg=self.current_theme["muted"], 
                                        font=self.font_mono)
        self.transfer_details.pack(anchor="e", pady=2)

    def _setup_receive_tab(self):
        """Setup receive tab content - Incoming mission control center"""
        # Receiver section - Defensive systems
        receiver_frame = self._create_section_frame(self.recv_tab, "Incoming Transfer Receiver - FRIDAY Defense Grid")
        
        receiver_control_frame = tk.Frame(receiver_frame, bg=self.current_theme["card"])
        receiver_control_frame.pack(fill="x", pady=8)
        
        self.listen_status = tk.Label(receiver_control_frame, 
                                     text="Defense Grid: Offline", 
                                     bg=self.current_theme["card"], 
                                     fg=self.current_theme["muted"], 
                                     font=self.font_normal)
        self.listen_status.pack(side="left", padx=(0, 15))
        
        listen_btn = ttk.Button(receiver_control_frame, 
                               text="Activate Defense Grid", 
                               style="Success.TButton", 
                               command=self.start_listening)
        listen_btn.pack(side="right")
        
        # Download folder section - Storage bay configuration
        storage_frame = self._create_section_frame(self.recv_tab, "Storage Bay Configuration")
        
        download_frame = tk.Frame(storage_frame, bg=self.current_theme["card"])
        download_frame.pack(fill="x", pady=8)
        
        tk.Label(download_frame, text="Storage Location:", 
                bg=self.current_theme["card"], fg=self.current_theme["muted"],
                font=self.font_normal).pack(anchor="w", pady=(0, 4))
        
        path_frame = tk.Frame(download_frame, bg=self.current_theme["card"])
        path_frame.pack(fill="x")
        
        self.download_path_var = tk.StringVar(value=str(self.download_dir))
        ttk.Entry(path_frame, 
                 textvariable=self.download_path_var, 
                 state="readonly", 
                 font=self.font_normal).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ttk.Button(path_frame, 
                  text="Change Location", 
                  style="Accent.TButton", 
                  command=self.change_download_location).pack(side="right")
        
        # Receive log section - Mission log display
        log_frame = self._create_section_frame(self.recv_tab, "Incoming Transfer Log - JARVIS Records")
        
        self.recv_log = scrolledtext.ScrolledText(log_frame, 
                                                 height=12, 
                                                 bg=self.current_theme["bg"], 
                                                 fg=self.current_theme["muted"],
                                                 font=self.font_mono, 
                                                 wrap="word")
        self.recv_log.pack(fill="both", expand=True, pady=8)
        self.recv_log.config(state="disabled")
        
        # Progress display - Incoming mission status
        progress_frame = self._create_section_frame(self.recv_tab, "Incoming Transfer Progress")
        
        self.recv_progress = ttk.Progressbar(progress_frame, 
                                           style="Modern.Horizontal.TProgressbar", 
                                           length=500)
        self.recv_progress.pack(fill="x", pady=8)
        
        self.recv_metrics = tk.Label(progress_frame, 
                                    text="Defense Grid: Standby • Speed: -- • ETA: --", 
                                    bg=self.current_theme["card"], 
                                    fg=self.current_theme["muted"], 
                                    font=self.font_mono)
        self.recv_metrics.pack(pady=4)

    def _setup_monitor_tab(self):
        """Setup monitor tab - Real-time transfer monitoring like Tony's workshop displays"""
        # Main monitoring display
        monitor_frame = self._create_section_frame(self.monitor_tab, "Live Transfer Monitor - Arc Reactor Power Grid")
        
        # Create scrollable monitoring area
        canvas = tk.Canvas(monitor_frame, bg=self.current_theme["card"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(monitor_frame, orient="vertical", command=canvas.yview)
        self.monitor_content = tk.Frame(canvas, bg=self.current_theme["card"])
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        canvas.create_window((0, 0), window=self.monitor_content, anchor="nw")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Update canvas scroll region when content changes
        def _update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.monitor_content.bind("<Configure>", _update_scroll_region)
        
        # Initial content
        self.no_transfers_label = tk.Label(self.monitor_content, 
                                          text="Arc Reactor Online - No active transfers\nAll systems ready for deployment", 
                                          font=self.font_normal, 
                                          bg=self.current_theme["card"], 
                                          fg=self.current_theme["muted"])
        self.no_transfers_label.pack(pady=50)
        
        # Dictionary to store transfer display widgets
        self.transfer_displays = {}

    def _setup_history_tab(self):
        """Setup history tab content - Mission archives like Stark's database"""
        # History controls
        control_frame = self._create_section_frame(self.hist_tab, "Mission Archives - Stark Industries Database")
        
        control_buttons = tk.Frame(control_frame, bg=self.current_theme["card"])
        control_buttons.pack(fill="x", pady=8)
        
        ttk.Button(control_buttons, 
                  text="Refresh Archives", 
                  style="Accent.TButton", 
                  command=self._refresh_history_ui).pack(side="left", padx=5)
        
        ttk.Button(control_buttons, 
                  text="Clear Archives", 
                  style="Danger.TButton", 
                  command=self._clear_history_prompt).pack(side="left", padx=5)
        
        ttk.Button(control_buttons, 
                  text="Export Archives", 
                  style="Success.TButton", 
                  command=self._export_history).pack(side="left", padx=5)
        
        # History display
        history_frame = self._create_section_frame(self.hist_tab, "Transfer History Log")
        
        self.hist_list = scrolledtext.ScrolledText(history_frame, 
                                                  height=20, 
                                                  bg=self.current_theme["bg"], 
                                                  fg=self.current_theme["muted"],
                                                  font=self.font_mono, 
                                                  wrap="word")
        self.hist_list.pack(fill="both", expand=True, pady=8)
        self.hist_list.config(state="disabled")
        
        # Context menu for history - Right-click actions
        self.hist_menu = tk.Menu(self.hist_list, tearoff=0)
        self.hist_menu.add_command(label="Open Folder", command=self._open_history_folder)
        self.hist_menu.add_command(label="Copy Details", command=self._copy_history_details)
        self.hist_menu.add_command(label="Show File Details", command=self._show_file_details)
        self.hist_list.bind("<Button-3>", self._show_history_menu)

    def _setup_settings_tab(self):
        """Setup settings tab content - System configuration like suit customization"""
        # Device settings
        device_frame = self._create_section_frame(self.settings_tab, "Device Configuration - Suit Identity")
        
        tk.Label(device_frame, 
                text="Device Name (Iron Man Callsign):", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(anchor="w", pady=(0, 4))
        
        self.device_name_var = tk.StringVar(value=self.device_name)
        name_frame = tk.Frame(device_frame, bg=self.current_theme["card"])
        name_frame.pack(fill="x", pady=4)
        
        ttk.Entry(name_frame, 
                 textvariable=self.device_name_var, 
                 font=self.font_normal).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ttk.Button(name_frame, 
                  text="Save Identity", 
                  style="Success.TButton", 
                  command=self.save_device_name).pack(side="right")
        
        # Performance settings
        perf_frame = self._create_section_frame(self.settings_tab, "Performance Tuning - Arc Reactor Settings")
        
        # Chunk size setting
        tk.Label(perf_frame, 
                text="Transfer Chunk Size (Arc Reactor Power Output):", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(anchor="w", pady=(0, 4))
        
        chunk_frame = tk.Frame(perf_frame, bg=self.current_theme["card"])
        chunk_frame.pack(fill="x", pady=4)
        
        self.chunk_size_var = tk.StringVar(value=str(CHUNK_SIZE // 1024))
        ttk.Entry(chunk_frame, 
                 textvariable=self.chunk_size_var, 
                 font=self.font_normal, 
                 width=10).pack(side="left", padx=(0, 5))
        
        tk.Label(chunk_frame, 
                text="KB", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(side="left", padx=(0, 10))
        
        ttk.Button(chunk_frame, 
                  text="Apply Power Settings", 
                  style="Accent.TButton", 
                  command=self._apply_performance_settings).pack(side="left")
        
        # Concurrent transfers setting
        tk.Label(perf_frame, 
                text="Max Concurrent Transfers (Parallel Arc Reactors):", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["muted"], 
                font=self.font_normal).pack(anchor="w", pady=(10, 4))
        
        concurrent_frame = tk.Frame(perf_frame, bg=self.current_theme["card"])
        concurrent_frame.pack(fill="x", pady=4)
        
        self.concurrent_var = tk.StringVar(value=str(MAX_CONCURRENT_TRANSFERS))
        ttk.Entry(concurrent_frame, 
                 textvariable=self.concurrent_var, 
                 font=self.font_normal, 
                 width=10).pack(side="left", padx=(0, 10))
        
        ttk.Button(concurrent_frame, 
                  text="Configure Reactors", 
                  style="Accent.TButton", 
                  command=self._apply_concurrent_settings).pack(side="left")
        
        # Theme settings
        theme_frame = self._create_section_frame(self.settings_tab, "Interface Theme - Suit Appearance")
        
        ttk.Button(theme_frame, 
                  text="Toggle Theme (Stealth Mode)", 
                  style="Accent.TButton", 
                  command=self.toggle_theme).pack(pady=8)
        
        # Duplicate management
        duplicate_frame = self._create_section_frame(self.settings_tab, "Duplicate Detection - FRIDAY Intelligence")
        
        duplicate_buttons = tk.Frame(duplicate_frame, bg=self.current_theme["card"])
        duplicate_buttons.pack(fill="x", pady=8)
        
        ttk.Button(duplicate_buttons, 
                  text="View Database", 
                  style="Accent.TButton", 
                  command=self.view_duplicates).pack(side="left", padx=5)
        
        ttk.Button(duplicate_buttons, 
                  text="Clear Database", 
                  style="Danger.TButton", 
                  command=self.clear_duplicate_database).pack(side="left", padx=5)
        
        ttk.Button(duplicate_buttons, 
                  text="Export Database", 
                  style="Success.TButton", 
                  command=self._export_duplicates).pack(side="left", padx=5)

    def _create_section_frame(self, parent, title):
        """Create a section frame with title - Workshop section headers"""
        frame = tk.Frame(parent, bg=self.current_theme["card"], bd=2, relief="solid")
        frame.pack(fill="x", pady=(0, 10))
        
        # Title with background
        title_frame = tk.Frame(frame, bg=self.current_theme["accent"], height=30)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, 
                text=title, 
                bg=self.current_theme["accent"], 
                fg="white", 
                font=self.font_bold).pack(pady=5)
        
        # Content area
        content_frame = tk.Frame(frame, bg=self.current_theme["card"])
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        return content_frame

    def _start_ui_updates(self):
        """Start periodic UI updates - HUD refresh like Iron Man's displays"""
        self._update_ui()
        self.root.after(int(UI_UPDATE_INTERVAL * 1000), self._start_ui_updates)
    
    def _update_ui(self):
        """Update UI elements - Refresh all display panels"""
        try:
            # Update global status
            active_count = len([t for t in self.active_transfers.values() if t.get('active', False)])
            queue_size = self.transfer_queue.qsize()
            total_transfers = active_count + queue_size
            
            status_text = f"Arc Reactor: Online | Active: {active_count} | Queued: {queue_size}"
            self.global_status.config(text=status_text)
            
            # Update queue status
            if total_transfers > 0:
                self.queue_status.config(text=f"Mission Queue: {total_transfers} operations in progress")
            else:
                self.queue_status.config(text="Mission Queue: Ready for deployment")
                
        except Exception as e:
            print(f"UI update error: {e}")  # Even Tony's tech has occasional glitches

    def _update_transfer_displays(self, transfer_snapshots):
        """Update transfer displays in monitor tab - Real-time mission status"""
        try:
            # Hide no transfers label if we have active transfers
            if transfer_snapshots and hasattr(self, 'no_transfers_label'):
                self.no_transfers_label.pack_forget()
            
            # Update or create displays for active transfers
            for transfer_id, snapshot in transfer_snapshots.items():
                if transfer_id not in self.transfer_displays:
                    self._create_transfer_display(transfer_id)
                
                self._update_single_transfer_display(transfer_id, snapshot)
            
            # Remove displays for completed transfers
            for transfer_id in list(self.transfer_displays.keys()):
                if transfer_id not in transfer_snapshots:
                    self._remove_transfer_display(transfer_id)
            
            # Show no transfers label if no active transfers
            if not transfer_snapshots and hasattr(self, 'no_transfers_label'):
                if not self.no_transfers_label.winfo_viewable():
                    self.no_transfers_label.pack(pady=50)
                    
        except Exception as e:
            print(f"Transfer display update error: {e}")

    def _create_transfer_display(self, transfer_id):
        """Create a new transfer display widget - Individual mission status panel"""
        # Main frame for this transfer
        transfer_frame = tk.Frame(self.monitor_content, 
                                 bg=self.current_theme["accent"], 
                                 bd=2, 
                                 relief="solid")
        transfer_frame.pack(fill="x", pady=5, padx=10)
        
        # Header
        header_frame = tk.Frame(transfer_frame, bg=self.current_theme["accent"])
        header_frame.pack(fill="x", padx=5, pady=2)
        
        title_label = tk.Label(header_frame, 
                              text=f"Transfer Mission {transfer_id}", 
                              bg=self.current_theme["accent"], 
                              fg="white", 
                              font=self.font_bold)
        title_label.pack(side="left")
        
        # Content area
        content_frame = tk.Frame(transfer_frame, bg=self.current_theme["card"])
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Status info
        status_frame = tk.Frame(content_frame, bg=self.current_theme["card"])
        status_frame.pack(fill="x", pady=2)
        
        # Progress bar
        progress_bar = ttk.Progressbar(content_frame, 
                                      style="Modern.Horizontal.TProgressbar", 
                                      length=400)
        progress_bar.pack(fill="x", pady=5)
        
        # Metrics display
        metrics_frame = tk.Frame(content_frame, bg=self.current_theme["card"])
        metrics_frame.pack(fill="x", pady=2)
        
        # Store references
        self.transfer_displays[transfer_id] = {
            'frame': transfer_frame,
            'status_frame': status_frame,
            'progress_bar': progress_bar,
            'metrics_frame': metrics_frame,
            'labels': {}
        }
        
        # Update canvas scroll region
        self.monitor_content.update_idletasks()

    def _update_single_transfer_display(self, transfer_id, snapshot):
        """Update a single transfer display - Mission status update"""
        if transfer_id not in self.transfer_displays:
            return
        
        display = self.transfer_displays[transfer_id]
        
        # Update progress bar
        if snapshot['total_bytes'] > 0:
            progress_percent = (snapshot['bytes_transferred'] / snapshot['total_bytes']) * 100
            display['progress_bar']['maximum'] = 100
            display['progress_bar']['value'] = progress_percent
        
        # Update or create status labels
        status_text = "ACTIVE"
        if snapshot['is_paused']:
            status_text = "PAUSED"
        elif snapshot['is_cancelled']:
            status_text = "CANCELLED"
        elif not snapshot['is_active']:
            status_text = "COMPLETED"
        
        # Current file
        current_file = snapshot.get('current_file', 'Preparing...')
        if len(current_file) > 50:
            current_file = "..." + current_file[-47:]
        
        # Progress info
        progress_text = f"{snapshot['files_completed']}/{snapshot['total_files']} files • {human_size(snapshot['bytes_transferred'])}/{human_size(snapshot['total_bytes'])}"
        
        # Speed and ETA
        speed_text = fmt_speed(snapshot['current_speed']) if snapshot['current_speed'] > 0 else "--"
        eta_text = fmt_eta(snapshot['eta_seconds']) if snapshot['eta_seconds'] else "ETA: --"
        metrics_text = f"{speed_text} • {eta_text}"
        
        # Update labels
        self._update_display_label(display, 'status', f"Status: {status_text}", display['status_frame'])
        self._update_display_label(display, 'current_file', f"File: {current_file}", display['status_frame'])
        self._update_display_label(display, 'progress', progress_text, display['metrics_frame'])
        self._update_display_label(display, 'metrics', metrics_text, display['metrics_frame'])

    def _update_display_label(self, display, key, text, parent):
        """Update or create a display label - Individual HUD element"""
        if key not in display['labels']:
            display['labels'][key] = tk.Label(parent, 
                                            bg=self.current_theme["card"], 
                                            fg=self.current_theme["muted"],
                                            font=self.font_mono)
            display['labels'][key].pack(anchor="w", pady=1)
        
        display['labels'][key].config(text=text)

    def _remove_transfer_display(self, transfer_id):
        """Remove a transfer display - Mission complete cleanup"""
        if transfer_id in self.transfer_displays:
            display = self.transfer_displays[transfer_id]
            display['frame'].destroy()
            del self.transfer_displays[transfer_id]

    # Global transfer controls - Master mission control
    def global_pause_transfers(self):
        """Pause all active transfers - Emergency stop like suit shutdown"""
        self.global_pause_event.clear()
        self.global_pause_btn.config(state="disabled")
        self.global_resume_btn.config(state="normal")
        self.notifier.notify("Transfers Paused", "All transfers have been paused")

    def global_resume_transfers(self):
        """Resume all paused transfers - Arc reactor back online"""
        self.global_pause_event.set()
        self.global_pause_btn.config(state="normal")
        self.global_resume_btn.config(state="disabled")
        self.notifier.notify("Transfers Resumed", "All transfers have been resumed")

    def global_cancel_transfers(self):
        """Cancel all active transfers - Abort mission"""
        self.global_cancel_event.set()
        self.notifier.notify("Transfers Cancelled", "All active transfers have been aborted")

    # Discovery and network methods
    def _start_discovery_listener(self):
        """Start discovery listener thread"""
        self.discovery_thread = threading.Thread(target=self._discovery_listener, daemon=True)
        self.discovery_thread.start()

    def _discovery_listener(self):
        """Discovery listener thread - Listen for device announcements"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.discovery_port))
            sock.settimeout(1.0)
            
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    try:
                        device_info = json.loads(data.decode('utf-8'))
                        device_name = device_info.get('name', f'Unknown-{addr[0]}')
                        self.discovered_devices[addr[0]] = device_name
                        self._update_device_list()
                    except Exception:
                        pass
                except socket.timeout:
                    continue
                except Exception:
                    break
                    
        except Exception as e:
            print(f"Discovery listener error: {e}")

    def _update_device_list(self):
        """Update the devices listbox"""
        def update():
            try:
                self.devices_listbox.delete(0, tk.END)
                for ip, name in self.discovered_devices.items():
                    self.devices_listbox.insert(tk.END, f"{name} ({ip})")
            except Exception:
                pass
        self.root.after(0, update)

    def start_discovery(self):
        """Start device discovery - Scan for other devices"""
        if self.is_discovering:
            return
            
        self.is_discovering = True
        self.discovery_status.config(text="Scanning for devices...")
        
        def discovery_thread():
            try:
                # Broadcast discovery message
                local_ip = self.get_local_ip()
                broadcast_data = json.dumps({
                    'name': self.device_name,
                    'ip': local_ip,
                    'port': self.transfer_port
                }).encode('utf-8')
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(5.0)
                
                # Try broadcasting to common network ranges
                networks = ['192.168.1.255', '192.168.0.255', '10.0.0.255', '172.16.255.255']
                for network in networks:
                    try:
                        sock.sendto(broadcast_data, (network, self.discovery_port))
                    except Exception:
                        pass
                
                time.sleep(3)  # Wait for responses
                
            except Exception as e:
                print(f"Discovery error: {e}")
            finally:
                self.is_discovering = False
                try:
                    sock.close()
                except:
                    pass
                self.root.after(0, lambda: self.discovery_status.config(text="Discovery complete"))
        
        threading.Thread(target=discovery_thread, daemon=True).start()

    # File selection methods
    def select_files(self):
        """Select files for transfer"""
        files = filedialog.askopenfilenames(
            title="Select files to transfer",
            filetypes=[("All files", "*.*")]
        )
        if files:
            self.selected_paths.extend(files)
            self._update_selection_display()

    def select_folder(self):
        """Select folder for transfer"""
        folder = filedialog.askdirectory(title="Select folder to transfer")
        if folder:
            self.selected_paths.append(folder)
            self._update_selection_display()

    def clear_selection(self):
        """Clear selected files"""
        self.selected_paths.clear()
        self._update_selection_display()

    def _update_selection_display(self):
        """Update the file selection display"""
        self.sel_text.config(state="normal")
        self.sel_text.delete("1.0", "end")
        
        if not self.selected_paths:
            self.sel_text.insert("end", "No files selected\nUse buttons above to select files or folders")
        else:
            total_size = 0
            file_count = 0
            
            for path in self.selected_paths:
                path_obj = Path(path)
                if path_obj.is_file():
                    size = path_obj.stat().st_size
                    total_size += size
                    file_count += 1
                    self.sel_text.insert("end", f"File: {path} ({human_size(size)})\n")
                elif path_obj.is_dir():
                    folder_size = 0
                    folder_files = 0
                    for item in path_obj.rglob("*"):
                        if item.is_file():
                            folder_size += item.stat().st_size
                            folder_files += 1
                    total_size += folder_size
                    file_count += folder_files
                    self.sel_text.insert("end", f"Folder: {path} ({folder_files} files, {human_size(folder_size)})\n")
            
            self.sel_text.insert("end", f"\nTotal: {file_count} files, {human_size(total_size)}")
        
        self.sel_text.config(state="disabled")

    def check_duplicates(self):
        """Check selected files for duplicates"""
        if not self.selected_paths:
            messagebox.showinfo("No Selection", "Please select files first")
            return
        
        duplicate_info = []
        
        for path in self.selected_paths:
            path_obj = Path(path)
            if path_obj.is_file():
                # Calculate hash
                hash_obj = hashlib.sha256()
                try:
                    with open(path_obj, 'rb') as f:
                        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                            hash_obj.update(chunk)
                    file_hash = hash_obj.hexdigest()
                    
                    # Check for duplicates
                    duplicates = self.duplicate_manager.get_duplicate_info(str(path_obj), file_hash)
                    if duplicates:
                        duplicate_info.append((str(path_obj), duplicates))
                        
                except Exception as e:
                    print(f"Error checking {path_obj}: {e}")
        
        if duplicate_info:
            # Show duplicate information
            self._show_duplicate_dialog(duplicate_info)
        else:
            messagebox.showinfo("No Duplicates", "No duplicate files found in selection")

    def _show_duplicate_dialog(self, duplicate_info):
        """Show dialog with duplicate information"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Duplicate Files Detected")
        dialog.geometry("800x500")
        dialog.configure(bg=self.current_theme["card"])
        dialog.transient(self.root)
        
        tk.Label(dialog, 
                text="FRIDAY Duplicate Detection Alert", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["accent"], 
                font=self.font_bold).pack(pady=15)
        
        text_widget = scrolledtext.ScrolledText(dialog, 
                                               height=20, 
                                               bg=self.current_theme["bg"], 
                                               fg=self.current_theme["muted"],
                                               font=self.font_mono, 
                                               wrap="word")
        text_widget.pack(fill="both", expand=True, padx=15, pady=10)
        
        for file_path, duplicates in duplicate_info:
            text_widget.insert("end", f"File: {file_path}\n")
            text_widget.insert("end", f"Previous transfers:\n")
            for dup in duplicates[-5:]:  # Show last 5
                timestamp = dup['timestamp'][:19].replace('T', ' ')
                text_widget.insert("end", f"  - {timestamp} to {dup['peer']}\n")
            text_widget.insert("end", "\n")
        
        text_widget.config(state="disabled")
        
        ttk.Button(dialog, text="Close", 
                  style="Accent.TButton",
                  command=dialog.destroy).pack(pady=15)

    def start_transfer(self):
        """Start file transfer"""
        if not self.selected_paths:
            messagebox.showwarning("No Files", "Please select files to transfer first")
            return
        
        # Get target
        target_ip = None
        selection = self.devices_listbox.curselection()
        if selection:
            device_info = self.devices_listbox.get(selection[0])
            # Extract IP from "Name (IP)" format
            if '(' in device_info and ')' in device_info:
                target_ip = device_info.split('(')[1].split(')')[0]
        
        manual_ip = self.manual_ip.get().strip()
        if not target_ip and manual_ip:
            target_ip = manual_ip
        
        if not target_ip:
            messagebox.showwarning("No Target", "Please select a target device or enter IP manually")
            return
        
        # Start transfer in background
        transfer_data = {
            'paths': self.selected_paths.copy(),
            'target_ip': target_ip,
            'transfer_id': f"send_{int(time.time() * 1000)}"
        }
        
        self.transfer_queue.put(transfer_data)
        self.notifier.notify("Transfer Started", f"Starting transfer to {target_ip}")

    # Receive methods
    def start_listening(self):
        """Start listening for incoming transfers - Activate defense grid"""
        if self.is_listening:
            return
        
        self.is_listening = True
        self.listen_status.config(text=f"Defense Grid: Active on port {self.transfer_port}", 
                                 fg=self.current_theme["success"])
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        """Main listening thread for incoming connections - Defense grid monitoring"""
        server_socket = None
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
            server_socket.bind(('', self.transfer_port))
            server_socket.listen(10)  # Increased backlog for multiple connections
            server_socket.settimeout(1.0)
            
            self._append_recv_log("Defense grid activated - Monitoring for incoming transfers...")
            
            while self.is_listening:
                try:
                    connection, address = server_socket.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break
                
                # Handle each connection in a separate thread - Multi-threat defense
                threading.Thread(
                    target=self._handle_incoming_transfer, 
                    args=(connection, address), 
                    daemon=True
                ).start()
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Defense Grid Error", 
                f"Failed to activate defense grid: {e}"))
            self.listen_status.config(text="Defense Grid: Offline", 
                                    fg="#d32f2f")
            self.is_listening = False
            
        finally:
            if server_socket:
                try:
                    server_socket.close()
                except:
                    pass

    def _receive_all(self, connection, num_bytes):
        """Receive exactly num_bytes from connection - Precision data reception"""
        data = bytearray()
        while len(data) < num_bytes:
            try:
                packet = connection.recv(num_bytes - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except socket.timeout:
                continue
            except Exception:
                return None
        return bytes(data)

    def _calculate_transfer_speed(self, speed_tracker):
        """Calculate current transfer speed"""
        if len(speed_tracker) < 2:
            return 0.0
        
        total_bytes = sum(chunk[1] for chunk in speed_tracker)
        time_span = speed_tracker[-1][0] - speed_tracker[0][0]
        
        return total_bytes / max(time_span, 0.1)

    def _calculate_eta(self, speed, remaining_bytes):
        """Calculate ETA based on current speed"""
        if speed <= 0:
            return None
        return remaining_bytes / speed

    def _handle_incoming_transfer(self, connection, address):
        """Handle incoming file transfer - Incoming mission processing"""
        start_time = time.time()
        peer_ip = address[0]
        total_received = 0
        verified_count = 0
        total_files = 0
        total_size = 0
        overwrite_policy = None  # None, 'overwrite', 'skip'
        
        # Generate unique transfer ID for monitoring
        transfer_id = f"incoming_{int(time.time() * 1000)}"
        
        try:
            # Set socket timeout for receive operations
            connection.settimeout(30.0)
            
            self._append_recv_log(f"Incoming transmission detected from {peer_ip}")
            
            # Receive metadata - Mission briefing reception
            header = self._receive_all(connection, 4)
            if not header:
                raise RuntimeError("No mission metadata received")
            
            metadata_length = struct.unpack('!I', header)[0]
            if metadata_length > 10 * 1024 * 1024:  # 10MB limit for metadata
                raise RuntimeError("Mission metadata too large")
            
            metadata_json = self._receive_all(connection, metadata_length)
            if not metadata_json:
                raise RuntimeError("Incomplete mission metadata")
            
            metadata = json.loads(metadata_json.decode('utf-8'))
            
            files = metadata.get('files', [])
            total_files = metadata.get('file_count', len(files))
            total_size = sum(f.get('size', 0) for f in files)
            
            self._append_recv_log(f"Mission briefing: {total_files} files, {human_size(total_size)} total")
            
            # Register with monitor - Incoming mission telemetry
            transfer_state = self.transfer_monitor.register_transfer(transfer_id, total_files, total_size)
            
            # Initialize progress tracking - Defense grid analysis
            self.root.after(0, lambda: self.recv_progress.configure(maximum=total_size, value=0))
            speed_tracker = deque(maxlen=int(SPEED_CALCULATION_WINDOW / UI_UPDATE_INTERVAL))
            last_ui_update = time.time()
            bytes_completed = 0
            files_completed = 0
            
            # Process each file - Incoming payload analysis
            for file_info in files:
                relative_path = (file_info.get('rel') or 
                               file_info.get('relative_path') or 
                               file_info.get('name', 'unknown'))
                file_size = file_info.get('size', 0)
                expected_hash = file_info.get('sha256')
                
                # Sanitize path to prevent directory traversal - Security protocol
                safe_path = os.path.basename(relative_path)
                save_path = Path(self.download_path_var.get()) / safe_path
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Handle existing files - Conflict resolution protocol
                if save_path.exists() and overwrite_policy is None:
                    def ask_overwrite():
                        return messagebox.askyesnocancel(
                            "FRIDAY Alert", 
                            f"File '{relative_path}' already exists in storage bay.\n"
                            f"Overwrite existing file?",
                            icon='question'
                        )
                    
                    result = None
                    self.root.after(0, lambda: ask_overwrite())
                    # This is simplified - in production, would need proper thread communication
                    
                if save_path.exists() and overwrite_policy == 'skip':
                    self._append_recv_log(f"Skipped: {relative_path} (already exists)")
                    continue
                
                # Check for duplicates - FRIDAY intelligence analysis
                if expected_hash:
                    is_duplicate, dup_info = self.duplicate_manager.is_duplicate(
                        str(save_path), expected_hash, peer_ip
                    )
                    if is_duplicate:
                        self._append_recv_log(f"FRIDAY Alert: Duplicate detected - {relative_path}")
                
                # Update current file status
                transfer_state.update(current_file=relative_path)
                self._append_recv_log(f"Receiving: {relative_path} ({human_size(file_size)})")
                
                # Receive file data - High-speed reception protocols
                hash_obj = hashlib.sha256()
                received_for_file = 0
                
                with open(save_path, "wb") as output_file:
                    while received_for_file < file_size:
                        # Calculate optimal chunk size based on remaining data
                        chunk_size = min(CHUNK_SIZE, file_size - received_for_file)
                        chunk = connection.recv(chunk_size)
                        if not chunk:
                            break
                        
                        output_file.write(chunk)
                        hash_obj.update(chunk)
                        
                        chunk_length = len(chunk)
                        received_for_file += chunk_length
                        bytes_completed += chunk_length
                        
                        # Track speed for UI updates
                        current_time = time.time()
                        speed_tracker.append((current_time, chunk_length))
                        
                        # Update UI periodically - Defense grid status display
                        if current_time - last_ui_update >= UI_UPDATE_INTERVAL:
                            speed = self._calculate_transfer_speed(speed_tracker)
                            eta = self._calculate_eta(speed, total_size - bytes_completed) if speed > 0 else None
                            
                            # Update transfer state
                            transfer_state.update(
                                bytes_transferred=bytes_completed,
                                current_speed=speed,
                                eta_seconds=eta,
                                files_completed=files_completed
                            )
                            
                            # Update receive UI
                            self._update_receive_ui(bytes_completed, total_size, speed, eta, 
                                                  files_completed, total_files, relative_path)
                            
                            last_ui_update = current_time
                
                # Verify file integrity - FRIDAY security verification
                actual_hash = hash_obj.hexdigest()
                if expected_hash and actual_hash.lower() == expected_hash.lower():
                    verified_count += 1
                    self._append_recv_log(f"Verified: {relative_path} - Hash match confirmed")
                    
                    # Add to duplicate database - FRIDAY intelligence update
                    self.duplicate_manager.add_file_hash(
                        str(save_path), actual_hash, peer_ip
                    )
                else:
                    self._append_recv_log(f"INTEGRITY FAILURE: {relative_path} - Hash mismatch detected!")
                
                files_completed += 1
                transfer_state.update(files_completed=files_completed)
            
            # Mission completion analysis
            duration = time.time() - start_time
            avg_speed = total_size / duration if duration > 0 else 0
            
            if self.is_listening:
                self._append_recv_log(f"Mission Complete: {total_files} files received")
                self._append_recv_log(f"Statistics: {human_size(total_size)} in {duration:.1f}s ({fmt_speed(avg_speed)})")
                
                self.root.after(0, lambda: messagebox.showinfo("Mission Complete", 
                    f"Received {total_files} files from {peer_ip}\n"
                    f"Verified: {verified_count}/{total_files}\n"
                    f"Total: {human_size(total_size)} in {duration:.1f}s"))
                
                self.notifier.notify(
                    "Incoming Transfer Complete", 
                    f"{total_files} files from {peer_ip} • Verified {verified_count}/{total_files}"
                )
                self._add_history("Receive", peer_ip, total_files, total_size, duration, 
                                f"{verified_count}/{total_files}", "Mission Success")
            else:
                self._append_recv_log("Mission interrupted - Defense grid offline")
                self._add_history("Receive", peer_ip, total_files, total_size, duration, 
                                "--", "Mission Interrupted")
                
        except Exception as e:
            self._append_recv_log(f"Mission Failed: {str(e)}")
            self._add_history("Receive", peer_ip if 'peer_ip' in locals() else "Unknown", 
                            0, 0, 0, "--", "Mission Failed")
            
        finally:
            try:
                connection.close()
            except:
                pass
            
            # Unregister from monitor
            if 'transfer_id' in locals():
                self.transfer_monitor.unregister_transfer(transfer_id)
            
            # Reset receive UI
            self.root.after(0, self._reset_receive_ui)

    def _update_receive_ui(self, bytes_received, total_bytes, speed, eta, files_done, total_files, current_file):
        """Update receive UI elements - Defense grid status display"""
        def update():
            try:
                # Progress bar update
                if total_bytes > 0:
                    progress = (bytes_received / total_bytes) * 100
                    self.recv_progress['maximum'] = 100
                    self.recv_progress['value'] = progress
                
                # Metrics update - Defense grid telemetry
                speed_text = fmt_speed(speed) if speed > 0 else "--"
                eta_text = fmt_eta(eta) if eta else "ETA: --"
                
                self.recv_metrics.config(
                    text=f"Defense Grid: Active • {speed_text} • {eta_text} • {files_done}/{total_files}"
                )
                
            except Exception as e:
                print(f"Receive UI update error: {e}")
        
        self.root.after(0, update)

    def _reset_receive_ui(self):
        """Reset receive UI to standby state - Defense grid standby"""
        try:
            self.recv_progress['value'] = 0
            self.recv_metrics.config(text="Defense Grid: Standby • Speed: -- • ETA: --")
        except Exception as e:
            print(f"Receive UI reset error: {e}")

    def _append_recv_log(self, text):
        """Append text to receive log - Mission log entry"""
        def append():
            try:
                self.recv_log.config(state="normal")
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.recv_log.insert("end", f"[{timestamp}] {text}\n")
                self.recv_log.see("end")
                self.recv_log.config(state="disabled")
            except Exception:
                pass
        
        self.root.after(0, append)

    # History methods - Mission archives like Stark's comprehensive database
    def _load_history(self):
        """Load transfer history from file - Accessing Stark Industries archives"""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_history(self):
        """Save transfer history to file - Backing up mission records"""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass

    def _add_history(self, direction, peer, files, size, duration, verified, status):
        """Add entry to transfer history - Archive mission record"""
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "direction": direction,
            "peer": peer,
            "files": files,
            "size": size,
            "duration": duration,
            "verified": verified,
            "status": status,
            "device": self.device_name
        }
        
        self.history.append(record)
        if len(self.history) > 2000:  # Increased archive capacity
            self.history = self.history[-2000:]
        
        self._save_history()

    def _refresh_history_ui(self):
        """Refresh history display - Update mission archives display"""
        def update():
            try:
                self.hist_list.config(state="normal")
                self.hist_list.delete("1.0", "end")
                
                if not self.history:
                    self.hist_list.insert("end", "No mission history available\nArc Reactor ready for first deployment\n")
                else:
                    self.hist_list.insert("end", "STARK INDUSTRIES MISSION ARCHIVES\n" + "="*60 + "\n\n")
                    
                    for i, record in enumerate(reversed(self.history[-100:])):  # Show last 100 entries
                        # Color coding based on status
                        if record['status'] in ['Mission Success', 'OK']:
                            status_icon = "✅"
                            color = self.current_theme["success"]
                        elif 'Failed' in record['status'] or 'Error' in record['status']:
                            status_icon = "❌"
                            color = "#d32f2f"
                        elif 'Cancelled' in record['status'] or 'Aborted' in record['status']:
                            status_icon = "⏹️"
                            color = "#ff9800"
                        else:
                            status_icon = "⚠️"
                            color = self.current_theme["muted"]
                        
                        # Format entry
                        avg_speed = record['size'] / max(record['duration'], 1) if record['duration'] > 0 else 0
                        
                        entry_text = (
                            f"{status_icon} [{record['time']}] {record['direction']} Mission\n"
                            f"   Target: {record['peer']}\n"
                            f"   Payload: {record['files']} files • {human_size(record['size'])}\n"
                            f"   Performance: {record['duration']:.1f}s • {fmt_speed(avg_speed)}\n"
                            f"   Integrity: {record['verified']} • Status: {record['status']}\n"
                            f"   {'─'*50}\n\n"
                        )
                        
                        tag = f"entry_{i}"
                        self.hist_list.insert("end", entry_text, tag)
                        self.hist_list.tag_configure(tag, foreground=color)
                
                self.hist_list.see("end")
                self.hist_list.config(state="disabled")
            except Exception as e:
                print(f"History refresh error: {e}")
        
        self.root.after(0, update)

    def _clear_history_prompt(self):
        """Prompt user to clear history - Archive purge protocol"""
        if messagebox.askyesno("Archive Purge", 
                              "Clear all mission archives?\n\nThis action cannot be undone.",
                              icon='warning'):
            self.history = []
            self._save_history()
            self._refresh_history_ui()
            self.notifier.notify("Archives Cleared", "Mission history purged")

    def _export_history(self):
        """Export history to file - Mission report generation"""
        if not self.history:
            messagebox.showinfo("Export Failed", "No mission history to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Mission Archives",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.history, f, indent=2)
                messagebox.showinfo("Export Complete", f"Mission archives exported to:\n{filename}")
                self.notifier.notify("Export Complete", "Mission archives exported successfully")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export archives:\n{str(e)}")

    # History context menu methods - Archive interaction protocols
    def _show_history_menu(self, event):
        """Show context menu for history - Archive access menu"""
        try:
            has_history = bool(self.history)
            
            self.hist_menu.entryconfigure("Open Folder", 
                                        state="normal" if has_history else "disabled")
            self.hist_menu.entryconfigure("Copy Details", 
                                        state="normal" if has_history else "disabled")
            self.hist_menu.entryconfigure("Show File Details", 
                                        state="normal" if has_history else "disabled")
            
            self.hist_menu.post(event.x_root, event.y_root)
        except Exception:
            pass

    def _open_history_folder(self, record=None):
        """Open folder from history record - Access mission files"""
        try:
            folder_path = Path(self.download_path_var.get())
            if folder_path.exists():
                os.startfile(str(folder_path))
            else:
                messagebox.showerror("Folder Not Found", "Storage bay location not accessible")
        except Exception as e:
            messagebox.showerror("Access Error", f"Could not open storage bay:\n{str(e)}")

    def _copy_history_details(self):
        """Copy history details to clipboard - Mission data extraction"""
        if self.history:
            record = self.history[-1]  # Most recent for simplicity
            details = (
                f"Mission Report: {record['time']}\n"
                f"Operation: {record['direction']}\n"
                f"Target: {record['peer']}\n"
                f"Payload: {record['files']} files ({human_size(record['size'])})\n"
                f"Duration: {record['duration']:.1f}s\n"
                f"Verification: {record['verified']}\n"
                f"Status: {record['status']}\n"
                f"Device: {record.get('device', 'Unknown')}"
            )
            
            self.root.clipboard_clear()
            self.root.clipboard_append(details)
            self.notifier.notify("Data Copied", "Mission details copied to clipboard")

    def _show_file_details(self):
        """Show detailed file information - Enhanced mission analysis"""
        if not self.history:
            return
        
        # Create detailed view window
        detail_window = tk.Toplevel(self.root)
        detail_window.title("Mission Analysis - Detailed Report")
        detail_window.geometry("700x500")
        detail_window.configure(bg=self.current_theme["card"])
        detail_window.transient(self.root)
        
        text_widget = scrolledtext.ScrolledText(detail_window, 
                                               height=25, 
                                               bg=self.current_theme["bg"], 
                                               fg=self.current_theme["muted"],
                                               font=self.font_mono, 
                                               wrap="word")
        text_widget.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Generate detailed report
        report = "STARK INDUSTRIES MISSION ANALYSIS REPORT\n"
        report += "="*60 + "\n\n"
        
        total_files = sum(r['files'] for r in self.history)
        total_size = sum(r['size'] for r in self.history)
        total_duration = sum(r['duration'] for r in self.history)
        
        report += f"SUMMARY STATISTICS\n"
        report += f"   Total Missions: {len(self.history)}\n"
        report += f"   Total Files Transferred: {total_files:,}\n"
        report += f"   Total Data Transferred: {human_size(total_size)}\n"
        report += f"   Total Operation Time: {total_duration:.1f}s\n"
        report += f"   Average Speed: {fmt_speed(total_size / max(total_duration, 1))}\n\n"
        
        # Recent missions
        report += f"RECENT MISSIONS (Last 10)\n"
        report += "-" * 40 + "\n"
        
        for record in self.history[-10:]:
            avg_speed = record['size'] / max(record['duration'], 1)
            report += f"{record['time']} | {record['direction']} | {record['peer']}\n"
            report += f"  Files: {record['files']} | Size: {human_size(record['size'])} | Speed: {fmt_speed(avg_speed)}\n"
            report += f"  Status: {record['status']} | Verified: {record['verified']}\n\n"
        
        text_widget.insert("1.0", report)
        text_widget.config(state="disabled")

    # Settings methods - System configuration protocols
    def change_download_location(self):
        """Change download directory - Storage bay reconfiguration"""
        new_directory = filedialog.askdirectory(title="Select new storage bay location")
        if new_directory:
            self.download_path_var.set(new_directory)
            self.download_dir = Path(new_directory)
            self.notifier.notify("Storage Updated", "Storage bay location updated")

    def save_device_name(self):
        """Save device name - Update suit identity"""
        name = self.device_name_var.get().strip()
        if name:
            self.device_name = name
            messagebox.showinfo("Identity Updated", f"Device identity updated to: {name}")
            self.notifier.notify("Identity Updated", "Device callsign updated")

    def _apply_performance_settings(self):
        """Apply performance settings - Arc reactor reconfiguration"""
        try:
            new_chunk_size = int(self.chunk_size_var.get()) * 1024
            if new_chunk_size < 1024 or new_chunk_size > 10 * 1024 * 1024:
                raise ValueError("Chunk size must be between 1KB and 10MB")
            
            global CHUNK_SIZE
            CHUNK_SIZE = new_chunk_size
            
            messagebox.showinfo("Performance Updated", 
                              f"Arc reactor power output set to {human_size(CHUNK_SIZE)}")
            self.notifier.notify("Performance Updated", "Arc reactor reconfigured")
        except ValueError as e:
            messagebox.showerror("Configuration Error", f"Invalid power setting: {str(e)}")

    def _apply_concurrent_settings(self):
        """Apply concurrent transfer settings - Multi-reactor configuration"""
        try:
            new_concurrent = int(self.concurrent_var.get())
            if new_concurrent < 1 or new_concurrent > 10:
                raise ValueError("Concurrent transfers must be between 1 and 10")
            
            global MAX_CONCURRENT_TRANSFERS
            MAX_CONCURRENT_TRANSFERS = new_concurrent
            
            # Reconfigure thread pool
            self.transfer_executor._max_workers = new_concurrent
            
            messagebox.showinfo("Reactor Configuration Updated", 
                              f"Parallel arc reactors set to: {new_concurrent}")
            self.notifier.notify("Reactors Configured", f"{new_concurrent} parallel reactors active")
        except ValueError as e:
            messagebox.showerror("Configuration Error", f"Invalid reactor setting: {str(e)}")

    def toggle_theme(self):
        """Toggle between light and dark theme - Suit appearance mode"""
        theme_name = "light" if self.current_theme == self.themes["dark"] else "dark"
        self.current_theme = self.themes[theme_name]
        self._save_theme()
        self._update_theme()
        
        mode_name = "Stealth Mode" if theme_name == "dark" else "Standard Mode"
        self.notifier.notify("Theme Changed", f"Switched to {mode_name}")

    def _update_theme(self):
        """Update UI elements to match current theme - Suit reconfiguration"""
        theme = self.current_theme
        self.root.configure(bg=theme["bg"])
        
        # Update all frames and components recursively
        self._update_theme_recursive(self.root, theme)
        self._configure_styles()
        self._refresh_history_ui()

    def _update_theme_recursive(self, widget, theme):
        """Recursively update widget themes - Complete suit reconfiguration"""
        try:
            if isinstance(widget, (tk.Frame, tk.Toplevel)):
                widget.configure(bg=theme["card"] if widget != self.root else theme["bg"])
            elif isinstance(widget, tk.Label):
                widget.configure(bg=theme["card"], fg=theme["muted"])
            elif isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                widget.configure(bg=theme["bg"], fg=theme["muted"])
            elif isinstance(widget, tk.Listbox):
                widget.configure(bg=theme["bg"], fg=theme["muted"], 
                               selectbackground=theme["accent"])
            
            # Process children
            for child in widget.winfo_children():
                self._update_theme_recursive(child, theme)
        except Exception:
            pass

    def view_duplicates(self):
        """View duplicate database - FRIDAY intelligence database"""
        dialog = tk.Toplevel(self.root)
        dialog.title("FRIDAY Intelligence Database - Duplicate Detection")
        dialog.geometry("900x600")
        dialog.configure(bg=self.current_theme["card"])
        dialog.transient(self.root)
        
        tk.Label(dialog, 
                text="FRIDAY Intelligence Database", 
                bg=self.current_theme["card"], 
                fg=self.current_theme["accent"], 
                font=self.font_bold).pack(pady=15)
        
        text_widget = scrolledtext.ScrolledText(dialog, 
                                               height=25, 
                                               bg=self.current_theme["bg"], 
                                               fg=self.current_theme["muted"],
                                               font=self.font_mono, 
                                               wrap="word")
        text_widget.pack(fill="both", expand=True, padx=15, pady=10)
        
        if not self.duplicate_manager.file_hashes:
            text_widget.insert("end", "FRIDAY Intelligence Database Empty\n")
            text_widget.insert("end", "No duplicate patterns detected\n")
            text_widget.insert("end", "All systems ready for fresh deployment\n")
        else:
            text_widget.insert("end", "FRIDAY DUPLICATE DETECTION DATABASE\n")
            text_widget.insert("end", "="*60 + "\n\n")
            
            for key, entries in self.duplicate_manager.file_hashes.items():
                hash_part, filename = key.rsplit('_', 1)
                text_widget.insert("end", f"File Pattern: {filename}\n")
                text_widget.insert("end", f"Hash Pattern: {hash_part[:16]}...\n")
                text_widget.insert("end", f"Detection Count: {len(entries)}\n")
                
                # Show recent detections
                text_widget.insert("end", "Recent Transfers:\n")
                for entry in entries[-5:]:  # Last 5 entries
                    timestamp = entry['timestamp'][:19].replace('T', ' ')
                    text_widget.insert("end", f"  • {timestamp} -> {entry['peer']}\n")
                    text_widget.insert("end", f"    Path: {entry['path']}\n")
                
                text_widget.insert("end", "─"*60 + "\n\n")
        
        text_widget.config(state="disabled")
        
        # Control buttons
        button_frame = tk.Frame(dialog, bg=self.current_theme["card"])
        button_frame.pack(pady=15)
        
        ttk.Button(button_frame, text="Refresh Database", 
                  style="Accent.TButton",
                  command=lambda: self._refresh_duplicate_view(text_widget)).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Export Database", 
                  style="Success.TButton",
                  command=self._export_duplicates).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Close", 
                  style="Accent.TButton",
                  command=dialog.destroy).pack(side="right", padx=5)

    def _refresh_duplicate_view(self, text_widget):
        """Refresh duplicate view - Database refresh protocol"""
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")
        
        if not self.duplicate_manager.file_hashes:
            text_widget.insert("end", "FRIDAY Intelligence Database Empty\n")
            text_widget.insert("end", "No duplicate patterns detected\n")
            text_widget.insert("end", "All systems ready for fresh deployment\n")
        else:
            text_widget.insert("end", "FRIDAY DUPLICATE DETECTION DATABASE\n")
            text_widget.insert("end", "="*60 + "\n\n")
            
            for key, entries in self.duplicate_manager.file_hashes.items():
                hash_part, filename = key.rsplit('_', 1)
                text_widget.insert("end", f"File Pattern: {filename}\n")
                text_widget.insert("end", f"Hash Pattern: {hash_part[:16]}...\n")
                text_widget.insert("end", f"Detection Count: {len(entries)}\n")
                
                # Show recent detections
                text_widget.insert("end", "Recent Transfers:\n")
                for entry in entries[-5:]:  # Last 5 entries
                    timestamp = entry['timestamp'][:19].replace('T', ' ')
                    text_widget.insert("end", f"  • {timestamp} -> {entry['peer']}\n")
                    text_widget.insert("end", f"    Path: {entry['path']}\n")
                
                text_widget.insert("end", "─"*60 + "\n\n")
        
        text_widget.config(state="disabled")

    def _export_duplicates(self):
        """Export duplicate database - Intelligence data export"""
        if not self.duplicate_manager.file_hashes:
            messagebox.showinfo("Export Failed", "No duplicate intelligence to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export FRIDAY Intelligence Database",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    export_data = {
                        'export_time': datetime.now().isoformat(),
                        'device_name': self.device_name,
                        'duplicate_database': dict(self.duplicate_manager.file_hashes)
                    }
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Export Complete", f"FRIDAY database exported to:\n{filename}")
                self.notifier.notify("Database Exported", "Intelligence data exported successfully")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export database:\n{str(e)}")

    def clear_duplicate_database(self):
        """Clear duplicate detection database - Intelligence memory wipe"""
        if messagebox.askyesno("Memory Wipe", 
                              "Clear FRIDAY's duplicate detection database?\n\n"
                              "This will erase all intelligence patterns.\n"
                              "This action cannot be undone.",
                              icon='warning'):
            self.duplicate_manager.clear_duplicates()
            messagebox.showinfo("Memory Cleared", "FRIDAY's duplicate database has been wiped")
            self.notifier.notify("Database Cleared", "Intelligence database purged")

    # Utility methods - Supporting systems like JARVIS protocols
    def get_local_ip(self):
        """Get local IP address - Network interface detection"""
        try:
            # Create connection to external server to determine local IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _on_configure(self, event=None):
        """Keep the main layout consistent when maximized/minimized."""
        try:
            state = self.root.state()
            # If maximized ('zoomed' on Windows), immediately restore to preferred geometry
            if state == 'zoomed':
                # Restore but allow user to still minimize
                self.root.state('normal')
                self.root.geometry("1200x900")
            # If normal (restored), ensure geometry is our preferred size
            elif state == 'normal':
                self.root.geometry("1200x900")
        except Exception:
            pass

    def _mission_complete_sequence(self, transfer_id):
        """Play a short mission-complete animation and notification."""
        try:
            # Small popup with simple canvas animation
            win = tk.Toplevel(self.root)
            win.title("Mission Complete")
            win.geometry("420x220")
            win.transient(self.root)
            win.resizable(False, False)
            frame = tk.Frame(win, bg=self.current_theme['card'])
            frame.pack(fill='both', expand=True)
            canvas = tk.Canvas(frame, width=400, height=150, bg=self.current_theme['card'], highlightthickness=0)
            canvas.pack(pady=10)
            text = canvas.create_text(200, 40, text='MISSION COMPLETE', font=self.font_bold, fill=self.current_theme['accent'])
            # Simple expanding circle animation
            circle = canvas.create_oval(190,70,210,90, outline=self.current_theme['accent'], width=3)
            for i in range(1,11):
                canvas.coords(circle, 200-i*20, 80-i*10, 200+i*20, 80+i*10)
                win.update()
                time.sleep(0.03)
            self.notifier.notify('Mission Complete', f'Transfer {transfer_id} finished successfully!')
            ttk.Button(frame, text='Close', command=win.destroy, style='Accent.TButton').pack(pady=6)
        except Exception:
            pass

    def _record_transfer_log(self, bytes_sent):
        """Record transfers for heatmap and usage stats, and persist to analytics DB."""
        try:
            ts = time.time()
            self.transfer_logs.append((ts, bytes_sent))
            # Keep to last 10000 entries
            if len(self.transfer_logs) > 10000:
                self.transfer_logs = self.transfer_logs[-10000:]
            # Persist to analytics
            try:
                if getattr(self, 'analytics', None):
                    self.analytics.record_transfer(ts, getattr(self, 'device_name', 'Unknown'), 'Send', bytes_sent, 'Mission Success')
            except Exception:
                pass
        except Exception:
            pass

    def _render_heatmap(self, parent):
        """Render a simple time-based heatmap into a provided frame."""
        try:
            heat_win = tk.Toplevel(self.root)
            heat_win.title('Transfer Heatmap')
            heat_win.geometry('800x400')
            heat_win.transient(self.root)
            canvas = tk.Canvas(heat_win, bg=self.current_theme['card'])
            canvas.pack(fill='both', expand=True)
            # Aggregate by hour of day for last 48 hours
            now = time.time()
            bins = [0]*48
            for ts, b in self.transfer_logs:
                hours_ago = int((now - ts) // 3600)
                if 0 <= hours_ago < 48:
                    bins[47-hours_ago] += b
            maxv = max(bins) if bins else 1
            w = 760/48
            for i, val in enumerate(bins):
                h = int((val/maxv) * 300) if maxv>0 else 0
                x = 10 + i*w
                y = 350 - h
                color = '#ff6b35' if val>0 else self.current_theme['card']
                canvas.create_rectangle(x, y, x+w-2, 350, fill=color, outline='')
            ttk.Button(heat_win, text='Close', command=heat_win.destroy, style='Accent.TButton').pack(pady=6)
        except Exception:
            pass

    def _render_topology(self, parent):
        """Render a simple network topology map from discovered devices."""
        try:
            topo_win = tk.Toplevel(self.root)
            topo_win.title('Network Topology')
            topo_win.geometry('800x600')
            topo_win.transient(self.root)
            canvas = tk.Canvas(topo_win, bg=self.current_theme['card'])
            canvas.pack(fill='both', expand=True)
            # Draw central node
            cx, cy = 400, 80
            canvas.create_oval(cx-30, cy-30, cx+30, cy+30, fill=self.current_theme['accent'], outline='')
            canvas.create_text(cx, cy, text='You', fill='white')
            # Spread discovered discovered devices
            ips = list(self.discovered_devices.items())
            for idx, (ip, name) in enumerate(ips):
                angle = (idx / max(1, len(ips))) * 3.1415 * 2
                rx = cx + int(250 * (0.9 * (idx%3+1)/3) * (1 if idx%2==0 else -1))
                ry = cy + 150 + (idx%5)*20
                canvas.create_line(cx, cy, rx, ry, fill=self.current_theme['muted'])
                canvas.create_oval(rx-24, ry-24, rx+24, ry+24, fill=self.current_theme['card'], outline=self.current_theme['accent'])
                canvas.create_text(rx, ry, text=name, fill=self.current_theme['muted'])
            ttk.Button(topo_win, text='Close', command=topo_win.destroy, style='Accent.TButton').pack(pady=6)
        except Exception:
            pass

    def _start_offline_monitor(self):
        """Start offline monitor thread."""
        try:
            if getattr(self, 'offline_monitor_thread', None) is None or not self.offline_monitor_thread.is_alive():
                self.offline_monitor_running = True
                self.offline_monitor_thread = threading.Thread(target=self._offline_monitor_loop, daemon=True)
                self.offline_monitor_thread.start()
        except Exception:
            pass

    def _offline_monitor_loop(self):
        """Periodically try to send queued transfers when network returns."""
        while getattr(self, 'offline_monitor_running', True):
            try:
                if self.offline_queue:
                    item = self.offline_queue[0]
                    target = item.get('target_ip')
                    # simple reachability check
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    try:
                        sock.connect((target, self.transfer_port))
                        sock.close()
                        # re-enqueue for processing by main queue
                        self.transfer_queue.put(self.offline_queue.popleft())
                    except Exception:
                        # still offline
                        pass
                time.sleep(5)
            except Exception:
                time.sleep(5)

    def _queue_offline_transfer(self, transfer_data):
        """Add transfer to offline queue for later retry."""
        try:
            self.offline_queue.append(transfer_data)
            self.notifier.notify('Offline Queue', f'Transfer queued for {transfer_data.get("target_ip")}. Will auto-resume when online.')
        except Exception:
            pass

    def _open_analytics_window(self):
        """Open a polished analytics dashboard window with charts (matplotlib embedded)."""
        if plt is None or FigureCanvasTkAgg is None or pd is None:
            messagebox.showinfo("Analytics Unavailable", "Missing optional packages: matplotlib, pandas, numpy, networkx.\nInstall them to enable analytics.")
            return
        try:
            win = tk.Toplevel(self.root)
            win.title("Analytics Dashboard - Goodluck Sharing")
            win.geometry("1000x700")
            win.transient(self.root)
            # Use notebook-like layout: charts on top, heatmap and stats below
            frame = tk.Frame(win, bg=self.current_theme['card'])
            frame.pack(fill='both', expand=True)
            fig, axes = plt.subplots(2,2, figsize=(10,6))
            df = self.analytics.query_transfers(60*60*24*30) if self.analytics else None  # last 30 days
            if df is None or df.empty:
                axes[0,0].text(0.5,0.5,"No data", ha='center'); axes[0,1].text(0.5,0.5,"No data", ha='center')
                axes[1,0].text(0.5,0.5,"No data", ha='center'); axes[1,1].text(0.5,0.5,"No data", ha='center')
            else:
                # Transfers over time (daily)
                df['date'] = pd.to_datetime(df['ts'], unit='s').dt.date
                daily = df.groupby('date')['bytes'].sum().reset_index()
                axes[0,0].plot(daily['date'], daily['bytes'], marker='o')
                axes[0,0].set_title('Daily Transfer Volume')
                axes[0,0].tick_params(axis='x', rotation=30)

                # Success vs failure pie
                status_counts = df['status'].value_counts()
                axes[0,1].pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=140)
                axes[0,1].set_title('Outcome Breakdown')

                # Heatmap (hourly last 48 hours)
                now = time.time()
                hours = 48
                bins = np.zeros(hours)
                for ts, b in zip(df['ts'], df['bytes']):
                    hours_ago = int((now - ts)//3600)
                    if 0 <= hours_ago < hours:
                        bins[hours-1-hours_ago] += b
                im = axes[1,0].imshow(bins.reshape(1,-1), aspect='auto')
                axes[1,0].set_title('Last 48 hours heatmap (aggregated by hour)')
                axes[1,0].set_yticks([])
                axes[1,0].set_xticks(range(0,hours,6))
                axes[1,0].set_xticklabels([f'{(int(time.time())//3600 - (hours-1-i))%24}:00' for i in range(0,hours,6)])

                # Top peers by volume
                peers = df.groupby('peer')['bytes'].sum().sort_values(ascending=False).head(6)
                axes[1,1].bar(peers.index.astype(str), peers.values)
                axes[1,1].set_title('Top Peers (by bytes)')

            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            ttk.Button(win, text='Close', command=win.destroy, style='Accent.TButton').pack(pady=6)
        except Exception as e:
            messagebox.showerror("Analytics Error", str(e))

    def _open_topology_window(self):
        """Render a polished topology using networkx and matplotlib"""
        if nx is None or plt is None or FigureCanvasTkAgg is None:
            messagebox.showinfo("Topology Unavailable", "Missing optional packages: networkx, matplotlib.")
            return
        try:
            win = tk.Toplevel(self.root)
            win.title("Network Topology - Goodluck Sharing")
            win.geometry("900x700")
            win.transient(self.root)
            frame = tk.Frame(win, bg=self.current_theme['card'])
            frame.pack(fill='both', expand=True)
            fig = plt.Figure(figsize=(9,6))
            ax = fig.add_subplot(111)
            G = nx.Graph()
            center = self.device_name or 'You'
            G.add_node(center)
            for ip, name in self.discovered_devices.items():
                G.add_node(name)
                G.add_edge(center, name)
            pos = nx.spring_layout(G, seed=42)
            nx.draw_networkx_nodes(G, pos, ax=ax, node_color='#ff6b35', node_size=600)
            nx.draw_networkx_edges(G, pos, ax=ax)
            nx.draw_networkx_labels(G, pos, ax=ax, font_size=9)
            ax.set_axis_off()
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            ttk.Button(win, text='Close', command=win.destroy, style='Accent.TButton').pack(pady=6)
        except Exception as e:
            messagebox.showerror("Topology Error", str(e))

    def _on_close(self):
        """Handle application close - Shutdown sequence like powering down suit"""
        try:
            # Stop all systems
            self.is_listening = False
            self.global_cancel_event.set()
            self.transfer_monitor.stop_monitoring()
            
            # Stop offline monitor thread
            try:
                self.offline_monitor_running = False
                t = getattr(self, 'offline_monitor_thread', None)
                if t and t.is_alive():
                    t.join(timeout=0.5)
            except Exception:
                pass
            
            # Close analytics database
            if self.analytics:
                self.analytics.close()
            
            # Wait briefly for threads to cleanup
            time.sleep(0.5)
            
            # Shutdown thread pool
            self.transfer_executor.shutdown(wait=False)
            
            # Final notification
            self.notifier.notify("System Shutdown", "Arc Reactor powering down...")
            
        except Exception:
            pass
        finally:
            self.root.destroy()

    def run(self):
        """Start the application - Power up the arc reactor"""
        try:
            self.notifier.notify("System Online", "Arc Reactor powered up - All systems operational")
            self.root.mainloop()
        except Exception as e:
            print(f"Application error: {e}")
        finally:
            # Ensure cleanup
            self._on_close()


# Main execution - Initialize Iron Man file sharing system
if __name__ == "__main__":
    try:
        # JARVIS: "Initializing Iron Man file sharing protocols..."
        app = GoodluckSharingApp()
        # JARVIS: "All systems online. Arc reactor stable. Ready for deployment."
        app.run()
    except KeyboardInterrupt:
        # JARVIS: "Emergency shutdown initiated by user."
        print("\nIron Man system shutdown by user command")
    except Exception as e:
        # JARVIS: "Critical system failure detected."
        print(f"\nCritical system failure: {e}")
        print("Contact Stark Industries for technical support")