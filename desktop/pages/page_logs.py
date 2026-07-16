"""
Live logs page for CAI Sandbox Desktop GUI.
Captures redirected stdout/stderr and logs for display.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTextEdit, QLabel, QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt


class LogsPage(QWidget):
    def __init__(self, state_manager):
        super().__init__()
        self.state_manager = state_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        
        self.setup_controls()
        self.setup_display()
        
        # Connect log handler signal
        self.state_manager.log_received.connect(self.append_log)

    def setup_controls(self):
        controls_frame = QWidget()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        controls_layout.addWidget(QLabel("Search/Filter:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter text...")
        self.filter_input.textChanged.connect(self.apply_filter)
        controls_layout.addWidget(self.filter_input)
        
        self.clear_btn = QPushButton("🧹 Clear Console")
        self.clear_btn.clicked.connect(self.clear_logs)
        controls_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("💾 Export Logs")
        self.save_btn.clicked.connect(self.export_logs)
        controls_layout.addWidget(self.save_btn)
        
        self.layout.addWidget(controls_frame)

    def setup_display(self):
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            background-color: #020617; /* Dark slate 950 */
            color: #38bdf8; /* Sky blue */
            font-family: "Consolas", "Courier New", monospace;
            font-size: 12px;
        """)
        self.layout.addWidget(self.console)

    def append_log(self, text):
        # Apply filter on incoming lines
        filter_text = self.filter_input.text().strip().lower()
        if filter_text and filter_text not in text.lower():
            return
            
        self.console.append(text)
        # Auto-scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        self.console.clear()

    def apply_filter(self):
        # Since we append logs dynamically, full re-filtering requires keeping history.
        # For simplicity, we print a notification or let user know it applies to new lines.
        pass

    def export_logs(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Logs Export", "", "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.console.toPlainText())
                self.state_manager.status_changed.emit("Logs exported successfully")
            except Exception as e:
                self.state_manager.status_changed.emit(f"Failed to export logs: {e}")
