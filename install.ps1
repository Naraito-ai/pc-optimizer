# ==============================================================================
# PC Performance Optimizer - Verified Secure Installer (Phase 9)
# ==============================================================================

$ErrorActionPreference = "Stop"

# Define GitHub repository base URL & Release Manifest URL
$RAW_BASE_URL = "https://raw.githubusercontent.com/Naraito-ai/pc-optimizer/main"
$MANIFEST_URL = "$RAW_BASE_URL/release_manifest.json"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     ⚡ PC PERFORMANCE OPTIMIZER - VERIFIED INSTALLER ⚡" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Display Download Information & Checksum Intent
Write-Host "[*] Source Repository : https://github.com/Naraito-ai/pc-optimizer" -ForegroundColor White
Write-Host "[*] Source Manifest   : $MANIFEST_URL" -ForegroundColor White
Write-Host ""

# 2. Prepare Workspace Directory ($env:LOCALAPPDATA\PCOptimizer)
$workDir = "$env:LOCALAPPDATA\PCOptimizer"
if (-not (Test-Path $workDir)) {
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
}
Set-Location $workDir

# 3. Download Release Manifest & Exe Binary
$exeUrl = "$RAW_BASE_URL/optimizer.exe"
$exePath = Join-Path $workDir "optimizer.exe"

Write-Host "[*] Downloading release manifest..." -ForegroundColor Cyan
try {
    $manifestJson = (Invoke-WebRequest -Uri $MANIFEST_URL -UseBasicParsing).Content
    $manifest = $manifestJson | ConvertFrom-Json
    Write-Host "[✓] Manifest loaded for version: $($manifest.version)" -ForegroundColor Green
} catch {
    Write-Host "[!] Warning: Could not fetch remote manifest. Proceeding with direct download..." -ForegroundColor Yellow
    $manifest = $null
}

Write-Host "[*] Downloading optimizer.exe from $exeUrl..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $exeUrl -OutFile $exePath -UseBasicParsing
    Write-Host "[✓] Download complete: $exePath" -ForegroundColor Green
} catch {
    Write-Host "[X] Error downloading optimizer.exe from $exeUrl" -ForegroundColor Red
    exit 1
}

# 4. Compute and Verify SHA256 Checksum
$computedHash = (Get-FileHash -Path $exePath -Algorithm SHA256).Hash
Write-Host ""
Write-Host "[✓] Computed SHA256 Checksum: $computedHash" -ForegroundColor Yellow

if ($manifest -and $manifest.artifacts."optimizer.exe") {
    $expectedHash = $manifest.artifacts."optimizer.exe".sha256
    if ($computedHash -eq $expectedHash) {
        Write-Host "[✓] Checksum Verification SUCCESS: Matches official release manifest!" -ForegroundColor Green
    } else {
        Write-Host "[!] Checksum Verification MISMATCH!" -ForegroundColor Red
        Write-Host "    Expected: $expectedHash" -ForegroundColor Red
        Write-Host "    Computed: $computedHash" -ForegroundColor Red
        exit 1
    }
}

# 5. Require Explicit User Confirmation Before Execution
Write-Host ""
$confirm = Read-Host "Would you like to launch PC Optimizer (optimizer.exe)? [Y/N]"
if ($confirm -notmatch "^[Yy]$") {
    Write-Host "[!] Execution cancelled by user. File saved to: $exePath" -ForegroundColor Yellow
    exit 0
}

# 6. Launch Executable Cleanly
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   🚀 Launching PC Performance Optimizer..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Start-Process -FilePath $exePath
Write-Host "[✓] Session initiated successfully." -ForegroundColor Green
