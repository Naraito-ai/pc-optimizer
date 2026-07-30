import os
import sys
import shutil
import subprocess

def check_pyinstaller():
    """Ensure PyInstaller is installed in the current Python environment."""
    try:
        import PyInstaller
        print("[+] PyInstaller module found.")
    except ImportError:
        print("[*] PyInstaller not detected. Installing pyinstaller via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("[+] PyInstaller installed successfully.")

def build_executable():
    """Build the standalone .exe file using PyInstaller."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    optimizer_script = os.path.join(script_dir, "optimizer.py")

    if not os.path.exists(optimizer_script):
        print(f"[X] Error: {optimizer_script} not found!")
        sys.exit(1)

    print("\n============================================================")
    print("      BUILDING PC OPTIMIZER STANDALONE EXECUTABLE")
    print("============================================================\n")

    # PyInstaller flags as specified:
    # --onefile : Pack into a single executable
    # --noconsole : Suppress default background console window
    # --uac-admin : Forces Windows UAC prompt for Administrator elevation on launch
    # --name : Output filename (optimizer.exe)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--uac-admin",
        "--name",
        "optimizer",
        optimizer_script
    ]

    print(f"Executing build command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True, cwd=script_dir)
    except subprocess.CalledProcessError as e:
        print(f"\n[X] Build failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    output_exe = os.path.join(script_dir, "dist", "optimizer.exe")
    if os.path.exists(output_exe):
        abs_path = os.path.abspath(output_exe)
        file_size_mb = os.path.getsize(output_exe) / (1024 * 1024)
        print("\n============================================================")
        print(" [+] BUILD SUCCESSFUL!")
        print("============================================================")
        print(f"Output Executable: {abs_path}")
        print(f"File Size        : {file_size_mb:.2f} MB")
        print("\nReady for deployment and distribution via GitHub Releases!")
    else:
        print("\n[X] Error: Build completed but output file not found in dist folder.")

if __name__ == "__main__":
    check_pyinstaller()
    build_executable()
