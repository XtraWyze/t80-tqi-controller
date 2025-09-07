#!/bin/bash
# Xbox Bluetooth Controller Setup Script
# Configures proper drivers and settings for Xbox controller Bluetooth support

set -e

echo "=== Xbox Bluetooth Controller Setup ==="
echo "This script will:"
echo "1. Install xboxdrv driver"
echo "2. Disable ERTM (Enhanced Retransmission Mode)"
echo "3. Configure Bluetooth for Xbox controllers"
echo "4. Set up proper permissions"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please run this script as a regular user (it will ask for sudo when needed)"
   exit 1
fi

# Update package list
echo "Updating package list..."
sudo apt update

# Install required packages
echo "Installing xboxdrv and dependencies..."
sudo apt install -y xboxdrv bluetooth bluez bluez-tools

# Check current ERTM status
echo ""
echo "=== Checking ERTM Status ==="
ERTM_STATUS=$(cat /sys/module/bluetooth/parameters/disable_ertm 2>/dev/null || echo "unknown")
echo "Current ERTM disable status: $ERTM_STATUS"

if [ "$ERTM_STATUS" = "N" ]; then
    echo "ERTM is currently enabled - this can cause Xbox controller connection issues"
    echo "Disabling ERTM..."
    
    # Disable ERTM temporarily
    echo "Y" | sudo tee /sys/module/bluetooth/parameters/disable_ertm > /dev/null
    echo "ERTM disabled for current session"
    
    # Make ERTM disable persistent across reboots
    echo "Making ERTM disable persistent..."
    
    # Method 1: Kernel module parameter
    if ! grep -q "bluetooth.disable_ertm=1" /boot/cmdline.txt; then
        sudo cp /boot/cmdline.txt /boot/cmdline.txt.backup
        sudo sed -i 's/$/ bluetooth.disable_ertm=1/' /boot/cmdline.txt
        echo "Added bluetooth.disable_ertm=1 to kernel command line"
    else
        echo "ERTM disable already in kernel command line"
    fi
    
    # Method 2: Modprobe configuration
    echo "options bluetooth disable_ertm=1" | sudo tee /etc/modprobe.d/bluetooth-xbox.conf > /dev/null
    echo "Created modprobe configuration for Bluetooth"
    
elif [ "$ERTM_STATUS" = "Y" ]; then
    echo "ERTM is already disabled ✓"
else
    echo "Could not determine ERTM status, setting up disable anyway..."
    echo "options bluetooth disable_ertm=1" | sudo tee /etc/modprobe.d/bluetooth-xbox.conf > /dev/null
fi

# Configure Bluetooth service
echo ""
echo "=== Configuring Bluetooth Service ==="

# Ensure Bluetooth service is enabled and running
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Add user to bluetooth group
sudo usermod -a -G bluetooth $USER
echo "Added $USER to bluetooth group"

# Create udev rules for Xbox controllers
echo ""
echo "=== Setting up Xbox Controller udev rules ==="

sudo tee /etc/udev/rules.d/99-xbox-controller.rules > /dev/null << 'EOF'
# Xbox Wireless Controller (Bluetooth)
SUBSYSTEM=="input", ATTRS{name}=="Xbox Wireless Controller", MODE="0666", GROUP="input"
SUBSYSTEM=="input", ATTRS{name}=="Microsoft Xbox Series S|X Controller", MODE="0666", GROUP="input"

# Xbox One Controller (USB)
SUBSYSTEM=="usb", ATTRS{idVendor}=="045e", ATTRS{idProduct}=="02ea", MODE="0666", GROUP="input"
SUBSYSTEM=="usb", ATTRS{idVendor}=="045e", ATTRS{idProduct}=="02fd", MODE="0666", GROUP="input"

# Xbox Series X|S Controller (USB)
SUBSYSTEM=="usb", ATTRS{idVendor}=="045e", ATTRS{idProduct}=="0b12", MODE="0666", GROUP="input"
SUBSYSTEM=="usb", ATTRS{idVendor}=="045e", ATTRS{idProduct}=="0b13", MODE="0666", GROUP="input"
EOF

echo "Created Xbox controller udev rules"

# Add user to input group
sudo usermod -a -G input $USER
echo "Added $USER to input group"

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Create Xbox controller helper script
echo ""
echo "=== Creating Xbox Controller Helper Scripts ==="

sudo tee /usr/local/bin/xbox-controller-setup > /dev/null << 'EOF'
#!/bin/bash
# Xbox Controller Bluetooth Helper Script

