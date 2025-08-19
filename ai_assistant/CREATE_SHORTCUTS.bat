@echo off
title Create Desktop Shortcuts
color 0A
cls

echo =====================================
echo  CREATING DESKTOP SHORTCUTS
echo =====================================
echo.

:: Get the current directory
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

:: Create a VBScript to create shortcuts (more reliable than PowerShell)
echo Creating shortcut script...
(
echo Set WshShell = CreateObject("WScript.Shell"^)
echo Set oShellLink = WshShell.CreateShortcut(WshShell.SpecialFolders("Desktop"^) ^& "\Medical Lien Assistant.lnk"^)
echo oShellLink.TargetPath = "%APP_DIR%\START_PROGRAM.bat"
echo oShellLink.WindowStyle = 1
echo oShellLink.IconLocation = "%SystemRoot%\System32\SHELL32.dll, 24"
echo oShellLink.Description = "Medical Lien Assistant - Case Management System"
echo oShellLink.WorkingDirectory = "%APP_DIR%"
echo oShellLink.Save
echo.
echo Set oShellLink2 = WshShell.CreateShortcut(WshShell.SpecialFolders("Desktop"^) ^& "\Medical Lien Assistant (Debug).lnk"^)
echo oShellLink2.TargetPath = "%APP_DIR%\START_WITH_CONSOLE.bat"
echo oShellLink2.WindowStyle = 1
echo oShellLink2.IconLocation = "%SystemRoot%\System32\SHELL32.dll, 15"
echo oShellLink2.Description = "Medical Lien Assistant with Debug Console"
echo oShellLink2.WorkingDirectory = "%APP_DIR%"
echo oShellLink2.Save
echo.
echo WScript.Echo "Shortcuts created successfully!"
) > "%TEMP%\CreateShortcuts.vbs"

:: Run the VBScript
echo Creating desktop shortcuts...
cscript //nologo "%TEMP%\CreateShortcuts.vbs"

:: Clean up
del "%TEMP%\CreateShortcuts.vbs" >nul 2>&1

:: Verify shortcuts were created
echo.
if exist "%USERPROFILE%\Desktop\Medical Lien Assistant.lnk" (
    echo [OK] Main shortcut created successfully!
) else (
    echo [WARNING] Could not verify main shortcut
)

if exist "%USERPROFILE%\Desktop\Medical Lien Assistant (Debug).lnk" (
    echo [OK] Debug shortcut created successfully!
) else (
    echo [WARNING] Could not verify debug shortcut
)

echo.
echo =====================================
echo  SHORTCUT CREATION COMPLETE
echo =====================================
echo.
echo Two shortcuts have been created on your desktop:
echo.
echo 1. Medical Lien Assistant
echo    - Runs the program normally (no console window)
echo.
echo 2. Medical Lien Assistant (Debug)
echo    - Runs with console window for troubleshooting
echo.
echo If shortcuts were not created, you can manually:
echo 1. Right-click START_PROGRAM.bat
echo 2. Select "Send to" -^> "Desktop (create shortcut)"
echo.
pause