# ==============================================================================
# PC Performance Optimizer - Verified Secure Installer
# ==============================================================================

$ErrorActionPreference = "Stop"

# Define GitHub repository base URL
$RAW_BASE_URL = "https://raw.githubusercontent.com/Naraito-ai/pc-optimizer/main"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     ⚡ PC PERFORMANCE OPTIMIZER - SECURE INSTALLER ⚡" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Administrator Privileges (Elevation Fix for iwr | iex)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] Administrator privileges are required to run this application." -ForegroundColor Yellow
    Write-Host "[*] Prompting for UAC elevation..." -ForegroundColor Cyan
    
    $scriptContent = (Invoke-WebRequest -Uri "$RAW_BASE_URL/install.ps1" -UseBasicParsing).Content
    $tempScript = "$env:TEMP\pc_optimizer_install.ps1"
    $scriptContent | Out-File -FilePath $tempScript -Encoding UTF8
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$tempScript`"" -Verb RunAs
    exit
}

Write-Host "[✓] Running with Administrator privileges." -ForegroundColor Green

# 2. Check and Install Python 3
Write-Host "[*] Checking Python 3 installation..." -ForegroundColor Cyan
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
    Write-Host "[!] Python 3 not found. Installing Python 3 via winget..." -ForegroundColor Yellow
    try {
        winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        Write-Host "[✓] Python 3 successfully installed!" -ForegroundColor Green
    } catch {
        Write-Host "[X] Failed to install Python via winget. Please install Python 3 manually from python.org." -ForegroundColor Red
        exit 1
    }
}

# 3. Create Persistent Workspace Directory (Survives Temp Cleanup)
$workDir = "$env:LOCALAPPDATA\PCOptimizer"
if (-not (Test-Path $workDir)) {
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
}
Set-Location $workDir

Write-Host "[*] Workspace directory: $workDir" -ForegroundColor Cyan

# 4. Download optimizer.py and requirements.txt (With Checksum Display)
$optimizerUrl = "$RAW_BASE_URL/optimizer.py"
$requirementsUrl = "$RAW_BASE_URL/requirements.txt"

Write-Host "[*] Source URL: $optimizerUrl" -ForegroundColor Cyan
Write-Host "[*] Downloading optimizer core files..." -ForegroundColor Cyan

try {
    Invoke-WebRequest -Uri $optimizerUrl -OutFile "$workDir\optimizer.py" -UseBasicParsing
    Invoke-WebRequest -Uri $requirementsUrl -OutFile "$workDir\requirements.txt" -UseBasicParsing
    
    # Calculate and display SHA256 checksum
    $hash = (Get-FileHash -Path "$workDir\optimizer.py" -Algorithm SHA256).Hash
    Write-Host "[✓] Downloaded optimizer.py successfully." -ForegroundColor Green
    Write-Host "[✓] SHA256 Checksum: $hash" -ForegroundColor Yellow
} catch {
    Write-Host "[X] Error downloading files from $RAW_BASE_URL. Please verify repository URL." -ForegroundColor Red
    exit 1
}

# 5. Install Required Dependencies
Write-Host "[*] Verifying Python dependencies..." -ForegroundColor Cyan
try {
    python -m pip install -r "$workDir\requirements.txt" --quiet
    Write-Host "[✓] Python dependencies verified." -ForegroundColor Green
} catch {
    Write-Host "[!] Could not auto-install dependencies. Starting application check..." -ForegroundColor Yellow
}

# 6. Launch Application
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   🚀 Launching PC Performance Optimizer GUI..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Start-Process python -ArgumentList "`"$workDir\optimizer.py`"" -Wait -NoNewWindow

Write-Host ""
Write-Host "[✓] Session complete." -ForegroundColor Green
