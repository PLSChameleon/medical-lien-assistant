@echo off
title Medical Lien Assistant
color 0B
cls

echo =====================================
echo  Starting Medical Lien Assistant...
echo =====================================
echo.

:: Make sure we're in the right directory
cd /d "%~dp0"

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python first:
    echo 1. Download from https://www.python.org
    echo 2. During installation, CHECK "Add Python to PATH"
    echo 3. After installation, try again
    echo.
    pause
    exit
)

:: Check for critical dependencies before starting
python -c "import cryptography" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Missing required package: cryptography
    echo Installing missing packages...
    python -m pip install cryptography
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install cryptography
        echo Please run INSTALL_COMPLETE.bat as administrator
        pause
        exit /b 1
    )
)

:: Try to run the program
echo Starting program...
echo.
echo Program will launch in a new window.
echo This terminal will close automatically in 3 seconds...
echo.

:: Start the program without console window and exit this batch
start "" pythonw simple_launcher.py
if %errorlevel% neq 0 (
    :: If pythonw fails, try with regular python
    start "" python simple_launcher.py
    if %errorlevel% neq 0 (
        echo.
        echo =====================================
        echo  Program failed to start
        echo =====================================
        echo.
        echo Possible issues:
        echo 1. Missing packages - Run INSTALL_SIMPLE.bat
        echo 2. Missing files - Make sure all files were copied
        echo 3. Python error - Check the error message above
        echo.
        echo For help, run CHECK_INSTALL.bat to diagnose issues
        echo.
        pause
        exit /b 1
    )
)

:: Wait 3 seconds then close
timeout /t 3 /nobreak >nul
exit