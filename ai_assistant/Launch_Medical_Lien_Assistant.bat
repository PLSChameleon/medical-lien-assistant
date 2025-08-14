@echo off
title Medical Lien Assistant - Multi-User
echo Starting Medical Lien Assistant...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if running from correct directory
if not exist "multi_user_launcher.py" (
    echo ERROR: Please run this file from the ai_assistant directory
    pause
    exit /b 1
)

REM Launch the application
python multi_user_launcher.py

REM If there was an error, keep window open
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)