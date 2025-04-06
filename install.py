#!/usr/bin/env python3
"""
ViZDoom Client Installation Script
This script installs and configures the ViZDoom client.
"""

import os
import sys
import shutil
import subprocess
import platform
import venv
from pathlib import Path

# Directory information
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(SCRIPT_DIR, "client_files")
VENV_DIR = os.path.join(SCRIPT_DIR, "venv")


def print_header(message):
    """Print header message"""
    print("\n" + "=" * 10 + " " + message + " " + "=" * 10)


def install_system_deps():
    """Install system dependencies"""
    if platform.system() == "Darwin":  # macOS
        print_header("macOS Detected")
        print("Installing required packages using Homebrew...")

        # Check if Homebrew is installed
        brew_cmd = subprocess.run(
            ["which", "brew"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if brew_cmd.returncode != 0:
            print("Homebrew not found. Would you like to install it? (y/n)")
            if input().lower() == "y":
                # Install Homebrew
                brew_install_cmd = "curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh"
                subprocess.run(["/bin/bash", "-c", brew_install_cmd], check=True)
            else:
                print(
                    "Skipping Homebrew installation. Some features may not work properly."
                )
                return

        # Install required packages
        print("Installing essential packages...")
        subprocess.run(
            ["brew", "install", "cmake", "boost", "sdl2", "wget"], check=True
        )


def setup_virtual_env():
    """Setup Python virtual environment"""
    print_header("Setting Up Python Virtual Environment")

    # Check if virtual environment already exists
    if os.path.exists(VENV_DIR):
        print(f"Virtual environment already exists at {VENV_DIR}")
        print("Would you like to recreate it? (y/n)")
        if input().lower() == "y":
            print("Removing existing virtual environment...")
            shutil.rmtree(VENV_DIR)
        else:
            print("Using existing virtual environment.")
            return

    # Create virtual environment
    print(f"Creating virtual environment at {VENV_DIR}...")
    venv.create(VENV_DIR, with_pip=True)

    # Get the path to the Python executable in the virtual environment
    if platform.system() == "Windows":
        venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
        venv_pip = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:  # Unix-based systems (Linux and macOS)
        venv_python = os.path.join(VENV_DIR, "bin", "python")
        venv_pip = os.path.join(VENV_DIR, "bin", "pip")

    # Upgrade pip within the virtual environment
    print("Upgrading pip in virtual environment...")
    subprocess.run(
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True
    )

    return venv_python, venv_pip


def install_python_deps(venv_pip=None):
    """Install Python packages"""
    print_header("Installing Python Packages")

    # Use virtualenv pip if available, otherwise use system pip
    pip_cmd = venv_pip if venv_pip else [sys.executable, "-m", "pip"]

    # Install required packages
    packages = [
        "numpy",
        "opencv-python",
        "matplotlib",
        "vizdoom",
        "pillow",
        "requests",
        "webdataset",
    ]
    for pkg in packages:
        print(f"Installing {pkg}...")
        try:
            if isinstance(pip_cmd, list):
                subprocess.run(pip_cmd + ["install", pkg], check=True)
            else:
                subprocess.run([pip_cmd, "install", pkg], check=True)
        except Exception as e:
            print(f"Error installing {pkg}: {e}")
            print(f"Continuing. Please install {pkg} manually later.")


def set_permissions():
    """Set execution permissions for client files"""
    print_header("Setting Up Execution Permissions")

    # Set execution permissions on Unix-based systems
    if platform.system() != "Windows":
        client_path = os.path.join(CLIENT_DIR, "client.py")
        if os.path.exists(client_path):
            print(f"Setting execution permissions for {client_path}...")
            os.chmod(client_path, 0o755)
        else:
            print(f"Warning: File {client_path} not found")


def create_run_script():
    """Create a run script for convenience"""
    print_header("Creating Run Script")

    run_script_path = os.path.join(SCRIPT_DIR, "run_client.sh")

    if platform.system() == "Windows":
        # Windows batch file
        with open(os.path.join(SCRIPT_DIR, "run_client.bat"), "w") as f:
            f.write("@echo off\n")
            f.write(
                f"{os.path.join('venv', 'Scripts', 'python.exe')} {os.path.join('client_files', 'client.py')}\n"
            )
        print(f"Created run script at {os.path.join(SCRIPT_DIR, 'run_client.bat')}")
    else:
        # Unix shell script
        with open(run_script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"source {os.path.join('venv', 'bin', 'activate')}\n")
            f.write(
                f"cd {os.path.join(SCRIPT_DIR, 'client_files')} && python client.py\n"
            )
        # Make script executable
        os.chmod(run_script_path, 0o755)
        print(f"Created run script at {run_script_path}")


def run_client(venv_python=None):
    """Run the client"""
    print_header("Run ViZDoom Client")

    python_cmd = venv_python if venv_python else sys.executable
    client_path = os.path.join(CLIENT_DIR, "client.py")

    if os.path.exists(client_path):
        print("Would you like to run the client now? (y/n)")
        if input().lower() == "y":
            try:
                os.chdir(CLIENT_DIR)
                if isinstance(python_cmd, list):
                    subprocess.run(python_cmd + ["client.py"], check=True)
                else:
                    subprocess.run([python_cmd, "client.py"], check=True)
            except Exception as e:
                print(f"Error running client: {e}")
    else:
        print(f"Error: File {client_path} not found")


def main():
    """Main installation process"""
    print("===== ViZDoom Client Installation Script =====")
    print("This script will set up everything you need to run the ViZDoom client.")
    print(f"Operating System: {platform.system()} {platform.release()}")
    print(f"Python Version: {platform.python_version()}")

    # Install system packages
    install_system_deps()

    # Setup virtual environment
    venv_python, venv_pip = setup_virtual_env()

    # Install Python packages in the virtual environment
    install_python_deps(venv_pip)

    # Set execution permissions
    set_permissions()

    # Create run script
    create_run_script()

    # Installation complete
    print_header("Installation Complete")
    print("ViZDoom client has been successfully installed!")
    print("To run the client, use the following commands:")

    if platform.system() == "Windows":
        print(f"venv\\Scripts\\activate")
    else:
        print(f"source venv/bin/activate")

    print(f"cd {CLIENT_DIR} && python client.py")
    print()
    print("Alternatively, you can use the provided run script:")

    if platform.system() == "Windows":
        print("run_client.bat")
    else:
        print("./run_client.sh")

    # Run client
    run_client(venv_python)


if __name__ == "__main__":
    main()
