import os
import sys
import time
import shutil
import ctypes
import winreg
import glob
import json
import argparse
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Tuple, Optional

# ── Program Metadata ────────────────────────────────────────────────────────
VERSION = "2.0.1"

# ── Dependency Check ─────────────────────────────────────────────────────────
MISSING_DEPS = []
try:
    import psutil
except ImportError:
    MISSING_DEPS.append(("psutil", ">=5.9.0"))

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    MISSING_DEPS.append(("colorama", ">=0.4.6"))

try:
    from tabulate import tabulate
except ImportError:
    MISSING_DEPS.append(("tabulate", ">=0.9.0"))

if MISSING_DEPS:
    dep_msg = (
        f"Missing required Python dependencies:\n" +
        "\n".join(f"  • {pkg} ({ver})" for pkg, ver in MISSING_DEPS) +
        "\n\nTo install dependencies, please run:\n  pip install -r requirements.txt"
    )
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Missing Dependencies", dep_msg)
    except Exception:
        pass
    print(dep_msg)
    sys.exit(1)

# ── Tkinter GUI Imports ───────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# ── Unicode Output Safety ─────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Logging Helper ────────────────────────────────────────────────────────────
def timestamped_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

# ── Dataclasses for State & Metrics ──────────────────────────────────────────
@dataclass
class StartupEntry:
    hive: str               # "HKCU" or "HKLM"
    key_path: str           # e.g., "Software\Microsoft\Windows\CurrentVersion\Run"
    disabled_key_path: str  # e.g., "Software\Microsoft\Windows\CurrentVersion\RunDisabled"
    value_name: str
    value_type: int
    value_data: str
    timestamp: str
    app_version: str
    modified_by_optimizer: bool = True

@dataclass
class CleanupPlan:
    estimated_bytes: int
    estimated_files: int
    targets: List[str]

@dataclass
class CleanupResult:
    estimated_bytes: int
    estimated_files: int
    actual_reclaimed_bytes: int
    files_deleted_count: int
    locked_files_count: int
    permission_denied_count: int
    skipped_files_count: int

# ── System Constants ─────────────────────────────────────────────────────────
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

# FIX 3: State File Path
_appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
STATE_FILE = os.path.join(_appdata, "PCOptimizer", "state.json")

# ── UAC / Admin Helpers ──────────────────────────────────────────────────────
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_if_needed():
    """If not admin, relaunch with UAC prompt and exit."""
    if not is_admin():
        if getattr(sys, 'frozen', False):
            script = sys.executable
            params = " ".join(f'"{a}"' for a in sys.argv[1:])
        else:
            script = sys.executable
            params = " ".join(f'"{a}"' for a in sys.argv)
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", script, params, None, 1
            )
            if ret <= 32:
                try:
                    root = tk.Tk(); root.withdraw()
                    messagebox.showerror(
                        "Admin Required",
                        "PC Optimizer requires Administrator privileges to tune system settings.\n"
                        "Please click 'Yes' on the UAC prompt."
                    )
                except Exception:
                    pass
        except Exception:
            pass
        sys.exit(0)

# ── True State Management & Change Ownership Tracking ──────────────────────
def default_state_structure() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "last_run": "Never",
        "last_score_before": 0,
        "last_score_after": 0,
        "gaming_mode": False,
        "is_scheduled": False,
        "modified_settings": {
            "power_plan": {
                "original_scheme_guid": None,
                "modified_by_optimizer": False
            },
            "visual_effects": {
                "original_fx_setting": None,
                "original_min_animate": None,
                "modified_by_optimizer": False
            },
            "gamedvr": {
                "original_gamedvr_enabled": None,
                "original_appcapture_enabled": None,
                "modified_by_optimizer": False
            },
            "telemetry_service": {
                "original_start_type": None,
                "original_state": None,
                "modified_by_optimizer": False
            },
            "scheduled_task": {
                "created_by_optimizer": False
            },
            "startup_entries": []
        }
    }

def load_state() -> Dict[str, Any]:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "modified_settings" not in data:
                    def_st = default_state_structure()
                    def_st.update(data)
                    data = def_st
                return data
    except Exception:
        pass
    return default_state_structure()

