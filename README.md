# ViZDoom Client Easy Installation Guide

## Introduction
This package allows you to easily install and run the ViZDoom client without setting up the entire ViZDoom environment.

## Installation

### Method 1: Shell Script (macOS/Linux)
```bash
# Give execution permission to the installation script
chmod +x install.sh

# Run the script
./install.sh
```

The script will:
- Set up a Python virtual environment (venv)
- Install all required dependencies
- Create a convenient run script for future use

### Method 2: Python Script (All Operating Systems)
```bash
# Run the Python script
python install.py
```

## Running the Client
After installation, you can run the client with:
```bash
# Activate the virtual environment
source venv/bin/activate

# Navigate to client directory and run
cd client_files
python client.py
```

Alternatively, you can use the provided run script:
```bash
./run_client.sh
```

You can also run the client directly at the end of the installation process.

## Client Features

### 1. Server Connection
- The client automatically loads the server list when started.
- Select a server and click "Connect to Selected Server" to join.

### 2. Player Settings
- **Player Name**: Enter your desired player name.
- **Player Color**: Choose your player color.
- **Enable ESP Overlay**: Toggle the ESP feature. 
  When enabled, "-ESP" will be added to your player name.

### 3. Game Controls
- **Movement**: W, A, S, D keys
- **Attack**: Left mouse button
- **Open doors/Interact**: E key
- **Change weapons**: Number keys or mouse wheel

### 4. ESP Feature
The ESP (Extra Sensory Perception) feature displays:
- Positions of other players
- Distance to players
- Direction indicators

## Troubleshooting

### Common Issues
- **Package installation errors**: Try installing the required packages manually:
  ```bash
  # Activate the virtual environment first
  source venv/bin/activate
  
  # Then install packages
  pip install numpy opencv-python matplotlib vizdoom pillow requests
  ```

- **Virtual environment issues**: If you encounter problems with the virtual environment:
  ```bash
  # Recreate the virtual environment
  rm -rf venv
  python3 -m venv venv
  source venv/bin/activate
  pip install numpy opencv-python matplotlib vizdoom pillow requests
  ```

- **Server connection failure**: Verify that the dashboard server URL is correct.

- **ESP window issues**: Try resizing the window or restarting the client.

### macOS Requirements
For macOS, you need these packages (the script installs them automatically):
```bash
brew install cmake boost sdl2 wget
```

## Advanced Settings
If additional settings are needed, please modify the following files:
- `client_files/cig.cfg`: Game-related settings
- `client_files/_vizdoom.ini`: ViZDoom engine settings

---
If you have any questions, please contact the developer. 