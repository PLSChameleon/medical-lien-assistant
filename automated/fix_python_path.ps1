# PowerShell script to locate Python and add it to PATH

Write-Host ""
Write-Host "🔍 Searching for Python installations..." -ForegroundColor Cyan

# Search common install paths
$possiblePaths = @(
    "$env:LOCALAPPDATA\Programs\Python",
    "$env:ProgramFiles\Python",
    "$env:ProgramFiles(x86)\Python",
    "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps"
)

$pythonExe = $null
$pythonScript = $null

foreach ($base in $possiblePaths) {
    if (Test-Path $base) {
        $found = Get-ChildItem -Path $base -Recurse -Include python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            $pythonExe = $found.DirectoryName
            $pythonScript = Join-Path $pythonExe "Scripts"
            break
        }
    }
}

if (-not $pythonExe) {
    Write-Host "❌ Python installation not found. Please install it from https://python.org/downloads" -ForegroundColor Red
    exit
}

Write-Host "✅ Found Python at: $pythonExe"
Write-Host "📁 Scripts directory: $pythonScript"

# Add to user PATH
$envPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathList = $envPath -split ";"

$updated = $false

if ($pathList -notcontains $pythonExe) {
    $pathList += $pythonExe
    $updated = $true
}
if ($pathList -notcontains $pythonScript) {
    $pathList += $pythonScript
    $updated = $true
}

if ($updated) {
    $newPath = ($pathList -join ";")
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "✅ Python and Scripts paths added to PATH!" -ForegroundColor Green
    Write-Host "🔄 Please restart your terminal or system for changes to take effect." -ForegroundColor Yellow
} else {
    Write-Host "ℹ️ Python paths are already in your PATH." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🧪 You can now try running:" -ForegroundColor Cyan
Write-Host "   python --version" -ForegroundColor Cyan
Write-Host "   pip --version" -ForegroundColor Cyan
