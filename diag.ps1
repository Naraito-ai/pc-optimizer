Write-Host "`n=== RAM ===" -ForegroundColor Cyan
$mem = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($mem.TotalVisibleMemorySize/1MB, 1)
$free  = [math]::Round($mem.FreePhysicalMemory/1MB, 1)
$used  = [math]::Round($total - $free, 1)
Write-Host "Total: ${total} GB  |  Used: ${used} GB  |  Free: ${free} GB"

Write-Host "`n=== CPU & DISK % ===" -ForegroundColor Cyan
$counters = Get-Counter '\PhysicalDisk(_Total)\% Disk Time', '\Processor(_Total)\% Processor Time' -SampleInterval 2 -MaxSamples 1
foreach ($s in $counters.CounterSamples) {
    $name = $s.Path.Split('\')[-1]
    Write-Host "${name}: $([math]::Round($s.CookedValue,1))%"
}

Write-Host "`n=== TOP 12 BY CPU ===" -ForegroundColor Cyan
Get-Process | Sort-Object CPU -Descending | Select-Object -First 12 | ForEach-Object {
    $cpu = [math]::Round($_.CPU, 1)
    $ram = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Host ("{0,-30} PID:{1,-6} CPU:{2,-8} RAM:{3} MB" -f $_.Name, $_.Id, $cpu, $ram)
}

Write-Host "`n=== TOP 10 BY RAM ===" -ForegroundColor Cyan
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 | ForEach-Object {
    $ram = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Host ("{0,-30} PID:{1,-6} RAM:{2} MB" -f $_.Name, $_.Id, $ram)
}
