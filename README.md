# ⚡ PC Performance Optimizer for Windows

A production-ready, CLI-based system performance tuning tool for Windows. It reclaims RAM, clears system & browser temp caches, optimizes CPU power schemes, manages registry startup programs, disables non-essential services, and optimizes network TCP stacks—with before/after performance reporting and automatic System Restore safety checkpoints.

---

## 🚀 Features Overview

1. **Memory Cleanup**
   - Flushes Windows process working set & standby memory.
   - Automatically terminates idle bloatware (OneDrive, Teams, Discord, Cortana, Skype, Phone Link).
   - Identifies non-system processes using **> 200MB RAM** and prompts for interactive cleanup.

2. **Temp File & Cache Cleanup**
   - Cleans `%TEMP%`, `C:\Windows\Temp`, and `C:\Windows\Prefetch`.
   - Safely purges Chrome, Edge, and Firefox browser caches.
   - Clears Windows Update cache (`C:\Windows\SoftwareDistribution\Download`).
   - Reports exact space freed in MB / GB.

3. **CPU & Power Optimization**
   - Switches Windows power plan to **High Performance** (`powercfg`).
   - Disables CPU Power Throttling via Windows Registry (`PowerThrottlingOff`).
   - Optimizes Windows visual effects and animations for maximum performance.

4. **Startup Program Manager**
   - Audits startup entries across `HKCU` and `HKLM` registry paths.
   - Interactive prompt to safely disable non-essential startup applications.

5. **Services Optimizer**
   - Stops and disables non-critical background services:
     - `SysMain` (Superfetch)
     - `PrintSpooler` (Print Spooler)
     - `DiagTrack` (Windows Telemetry)
     - `WSearch` (Windows Search Indexing)

6. **Network & TCP Stack Tweaks**
   - Flushes DNS cache (`ipconfig /flushdns`).
   - Resets Winsock catalog & IP stack (`netsh winsock reset`, `netsh int ip reset`).
   - Optimizes TCP window auto-tuning level (`autotuninglevel=normal`).

7. **Safety & Baseline Reporting**
   - **System Restore Point**: Automatically creates a Windows System Restore Point (`Checkpoint-Computer`) before making changes.
   - **Admin Verification**: Requires and verifies Administrator privileges prior to execution.
   - **Before/After Report**: Generates a clean comparison table displaying RAM %, CPU %, and disk space freed.

---

## 🛠️ Option A: One-Line PowerShell Quick Install (Hosted Script)

No manual code download required! Run the automated installer directly in PowerShell.

### Instructions:

1. Press `Win + X` and select **Terminal (Admin)** or **Windows PowerShell (Admin)**.
2. Paste and run the following command:

```powershell
iwr -useb https://raw.githubusercontent.com/USERNAME/pc-optimizer/main/install.ps1 | iex
```

> **Note**: Replace `USERNAME` in the URL with your actual GitHub username once pushed.
> The installer automatically detects Python 3 (installs it via `winget` if missing), downloads `optimizer.py` and `requirements.txt`, installs dependencies, and launches the optimizer with elevated privileges.

---

## 📦 Option B: Standalone `.exe` Executable (No Python Required)

For end users who do not have Python installed.

### Instructions for Users:
1. Go to the [Releases](https://github.com/USERNAME/pc-optimizer/releases) page of the GitHub repository.
2. Download `optimizer.exe`.
3. Right-click `optimizer.exe` and select **Run as Administrator**.

### SmartScreen Bypass Note:
> ⚠️ **Windows SmartScreen Warning**  
> Because `optimizer.exe` is a custom standalone tool built with PyInstaller and is not signed with an expensive Extended Validation (EV) Code Signing Certificate, Windows SmartScreen may display a blue warning banner (*"Windows protected your PC"*).  
>   
> **This is completely normal for unsigned open-source binaries.**  
> To run the tool:  
> 1. Click **More info**.  
> 2. Click **Run anyway**.

---

## 🏗️ Developer Guide: Building `.exe` with `build.py`

To build your own standalone `.exe` binary from source:

1. Clone the repository and install requirements:
   ```cmd
   git clone https://github.com/USERNAME/pc-optimizer.git
   cd pc-optimizer
   pip install -r requirements.txt
   ```

2. Run the automated PyInstaller build script:
   ```cmd
   python build.py
   ```

3. The compiled binary will be placed at:
   ```text
   pc-optimizer\dist\optimizer.exe
   ```

---

## 🌐 GitHub Repository Setup & Release Guide

Follow these steps to host your repository and set up Option A and Option B:

### Step 1: Push Code to GitHub
```cmd
git init
git add .
git commit -m "Initial commit of Windows PC Performance Optimizer"
git branch -M main
git remote add origin https://github.com/USERNAME/pc-optimizer.git
git push -u origin main
```

### Step 2: Update `install.ps1` Raw URL
Edit `install.ps1` and replace `USERNAME` with your actual GitHub username:
```powershell
$RAW_BASE_URL = "https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/pc-optimizer/main"
```

### Step 3: Create GitHub Release (For Option B `.exe`)
1. Go to `https://github.com/USERNAME/pc-optimizer` in your browser.
2. On the right sidebar, click **Create a new release**.
3. Set tag version to `v1.0.0` and title to `v1.0.0 - Production Release`.
4. Drag and drop `dist/optimizer.exe` into the **Attach binaries** field.
5. Click **Publish release**.

---

## 🛡️ License & Safety Notice

This tool is provided for system maintenance purposes. All high-impact operations (service disabling, process termination, startup removal) require explicit user confirmation. A System Restore Point is triggered automatically before operations begin.
