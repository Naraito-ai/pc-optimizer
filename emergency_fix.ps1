# ==============================================================================
# Emergency PC Relief Script — Safe System Recovery Tool
# ==============================================================================
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Advanced,
    [switch]$VerboseLogging
)

function Log-Message {
    param([string]$Message, [string]$Color = "White")
    if ($VerboseLogging -or $Color -ne "Gray") {
        Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
    }
}

Log-Message "=== EMERGENCY SYSTEM RELIEF RUNNING ===" "Cyan"

# 1. Ensure SysMain is active (prevents app launch lag)
if ($PSCmdlet.ShouldProcess("SysMain Service", "Set to automatic startup and start")) {
    Log-Message "[1] Ensuring SysMain (Superfetch) is running..." "Yellow"
    try {
        sc.exe config SysMain start=auto | Out-Null
        sc.exe start SysMain 2>$null | Out-Null
        Log-Message "    ✔ SysMain active" "Green"
    } catch {
        Log-Message "    ⚠️ SysMain notice: $_" "Yellow"
    }
}

# 2. Ensure Windows Search Indexer (WSearch) is active
if ($PSCmdlet.ShouldProcess("WSearch Service", "Set to automatic startup and start")) {
    Log-Message "[2] Ensuring Windows Search Indexer is running..." "Yellow"
    try {
        sc.exe config WSearch start=auto | Out-Null
        sc.exe start WSearch 2>$null | Out-Null
        Log-Message "    ✔ WSearch active" "Green"
    } catch {
        Log-Message "    ⚠️ WSearch notice: $_" "Yellow"
    }
}

# 3. Ensure Power Plan is Balanced
if ($PSCmdlet.ShouldProcess("Power Scheme", "Switch to Balanced")) {
    Log-Message "[3] Setting Balanced power plan..." "Yellow"
    try {
        powercfg /setactive SCHEME_BALANCED | Out-Null
        Log-Message "    ✔ Balanced power plan active" "Green"
    } catch {
        Log-Message "    ⚠️ Power plan notice: $_" "Yellow"
    }
}

# 4. Safe Bloatware Process Cleanup (System Critical & Maintenance Services NEVER killed unless -Advanced)
$safeTargets = @("OneDrive", "Teams", "Cortana", "Skype", "YourPhone", "Discord")
$advancedTargets = @("SearchProtocolHost", "SearchFilterHost")

$targetsToKill = $safeTargets
if ($Advanced) {
    Log-Message "[!] Advanced Mode active: Including secondary search protocol handlers." "Yellow"
    $targetsToKill += $advancedTargets
} else {
    Log-Message "[i] Standard Safety Mode: System installer & maintenance processes (TrustedInstaller, TiWorker, vssvc, WmiPrvSE, msiexec) are PROTECTED." "Gray"
}

Log-Message "[4] Checking non-essential background processes..." "Yellow"
foreach ($t in $targetsToKill) {
    if ($PSCmdlet.ShouldProcess($t, "Terminate Process")) {
        $procs = Get-Process -Name $t -ErrorAction SilentlyContinue
        if ($procs) {
            $procs | Stop-Process -Force -ErrorAction SilentlyContinue
            Log-Message "    ✔ Stopped non-essential process: $t" "Green"
        }
    }
}

# 5. Flush DNS
if ($PSCmdlet.ShouldProcess("DNS Cache", "Flush DNS Resolver Cache")) {
    Log-Message "[5] Flushing DNS..." "Yellow"
    try {
        ipconfig /flushdns | Out-Null
        Log-Message "    ✔ DNS flushed" "Green"
    } catch {
        Log-Message "    ⚠️ DNS flush notice: $_" "Yellow"
    }
}

# 6. Current System Metrics Summary
Log-Message "`n=== CURRENT SYSTEM METRICS ===" "Cyan"
$os = Get-CimInstance Win32_OperatingSystem
$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$free  = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$used  = [math]::Round($total - $free, 2)
$pct   = [math]::Round(($used / $total) * 100, 1)
Log-Message "RAM Usage: ${used} GB / ${total} GB (${pct}% used)" "White"

Log-Message "`n=== EMERGENCY RELIEF COMPLETE ===" "Green"
