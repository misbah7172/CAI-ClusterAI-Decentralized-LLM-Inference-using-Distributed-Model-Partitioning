"""
One-click build script for packaging the CAI Sandbox Desktop Application into a standalone .exe.
"""

import os
import shutil
import subprocess
import sys

def build():
    print("==================================================")
    print("Building CAI Sandbox Standalone Desktop Executable")
    print("==================================================")
    
    # Change to project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(project_root)
    
    # Clean previous build artifacts
    for directory in ["build", "dist"]:
        if os.path.exists(directory):
            print(f"Cleaning old '{directory}' directory...")
            try:
                shutil.rmtree(directory)
            except Exception as e:
                print(f"Warning: Could not remove {directory}: {e}")
                
    # Detect the correct pyinstaller executable path in venv
    venv_pyinstaller = os.path.join(project_root, ".venv", "Scripts", "pyinstaller.exe")
    if os.path.exists(venv_pyinstaller):
        pyinstaller_bin = venv_pyinstaller
    else:
        pyinstaller_bin = "pyinstaller"
        
    print(f"Using PyInstaller: {pyinstaller_bin}")

    # Build command with necessary data mappings for internal modules
    # In Windows, PyInstaller expects data format as source;destination
    cmd = [
        pyinstaller_bin,
        "--onefile",
        "--noconsole",
        "--name=CAI_Sandbox",
        "--add-data=desktop;desktop",
        "--add-data=sandbox;sandbox",
        "--add-data=model;model",
        "--add-data=proto;proto",
        "--add-data=monitoring;monitoring",
        "--clean",
        "main_gui.py"
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print("\n==================================================")
            print("SUCCESS: Standalone executable created at:")
            print(f"  {os.path.join(project_root, 'dist', 'CAI_Sandbox.exe')}")
            print("==================================================")
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: PyInstaller execution failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\nERROR: Build crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
