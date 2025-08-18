#!/usr/bin/env python3
"""Test script to debug GUI window creation"""

import sys
import os
from pathlib import Path

# Add the parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("Test script starting...", flush=True)

try:
    print("Importing Qt...", flush=True)
    from qt_compat import QApplication, QMainWindow
    
    print("Creating QApplication...", flush=True)
    app = QApplication(sys.argv)
    
    print("Creating basic window...", flush=True)
    window = QMainWindow()
    window.setWindowTitle("Test Window")
    window.setGeometry(100, 100, 800, 600)
    
    print("Showing window...", flush=True)
    window.show()
    
    print("Starting event loop...", flush=True)
    sys.exit(app.exec_())
    
except Exception as e:
    print(f"Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")