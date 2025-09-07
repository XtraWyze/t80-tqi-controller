#!/bin/bash
# Setup script for T80 GUI Controller on Raspberry Pi

echo "Setting up T80 GUI Controller..."

# Update system
echo "Updating system packages..."
sudo apt update

# Install required system packages
echo "Installing system dependencies..."
sudo apt install -y python3-pip python3-tk python3-dev i2c-tools

# Enable I2C interface
echo "Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Set up udev rules for input device access
echo "Setting up udev rules..."
sudo tee /etc/udev/rules.d/99-thrustmaster.rules > /dev/null << EOF
# Thrustmaster T80 Racing Wheel
SUBSYSTEM=="input", ATTRS{idVendor}=="044f", ATTRS{idProduct}=="b664", MODE="0666", GROUP="input"
# All input devices for testing
SUBSYSTEM=="input", GROUP="input", MODE="0664"
EOF

# Add user to input group
echo "Adding user to input group..."
sudo usermod -a -G input $USER

# Reload udev rules
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

# Create desktop launcher
echo "Creating desktop launcher..."
cat > ~/Desktop/T80_Controller.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=T80 Controller
Comment=Thrustmaster T80 to TQi Controller
Exec=python3 $(pwd)/t80_gui.py
Icon=input-gaming
Terminal=false
Categories=Game;Settings;
EOF

chmod +x ~/Desktop/T80_Controller.desktop

echo ""
echo "Setup complete!"
echo ""
echo "IMPORTANT: Please reboot your Raspberry Pi for all changes to take effect."
echo ""
echo "After reboot, you can:"
echo "1. Double-click the T80_Controller icon on your desktop"
echo "2. Or run: python3 t80_gui.py"
echo ""
echo "Make sure to:"
echo "1. Connect your I2C DACs to the correct addresses (0x60 for steering, 0x61 for throttle)"
echo "2. Connect your Thrustmaster T80 wheel via USB"
echo "3. Check I2C connections with: sudo i2cdetect -y 1"
echo ""
