@echo off
title Medical Lien Assistant - Complete Installation
color 0A
cls

echo ============================================
echo  MEDICAL LIEN ASSISTANT - COMPLETE INSTALLER
echo ============================================
echo.
echo This installer will:
echo  - Check/Install Python
echo  - Install ALL required packages
echo  - Create desktop shortcuts
echo  - Verify installation
echo.
echo Press any key to start...
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
    echo Administrator access needed to:
    echo - Install Python if needed
    echo - Create desktop shortcuts
    echo.
    echo Click YES on the next prompt...
    echo.
    timeout /t 3 /nobreak >nul
    
    :: Relaunch as administrator
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

:: Store the application directory
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

echo =====================================
echo  STEP 1: CHECKING PYTHON
echo =====================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is installed
    python --version
    echo.
    goto :CheckPip
)

:: Python not found - provide download instructions
echo [!] Python is not installed
echo.
echo AUTOMATIC INSTALLATION:
echo ----------------------
echo Downloading Python 3.11...
echo.

:: Download Python installer
powershell -Command "& { 
    $ProgressPreference = 'SilentlyContinue'
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'
        Write-Host '[OK] Download complete' -ForegroundColor Green
    } catch {
        Write-Host '[ERROR] Download failed: ' $_.Exception.Message -ForegroundColor Red
        exit 1
    }
}"

if not exist "%TEMP%\python_installer.exe" (
    echo [ERROR] Failed to download Python
    echo.
    echo Please install Python manually from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Installing Python...
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_pip=1

:: Wait for installation
timeout /t 15 /nobreak >nul

:: Clean up
del "%TEMP%\python_installer.exe" >nul 2>&1

:: Refresh PATH
call :RefreshPath

:CheckPip
echo =====================================
echo  STEP 2: UPGRADING PIP
echo =====================================
echo.

python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Pip not found - installing...
    python -m ensurepip --default-pip
)

echo Upgrading pip to latest version...
python -m pip install --upgrade pip
echo [OK] Pip is ready
echo.

echo =====================================
echo  STEP 3: INSTALLING PACKAGES
echo =====================================
echo.

:: Check if requirements.txt exists
if exist "%APP_DIR%\requirements.txt" (
    echo Installing from requirements.txt...
    echo This may take 5-10 minutes...
    echo.
    
    :: Install all requirements at once
    python -m pip install -r "%APP_DIR%\requirements.txt"
    
    if %errorlevel% neq 0 (
        echo.
        echo [WARNING] Some packages may have failed to install
        echo Attempting individual installation...
        echo.
        goto :InstallIndividual
    )
    
    echo [OK] All packages installed from requirements.txt
    goto :InstallPlaywright
) else (
    echo requirements.txt not found, installing packages individually...
    goto :InstallIndividual
)

:InstallIndividual
echo Installing packages individually...
echo.

:: Critical packages - install one by one with error checking
echo [1/10] Installing cryptography (security)...
python -m pip install cryptography

echo [2/10] Installing OpenAI...
python -m pip install openai

echo [3/10] Installing Google Authentication...
python -m pip install google-auth google-auth-oauthlib google-auth-httplib2

echo [4/10] Installing Gmail API...
python -m pip install google-api-python-client

echo [5/10] Installing Data Processing (pandas)...
python -m pip install pandas openpyxl

echo [6/10] Installing User Interface (PyQt5)...
python -m pip install PyQt5

echo [7/10] Installing Email Validator...
python -m pip install email-validator

echo [8/10] Installing Utilities...
python -m pip install python-dotenv pytz requests

echo [9/10] Installing Web Automation...
python -m pip install playwright

echo [10/10] Final dependencies...
python -m pip install pyqt5-tools

:InstallPlaywright
echo.
echo =====================================
echo  STEP 4: CONFIGURING BROWSER
echo =====================================
echo.

echo Installing browser components...
python -m playwright install chromium
if %errorlevel% equ 0 (
    echo [OK] Browser components installed
) else (
    echo [INFO] Browser components will be installed on first run
)

echo.
echo =====================================
echo  STEP 5: CREATING SHORTCUTS
echo =====================================
echo.

