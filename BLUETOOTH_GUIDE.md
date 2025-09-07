# Bluetooth Controller Support

The T80 TQI Controller system now supports Bluetooth controllers in addition to the original T80 wheel and USB controllers.

## Supported Controllers

### Wireless Controllers (Bluetooth)
- **Xbox Wireless Controllers** (Xbox One, Xbox Series X/S)
- **PlayStation Controllers** (DualShock 4, DualSense)
- **Generic Bluetooth Gamepads**

### Wired Controllers (USB)
- **Thrustmaster T80 Racing Wheel** (Primary target)
- **Xbox Controllers** (via USB)
- **Generic USB Gamepads**

## Setup Instructions

### 1. Pairing a Bluetooth Controller

#### Xbox Controllers
1. Put the controller in pairing mode:
   - Hold the **Xbox button** + **Connect button** (small button on top) simultaneously
   - The Xbox button will flash rapidly when in pairing mode

2. Using the GUI:
   - Open the **Service Control** tab
   - Click **"Scan for Controllers"** in the Bluetooth section
   - Wait for the scan to complete (10 seconds)
   - Select your controller from the list
   - Click **"Connect Controller"**

3. Using command line:
   ```bash
   bluetoothctl
   scan on
   # Wait for your controller to appear
   pair XX:XX:XX:XX:XX:XX  # Replace with your controller's MAC
   connect XX:XX:XX:XX:XX:XX
   ```

#### PlayStation Controllers
1. Put the controller in pairing mode:
   - Hold **Share** + **PS button** simultaneously until the light bar flashes
   
2. Follow the same GUI or command line steps as Xbox controllers

### 2. Controller Detection

The system automatically detects and prioritizes controllers in this order:
1. **T80 Wheel** (if `controller_type: "t80"` in config)
2. **Xbox Controllers** (if `controller_type: "xbox"` in config) 
3. **Auto-detection** (if `controller_type: "auto"` - default)
   - Prioritizes T80 wheels
   - Falls back to Xbox controllers
   - Then generic gamepads

### 3. Configuration

Edit `t80_config.json` to set controller preferences:

```json
{
  "controller_type": "auto",          // "auto", "t80", "xbox", "gamepad"
  "xbox_use_triggers": true,          // Use triggers for throttle/brake
  "xbox_steering_axis": 0,            // Left stick X-axis for steering
  "xbox_throttle_axis": 5,            // Right trigger for throttle
  "xbox_brake_axis": 2                // Left trigger for brake
}
```

## Bluetooth Management

### GUI Features
- **Bluetooth Status**: Shows if Bluetooth adapter is active
- **Controller List**: Displays paired controllers and connection status
- **Scan Function**: Discovers new controllers (10-second scan)
- **Connect/Disconnect**: Manage controller connections
- **Real-time Status**: Updates connection status automatically

### Command Line Utilities

Use the included `bluetooth_utils.py` for status checking:
```bash
python bluetooth_utils.py
```

### Manual Bluetooth Management

```bash
# Check Bluetooth status
bluetoothctl show

# List paired devices
bluetoothctl devices

# Connect to a specific controller
bluetoothctl connect XX:XX:XX:XX:XX:XX

# Disconnect a controller
bluetoothctl disconnect XX:XX:XX:XX:XX:XX

# Remove a paired device
bluetoothctl remove XX:XX:XX:XX:XX:XX
```

## Controller Mapping

### Xbox Wireless Controller
- **Left Stick X**: Steering input
- **Right Trigger (RT)**: Throttle (if `xbox_use_triggers: true`)
- **Left Trigger (LT)**: Brake (if `xbox_use_triggers: true`)
- **Right Stick Y**: Throttle (if `xbox_use_triggers: false`)
- **A Button**: Forward/Throttle (button mode)
- **B Button**: Reverse/Brake (button mode)

### T80 Racing Wheel
- **Wheel Rotation**: Steering input
- **Right Pedal**: Throttle
- **Left Pedal**: Brake
- **Paddle Shifters**: Alternative throttle/brake buttons

## Troubleshooting

### Controller Not Detected
1. Check Bluetooth status: `bluetoothctl show`
2. Ensure controller is in pairing mode
3. Check if controller appears in device list: `bluetoothctl devices`
4. Try manual pairing: `bluetoothctl pair XX:XX:XX:XX:XX:XX`

### Connection Issues
1. Remove and re-pair the device:
   ```bash
   bluetoothctl remove XX:XX:XX:XX:XX:XX
   # Put controller in pairing mode again
   bluetoothctl scan on
   bluetoothctl pair XX:XX:XX:XX:XX:XX
   bluetoothctl connect XX:XX:XX:XX:XX:XX
   ```

2. Restart Bluetooth service:
   ```bash
   sudo systemctl restart bluetooth
   ```

### Input Not Working
1. Check if device appears in input list:
   ```bash
   ls /dev/input/event*
   cat /proc/bus/input/devices
   ```

2. Verify controller type detection:
   ```bash
   python bluetooth_utils.py
   ```

3. Test input events:
   ```bash
   sudo evtest /dev/input/eventX  # Replace X with your device number
   ```

### Permission Issues
Add your user to the input group:
```bash
sudo usermod -a -G input $USER
# Log out and back in
```

## Technical Details

### Bluetooth Controller Detection
The system uses multiple detection methods:
1. **bluetoothctl devices**: Lists paired Bluetooth controllers
2. **/dev/input/event*** scanning: Finds active input devices
3. **Name matching**: Correlates Bluetooth devices with input devices
4. **Capability checking**: Verifies device has controller capabilities

### Auto-detection Logic
```python
def find_input_device():
    # 1. Check /dev/input/by-id for USB devices (fastest)
    # 2. Scan Bluetooth paired devices
    # 3. Match Bluetooth devices to /dev/input/event* devices
    # 4. Return best match based on controller_type preference
```

### Performance Considerations
- USB controllers have lower latency than Bluetooth
- Bluetooth scan takes 10 seconds (only when requested)
- Controller detection is cached during active sessions
- Multiple controllers can be paired but only one is active at a time

## Integration with TQI System

The Bluetooth support is fully integrated with the existing TQI hardware:
- Same I2C DAC outputs (0x60, 0x61)
- Identical signal processing and acceleration curves
- Full compatibility with existing calibration and configuration
- Seamless switching between T80 wheel and Bluetooth controllers

## Future Enhancements

Potential improvements for future versions:
- Multiple simultaneous controller support
- Controller-specific profiles and mappings
- Haptic feedback support for compatible controllers
- Battery level monitoring for wireless controllers
- Custom button mapping interface
