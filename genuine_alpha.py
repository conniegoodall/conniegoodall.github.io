import sys
import uuid
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QLineEdit, QMessageBox, QStackedWidget,
    QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer

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
    
    QMessageBox {{ background-color: {PANEL_BG}; }}
    QMessageBox QLabel {{ color: {TEXT}; font-size: 14px; }}
    
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
    
    QListWidget {{ background-color: transparent; border: none; }}
    QListWidget::item {{ 
        background-color: {PANEL_BG}; 
        border-radius: 8px; 
        margin-bottom: 6px; 
        padding: 5px; 
    }}
    QListWidget::item:selected {{ background-color: {ACCENT}; }}
    
    QCheckBox {{ color: {TEXT}; spacing: 12px; font-size: 14px; }}
    QCheckBox::indicator {{ 
        width: 20px; height: 20px; 
        border: 2px solid {BORDER}; border-radius: 4px; 
    }}
    QCheckBox::indicator:checked {{ background-color: #32CD32; }}
    """

class GenuineAlphaWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._is_active = False
        self._setup_ui()
        self._populate_dummy_data()

    def _setup_ui(self):
        self.setWindowTitle("Node-Mate - Autonomous Agent v0.1-Beta")
        self.resize(1280, 850)
        self.setStyleSheet(Styles.SHEET)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 1. Top Bar
        top_bar = QHBoxLayout()
        self.title_label = QLabel("🤖 Node-Mate <span style='color:#a0a0a0'>- Genuine UI Shell Beta</span>")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        top_bar.addWidget(self.title_label)
        
        top_bar.addSpacing(40)
        
        self.perf_stats = QLabel("⚙️ CPU: 12% | 🧠 RAM: 4.2GB | 🚀 GPU: 3%")
        self.perf_stats.setStyleSheet(f"color: {Styles.TEXT_DIM}; font-size: 13px; font-family: 'Consolas', 'Courier New';")
        top_bar.addWidget(self.perf_stats)

        top_bar.addStretch()

        self.settings_btn = QPushButton("⚙️ Settings", objectName="Secondary")
        self.settings_btn.setFixedWidth(110)
        self.settings_btn.clicked.connect(lambda: self._show_beta_message("Settings Menu"))
        top_bar.addWidget(self.settings_btn)
        
        self.agent_status_btn = QPushButton("Start Agent")
        self.agent_status_btn.setMinimumWidth(150)
        self.agent_status_btn.clicked.connect(self._toggle_agent)
        top_bar.addWidget(self.agent_status_btn)
        
        main_layout.addLayout(top_bar)

        # 2. Main Layout (Sidebar + Content)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left Sidebar
        sidebar = QVBoxLayout()
        sidebar.setSpacing(20)
        
        self.panel_stats = self._create_panel("Status Summary")
        stats_layout = QGridLayout()
        self.stat_last_check = self._add_stat(stats_layout, "Last Check", "Never", 0, 0)
        self.stat_total_nodes = self._add_stat(stats_layout, "Total Nodes", "3", 0, 1)
        self.stat_healthy = self._add_stat(stats_layout, "Healthy", "0", 1, 0, color=Styles.SUCCESS)
        self.stat_failed = self._add_stat(stats_layout, "Failed", "0", 1, 1, color=Styles.DANGER)
        self.panel_stats.layout().addLayout(stats_layout)
        sidebar.addWidget(self.panel_stats)

        self.panel_status = self._create_panel("Node Status (Queue)")
        status_layout = QVBoxLayout()
        self.status_list = QListWidget()
        status_layout.addWidget(self.status_list)
        self.panel_status.layout().addLayout(status_layout)
        sidebar.addWidget(self.panel_status)

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

        # Right Main Panel
        self.right_stack = QStackedWidget()
        
        self.panel_mgmt = self._create_panel("Nodes Management (Apps)")
        mgmt_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        
        scan_btn = QPushButton("🔍 Scan System", objectName="Secondary")
        scan_btn.clicked.connect(lambda: self._show_beta_message("System Scanner"))
        
        add_btn = QPushButton("➕ Add App", objectName="Secondary")
        add_btn.clicked.connect(lambda: self._show_beta_message("Manual App Adder"))

        start_all_btn = QPushButton("▶️ Start All")
        start_all_btn.clicked.connect(lambda: self._show_beta_message("Mass Node Starter"))
        
        stop_all_btn = QPushButton("⏹️ Stop All", objectName="Danger")
        stop_all_btn.clicked.connect(lambda: self._show_beta_message("Mass Node Stopper"))
        
        btn_row.addWidget(scan_btn)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(start_all_btn)
        btn_row.addWidget(stop_all_btn)
        mgmt_layout.addLayout(btn_row)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search apps...")
        mgmt_layout.addWidget(self.search_input)
        
        self.mgmt_list = QListWidget()
        mgmt_layout.addWidget(self.mgmt_list)
        self.panel_mgmt.layout().addLayout(mgmt_layout)
        self.right_stack.addWidget(self.panel_mgmt)
        
        content_layout.addWidget(self.right_stack)
        main_layout.addLayout(content_layout)
        
        # Footer - Ad Banner Space
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
        self.ad_text = QLabel("🚀 [PAID ADVERTISING SPACE - 728x90] 🚀")
        self.ad_text.setStyleSheet(f"color: {Styles.ACCENT}; font-weight: bold; font-size: 16px;")
        ad_layout.addStretch()
        ad_layout.addWidget(self.ad_text)
        ad_layout.addStretch()
        
        main_layout.addWidget(self.ad_banner)

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

    def _populate_dummy_data(self):
        # Dummy Apps
        for app in ["Docker Desktop", "Pi Network", "Opera GX - Profile 1"]:
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            
            chk = QCheckBox(app)
            layout.addWidget(chk)
            layout.addStretch()
            
            btn = QPushButton("Props")
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda _, a=app: self._show_beta_message(f"Properties for {a}"))
            layout.addWidget(btn)
            
            item.setSizeHint(widget.sizeHint())
            self.mgmt_list.addItem(item)
            self.mgmt_list.setItemWidget(item, widget)

        self.actions_list.addItem("UI Initialization Complete...")
        self.actions_list.addItem("Awaiting network APIs...")

    def _toggle_agent(self):
        if not self._is_active:
            self._is_active = True
            self.agent_status_btn.setText("Stop Agent")
            self.agent_status_btn.setStyleSheet(f"background-color: {Styles.DANGER};")
            self.actions_list.insertItem(0, "Agent monitoring started (Mock Mode)")
        else:
            self._is_active = False
            self.agent_status_btn.setText("Start Agent")
            self.agent_status_btn.setStyleSheet(f"background-color: {Styles.ACCENT};")
            self.actions_list.insertItem(0, "Agent stopped")

    def _show_beta_message(self, feature_name):
        QMessageBox.information(
            self, 
            "Beta Version", 
            f"Veloce Node-Mate v0.1-Beta\n\n"
            f"The '{feature_name}' module is disabled in this UI shell.\n"
            "This genuine alpha is provided for UI layout and ad network approval testing only."
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GenuineAlphaWindow()
    window.show()
    sys.exit(app.exec())
