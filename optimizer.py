import os
import sys
import time
import shutil
import ctypes
import winreg
import glob
import argparse
import subprocess
from typing import List, Dict, Any

# ── Unicode safety: prevent CP1252 crashes on Windows CMD ──────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import psutil
    from colorama import init, Fore, Style
    from tabulate import tabulate
except ImportError:
    print("Required packages missing. Run: pip install -r requirements.txt")
    sys.exit(1)

init(autoreset=True)

# ── Argument parsing ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Windows PC Performance Optimizer")
parser.add_argument("--auto", "-a", action="store_true",
                    help="Run all safe optimizations automatically (no prompts)")
parser.add_argument("--interactive", "-i", action="store_true",
                    help="Force interactive prompt mode")
args, _ = parser.parse_known_args()

# Default to AUTO unless --interactive is explicitly passed
AUTO_MODE = not args.interactive

# ── Constants ───────────────────────────────────────────────────────────────
SYSTEM_CRITICAL_PROCESSES = {
    "svchost.exe", "lsass.exe", "csrss.exe", "winlogon.exe", "explorer.exe",
    "smss.exe", "services.exe", "system", "idle", "registry", "spoolsv.exe",
    "dwm.exe", "ctfmon.exe", "fontdrvhost.exe", "sihost.exe", "taskhostw.exe",
    "securityhealthservice.exe", "smartscreen.exe", "conhost.exe",
    "memcompression", "vmmem", "vmmemwsl",
}

BLOATWARE_PROCESSES = [
    "onedrive.exe", "ms-teams.exe", "teams.exe", "discord.exe", "cortana.exe",
    "searchapp.exe", "skype.exe", "yourphone.exe", "phone-link.exe",
    "xboxstat.exe", "gamebar.exe",
]

STARTUP_PROTECTED_KEYWORDS = [
    "securityhealth", "realtek", "nvidia", "amd", "intel",
    "antivirus", "defender", "bluetooth",
]

# ── UAC / Admin helpers ─────────────────────────────────────────────────────
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_if_needed():
    """If not admin, relaunch with UAC elevation prompt and exit current process."""
    if not is_admin():
        script = sys.executable
        params  = " ".join(f'"{a}"' for a in sys.argv)
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", script, params, None, 1
            )
            if ret <= 32:
                # UAC was cancelled or failed — show a message box
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk(); root.withdraw()
                    messagebox.showerror(
                        "Admin Required",
                        "This tool requires Administrator privileges.\n"
                        "Right-click the .exe and choose 'Run as administrator'."
                    )
                except Exception:
                    pass
        except Exception:
            pass
        sys.exit(0)

def check_admin_privileges():
    elevate_if_needed()   # Triggers UAC and relaunches; only continues if already admin

# ── UI helpers ──────────────────────────────────────────────────────────────
def print_header():
    os.system("cls")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "       [+] WINDOWS PC PERFORMANCE OPTIMIZER [+]")
    print(Fore.CYAN + Style.BRIGHT + "       Production-Ready System Tuning Tool")
    mode_label = "AUTOMATIC (--auto)" if AUTO_MODE else "INTERACTIVE"
    mode_color = Fore.MAGENTA if AUTO_MODE else Fore.YELLOW
    print(mode_color + Style.BRIGHT + f"       MODE: {mode_label}")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65 + "\n")

def print_step_start(name: str):
    print(Fore.WHITE + Style.BRIGHT + f"\n[RUNNING] {name}...")

def print_step_done(name: str, detail: str = ""):
    extra = f" ({detail})" if detail else ""
    print(Fore.GREEN + Style.BRIGHT + f"[DONE] {name}{extra}")

def print_step_skipped(name: str, reason: str = ""):
    extra = f" ({reason})" if reason else ""
    print(Fore.YELLOW + Style.BRIGHT + f"[SKIPPED] {name}{extra}")

