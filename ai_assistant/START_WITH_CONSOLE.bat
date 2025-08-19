@echo off
title Medical Lien Assistant - Console Mode
color 0B
cls

echo =====================================
echo  Medical Lien Assistant - Debug Mode
echo =====================================
echo.
echo This window shows program logs and debug information.
echo You can minimize it, but DO NOT close it or the program will stop.
echo.
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
    echo Please run INSTALL_SIMPLE.bat first.
    echo.
    pause
    exit
)

:: Run with console window for debugging
python simple_launcher.py

:: If program exits, show error
if %errorlevel% neq 0 (
    echo.
    echo =====================================
    echo  Program exited with error code: %errorlevel%
    echo =====================================
    echo.
    pause
)

exit