case "$1" in
    scan)
        echo "Scanning for Xbox controllers (10 seconds)..."
        bluetoothctl discoverable on
        bluetoothctl pairable on
        bluetoothctl scan on &
        SCAN_PID=$!
        sleep 10
        kill $SCAN_PID 2>/dev/null
        bluetoothctl scan off
        echo "Scan complete. Available devices:"
        bluetoothctl devices | grep -i xbox
        ;;
    connect)
        if [ -z "$2" ]; then
            echo "Usage: xbox-controller-setup connect <MAC_ADDRESS>"
            echo "Available Xbox controllers:"
            bluetoothctl devices | grep -i xbox
            exit 1
        fi
        echo "Connecting to Xbox controller $2..."
        bluetoothctl connect "$2"
        ;;
    disconnect)
        if [ -z "$2" ]; then
            echo "Usage: xbox-controller-setup disconnect <MAC_ADDRESS>"
            echo "Connected Xbox controllers:"
            bluetoothctl devices | grep -i xbox
            exit 1
        fi
        echo "Disconnecting Xbox controller $2..."
        bluetoothctl disconnect "$2"
        ;;
    status)
        echo "=== Bluetooth Status ==="
        bluetoothctl show | grep -E "(Powered|Discoverable|Pairable)"
        echo ""
        echo "=== Xbox Controllers ==="
        bluetoothctl devices | grep -i xbox | while read line; do
            mac=$(echo $line | awk '{print $2}')
            name=$(echo $line | cut -d' ' -f3-)
            connected=$(bluetoothctl info $mac | grep "Connected: yes" >/dev/null && echo "🟢 Connected" || echo "🔴 Disconnected")
            echo "$connected - $name ($mac)"
        done
        echo ""
        echo "=== Input Devices ==="
        ls /dev/input/event* | while read device; do
            name=$(cat /sys/class/input/$(basename $device)/device/name 2>/dev/null || echo "Unknown")
            if echo "$name" | grep -qi xbox; then
                echo "📱 $device - $name"
            fi
        done
        ;;
    *)
        echo "Xbox Controller Bluetooth Helper"
        echo "Usage: xbox-controller-setup <command> [args]"
        echo ""
        echo "Commands:"
        echo "  scan                    - Scan for Xbox controllers"
        echo "  connect <MAC>          - Connect to specific controller"
        echo "  disconnect <MAC>       - Disconnect specific controller"
        echo "  status                 - Show controller status"
        echo ""
        echo "Examples:"
        echo "  xbox-controller-setup scan"
        echo "  xbox-controller-setup connect 68:6C:E6:95:A6:C8"
        echo "  xbox-controller-setup status"
        ;;
esac
EOF

sudo chmod +x /usr/local/bin/xbox-controller-setup

# Create systemd service to ensure ERTM is disabled on boot
echo ""
echo "=== Creating ERTM disable service ==="

sudo tee /etc/systemd/system/disable-ertm.service > /dev/null << 'EOF'
[Unit]
Description=Disable Bluetooth ERTM for Xbox Controllers
After=bluetooth.service
Wants=bluetooth.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo Y > /sys/module/bluetooth/parameters/disable_ertm'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable disable-ertm.service
echo "Created systemd service to disable ERTM on boot"

# Test Bluetooth functionality
echo ""
echo "=== Testing Bluetooth Functionality ==="
if systemctl is-active --quiet bluetooth; then
    echo "✓ Bluetooth service is running"
else
    echo "✗ Bluetooth service is not running"
    sudo systemctl start bluetooth
fi

# Check ERTM status after changes
NEW_ERTM_STATUS=$(cat /sys/module/bluetooth/parameters/disable_ertm 2>/dev/null || echo "unknown")
echo "ERTM disable status after changes: $NEW_ERTM_STATUS"

# Final status report
echo ""
echo "=== Setup Complete ==="
echo "✓ xboxdrv installed"
echo "✓ ERTM disabled (effective after reboot)"
echo "✓ Bluetooth service configured"
echo "✓ User permissions set"
echo "✓ Helper scripts created"
echo ""
echo "IMPORTANT: You need to log out and back in (or reboot) for group changes to take effect"
echo ""
echo "To use Xbox controllers:"
echo "1. Put controller in pairing mode (Xbox + Connect buttons)"
echo "2. Run: xbox-controller-setup scan"
echo "3. Run: xbox-controller-setup connect <MAC_ADDRESS>"
echo "4. Test with your T80 TQI application"
echo ""
echo "For troubleshooting, run: xbox-controller-setup status"
echo ""
echo "Reboot recommended to ensure all changes take effect."