def print_auto(msg: str):
    print(Fore.MAGENTA + Style.BRIGHT + f"  [AUTO] {msg}")

def print_warn(msg: str):
    print(Fore.YELLOW + f"[WARNING] {msg}")

def print_err(msg: str):
    print(Fore.RED + f"[ERROR] {msg}")

def ask_yn(prompt: str, default_yes: bool = False) -> bool:
    """Always returns True in AUTO_MODE without prompting."""
    if AUTO_MODE:
        return True
    suffix = " [Y/n]: " if default_yes else " [y/N]: "
    try:
        choice = input(Fore.LIGHTWHITE_EX + prompt + suffix).strip().lower()
        if not choice:
            return default_yes
        return choice.startswith("y")
    except (KeyboardInterrupt, EOFError):
        print()
        return False

# ── System metrics ──────────────────────────────────────────────────────────
def get_metrics() -> Dict[str, Any]:
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    return {
        "ram_pct":      ram.percent,
        "ram_used_gb":  ram.used  / (1024 ** 3),
        "ram_total_gb": ram.total / (1024 ** 3),
        "cpu_pct":      psutil.cpu_percent(interval=0.5),
        "disk_free_gb": disk.free  / (1024 ** 3),
        "disk_total_gb":disk.total / (1024 ** 3),
    }

# ══════════════════════════════════════════════════════════════════════════════
# STEP 0 — System Restore Point
# ══════════════════════════════════════════════════════════════════════════════
def create_restore_point():
    print_step_start("Creating System Restore Point")
    try:
        cmd = ("Checkpoint-Computer "
               "-Description 'Before_PC_Optimizer' "
               "-RestorePointType 'MODIFY_SETTINGS'")
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", cmd],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            print_step_done("System Restore Point", "Created successfully")
        else:
            print_warn("Could not create restore point (may be rate-limited by Windows).")
            print_step_skipped("System Restore Point")
    except Exception as e:
        print_warn(f"Restore point error: {e}")
        print_step_skipped("System Restore Point")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Bloatware process killer  (NO working-set flush)
# ══════════════════════════════════════════════════════════════════════════════
def kill_bloatware():
    print_step_start("Bloatware & Non-Essential Process Optimizer")
    killed: List[str] = []

    # Auto-kill known bloatware
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info["name"] or "").lower()
            if name in BLOATWARE_PROCESSES:
                proc.kill()
                killed.append(name)
        except Exception:
            continue

    if killed:
        names = ", ".join(sorted(set(killed)))
        if AUTO_MODE:
            print_auto(f"Terminated bloatware: {names}")
        else:
            print(Fore.GREEN + f"  -> Terminated: {names}")

    # Interactive: ask about heavy user processes
    if not AUTO_MODE:
        current_pid = os.getpid()
        heavy = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                p   = proc.info
                pid = p["pid"]
                nm  = p["name"] or "Unknown"
                if pid == current_pid or pid <= 4 or nm.lower() in SYSTEM_CRITICAL_PROCESSES:
                    continue
                mb = p["memory_info"].rss / (1024 * 1024)
                if mb > 200:
                    heavy.append((pid, nm, mb))
            except Exception:
                continue
        if heavy:
            print(Fore.YELLOW + f"\n  {len(heavy)} process(es) using >200 MB RAM:")
            for pid, nm, mb in heavy:
                if ask_yn(f"    Terminate '{nm}' (PID {pid}, {mb:.0f} MB)?"):
                    try:
                        psutil.Process(pid).kill()
                        print(Fore.GREEN + f"    [OK] Terminated {nm}")
                    except Exception as e:
                        print_err(f"    Could not terminate {nm}: {e}")
    else:
        print_auto("Skipped killing user apps >200 MB (preserves open work)")

    print_step_done("Bloatware & Process Optimizer",
                    f"{len(set(killed))} bloatware process(es) removed")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Temp file & cache cleanup
