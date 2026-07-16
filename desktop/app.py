"""
MainWindow application container for CAI Sandbox Desktop GUI.
Provides sidebar navigation, status polling, and page management.
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QFrame, QPushButton, QLabel, QStackedWidget, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer

from desktop.core.sandbox_state import SandboxStateManager
from desktop.pages.page_nodes import NodesPage
from desktop.pages.page_simulation import SimulationPage
from desktop.pages.page_deploy import DeployPage
from desktop.pages.page_inference import InferencePage
from desktop.pages.page_logs import LogsPage


class CAIWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAI Sandbox Desktop Manager")
        self.resize(1100, 750)
        
        # Central state manager instance
        self.state_manager = SandboxStateManager()
        
        # Central Widget & Base Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create UI
        self.setup_sidebar()
        self.setup_content_area()
        
        # Setup background metrics timer (polls telemetry/registry updates)
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.state_manager.update_metrics)
        self.metrics_timer.start(3000) # update every 3 seconds
        
        # Connect state manager status changes to status bar
        self.state_manager.status_changed.connect(self.update_status_bar)
        
        # Initial view
        self.switch_page(0)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)
        
        # App Title / Logo
        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(20, 0, 20, 20)
        
        logo = QLabel("K")
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #14b8a6, stop:1 #0d9488);
            border-radius: 6px;
            color: #0f172a;
            font-size: 18px;
            font-weight: bold;
        """)
        
        title_lbl = QLabel("CAI Sandbox")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        
        title_layout.addWidget(logo)
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        sidebar_layout.addWidget(title_frame)
        
        # Navigation Button Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        
        nav_buttons = [
            ("  Control & Nodes", 0),
            ("  Virtual Simulation", 1),
            ("  Model Deployment", 2),
            ("  Distributed Chat", 3),
            ("  Terminal Logs", 4),
        ]
        
        for text, index in nav_buttons:
            btn = QPushButton(text)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(50)
            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            self.nav_group.addButton(btn, index)
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        # Footer / Node Status
        self.status_lbl = QLabel("🔴 Control Plane: Inactive")
        self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 0 20px;")
        sidebar_layout.addWidget(self.status_lbl)
        
        self.main_layout.addWidget(self.sidebar)

    def setup_content_area(self):
        # Content frame holding top-bar, stacked pages and status footer
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(15)
        
        # Top header
        self.header_lbl = QLabel("CAI Control Panel")
        self.header_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        content_layout.addWidget(self.header_lbl)
        
        # Pages Stack
        self.pages_stack = QStackedWidget()
        
        # Instantiate pages
        self.page_nodes = NodesPage(self.state_manager)
        self.page_simulation = SimulationPage(self.state_manager)
        self.page_deploy = DeployPage(self.state_manager)
        self.page_inference = InferencePage(self.state_manager)
        self.page_logs = LogsPage(self.state_manager)
        
        self.pages_stack.addWidget(self.page_nodes)
        self.pages_stack.addWidget(self.page_simulation)
        self.pages_stack.addWidget(self.page_deploy)
        self.pages_stack.addWidget(self.page_inference)
        self.pages_stack.addWidget(self.page_logs)
        
        content_layout.addWidget(self.pages_stack)
        
        # Status footer bar
        self.footer_lbl = QLabel("Ready")
        self.footer_lbl.setStyleSheet("color: #64748b; border-top: 1px solid #1e293b; padding-top: 8px; font-size: 12px;")
        content_layout.addWidget(self.footer_lbl)
        
        self.main_layout.addWidget(content_frame)

    def switch_page(self, index: int):
        self.pages_stack.setCurrentIndex(index)
        # Check corresponding nav button
        btn = self.nav_group.button(index)
        if btn:
            btn.setChecked(True)
            
        # Update header title based on view
        titles = {
            0: "Sandbox Control & Node Registry",
            1: "Virtual Cluster Hardware Simulation",
            2: "Model Partitioning & Distributed Deployment",
            3: "Decentralized Model Inference Console",
            4: "Sandbox Live Service Terminal",
        }
        self.header_lbl.setText(titles.get(index, "CAI Sandbox"))

    def update_status_bar(self, status: str):
        self.footer_lbl.setText(status)
        if self.state_manager.sandbox_active:
            role = self.state_manager.config.role.value.upper()
            self.status_lbl.setText(f"🟢 Control Plane: Active ({role})")
            self.status_lbl.setStyleSheet("color: #14b8a6; font-size: 11px; padding: 0 20px;")
        else:
            self.status_lbl.setText("🔴 Control Plane: Inactive")
            self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 0 20px;")

    def closeEvent(self, event):
        # Shut down sandbox cleanly upon app close
        self.state_manager.stop_sandbox()
        self.state_manager.restore_streams()
        event.accept()
