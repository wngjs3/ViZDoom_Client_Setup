#!/bin/bash

echo "===== ViZDoom Client Installation Script ====="
echo "This script will set up everything you need to run the ViZDoom client."

# Store current path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$SCRIPT_DIR/client_files"

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

# Set up Python virtual environment
echo "===== Setting up Python virtual environment ====="
python3 -m venv venv
# Using source to ensure the script works in different shells
source venv/bin/activate

# Install required Python packages
echo "===== Installing Python packages ====="
pip install --upgrade pip
pip install numpy opencv-python matplotlib vizdoom pillow requests

# Set execution permissions
echo "===== Setting up execution permissions ====="
chmod +x "$CLIENT_DIR/client.py"

# Create activation script for convenience
cat > run_client.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd "$(dirname "${BASH_SOURCE[0]}")/client_files" && python client.py
EOF
chmod +x run_client.sh

echo "===== Installation complete! ====="
echo "To run the client, use the following commands:"
echo "source venv/bin/activate"
echo "cd $CLIENT_DIR && python client.py"
echo ""
echo "Alternatively, you can use the provided run script:"
echo "./run_client.sh"

# Provide run option
read -p "Would you like to run the client now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  cd "$CLIENT_DIR" && python client.py
fi 