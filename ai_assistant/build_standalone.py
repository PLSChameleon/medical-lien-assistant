"""
Build standalone executable for Medical Lien Assistant
This creates a single executable that includes Python and all dependencies
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller if not present"""
    try:
        import PyInstaller
        print("✓ PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")

def create_spec_file():
    """Create PyInstaller spec file with all necessary configurations"""
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None

# Get the absolute path to the ai_assistant directory
app_path = Path(r'c:\\devops-copy\\ai_assistant').resolve()

a = Analysis(
    ['multi_user_launcher.py'],
    pathex=[str(app_path)],
    binaries=[],
    datas=[
        ('credentials.json', '.'),
        ('*.py', '.'),
        ('logs', 'logs'),
    ],
    hiddenimports=[
        'openai',
        'dotenv',
        'google.auth',
        'google.auth.transport.requests',
        'google.oauth2',
        'google.oauth2.credentials',
        'googleapiclient',
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'pandas',
        'openpyxl',
        'email_validator',
        'requests',
        'pytz',
        'playwright',
        'playwright.sync_api',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'cryptography',
        'cryptography.fernet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MedicalLienAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)
"""
    
    with open('medical_lien_assistant.spec', 'w') as f:
        f.write(spec_content)
    print("✓ Created PyInstaller spec file")

def build_executable():
    """Build the standalone executable"""
    print("\nBuilding standalone executable...")
    print("This may take several minutes on first run...\n")
    
    try:
        # Run PyInstaller
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--clean",  # Clean PyInstaller cache
            "--onefile",  # Create single executable
            "--windowed",  # No console window
            "--name", "MedicalLienAssistant",
            "--add-data", "credentials.json;.",
            "--hidden-import", "openai",
            "--hidden-import", "dotenv",
            "--hidden-import", "google.auth",
            "--hidden-import", "googleapiclient",
            "--hidden-import", "pandas",
            "--hidden-import", "playwright",
            "--hidden-import", "PyQt5",
            "--hidden-import", "cryptography",
            "multi_user_launcher.py"
        ])
        
        print("\n✓ Executable built successfully!")
        print(f"  Location: {Path('dist/MedicalLienAssistant.exe').resolve()}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)

def create_installer_script():
    """Create a simple installer batch script"""
    installer_content = """@echo off
title Medical Lien Assistant Installer
color 0A

echo ========================================
echo  Medical Lien Assistant - Installation
echo ========================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This installer requires administrator privileges.
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Set installation directory
set "INSTALL_DIR=%ProgramFiles%\\Medical Lien Assistant"
set "DESKTOP=%USERPROFILE%\\Desktop"
set "START_MENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs"

echo Installation directory: %INSTALL_DIR%
echo.

:: Create installation directory
echo Creating installation directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy executable
echo Installing application...
copy /Y "MedicalLienAssistant.exe" "%INSTALL_DIR%\\" >nul
if exist "credentials.json" copy /Y "credentials.json" "%INSTALL_DIR%\\" >nul

:: Create desktop shortcut
echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\\Medical Lien Assistant.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\MedicalLienAssistant.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\MedicalLienAssistant.exe'; $Shortcut.Save()"

:: Create Start Menu shortcut
echo Creating Start Menu entry...
if not exist "%START_MENU%\\Medical Lien Assistant" mkdir "%START_MENU%\\Medical Lien Assistant"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_MENU%\\Medical Lien Assistant\\Medical Lien Assistant.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\MedicalLienAssistant.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\MedicalLienAssistant.exe'; $Shortcut.Save()"

:: Install Playwright browsers (required for CMS automation)
echo.
echo Installing browser components for CMS automation...
echo This may take a few minutes on first installation...
cd "%INSTALL_DIR%"
"%INSTALL_DIR%\\MedicalLienAssistant.exe" --install-browsers 2>nul

echo.
echo ========================================
echo  Installation Complete!
echo ========================================
echo.
echo Medical Lien Assistant has been installed successfully.
echo.
echo Shortcuts created:
echo  - Desktop: Medical Lien Assistant
echo  - Start Menu: Medical Lien Assistant
echo.
echo You can now run the application from your desktop or Start Menu.
echo.
pause
"""
    
    with open('dist/Install_Medical_Lien_Assistant.bat', 'w') as f:
        f.write(installer_content)
    print("✓ Created installer script")

def create_portable_package():
    """Create a portable ZIP package that can be run without installation"""
    print("\nCreating portable package...")
    
    # Create portable directory
    portable_dir = Path('dist/MedicalLienAssistant_Portable')
    portable_dir.mkdir(exist_ok=True)
    
    # Copy executable and required files
    shutil.copy2('dist/MedicalLienAssistant.exe', portable_dir)
    if Path('credentials.json').exists():
        shutil.copy2('credentials.json', portable_dir)
    
    # Create run script for portable version
    run_script = """@echo off
title Medical Lien Assistant - Portable
echo Starting Medical Lien Assistant (Portable Version)...
echo.
echo First time setup may take a few moments...
start "" "%~dp0MedicalLienAssistant.exe"
"""
    
    with open(portable_dir / 'Run_Medical_Lien_Assistant.bat', 'w') as f:
        f.write(run_script)
    
    # Create README for portable version
    readme = """Medical Lien Assistant - Portable Version
=========================================

This is a portable version that runs without installation.

To use:
1. Extract this folder to any location (e.g., Desktop, USB drive)
2. Double-click "Run_Medical_Lien_Assistant.bat"
3. Complete the one-time setup wizard

No Python installation required!
All dependencies are included in the executable.

First-time setup:
- You'll be prompted to authenticate with Gmail
- Enter your CMS credentials
- These will be saved securely for future use

Files in this package:
- MedicalLienAssistant.exe - Main application
- Run_Medical_Lien_Assistant.bat - Launch script
- credentials.json - Gmail API configuration
"""
    
    with open(portable_dir / 'README.txt', 'w') as f:
        f.write(readme)
    
    # Create ZIP archive
    shutil.make_archive('dist/MedicalLienAssistant_Portable', 'zip', portable_dir)
    print(f"✓ Created portable package: dist/MedicalLienAssistant_Portable.zip")

def main():
    """Main build process"""
    print("=" * 50)
    print("Medical Lien Assistant - Standalone Build")
    print("=" * 50)
    
    # Change to ai_assistant directory
    os.chdir(Path(__file__).parent)
    
    # Step 1: Install PyInstaller
    install_pyinstaller()
    
    # Step 2: Build executable
    build_executable()
    
    # Step 3: Create installer
    create_installer_script()
    
    # Step 4: Create portable package
    create_portable_package()
    
    print("\n" + "=" * 50)
    print("Build Complete!")
    print("=" * 50)
    print("\nCreated:")
    print("1. Standalone executable: dist/MedicalLienAssistant.exe")
    print("2. Installer: dist/Install_Medical_Lien_Assistant.bat")
    print("3. Portable package: dist/MedicalLienAssistant_Portable.zip")
    print("\nDistribution options:")
    print("- Send the installer for permanent installation")
    print("- Send the portable ZIP for no-install usage")
    print("\nUsers DO NOT need Python installed!")

if __name__ == "__main__":
    main()