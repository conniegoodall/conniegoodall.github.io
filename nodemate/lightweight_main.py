"""
Lightweight Main Window - Premium Dashboard
Integrates psutil watchdog, Telegram alerts, and live viewport with a sleek 4-panel UI.
"""

from __future__ import annotations

import sys
import logging
import threading
import json
import uuid
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QLineEdit, QMessageBox, QTabWidget, QFormLayout,
    QSpinBox, QDoubleSpinBox, QDialogButtonBox, QFileDialog,
    QFrame, QGridLayout, QScrollArea, QDialog, QStackedWidget
)
from PyQt6.QtCore import QTimer, pyqtSignal, Qt, QSize, QUrl
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette
from PyQt6.QtWebEngineWidgets import QWebEngineView
import base64
import socket

# Import lightweight components
from nodemate.lightweight_watchdog import LightweightWatchdog
from nodemate.telegram_bot import TelegramAlertBot
from nodemate.live_viewport import LiveViewportServer
from nodemate.config_store import NodeEntry, load_config, save_config, node_from_dict
from nodemate.discovery import scan_system_safe

logger = logging.getLogger(__name__)

class Styles:
    MAIN_BG = "#1a1c1e"
    PANEL_BG = "#24282d"
    ACCENT = "#3498db"
    SUCCESS = "#4CAF50"
    WARNING = "#ff9800"
    DANGER = "#f44336"
    TEXT = "#ffffff"
    TEXT_DIM = "#a0a0a0"
    BORDER = "#3a3f44"

    SHEET = f"""
    QMainWindow {{ background-color: {MAIN_BG}; color: {TEXT}; }}
    QWidget {{ color: {TEXT}; font-family: 'Segoe UI', sans-serif; }}
    
    /* Ensure MessageBox text is always visible regardless of system theme */
    QMessageBox {{
        background-color: {PANEL_BG};
    }}
    QMessageBox QLabel {{
        color: {TEXT};
        font-size: 14px;
    }}
    
    QFrame#Panel {{ 
        background-color: {PANEL_BG}; 
        border: 1px solid {BORDER}; 
        border-radius: 12px; 
    }}
    
    QLabel#Header {{ font-size: 16px; font-weight: bold; color: {ACCENT}; margin-bottom: 5px; }}
    QLabel#StatValue {{ font-size: 24px; font-weight: bold; color: {TEXT}; }}
    QLabel#StatLabel {{ font-size: 12px; color: {TEXT_DIM}; }}
    
    QPushButton {{ 
        background-color: {ACCENT}; 
        border: none; 
        border-radius: 6px; 
        padding: 8px 4px; 
        font-weight: bold; 
        min-height: 35px;
    }}
    QPushButton:hover {{ background-color: #2980b9; }}
    QPushButton#Secondary {{ background-color: #3a3f44; }}
    QPushButton#Secondary:hover {{ background-color: #4a4f54; }}
    QPushButton#Danger {{ background-color: {DANGER}; }}
    
    QLineEdit {{ 
        background-color: {MAIN_BG}; 
        border: 1px solid {BORDER}; 
        border-radius: 6px; 
        padding: 8px; 
        color: white; 
    }}
    
    QListWidget {{ 
        background-color: transparent; 
        border: none; 
    }}
    QListWidget::item {{ 
        background-color: {PANEL_BG}; 
        border-radius: 8px; 
        margin-bottom: 6px; 
        padding: 5px; 
    }}
    QListWidget::item:selected {{ 
        background-color: {ACCENT}; 
    }}
    QCheckBox {{ 
        color: {TEXT}; 
        spacing: 12px; 
        font-size: 14px; 
    }}
    QCheckBox::indicator {{ 
        width: 20px; 
        height: 20px; 
        border: 2px solid {BORDER}; 
        border-radius: 4px; 
    }}
    QCheckBox::indicator:checked {{ 
        background-color: #32CD32;
    }}
    """

class LightweightMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.watchdog = LightweightWatchdog(self)
        self._nodes: List[NodeEntry] = []
        
        # --- UDP Anti-Farm Limiter Setup ---
        self.instance_id = str(uuid.uuid4())[:8]
        self.startup_time = datetime.now().timestamp()
        self.active_lan_instances = {self.instance_id: {'last_seen': self.startup_time, 'startup': self.startup_time}}
        self.udp_port = 37020
        self.max_instances = 3
        self.ad_allowed = True
        
        self._start_udp_listener()
        self._start_udp_broadcaster()
        
        self._setup_ui()
        self._load_nodes()
        self._setup_connections()
        
        # Periodic UI update timer
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._update_stats)
        self.ui_timer.start(5000)
        
        # Drag and Drop support
        self.setAcceptDrops(True)

    # --- UDP Broadcast Methods ---
    def _start_udp_listener(self):
        """Listens for heartbeats from other Node-Mate instances on the LAN"""
        self.udp_socket_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        
        # Enable port reuse so multiple instances on the SAME machine can listen to the same port
        if sys.platform == 'win32':
            self.udp_socket_in.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        else:
            self.udp_socket_in.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            
        self.udp_socket_in.bind(('', self.udp_port))
        self.udp_socket_in.setblocking(False)
        
        self.listener_timer = QTimer()
        self.listener_timer.timeout.connect(self._poll_udp)
        self.listener_timer.start(1000)

    def _poll_udp(self):
        """Read all incoming UDP heartbeats non-blocking"""
        while True:
            try:
                data, _ = self.udp_socket_in.recvfrom(1024)
                msg = data.decode('utf-8')
                if msg.startswith("NODEMATE_HEARTBEAT:"):
                    parts = msg.split(":")
                    peer_id = parts[1]
                    try:
                        peer_startup = float(parts[2]) if len(parts) >= 3 else datetime.now().timestamp()
                    except ValueError:
                        peer_startup = datetime.now().timestamp()
                    
                    if peer_id in self.active_lan_instances and isinstance(self.active_lan_instances[peer_id], dict):
                        peer_startup = self.active_lan_instances[peer_id].get('startup', peer_startup)
                        
                    self.active_lan_instances[peer_id] = {
                        'last_seen': datetime.now().timestamp(),
                        'startup': peer_startup
                    }
            except BlockingIOError:
                break # No more data to read right now
            except ConnectionResetError:
                # Windows specific UDP error: previous sendto caused ICMP Port Unreachable.
                # Ignore and keep reading.
                continue
            except Exception as e:
                # Other socket errors, log and break
                if getattr(e, 'winerror', None) != 10035:
                    logger.error(f"UDP read error: {e}")
                break
                
        self._evaluate_farm_limit()

    def _start_udp_broadcaster(self):
        """Broadcasts this instance's existence to the LAN every 2 seconds"""
        self.udp_socket_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.udp_socket_out.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.broadcast_timer = QTimer()
        self.broadcast_timer.timeout.connect(self._send_heartbeat)
        self.broadcast_timer.start(2000)

    def _send_heartbeat(self):
        msg = f"NODEMATE_HEARTBEAT:{self.instance_id}:{self.startup_time}".encode('utf-8')
        try:
            self.udp_socket_out.sendto(msg, ('<broadcast>', self.udp_port))
        except Exception:
            pass # Ignore network unreachable errors

    def _evaluate_farm_limit(self):
        """Check if we are exceeding the 3 PC limit and disable ads if necessary"""
        now = datetime.now().timestamp()
        
        # Remove dead instances (no heartbeat in 6 seconds)
        active_peers = {}
        for pid, data in self.active_lan_instances.items():
            if isinstance(data, dict):
                if now - data['last_seen'] < 6:
                    active_peers[pid] = data
            else:
                # Fallback for old format
                if now - data < 6:
                    active_peers[pid] = {'last_seen': data, 'startup': now}
                    
        self.active_lan_instances = active_peers
        
        # Ensure our own instance ID is always in the active list
        if self.instance_id not in self.active_lan_instances:
            self.active_lan_instances[self.instance_id] = {
                'last_seen': now,
                'startup': self.startup_time
            }
            
        # Sort IDs by startup time (oldest first). Tie-breaker is the ID itself.
        sorted_ids = sorted(self.active_lan_instances.keys(), key=lambda pid: (self.active_lan_instances[pid]['startup'], pid))
        
        my_rank = sorted_ids.index(self.instance_id) + 1
        
        # If I am the 4th, 5th, etc... I get blocked.
        should_allow_ad = my_rank <= self.max_instances
        
        if should_allow_ad != self.ad_allowed:
            self.ad_allowed = should_allow_ad
            self._update_ad_banner_ui(my_rank, len(sorted_ids))

    def _update_ad_banner_ui(self, rank, total_active):
        """Dynamically update the footer text based on limit status"""
        if not hasattr(self, 'ad_text'):
            return # UI not built yet
            
        dev_key_path = Path(".dev_bypass.key")
        if dev_key_path.exists():
            # In Dev mode, we just update the text to show the limiter is working
            if self.ad_allowed:
                self.ad_text.setText(f"🚀 [DEV MODE: Ad Allowed (Instance {rank}/{total_active})] 🚀")
                self.ad_text.setStyleSheet(f"color: {Styles.SUCCESS}; font-weight: bold; font-size: 14px;")
            else:
                self.ad_text.setText(f"🛑 [DEV MODE: Ad Blocked by LAN Limit (Instance {rank}/{total_active})] 🛑")
                self.ad_text.setStyleSheet(f"color: {Styles.DANGER}; font-weight: bold; font-size: 14px;")
        else:
            # Production mode logic
            if not self.ad_allowed:
                # We exceeded limit. Hide the web view, show the blocked text.
                if hasattr(self, 'web_view'):
                    self.web_view.hide()
                # If we are blocked, we must show the ad_text placeholder so the UI doesn't collapse
                self.ad_text.setText(f"🛑 [Ads Paused: Anti-Farm LAN Limit Reached] 🛑")
                self.ad_text.show()
            else:
                # We are within limit. Show the web view, hide the text.
                self.ad_text.hide()
                if hasattr(self, 'web_view'):
                    self.web_view.show()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        added_count = 0
        from pathlib import Path
        for f in files:
            p = Path(f) # using p to avoid conflict
            if p.suffix.lower() == ".lnk":
                if self._add_from_shortcut(p):
                    added_count += 1
            elif p.suffix.lower() == ".exe":
                if self._add_from_exe(p):
                    added_count += 1
        
        if added_count > 0:
            self._save_nodes()
            self._refresh_node_lists()
            self._log_action(f"Dropped and added {added_count} new node(s)")
            if self.watchdog.is_active:
                self.watchdog.start_monitoring([n for n in self._nodes if n.enabled])
            
    def _add_from_shortcut(self, lnk_path: Path) -> bool:
        try:
            import win32com.client
            import shlex
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(lnk_path))
            target = shortcut.TargetPath
            args = shortcut.Arguments
            
            # 1. Detect Browser Type
            browser_type = "exe"
            target_lower = target.lower()
            if "chrome.exe" in target_lower: browser_type = "chrome"
            elif "msedge.exe" in target_lower: browser_type = "edge"
            elif "brave.exe" in target_lower: browser_type = "brave"
            elif "opera.exe" in target_lower or "launcher.exe" in target_lower: 
                browser_type = "opera"
                # Improvement: Prefer launcher.exe in the parent folder if possible
                if "opera.exe" in target_lower:
                    try:
                        parent_launcher = Path(target).parent.parent / "launcher.exe"
                        if parent_launcher.exists():
                            target = str(parent_launcher)
                    except: pass
            elif "vivaldi.exe" in target_lower: browser_type = "vivaldi"
            elif "datagram" in target_lower: browser_type = "chrome"
            elif "titan" in target_lower: browser_type = "chrome"
            elif "solana" in target_lower: browser_type = "chrome"
            
            # 2. Extract Profile and User Data Dir
            profile = "Default"
            user_data = None
            
            parts = shlex.split(args) if args else []
            for part in parts:
                if "--profile-directory=" in part:
                    profile = part.split("=")[1].strip('"')
                elif "--user-data-dir=" in part:
                    user_data = part.split("=")[1].strip('"')
            
            # Deduplicate
            if any(n.exe_path == target and getattr(n, 'exe_args', '') == args for n in self._nodes):
                return False
                
            new_node = NodeEntry(
                id=str(uuid.uuid4())[:8],
                name=lnk_path.stem,
                node_type="browser" if browser_type != "exe" else "exe",
                exe_path=target,
                exe_args=args,
                browser_exe=browser_type if browser_type != "exe" else None,
                browser_profile_dir=profile,
                browser_user_data_dir=user_data,
                enabled=True
            )
            self._nodes.append(new_node)
            return True
        except Exception as e:
            logger.error(f"Error adding from shortcut: {e}")
            return False

    def _add_from_exe(self, exe_path: Path) -> bool:
        # Deduplicate
        if any(n.exe_path == str(exe_path) for n in self._nodes):
            return False
            
        new_node = NodeEntry(
            id=str(uuid.uuid4())[:8],
            name=exe_path.stem,
            node_type="exe",
            exe_path=str(exe_path),
            enabled=True
        )
        self._nodes.append(new_node)
        return True

    def _setup_ui(self):
        self.setWindowTitle("Node-Mate - Autonomous Agent v2.0")
        self.resize(1280, 850)
        
        # Disable the native minimize and maximize buttons to prevent ad impression loss
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMinimizeButtonHint)
        
        self.setStyleSheet(Styles.SHEET)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 1. Top Bar (Title, Stats & Global Actions)
        top_bar = QHBoxLayout()
        self.title_label = QLabel("🤖 Node-Mate <span style='color:#a0a0a0'>- Autonomous Agent</span>")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        top_bar.addWidget(self.title_label)
        
        top_bar.addSpacing(40)
        
        # New: System Stats in Top Bar
        self.perf_stats = QLabel("⚙️ CPU: 0% | 🧠 RAM: 0.0GB | 🚀 GPU: 0%")
        self.perf_stats.setStyleSheet(f"color: {Styles.TEXT_DIM}; font-size: 13px; font-family: 'Consolas', 'Courier New';")
        top_bar.addWidget(self.perf_stats)

        top_bar.addStretch()

        # Mini-Mode Button
        self.mini_mode_btn = QPushButton("↘️ Mini Mode", objectName="Secondary")
        self.mini_mode_btn.setFixedWidth(110)
        self.mini_mode_btn.clicked.connect(self._toggle_mini_mode)
        top_bar.addWidget(self.mini_mode_btn)
        
        self.agent_status_btn = QPushButton("Start Agent")
        self.agent_status_btn.setMinimumWidth(150)
        self.agent_status_btn.clicked.connect(self._toggle_agent)
        top_bar.addWidget(self.agent_status_btn)
        
        main_layout.addLayout(top_bar)

        # 2. Main Layout (Sidebar + Content)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left Sidebar (1, 2, 3)
        sidebar = QVBoxLayout()
        sidebar.setSpacing(20)
        
        # Panel 1: Status Summary
        self.panel_stats = self._create_panel("Status Summary")
        stats_layout = QGridLayout()
        self.stat_last_check = self._add_stat(stats_layout, "Last Check", "Never", 0, 0)
        self.stat_total_nodes = self._add_stat(stats_layout, "Total Nodes", "0", 0, 1)
        self.stat_healthy = self._add_stat(stats_layout, "Healthy", "0", 1, 0, color=Styles.SUCCESS)
        self.stat_failed = self._add_stat(stats_layout, "Failed", "0", 1, 1, color=Styles.DANGER)
        self.panel_stats.layout().addLayout(stats_layout)
        sidebar.addWidget(self.panel_stats)

        # Panel 2: Node Status
        self.panel_status = self._create_panel("Node Status")
        status_layout = QVBoxLayout()
        self.status_list = QListWidget()
        status_layout.addWidget(self.status_list)
        self.panel_status.layout().addLayout(status_layout)
        sidebar.addWidget(self.panel_status)

        # Panel 3: Recent Actions
        self.panel_actions = self._create_panel("Recent Agent Actions")
        actions_layout = QVBoxLayout()
        self.actions_list = QListWidget()
        actions_layout.addWidget(self.actions_list)
        self.panel_actions.layout().addLayout(actions_layout)
        sidebar.addWidget(self.panel_actions)
        
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(380)
        content_layout.addWidget(sidebar_widget)

        # Right Main Panel (Stacked Widget for App vs CLI views)
        self.right_stack = QStackedWidget()
        
        # View 1: Regular Apps Management
        self.panel_mgmt = self._create_panel("Nodes Management (Apps)")
        mgmt_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        
        # Removed Scan System button. Made Add App prominent.
        add_btn = QPushButton("➕ Add App")
        add_btn.setMinimumWidth(150)
        add_btn.clicked.connect(self._add_node_manually)

        switch_cli_btn = QPushButton("➡️ CLI Scripts Mode", objectName="Secondary")
        switch_cli_btn.clicked.connect(lambda: self.right_stack.setCurrentIndex(1))
        
        start_all_btn = QPushButton("▶️ Start All")
        start_all_btn.clicked.connect(self._start_all_nodes)
        
        stop_all_btn = QPushButton("⏹️ Stop All", objectName="Danger")
        stop_all_btn.clicked.connect(self._stop_all_nodes)
        
        btn_row.addWidget(add_btn)
        btn_row.addWidget(switch_cli_btn)
        btn_row.addStretch()
        btn_row.addWidget(start_all_btn)
        btn_row.addWidget(stop_all_btn)
        mgmt_layout.addLayout(btn_row)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search apps...")
        self.search_input.textChanged.connect(self._filter_nodes)
        mgmt_layout.addWidget(self.search_input)
        
        self.mgmt_list = QListWidget()
        mgmt_layout.addWidget(self.mgmt_list)
        self.panel_mgmt.layout().addLayout(mgmt_layout)
        self.right_stack.addWidget(self.panel_mgmt)
        
        # View 2: CLI Scripts Management
        self.panel_cli = self._create_panel("Nodes Management (CLI Scripts)")
        cli_layout = QVBoxLayout()
        cli_btn_row = QHBoxLayout()
        
        switch_app_btn = QPushButton("⬅️ Back to Apps")
        switch_app_btn.clicked.connect(lambda: self.right_stack.setCurrentIndex(0))
        
        add_cli_btn = QPushButton("➕ Add Script (.bat, .sh)", objectName="Secondary")
        add_cli_btn.clicked.connect(self._add_cli_script_manually)
        
        cli_start_all_btn = QPushButton("▶️ Start All")
        cli_start_all_btn.clicked.connect(self._start_all_cli_nodes)
        
        cli_stop_all_btn = QPushButton("⏹️ Stop All", objectName="Danger")
        cli_stop_all_btn.clicked.connect(self._stop_all_cli_nodes)
        
        cli_btn_row.addWidget(switch_app_btn)
        cli_btn_row.addWidget(add_cli_btn)
        cli_btn_row.addStretch()
        cli_btn_row.addWidget(cli_start_all_btn)
        cli_btn_row.addWidget(cli_stop_all_btn)
        cli_layout.addLayout(cli_btn_row)
        
        self.cli_search_input = QLineEdit()
        self.cli_search_input.setPlaceholderText("Search scripts...")
        self.cli_search_input.textChanged.connect(self._filter_cli_nodes)
        cli_layout.addWidget(self.cli_search_input)
        
        self.cli_list = QListWidget()
        cli_layout.addWidget(self.cli_list)
        self.panel_cli.layout().addLayout(cli_layout)
        self.right_stack.addWidget(self.panel_cli)
        
        content_layout.addWidget(self.right_stack)
        main_layout.addLayout(content_layout)
        
        # 3. Footer - Adsterra Ad Banner (with Dev Bypass and Anti-Farm)
        self.ad_banner = QFrame(objectName="AdSpace")
        self.ad_banner.setFixedHeight(90) 
        self.ad_banner.setStyleSheet(f"""
            QFrame#AdSpace {{ 
                background-color: #0d0e10; 
                border: 1px dashed #3a3f44; 
                border-radius: 8px;
            }}
        """)
        ad_layout = QHBoxLayout(self.ad_banner)
        ad_layout.setContentsMargins(0, 0, 0, 0)

        # Base64 Encoded Adsterra Snippet (728x90) - Full Mode
        ad_html_raw_728 = """
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background-color:#0d0e10;display:flex;justify-content:center;align-items:center;height:100vh;overflow:hidden;">
            <script type="text/javascript">
                atOptions = {
                    'key' : '14860aa79a4bd14ed1bd40df838cc61e',
                    'format' : 'iframe',
                    'height' : 90,
                    'width' : 728,
                    'params' : {}
                };
            </script>
            <script type="text/javascript" src="https://www.highperformanceformat.com/14860aa79a4bd14ed1bd40df838cc61e/invoke.js"></script>
        </body>
        </html>
        """
        self.ad_html_b64_728 = base64.b64encode(ad_html_raw_728.encode('utf-8')).decode('utf-8')

        # Base64 Encoded Adsterra Snippet (300x250) - Mini Mode
        ad_html_raw_300 = """
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background-color:#0d0e10;display:flex;justify-content:center;align-items:center;height:100vh;overflow:hidden;">
            <script type="text/javascript">
                atOptions = {
                    'key' : '157f60ecff4754886ad14ba657341765',
                    'format' : 'iframe',
                    'height' : 250,
                    'width' : 300,
                    'params' : {}
                };
            </script>
            <script type="text/javascript" src="https://www.highperformanceformat.com/157f60ecff4754886ad14ba657341765/invoke.js"></script>
        </body>
        </html>
        """
        self.ad_html_b64_300 = base64.b64encode(ad_html_raw_300.encode('utf-8')).decode('utf-8')

        # Dev Bypass Check
        dev_key_path = Path(".dev_bypass.key")
        
        # We always need self.ad_text initialized so the limiter can toggle it on/off
        self.ad_text = QLabel("")
        self.ad_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if dev_key_path.exists():
            # Developer Mode: Show fake banner to prevent IP bans
            self.ad_text.setText("🚀 [DEV MODE: Adsterra Bypassed] 🚀")
            self.ad_text.setStyleSheet(f"color: {Styles.SUCCESS}; font-weight: bold; font-size: 14px;")
            ad_layout.addWidget(self.ad_text)
        else:
            # Production Mode: Render real Adsterra banner via Base64 to prevent tampering
            self.web_view = QWebEngineView()
            self.web_view.setMinimumSize(728, 90)
            self.web_view.setMaximumSize(728, 90) 
            self._reload_ad_content() # Initial load
            
            # Center the web view in the layout
            ad_layout.addStretch()
            ad_layout.addWidget(self.web_view)
            
            # Add the text label but keep it hidden by default (only shows if limited)
            self.ad_text.hide()
            self.ad_text.setStyleSheet(f"color: {Styles.DANGER}; font-weight: bold; font-size: 14px;")
            ad_layout.addWidget(self.ad_text)
            
            ad_layout.addStretch()
            
            # Setup randomized Auto-Refresh Timer to safely increase impressions without risking bans
            self.ad_refresh_timer = QTimer()
            self.ad_refresh_timer.timeout.connect(self._reload_ad_content)
            # Initial random interval between 5 and 7 minutes (300,000 to 420,000 ms)
            initial_interval = random.randint(300000, 420000)
            self.ad_refresh_timer.start(initial_interval) 
        
        main_layout.addWidget(self.ad_banner)
        
    def _reload_ad_content(self):
        """Forces the QWebEngineView to reload the Base64 content, generating a new impression."""
        if hasattr(self, 'web_view') and self.ad_allowed:
            # We must re-decode and set HTML to force a true refresh of the iframe source
            if getattr(self, '_is_mini_mode', False):
                html_content = base64.b64decode(self.ad_html_b64_300).decode('utf-8')
            else:
                html_content = base64.b64decode(self.ad_html_b64_728).decode('utf-8')
                
            # Instead of loading via data URI which blocks cookies, we load HTML with a dummy base URL
            self.web_view.setHtml(html_content, baseUrl=QUrl("http://localhost"))
            logger.info("Adsterra Banner auto-refreshed.")
            
        # Recalculate a new random interval for the next refresh (between 5 and 7 minutes)
        if hasattr(self, 'ad_refresh_timer'):
            next_interval = random.randint(300000, 420000)
            self.ad_refresh_timer.setInterval(next_interval)
            logger.info(f"Next ad refresh randomized: {next_interval / 1000 / 60:.2f} minutes.")

    def _toggle_mini_mode(self):
        """Moves the app to the bottom right corner, keeping it un-minimized so ads count."""
        screen = QApplication.primaryScreen().availableGeometry()
        
        if getattr(self, '_is_mini_mode', False):
            # Restore to full view
            self._is_mini_mode = False
            self.mini_mode_btn.setText("↘️ Mini Mode")
            # Restore central widget layout and sizing
            self.title_label.show()
            self.perf_stats.show()
            
            # Switch back to the 728x90 layout
            self.ad_banner.setFixedHeight(90)
            if hasattr(self, 'web_view'):
                self.web_view.setMinimumSize(728, 90)
                self.web_view.setMaximumSize(728, 90)
            self._reload_ad_content() # Reload with 728x90 snippet
            
            # Remove strict size constraints so the window can expand again
            self.setMinimumSize(800, 600)
            self.setMaximumSize(16777215, 16777215) # Default PyQt max size
            
            self.resize(1280, 850)
            self.right_stack.show()
            self.panel_stats.show()
            self.panel_status.show()
            self.panel_actions.show()
            
            # Center on screen
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )
        else:
            # Enter Mini Mode
            self._is_mini_mode = True
            self.mini_mode_btn.setText("↖️ Full Mode")
            
            # Hide large panels, only keep the queue and ad banner
            self.right_stack.hide()
            self.panel_stats.hide()
            self.panel_actions.hide()
            
            # Make the title bar super compact
            self.title_label.hide()
            self.perf_stats.hide()
            
            # Hide the Node Status list to make it as tiny as possible
            self.panel_status.hide()
            
            # Switch to the 300x250 layout
            self.ad_banner.setFixedHeight(250)
            if hasattr(self, 'web_view'):
                self.web_view.setMinimumSize(300, 250)
                self.web_view.setMaximumSize(300, 250)
            self._reload_ad_content() # Reload with 300x250 snippet
            
            # Force the window to be EXACTLY 320x310 and lock it there
            self.setMinimumSize(320, 310)
            self.setMaximumSize(320, 310)
            self.resize(320, 310)
            
            # Move to bottom right of the screen
            self.move(
                screen.width() - self.width() - 20,
                screen.height() - self.height() - 40 # slightly higher to clear taskbar
            )
        
    def _add_node_manually(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Node Executable or Shortcut", "", 
            "Executables/Shortcuts (*.exe *.lnk);;All Files (*)"
        )
        if file_path:
            p = Path(file_path)
            if p.suffix.lower() == ".lnk":
                if self._add_from_shortcut(p):
                    self._refresh_node_lists()
            else:
                if self._add_from_exe(p):
                    self._refresh_node_lists()
            self._log_action(f"Manually added node: {p.name}")
            if self.watchdog.is_active:
                self.watchdog.start_monitoring([n for n in self._nodes if n.enabled])
            
        # Re-apply accepting drops
        self.setAcceptDrops(True)

    def _add_cli_script_manually(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CLI Script", "", 
            "Scripts (*.bat *.ps1 *.sh *.cmd);;All Files (*)"
        )
        if file_path:
            p = Path(file_path)
            # Deduplicate
            if any(n.exe_path == str(p) for n in self._nodes):
                QMessageBox.warning(self, "Duplicate", f"Script '{p.name}' is already in the list.")
                return

            new_node = NodeEntry(
                id=str(uuid.uuid4())[:8],
                name=p.stem,
                node_type="exe", # We handle scripts via 'exe' type in the launcher
                exe_path=str(p),
                run_without_hidden_console=True, # Scripts usually need to be visible or need a console
                enabled=True
            )
            self._nodes.append(new_node)
            self._refresh_node_lists()
            self._log_action(f"Manually added CLI script: {p.name}")
            if self.watchdog.is_active:
                self.watchdog.start_monitoring([n for n in self._nodes if n.enabled])

    def _create_panel(self, title: str) -> QFrame:
        frame = QFrame(objectName="Panel")
        layout = QVBoxLayout(frame)
        header = QLabel(title.upper(), objectName="Header")
        layout.addWidget(header)
        return frame

    def _add_stat(self, layout, label: str, val: str, r, c, color=None) -> QLabel:
        v_label = QLabel(val, objectName="StatValue")
        if color: v_label.setStyleSheet(f"color: {color};")
        l_label = QLabel(label, objectName="StatLabel")
        container = QVBoxLayout()
        container.addWidget(v_label)
        container.addWidget(l_label)
        layout.addLayout(container, r, c)
        return v_label

    def _setup_connections(self):
        self.watchdog.node_status_changed.connect(self._on_node_status_changed)
        self.watchdog.alert_required.connect(self._on_alert_required)

    def _toggle_agent(self):
        if not self.watchdog.is_active:
            enabled_nodes = [n for n in self._nodes if n.enabled]
            if not enabled_nodes:
                QMessageBox.warning(self, "No Nodes", "Tick some nodes in 'Nodes Management' to monitor them!")
                return
            self.watchdog.start_monitoring(enabled_nodes)
            self.agent_status_btn.setText("Stop Agent")
            self.agent_status_btn.setStyleSheet(f"background-color: {Styles.DANGER};")
            self._log_action("Agent started monitoring nodes")
            self._save_agent_state(True)
        else:
            self.watchdog.stop_monitoring()
            self.agent_status_btn.setText("Start Agent")
            self.agent_status_btn.setStyleSheet(f"background-color: {Styles.ACCENT};")
            self._log_action("Agent manually stopped")
            self._save_agent_state(False)

    def _save_agent_state(self, is_active: bool):
        """Saves the last known state of the agent so it can auto-recover after a reboot."""
        state_path = Path.home() / ".nodemate" / "agent_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(state_path, 'w') as f:
                json.dump({"was_active": is_active}, f)
        except Exception as e:
            logger.error(f"Failed to save agent state: {e}")

    def _load_nodes(self):
        # Use existing nodes from nodes.json in home dir or fallback
        config_path = Path.home() / ".nodemate" / "nodes.json"
        flag_path = Path.home() / ".nodemate" / "user_setup.done"
        
        # FIRST RUN CHECK:
        # If the user_setup.done flag does not exist, we must assume this is a fresh install
        # or a first run. We must WIPE the nodes.json so they don't see the developer's nodes.
        if config_path.exists() and not flag_path.exists():
            try:
                logger.info("First run detected. Wiping bundled nodes.json.")
                config_path.unlink()
            except Exception as e:
                logger.error(f"Failed to wipe bundled nodes.json: {e}")
                
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    self._nodes = [node_from_dict(d) for d in data]
            except Exception as e:
                logger.error(f"Failed to load nodes: {e}")
        else:
            self._nodes = []
            
        self._refresh_node_lists()
        
        # Ensure Empty State message if no nodes exist
        if not self._nodes:
            self._log_action("No nodes detected. Click '+ Add App' to begin.")
            
        # Check if the agent should auto-start due to a power outage / reboot
        self._check_auto_start_agent()

    def _check_auto_start_agent(self):
        """If the agent was ON before the app closed, turn it back ON automatically."""
        state_path = Path.home() / ".nodemate" / "agent_state.json"
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    data = json.load(f)
                    if data.get("was_active", False):
                        # Use a slight delay to let the UI finish rendering before starting heavy operations
                        QTimer.singleShot(1000, self._auto_start_recovery)
            except Exception as e:
                logger.error(f"Failed to read agent state: {e}")

    def _auto_start_recovery(self):
        enabled_nodes = [n for n in self._nodes if n.enabled]
        if enabled_nodes and not self.watchdog.is_active:
            self._log_action("🔄 Power Outage Recovery: Auto-starting Agent...")
            self.watchdog.start_monitoring(enabled_nodes)
            self.agent_status_btn.setText("Stop Agent")
            self.agent_status_btn.setStyleSheet(f"background-color: {Styles.DANGER};")

    def _save_nodes(self):
        config_path = Path.home() / ".nodemate" / "nodes.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump([n.to_dict() for n in self._nodes], f, indent=2)

    def _refresh_node_lists(self):
        self._save_nodes()
        
        # Save current scroll positions
        mgmt_scroll = self.mgmt_list.verticalScrollBar().value()
        cli_scroll = self.cli_list.verticalScrollBar().value()
        status_scroll = self.status_list.verticalScrollBar().value()
        
        self.mgmt_list.clear()
        self.cli_list.clear()
        self.status_list.clear()
        
        # Sort nodes alphabetically by name (case-insensitive)
        sorted_nodes = sorted(self._nodes, key=lambda n: n.name.lower() if n.name else "")
        
        # Build the Node Status (Blue Box) list based STRICTLY on the order they are enabled
        # Filter to only enabled nodes, and sort them by their internal order timestamp (if available) or keep their loaded order
        enabled_nodes = [n for n in self._nodes if n.enabled]
        
        # Sort enabled nodes by when they were enabled/ticked (we can rely on their internal state or list position)
        # To make it perfectly match the "ticked order", we will populate the blue box using a separate logic below.
        
        for node in sorted_nodes:
            # Determine if it's a script based on the executable extension
            is_script = False
            if node.exe_path:
                ext = Path(node.exe_path).suffix.lower()
                if ext in ['.bat', '.cmd', '.ps1', '.sh']:
                    is_script = True

            # Mgmt item (Searchable)
            m_item = QListWidgetItem()
            m_widget = QWidget()
            m_layout = QHBoxLayout(m_widget)
            m_layout.setContentsMargins(5, 5, 10, 5)
            
            cb = QCheckBox(node.name)
            cb.blockSignals(True)  # CRITICAL: Prevent refresh loop
            cb.setChecked(node.enabled)
            cb.blockSignals(False)
            cb.stateChanged.connect(lambda state, n=node: self._on_node_toggled(n, bool(state)))
            
            # Action Buttons: Stop, Props, Remove
            stop_btn = QPushButton("Stop", objectName="Danger")
            stop_btn.setFixedWidth(55)
            stop_btn.clicked.connect(lambda _, n=node: self._stop_single_process(n))
            
            props_btn = QPushButton("Props", objectName="Secondary")
            props_btn.setFixedWidth(55)
            props_btn.clicked.connect(lambda _, n=node: self._edit_node(n))
            
            remove_btn = QPushButton("Remove", objectName="Danger")
            remove_btn.setFixedWidth(75)
            remove_btn.clicked.connect(lambda _, n=node: self._remove_node(n))
            
            m_widget.setStyleSheet(f"""
                QWidget {{
                    border-bottom: 1px solid {Styles.BORDER};
                }}
                QCheckBox {{
                    border: none;
                }}
                QPushButton {{
                    border-bottom: none; /* Prevent double borders on buttons */
                }}
            """)
            
            m_layout.addWidget(cb)
            m_layout.addStretch()
            m_layout.addWidget(props_btn)
            m_layout.addWidget(remove_btn)
            m_layout.addWidget(stop_btn)
            
            m_widget.setMinimumHeight(50)
            m_item.setSizeHint(m_widget.sizeHint())

            # Route to the correct list
            if is_script:
                self.cli_list.addItem(m_item)
                self.cli_list.setItemWidget(m_item, m_widget)
            else:
                self.mgmt_list.addItem(m_item)
                self.mgmt_list.setItemWidget(m_item, m_widget)
            
        # Add Status items (Blue Box) separately, sorting ONLY by their ticked order
        # We use self._nodes instead of sorted_nodes because self._nodes retains insertion/update order
        for node in self._nodes:
            if node.enabled:
                self._add_status_item(node)
        
        # Restore scroll positions
        self.mgmt_list.verticalScrollBar().setValue(mgmt_scroll)
        self.cli_list.verticalScrollBar().setValue(cli_scroll)
        self.status_list.verticalScrollBar().setValue(status_scroll)
        
        self._update_stats()

    def _filter_cli_nodes(self, text):
        text = text.lower()
        for i in range(self.cli_list.count()):
            item = self.cli_list.item(i)
            widget = self.cli_list.itemWidget(item)
            cb = widget.findChild(QCheckBox)
            item.setHidden(text not in cb.text().lower())

    def _start_all_nodes(self):
        for node in self._nodes:
            if not (node.exe_path and Path(node.exe_path).suffix.lower() in ['.bat', '.cmd', '.ps1', '.sh']):
                node.enabled = True
        self._save_nodes()
        self._refresh_node_lists()
        self._log_action("Enabled all app nodes")

    def _start_all_cli_nodes(self):
        for node in self._nodes:
            if node.exe_path and Path(node.exe_path).suffix.lower() in ['.bat', '.cmd', '.ps1', '.sh']:
                node.enabled = True
        self._save_nodes()
        self._refresh_node_lists()
        self._log_action("Enabled all CLI scripts")

    def _stop_all_cli_nodes(self):
        for node in self._nodes:
            if node.exe_path and Path(node.exe_path).suffix.lower() in ['.bat', '.cmd', '.ps1', '.sh']:
                node.enabled = False
        self._save_nodes()
        self._refresh_node_lists()
        self._log_action("Disabled all CLI scripts")

    def _stop_all_nodes(self):
        for node in self._nodes:
            if not (node.exe_path and Path(node.exe_path).suffix.lower() in ['.bat', '.cmd', '.ps1', '.sh']):
                node.enabled = False
        self._save_nodes()
        self._refresh_node_lists()
        self._log_action("Disabled all app nodes")

    def _stop_single_process(self, node: NodeEntry):
        """Actively kills a specific process tree without changing its enabled state."""
        import threading
        def kill_process():
            try:
                from nodemate.launcher import find_pids_for_node
                import psutil
                pids = find_pids_for_node(node)
                for pid in pids:
                    try:
                        proc = psutil.Process(pid)
                        for child in proc.children(recursive=True):
                            child.kill()
                        proc.kill()
                        self._log_action(f"Force stopped process for {node.name}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception as e:
                logger.error(f"Failed to force stop process for {node.name}: {e}")
        
        # Uncheck it so the watchdog doesn't immediately restart it
        node.enabled = False
        self._save_nodes()
        self._refresh_node_lists()
        
        # Kill it in the background
        threading.Thread(target=kill_process, daemon=True).start()

    def _on_node_toggled(self, node: NodeEntry, state: bool):
        # The checkbox passes state as an integer (0 or 2).
        # We MUST check if the state is actually changing to prevent the UI from infinite looping.
        new_state_bool = bool(state)
        if node.enabled == new_state_bool:
            return
            
        # Docker Desktop Rule: Warn the user and prevent auto-management of the main daemon.
        if new_state_bool and "docker desktop" in (node.name or "").lower():
            QMessageBox.warning(self, "Docker Desktop Notice", 
                "Docker Desktop should be launched manually before starting the agent.\n\n"
                "The agent is designed to monitor individual Docker Containers (like 'pi-consensus'), "
                "not the main Docker Engine itself. Please uncheck Docker Desktop and use the 'Linked Container' "
                "field in the 'Props' of your specific apps instead.")
            
            # Uncheck it visually by refreshing the list, but don't save the True state
            # We must use QTimer.singleShot to uncheck it slightly after the event loop to avoid visual bugs
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._force_untick_node(node))
            return
            
        logger.info(f"Node toggled: {node.name} ({node.id}) -> {new_state_bool}")
        node.enabled = new_state_bool
        
        # When a node is checked, move it to the end of the internal list so it becomes the "last ticked"
        # This guarantees the Blue Box shows them in exact tick order, and the watchdog launches them in tick order.
        if new_state_bool:
            try:
                self._nodes.remove(node)
                self._nodes.append(node)
            except ValueError:
                pass
        
        self._save_nodes()
        self._refresh_node_lists()
        if self.watchdog.is_active:
            # Hot reload if running
            self.watchdog.start_monitoring([n for n in self._nodes if n.enabled])

    def _add_status_item(self, node: NodeEntry):
        s_item = QListWidgetItem()
        s_widget = QWidget()
        s_layout = QHBoxLayout(s_widget)
        
        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {Styles.TEXT_DIM}; font-size: 18px;")
        
        name_label = QLabel(node.name)
        status_label = QLabel("Initializing...")
        status_label.setStyleSheet(f"color: {Styles.TEXT_DIM};")
        
        s_layout.addWidget(indicator)
        s_layout.addWidget(name_label)
        s_layout.addStretch()
        s_layout.addWidget(status_label)
        
        s_item.setSizeHint(s_widget.sizeHint())
        s_item.setData(Qt.ItemDataRole.UserRole, node.id)
        self.status_list.addItem(s_item)
        self.status_list.setItemWidget(s_item, s_widget)

    def _force_untick_node(self, node: NodeEntry):
        """Helper to force a node to be unchecked after a warning."""
        node.enabled = False
        self._save_nodes()
        self._refresh_node_lists()

    def _on_node_status_changed(self, node_id: str, status: str, message: str):
        logger.info(f"Status changed signal received: {node_id} | {status} | {message}")
        # Call the _update_stats method to refresh performance stats
        self._update_stats()

        # Update node status in UI
        for i in range(self.status_list.count()):
            item = self.status_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == node_id:
                widget = self.status_list.itemWidget(item)
                indicator = widget.findChild(QLabel, "") # indicator is first label
                status_label = widget.findChildren(QLabel)[-1]
                
                status_label.setText(message)
                if status == "healthy": 
                    indicator.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 18px;")
                    status_label.setStyleSheet(f"color: {Styles.SUCCESS};")
                elif status == "waiting":
                    indicator.setStyleSheet(f"color: {Styles.WARNING}; font-size: 18px;")
                    status_label.setStyleSheet(f"color: {Styles.WARNING};")
                else:
                    indicator.setStyleSheet(f"color: {Styles.DANGER}; font-size: 18px;")
                    status_label.setStyleSheet(f"color: {Styles.DANGER};")
                break
        
        self._log_action(f"{node_id[:8]}...: {message}")

    def _log_action(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"{ts} - {msg}")
        self.actions_list.insertItem(0, item)
        if self.actions_list.count() > 100: self.actions_list.takeItem(100)

    def _update_stats(self):
        import psutil
        try:
            # Global Stats (Matched to Task Manager) - Fast!
            self.stat_total_nodes.setText(str(len(self._nodes)))
            self.stat_last_check.setText(datetime.now().strftime("%H:%M"))

            cpu_pct = psutil.cpu_percent()
            ram = psutil.virtual_memory()
            self.perf_stats.setText(f"⚙️ CPU: {cpu_pct}% | 🧠 RAM: {ram.percent}% ({ram.used/(1024**3):.1f}GB) | 🚀 GPU: 0%")

            # Update Node-Specific Stats (PASSIVE)
            # We don't scan processes here anymore. The status labels are updated 
            # via signals from the watchdog or during manual refresh events.
            pass
        except Exception as e:
            logger.error(f"Stats update error: {e}")

    def _filter_nodes(self, text):
        text = text.lower()
        for i in range(self.mgmt_list.count()):
            item = self.mgmt_list.item(i)
            widget = self.mgmt_list.itemWidget(item)
            cb = widget.findChild(QCheckBox)
            item.setHidden(text not in cb.text().lower())

    def _edit_node(self, node: NodeEntry):
        dialog = NodeEditDialog(node, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_nodes()
            self._refresh_node_lists()

    def _update_node(self, node: NodeEntry):
        if not node.update_command:
            QMessageBox.warning(self, "Update", f"No update command set for {node.name}.\nSet it in 'Props' first.")
            return
            
        self._log_action(f"Updating {node.name}...")
        from nodemate.launcher import run_update_command
        code, out = run_update_command(node.update_command)
        
        if code == 0:
            QMessageBox.information(self, "Update Success", f"{node.name} updated successfully!\nOutput:\n{out}")
        else:
            QMessageBox.critical(self, "Update Failed", f"{node.name} update failed (Code {code}).\nOutput:\n{out}")

    def _remove_node(self, node: NodeEntry):
        # Removed confirmation popup. Just deletes immediately.
        self._nodes = [n for n in self._nodes if n.id != node.id]
        self._save_nodes()
        self._refresh_node_lists()
        self._log_action(f"Removed node: {node.name}")

    def _on_alert_required(self, name, path):
        self._log_action(f"⚠️ ALERT: {name} needs manual login!")

class NodeEditDialog(QDialog):
    def __init__(self, node: NodeEntry, parent=None):
        super().__init__(parent)
        self.node = node
        self.setWindowTitle(f"Node - {node.name}")
        self.setStyleSheet(Styles.SHEET + f"""
            QDialog {{ background-color: {Styles.MAIN_BG}; }} 
            QLabel {{ color: {Styles.TEXT}; }}
            QLineEdit, QSpinBox {{ 
                background-color: #000000; 
                color: #ffffff; 
                border: 1px solid {Styles.BORDER}; 
                padding: 5px; 
                border-radius: 4px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 24px;
                background-color: #444444;
                border: 1px solid #666666;
                border-radius: 2px;
            }}
            QSpinBox::up-arrow {{
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 5px solid #ffffff;
                width: 0; height: 0;
            }}
            QSpinBox::down-arrow {{
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0; height: 0;
            }}
        """)
        self.setMinimumWidth(550)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.name_edit = QLineEdit(node.name)
        self.exe_edit = QLineEdit(node.exe_path)
        self.args_edit = QLineEdit(node.exe_args)
        
        # Linked Docker Container
        self.docker_edit = QLineEdit(getattr(node, 'docker_name', ''))
        self.docker_edit.setPlaceholderText("Optional: e.g. pi-consensus (monitors container too)")
        
        # Auto Click Settings
        self.auto_click_edit = QLineEdit(getattr(node, 'auto_click_image_path', ''))
        self.auto_click_edit.setPlaceholderText("Optional: Screenshot of button to auto-click")
        
        self.auto_click_delay_spin = QSpinBox()
        self.auto_click_delay_spin.setRange(1, 300)
        self.auto_click_delay_spin.setValue(getattr(node, 'auto_click_delay', 15))
        self.auto_click_delay_spin.setSuffix(" sec (wait before click)")
        
        # CPU Heartbeat Settings
        self.zero_cpu_cb = QCheckBox("Restart app / Click button if CPU drops to 0%")
        self.zero_cpu_cb.setChecked(getattr(node, 'restart_on_zero_cpu', False))
        
        self.zero_cpu_spin = QSpinBox()
        self.zero_cpu_spin.setRange(1, 1440)
        self.zero_cpu_spin.setValue(getattr(node, 'zero_cpu_minutes', 5))
        self.zero_cpu_spin.setSuffix(" minutes at 0% CPU")
        
        # Startup Delay (Seconds)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3600)
        self.delay_spin.setValue(max(node.start_delay_seconds, node.start_delay_minutes * 60))
        self.delay_spin.setSuffix(" seconds")
        
        self.heavy_cb = QCheckBox("Heavy (wait for 1GB RAM headroom when batch-starting)")
        self.heavy_cb.setChecked(getattr(node, 'wait_for_ram', False))
        
        self.auto_start_cb = QCheckBox("Auto-start when ticked but not running (watchdog launches it)")
        self.auto_start_cb.setChecked(getattr(node, 'auto_start', True))

        self.visible_console_cb = QCheckBox("Run with visible console (Don't hide window) - Best for scripts")
        self.visible_console_cb.setChecked(getattr(node, 'run_without_hidden_console', False))

        # Add help hints
        hint_style = "color: #a0a0a0; font-size: 11px; margin-bottom: 5px;"
        
        form.addRow("Display Name:", self.name_edit)
        form.addRow("Executable (.exe):", self._wrap_with_browse(self.exe_edit))
        form.addRow("Arguments (optional):", self.args_edit)
        form.addRow("Linked Container:", self.docker_edit)
        form.addRow("Startup Delay:", self.delay_spin)
        form.addRow("Auto-Click Image:", self._wrap_with_browse_image(self.auto_click_edit))
        form.addRow("Auto-Click Wait:", self.auto_click_delay_spin)
        form.addRow("0% CPU Timeout:", self.zero_cpu_spin)
        
        layout.addLayout(form)
        layout.addWidget(self.heavy_cb)
        layout.addWidget(self.auto_start_cb)
        layout.addWidget(self.visible_console_cb)
        layout.addWidget(self.zero_cpu_cb)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addStretch()
        layout.addWidget(btns)

    def _wrap_with_browse(self, line_edit):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("Browse...", objectName="Secondary")
        btn.setFixedWidth(80)
        btn.clicked.connect(lambda: self._browse_exe(line_edit))
        l.addWidget(line_edit)
        l.addWidget(btn)
        return w

    def _wrap_with_browse_image(self, line_edit):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("Browse...", objectName="Secondary")
        btn.setFixedWidth(80)
        btn.clicked.connect(lambda: self._browse_image(line_edit))
        l.addWidget(line_edit)
        l.addWidget(btn)
        return w

    def _browse_exe(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select Executable", "", "Executables (*.exe);;All Files (*.*)")
        if path: line_edit.setText(path)

    def _browse_image(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select Button Image", "", "Images (*.png *.jpg *.jpeg);;All Files (*.*)")
        if path: line_edit.setText(path)

    def _save(self):
        self.node.name = self.name_edit.text()
        self.node.exe_path = self.exe_edit.text()
        self.node.exe_args = self.args_edit.text()
        self.node.docker_name = self.docker_edit.text()
        self.node.start_delay_seconds = self.delay_spin.value()
        self.node.start_delay_minutes = self.delay_spin.value() // 60
        self.node.wait_for_ram = self.heavy_cb.isChecked()
        self.node.auto_start = self.auto_start_cb.isChecked()
        self.node.run_without_hidden_console = self.visible_console_cb.isChecked()
        self.node.auto_click_image_path = self.auto_click_edit.text()
        self.node.auto_click_delay = self.auto_click_delay_spin.value()
        self.node.restart_on_zero_cpu = self.zero_cpu_cb.isChecked()
        self.node.zero_cpu_minutes = self.zero_cpu_spin.value()
        self.accept()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Settings")
        self.setMinimumWidth(400)
        self.setStyleSheet(Styles.SHEET + f"QDialog {{ background-color: {Styles.MAIN_BG}; }}")
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Load current config to show in fields
        config = load_config()
        
        self.bot_token = QLineEdit(config.get("telegram_token", ""))
        self.bot_token.setPlaceholderText("Enter Telegram Bot Token")
        self.chat_id = QLineEdit(config.get("telegram_chat_id", ""))
        self.chat_id.setPlaceholderText("Enter Chat ID")
        
        form.addRow("🤖 Bot Token:", self.bot_token)
        form.addRow("💬 Chat ID:", self.chat_id)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def accept(self):
        config = load_config()
        config["telegram_token"] = self.bot_token.text()
        config["telegram_chat_id"] = self.chat_id.text()
        save_config(config)
        super().accept()

def main():
    app = QApplication(sys.argv)
    window = LightweightMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