# ══════════════════════════════════════════════════════════════════════════════
def clean_temp_files() -> float:
    print_step_start("Temporary Files & Cache Cleanup")
    local   = os.environ.get("LOCALAPPDATA", "")
    user_tmp= os.environ.get("TEMP", "")
    targets = [
        user_tmp,
        r"C:\Windows\Temp",
        r"C:\Windows\Prefetch",
        r"C:\Windows\SoftwareDistribution\Download",
    ]
    if local:
        targets += [
            os.path.join(local, r"Google\Chrome\User Data\Default\Cache"),
            os.path.join(local, r"Google\Chrome\User Data\Default\Code Cache"),
            os.path.join(local, r"Microsoft\Edge\User Data\Default\Cache"),
            os.path.join(local, r"Microsoft\Edge\User Data\Default\Code Cache"),
        ]
        targets += glob.glob(
            os.path.join(local, r"Mozilla\Firefox\Profiles\*\cache2")
        )

    bytes_freed = 0
    for d in targets:
        if not d or not os.path.exists(d):
            continue
        if AUTO_MODE:
            print_auto(f"Cleaning: {d}")
        else:
            print(Fore.WHITE + f"  Cleaning: {d}")
        for root, dirs, files in os.walk(d):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    bytes_freed += os.path.getsize(fp)
                    os.remove(fp)
                except Exception:
                    pass
            for sd in dirs:
                try:
                    shutil.rmtree(os.path.join(root, sd), ignore_errors=True)
                except Exception:
                    pass

    mb = bytes_freed / (1024 ** 2)
    gb = bytes_freed / (1024 ** 3)
    freed_str = f"{gb:.2f} GB" if gb >= 1.0 else f"{mb:.1f} MB"
    print_step_done("Temp & Cache Cleanup", f"Freed {freed_str}")
    return mb

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Power & visual effects  (BALANCED plan — no High Performance)
# ══════════════════════════════════════════════════════════════════════════════
def optimize_power_and_visuals():
    print_step_start("Power Plan & Visual Effects Optimization")

    # BALANCED — safe for laptops and desktops.
    # High Performance forces CPU to 100% clock speed → heat → throttle → lag.
    try:
        subprocess.run(["powercfg", "/setactive", "SCHEME_BALANCED"],
                       check=True, capture_output=True)
        if AUTO_MODE:
            print_auto("Power plan set to Balanced (prevents CPU overheating)")
        else:
            print(Fore.GREEN + "  [OK] Power plan: Balanced")
    except Exception as e:
        print_warn(f"Could not set Balanced plan: {e}")

    # Visual effects → "Adjust for best performance"
    if ask_yn("  Optimize Windows visual effects for performance?", default_yes=True):
        try:
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
            ) as k:
                winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, 2)

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE
            ) as k:
                winreg.SetValueEx(k, "MinAnimate", 0, winreg.REG_SZ, "0")

            SPI_SETANIMATION = 0x0043
            class ANIMATIONINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("iMinAnimate", ctypes.c_int)]
            ai = ANIMATIONINFO(ctypes.sizeof(ANIMATIONINFO), 0)
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETANIMATION, ctypes.sizeof(ANIMATIONINFO), ctypes.byref(ai), 3
            )
            if AUTO_MODE:
                print_auto("Visual effects optimized for maximum performance")
            else:
                print(Fore.GREEN + "  [OK] Visual effects optimized")
        except Exception as e:
            print_warn(f"Could not adjust visual effects: {e}")

    print_step_done("Power Plan & Visual Effects")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Startup program manager
