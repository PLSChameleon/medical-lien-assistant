@echo off
title Medical Lien Assistant - Installation Check
color 0B
cls

echo =====================================
echo  INSTALLATION STATUS CHECK
echo =====================================
echo.
echo Checking your installation...
echo.

set "ERRORS=0"
set "WARNINGS=0"

:: Check Python
echo [1/6] Checking Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo       [OK] Python is installed
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo       Version: %%i
) else (
    echo       [ERROR] Python is NOT installed
    echo       Run INSTALL_SIMPLE.bat to fix this
    set /a ERRORS+=1
)
echo.

:: Check pip
echo [2/6] Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo       [OK] pip is installed
) else (
    echo       [WARNING] pip not found
    set /a WARNINGS+=1
)
echo.

:: Check required Python packages
echo [3/6] Checking required packages...
set "MISSING_PACKAGES="

python -c "import openai" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] openai
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] pandas
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] PyQt5
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import google.auth" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] google-auth
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] playwright
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

if not defined MISSING_PACKAGES (
    echo       [OK] All required packages installed
)
echo.

:: Check program files
echo [4/6] Checking program files...
set "MISSING_FILES="

if not exist "multi_user_launcher.py" (
    echo       [MISSING] multi_user_launcher.py
    set "MISSING_FILES=1"
    set /a ERRORS+=1
)

if not exist "enhanced_gui_app.py" (
    echo       [MISSING] enhanced_gui_app.py
    set "MISSING_FILES=1"
    set /a ERRORS+=1
)

if not exist "services\gmail_service.py" (
    echo       [MISSING] services\gmail_service.py
    set "MISSING_FILES=1"
    set /a ERRORS+=1
)

if not exist "config.py" (
    echo       [MISSING] config.py
    set "MISSING_FILES=1"
    set /a ERRORS+=1
)

if not defined MISSING_FILES (
    echo       [OK] All program files found
)
echo.

:: Check configuration files
echo [5/6] Checking configuration...
set "CONFIG_ISSUES="

if not exist "credentials.json" (
    echo       [INFO] credentials.json not found
    echo              This file is needed for Gmail
    echo              Your admin will provide this file
    set /a WARNINGS+=1
    set "CONFIG_ISSUES=1"
)

if exist "token.json" (
    echo       [OK] Gmail token found (already authenticated)
) else (
    echo       [INFO] Gmail not yet authenticated
    echo              You'll set this up on first run
    set "CONFIG_ISSUES=1"
)

if not defined CONFIG_ISSUES (
    echo       [OK] Configuration looks good
)
echo.

:: Check shortcuts
echo [6/6] Checking shortcuts...
if exist "%USERPROFILE%\Desktop\Medical Lien Assistant.lnk" (
    echo       [OK] Desktop shortcut exists
) else (
    echo       [INFO] No desktop shortcut
    echo              Run INSTALL_SIMPLE.bat to create
)
echo.

:: Summary
echo =====================================
echo  SUMMARY
echo =====================================
echo.

if %ERRORS% equ 0 (
    if %WARNINGS% equ 0 (
        color 0A
        echo STATUS: READY TO USE!
        echo.
        echo Everything looks good!
        echo You can start the program now.
    ) else (
        color 0E
        echo STATUS: READY (with minor issues)
        echo.
        echo The program should work, but you have %WARNINGS% warning(s).
        echo Run INSTALL_SIMPLE.bat to fix any issues.
    )
) else (
    color 0C
    echo STATUS: NOT READY
    echo.
    echo Found %ERRORS% critical error(s).
    echo Please run INSTALL_SIMPLE.bat to fix issues.
)

echo.
echo =====================================
echo.
echo NEXT STEPS:
echo -----------

if %ERRORS% gtr 0 (
    echo 1. Run INSTALL_SIMPLE.bat to fix issues
    echo 2. Run this check again to verify
) else (
    if not exist "credentials.json" (
        echo 1. Get credentials.json from your administrator
        echo 2. Place it in this folder: %CD%
        echo 3. Run START_PROGRAM.bat
    ) else (
        if not exist "token.json" (
            echo 1. Run START_PROGRAM.bat
            echo 2. Complete Gmail setup when prompted
            echo 3. Upload your spreadsheet
        ) else (
            echo Run START_PROGRAM.bat to start using the program!
        )
    )
)

echo.
pause