# ==============================================================================
# PC Performance Quick Diagnostic Tool
# ==============================================================================
Write-Host "`n=== SYSTEM MEMORY STATUS ===" -ForegroundColor Cyan
$mem = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($mem.TotalVisibleMemorySize / 1MB, 2)
$free  = [math]::Round($mem.FreePhysicalMemory / 1MB, 2)
$used  = [math]::Round($total - $free, 2)
$pct   = [math]::Round(($used / $total) * 100, 1)
Write-Host "Total RAM: ${total} GB  |  Used: ${used} GB (${pct}%)  |  Free: ${free} GB" -ForegroundColor White

Write-Host "`n=== TOP 10 CPU CONSUMERS ===" -ForegroundColor Cyan
Get-Process | Where-Object { $_.CPU -ne $null } | Sort-Object CPU -Descending | Select-Object -First 10 | ForEach-Object {
    $cpuSec = [math]::Round($_.CPU, 1)
    $ramMB  = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Host ("{0,-32} PID:{1,-6} CPU:{2,-8}s RAM:{3} MB" -f $_.Name, $_.Id, $cpuSec, $ramMB)
}

Write-Host "`n=== TOP 10 RAM CONSUMERS ===" -ForegroundColor Cyan
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 | ForEach-Object {
    $ramMB = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Host ("{0,-32} PID:{1,-6} RAM:{2} MB" -f $_.Name, $_.Id, $ramMB)
}
