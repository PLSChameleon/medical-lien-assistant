@echo off
title Medical Lien Assistant - Easy Installation
color 0A
cls

echo =====================================
echo  MEDICAL LIEN ASSISTANT - EASY SETUP
echo =====================================
echo.
echo This will install everything automatically.
echo No technical knowledge required!
echo.
echo Press any key to start installation...
pause >nul
cls

:: Set error handling
setlocal enabledelayedexpansion

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo =====================================
    echo  REQUESTING ADMINISTRATOR ACCESS
    echo =====================================
    echo.
    echo This installer needs administrator access to:
    echo - Install Python if needed
    echo - Create desktop shortcuts
    echo.
    echo Please click YES on the next prompt...
    echo.
    timeout /t 3 /nobreak >nul
    
    :: Relaunch as administrator
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

echo =====================================
echo  STEP 1: CHECKING PYTHON
echo =====================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is already installed
    python --version
    echo.
    goto :InstallPackages
)

:: Python not found - install it automatically
echo [!] Python not found - Installing automatically...
echo.
echo Downloading Python (this may take a minute)...

:: Download Python installer silently
powershell -Command "& { 
    $ProgressPreference = 'SilentlyContinue'
    try {
        Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'
        Write-Host '[OK] Download complete' -ForegroundColor Green
    } catch {
        Write-Host '[ERROR] Download failed. Please check internet connection.' -ForegroundColor Red
        exit 1
    }
}"

if not exist "%TEMP%\python_installer.exe" (
    echo [ERROR] Failed to download Python
    echo.
    echo Please install Python manually from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo.
echo Installing Python (this will take 2-3 minutes)...
echo Please wait...

:: Install Python silently with all options
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_pip=1 Include_launcher=1

:: Wait for installation to complete
timeout /t 10 /nobreak >nul

:: Clean up installer
del "%TEMP%\python_installer.exe" >nul 2>&1

:: Refresh PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"
set "PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts"
set "PATH=%PATH%;C:\Python311;C:\Python311\Scripts"

:: Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Python installed but not in PATH yet
    echo.
    echo Please restart your computer and run this installer again.
    echo.
    pause
    exit /b 1
)

echo [OK] Python installed successfully!
echo.

:InstallPackages
echo =====================================
echo  STEP 2: INSTALLING COMPONENTS
echo =====================================
echo.
echo This will take 5-10 minutes...
echo.

:: Upgrade pip first
echo [1/8] Upgrading pip...
python -m pip install --upgrade pip --quiet --no-warn-script-location

:: Install packages with progress indicator
echo [2/8] Installing OpenAI...
python -m pip install openai --quiet --no-warn-script-location

echo [3/8] Installing Google Authentication...
python -m pip install google-auth google-auth-oauthlib google-auth-httplib2 --quiet --no-warn-script-location

echo [4/8] Installing Gmail API...
python -m pip install google-api-python-client --quiet --no-warn-script-location

echo [5/8] Installing Data Processing...
python -m pip install pandas openpyxl --quiet --no-warn-script-location

echo [6/8] Installing User Interface...
python -m pip install PyQt5 --quiet --no-warn-script-location

echo [7/8] Installing Web Browser...
python -m pip install playwright --quiet --no-warn-script-location

echo [8/8] Installing Security and Additional Components...
python -m pip install cryptography python-dotenv pytz requests email-validator --quiet --no-warn-script-location

echo.
echo =====================================
echo  STEP 3: CONFIGURING BROWSER
echo =====================================
echo.

:: Install Playwright browsers
python -m playwright install chromium --with-deps >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Browser components installed
) else (
    echo [WARNING] Browser components may need manual setup
)

echo.
echo =====================================
echo  STEP 4: CREATING SHORTCUTS
echo =====================================
echo.

:: Create desktop shortcut
set "DESKTOP=%USERPROFILE%\Desktop"
set "APP_DIR=%~dp0"

:: Remove trailing backslash from APP_DIR
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

