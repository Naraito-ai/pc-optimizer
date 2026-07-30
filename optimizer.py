import os
import sys
import time
import shutil
import ctypes
import winreg
import glob
import subprocess
from typing import List, Tuple, Dict, Any

try:
    import psutil
    from colorama import init, Fore, Style
    from tabulate import tabulate
except ImportError:
    print("Required packages missing. Please install dependencies using: pip install -r requirements.txt")
    sys.exit(1)

# Initialize colorama
init(autoreset=True)

# System critical process blacklist (Must never be terminated)
SYSTEM_CRITICAL_PROCESSES = {
    "svchost.exe", "lsass.exe", "csrss.exe", "winlogon.exe", "explorer.exe",
    "smss.exe", "services.exe", "system", "idle", "registry", "spoolsv.exe",
    "dwm.exe", "ctfmon.exe", "fontdrvhost.exe", "sihost.exe", "taskhostw.exe",
    "securityhealthservice.exe", "smartscreen.exe", "conhost.exe"
}

# Known bloatware / background processes to target
BLOATWARE_PROCESSES = [
    "onedrive.exe", "ms-teams.exe", "teams.exe", "discord.exe", "cortana.exe",
    "searchapp.exe", "skype.exe", "yourphone.exe", "phone-link.exe",
    "xboxstat.exe", "gamebar.exe"
]

def print_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "       [+] WINDOWS PC PERFORMANCE OPTIMIZER [+]")
    print(Fore.CYAN + Style.BRIGHT + "       Production-Ready System Tuning Tool")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65 + "\n")

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def check_admin_privileges():
    if not is_admin():
        print(Fore.RED + Style.BRIGHT + "[ERROR] Administrator privileges are required to run this tool.")
        print(Fore.YELLOW + "Please restart your terminal/PowerShell as Administrator or right-click the executable and select 'Run as Administrator'.")
        sys.exit(1)

def print_step_start(step_name: str):
    print(Fore.WHITE + Style.BRIGHT + f"\n[RUNNING] {step_name}...")

def print_step_done(step_name: str, details: str = ""):
    extra = f" ({details})" if details else ""
    print(Fore.GREEN + Style.BRIGHT + f"[DONE] {step_name}{extra}")

def print_step_skipped(step_name: str, reason: str = ""):
    extra = f" ({reason})" if reason else ""
    print(Fore.YELLOW + Style.BRIGHT + f"[SKIPPED] {step_name}{extra}")

def print_warning(msg: str):
    print(Fore.YELLOW + f"[WARNING] {msg}")

def print_error(msg: str):
    print(Fore.RED + f"[ERROR] {msg}")

def ask_user_yn(prompt_text: str, default_yes: bool = False) -> bool:
    default_str = " [Y/n]: " if default_yes else " [y/N]: "
    try:
        choice = input(Fore.LIGHTWHITE_EX + prompt_text + default_str).strip().lower()
        if not choice:
            return default_yes
        return choice.startswith('y')
    except (KeyboardInterrupt, EOFError):
        print()
        return False

def create_system_restore_point():
    print_step_start("Creating System Restore Point")
    try:
        ps_cmd = "Checkpoint-Computer -Description 'Before PC Optimizer' -RestorePointType 'MODIFY_SETTINGS'"
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            print_step_done("System Restore Point", "Created successfully")
        else:
            print_warning("Could not create restore point (System Restore may be disabled or limited by Windows policy).")
            print_step_skipped("System Restore Point", "Bypassed")
    except Exception as e:
        print_warning(f"Failed to execute restore point creation: {e}")
        print_step_skipped("System Restore Point")

def get_system_metrics() -> Dict[str, Any]:
    ram = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=0.5)
    disk = psutil.disk_usage("C:\\")
    return {
        "ram_pct": ram.percent,
        "ram_used_gb": ram.used / (1024 ** 3),
        "ram_total_gb": ram.total / (1024 ** 3),
        "cpu_pct": cpu_pct,
        "disk_free_gb": disk.free / (1024 ** 3),
        "disk_total_gb": disk.total / (1024 ** 3)
    }

