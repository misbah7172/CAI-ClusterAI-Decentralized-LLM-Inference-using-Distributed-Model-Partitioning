"""
Simulation page for CAI Sandbox Desktop GUI.
Allows spawning virtual hardware workers and monitoring live telemetry.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QSlider, QComboBox, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt6.QtCore import Qt


class SimulationPage(QWidget):
    def __init__(self, state_manager):
        super().__init__()
        self.state_manager = state_manager
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(15)
        
        self.setup_left_panel()
        self.setup_right_panel()
        
        # Connect state manager signals
        self.state_manager.sim_metrics_updated.connect(self.update_simulation_telemetry)

    def setup_left_panel(self):
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Control Settings
        self.sim_settings = QGroupBox("Simulation Settings")
        settings_layout = QVBoxLayout(self.sim_settings)
        settings_layout.setSpacing(12)
        
        # Virtual Workers Slider
        settings_layout.addWidget(QLabel("Number of Virtual Workers:"))
        self.workers_lbl = QLabel("2 Workers")
        self.workers_lbl.setStyleSheet("font-weight: bold; color: #14b8a6;")
        settings_layout.addWidget(self.workers_lbl)
        
        self.workers_slider = QSlider(Qt.Orientation.Horizontal)
        self.workers_slider.setRange(1, 10)
        self.workers_slider.setValue(2)
        self.workers_slider.valueChanged.connect(self.on_slider_changed)
        settings_layout.addWidget(self.workers_slider)
        
        # Mix Strategy
        settings_layout.addWidget(QLabel("Mix Strategy Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["mixed", "gpu", "cpu"])
        settings_layout.addWidget(self.profile_combo)
        
        left_layout.addWidget(self.sim_settings)
        
        # Operations
        self.ops_group = QGroupBox("Simulation Controls")
        ops_layout = QVBoxLayout(self.ops_group)
        
        self.spawn_btn = QPushButton("⚡ Spawn Simulated Workers")
        self.spawn_btn.setObjectName("primaryBtn")
        self.spawn_btn.clicked.connect(self.toggle_simulation)
        ops_layout.addWidget(self.spawn_btn)
        
        self.kill_btn = QPushButton("🛑 Terminate Simulation")
        self.kill_btn.setObjectName("dangerBtn")
        self.kill_btn.setEnabled(False)
        self.kill_btn.clicked.connect(self.toggle_simulation)
        ops_layout.addWidget(self.kill_btn)
        
        left_layout.addWidget(self.ops_group)
        
        # Explanation panel
        info_box = QGroupBox("Virtual Worker Info")
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(QLabel(
            "Virtual workers emulate heterogeneous node profiles "
            "(RTX 4090, Jetson Nano, low-power edge, etc.) "
            "allowing cluster validation on a single workstation."
        ))
        left_layout.addWidget(info_box)
        
        left_layout.addStretch()
        self.layout.addWidget(self.left_panel, 2)

    def setup_right_panel(self):
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("<b>Live Telemetry & Metrics Stream</b>"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Virtual Node ID", "Uptime/Status", "CPU Load", "Power Draw", "GPU Temp"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.table)
        
        self.layout.addWidget(self.right_panel, 5)

    def on_slider_changed(self, value):
        self.workers_lbl.setText(f"{value} Workers")

    def toggle_simulation(self):
        if not self.state_manager.sim_active:
            # Check if sandbox is active
            if not self.state_manager.sandbox_active:
                self.state_manager.status_changed.emit("Error: Start the control plane first")
                return
            
            num_nodes = self.workers_slider.value()
            profile_mix = self.profile_combo.currentText()
            
            success, msg = self.state_manager.start_simulation(num_nodes, profile_mix)
            if success:
                self.sim_settings.setEnabled(False)
                self.spawn_btn.setEnabled(False)
                self.kill_btn.setEnabled(True)
            else:
                self.state_manager.status_changed.emit(f"Simulation launch failed: {msg}")
        else:
            self.state_manager.stop_simulation()
            self.sim_settings.setEnabled(True)
            self.spawn_btn.setEnabled(True)
            self.kill_btn.setEnabled(False)
            self.table.setRowCount(0)

    def update_simulation_telemetry(self, sim_metrics):
        self.table.setRowCount(0)
        for i, metric in enumerate(sim_metrics):
            self.table.insertRow(i)
            
            # Node ID
            self.table.setItem(i, 0, QTableWidgetItem(metric["node_id"]))
            
            # Status
            status_item = QTableWidgetItem(metric["state"])
            status_item.setForeground(Qt.GlobalColor.green if metric["state"] == "active" else Qt.GlobalColor.red)
            self.table.setItem(i, 1, status_item)
            
            # CPU Load (Progress Bar Widget)
            cpu_val = int(metric["cpu_load"])
            cpu_bar = QProgressBar()
            cpu_bar.setRange(0, 100)
            cpu_bar.setValue(cpu_val)
            cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #14b8a6; }")
            self.table.setCellWidget(i, 2, cpu_bar)
            
            # Power Draw
            power_val = f"{metric['power_draw']:.1f} W"
            self.table.setItem(i, 3, QTableWidgetItem(power_val))
            
            # GPU Temp
            temp_val = f"{metric['gpu_temp']:.1f} °C" if metric["gpu_temp"] > 0 else "N/A"
            self.table.setItem(i, 4, QTableWidgetItem(temp_val))
