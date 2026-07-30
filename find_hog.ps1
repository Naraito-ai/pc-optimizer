# ==============================================================================
# PC Diagnostic Tool — Automated Resource & svchost Analyzer
# ==============================================================================
param(
    [switch]$ShutdownWSL
)

Write-Host "=== SYSTEM RESOURCE DIAGNOSTIC ===" -ForegroundColor Cyan

# 1. RAM Summary
$os = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$free  = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$used  = [math]::Round($total - $free, 2)
$pct   = [math]::Round(($used / $total) * 100, 1)
Write-Host "RAM Status: ${used} GB / ${total} GB (${pct}% used, ${free} GB free)`n" -ForegroundColor White

# 2. Top 10 CPU Consumers
Write-Host "=== TOP 10 PROCESSES BY CPU TIME ===" -ForegroundColor Yellow
Get-Process | Where-Object { $_.CPU -ne $null } | Sort-Object CPU -Descending | Select-Object -First 10 | ForEach-Object {
    $cpuSec = [math]::Round($_.CPU, 1)
    $ramMB  = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Host ("  {0,-32} PID:{1,-6} CPU:{2,-8}s RAM:{3} MB" -f $_.Name, $_.Id, $cpuSec, $ramMB)
}

# 3. Top 10 Memory Consumers
Write-Host "`n=== TOP 10 PROCESSES BY RAM USAGE ===" -ForegroundColor Yellow
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 | ForEach-Object {
    $ramMB = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Host ("  {0,-32} PID:{1,-6} RAM:{2} MB" -f $_.Name, $_.Id, $ramMB)
}

# 4. Auto-detect svchost Process Groups and Hosted Services
Write-Host "`n=== ACTIVE SVCHOST PROCESS GROUPS & SERVICES ===" -ForegroundColor Yellow
$svcHosts = Get-Process -Name svchost -ErrorAction SilentlyContinue | Sort-Object WorkingSet -Descending | Select-Object -First 5
foreach ($sh in $svcHosts) {
    $spid = $sh.Id
    $sram = [math]::Round($sh.WorkingSet / 1MB, 1)
    Write-Host "  svchost (PID $spid) — RAM: ${sram} MB" -ForegroundColor White
    $services = Get-CimInstance Win32_Service | Where-Object { $_.ProcessId -eq $spid }
    if ($services) {
        foreach ($svc in $services) {
            Write-Host "    └─ $($svc.Name) ($($svc.DisplayName)) [State: $($svc.State)]" -ForegroundColor Gray
        }
    } else {
        Write-Host "    └─ (No active Windows services mapped to this host)" -ForegroundColor Gray
    }
}

# 5. WSL Check (Never automatically shut down)
$wslProc = Get-Process -Name "vmmem", "vmmemwsl" -ErrorAction SilentlyContinue
if ($wslProc) {
    $wslRam = [math]::Round(($wslProc | Measure-Object -Property WorkingSet -Sum).Sum / 1MB, 1)
    Write-Host "`n=== WSL CONTAINER STATUS ===" -ForegroundColor Cyan
    Write-Host "  WSL process detected consuming ${wslRam} MB RAM." -ForegroundColor Yellow
    
    if ($ShutdownWSL) {
        Write-Host "  [-ShutdownWSL flag passed] Shutting down WSL..." -ForegroundColor Yellow
        wsl --shutdown 2>$null
        Write-Host "  ✔ WSL shutdown requested." -ForegroundColor Green
    } else {
        Write-Host "  ℹ WSL is running normally. Pass -ShutdownWSL switch if you want to close WSL containers." -ForegroundColor Gray
    }
}