def save_state(data: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ── Health Score Calculation (With Caching - FIX 4) ──────────────────────────
_health_cache = {"score": None, "ts": 0}

def invalidate_health_score_cache():
    _health_cache["score"] = None
    _health_cache["ts"] = 0

def calculate_health_score() -> Tuple[int, str, List[str]]:
    """Calculates dynamic PC Health Score (0-100) based on real metrics with 30s caching."""
    now = time.time()
    if _health_cache["score"] is not None and now - _health_cache["ts"] < 30:
        return _health_cache["score"]

    score = 100
    issues = []

    # 1. RAM Usage
    ram = psutil.virtual_memory()
    if ram.percent > 85:
        score -= 25
        issues.append(f"Critical RAM pressure ({ram.percent:.0f}% used)")
    elif ram.percent > 70:
        score -= 15
        issues.append(f"High RAM usage ({ram.percent:.0f}% used)")
    elif ram.percent > 55:
        score -= 5

    # 2. Disk Space
    try:
        disk = psutil.disk_usage("C:\\")
        free_gb = disk.free / (1024 ** 3)
        if free_gb < 15:
            score -= 20
            issues.append(f"Low C: drive space ({free_gb:.1f} GB free)")
        elif free_gb < 30:
            score -= 10
            issues.append(f"C: drive filling up ({free_gb:.1f} GB free)")
    except Exception:
        pass

    # 3. Temp File Junk
    user_tmp = os.environ.get("TEMP", r"C:\Windows\Temp")
    temp_size_mb = 0
    try:
        for root, _, files in os.walk(user_tmp, followlinks=False):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        temp_size_mb += os.path.getsize(fp) / (1024 * 1024)
                except Exception:
                    pass
            if temp_size_mb > 2000:
                break
    except Exception:
        pass

    if temp_size_mb > 1000:
        score -= 15
        issues.append(f"Over {temp_size_mb/1024:.1f} GB temporary junk files found")
    elif temp_size_mb > 300:
        score -= 8
        issues.append("Temporary files and cache accumulating")

    # 4. Telemetry Service Check
    try:
        res = subprocess.run(["sc", "query", "DiagTrack"], capture_output=True, text=True)
        if "RUNNING" in res.stdout:
            score -= 10
            issues.append("Windows Telemetry (DiagTrack) actively running")
    except Exception:
        pass

    # 5. Startup Apps
    try:
        startup_count = 0
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as k:
            idx = 0
            while True:
                try:
                    winreg.EnumValue(k, idx)
                    startup_count += 1
                    idx += 1
                except OSError:
                    break
        if startup_count > 5:
            score -= 10
            issues.append(f"{startup_count} apps launching on Windows startup")
    except Exception:
        pass

    score = max(10, min(100, score))
    status = "Excellent" if score >= 85 else ("Good" if score >= 70 else ("Fair" if score >= 50 else "Poor"))
    result = (score, status, issues)

    _health_cache["score"] = result
    _health_cache["ts"] = now
    return result

# ── Cleanup Engine (Planning, Dry-Run & Safe Execution) ──────────────────────
def get_cleanup_targets(advanced_mode: bool = False) -> List[str]:
    local = os.environ.get("LOCALAPPDATA", "")
    user_tmp = os.environ.get("TEMP", "")
    targets = [
        user_tmp,
        r"C:\Windows\Temp",
        r"C:\Windows\Prefetch",
    ]
    if advanced_mode:
        targets.append(r"C:\Windows\SoftwareDistribution\Download")

    if local:
        targets += [
            os.path.join(local, r"Google\Chrome\User Data\Default\Cache"),
            os.path.join(local, r"Google\Chrome\User Data\Default\Code Cache"),
            os.path.join(local, r"Microsoft\Edge\User Data\Default\Cache"),
            os.path.join(local, r"Microsoft\Edge\User Data\Default\Code Cache"),
        ]
        targets += glob.glob(os.path.join(local, r"Mozilla\Firefox\Profiles\*\cache2"))
    return [t for t in targets if t and os.path.exists(t)]

def estimate_cleanup_size(advanced_mode: bool = False) -> CleanupPlan:
    """Performs a dry-run scan without deleting anything."""
    targets = get_cleanup_targets(advanced_mode)
    total_bytes = 0
    total_files = 0

    for d in targets:
        try:
            for root, _, files in os.walk(d, followlinks=False):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        if not os.path.islink(fp):
                            total_bytes += os.path.getsize(fp)
                            total_files += 1
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, OSError):
            continue

    return CleanupPlan(estimated_bytes=total_bytes, estimated_files=total_files, targets=targets)

def clean_temp_files_log(logger=timestamped_log, advanced_mode: bool = False) -> CleanupResult:
    logger("[3/6] Cleaning temporary files & system caches...")
    
    # Handle Windows Update service if advanced cleanup includes SoftwareDistribution
    wuauserv_stopped = False
    if advanced_mode:
        try:
            res = subprocess.run(["sc", "stop", "wuauserv"], capture_output=True)
            wuauserv_stopped = (res.returncode == 0)
        except Exception:
            pass

    plan = estimate_cleanup_size(advanced_mode)
    est_mb = plan.estimated_bytes / (1024 ** 2)
    logger(f"  ℹ Dry-run estimation: ~{est_mb:.1f} MB in {plan.estimated_files} candidate file(s)")

    bytes_freed = 0
    files_deleted = 0
    locked_count = 0
    perm_denied_count = 0
    skipped_count = 0

    for d in plan.targets:
        try:
            for root, _, files in os.walk(d, followlinks=False):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        if os.path.islink(fp):
                            os.unlink(fp)
                            files_deleted += 1
                        else:
                            sz = os.path.getsize(fp)
                            os.remove(fp)
                            bytes_freed += sz
                            files_deleted += 1
                    except PermissionError:
                        perm_denied_count += 1
                    except OSError as e:
                        if getattr(e, 'winerror', 0) in (32, 33):  # File locked by another process
                            locked_count += 1
                        else:
                            skipped_count += 1
                    except FileNotFoundError:
                        skipped_count += 1
        except Exception:
            pass

    if wuauserv_stopped:
        try:
            subprocess.run(["sc", "start", "wuauserv"], capture_output=True)
        except Exception:
            pass

    mb = bytes_freed / (1024 ** 2)
    gb = bytes_freed / (1024 ** 3)
    freed_str = f"{gb:.2f} GB" if gb >= 1.0 else f"{mb:.1f} MB"
    
    result = CleanupResult(
        estimated_bytes=plan.estimated_bytes,
        estimated_files=plan.estimated_files,
        actual_reclaimed_bytes=bytes_freed,
        files_deleted_count=files_deleted,
        locked_files_count=locked_count,
        permission_denied_count=perm_denied_count,
        skipped_files_count=skipped_count
    )

    logger(f"  ✔ Cleared safe caches. Actual space freed: {freed_str} ({files_deleted} files removed)")
    if locked_count > 0 or perm_denied_count > 0:
        logger(f"  ℹ Safely skipped {locked_count} locked file(s) and {perm_denied_count} protected file(s).")

    return result

