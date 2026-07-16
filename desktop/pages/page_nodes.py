"""
Nodes control and cluster registry page for CAI Sandbox Desktop GUI.
Allows starting/stopping sandbox agent and viewing active cluster topology.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, 
    QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt


class NodesPage(QWidget):
    def __init__(self, state_manager):
        super().__init__()
        self.state_manager = state_manager
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(15)
        
        self.setup_left_panel()
        self.setup_right_panel()
        
        # Connect signals
        self.state_manager.nodes_updated.connect(self.update_nodes_table)

    def setup_left_panel(self):
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Configuration Group Box
        self.config_group = QGroupBox("Configuration Settings")
        form_layout = QGridLayout(self.config_group)
        form_layout.setSpacing(10)
        
        form_layout.addWidget(QLabel("Cluster Mode:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["single", "multi_primary", "multi_worker"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_or_role_changed)
        form_layout.addWidget(self.mode_combo, 0, 1)
        
        form_layout.addWidget(QLabel("Node Role:"), 1, 0)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["primary", "worker"])
        self.role_combo.currentTextChanged.connect(self.on_mode_or_role_changed)
        form_layout.addWidget(self.role_combo, 1, 1)
        
        form_layout.addWidget(QLabel("Node ID:"), 2, 0)
        self.node_id_input = QLineEdit("desktop-primary-node")
        form_layout.addWidget(self.node_id_input, 2, 1)
        
        form_layout.addWidget(QLabel("gRPC Control Port:"), 3, 0)
        self.grpc_port_input = QSpinBox()
        self.grpc_port_input.setRange(1024, 65535)
        self.grpc_port_input.setValue(50100)
        form_layout.addWidget(self.grpc_port_input, 3, 1)
        
        form_layout.addWidget(QLabel("Controller API Port:"), 4, 0)
        self.api_port_input = QSpinBox()
        self.api_port_input.setRange(1024, 65535)
        self.api_port_input.setValue(8200)
        form_layout.addWidget(self.api_port_input, 4, 1)
        
        # Worker Join Inputs (hidden by default unless role is worker)
        self.primary_addr_label = QLabel("Primary Node Address:")
        self.primary_addr_input = QLineEdit()
        self.primary_addr_input.setPlaceholderText("e.g. 192.168.1.100:50100")
        
        self.token_label = QLabel("Join Access Token:")
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addWidget(self.primary_addr_label, 5, 0)
        form_layout.addWidget(self.primary_addr_input, 5, 1)
        form_layout.addWidget(self.token_label, 6, 0)
        form_layout.addWidget(self.token_input, 6, 1)
        
        self.set_worker_inputs_visible(False)
        
        left_layout.addWidget(self.config_group)
        
        # Launch Group Box
        self.launch_group = QGroupBox("Launch Panel")
        launch_layout = QVBoxLayout(self.launch_group)
        
        self.start_btn = QPushButton("🚀 Launch Sandbox Control Plane")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self.toggle_sandbox)
        launch_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("🛑 Stop Sandbox Services")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.toggle_sandbox)
        launch_layout.addWidget(self.stop_btn)
        
        left_layout.addWidget(self.launch_group)
        
        # Access Info Box
        self.token_group = QGroupBox("Worker Connection Access")
        token_layout = QVBoxLayout(self.token_group)
        self.token_display = QLineEdit()
        self.token_display.setReadOnly(True)
        self.token_display.setPlaceholderText("Join token will appear here once started")
        token_layout.addWidget(QLabel("Provide this token for remote workers to join:"))
        token_layout.addWidget(self.token_display)
        
        left_layout.addWidget(self.token_group)
        left_layout.addStretch()
        
        self.layout.addWidget(self.left_panel, 2)

    def setup_right_panel(self):
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("<b>Registered Cluster Nodes</b>"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Node ID", "Role", "Address", "State", "Uptime", "GPU Type", "VRAM", "RAM", "CPU"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.table)
        
        self.layout.addWidget(self.right_panel, 5)

    def on_mode_or_role_changed(self):
        mode = self.mode_combo.currentText()
        role = self.role_combo.currentText()
        
        if role == "worker":
            self.set_worker_inputs_visible(True)
            self.node_id_input.setText("desktop-worker-node")
        else:
            self.set_worker_inputs_visible(False)
            self.node_id_input.setText("desktop-primary-node")

    def set_worker_inputs_visible(self, visible):
        self.primary_addr_label.setVisible(visible)
        self.primary_addr_input.setVisible(visible)
        self.token_label.setVisible(visible)
        self.token_input.setVisible(visible)

    def toggle_sandbox(self):
        if not self.state_manager.sandbox_active:
            # Start
            mode = self.mode_combo.currentText()
            role = self.role_combo.currentText()
            node_id = self.node_id_input.text()
            grpc_port = self.grpc_port_input.value()
            api_port = self.api_port_input.value()
            primary_addr = self.primary_addr_input.text()
            token = self.token_input.text()
            
            success, msg = self.state_manager.start_sandbox(
                mode=mode,
                role=role,
                node_id=node_id,
                grpc_port=grpc_port,
                api_port=api_port,
                primary_address=primary_addr,
                access_token=token
            )
            
            if success:
                self.config_group.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                if self.state_manager.join_token:
                    self.token_display.setText(self.state_manager.join_token)
            else:
                self.token_display.setText(f"Error: {msg}")
        else:
            # Stop
            self.state_manager.stop_sandbox()
            self.config_group.setEnabled(True)
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.token_display.clear()
            self.table.setRowCount(0)

    def update_nodes_table(self, nodes):
        self.table.setRowCount(0)
        for i, node in enumerate(nodes):
            self.table.insertRow(i)
            
            # Format row data
            uptime = f"{node.get('uptime_s', 0)}s" if node.get("uptime_s") else "N/A"
            vram = f"{node.get('gpu_vram_mb', 0):.0f} MB"
            ram = f"{node.get('ram_mb', 0) / 1024:.1f} GB"
            cpu = f"{node.get('cpu_cores', 0)} Cores"
            
            row_items = [
                node.get("node_id", ""),
                node.get("role", "worker"),
                node.get("address", ""),
                node.get("state", "active"),
                uptime,
                node.get("gpu_type", "None"),
                vram,
                ram,
                cpu
            ]
            
            for j, val in enumerate(row_items):
                item = QTableWidgetItem(str(val))
                if j == 0 and node.get("is_self"):
                    item.setText(f"{val} (Local)")
                    item.setForeground(Qt.GlobalColor.cyan)
                self.table.setItem(i, j, item)
