#!/bin/bash
# Xbox Bluetooth Troubleshooting Script
# Diagnoses and fixes common Xbox controller Bluetooth issues

echo "=== Xbox Controller Bluetooth Troubleshooting ==="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK") echo "✓ $message" ;;
        "WARN") echo "⚠ $message" ;;
        "ERROR") echo "✗ $message" ;;
        "INFO") echo "ℹ $message" ;;
    esac
}

echo "=== System Check ==="

# Check if running on Raspberry Pi
if grep -q "Raspberry Pi" /proc/cpuinfo; then
    print_status "OK" "Running on Raspberry Pi"
else
    print_status "WARN" "Not running on Raspberry Pi - some fixes may not apply"
fi

# Check BlueZ installation
if command_exists bluetoothctl; then
    BLUEZ_VERSION=$(bluetoothctl --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+' | head -1)
    print_status "OK" "BlueZ installed (version $BLUEZ_VERSION)"
else
    print_status "ERROR" "BlueZ not installed - run: sudo apt install bluez"
fi

# Check xboxdrv installation
if command_exists xboxdrv; then
    print_status "OK" "xboxdrv installed"
else
    print_status "WARN" "xboxdrv not installed - run: sudo apt install xboxdrv"
fi

# Check Bluetooth service
if systemctl is-active --quiet bluetooth; then
    print_status "OK" "Bluetooth service is running"
else
    print_status "ERROR" "Bluetooth service not running"
    echo "   Fix: sudo systemctl start bluetooth"
fi

# Check ERTM status
ERTM_STATUS=$(cat /sys/module/bluetooth/parameters/disable_ertm 2>/dev/null || echo "unknown")
if [ "$ERTM_STATUS" = "Y" ]; then
    print_status "OK" "ERTM is disabled"
elif [ "$ERTM_STATUS" = "N" ]; then
    print_status "ERROR" "ERTM is enabled - this causes Xbox controller issues"
    echo "   Fix: echo Y | sudo tee /sys/module/bluetooth/parameters/disable_ertm"
else
    print_status "WARN" "Cannot determine ERTM status"
fi

# Check user groups
if groups | grep -q bluetooth; then
    print_status "OK" "User is in bluetooth group"
else
    print_status "WARN" "User not in bluetooth group"
    echo "   Fix: sudo usermod -a -G bluetooth $USER (then logout/login)"
fi

if groups | grep -q input; then
    print_status "OK" "User is in input group"
else
    print_status "WARN" "User not in input group"
    echo "   Fix: sudo usermod -a -G input $USER (then logout/login)"
fi

echo ""
echo "=== Bluetooth Hardware Check ==="

# Check Bluetooth adapter
ADAPTER_INFO=$(bluetoothctl show 2>/dev/null | grep -E "(Powered|Discoverable|Pairable)")
if [ -n "$ADAPTER_INFO" ]; then
    print_status "OK" "Bluetooth adapter detected"
    echo "$ADAPTER_INFO" | while read line; do
        echo "   $line"
    done
else
    print_status "ERROR" "No Bluetooth adapter found"
fi

echo ""
echo "=== Xbox Controller Check ==="

# Check for paired Xbox controllers
XBOX_DEVICES=$(bluetoothctl devices 2>/dev/null | grep -i xbox)
if [ -n "$XBOX_DEVICES" ]; then
    print_status "OK" "Xbox controllers found:"
    echo "$XBOX_DEVICES" | while read line; do
        MAC=$(echo $line | awk '{print $2}')
        NAME=$(echo $line | cut -d' ' -f3-)
        CONNECTED=$(bluetoothctl info $MAC 2>/dev/null | grep "Connected: yes" >/dev/null && echo "Connected" || echo "Disconnected")
        echo "   $CONNECTED - $NAME ($MAC)"
    done
else
    print_status "WARN" "No Xbox controllers paired"
    echo "   To pair: Put controller in pairing mode and run 'xbox-controller-setup scan'"
fi

# Check input devices
echo ""
echo "=== Input Device Check ==="
XBOX_INPUT_DEVICES=$(ls /dev/input/event* 2>/dev/null | while read device; do
    name=$(cat /sys/class/input/$(basename $device)/device/name 2>/dev/null || echo "Unknown")
    if echo "$name" | grep -qi xbox; then
        echo "$device - $name"
    fi
done)

if [ -n "$XBOX_INPUT_DEVICES" ]; then
    print_status "OK" "Xbox input devices found:"
    echo "$XBOX_INPUT_DEVICES" | while read line; do
        echo "   $line"
    done
else
    print_status "WARN" "No Xbox input devices found"
fi

echo ""
echo "=== Common Issues and Fixes ==="

# Check for common issues
echo ""
echo "🔧 Quick Fixes:"
echo ""

# ERTM fix
if [ "$ERTM_STATUS" = "N" ]; then
    echo "1. Disable ERTM (most common fix):"
    echo "   echo Y | sudo tee /sys/module/bluetooth/parameters/disable_ertm"
    echo "   # Make permanent: echo 'options bluetooth disable_ertm=1' | sudo tee /etc/modprobe.d/bluetooth-xbox.conf"
    echo ""
fi

# Connection issues
echo "2. If controller won't connect:"
echo "   # Remove and re-pair"
echo "   bluetoothctl remove <MAC_ADDRESS>"
echo "   # Put controller in pairing mode (Xbox + Connect buttons)"
echo "   xbox-controller-setup scan"
echo "   xbox-controller-setup connect <MAC_ADDRESS>"
echo ""

# Permission issues
echo "3. If permission denied errors:"
echo "   sudo chmod 666 /dev/input/event*"
echo "   # Or reboot after adding to groups"
echo ""

# Service restart
echo "4. Reset Bluetooth completely:"
echo "   sudo systemctl restart bluetooth"
echo "   sudo rmmod btusb bluetooth"
echo "   sudo modprobe bluetooth"
echo "   sudo modprobe btusb"
echo ""

# Input lag
echo "5. Reduce input lag:"
echo "   # Enable raw output mode in T80 TQI config"
echo "   # Set xbox_raw_output: true"
echo ""

echo "=== Advanced Diagnostics ==="
echo ""
echo "📊 Useful diagnostic commands:"
echo "   bluetoothctl devices                 # List all paired devices"
echo "   bluetoothctl info <MAC>             # Detailed device info"
echo "   sudo evtest /dev/input/eventX      # Test input events"
echo "   lsusb | grep Xbox                   # Check USB Xbox controllers"
echo "   dmesg | grep -i bluetooth           # Bluetooth kernel messages"
echo "   systemctl status bluetooth          # Bluetooth service status"
echo ""

echo "=== Log Analysis ==="
echo ""
echo "Recent Bluetooth logs:"
journalctl -u bluetooth --no-pager --lines=5 2>/dev/null | tail -5

echo ""
echo "Recent kernel messages about Xbox:"
dmesg | grep -i xbox | tail -3

echo ""
echo "=== Summary ==="
echo "Run this script again after applying fixes to verify resolution."
echo "For persistent issues, try: sudo reboot"
