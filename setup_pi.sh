#!/bin/bash
# Setup script for T80 GUI Controller on Raspberry Pi

set -e  # Exit on any error

echo "========================================"
echo "T80 Racing Wheel Controller Setup"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "[ERROR] Please do not run this script as root."
    echo "[INFO] Run it as a regular user, sudo will be used when needed."
    exit 1
fi

echo "Setting up T80 GUI Controller..."

# Update system
echo "Updating system packages..."
sudo apt update
echo "[SUCCESS] System packages updated"

# Install required system packages
echo "Installing system dependencies..."
sudo apt install -y python3-pip python3-tk python3-dev i2c-tools python3-venv python3-full
echo "[SUCCESS] System dependencies installed"

# Enable I2C interface
echo "Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0
echo "[SUCCESS] I2C interface enabled"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "[SUCCESS] Virtual environment created"
else
    echo "[INFO] Virtual environment already exists"
fi

# Install Python dependencies in virtual environment
echo "Installing Python dependencies..."
.venv/bin/pip install -r requirements.txt
echo "[SUCCESS] Python dependencies installed"

# Set up udev rules for input device access
echo "Setting up udev rules..."
sudo tee /etc/udev/rules.d/99-thrustmaster.rules > /dev/null << EOF
# Thrustmaster T80 Racing Wheel
SUBSYSTEM=="input", ATTRS{idVendor}=="044f", ATTRS{idProduct}=="b664", MODE="0666", GROUP="input"
# All input devices for testing
SUBSYSTEM=="input", GROUP="input", MODE="0664"
EOF
echo "[SUCCESS] Udev rules configured"

# Add user to input and i2c groups
echo "Adding user to input and i2c groups..."
sudo usermod -a -G input $USER
sudo usermod -a -G i2c $USER
echo "[SUCCESS] User added to input and i2c groups"

# Reload udev rules
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "[SUCCESS] Udev rules reloaded"

# Create desktop launcher
echo "Creating desktop launcher..."
CURRENT_DIR=$(pwd)
DESKTOP_FILE="$HOME/Desktop/T80_Controller.desktop"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=T80 Controller
Comment=Thrustmaster T80 to TQi Controller
Exec=$CURRENT_DIR/.venv/bin/python $CURRENT_DIR/t80_gui.py
Icon=input-gaming
Terminal=false
Categories=Game;Settings;
EOF

chmod +x "$DESKTOP_FILE"
echo "[SUCCESS] Desktop launcher created"

# Install systemd service for auto-start
echo "Installing auto-start service..."
sudo cp t80-headless.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable t80-headless.service
echo "[SUCCESS] Auto-start service installed and enabled"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "IMPORTANT: Please reboot your Raspberry Pi for all changes to take effect."
echo ""
echo "After reboot, the T80 controller will auto-start in headless mode."
echo "You can also:"
echo "1. Double-click the T80_Controller icon on your desktop to run the GUI"
echo "2. Or run: .venv/bin/python t80_gui.py"
echo "3. Check auto-start service: sudo systemctl status t80-headless.service"
echo ""
echo "Make sure to:"
echo "1. Connect your I2C DACs to the correct addresses (0x60 for steering, 0x61 for throttle)"
echo "2. Connect your Thrustmaster T80 wheel via USB"
echo "3. Check I2C connections with: sudo i2cdetect -y 1"
echo ""
echo "[SUCCESS] Setup completed successfully! 🏎️"