# ══════════════════════════════════════════════════════════════════════════════
def manage_startup():
    print_step_start("Startup Program Manager")
    locations = [
        (winreg.HKEY_CURRENT_USER,
         r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    ]
    items = []
    for root, path, label in locations:
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as k:
                idx = 0
                while True:
                    try:
                        name, data, _ = winreg.EnumValue(k, idx)
                        items.append((root, path, label, name, data))
                        idx += 1
                    except OSError:
                        break
        except Exception:
            continue

    if not items:
        print(Fore.WHITE + "  No registry startup items found.")
        print_step_done("Startup Manager", "0 items processed")
        return

    print(Fore.CYAN + f"  Found {len(items)} startup item(s)\n")
    disabled = 0
    for root, path, label, name, cmd in items:
        name_l = name.lower()
        cmd_l  = cmd.lower()
        protected = any(
            kw in name_l or kw in cmd_l for kw in STARTUP_PROTECTED_KEYWORDS
        )
        if AUTO_MODE:
            if protected:
                print_auto(f"Kept protected startup item: '{name}'")
            else:
                try:
                    with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as k:
                        winreg.DeleteValue(k, name)
                    disabled += 1
                    print_auto(f"Disabled non-essential startup item: '{name}'")
                except Exception as e:
                    print_err(f"  Could not remove '{name}': {e}")
        else:
            print(Fore.WHITE + f"  [{label}] {Fore.YELLOW}{name}{Fore.WHITE} -> {cmd[:70]}")
            if ask_yn(f"    Disable '{name}' from startup?"):
                try:
                    with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as k:
                        winreg.DeleteValue(k, name)
                    disabled += 1
                    print(Fore.GREEN + f"    [OK] Disabled: {name}")
                except Exception as e:
                    print_err(f"    Failed: {e}")

    print_step_done("Startup Manager", f"{disabled} item(s) disabled")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Windows services optimizer
#          SysMain is intentionally NOT in this list.
#          Disabling Superfetch causes cold-disk app launches → lag.
# ══════════════════════════════════════════════════════════════════════════════
def optimize_services():
    print_step_start("Windows Services Optimizer")

    # allow_auto=True  → disabled in --auto mode
    # allow_auto=False → skipped in --auto mode (needs manual confirmation)
    services = [
        ("DiagTrack",    "Connected User Experiences & Telemetry",
         "Background Windows telemetry — safe to disable", True),
        ("WSearch",      "Windows Search Indexer",
         "File indexing — reduces background disk/CPU", True),
        ("PrintSpooler", "Print Spooler",
         "Only needed if you print documents", False),
    ]

    disabled = 0
    for svc, display, reason, allow_auto in services:
        if AUTO_MODE:
            if not allow_auto:
                print_auto(f"Skipped '{display}' (manual confirmation required)")
                print_step_skipped(display, "skipped in auto mode")
                continue
            try:
                subprocess.run(["sc", "stop",   svc], capture_output=True)
                res = subprocess.run(
                    ["sc", "config", svc, "start=disabled"],
                    capture_output=True, text=True
                )
                if res.returncode == 0:
                    print_auto(f"Stopped & disabled: '{display}'")
                    disabled += 1
                else:
                    print_warn(f"Could not disable {display}: {res.stderr.strip()}")
            except Exception as e:
                print_err(f"Service error ({svc}): {e}")
        else:
            if ask_yn(f"  Disable '{display}' ({reason})?"):
                try:
                    subprocess.run(["sc", "stop",   svc], capture_output=True)
                    res = subprocess.run(
                        ["sc", "config", svc, "start=disabled"],
                        capture_output=True, text=True
                    )
                    if res.returncode == 0:
                        print(Fore.GREEN + f"  [OK] Disabled: {display}")
                        disabled += 1
                    else:
                        print_warn(f"Could not disable {display}")
                except Exception as e:
                    print_err(f"Failed ({svc}): {e}")
            else:
                print_step_skipped(display, "kept by user")

    print_step_done("Services Optimizer", f"{disabled} service(s) disabled")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Network tweaks
# ══════════════════════════════════════════════════════════════════════════════
def optimize_network():
    print_step_start("Network & TCP Stack Tweaks")
    cmds = [
        ("Flush DNS Cache",            ["ipconfig", "/flushdns"]),
        ("Reset Winsock Catalog",      ["netsh", "winsock", "reset"]),
        ("Reset IP Stack",             ["netsh", "int", "ip", "reset"]),
        ("Set TCP Auto-Tuning Normal", ["netsh", "int", "tcp", "set",
                                        "global", "autotuninglevel=normal"]),
    ]
    for label, cmd in cmds:
        try:
            if AUTO_MODE:
                print_auto(f"Running: {' '.join(cmd)}")
            else:
                print(Fore.WHITE + f"  Running: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True)
            status = "OK" if res.returncode == 0 else "notice"
            detail = res.stdout.strip() or res.stderr.strip()
            if res.returncode == 0:
                if AUTO_MODE:
                    print_auto(f"{label}: done")
                else:
                    print(Fore.GREEN + f"  [OK] {label}")
            else:
                print_warn(f"{label} {status}: {detail[:120]}")
        except Exception as e:
            print_err(f"{label} failed: {e}")

    print_step_done("Network & TCP Stack Tweaks")

# ══════════════════════════════════════════════════════════════════════════════
# BEFORE / AFTER REPORT
# ══════════════════════════════════════════════════════════════════════════════
def print_report(before: Dict, after: Dict, mb_freed: float):
    print("\n" + Fore.CYAN + Style.BRIGHT + "=" * 65)
    print(Fore.CYAN + Style.BRIGHT + "          BEFORE vs AFTER OPTIMIZATION REPORT")
    print(Fore.CYAN + Style.BRIGHT + "=" * 65)

    ram_diff  = before["ram_pct"] - after["ram_pct"]
    disk_diff = after["disk_free_gb"] - before["disk_free_gb"]

    table = [
        ["RAM Usage (%)",
         f"{before['ram_pct']:.1f}%",
         f"{after['ram_pct']:.1f}%",
         f"-{ram_diff:.1f}%" if ram_diff >= 0 else f"+{abs(ram_diff):.1f}%"],
        ["RAM Used (GB)",
         f"{before['ram_used_gb']:.2f} GB",
         f"{after['ram_used_gb']:.2f} GB",
         f"{after['ram_used_gb'] - before['ram_used_gb']:+.2f} GB"],
        ["CPU Load (%)",
         f"{before['cpu_pct']:.1f}%",
         f"{after['cpu_pct']:.1f}%",
         f"{after['cpu_pct'] - before['cpu_pct']:+.1f}%"],
        ["C: Free Space",
         f"{before['disk_free_gb']:.2f} GB",
         f"{after['disk_free_gb']:.2f} GB",
         f"{disk_diff:+.2f} GB"],
    ]
    try:
        print(Fore.WHITE + tabulate(
            table, headers=["Metric", "Before", "After", "Change"],
            tablefmt="simple"
        ))
    except Exception:
        # Absolute fallback — plain text
        for row in table:
            print("  " + " | ".join(str(c) for c in row))

    print("\n" + Fore.GREEN + Style.BRIGHT +
          "Optimization Complete. Your PC is now running cleaner.")
    print(Fore.YELLOW +
          "Note: Network changes (Winsock/IP reset) require a restart to fully apply.\n")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    check_admin_privileges()
    print_header()
    print(Fore.GREEN + Style.BRIGHT +
          "Administrator privileges verified. Starting optimization...\n")

    create_restore_point()

    print(Fore.CYAN + "\nCapturing baseline system metrics...")
    before = get_metrics()

    kill_bloatware()
    mb_freed = clean_temp_files()
    optimize_power_and_visuals()
    manage_startup()
    optimize_services()
    optimize_network()

    print(Fore.CYAN + "\nCapturing post-optimization metrics...")
    time.sleep(1)
    after = get_metrics()

    print_report(before, after, mb_freed)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.RED + "\n[CANCELLED] Interrupted by user.")
        sys.exit(0)
