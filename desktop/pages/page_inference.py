"""
Distributed inference prompt console for CAI Sandbox Desktop GUI.
Provides custom prompt entries and response telemetry displays.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QSlider, QPushButton, QTextEdit, QLineEdit
)
from PyQt6.QtCore import Qt


class InferencePage(QWidget):
    def __init__(self, state_manager):
        super().__init__()
        self.state_manager = state_manager
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(15)
        
        self.setup_left_panel()
        self.setup_right_panel()
        
        # Connect inference callback signals
        self.state_manager.inference_completed.connect(self.display_inference_result)

    def setup_left_panel(self):
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Parameters Settings Box
        params_box = QGroupBox("Inference Tunings")
        form_layout = QVBoxLayout(params_box)
        form_layout.setSpacing(10)
        
        # Max Tokens Slider
        form_layout.addWidget(QLabel("Max Tokens:"))
        self.tokens_lbl = QLabel("30 Tokens")
        self.tokens_lbl.setStyleSheet("font-weight: bold; color: #14b8a6;")
        form_layout.addWidget(self.tokens_lbl)
        
        self.tokens_slider = QSlider(Qt.Orientation.Horizontal)
        self.tokens_slider.setRange(5, 500)
        self.tokens_slider.setValue(30)
        self.tokens_slider.valueChanged.connect(self.on_tokens_changed)
        form_layout.addWidget(self.tokens_slider)
        
        # Temperature Slider
        form_layout.addWidget(QLabel("Temperature:"))
        self.temp_lbl = QLabel("0.70")
        self.temp_lbl.setStyleSheet("font-weight: bold; color: #14b8a6;")
        form_layout.addWidget(self.temp_lbl)
        
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 150) # scaled 0.0 - 1.5
        self.temp_slider.setValue(70)
        self.temp_slider.valueChanged.connect(self.on_temp_changed)
        form_layout.addWidget(self.temp_slider)
        
        left_layout.addWidget(params_box)
        
        # Inference Telemetry stats
        self.stats_group = QGroupBox("Performance Statistics")
        stats_layout = QVBoxLayout(self.stats_group)
        self.tps_lbl = QLabel("Throughput: N/A")
        self.latency_lbl = QLabel("Latency: N/A")
        self.count_lbl = QLabel("Tokens Generated: N/A")
        stats_layout.addWidget(self.tps_lbl)
        stats_layout.addWidget(self.latency_lbl)
        stats_layout.addWidget(self.count_lbl)
        left_layout.addWidget(self.stats_group)
        
        left_layout.addStretch()
        self.layout.addWidget(self.left_panel, 2)

    def setup_right_panel(self):
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Prompt Entry
        right_layout.addWidget(QLabel("<b>Input Prompt:</b>"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Type prompt here... e.g. 'Kubernetes AI scheduling optimization is...'")
        self.prompt_input.setMaximumHeight(120)
        right_layout.addWidget(self.prompt_input)
        
        # Trigger button
        self.run_btn = QPushButton("🔮 Trigger Distributed Text Generation")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.clicked.connect(self.run_inference)
        right_layout.addWidget(self.run_btn)
        
        # Response Window
        right_layout.addWidget(QLabel("<b>Generated Response Output:</b>"))
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        right_layout.addWidget(self.output_display)
        
        self.layout.addWidget(self.right_panel, 5)

    def on_tokens_changed(self, val):
        self.tokens_lbl.setText(f"{val} Tokens")

    def on_temp_changed(self, val):
        self.temp_lbl.setText(f"{val / 100:.2f}")

    def run_inference(self):
        if not self.state_manager.sandbox_active:
            self.state_manager.status_changed.emit("Error: Sandbox Control Plane inactive")
            return
            
        if not self.state_manager.deployments:
            self.state_manager.status_changed.emit("Error: No active deployment. Deploy a model first.")
            return
            
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.state_manager.status_changed.emit("Error: Prompt cannot be empty")
            return
            
        target_model = self.state_manager.deployments[-1]["model_name"]
        max_tokens = self.tokens_slider.value()
        temp = self.temp_slider.value() / 100.0
        
        self.run_btn.setEnabled(False)
        self.output_display.setText("Generating tokens in cluster, please wait...")
        
        self.state_manager.trigger_inference(target_model, prompt, max_tokens, temp)

    def display_inference_result(self, success, text, metrics):
        self.run_btn.setEnabled(True)
        if success:
            self.output_display.setText(text)
            self.tps_lbl.setText(f"Throughput: {metrics.get('tps', 0.0):.2f} Tok/s")
            self.latency_lbl.setText(f"Latency: {metrics.get('time_taken', 0.0):.2f} s")
            self.count_lbl.setText(f"Tokens Generated: {metrics.get('tokens_generated', 0)}")
        else:
            self.output_display.setText(f"Inference Failure: {text}")
            self.tps_lbl.setText("Throughput: Error")
            self.latency_lbl.setText("Latency: Error")
            self.count_lbl.setText("Tokens Generated: Error")
