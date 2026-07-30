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
    """Build the standalone .exe file using PyInstaller."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    optimizer_script = os.path.join(script_dir, "optimizer.py")
    version_file = os.path.join(script_dir, "version_info.txt")

    if not os.path.exists(optimizer_script):
        print(f"[X] Error: {optimizer_script} not found!")
        sys.exit(1)

    print("\n============================================================")
    print("      BUILDING PC OPTIMIZER STANDALONE EXECUTABLE")
    print("============================================================\n")

    cmd = [
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
        cmd.extend(["--version-file", version_file])

    cmd.append(optimizer_script)

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
