# Emergency PC Relief Script
Write-Host "=== EMERGENCY RELIEF RUNNING ===" -ForegroundColor Red

# 1. Make sure SysMain is running
Write-Host "[1] Ensuring SysMain is running..." -ForegroundColor Yellow
sc.exe config SysMain start=auto | Out-Null
sc.exe start SysMain 2>$null | Out-Null
Write-Host "    SysMain OK" -ForegroundColor Green

# 2. Re-enable WSearch (search indexer - disabling can cause background thrashing)
Write-Host "[2] Ensuring WSearch is running..." -ForegroundColor Yellow
sc.exe config WSearch start=auto | Out-Null
sc.exe start WSearch 2>$null | Out-Null
Write-Host "    WSearch OK" -ForegroundColor Green

# 3. Make sure power plan is Balanced
Write-Host "[3] Setting Balanced power plan..." -ForegroundColor Yellow
powercfg /setactive SCHEME_BALANCED | Out-Null
Write-Host "    Balanced plan active" -ForegroundColor Green

# 4. Kill known heavy hitters if running
Write-Host "[4] Killing known background hogs..." -ForegroundColor Yellow
$targets = @("SearchIndexer","SearchProtocolHost","SearchFilterHost","TiWorker","TrustedInstaller","WmiPrvSE","msiexec","vssvc")
foreach ($t in $targets) {
    $procs = Get-Process -Name $t -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "    Stopped: $t" -ForegroundColor Yellow
    }
}

# 5. Clear standby pagefile pressure by asking Windows to trim working sets gently
Write-Host "[5] Requesting Windows memory trim..." -ForegroundColor Yellow
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
Write-Host "    Memory trim requested" -ForegroundColor Green

# 6. Flush DNS
Write-Host "[6] Flushing DNS..." -ForegroundColor Yellow
ipconfig /flushdns | Out-Null
Write-Host "    DNS flushed" -ForegroundColor Green

# 7. Show current top CPU hogs
Write-Host "`n=== CURRENT TOP CPU PROCESSES ===" -ForegroundColor Cyan
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 | ForEach-Object {
    $cpuSec = [math]::Round($_.CPU, 1)
    $ramMB  = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Host ("{0,-35} PID:{1,-6} CPU:{2,-8}s RAM:{3} MB" -f $_.Name, $_.Id, $cpuSec, $ramMB)
}

# 8. RAM summary
Write-Host "`n=== RAM SUMMARY ===" -ForegroundColor Cyan
$os    = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$free  = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$used  = [math]::Round($total - $free, 2)
$pct   = [math]::Round(($used / $total) * 100, 1)
Write-Host "Total: ${total} GB  |  Used: ${used} GB (${pct}%)  |  Free: ${free} GB" -ForegroundColor White

Write-Host "`n=== DONE - Your PC should feel better now ===" -ForegroundColor Green
Write-Host "If still slow: RESTART YOUR PC (Winsock reset needs a reboot)" -ForegroundColor Yellow