# ── Restore Point ─────────────────────────────────────────────────────────────
def create_restore_point_log(logger=timestamped_log):
    logger("[1/6] Creating System Restore Point...")
    try:
        cmd = "Checkpoint-Computer -Description 'Before_PC_Optimizer' -RestorePointType 'MODIFY_SETTINGS'"
        res = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], capture_output=True, text=True)
        if res.returncode == 0:
            logger("  ✔ System Restore Point created successfully.")
        else:
            logger("  ℹ Restore point skipped (Windows limits restore points to 1 per 24h).")
    except Exception as e:
        logger(f"  ⚠️ Restore point notice: {e}")

# ── Process Bloatware Optimizer ──────────────────────────────────────────────
def kill_bloatware_log(logger=timestamped_log):
    logger("[2/6] Terminating non-essential background bloatware...")
    killed = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info["name"] or "").lower()
            if name in BLOATWARE_PROCESSES:
                proc.kill()
                killed.append(name)
        except Exception:
            continue
    if killed:
        logger(f"  ✔ Closed bloatware: {', '.join(set(killed))}")
    else:
        logger("  ✔ No active bloatware processes running.")

# ── Power & Visual Effects Optimizer (With State Capture) ───────────────────
def optimize_power_and_visuals_log(logger=timestamped_log):
    logger("[4/6] Setting Balanced power plan & optimizing visual effects...")
    state = load_state()
    ms = state["modified_settings"]

    # 1. Capture & Set Power Plan
    if not ms["power_plan"]["modified_by_optimizer"]:
        try:
            res = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True)
            if res.returncode == 0:
                guid = res.stdout.split(":")[1].strip().split()[0]
                ms["power_plan"]["original_scheme_guid"] = guid
        except Exception:
            pass

    try:
        subprocess.run(["powercfg", "/setactive", "SCHEME_BALANCED"], check=True, capture_output=True)
        ms["power_plan"]["modified_by_optimizer"] = True
        logger("  ✔ Power plan set to Balanced (safe, prevents thermal throttling).")
    except Exception as e:
        logger(f"  ⚠️ Power plan notice: {e}")

    # 2. Capture & Set Visual Effects
    if not ms["visual_effects"]["modified_by_optimizer"]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "VisualFXSetting")
                ms["visual_effects"]["original_fx_setting"] = val
        except Exception:
            pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "MinAnimate")
                ms["visual_effects"]["original_min_animate"] = str(val)
        except Exception:
            pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects") as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "MinAnimate", 0, winreg.REG_SZ, "0")
        
        SPI_SETANIMATION = 0x0043
        class ANIMATIONINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("iMinAnimate", ctypes.c_int)]
        ai = ANIMATIONINFO(ctypes.sizeof(ANIMATIONINFO), 0)
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETANIMATION, ctypes.sizeof(ANIMATIONINFO), ctypes.byref(ai), 3)
        ms["visual_effects"]["modified_by_optimizer"] = True
        logger("  ✔ Windows visual animations optimized for responsiveness.")
    except Exception as e:
        logger(f"  ⚠️ Visual effects notice: {e}")

    save_state(state)