:: Create START_PROGRAM.bat if it doesn't exist
if not exist "%APP_DIR%\START_PROGRAM.bat" (
    echo @echo off > "%APP_DIR%\START_PROGRAM.bat"
    echo title Medical Lien Assistant >> "%APP_DIR%\START_PROGRAM.bat"
    echo cd /d "%%~dp0" >> "%APP_DIR%\START_PROGRAM.bat"
    echo python multi_user_launcher.py >> "%APP_DIR%\START_PROGRAM.bat"
    echo if errorlevel 1 pause >> "%APP_DIR%\START_PROGRAM.bat"
)

:: Create desktop shortcut using PowerShell
powershell -Command "& {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Medical Lien Assistant.lnk')
    $Shortcut.TargetPath = '%APP_DIR%\START_PROGRAM.bat'
    $Shortcut.WorkingDirectory = '%APP_DIR%'
    $Shortcut.IconLocation = '%SystemRoot%\System32\SHELL32.dll,13'
    $Shortcut.Description = 'Medical Lien Assistant'
    $Shortcut.Save()
}"

if exist "%DESKTOP%\Medical Lien Assistant.lnk" (
    echo [OK] Desktop shortcut created
) else (
    echo [INFO] Shortcut creation skipped
)

:: Create Start Menu shortcut
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -Command "& {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('%STARTMENU%\Medical Lien Assistant.lnk')
    $Shortcut.TargetPath = '%APP_DIR%\START_PROGRAM.bat'
    $Shortcut.WorkingDirectory = '%APP_DIR%'
    $Shortcut.IconLocation = '%SystemRoot%\System32\SHELL32.dll,13'
    $Shortcut.Description = 'Medical Lien Assistant'
    $Shortcut.Save()
}"

echo [OK] Start Menu shortcut created
echo.

:: Check for required files
echo =====================================
echo  STEP 5: CHECKING FILES
echo =====================================
echo.

set "MISSING_FILES="

if not exist "%APP_DIR%\multi_user_launcher.py" (
    echo [ERROR] Missing: multi_user_launcher.py
    set "MISSING_FILES=1"
)

if not exist "%APP_DIR%\enhanced_gui_app.py" (
    echo [ERROR] Missing: enhanced_gui_app.py
    set "MISSING_FILES=1"
)

if not exist "%APP_DIR%\services\gmail_service.py" (
    echo [ERROR] Missing: services\gmail_service.py
    set "MISSING_FILES=1"
)

if defined MISSING_FILES (
    echo.
    echo [ERROR] Some program files are missing!
    echo Please make sure all files were copied correctly.
    echo.
    pause
    exit /b 1
)

echo [OK] All program files found
echo.

:: Setup complete
cls
color 0A
echo.
echo =====================================
echo     INSTALLATION COMPLETE!
echo =====================================
echo.
echo The Medical Lien Assistant is ready to use!
echo.
echo TO START THE PROGRAM:
echo ------------------
echo Option 1: Double-click "Medical Lien Assistant" on your Desktop
echo Option 2: Click START_PROGRAM.bat in this folder
echo.
echo FIRST TIME SETUP:
echo ----------------
echo When you first run the program:
echo.
echo 1. GMAIL SETUP:
echo    - Click "Authenticate Gmail"
echo    - Sign in to your Gmail account
echo    - Allow access when prompted
echo    - That's it! No codes to copy!
echo.
echo 2. SPREADSHEET:
echo    - Click "File" menu
echo    - Select "Upload Spreadsheet"
echo    - Choose your Excel file
echo.
echo 3. CMS LOGIN:
echo    - Enter your CMS username
echo    - Enter your CMS password
echo    - Click "Test Connection"
echo.
echo =====================================
echo.
echo Press any key to start the program now...
pause >nul

:: Start the program
echo.
echo Starting Medical Lien Assistant...
start "" "%APP_DIR%\START_PROGRAM.bat"

exit