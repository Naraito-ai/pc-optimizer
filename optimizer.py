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
from datetime import datetime
from typing import List, Dict, Any, Tuple

# ── Import Third-Party Libraries ─────────────────────────────────────────────
try:
    import psutil
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil", "tabulate", "colorama"])
    import psutil

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    pass

# ── Tkinter GUI Imports ───────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# ── Unicode Output Safety ─────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

STATE_FILE = os.path.join(os.environ.get("APPDATA", r"C:\AppData"), "PCOptimizer", "state.json")

# ── UAC / Admin Helpers ──────────────────────────────────────────────────────
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_if_needed():
    """If not admin, relaunch with UAC prompt and exit."""
    if not is_admin():
        script = sys.executable
        params = " ".join(f'"{a}"' for a in sys.argv)
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", script, params, None, 1
            )
            if ret <= 32:
                try:
                    root = tk.Tk()
                    root.withdraw()
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

# ── State Management ─────────────────────────────────────────────────────────
def load_state() -> Dict[str, Any]:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "last_run": "Never",
        "last_score_before": 0,
        "last_score_after": 0,
        "gaming_mode": False,
        "is_scheduled": False
    }

def save_state(data: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ── Health Score Calculation ──────────────────────────────────────────────────
def calculate_health_score() -> Tuple[int, str, List[str]]:
    """Calculates dynamic PC Health Score (0-100) based on real metrics."""
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
        for root, _, files in os.walk(user_tmp):
            for f in files:
                try:
                    temp_size_mb += os.path.getsize(os.path.join(root, f)) / (1024 * 1024)
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
    return score, status, issues

# ── Optimization Core Engine Functions ───────────────────────────────────────
def create_restore_point_log(logger=print):
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

def kill_bloatware_log(logger=print):
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

def clean_temp_files_log(logger=print) -> float:
    logger("[3/6] Cleaning temporary files & system caches...")
    local = os.environ.get("LOCALAPPDATA", "")
    user_tmp = os.environ.get("TEMP", "")
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
        targets += glob.glob(os.path.join(local, r"Mozilla\Firefox\Profiles\*\cache2"))

    bytes_freed = 0
    for d in targets:
        if not d or not os.path.exists(d):
            continue
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
    logger(f"  ✔ Cleared safe caches. Space freed: {freed_str}")
    return mb

def optimize_power_and_visuals_log(logger=print):
    logger("[4/6] Setting Balanced power plan & optimizing visual effects...")
    try:
        subprocess.run(["powercfg", "/setactive", "SCHEME_BALANCED"], check=True, capture_output=True)
        logger("  ✔ Power plan set to Balanced (safe, prevents thermal throttling).")
    except Exception as e:
        logger(f"  ⚠️ Power plan notice: {e}")

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects") as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "MinAnimate", 0, winreg.REG_SZ, "0")
        logger("  ✔ Windows visual animations optimized for responsiveness.")
    except Exception as e:
        logger(f"  ⚠️ Visual effects notice: {e}")

def optimize_startup_and_services_log(logger=print):
    logger("[5/6] Tuning startup apps & background telemetry...")
    # Startup apps
    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    disabled_startup = 0
    for root, path in locations:
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as k:
                idx = 0
                while True:
                    try:
                        name, cmd, _ = winreg.EnumValue(k, idx)
                        name_l, cmd_l = name.lower(), cmd.lower()
                        protected = any(kw in name_l or kw in cmd_l for kw in STARTUP_PROTECTED_KEYWORDS)
                        if not protected:
                            try:
                                with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as wk:
                                    winreg.DeleteValue(wk, name)
                                disabled_startup += 1
                                logger(f"  ✔ Disabled startup app: '{name}'")
                            except Exception:
                                pass
                        idx += 1
                    except OSError:
                        break
        except Exception:
            continue

    # Telemetry and Search
    services = [("DiagTrack", "Windows Telemetry"), ("WSearch", "Windows Search Indexer")]
    for svc, display in services:
        try:
            subprocess.run(["sc", "stop", svc], capture_output=True)
            res = subprocess.run(["sc", "config", svc, "start=disabled"], capture_output=True)
            if res.returncode == 0:
                logger(f"  ✔ Stopped & disabled: {display}")
        except Exception:
            pass

def optimize_network_log(logger=print):
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
def enable_gaming_mode_log(logger=print):
    logger("🎮 Enabling Gaming Mode...")
    # 1. Power Plan -> High Performance or Ultimate Performance
    try:
        # Check if High performance scheme exists
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
        logger("  ✔ Disabled GameDVR background video capture (reduces micro-stutter).")
    except Exception as e:
        logger(f"  ⚠️ GameDVR notice: {e}")

    # 3. Clean up non-essential background processes
    kill_bloatware_log(logger)
    logger("🎮 Gaming Mode active! Remember to restore Normal mode when finished.")

def restore_normal_mode_log(logger=print):
    logger("↩ Restoring Normal Mode...")
    try:
        subprocess.run(["powercfg", "/setactive", "SCHEME_BALANCED"], capture_output=True)
        logger("  ✔ Power plan restored to Balanced (cool & quiet).")
    except Exception as e:
        logger(f"  ⚠️ Power plan notice: {e}")

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore") as k:
            winreg.SetValueEx(k, "GameDVR_Enabled", 0, winreg.REG_DWORD, 1)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR") as k:
            winreg.SetValueEx(k, "AppCaptureEnabled", 0, winreg.REG_DWORD, 1)
        logger("  ✔ Default Windows settings restored.")
    except Exception as e:
        logger(f"  ⚠️ Restore notice: {e}")

    logger("✔ Restored to Normal Mode.")

# ── Task Scheduler (Weekly Schedule) ──────────────────────────────────────────
def is_task_scheduled() -> bool:
    try:
        res = subprocess.run(["schtasks", "/query", "/tn", "PCOptimizerWeekly"], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def toggle_weekly_schedule_log(logger=print) -> bool:
    scheduled = is_task_scheduled()
    exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    
    if scheduled:
        logger("⏰ Removing weekly automatic optimization schedule...")
        res = subprocess.run(["schtasks", "/delete", "/tn", "PCOptimizerWeekly", "/f"], capture_output=True, text=True)
        if res.returncode == 0:
            logger("  ✔ Weekly schedule removed.")
            return False
        else:
            logger("  ⚠️ Could not remove scheduled task.")
            return True
    else:
        logger("⏰ Scheduling automatic weekly PC optimization (Every Sunday at 3:00 AM)...")
        cmd = f'schtasks /create /tn "PCOptimizerWeekly" /tr "\"{exe_path}\" --auto" /sc weekly /d SUN /st 03:00 /f /rl HIGHEST'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
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
        self.root.geometry("640x660")
        self.root.minsize(600, 620)
        self.root.configure(bg="#09090d")

        # Set Window Icon if possible
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.state = load_state()
        self.is_running = False

        self._create_styles()
        self._build_ui()
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
            header_frame, text="v2.0 • Safe Tuning",
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
            log_card, font=("Consolas", 9.5), bg="#0a0a0f", fg="#d1d5db",
            insertbackground="#ffffff", relief="flat", highlightthickness=0
        )
        self.log_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_area.insert(tk.END, "Ready. Click 'Optimize My PC' for a 1-click safe cleanup.\n")

    # ── UI HELPERS ───────────────────────────────────────────────────────────
    def log(self, msg: str):
        def _update():
            self.log_area.insert(tk.END, f"{msg}\n")
            self.log_area.see(tk.END)
        self.root.after(0, _update)

    def draw_score_bar(self, score: int):
        self.score_canvas.delete("all")
        w = self.score_canvas.winfo_width() or 560
        h = 14
        fill_w = int((score / 100) * w)

        # Bar background
        self.score_canvas.create_rectangle(0, 0, w, h, fill="#1e1e2d", width=0)

        # Color based on score
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
        self.set_running_state(True)
        self.log_area.delete("1.0", tk.END)
        self.log("🚀 Starting Safe 1-Click PC Optimization...")

        def _worker():
            score_before, _, _ = calculate_health_score()
            create_restore_point_log(self.log)
            kill_bloatware_log(self.log)
            clean_temp_files_log(self.log)
            optimize_power_and_visuals_log(self.log)
            optimize_startup_and_services_log(self.log)
            optimize_network_log(self.log)

            time.sleep(1)
            score_after, status, _ = calculate_health_score()
            self.log(f"\n🎉 OPTIMIZATION COMPLETE! Health Score: {score_before} → {score_after} ({status})")

            # Update State
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
            self.root.after(0, lambda: (self.refresh_health_score(), self.set_running_state(False)))

        threading.Thread(target=_worker, daemon=True).start()

    def on_restore_clicked(self):
        if self.is_running:
            return
        self.set_running_state(True)
        self.log("\n↩ Restoring Normal System Settings...")

        def _worker():
            restore_normal_mode_log(self.log)
            self.state["gaming_mode"] = False
            save_state(self.state)
            self.root.after(0, lambda: (self.refresh_health_score(), self.set_running_state(False)))

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
    print("=========================================================")
    print("       [+] WINDOWS PC PERFORMANCE OPTIMIZER [+]")
    print("       AUTOMATIC BACKGROUND RUN (--auto)")
    print("=========================================================\n")
    create_restore_point_log()
    kill_bloatware_log()
    clean_temp_files_log()
    optimize_power_and_visuals_log()
    optimize_startup_and_services_log()
    optimize_network_log()
    print("\n[DONE] Automatic background optimization complete.")

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    elevate_if_needed()

    # Parse CLI flags
    parser = argparse.ArgumentParser(description="PC Performance Optimizer")
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

    # Default launch: GUI App Window
    root = tk.Tk()
    app = PCOptimizerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