:: Create START_PROGRAM.bat if it doesn't exist
if not exist "%APP_DIR%\START_PROGRAM.bat" (
    echo Creating startup script...
    (
        echo @echo off
        echo title Medical Lien Assistant
        echo color 0B
        echo cd /d "%%~dp0"
        echo.
        echo echo Starting Medical Lien Assistant...
        echo echo.
        echo.
        echo :: Check if Python is available
        echo python --version ^>nul 2^>^&1
        echo if %%errorlevel%% neq 0 ^(
        echo     echo ERROR: Python is not installed or not in PATH
        echo     echo Please run INSTALL_COMPLETE.bat first
        echo     pause
        echo     exit /b 1
        echo ^)
        echo.
        echo :: Run the launcher
        echo python multi_user_launcher.py
        echo.
        echo :: Check for errors
        echo if %%errorlevel%% neq 0 ^(
        echo     echo.
        echo     echo ERROR: Program failed to start
        echo     echo.
        echo     echo Common fixes:
        echo     echo 1. Run INSTALL_COMPLETE.bat as administrator
        echo     echo 2. Make sure all files were copied correctly
        echo     echo 3. Check that antivirus is not blocking the program
        echo     echo.
        echo     pause
        echo ^)
    ) > "%APP_DIR%\START_PROGRAM.bat"
    echo [OK] Startup script created
)

:: Create desktop shortcut using PowerShell with better error handling
set "DESKTOP=%USERPROFILE%\Desktop"

echo Creating desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {
    try {
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Medical Lien Assistant.lnk')
        $Shortcut.TargetPath = '%APP_DIR%\START_PROGRAM.bat'
        $Shortcut.WorkingDirectory = '%APP_DIR%'
        $Shortcut.IconLocation = '%SystemRoot%\System32\SHELL32.dll,13'
        $Shortcut.Description = 'Medical Lien Assistant - Automated Collections System'
        $Shortcut.WindowStyle = 1
        $Shortcut.Save()
        Write-Host '[OK] Desktop shortcut created successfully' -ForegroundColor Green
    } catch {
        Write-Host '[ERROR] Failed to create desktop shortcut: ' $_.Exception.Message -ForegroundColor Red
    }
}"

:: Also create Start Menu shortcut
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
echo Creating Start Menu shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {
    try {
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('%STARTMENU%\Medical Lien Assistant.lnk')
        $Shortcut.TargetPath = '%APP_DIR%\START_PROGRAM.bat'
        $Shortcut.WorkingDirectory = '%APP_DIR%'
        $Shortcut.IconLocation = '%SystemRoot%\System32\SHELL32.dll,13'
        $Shortcut.Description = 'Medical Lien Assistant - Automated Collections System'
        $Shortcut.Save()
        Write-Host '[OK] Start Menu shortcut created' -ForegroundColor Green
    } catch {
        Write-Host '[INFO] Start Menu shortcut skipped' -ForegroundColor Yellow
    }
}"

echo.
echo =====================================
echo  STEP 6: VERIFYING INSTALLATION
echo =====================================
echo.

:: Verify critical packages
echo Checking installed packages...
python -c "import cryptography; print('[OK] Cryptography module found')" 2>nul || echo [ERROR] Cryptography module missing
python -c "import openai; print('[OK] OpenAI module found')" 2>nul || echo [ERROR] OpenAI module missing
python -c "import pandas; print('[OK] Pandas module found')" 2>nul || echo [ERROR] Pandas module missing
python -c "import PyQt5; print('[OK] PyQt5 module found')" 2>nul || echo [ERROR] PyQt5 module missing
python -c "import google.auth; print('[OK] Google Auth module found')" 2>nul || echo [ERROR] Google Auth module missing

echo.
echo Checking program files...
if exist "%APP_DIR%\multi_user_launcher.py" (
    echo [OK] Launcher found
) else (
    echo [ERROR] multi_user_launcher.py missing
)

if exist "%APP_DIR%\enhanced_gui_app.py" (
    echo [OK] Main application found
) else (
    echo [ERROR] enhanced_gui_app.py missing
)

if exist "%APP_DIR%\services\gmail_service.py" (
    echo [OK] Services folder found
) else (
    echo [ERROR] Services folder missing or incomplete
)

:: Final message
echo.
echo =====================================
echo     INSTALLATION COMPLETE!
echo =====================================
echo.
echo The Medical Lien Assistant has been installed!
echo.
echo TO START THE PROGRAM:
echo --------------------
echo 1. Look for "Medical Lien Assistant" on your Desktop
echo 2. Double-click to start
echo.
echo OR
echo.
echo Run START_PROGRAM.bat from this folder
echo.
echo TROUBLESHOOTING:
echo ---------------
echo If the program doesn't start:
echo 1. Right-click this installer and "Run as administrator"
echo 2. Make sure Windows Defender isn't blocking it
echo 3. Try restarting your computer
echo.
echo =====================================
echo.
echo Would you like to start the program now? (Y/N)
set /p START_NOW=

if /i "%START_NOW%"=="Y" (
    echo.
    echo Starting Medical Lien Assistant...
    start "" "%APP_DIR%\START_PROGRAM.bat"
)

echo.
echo Press any key to exit installer...
pause >nul
exit

:RefreshPath
:: Refresh system PATH
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%B"
set "PATH=%SYS_PATH%;%USR_PATH%"
exit /b