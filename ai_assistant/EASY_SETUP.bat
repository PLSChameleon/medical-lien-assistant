@echo off
title Medical Lien Assistant - Easy Setup
color 0A

echo =====================================
echo  Medical Lien Assistant - Easy Setup
echo =====================================
echo.
echo This will automatically set up everything needed.
echo No technical knowledge required!
echo.
pause

:: Check Python installation
echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Installing Python...
    echo.
    echo Downloading Python installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -OutFile 'python_installer.exe'"
    
    echo Installing Python (this may take a few minutes)...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    
    :: Refresh environment variables
    call refreshenv >nul 2>&1
    
    echo Python installed successfully!
) else (
    echo Python is already installed!
)

echo.
echo =====================================
echo Installing application dependencies...
echo =====================================
echo.

:: Install pip packages
echo Installing required packages (this may take 5-10 minutes)...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

:: Install Playwright browsers
echo.
echo Installing browser components...
python -m playwright install chromium --with-deps

echo.
echo =====================================
echo Creating desktop shortcuts...
echo =====================================

:: Create desktop shortcut for the launcher
set "DESKTOP=%USERPROFILE%\Desktop"
set "APP_DIR=%CD%"

echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Medical Lien Assistant.lnk'); $Shortcut.TargetPath = 'cmd.exe'; $Shortcut.Arguments = '/c cd /d \"%APP_DIR%\" && python multi_user_launcher.py'; $Shortcut.WorkingDirectory = '%APP_DIR%'; $Shortcut.WindowStyle = 7; $Shortcut.Description = 'Medical Lien Assistant'; $Shortcut.Save()"

echo.
echo =====================================
echo  Setup Complete!
echo =====================================
echo.
echo Medical Lien Assistant is ready to use!
echo.
echo A shortcut has been created on your desktop.
echo Double-click "Medical Lien Assistant" to start.
echo.
echo First time you run it:
echo  1. You'll see a setup wizard
echo  2. Enter your Gmail address
echo  3. Enter your CMS credentials
echo  4. That's it! Your credentials will be saved securely.
echo.
pause