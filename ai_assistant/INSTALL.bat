@echo off
title Medical Lien Assistant - Installer
color 0A

echo ======================================
echo  Medical Lien Assistant Installation
echo ======================================
echo.
echo This will install everything needed to run
echo the Medical Lien Assistant on your computer.
echo.
echo No technical knowledge required!
echo.
echo Press any key to begin installation...
pause >nul

:: Run PowerShell installer with proper execution policy
powershell.exe -ExecutionPolicy Bypass -File "%~dp0Install_Assistant.ps1"

:: Check if installation succeeded
if %errorlevel% equ 0 (
    color 0A
    echo.
    echo Installation completed successfully!
) else (
    color 0C
    echo.
    echo Installation encountered an error.
    echo Please try running as Administrator.
)

pause