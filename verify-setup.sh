#!/bin/bash
# Final verification script for T80 headless setup

echo "=== T80 Headless Setup Verification ==="
echo ""

echo "1. Checking service installation..."
if systemctl is-enabled t80-headless.service >/dev/null 2>&1; then
    echo "✅ t80-headless.service is enabled for boot"
else
    echo "❌ Service not enabled"
    exit 1
fi

echo ""
echo "2. Checking for conflicting services..."
CONFLICTS=$(systemctl list-unit-files --state=enabled | grep -E "(t80|tqi|wheel|racing)" | grep -v "t80-headless.service" || true)
if [ -z "$CONFLICTS" ]; then
    echo "✅ No conflicting services found"
else
    echo "⚠️  Potential conflicts found:"
    echo "$CONFLICTS"
fi

echo ""
echo "3. Testing service startup..."
sudo systemctl restart t80-headless.service
sleep 3
if systemctl is-active t80-headless.service >/dev/null 2>&1; then
    echo "✅ Service starts successfully"
else
    echo "❌ Service failed to start"
    sudo systemctl status t80-headless.service
    exit 1
fi

echo ""
echo "4. Checking hardware connections..."
echo "I2C DACs:"
i2c_result=$(sudo i2cdetect -y 1 2>/dev/null | grep -E "60|61" || true)
if [[ $i2c_result == *"60"* && $i2c_result == *"61"* ]]; then
    echo "✅ Both DACs detected at 0x60 and 0x61"
else
    echo "⚠️  DACs not detected or wrong addresses"
    sudo i2cdetect -y 1
fi

echo ""
echo "T80 Wheel:"
if ls /dev/input/by-id/*Thrustmaster* >/dev/null 2>&1; then
    echo "✅ T80 wheel detected"
    ls /dev/input/by-id/*Thrustmaster*
else
    echo "⚠️  T80 wheel not detected"
fi

echo ""
echo "5. Checking service logs..."
LAST_LOG=$(sudo journalctl -u t80-headless.service --no-pager -n 1 --since="1 minute ago" 2>/dev/null | tail -1)
if [[ $LAST_LOG == *"Using input"* ]]; then
    echo "✅ Service is processing input"
    echo "   $LAST_LOG"
else
    echo "ℹ️  Recent service activity:"
    sudo journalctl -u t80-headless.service --no-pager -n 3
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Your T80 controller is now configured to start automatically on boot."
echo "Simply plug in power and your T80 wheel - no display or interaction needed!"
echo ""
echo "Management commands:"
echo "  ./t80-control.sh status  - Check service status"
echo "  ./t80-control.sh logs    - View live logs"
echo "  ./t80-control.sh test    - Test hardware"
echo ""