# ----------------------------------------------------
# 1. MEMORY CLEANUP
# ----------------------------------------------------
def flush_standby_memory():
    """Flush working set memory of accessible processes to free RAM."""
    print_step_start("Flushing Process Working Sets")
    freed_count = 0
    try:
        psapi = ctypes.windll.psapi
        kernel32 = ctypes.windll.kernel32
        PROCESS_ALL_ACCESS = 0x1F0FFF

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                name = (proc.info['name'] or '').lower()
                if pid <= 4 or name in SYSTEM_CRITICAL_PROCESSES:
                    continue
                handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
                if handle:
                    psapi.EmptyWorkingSet(handle)
                    kernel32.CloseHandle(handle)
                    freed_count += 1
            except Exception:
                continue
        print_step_done("Flushing Process Working Sets", f"Emptied RAM working sets for {freed_count} processes")
    except Exception as e:
        print_warning(f"Working set flush encounterd an issue: {e}")
        print_step_skipped("Flushing Process Working Sets")

def kill_bloatware_and_heavy_apps():
    print_step_start("Bloatware & Non-Essential Process Optimizer")
    
    # Part A: Target bloatware
    terminated_bloat = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pname = (proc.info['name'] or '').lower()
            if pname in BLOATWARE_PROCESSES:
                proc.kill()
                terminated_bloat.append(pname)
        except Exception:
            continue

    if terminated_bloat:
        print(Fore.GREEN + f"  -> Terminated bloatware processes: {', '.join(set(terminated_bloat))}")

    # Part B: Non-system processes using > 200MB RAM
    print(Fore.CYAN + "\n  Checking non-system processes consuming > 200MB RAM...")
    heavy_procs = []
    current_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            pid = proc.info['pid']
            pname = proc.info['name'] or 'Unknown'
            pname_lower = pname.lower()
            
            if pid == current_pid or pid <= 4 or pname_lower in SYSTEM_CRITICAL_PROCESSES:
                continue
            
            rss_mb = proc.info['memory_info'].rss / (1024 * 1024)
            if rss_mb > 200:
                heavy_procs.append((pid, pname, rss_mb))
        except Exception:
            continue

    killed_count = 0
    if heavy_procs:
        print(Fore.YELLOW + f"  Found {len(heavy_procs)} heavy process(es) using > 200MB RAM:")
        for pid, name, rss in heavy_procs:
            if ask_user_yn(f"    Terminate '{name}' (PID: {pid}, RAM: {rss:.1f} MB)?"):
                try:
                    p = psutil.Process(pid)
                    p.kill()
                    killed_count += 1
                    print(Fore.GREEN + f"    [OK] Terminated {name}")
                except Exception as e:
                    print_error(f"    Could not terminate {name}: {e}")
    else:
        print(Fore.WHITE + "  No non-system processes found using > 200MB RAM.")

    print_step_done("Bloatware & Process Cleanup", f"Killed {len(set(terminated_bloat)) + killed_count} process(es)")

# ----------------------------------------------------
# 2. TEMP FILE CLEANUP
# ----------------------------------------------------
def clean_temp_files() -> float:
    print_step_start("Temporary Files & Cache Cleanup")
    bytes_freed = 0

    # Define targets
    local_appdata = os.environ.get('LOCALAPPDATA', '')
    user_temp = os.environ.get('TEMP', '')
    win_temp = r"C:\Windows\Temp"
    prefetch = r"C:\Windows\Prefetch"
    wu_cache = r"C:\Windows\SoftwareDistribution\Download"

    temp_dirs = [user_temp, win_temp, prefetch, wu_cache]

    # Safe Browser Caches
    if local_appdata:
        temp_dirs.extend([
            os.path.join(local_appdata, r"Google\Chrome\User Data\Default\Cache"),
            os.path.join(local_appdata, r"Google\Chrome\User Data\Default\Code Cache"),
            os.path.join(local_appdata, r"Microsoft\Edge\User Data\Default\Cache"),
            os.path.join(local_appdata, r"Microsoft\Edge\User Data\Default\Code Cache"),
        ])
        
        # Firefox Profile Caches
        ff_profiles = glob.glob(os.path.join(local_appdata, r"Mozilla\Firefox\Profiles\*\cache2"))
        temp_dirs.extend(ff_profiles)

    for target_dir in temp_dirs:
        if not target_dir or not os.path.exists(target_dir):
            continue

        print(Fore.WHITE + f"  Cleaning: {target_dir}")
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    bytes_freed += size
                except Exception:
                    # Locked files in use by Windows/apps skipped safely
                    pass

            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    shutil.rmtree(dir_path, ignore_errors=True)
                except Exception:
                    pass

    mb_freed = bytes_freed / (1024 * 1024)
    gb_freed = bytes_freed / (1024 ** 3)
    freed_str = f"{gb_freed:.2f} GB" if gb_freed >= 1.0 else f"{mb_freed:.1f} MB"
    print_step_done("Temporary Files & Cache Cleanup", f"Freed {freed_str}")
    return mb_freed

