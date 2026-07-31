# ⚡ PC Performance Optimizer for Windows

A safe, production-ready desktop performance tuning application for Windows 10 and 11. Designed with safe default rules, live PC Health Score monitoring, 1-click safe cleanup, Gaming Mode, automated weekly maintenance, and full restore capability.

---

## 🚀 How to Use

Double-click `optimizer.exe` → Accept UAC prompt → Desktop App window opens.  
Everything is controlled through the clean desktop interface buttons:

| Button | What it does |
|---|---|
| **🚀 Optimize My PC** | Full 1-click safe cleanup &amp; system tuning |
| **🎮 Gaming Mode** | Terminate bloatware, disable GameDVR recording |
| **↩ Restore Normal** | Undo all changes made by this app back to original values |
| **⏰ Schedule Weekly** | Auto-clean every Sunday at 3:00 AM using `optimizer-auto.exe` |

---

## ⚙️ Advanced / Background Use (CLI)

For automation, custom scripts, or scheduled tasks only:

```text
optimizer-auto.exe --auto      Full cleanup, no window
optimizer-auto.exe --gaming    Gaming mode, no window
optimizer-auto.exe --restore   Restore normal mode, no window
```

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

### Building Standalone Executables from Source
To compile `optimizer.exe` (GUI) and `optimizer-auto.exe` (CLI):

```cmd
python build.py
```

### Generating Release Checksums
To calculate SHA256 checksums and output `release_manifest.json`:

```cmd
python generate_manifest.py
```

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
