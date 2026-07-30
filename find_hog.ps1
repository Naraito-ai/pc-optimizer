# Identify and fix high CPU svchost + WSL memory
Write-Host "=== IDENTIFYING HIGH CPU SVCHOST ===" -ForegroundColor Red

# Find what service is in that svchost PID 13824
Write-Host "`nServices in top svchost (PID 13824):" -ForegroundColor Yellow
Get-CimInstance Win32_Service | Where-Object { $_.ProcessId -eq 13824 } | ForEach-Object {
    Write-Host "  -> $($_.Name) : $($_.DisplayName) [$($_.State)]" -ForegroundColor White
}

# Also show all high CPU svchost instances
Write-Host "`nAll svchost processes with CPU > 10s:" -ForegroundColor Yellow
Get-Process -Name svchost | Where-Object { $_.CPU -gt 10 } | ForEach-Object {
    $pid = $_.Id
    $cpu = [math]::Round($_.CPU, 1)
    $ram = [math]::Round($_.WorkingSet/1MB, 1)
    Write-Host "  PID $pid  CPU:${cpu}s  RAM:${ram}MB" -ForegroundColor White
    Get-CimInstance Win32_Service | Where-Object { $_.ProcessId -eq $pid } | ForEach-Object {
        Write-Host "    Service: $($_.Name) - $($_.DisplayName)" -ForegroundColor Cyan
    }
}

# Stop WSL to free 435MB RAM
Write-Host "`n=== STOPPING WSL TO FREE RAM ===" -ForegroundColor Yellow
wsl --shutdown 2>$null
Write-Host "WSL shutdown requested (frees ~435MB RAM)" -ForegroundColor Green

# Show updated RAM
Start-Sleep -Seconds 2
$os   = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
$free  = [math]::Round($os.FreePhysicalMemory/1MB, 2)
$used  = [math]::Round($total - $free, 2)
$pct   = [math]::Round(($used/$total)*100, 1)
Write-Host "`nRAM now: Used=${used}GB / ${total}GB (${pct}%)  Free=${free}GB" -ForegroundColor Green
