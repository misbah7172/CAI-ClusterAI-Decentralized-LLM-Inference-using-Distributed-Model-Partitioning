"""
Root-level entry point for the CAI Sandbox Desktop GUI.
This resolves PyInstaller import mapping issues by using the root directory as the package anchor.
"""

import os
import sys

# Support PyInstaller runtime directory
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _PROJECT_ROOT = sys._MEIPASS
else:
    _PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from desktop.main import main

if __name__ == "__main__":
    main()
