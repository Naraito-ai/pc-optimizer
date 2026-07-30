# ==============================================================================
# PC Performance Optimizer - One-Line Installer & Runner (Option A)
# Run via: iwr -useb https://raw.githubusercontent.com/USERNAME/pc-optimizer/main/install.ps1 | iex
# ==============================================================================

$ErrorActionPreference = "Stop"

# Define GitHub raw repository base URL
$RAW_BASE_URL = "https://raw.githubusercontent.com/USERNAME/pc-optimizer/main"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     ⚡ PC PERFORMANCE OPTIMIZER - AUTOMATED INSTALLER ⚡" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] Administrator privileges are required to run this installer." -ForegroundColor Yellow
    Write-Host "[*] Relaunching script with elevated privileges..." -ForegroundColor Cyan
    
    $scriptUrl = "$RAW_BASE_URL/install.ps1"
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command `"iwr -useb '$scriptUrl' | iex`"" -Verb RunAs
    exit
}

Write-Host "[✓] Running with Administrator privileges." -ForegroundColor Green

# 2. Check and Install Python 3
Write-Host "[*] Checking for Python 3 installation..." -ForegroundColor Cyan
$pythonInstalled = $false

try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3") {
        $pythonInstalled = $true
        Write-Host "[✓] Python 3 detected: $pythonVersion" -ForegroundColor Green
    }
} catch {
    $pythonInstalled = $false
}

if (-not $pythonInstalled) {
    Write-Host "[!] Python 3 not found. Installing Python 3 silently via winget..." -ForegroundColor Yellow
    try {
        winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        
        # Refresh environment variables PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Write-Host "[✓] Python 3 successfully installed!" -ForegroundColor Green
    } catch {
        Write-Host "[X] Failed to install Python via winget. Please install Python 3 manually from python.org." -ForegroundColor Red
        exit 1
    }
}

# 3. Create Temporary Workspace Directory
$workDir = Join-Path $env:TEMP "PCOptimizerWorkspace"
if (Test-Path $workDir) {
    Remove-Item $workDir -Recurse -Force | Out-Null
}
New-Item -ItemType Directory -Path $workDir | Out-Null
Set-Location $workDir

Write-Host "[*] Workspace directory prepared: $workDir" -ForegroundColor Cyan

# 4. Download optimizer.py and requirements.txt
Write-Host "[*] Downloading optimizer core files from GitHub repository..." -ForegroundColor Cyan

$optimizerUrl = "$RAW_BASE_URL/optimizer.py"
$requirementsUrl = "$RAW_BASE_URL/requirements.txt"

try {
    Invoke-WebRequest -Uri $optimizerUrl -OutFile "$workDir\optimizer.py" -UseBasicParsing
    Invoke-WebRequest -Uri $requirementsUrl -OutFile "$workDir\requirements.txt" -UseBasicParsing
    Write-Host "[✓] Files downloaded successfully." -ForegroundColor Green
} catch {
    Write-Host "[X] Error downloading files from $RAW_BASE_URL. Please verify repository URL and connection." -ForegroundColor Red
    exit 1
}

# 5. Install Required Dependencies
Write-Host "[*] Installing Python dependencies (psutil, colorama, tabulate)..." -ForegroundColor Cyan
try {
    python -m pip install --upgrade pip --quiet
    python -m pip install -r "$workDir\requirements.txt" --quiet
    Write-Host "[✓] Python dependencies installed successfully." -ForegroundColor Green
} catch {
    Write-Host "[X] Failed to install Python requirements." -ForegroundColor Red
    exit 1
}

# 6. Launch optimizer.py
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   🚀 Launching PC Performance Optimizer..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Start-Process python -ArgumentList "$workDir\optimizer.py" -Wait -NoNewWindow

Write-Host ""
Write-Host "[✓] Optimizer session finished." -ForegroundColor Green
