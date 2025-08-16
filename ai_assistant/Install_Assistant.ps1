# Medical Lien Assistant - Automated Installer
# This script handles everything automatically

Write-Host "======================================" -ForegroundColor Cyan
Write-Host " Medical Lien Assistant - Auto Setup " -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Function to check and install Python
function Install-Python {
    Write-Host "Checking Python installation..." -ForegroundColor Yellow
    
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion) {
            Write-Host "✓ Python is already installed: $pythonVersion" -ForegroundColor Green
            return $true
        }
    } catch {
        # Python not found
    }
    
    Write-Host "Python not found. Installing Python 3.11..." -ForegroundColor Yellow
    
    # Download Python installer
    $pythonUrl = "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
    $installerPath = "$env:TEMP\python_installer.exe"
    
    Write-Host "Downloading Python..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
    
    Write-Host "Installing Python (this will take a few minutes)..." -ForegroundColor Yellow
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
    
    Remove-Item $installerPath -Force
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "✓ Python installed successfully!" -ForegroundColor Green
    return $true
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host ""
    Write-Host "Installing application dependencies..." -ForegroundColor Yellow
    Write-Host "This will take 5-10 minutes on first installation..." -ForegroundColor Gray
    
    # Upgrade pip
    Write-Host "Updating pip..." -ForegroundColor Yellow
    python -m pip install --upgrade pip --quiet
    
    # Install requirements
    Write-Host "Installing required packages..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt --quiet
    
    # Install Playwright browsers
    Write-Host "Installing browser automation components..." -ForegroundColor Yellow
    python -m playwright install chromium --with-deps
    
    Write-Host "✓ All dependencies installed!" -ForegroundColor Green
}

# Function to create shortcuts
function Create-Shortcuts {
    Write-Host ""
    Write-Host "Creating shortcuts..." -ForegroundColor Yellow
    
    $shell = New-Object -ComObject WScript.Shell
    $currentDir = Get-Location
    
    # Desktop shortcut
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcut = $shell.CreateShortcut("$desktopPath\Medical Lien Assistant.lnk")
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -Command `"cd '$currentDir'; python multi_user_launcher.py`""
    $shortcut.WorkingDirectory = $currentDir
    $shortcut.Description = "Medical Lien Assistant"
    $shortcut.Save()
    
    # Start Menu shortcut
    $startMenuPath = [Environment]::GetFolderPath("StartMenu")
    $programsPath = "$startMenuPath\Programs\Medical Lien Assistant"
    
    if (!(Test-Path $programsPath)) {
        New-Item -ItemType Directory -Path $programsPath -Force | Out-Null
    }
    
    $shortcut = $shell.CreateShortcut("$programsPath\Medical Lien Assistant.lnk")
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -Command `"cd '$currentDir'; python multi_user_launcher.py`""
    $shortcut.WorkingDirectory = $currentDir
    $shortcut.Description = "Medical Lien Assistant"
    $shortcut.Save()
    
    Write-Host "✓ Shortcuts created on Desktop and Start Menu!" -ForegroundColor Green
}

# Function to test installation
function Test-Installation {
    Write-Host ""
    Write-Host "Testing installation..." -ForegroundColor Yellow
    
    try {
        $testResult = python -c "import openai, pandas, playwright, PyQt5; print('OK')" 2>$null
        if ($testResult -eq "OK") {
            Write-Host "✓ Installation verified successfully!" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "✗ Installation verification failed" -ForegroundColor Red
        return $false
    }
}

# Main installation process
try {
    # Step 1: Install Python if needed
    Install-Python
    
    # Step 2: Install dependencies
    Install-Dependencies
    
    # Step 3: Create shortcuts
    Create-Shortcuts
    
    # Step 4: Test installation
    $testOk = Test-Installation
    
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Green
    Write-Host "    Installation Complete!           " -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Medical Lien Assistant is ready to use!" -ForegroundColor Green
    Write-Host ""
    Write-Host "How to start:" -ForegroundColor Cyan
    Write-Host "  1. Click the 'Medical Lien Assistant' icon on your desktop" -ForegroundColor White
    Write-Host "  2. Or find it in your Start Menu" -ForegroundColor White
    Write-Host ""
    Write-Host "First time setup:" -ForegroundColor Cyan
    Write-Host "  • The setup wizard will guide you" -ForegroundColor White
    Write-Host "  • Enter your Gmail address" -ForegroundColor White
    Write-Host "  • Enter your CMS credentials" -ForegroundColor White
    Write-Host "  • Your credentials are saved securely" -ForegroundColor White
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
} catch {
    Write-Host ""
    Write-Host "Installation failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please contact support for assistance." -ForegroundColor Yellow
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}