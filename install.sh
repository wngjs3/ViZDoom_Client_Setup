#!/bin/bash

echo "===== ViZDoom Client Installation Script ====="
echo "This script will set up everything you need to run the ViZDoom client."

# Create required directories
mkdir -p ViZDoom/client

# Store current path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$SCRIPT_DIR/ViZDoom/client"

# Check if macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "===== macOS detected ====="
  echo "Installing required packages using Homebrew..."
  
  # Check if Homebrew is installed
  if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
  
  # Install required packages
  brew install cmake boost sdl2 wget
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
  echo "Python3 not found. Please install Python3 to continue."
  exit 1
fi

# Install required Python packages
echo "===== Installing Python packages ====="
pip3 install --upgrade pip
pip3 install numpy opencv-python matplotlib vizdoom pillow requests

# Copy client files
echo "===== Setting up client files ====="

# Copy required files
cp -r "$SCRIPT_DIR/client_files/client.py" "$CLIENT_DIR/"
cp -r "$SCRIPT_DIR/client_files/utils.py" "$CLIENT_DIR/"
cp -r "$SCRIPT_DIR/client_files/cig.cfg" "$CLIENT_DIR/"
cp -r "$SCRIPT_DIR/client_files/cig.wad" "$CLIENT_DIR/"
cp -r "$SCRIPT_DIR/client_files/mock.wad" "$CLIENT_DIR/"
cp -r "$SCRIPT_DIR/client_files/_vizdoom.ini" "$CLIENT_DIR/"

# Set execution permissions
chmod +x "$CLIENT_DIR/client.py"

echo "===== Installation complete! ====="
echo "To run the client, use the following command:"
echo "cd $CLIENT_DIR && python3 client.py"

# Provide run option
read -p "Would you like to run the client now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  cd "$CLIENT_DIR" && python3 client.py
fi 