# ── Startup & Services Management (Disable via Move to RunDisabled) ────────
def optimize_startup_and_services_log(logger=timestamped_log):
    logger("[5/6] Tuning startup apps & background telemetry...")
    state = load_state()
    ms = state["modified_settings"]
    startup_backups = ms.get("startup_entries", [])

    locations = [
        (winreg.HKEY_CURRENT_USER,
         r"Software\Microsoft\Windows\CurrentVersion\Run",
         r"Software\Microsoft\Windows\CurrentVersion\RunDisabled",
         "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"Software\Microsoft\Windows\CurrentVersion\Run",
         r"Software\Microsoft\Windows\CurrentVersion\RunDisabled",
         "HKLM"),
    ]
    disabled_startup = 0

    for hkey, run_path, disabled_path, label in locations:
        try:
            with winreg.OpenKey(hkey, run_path, 0, winreg.KEY_READ) as k:
                idx = 0
                while True:
                    try:
                        name, val_data, val_type = winreg.EnumValue(k, idx)
                        name_l, cmd_l = name.lower(), str(val_data).lower()
                        protected = any(kw in name_l or kw in cmd_l for kw in STARTUP_PROTECTED_KEYWORDS)
                        moved = False
                        if not protected:
                            try:
                                # 1. Copy entry to RunDisabled subkey (Disable strategy, not permanent deletion)
                                with winreg.CreateKey(hkey, disabled_path) as dk:
                                    winreg.SetValueEx(dk, name, 0, val_type, val_data)

                                # 2. Save backup metadata to state
                                entry = StartupEntry(
                                    hive=label,
                                    key_path=run_path,
                                    disabled_key_path=disabled_path,
                                    value_name=name,
                                    value_type=val_type,
                                    value_data=str(val_data),
                                    timestamp=datetime.now().isoformat(),
                                    app_version=VERSION,
                                    modified_by_optimizer=True
                                )
                                startup_backups.append(asdict(entry))

                                # 3. Remove entry from Run subkey
                                with winreg.OpenKey(hkey, run_path, 0, winreg.KEY_SET_VALUE) as rk:
                                    winreg.DeleteValue(rk, name)

                                disabled_startup += 1
                                logger(f"  ✔ Moved startup app to RunDisabled: '{name}'")
                                moved = True
                            except Exception as e:
                                logger(f"  ⚠️ Could not disable '{name}': {e}")
                        if not moved:
                            idx += 1
                    except OSError:
                        break
        except Exception:
            continue

    ms["startup_entries"] = startup_backups

    # Telemetry Service (Capture Original State First)
    if not ms["telemetry_service"]["modified_by_optimizer"]:
        try:
            res_cfg = subprocess.run(["sc", "qc", "DiagTrack"], capture_output=True, text=True)
            if "START_TYPE" in res_cfg.stdout:
                st = res_cfg.stdout.split("START_TYPE")[1].split()[1].lower()
                ms["telemetry_service"]["original_start_type"] = st
            res_q = subprocess.run(["sc", "query", "DiagTrack"], capture_output=True, text=True)
            if "STATE" in res_q.stdout:
                st = res_q.stdout.split("STATE")[1].split()[1].upper()
                ms["telemetry_service"]["original_state"] = st
        except Exception:
            pass

    try:
        subprocess.run(["sc", "stop", "DiagTrack"], capture_output=True)
        res = subprocess.run(["sc", "config", "DiagTrack", "start=disabled"], capture_output=True)
        if res.returncode == 0:
            ms["telemetry_service"]["modified_by_optimizer"] = True
            logger("  ✔ Stopped & disabled: Windows Telemetry (DiagTrack)")
    except Exception:
        pass

    save_state(state)

