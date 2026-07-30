# ⚡ PC Performance Optimizer for Windows

A safe, production-ready desktop performance tuning application for Windows 10 and 11. Designed with safe default rules, live PC Health Score monitoring, 1-click safe cleanup, Gaming Mode, automated weekly maintenance, and full restore capability.

---

## 🚀 Features Overview

1. **Live PC Health Score (0–100)**
   - Real-time scoring based on RAM pressure, C: drive free space, temporary junk files size, telemetry status, and startup apps count.

2. **1-Click Safe Cleanup Engine**
   - Cleans `%TEMP%`, `C:\Windows\Temp`, `C:\Windows\Prefetch`, and Chrome/Edge/Firefox browser caches.
   - Includes dry-run estimation scanner and accurate measurement of actual reclaimed disk space.
   - Avoids aggressive working-set RAM flushing to prevent pagefile disk thrashing and system hanging.

3. **Power & Visual Effects Tuning**
   - Configures the safe **Balanced** power plan to prevent CPU overheating and thermal throttling.
   - Optimizes Windows visual animations for responsiveness.

4. **Startup Program Manager (With Registry Backup)**
   - Audits startup items in `HKCU` and `HKLM` registry paths.
   - Backs up registry entries (`hive`, `key`, `name`, `type`, `value_data`, `timestamp`, `app_version`) to structured state before disabling non-essential startup apps.

5. **Telemetry Management**
   - Disables `DiagTrack` (Connected User Experiences & Telemetry).
   - Preserves Start menu and file search indexing (`WSearch`).

6. **Gaming Mode & Restoration**
   - **Gaming Mode**: Temporarily enables High Performance power plan and disables GameDVR background recording to prevent micro-stuttering.
   - **Restore Normal Mode**: Reverts all reversible modifications — restores Balanced power plan, GameDVR settings, telemetry startup mode, visual effects, and backed-up startup entries.

7. **Automated Weekly Scheduler**
   - One-click integration with native Windows Task Scheduler (`PCOptimizerWeekly`) running every Sunday at 3:00 AM.

8. **Safety Checkpoints**
   - Triggers a Windows **System Restore Point** (`Checkpoint-Computer`) before executing optimization steps.

---

## ⬇️ Installation & Running Options

### Option A: Verified PowerShell Installer

Run the verified setup script in Windows PowerShell (Admin):

```powershell
iwr -useb https://raw.githubusercontent.com/Naraito-ai/pc-optimizer/main/install.ps1 | iex
```

> **Security Note**: The installer prints the source URL, downloads `optimizer.py`, displays the computed SHA256 checksum for verification, verifies Python 3 dependencies, and launches the desktop app.

---

### Option B: Standalone `.exe` Executable (No Python Required)

1. Download `optimizer.exe` from the latest release or site root.
2. Double-click `optimizer.exe` and grant Administrator permission when prompted by UAC.

#### Windows SmartScreen Notice:
> ℹ️ **SmartScreen Warning**:  
> Windows SmartScreen may display a warning banner (*"Windows protected your PC"*) on first launch because `optimizer.exe` is an independent open-source executable and is not signed with an Extended Validation (EV) Code Signing Certificate.  
>  
> To run: Click **More info** → **Run anyway**. Source code and release SHA256 hashes are published on GitHub for complete transparency.

---

## 🧪 Testing & Developer Guide

### Running Unit Tests
The repository includes a comprehensive unit test suite using `unittest` and mocks to verify software logic without modifying your system:

```cmd
git clone https://github.com/Naraito-ai/pc-optimizer.git
cd pc-optimizer
pip install -r requirements-dev.txt
python -m unittest discover tests
```

### Building Standalone `.exe` from Source
To compile `optimizer.exe` using PyInstaller:

```cmd
python -m PyInstaller --clean --onefile --windowed --uac-admin --name optimizer optimizer.py
```

### Generating Release Checksums
To calculate SHA256 checksums and output `release_manifest.json`:

```cmd
python generate_manifest.py
```

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
