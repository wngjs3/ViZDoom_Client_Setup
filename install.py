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
from pathlib import Path

# Directory information
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(SCRIPT_DIR, "ViZDoom", "client")
CLIENT_FILES_DIR = os.path.join(SCRIPT_DIR, "client_files")


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


def install_python_deps():
    """Install Python packages"""
    print_header("Installing Python Packages")

    # Upgrade pip
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True
    )

    # Install required packages
    packages = ["numpy", "opencv-python", "matplotlib", "vizdoom", "pillow", "requests"]
    for pkg in packages:
        print(f"Installing {pkg}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=True)
        except Exception as e:
            print(f"Error installing {pkg}: {e}")
            print(f"Continuing. Please install {pkg} manually later.")


def setup_client():
    """Set up client files"""
    print_header("Setting Up Client Files")

    # Create client directory
    os.makedirs(CLIENT_DIR, exist_ok=True)

    # Copy client files
    files = ["client.py", "utils.py", "cig.cfg", "cig.wad", "mock.wad", "_vizdoom.ini"]
    for file in files:
        src = os.path.join(CLIENT_FILES_DIR, file)
        dst = os.path.join(CLIENT_DIR, file)

        if os.path.exists(src):
            print(f"Copying {file}...")
            shutil.copy2(src, dst)
        else:
            print(f"Warning: File {file} not found")

    # Set execution permissions on Unix-based systems
    if platform.system() != "Windows":
        client_path = os.path.join(CLIENT_DIR, "client.py")
        os.chmod(client_path, 0o755)


def run_client():
    """Run the client"""
    print_header("Run ViZDoom Client")

    client_path = os.path.join(CLIENT_DIR, "client.py")
    if os.path.exists(client_path):
        print("Would you like to run the client now? (y/n)")
        if input().lower() == "y":
            try:
                os.chdir(CLIENT_DIR)
                subprocess.run([sys.executable, "client.py"], check=True)
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

    # Install Python packages
    install_python_deps()

    # Set up client
    setup_client()

    # Installation complete
    print_header("Installation Complete")
    print("ViZDoom client has been successfully installed!")
    print("To run the client, use the following command:")
    print(f"cd {CLIENT_DIR} && python client.py")

    # Run client
    run_client()


if __name__ == "__main__":
    main()
