"""
Model placement and partitioning deployment page for CAI Sandbox Desktop GUI.
Allows chunk allocation and layout mapping across active nodes.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QComboBox, QSpinBox, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt


class DeployPage(QWidget):
    def __init__(self, state_manager):
        super().__init__()
        self.state_manager = state_manager
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(15)
        
        self.setup_left_panel()
        self.setup_right_panel()

    def setup_left_panel(self):
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Partition Settings Box
        settings_box = QGroupBox("Deployment Layout")
        form_layout = QVBoxLayout(settings_box)
        form_layout.setSpacing(10)
        
        # Models
        form_layout.addWidget(QLabel("Target Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "microsoft/phi-2",
            "openai-community/gpt2",
            "google/gemma-2b",
            "tiiuae/falcon-7b",
            "mistralai/Mistral-7B-v0.1"
        ])
        form_layout.addWidget(self.model_combo)
        
        # Strategy
        form_layout.addWidget(QLabel("Placement Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["balanced", "energy", "latency"])
        form_layout.addWidget(self.strategy_combo)
        
        # Chunks Count
        form_layout.addWidget(QLabel("Number of Partitions (Chunks):"))
        self.chunks_spin = QSpinBox()
        self.chunks_spin.setRange(1, 12)
        self.chunks_spin.setValue(2)
        form_layout.addWidget(self.chunks_spin)
        
        left_layout.addWidget(settings_box)
        
        # Action Buttons
        self.deploy_btn = QPushButton("🚀 Partition & Deploy to Cluster")
        self.deploy_btn.setObjectName("primaryBtn")
        self.deploy_btn.clicked.connect(self.deploy_model)
        left_layout.addWidget(self.deploy_btn)
        
        left_layout.addStretch()
        self.layout.addWidget(self.left_panel, 2)

    def setup_right_panel(self):
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("<b>Cluster Partition Placements</b>"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Deployment ID", "Chunk ID", "Target Node ID", "Inference Endpoint"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.table)
        
        self.layout.addWidget(self.right_panel, 5)

    def deploy_model(self):
        if not self.state_manager.sandbox_active:
            self.state_manager.status_changed.emit("Error: Start the control plane first")
            return
            
        model = self.model_combo.currentText()
        strategy = self.strategy_combo.currentText()
        chunks = self.chunks_spin.value()
        
        success, res = self.state_manager.deploy_model(model, chunks, strategy)
        if success:
            self.state_manager.status_changed.emit(f"Model {model} deployed successfully!")
            self.update_placements_table()
        else:
            self.state_manager.status_changed.emit(f"Deployment failed: {res}")

    def update_placements_table(self):
        self.table.setRowCount(0)
        row_idx = 0
        for dep in self.state_manager.deployments:
            dep_id = dep["deployment_id"]
            for p in dep["placements"]:
                self.table.insertRow(row_idx)
                self.table.setItem(row_idx, 0, QTableWidgetItem(dep_id))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(p.get("chunk_id", ""))))
                self.table.setItem(row_idx, 2, QTableWidgetItem(p.get("node_id", "")))
                self.table.setItem(row_idx, 3, QTableWidgetItem(p.get("endpoint", "initializing")))
                row_idx += 1
