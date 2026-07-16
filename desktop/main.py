"""
Main entry point for the CAI Sandbox Desktop Application.
Initializes PyQt6 app, sets up styling, and launches MainWindow.
"""

import os
import sys

# Support PyInstaller runtime directory
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _PROJECT_ROOT = sys._MEIPASS
else:
    _PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


from PyQt6.QtWidgets import QApplication
from desktop.app import CAIWindow

def main():
    app = QApplication(sys.argv)
    
    # Modern dark stylesheet with glassmorphism touches and deep teal accents
    app.setStyleSheet("""
        QMainWindow {
            background-color: #0f172a; /* Slate 900 */
        }
        QWidget {
            color: #f8fafc; /* Slate 50 */
            font-family: "Outfit", "Segoe UI", sans-serif;
            font-size: 13px;
        }
        QFrame#sidebar {
            background-color: #020617; /* Slate 950 */
            border-right: 1px solid #1e293b;
        }
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            outline: none;
        }
        QPushButton:hover {
            background-color: #334155;
            border-color: #475569;
        }
        QPushButton:pressed {
            background-color: #0f172a;
        }
        QPushButton#primaryBtn {
            background-color: #0d9488; /* Teal 600 */
            border: 1px solid #0f766e;
        }
        QPushButton#primaryBtn:hover {
            background-color: #14b8a6; /* Teal 500 */
        }
        QPushButton#primaryBtn:pressed {
            background-color: #0f766e;
        }
        QPushButton#dangerBtn {
            background-color: #e11d48; /* Rose 600 */
            border: 1px solid #be123c;
        }
        QPushButton#dangerBtn:hover {
            background-color: #f43f5e; /* Rose 500 */
        }
        QPushButton#dangerBtn:pressed {
            background-color: #be123c;
        }
        QPushButton#navBtn {
            background-color: transparent;
            border: none;
            text-align: left;
            padding: 12px 20px;
            border-radius: 0px;
            font-size: 14px;
        }
        QPushButton#navBtn:hover {
            background-color: #1e293b;
        }
        QPushButton#navBtn:checked {
            background-color: #0f766e;
            border-left: 4px solid #14b8a6;
            font-weight: bold;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 6px 10px;
            color: #ffffff;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
            border-color: #14b8a6;
        }
        QGroupBox {
            border: 1px solid #1e293b;
            border-radius: 8px;
            margin-top: 15px;
            font-weight: bold;
            padding-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            color: #14b8a6;
        }
        QTableWidget {
            background-color: #0b0f19;
            border: 1px solid #1e293b;
            border-radius: 6px;
            gridline-color: #1e293b;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QHeaderView::section {
            background-color: #1e293b;
            color: #94a3b8;
            padding: 6px;
            border: 1px solid #0f172a;
            font-weight: bold;
        }
        QProgressBar {
            border: 1px solid #1e293b;
            background-color: #0b0f19;
            text-align: center;
            border-radius: 4px;
        }
        QProgressBar::chunk {
            background-color: #14b8a6;
        }
        QScrollBar:vertical {
            border: none;
            background: #020617;
            width: 8px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #334155;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)
    
    window = CAIWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