# ----------------------------------------------------
# 3. CPU & POWER OPTIMIZATION
# ----------------------------------------------------
def optimize_cpu_and_power():
    print_step_start("CPU & Power Plan Optimization")

    # 1. Power Plan to High Performance
    try:
        # High Performance GUID
        high_perf_guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        subprocess.run(["powercfg", "/setactive", high_perf_guid], check=True, capture_output=True)
        print(Fore.GREEN + "  [OK] Windows Power Plan switched to 'High Performance'")
    except Exception as e:
        print_warning(f"Could not set High Performance power plan: {e}")

    # 2. Disable CPU Throttling via Registry
    try:
        key_path = r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling"
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            winreg.SetValueEx(key, "PowerThrottlingOff", 0, winreg.REG_DWORD, 1)
        print(Fore.GREEN + "  [OK] Disabled Power Throttling in Registry")
    except Exception as e:
        print_warning(f"Could not update Power Throttling registry key: {e}")

    # 3. Disable Visual Effects (Animations & Effects)
    if ask_user_yn("  Optimize Windows visual effects for best performance?", default_yes=True):
        try:
            # Set VisualFXSetting to Adjust for Best Performance (2)
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)

            # Disable window animation effects
            desktop_key = r"Control Panel\Desktop"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, desktop_key, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "MinAnimate", 0, winreg.REG_SZ, "0")

            # Apply SystemParametersInfo visual updates
            SPI_SETANIMATION = 0x0043
            class ANIMATIONINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("iMinAnimate", ctypes.c_int)]
            
            anim = ANIMATIONINFO(cbSize=ctypes.sizeof(ANIMATIONINFO), iMinAnimate=0)
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETANIMATION, ctypes.sizeof(ANIMATIONINFO), ctypes.byref(anim), 3)

            print(Fore.GREEN + "  [OK] Visual effects optimized for maximum performance")
        except Exception as e:
            print_warning(f"Could not adjust visual effects settings: {e}")

    print_step_done("CPU & Power Plan Optimization")

# ----------------------------------------------------
# 4. STARTUP PROGRAM MANAGER
# ----------------------------------------------------
def manage_startup_programs():
    print_step_start("Startup Program Manager")
    
    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run")
    ]

    items_found = []
    for root, key_path, name_label in locations:
        try:
            with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        val_name, val_data, _ = winreg.EnumValue(key, index)
                        items_found.append((root, key_path, name_label, val_name, val_data))
                        index += 1
                    except OSError:
                        break
        except Exception:
            continue

    if not items_found:
        print(Fore.WHITE + "  No registry startup items found.")
        print_step_done("Startup Program Manager", "0 items processed")
        return

    print(Fore.CYAN + f"  Found {len(items_found)} startup program(s) in registry:\n")
    disabled_count = 0

    for root, key_path, label, name, command in items_found:
        print(Fore.WHITE + f"  * [{label}] {Fore.YELLOW}{name}{Fore.WHITE} -> {command[:70]}")
        if ask_user_yn(f"    Disable/Remove '{name}' from startup?"):
            try:
                with winreg.OpenKey(root, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, name)
                disabled_count += 1
                print(Fore.GREEN + f"    [OK] Disabled startup item: {name}")
            except Exception as e:
                print_error(f"    Failed to remove {name}: {e}")

    print_step_done("Startup Program Manager", f"Disabled {disabled_count} program(s)")

# ----------------------------------------------------
# 5. SERVICES OPTIMIZER
# ----------------------------------------------------
def optimize_services():
    print_step_start("Windows Services Optimizer")

    # Services list: (service_name, display_name, prompt_reason)
    target_services = [
        ("SysMain", "SysMain / Superfetch", "Preloads apps into RAM; disabling reduces disk/RAM overhead"),
        ("PrintSpooler", "Print Spooler", "Only needed if you use a printer"),
        ("DiagTrack", "Connected User Experiences and Telemetry", "Disables background Windows telemetry data collection"),
        ("WSearch", "Windows Search Indexer", "Disables file search indexing to reduce disk/CPU usage")
    ]

    disabled_services = 0
    for service_name, display_name, reason in target_services:
        prompt = f"Disable service '{display_name}' ({reason})?"
        if ask_user_yn(f"  {prompt}"):
            try:
                # Stop service
                subprocess.run(["sc", "stop", service_name], capture_output=True, text=True)
                # Disable service
                res = subprocess.run(["sc", "config", service_name, "start=disabled"], capture_output=True, text=True)
                if res.returncode == 0:
                    print(Fore.GREEN + f"  [OK] Stopped and disabled service: {display_name}")
                    disabled_services += 1
                else:
                    print_warning(f"Could not disable {display_name}: {res.stderr.strip()}")
            except Exception as e:
                print_error(f"Failed to modify service {service_name}: {e}")
        else:
            print_step_skipped(display_name, "Kept enabled by user")

    print_step_done("Windows Services Optimizer", f"{disabled_services} service(s) disabled")