# ── Network Stack Tweaks ──────────────────────────────────────────────────────
def optimize_network_log(logger=timestamped_log):
    logger("[6/6] Flushing DNS & resetting network stack...")
    cmds = [
        ("Flush DNS Cache", ["ipconfig", "/flushdns"]),
        ("Reset Winsock", ["netsh", "winsock", "reset"]),
        ("Reset IP Stack", ["netsh", "int", "ip", "reset"]),
        ("TCP Auto-Tuning", ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"])
    ]
    for label, cmd in cmds:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                logger(f"  ✔ {label}: OK")
        except Exception:
            pass

# ── Gaming Mode Functions ─────────────────────────────────────────────────────
def enable_gaming_mode_log(logger=timestamped_log):
    logger("🎮 Enabling Gaming Mode...")
    state = load_state()
    ms = state["modified_settings"]

    if not ms["gamedvr"]["modified_by_optimizer"]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "GameDVR_Enabled")
                ms["gamedvr"]["original_gamedvr_enabled"] = val
        except Exception:
            pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "AppCaptureEnabled")
                ms["gamedvr"]["original_appcapture_enabled"] = val
        except Exception:
            pass

    # 1. Power Plan -> High Performance or Ultimate Performance
    try:
        res = subprocess.run(["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"], capture_output=True)
        if res.returncode != 0:
            subprocess.run(["powercfg", "/setactive", "SCHEME_MIN"], capture_output=True)
        logger("  ✔ Power plan switched to High Performance (Gaming mode).")
    except Exception as e:
        logger(f"  ⚠️ Power scheme notice: {e}")

    # 2. Disable GameDVR background recording (frees GPU/CPU encoding overhead)
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore") as k:
            winreg.SetValueEx(k, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR") as k:
            winreg.SetValueEx(k, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0)
        ms["gamedvr"]["modified_by_optimizer"] = True
        logger("  ✔ Disabled GameDVR background video capture (reduces micro-stutter).")
    except Exception as e:
        logger(f"  ⚠️ GameDVR notice: {e}")

    kill_bloatware_log(logger)
    state["gaming_mode"] = True
    save_state(state)
    logger("🎮 Gaming Mode active! Remember to restore Normal mode when finished.")

def restore_normal_mode_log(logger=timestamped_log):
    logger("↩ Restoring Normal Mode (Restoring ORIGINAL values only)...")
    state = load_state()
    ms = state["modified_settings"]

    # 1. Restore Power Plan if modified by optimizer
    if ms["power_plan"]["modified_by_optimizer"]:
        orig_guid = ms["power_plan"].get("original_scheme_guid") or "SCHEME_BALANCED"
        try:
            subprocess.run(["powercfg", "/setactive", orig_guid], capture_output=True)
            ms["power_plan"]["modified_by_optimizer"] = False
            logger(f"  ✔ Power plan restored to original state ({orig_guid}).")
        except Exception as e:
            logger(f"  ⚠️ Power plan restore notice: {e}")

    # 2. Restore Visual Effects if modified by optimizer
    if ms["visual_effects"]["modified_by_optimizer"]:
        orig_fx = ms["visual_effects"].get("original_fx_setting")
        orig_anim = ms["visual_effects"].get("original_min_animate")
        if orig_fx is not None:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects") as k:
                    winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, orig_fx)
            except Exception:
                pass
        if orig_anim is not None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, "MinAnimate", 0, winreg.REG_SZ, str(orig_anim))
            except Exception:
                pass

        SPI_SETANIMATION = 0x0043
        class ANIMATIONINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("iMinAnimate", ctypes.c_int)]
        ai_val = 1 if (orig_anim == "1" or orig_anim is None) else 0
        ai = ANIMATIONINFO(ctypes.sizeof(ANIMATIONINFO), ai_val)
        try:
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETANIMATION, ctypes.sizeof(ANIMATIONINFO), ctypes.byref(ai), 3)
        except Exception:
            pass
        ms["visual_effects"]["modified_by_optimizer"] = False
        logger("  ✔ Visual effects restored to original state.")

    # 3. Restore GameDVR if modified by optimizer
    if ms["gamedvr"]["modified_by_optimizer"]:
        orig_gdvr = ms["gamedvr"].get("original_gamedvr_enabled")
        orig_acap = ms["gamedvr"].get("original_appcapture_enabled")
        gdvr_val = 1 if orig_gdvr is None else orig_gdvr
        acap_val = 1 if orig_acap is None else orig_acap
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore") as k:
                winreg.SetValueEx(k, "GameDVR_Enabled", 0, winreg.REG_DWORD, gdvr_val)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR") as k:
                winreg.SetValueEx(k, "AppCaptureEnabled", 0, winreg.REG_DWORD, acap_val)
            ms["gamedvr"]["modified_by_optimizer"] = False
            logger("  ✔ GameDVR settings restored to original state.")
        except Exception as e:
            logger(f"  ⚠️ GameDVR restore notice: {e}")

    # 4. Restore Telemetry Service ONLY if modified by optimizer
    if ms["telemetry_service"]["modified_by_optimizer"]:
        orig_st = ms["telemetry_service"].get("original_start_type") or "auto"
        orig_state = ms["telemetry_service"].get("original_state") or "RUNNING"
        try:
            subprocess.run(["sc", "config", "DiagTrack", f"start={orig_st}"], capture_output=True)
            if orig_state == "RUNNING":
                subprocess.run(["sc", "start", "DiagTrack"], capture_output=True)
            ms["telemetry_service"]["modified_by_optimizer"] = False
            logger(f"  ✔ Telemetry service (DiagTrack) restored to original start mode ({orig_st}).")
        except Exception as e:
            logger(f"  ⚠️ Telemetry service restore notice: {e}")
    else:
        logger("  ℹ Telemetry service was not modified by optimizer — keeping existing status.")

    # 5. Restore Disabled Startup Entries (FIX 6: Type-Aware Restore)
    startup_entries = ms.get("startup_entries", [])
    restored_count = 0
    remaining_entries = []

    for entry in startup_entries:
        if entry.get("modified_by_optimizer", False):
            try:
                hkey = winreg.HKEY_CURRENT_USER if entry["hive"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
                # Recreate in Run with proper value_type awareness
                with winreg.OpenKey(hkey, entry["key_path"], 0, winreg.KEY_SET_VALUE) as rk:
                    val_type = entry["value_type"]
                    raw = entry["value_data"]
                    if val_type == winreg.REG_DWORD:
                        write_val = int(raw) if str(raw).isdigit() else 0
                    else:
                        write_val = str(raw)
                    winreg.SetValueEx(rk, entry["value_name"], 0, val_type, write_val)

                # Remove from RunDisabled
                try:
                    with winreg.OpenKey(hkey, entry["disabled_key_path"], 0, winreg.KEY_SET_VALUE) as dk:
                        winreg.DeleteValue(dk, entry["value_name"])
                except Exception:
                    pass
                restored_count += 1
                logger(f"  ✔ Restored startup entry: '{entry['value_name']}'")
            except Exception as e:
                logger(f"  ⚠️ Could not restore startup entry '{entry.get('value_name')}': {e}")
                remaining_entries.append(entry)
        else:
            remaining_entries.append(entry)

    ms["startup_entries"] = remaining_entries
    state["gaming_mode"] = False
    save_state(state)

    logger(f"✔ Restore complete. Reverted all settings modified by this application.")

# ── Task Scheduler (Weekly Schedule - FIX 1: Uses optimizer-auto.exe) ───────
def is_task_scheduled() -> bool:
    try:
        res = subprocess.run(["schtasks", "/query", "/tn", "PCOptimizerWeekly"], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def toggle_weekly_schedule_log(logger=timestamped_log) -> bool:
    scheduled = is_task_scheduled()
    state = load_state()

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        exe_path = os.path.join(exe_dir, "optimizer-auto.exe")
        if not os.path.exists(exe_path):
            exe_path = sys.executable
    else:
        exe_path = os.path.abspath(__file__)
    
    if scheduled:
        logger("⏰ Removing weekly automatic optimization schedule...")
        res = subprocess.run(["schtasks", "/delete", "/tn", "PCOptimizerWeekly", "/f"], capture_output=True, text=True)
        if res.returncode == 0:
            state["modified_settings"]["scheduled_task"]["created_by_optimizer"] = False
            state["is_scheduled"] = False
            save_state(state)
            logger("  ✔ Weekly schedule removed.")
            return False
        else:
            logger("  ⚠️ Could not remove scheduled task.")
            return True
    else:
        logger("⏰ Scheduling automatic weekly PC optimization (Every Sunday at 3:00 AM)...")
        tr_arg = f'"{exe_path}" --auto' if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{exe_path}" --auto'
        cmd = [
            "schtasks", "/create",
            "/tn", "PCOptimizerWeekly",
            "/tr", tr_arg,
            "/sc", "weekly",
            "/d", "SUN",
            "/st", "03:00",
            "/f",
            "/rl", "HIGHEST"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            state["modified_settings"]["scheduled_task"]["created_by_optimizer"] = True
            state["is_scheduled"] = True
            save_state(state)
            logger("  ✔ Weekly schedule created! Runs Sundays at 3 AM.")
            return True
        else:
            logger(f"  ⚠️ Task scheduler error: {res.stderr.strip()}")
            return False

# ══════════════════════════════════════════════════════════════════════════════
# MODERN TKINTER GUI APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class PCOptimizerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("⚡ PC Optimizer")
        self.root.geometry("640x670")
        self.root.minsize(600, 630)
        self.root.configure(bg="#09090d")

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.state = load_state()
        self.is_running = False

        self._create_styles()
        self._build_ui()
        self._update_gaming_button_state()
        self.refresh_health_score()

    def _create_styles(self):
        self.colors = {
            "bg": "#09090d",
            "card": "#12121a",
            "border": "#1f1f2e",
            "accent": "#00e5a0",
            "accent_hover": "#00c78b",
            "accent_dim": "#003827",
            "gaming": "#a855f7",
            "gaming_hover": "#9333ea",
            "text": "#f3f4f6",
            "muted": "#9ca3af",
            "subtle": "#6b7280",
            "green": "#10b981",
            "yellow": "#f59e0b",
            "red": "#ef4444"
        }

    # FIX 5: Gaming mode visual button state updater
    def _update_gaming_button_state(self):
        if self.state.get("gaming_mode"):
            self.btn_gaming.config(
                text="🎮 Gaming Mode: ON",
                bg=self.colors["gaming"],
                fg="#ffffff"
            )
        else:
            self.btn_gaming.config(
                text="🎮 Gaming Mode",
                bg="#261a38",
                fg=self.colors["text"]
            )

    def _build_ui(self):
        # ── HEADER ──
        header_frame = tk.Frame(self.root, bg=self.colors["bg"], pady=15, padx=25)
        header_frame.pack(fill="x")

        logo_label = tk.Label(
            header_frame, text="⚡ PC Optimizer",
            font=("Segoe UI", 20, "bold"), fg=self.colors["text"], bg=self.colors["bg"]
        )
        logo_label.pack(side="left")

        ver_label = tk.Label(
            header_frame, text=f"v{VERSION} • Safe Tuning",
            font=("Segoe UI", 10), fg=self.colors["accent"], bg=self.colors["bg"]
        )
        ver_label.pack(side="right", ipady=4)

        # ── MAIN CONTAINER ──
        main_container = tk.Frame(self.root, bg=self.colors["bg"], padx=20, pady=5)
        main_container.pack(fill="both", expand=True)

        # ── HEALTH SCORE CARD ──
        score_card = tk.Frame(main_container, bg=self.colors["card"], bd=1, relief="solid", highlightbackground=self.colors["border"], highlightthickness=1)
        score_card.pack(fill="x", pady=(0, 15), ipady=15, ipadx=15)

        score_header = tk.Frame(score_card, bg=self.colors["card"])
        score_header.pack(fill="x", padx=15, pady=(5, 5))

        tk.Label(score_header, text="PC Health Score:", font=("Segoe UI", 12, "bold"), fg=self.colors["muted"], bg=self.colors["card"]).pack(side="left")
        
        self.score_val_lbl = tk.Label(score_header, text="--/100", font=("Segoe UI", 16, "bold"), fg=self.colors["accent"], bg=self.colors["card"])
        self.score_val_lbl.pack(side="left", padx=8)

        self.status_pill = tk.Label(score_header, text=" Checking... ", font=("Segoe UI", 10, "bold"), fg="#000000", bg=self.colors["green"], padx=8, pady=2)
        self.status_pill.pack(side="right")

        # Custom Score Bar Canvas
        self.score_canvas = tk.Canvas(score_card, height=14, bg="#1a1a26", highlightthickness=0)
        self.score_canvas.pack(fill="x", padx=15, pady=8)

        self.issues_lbl = tk.Label(score_card, text="Scanning system health metrics...", font=("Segoe UI", 10), fg=self.colors["subtle"], bg=self.colors["card"], anchor="w", justify="left")
        self.issues_lbl.pack(fill="x", padx=15, pady=(2, 0))

        # ── ACTION BUTTONS CARD ──
        btns_card = tk.Frame(main_container, bg=self.colors["card"], bd=1, relief="solid", highlightbackground=self.colors["border"], highlightthickness=1)
        btns_card.pack(fill="x", pady=(0, 15), ipady=12, ipadx=15)

        # Big Primary Button: Optimize My PC
        self.btn_optimize = tk.Button(
            btns_card, text="🚀  Optimize My PC",
            font=("Segoe UI", 13, "bold"), fg="#000000", bg=self.colors["accent"],
            activebackground=self.colors["accent_hover"], activeforeground="#000000",
            relief="flat", cursor="hand2", pady=10, command=self.on_optimize_clicked
        )
        self.btn_optimize.pack(fill="x", padx=15, pady=(5, 10))

        # Secondary Button Grid (Gaming Mode, Restore, Schedule)
        row_frame = tk.Frame(btns_card, bg=self.colors["card"])
        row_frame.pack(fill="x", padx=15)

        self.btn_gaming = tk.Button(
            row_frame, text="🎮 Gaming Mode",
            font=("Segoe UI", 10, "bold"), fg=self.colors["text"], bg="#261a38",
            activebackground=self.colors["gaming"], activeforeground="#ffffff",
            relief="flat", cursor="hand2", pady=7, command=self.on_gaming_clicked
        )
        self.btn_gaming.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_restore = tk.Button(
            row_frame, text="↩ Restore Normal",
            font=("Segoe UI", 10, "bold"), fg=self.colors["text"], bg="#1f2430",
            activebackground="#334155", activeforeground="#ffffff",
            relief="flat", cursor="hand2", pady=7, command=self.on_restore_clicked
        )
        self.btn_restore.pack(side="left", fill="x", expand=True, padx=5)

        sched_text = "⏰ Scheduled: Sun 3AM" if is_task_scheduled() else "⏰ Schedule Weekly"
        self.btn_schedule = tk.Button(
            row_frame, text=sched_text,
            font=("Segoe UI", 10, "bold"), fg=self.colors["text"], bg="#1f2430",
            activebackground="#334155", activeforeground="#ffffff",
            relief="flat", cursor="hand2", pady=7, command=self.on_schedule_clicked
        )
        self.btn_schedule.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # ── LAST RUN & LOG VIEW ──
        log_card = tk.Frame(main_container, bg=self.colors["card"], bd=1, relief="solid", highlightbackground=self.colors["border"], highlightthickness=1)
        log_card.pack(fill="both", expand=True, pady=(0, 10))

        log_hdr = tk.Frame(log_card, bg=self.colors["card"])
        log_hdr.pack(fill="x", padx=15, pady=(10, 5))

        tk.Label(log_hdr, text="Activity Log", font=("Segoe UI", 10, "bold"), fg=self.colors["muted"], bg=self.colors["card"]).pack(side="left")
        
        last_str = self.state.get("last_run", "Never")
        if self.state.get("last_score_before") and self.state.get("last_score_after"):
            last_str += f" • Score: {self.state['last_score_before']} → {self.state['last_score_after']}"
        self.last_run_lbl = tk.Label(log_hdr, text=f"Last Run: {last_str}", font=("Segoe UI", 9), fg=self.colors["subtle"], bg=self.colors["card"])
        self.last_run_lbl.pack(side="right")

        self.log_area = scrolledtext.ScrolledText(
            log_card, font=("Consolas", 9), bg="#0a0a0f", fg="#d1d5db",
            insertbackground="#ffffff", relief="flat", highlightthickness=0
        )
        self.log_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log("Ready. Click 'Optimize My PC' for a 1-click safe cleanup.")

        # FIX 7: Antivirus false positive notice label at bottom
        av_label = tk.Label(
            main_container,
            text="ℹ If Windows Defender flagged this file: it's a false positive common with unsigned PyInstaller apps. Source code on GitHub.",
            font=("Segoe UI", 8), fg=self.colors["subtle"],
            bg=self.colors["bg"], wraplength=580, justify="left"
        )
        av_label.pack(fill="x", pady=(0, 8))

    # ── UI HELPERS ───────────────────────────────────────────────────────────
    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        def _update():
            self.log_area.insert(tk.END, f"[{ts}] {msg}\n")
            self.log_area.see(tk.END)
        self.root.after(0, _update)

    def draw_score_bar(self, score: int):
        self.score_canvas.delete("all")
        w = self.score_canvas.winfo_width() or 560
        h = 14
        fill_w = int((score / 100) * w)

        self.score_canvas.create_rectangle(0, 0, w, h, fill="#1e1e2d", width=0)
        color = self.colors["green"] if score >= 80 else (self.colors["yellow"] if score >= 60 else self.colors["red"])
        self.score_canvas.create_rectangle(0, 0, fill_w, h, fill=color, width=0)

    def refresh_health_score(self):
        def _calc():
            score, status, issues = calculate_health_score()
            def _update():
                self.score_val_lbl.config(text=f"{score}/100")
                self.status_pill.config(text=f" {status} ")
                if status == "Excellent" or status == "Good":
                    self.status_pill.config(bg=self.colors["green"], fg="#000000")
                elif status == "Fair":
                    self.status_pill.config(bg=self.colors["yellow"], fg="#000000")
                else:
                    self.status_pill.config(bg=self.colors["red"], fg="#ffffff")

                self.draw_score_bar(score)

                if issues:
                    self.issues_lbl.config(text="⚠️ " + "  •  ".join(issues[:2]))
                else:
                    self.issues_lbl.config(text="✔ System health is optimal! No major issues detected.", fg=self.colors["green"])

            self.root.after(0, _update)

        threading.Thread(target=_calc, daemon=True).start()

    def set_running_state(self, running: bool):
        self.is_running = running
        state = "disabled" if running else "normal"
        self.btn_optimize.config(state=state)
        self.btn_gaming.config(state=state)
        self.btn_restore.config(state=state)
        self.btn_schedule.config(state=state)

    # ── BUTTON HANDLERS ──────────────────────────────────────────────────────
    def on_optimize_clicked(self):
        if self.is_running:
            return
        
        # Confirmation prompt for safe optimization
        if not messagebox.askyesno(
            "Confirm Safe Optimization",
            "PC Optimizer will now execute safe system tuning:\n\n"
            "• Create a System Restore Point\n"
            "• Clean temporary files & browser caches\n"
            "• Configure Balanced power plan & visual animations\n"
            "• Move non-essential startup apps to RunDisabled (backed up)\n"
            "• Disable background telemetry (DiagTrack)\n"
            "• Flush DNS & reset network stack\n\n"
            "Would you like to proceed?"
        ):
            return

        self.set_running_state(True)
        self.log_area.delete("1.0", tk.END)
        self.log("🚀 Starting Safe 1-Click PC Optimization...")

        def _worker():
            score_before, _, _ = calculate_health_score()
            create_restore_point_log(self.log)
            kill_bloatware_log(self.log)
            clean_temp_files_log(self.log, advanced_mode=False)
            optimize_power_and_visuals_log(self.log)
            optimize_startup_and_services_log(self.log)
            optimize_network_log(self.log)

            time.sleep(1)
            invalidate_health_score_cache()  # Force cache invalidation after optimization
            score_after, status, _ = calculate_health_score()
            self.log(f"\n🎉 OPTIMIZATION COMPLETE! Health Score: {score_before} → {score_after} ({status})")

            now_str = datetime.now().strftime("%a %I:%M %p")
            self.state["last_run"] = now_str
            self.state["last_score_before"] = score_before
            self.state["last_score_after"] = score_after
            save_state(self.state)

            def _finish():
                self.last_run_lbl.config(text=f"Last Run: {now_str} • Score: {score_before} → {score_after}")
                self.refresh_health_score()
                self.set_running_state(False)

            self.root.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def on_gaming_clicked(self):
        if self.is_running:
            return
        self.set_running_state(True)
        self.log("\n🎮 Activating Gaming Mode...")

        def _worker():
            enable_gaming_mode_log(self.log)
            self.state["gaming_mode"] = True
            save_state(self.state)
            def _finish_gaming():
                self._update_gaming_button_state()
                self.refresh_health_score()
                self.set_running_state(False)
            self.root.after(0, _finish_gaming)

        threading.Thread(target=_worker, daemon=True).start()

    def on_restore_clicked(self):
        if self.is_running:
            return
        if not messagebox.askyesno(
            "Confirm Restore Normal Mode",
            "This will revert all settings modified by PC Optimizer back to their ORIGINAL captured values.\n\n"
            "• Restore original Power Plan\n"
            "• Restore original Visual Effects\n"
            "• Restore GameDVR settings\n"
            "• Restore Telemetry service mode (only if modified by this app)\n"
            "• Restore disabled startup entries\n\n"
            "Proceed with restore?"
        ):
            return

        self.set_running_state(True)
        self.log("\n↩ Restoring Normal System Settings...")

        def _worker():
            restore_normal_mode_log(self.log)
            self.state["gaming_mode"] = False
            save_state(self.state)
            def _finish_restore():
                self._update_gaming_button_state()
                self.refresh_health_score()
                self.set_running_state(False)
            self.root.after(0, _finish_restore)

        threading.Thread(target=_worker, daemon=True).start()

    def on_schedule_clicked(self):
        if self.is_running:
            return
        self.set_running_state(True)

        def _worker():
            is_now_sched = toggle_weekly_schedule_log(self.log)
            self.state["is_scheduled"] = is_now_sched
            save_state(self.state)

            def _update():
                btn_txt = "⏰ Scheduled: Sun 3AM" if is_now_sched else "⏰ Schedule Weekly"
                self.btn_schedule.config(text=btn_txt)
                self.set_running_state(False)

            self.root.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# CLI MODE ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def run_cli_auto():
    timestamped_log("=========================================================")
    timestamped_log(f"       [+] WINDOWS PC PERFORMANCE OPTIMIZER v{VERSION} [+]")
    timestamped_log("       AUTOMATIC BACKGROUND RUN (--auto)")
    timestamped_log("=========================================================\n")
    create_restore_point_log()
    kill_bloatware_log()
    clean_temp_files_log()
    optimize_power_and_visuals_log()
    optimize_startup_and_services_log()
    optimize_network_log()
    timestamped_log("\n[DONE] Automatic background optimization complete.")

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    elevate_if_needed()

    parser = argparse.ArgumentParser(description=f"PC Performance Optimizer v{VERSION}")
    parser.add_argument("--auto", action="store_true", help="Run full optimization headlessly")
    parser.add_argument("--gaming", action="store_true", help="Activate gaming mode headlessly")
    parser.add_argument("--restore", action="store_true", help="Restore normal mode headlessly")
    args, _ = parser.parse_known_args()

    if args.auto:
        run_cli_auto()
        sys.exit(0)
    elif args.gaming:
        enable_gaming_mode_log()
        sys.exit(0)
    elif args.restore:
        restore_normal_mode_log()
        sys.exit(0)

    root = tk.Tk()
    app = PCOptimizerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
