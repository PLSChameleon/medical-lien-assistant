@echo off
title Medical Lien Assistant - Installation Verification
color 0E
cls

echo ================================================
echo  MEDICAL LIEN ASSISTANT - INSTALLATION CHECK
echo ================================================
echo.
echo Checking your installation...
echo.

set "ERRORS=0"
set "WARNINGS=0"

:: Check Python installation
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo       [OK] Python %%i installed
) else (
    echo       [ERROR] Python is not installed or not in PATH
    set /a ERRORS+=1
)

:: Check pip
echo [2/7] Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo       [OK] pip is installed
) else (
    echo       [ERROR] pip is not installed
    set /a ERRORS+=1
)

:: Check critical Python packages
echo [3/7] Checking required packages...
set "MISSING_PACKAGES="

python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] PyQt5 - User interface
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import openai" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] openai - AI functionality
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] pandas - Data processing
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import googleapiclient" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] google-api-python-client - Gmail integration
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import cryptography" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] cryptography - Security features
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

python -c "import playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [MISSING] playwright - Web automation
    set "MISSING_PACKAGES=1"
    set /a WARNINGS+=1
)

if not defined MISSING_PACKAGES (
    echo       [OK] All required packages installed
)

:: Check program files
echo [4/7] Checking program files...
set "MISSING_FILES="

if not exist "simple_launcher.py" (
    echo       [MISSING] simple_launcher.py
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

if not exist "services\email_cache_service.py" (
    echo       [MISSING] services\email_cache_service.py
    set "MISSING_FILES=1"
    set /a ERRORS+=1
)

if not exist "data\default_cadence_profile.json" (
    echo       [MISSING] data\default_cadence_profile.json
    set "MISSING_FILES=1"
    set /a WARNINGS+=1
)

if not defined MISSING_FILES (
    echo       [OK] All core files present
)

:: Check START_PROGRAM.bat
echo [5/7] Checking launcher script...
if exist "START_PROGRAM.bat" (
    echo       [OK] START_PROGRAM.bat exists
) else (
    echo       [WARNING] START_PROGRAM.bat missing - creating now...
    echo @echo off > "START_PROGRAM.bat"
    echo title Medical Lien Assistant >> "START_PROGRAM.bat"
    echo cd /d "%%~dp0" >> "START_PROGRAM.bat"
    echo python simple_launcher.py >> "START_PROGRAM.bat"
    echo if errorlevel 1 pause >> "START_PROGRAM.bat"
    echo       [OK] Created START_PROGRAM.bat
)

:: Check Desktop shortcut
echo [6/7] Checking desktop shortcut...
if exist "%USERPROFILE%\Desktop\Medical Lien Assistant.lnk" (
    echo       [OK] Desktop shortcut exists
) else (
    echo       [INFO] No desktop shortcut found (can be created manually)
    set /a WARNINGS+=1
)

:: Check data directories
echo [7/7] Checking data directories...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "logs\errors" mkdir logs\errors
echo       [OK] Data directories ready

echo.
echo ================================================
echo  VERIFICATION COMPLETE
echo ================================================
echo.

if %ERRORS% equ 0 (
    if %WARNINGS% equ 0 (
        color 0A
        echo STATUS: READY TO RUN
        echo.
        echo Your installation is complete and verified!
        echo.
        echo To start the program:
        echo   - Double-click "Medical Lien Assistant" on your desktop
        echo   - OR double-click START_PROGRAM.bat
        echo.
    ) else (
        color 0E
        echo STATUS: READY WITH MINOR ISSUES
        echo.
        echo Found %WARNINGS% minor issue(s) that won't prevent running.
        echo.
        echo To fix missing packages, run: INSTALL_SIMPLE.bat
        echo.
        echo The program should still work. To start:
        echo   - Double-click START_PROGRAM.bat
        echo.
    )
) else (
    color 0C
    echo STATUS: INSTALLATION INCOMPLETE
    echo.
    echo Found %ERRORS% critical error(s) that must be fixed.
    echo.
    echo Please run INSTALL_SIMPLE.bat to complete installation.
    echo.
)

echo Press any key to exit...
pause >nul
exit