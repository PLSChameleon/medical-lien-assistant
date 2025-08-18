#!/usr/bin/env python3
"""
Simple launcher for the enhanced GUI app with seamless Gmail authentication.
This bypasses the multi-user system for a cleaner single-user experience.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Launch the enhanced GUI app directly."""
    try:
        print("Starting launcher...")
        # Import and run the enhanced GUI app
        from enhanced_gui_app import EnhancedMainWindow
        from qt_compat import QApplication
        
        print("Creating QApplication...")
        # Create the application
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        print("Creating main window...")
        # Create and show the main window
        window = EnhancedMainWindow()
        
        print("Showing window...")
        window.show()
        
        print("Starting event loop...")
        # Run the application
        sys.exit(app.exec_())
        
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("\nPlease run INSTALL_COMPLETE.bat to install all required packages.")
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching application: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()