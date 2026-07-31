import os
import sys
import subprocess

def check_pyinstaller():
    """Check if PyInstaller is installed in the current environment."""
    try:
        import PyInstaller
        print("[+] PyInstaller module detected.")
    except ImportError:
        print("[X] PyInstaller missing.")
        print("Please install development dependencies using:")
        print("  pip install -r requirements-dev.txt")
        print("or:")
        print("  pip install pyinstaller")
        sys.exit(1)

def build_executable():
    """Build both GUI (optimizer.exe) and CLI (optimizer-auto.exe) executables using PyInstaller."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    optimizer_script = os.path.join(script_dir, "optimizer.py")
    version_file = os.path.join(script_dir, "version_info.txt")

    if not os.path.exists(optimizer_script):
        print(f"[X] Error: {optimizer_script} not found!")
        sys.exit(1)

    print("\n============================================================")
    print("      BUILDING PC OPTIMIZER STANDALONE EXECUTABLES")
    print("============================================================\n")

    # 1. GUI Executable (optimizer.exe)
    print("[1/2] Building Desktop GUI Executable (optimizer.exe)...")
    cmd_gui = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--name",
        "optimizer"
    ]
    if os.path.exists(version_file):
        cmd_gui.extend(["--version-file", version_file])
    cmd_gui.append(optimizer_script)

    print(f"Executing GUI build command: {' '.join(cmd_gui)}\n")
    try:
        subprocess.run(cmd_gui, check=True, cwd=script_dir)
    except subprocess.CalledProcessError as e:
        print(f"\n[X] GUI Build failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    # 2. CLI Auto Executable (optimizer-auto.exe)
    print("\n[2/2] Building Headless/Scheduled Task CLI Executable (optimizer-auto.exe)...")
    cmd_cli = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        "--console",
        "--uac-admin",
        "--name",
        "optimizer-auto"
    ]
    if os.path.exists(version_file):
        cmd_cli.extend(["--version-file", version_file])
    cmd_cli.append(optimizer_script)

    print(f"Executing CLI build command: {' '.join(cmd_cli)}\n")
    try:
        subprocess.run(cmd_cli, check=True, cwd=script_dir)
    except subprocess.CalledProcessError as e:
        print(f"\n[X] CLI Build failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    gui_exe = os.path.join(script_dir, "dist", "optimizer.exe")
    cli_exe = os.path.join(script_dir, "dist", "optimizer-auto.exe")

    if os.path.exists(gui_exe) and os.path.exists(cli_exe):
        gui_mb = os.path.getsize(gui_exe) / (1024 * 1024)
        cli_mb = os.path.getsize(cli_exe) / (1024 * 1024)
        print("\n============================================================")
        print(" [+] DUAL BUILDS SUCCESSFUL!")
        print("============================================================")
        print(f"GUI  Executable: {os.path.abspath(gui_exe)} ({gui_mb:.2f} MB)")
        print(f"CLI  Executable: {os.path.abspath(cli_exe)} ({cli_mb:.2f} MB)")
        print("\nReady for deployment and distribution via GitHub Releases!")
    else:
        print("\n[X] Error: Build completed but one or both output binaries missing in dist folder.")
        sys.exit(1)

if __name__ == "__main__":
    check_pyinstaller()
    build_executable()
