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

:: Try to run the program
echo Starting program...
echo.
python multi_user_launcher.py

:: Check if program exited with error
if %errorlevel% neq 0 (
    echo.
    echo =====================================
    echo  Program exited with an error
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
)