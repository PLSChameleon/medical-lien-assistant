#!/usr/bin/env python3
"""
Simple launcher for the enhanced GUI app with seamless Gmail authentication.
This bypasses the multi-user system for a cleaner single-user experience.
"""

import sys
import os
from pathlib import Path
import traceback

# Add the parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Check if all required dependencies are installed."""
    missing = []
    
    try:
        import PyQt5
    except ImportError:
        missing.append("PyQt5")
    
    try:
        import openai
    except ImportError:
        missing.append("openai")
    
    try:
        import pandas
    except ImportError:
        missing.append("pandas")
    
    try:
        import googleapiclient
    except ImportError:
        missing.append("google-api-python-client")
    
    return missing

def main():
    """Launch the enhanced GUI app directly."""
    try:
        # Check dependencies first
        missing = check_dependencies()
        if missing:
            print("=" * 50)
            print("ERROR: Missing Required Packages")
            print("=" * 50)
            print(f"\nThe following packages are not installed:")
            for package in missing:
                print(f"  - {package}")
            print("\nTo fix this, please run:")
            print("  INSTALL_SIMPLE.bat")
            print("\nOr manually install with:")
            print(f"  python -m pip install {' '.join(missing)}")
            print("=" * 50)
            input("\nPress Enter to exit...")
            sys.exit(1)
        
        # Try to import the main application
        try:
            from enhanced_gui_app import EnhancedMainWindow
            from qt_compat import QApplication
        except ImportError as e:
            print("=" * 50)
            print("ERROR: Application Files Missing")
            print("=" * 50)
            print(f"\nCould not import application modules: {e}")
            print("\nPlease ensure all files are present:")
            print("  - enhanced_gui_app.py")
            print("  - qt_compat.py")
            print("  - All files in the services/ folder")
            print("=" * 50)
            input("\nPress Enter to exit...")
            sys.exit(1)
        
        # Create the application
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        app.setApplicationName("Medical Lien Assistant")
        app.setOrganizationName("ProHealth Advanced Imaging")
        
        # Create and show the main window
        try:
            window = EnhancedMainWindow()
            window.show()
        except Exception as e:
            print("=" * 50)
            print("ERROR: Failed to Create Main Window")
            print("=" * 50)
            print(f"\nError details: {e}")
            print("\nThis might be due to:")
            print("  1. Missing configuration files")
            print("  2. Corrupted data files")
            print("  3. Permission issues")
            print("\nTry running INSTALL_SIMPLE.bat as administrator")
            print("=" * 50)
            traceback.print_exc()
            input("\nPress Enter to exit...")
            sys.exit(1)
        
        # Run the application
        sys.exit(app.exec_())
        
    except Exception as e:
        print("=" * 50)
        print("ERROR: Unexpected Error")
        print("=" * 50)
        print(f"\nAn unexpected error occurred: {e}")
        print("\nFull error details:")
        traceback.print_exc()
        print("\nPlease try:")
        print("  1. Run INSTALL_SIMPLE.bat")
        print("  2. Restart your computer")
        print("  3. Contact support if the issue persists")
        print("=" * 50)
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()