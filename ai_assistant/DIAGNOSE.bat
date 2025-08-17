@echo off
title Medical Lien Assistant - Diagnostic Tool
color 0E
cls

echo =====================================
echo  MEDICAL LIEN ASSISTANT - DIAGNOSTICS
echo =====================================
echo.
echo This will check your installation...
echo.

:: Check Python
echo [1] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo     [OK] Python is installed:
    python --version
) else (
    echo     [ERROR] Python is NOT installed
    echo     Run INSTALL_COMPLETE.bat to install Python
)
echo.

:: Check pip
echo [2] Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo     [OK] pip is installed
) else (
    echo     [ERROR] pip is NOT installed
)
echo.

:: Check critical packages
echo [3] Checking required packages...
echo.

:: Create a Python script to check all packages
echo import sys > check_packages.py
echo import importlib >> check_packages.py
echo packages = { >> check_packages.py
echo     'cryptography': 'Security/Encryption', >> check_packages.py
echo     'openai': 'AI Services', >> check_packages.py
echo     'pandas': 'Data Processing', >> check_packages.py
echo     'PyQt5': 'User Interface', >> check_packages.py
echo     'google.auth': 'Google Authentication', >> check_packages.py
echo     'googleapiclient': 'Gmail API', >> check_packages.py
echo     'openpyxl': 'Excel Support', >> check_packages.py
echo     'dotenv': 'Configuration', >> check_packages.py
echo     'playwright': 'Web Automation', >> check_packages.py
echo } >> check_packages.py
echo missing = [] >> check_packages.py
echo for package, description in packages.items(): >> check_packages.py
echo     try: >> check_packages.py
echo         if package == 'google.auth': >> check_packages.py
echo             import google.auth >> check_packages.py
echo         elif package == 'googleapiclient': >> check_packages.py
echo             import googleapiclient >> check_packages.py
echo         elif package == 'dotenv': >> check_packages.py
echo             import dotenv >> check_packages.py
echo         else: >> check_packages.py
echo             importlib.import_module(package) >> check_packages.py
echo         print(f'     [OK] {description} ({package})') >> check_packages.py
echo     except ImportError: >> check_packages.py
echo         print(f'     [MISSING] {description} ({package})') >> check_packages.py
echo         missing.append(package) >> check_packages.py
echo if missing: >> check_packages.py
echo     print('\nMissing packages:', ', '.join(missing)) >> check_packages.py
echo     sys.exit(1) >> check_packages.py

python check_packages.py
if %errorlevel% neq 0 (
    echo.
    echo     Some packages are missing!
    echo     Run INSTALL_COMPLETE.bat to install them
)

:: Clean up temp file
del check_packages.py >nul 2>&1

echo.
echo [4] Checking Gmail setup...
echo.

if exist "credentials.json" (
    echo     [OK] credentials.json found
) else (
    echo     [ERROR] credentials.json MISSING
    echo            This file is required for Gmail access
    echo            Contact your administrator for this file
)

if exist "token.json" (
    echo     [OK] Gmail already authenticated
) else (
    echo     [INFO] Gmail not authenticated yet
    echo            Authentication will happen on first run
)

echo.
echo [5] Checking program files...
echo.

set MISSING_FILES=0

if exist "multi_user_launcher.py" (
    echo     [OK] Launcher found
) else (
    echo     [ERROR] multi_user_launcher.py MISSING
    set MISSING_FILES=1
)

if exist "enhanced_gui_app.py" (
    echo     [OK] Main application found
) else (
    echo     [ERROR] enhanced_gui_app.py MISSING
    set MISSING_FILES=1
)

if exist "services\gmail_service.py" (
    echo     [OK] Services folder found
) else (
    echo     [ERROR] Services folder MISSING
    set MISSING_FILES=1
)

if exist "data" (
    echo     [OK] Data folder found
) else (
    echo     [WARNING] Data folder missing (will be created on first run)
    mkdir data 2>nul
)

echo.
echo [6] Checking desktop shortcut...
if exist "%USERPROFILE%\Desktop\Medical Lien Assistant.lnk" (
    echo     [OK] Desktop shortcut exists
) else (
    echo     [INFO] No desktop shortcut found
    echo     Run INSTALL_COMPLETE.bat to create one
)

echo.
echo =====================================
echo  DIAGNOSTIC SUMMARY
echo =====================================
echo.

if %MISSING_FILES% equ 1 (
    color 0C
    echo STATUS: INCOMPLETE INSTALLATION
    echo.
    echo Some program files are missing!
    echo Make sure you copied ALL files from the USB drive.
) else (
    python -c "import cryptography, PyQt5, pandas, openai" >nul 2>&1
    if %errorlevel% equ 0 (
        color 0A
        echo STATUS: READY TO RUN
        echo.
        echo Everything looks good!
        echo You can run START_PROGRAM.bat
    ) else (
        color 0E
        echo STATUS: PACKAGES MISSING
        echo.
        echo Program files are present but some packages need to be installed.
        echo Run INSTALL_COMPLETE.bat to install missing packages.
    )
)

echo.
echo =====================================
echo.
echo Press any key to exit...
pause >nul