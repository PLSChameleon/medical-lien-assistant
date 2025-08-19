@echo off
title Medical Lien Assistant
cls

:: Make sure we're in the right directory
cd /d "%~dp0"

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please run INSTALL_SIMPLE.bat first to install everything.
    echo.
    pause
    exit
)

:: Check if the launcher file exists
if not exist "simple_launcher.py" (
    color 0C
    echo [ERROR] simple_launcher.py not found!
    echo.
    echo Please make sure all files are in the correct location.
    pause
    exit /b 1
)

:: Run without console window
start "" pythonw simple_launcher.py

:: Close this window after a short delay
timeout /t 2 /nobreak >nul
exit