# ----------------------------------------------------
# 6. NETWORK TWEAKS
# ----------------------------------------------------
def optimize_network():
    print_step_start("Network & TCP Stack Tweaks")

    net_commands = [
        ("Flushing DNS Cache", ["ipconfig", "/flushdns"]),
        ("Resetting Winsock Catalog", ["netsh", "winsock", "reset"]),
        ("Resetting IP Stack", ["netsh", "int", "ip", "reset"]),
        ("Setting TCP Auto-Tuning to Normal", ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"])
    ]

    for label, cmd in net_commands:
        try:
            print(Fore.WHITE + f"  Executing: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(Fore.GREEN + f"  [OK] {label} succeeded")
            else:
                print_warning(f"{label} notice: {res.stdout.strip() or res.stderr.strip()}")
        except Exception as e:
            print_error(f"Command failed ({' '.join(cmd)}): {e}")

    print_step_done("Network & TCP Stack Tweaks")

# ----------------------------------------------------
# MAIN EXECUTION FLOW
# ----------------------------------------------------
def main():
    check_admin_privileges()
    print_header()

    print(Fore.GREEN + Style.BRIGHT + "Administrator privileges verified. Preparing optimization task...\n")
    
    # 0. Create Restore Point
    create_system_restore_point()

    # Capture BEFORE metrics
    print(Fore.CYAN + "\nCapturing baseline system metrics...")
    before_metrics = get_system_metrics()

    # 1. Memory Cleanup
    flush_standby_memory()
    kill_bloatware_and_heavy_apps()

    # 2. Temp File Cleanup
    mb_freed = clean_temp_files()

    # 3. CPU & Power Optimization
    optimize_cpu_and_power()

    # 4. Startup Manager
    manage_startup_programs()

    # 5. Services Optimizer
    optimize_services()

    # 6. Network Tweaks
    optimize_network()

    # Capture AFTER metrics
    print(Fore.CYAN + "\nCapturing post-optimization system metrics...")
    time.sleep(1)
    after_metrics = get_system_metrics()

    # 7. BEFORE / AFTER REPORT
    print("\n" + Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "            BEFORE vs AFTER OPTIMIZATION REPORT")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)

    ram_diff = before_metrics["ram_pct"] - after_metrics["ram_pct"]
    ram_diff_str = f"-{ram_diff:.1f}%" if ram_diff >= 0 else f"+{abs(ram_diff):.1f}%"
    
    disk_diff = after_metrics["disk_free_gb"] - before_metrics["disk_free_gb"]
    disk_diff_str = f"+{disk_diff:.2f} GB" if disk_diff >= 0 else f"{disk_diff:.2f} GB"

    table_data = [
        ["RAM Usage (%)", f"{before_metrics['ram_pct']:.1f}%", f"{after_metrics['ram_pct']:.1f}%", ram_diff_str],
        ["RAM Used (GB)", f"{before_metrics['ram_used_gb']:.2f} GB", f"{after_metrics['ram_used_gb']:.2f} GB", f"{- (before_metrics['ram_used_gb'] - after_metrics['ram_used_gb']):.2f} GB"],
        ["CPU Load (%)", f"{before_metrics['cpu_pct']:.1f}%", f"{after_metrics['cpu_pct']:.1f}%", f"{after_metrics['cpu_pct'] - before_metrics['cpu_pct']:.1f}%"],
        ["C: Drive Free Space", f"{before_metrics['disk_free_gb']:.2f} GB", f"{after_metrics['disk_free_gb']:.2f} GB", disk_diff_str],
    ]

    headers = ["Metric", "Before", "After", "Improvement"]
    print(Fore.WHITE + tabulate(table_data, headers=headers, tablefmt="fancy_grid"))

    print("\n" + Fore.GREEN + Style.BRIGHT + "Optimization Complete. Your PC is now running cleaner.")
    print(Fore.YELLOW + "Note: Some network or service changes may require a system restart to take full effect.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.RED + "\n[CANCELLED] Optimization process interrupted by user.")
        sys.exit(0)
