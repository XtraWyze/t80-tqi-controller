#!/usr/bin/env python3
import time, math, os, sys, json, subprocess
from evdev import InputDevice, ecodes
from smbus2 import SMBus, i2c_msg

# Load configuration from JSON file
def load_config():
    """Load configuration from t80_config.json"""
    default_config = {
        "i2c_bus": 1,
        "steering_addr": 0x60,
        "throttle_addr": 0x61,
        "update_hz": 200,
        "deadzone": 0.02,
        "expo": 0.25,
        "clamp": 0.98,
        "invert_throttle": True,
        "invert_steering": False,
        "grab_device": True,
        "use_separate_pedals": True,
        "pedal_mode": "buttons",
        "analog_pedal_feel": True,
        "throttle_ramp_duration": 1.0,
        "acceleration_curve": "exponential",
        "curve_strength": 2.0,
        "controller_type": "auto",
        "xbox_use_triggers": True,
        "xbox_raw_output": False
    }
    
    try:
        with open("t80_config.json", 'r') as f:
            loaded_config = json.load(f)
            default_config.update(loaded_config)
    except FileNotFoundError:
        print("Config file not found, using defaults")
    except Exception as e:
        print(f"Error loading config: {e}, using defaults")
    
    return default_config

# Load configuration
config = load_config()

# ---- Config from file ----
I2C_BUS = config["i2c_bus"]
STEERING_ADDR = config["steering_addr"]
THROTTLE_ADDR = config["throttle_addr"]
UPDATE_HZ = config["update_hz"]
DEADZONE = config["deadzone"]
EXPO = config["expo"]
CLAMP = config["clamp"]
INVERT_THROTTLE = config["invert_throttle"]
INVERT_STEERING = config["invert_steering"]
GRAB_DEVICE = config["grab_device"]
USE_SEPARATE_PEDALS = config["use_separate_pedals"]
PEDAL_MODE = config["pedal_mode"]
ANALOG_PEDAL_FEEL = config["analog_pedal_feel"]
THROTTLE_RAMP_DURATION = config["throttle_ramp_duration"]
ACCELERATION_CURVE = config["acceleration_curve"]
CURVE_STRENGTH = config["curve_strength"]
CONTROLLER_TYPE = config["controller_type"]
XBOX_USE_TRIGGERS = config["xbox_use_triggers"]
XBOX_RAW_OUTPUT = config.get("xbox_raw_output", False)

# Button codes for pedals (adjust these based on your T80 wheel)
FORWARD_PEDAL_CODES = {ecodes.BTN_TR, ecodes.BTN_TRIGGER}
REVERSE_PEDAL_CODES = {ecodes.BTN_TL, ecodes.BTN_THUMB}

# Map your input device automatically with controller type detection:
DEFAULT_INPUT = "/dev/input/event0"
CONTROLLER_TYPE = "auto"  # "auto", "t80", "xbox", "gamepad"

def find_bluetooth_controllers():
    """Find Bluetooth controllers using bluetoothctl"""
    bluetooth_devices = []
    try:
        result = subprocess.run(['bluetoothctl', 'devices'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if 'Device' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        mac = parts[1]
                        name = ' '.join(parts[2:])
                        if any(term in name.lower() for term in ['controller', 'xbox', 'gamepad', 'joystick']):
                            bluetooth_devices.append((mac, name))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return bluetooth_devices

def find_input_device():
    """Find compatible input device (T80, Xbox controller, or generic gamepad)
    Enhanced with Bluetooth support"""
    byid = "/dev/input/by-id"
    devices = []
    bluetooth_controllers = find_bluetooth_controllers()
    
    # First, check /dev/input/by-id for USB devices
    if os.path.isdir(byid):
        for name in os.listdir(byid):
            if "event" in name:
                device_path = os.path.join(byid, name)
                # Prioritize based on controller type preference
                if CONTROLLER_TYPE == "t80" and "Thrustmaster" in name:
                    return device_path, "t80"
                elif CONTROLLER_TYPE == "xbox" and ("Microsoft" in name or "Xbox" in name):
                    return device_path, "xbox"
                elif "Thrustmaster" in name:
                    devices.append((device_path, "t80"))
                elif "Microsoft" in name or "Xbox" in name:
                    devices.append((device_path, "xbox"))
                elif any(term in name.lower() for term in ["controller", "gamepad", "joystick"]):
                    devices.append((device_path, "gamepad"))
    
    # Check for Bluetooth controllers by scanning /dev/input/event* devices
    for i in range(10):  # Check event0 through event9
        device_path = f"/dev/input/event{i}"
        if os.path.exists(device_path):
            try:
                test_device = InputDevice(device_path)
                name = test_device.name.lower()
                test_device.close()
                
                # Check if this is a Bluetooth controller
                is_bluetooth = False
                for mac, bt_name in bluetooth_controllers:
                    if bt_name.lower() in name or name in bt_name.lower():
                        is_bluetooth = True
                        break
                
                if is_bluetooth or "xbox" in name or "controller" in name:
                    controller_type = "xbox" if "xbox" in name else "gamepad"
                    if CONTROLLER_TYPE == "auto" or CONTROLLER_TYPE == controller_type:
                        print(f"Found Bluetooth controller: {test_device.name} at {device_path}")
                        devices.append((device_path, controller_type))
                elif "thrustmaster" in name:
                    if CONTROLLER_TYPE == "auto" or CONTROLLER_TYPE == "t80":
                        devices.append((device_path, "t80"))
            except (OSError, PermissionError):
                continue
    
    # Return the first compatible device if auto-detection
    if devices and CONTROLLER_TYPE == "auto":
        return devices[0]
    
    # Return specific type if found
    for device_path, controller_type in devices:
        if CONTROLLER_TYPE == controller_type:
            return device_path, controller_type
    
    # Fallback to first device or default
    if devices:
        return devices[0]
    return DEFAULT_INPUT, "unknown"

def detect_controller_type(device_path):
    """Detect controller type from device name"""
    try:
        test_device = InputDevice(device_path)
        name = test_device.name.lower()
        test_device.close()
        
        if "thrustmaster" in name:
            return "t80"
        elif "microsoft" in name or "xbox" in name:
            return "xbox"
        elif any(term in name for term in ["controller", "gamepad"]):
            return "gamepad"
        else:
            return "unknown"
    except:
        return "unknown"

# Axis codes (tweak with evtest if needed)
STEERING_CODES = {ecodes.ABS_X, ecodes.ABS_RX}
THROTTLE_CODES = {ecodes.ABS_Y, ecodes.ABS_RY,
                  ecodes.ABS_Z, ecodes.ABS_RZ,
                  ecodes.ABS_THROTTLE, ecodes.ABS_BRAKE}

# ---- Helpers ----
def normalize(v, vmin, vmax):
    span = (vmax - vmin) or 1
    x = (2.0 * (v - vmin) / span) - 1.0
    return max(-1.0, min(1.0, x))

def apply_deadzone(x, dz):
    if abs(x) <= dz: return 0.0
    s = (abs(x) - dz) / (1.0 - dz)
    return math.copysign(s, x)

def expo(x, k):
    return x if k <= 0 else (1 - k)*x + k*(x**3)

def to_dac12(x):
    x = max(-CLAMP, min(CLAMP, x)) / CLAMP
    return max(0, min(4095, int(round((x + 1) * 4095 / 2))))

def apply_acceleration_curve(progress):
    """Apply acceleration curve to throttle progress (0.0 to 1.0)"""
    if progress <= 0:
        return 0.0
    if progress >= 1:
        return 1.0
    
    if ACCELERATION_CURVE == "linear":
        return progress
    
    elif ACCELERATION_CURVE == "exponential":
        # Exponential curve: starts slow, accelerates faster
        return progress ** CURVE_STRENGTH
    
    elif ACCELERATION_CURVE == "quadratic":
        # Quadratic curve: gentle acceleration curve
        return progress ** 2
    
    elif ACCELERATION_CURVE == "s_curve":
        # S-curve: slow start, fast middle, slow end (like real car)
        import math
        # Use a sigmoid-like function
        x = (progress - 0.5) * CURVE_STRENGTH * 2  # Scale and center around 0
        return 1 / (1 + math.exp(-x))
    
    else:
        # Default to linear if unknown curve type
        return progress

class MCP4725:
    def __init__(self, bus, addr):
        self.bus = bus; self.addr = addr
    def write(self, val):
        val = max(0, min(4095, int(val)))
        hi = (val >> 4) & 0xFF
        lo = (val & 0x0F) << 4
        # Prefer "write DAC register" (0x40)
        try:
            self.bus.write_i2c_block_data(self.addr, 0x40, [hi, lo])
        except OSError:
            # Fallback fast-write w/o command byte
            msg = i2c_msg.write(self.addr, bytes([hi, lo]))
            self.bus.i2c_rdwr(msg)

def main():
    # Detect input device and controller type
    if len(sys.argv) < 2:
        device_info = find_input_device()
        if isinstance(device_info, tuple):
            dev_path, controller_type = device_info
        else:
            dev_path = device_info
            controller_type = detect_controller_type(dev_path)
    else:
        dev_path = sys.argv[1]
        controller_type = detect_controller_type(dev_path)
    
    print("Using input:", dev_path)
    print("Controller type:", controller_type)
    
    if USE_SEPARATE_PEDALS and PEDAL_MODE == "buttons":
        print("Pedal mode: Separate button pedals")
        print("Forward codes:", FORWARD_PEDAL_CODES)
        print("Reverse codes:", REVERSE_PEDAL_CODES)
    else:
        print("Pedal mode: Single axis throttle")

    bus = SMBus(I2C_BUS)
    dac_st = MCP4725(bus, STEERING_ADDR)
    dac_th = MCP4725(bus, THROTTLE_ADDR)

    dev = InputDevice(dev_path)
    if GRAB_DEVICE:
        try: dev.grab()
        except: pass

    # auto-cal mins/maxes for axes
    ax_min = {'x': +32767, 'y': +32767, 'forward': 0, 'reverse': 0}
    ax_max = {'x': -32768, 'y': -32768, 'forward': 255, 'reverse': 255}
    ax_val = {'x': 0, 'y': 0, 'forward': 0, 'reverse': 0}
    
    # Button states for pedals
    button_states = {'forward': False, 'reverse': False}
    
    # Duration-based throttle system
    button_press_start_time = {'forward': None, 'reverse': None}
    throttle_ramp_duration = THROTTLE_RAMP_DURATION  # Time to reach full throttle from config
    
    # Output smoothing for stable output
    steering_filter = [0.0] * 5  # 5-sample moving average
    throttle_filter = [0.0] * 3  # 3-sample moving average for faster response
    filter_index = 0

    center = 2048
    dac_st.write(center); dac_th.write(center)

    period = 1.0 / UPDATE_HZ
    last = time.time()

    import select

    try:
        while True:
            # Use select to check if input is available (non-blocking)
            ready, _, _ = select.select([dev], [], [], 0.001)  # 1ms timeout
            
            if ready:
                # Process available input events
                try:
                    for event in dev.read():
                        # Handle axis events 
                        if event.type == ecodes.EV_ABS:
                            code = event.code; val = event.value
                            
                            # Determine axis based on controller type
                            ax = None
                            if controller_type == "xbox":
                                # Xbox controller mapping
                                if code == ecodes.ABS_X:  # Left stick X for steering
                                    ax = 'x'
                                elif code == ecodes.ABS_RZ and XBOX_USE_TRIGGERS:  # Right trigger
                                    ax = 'forward'
                                elif code == ecodes.ABS_Z and XBOX_USE_TRIGGERS:   # Left trigger  
                                    ax = 'reverse'
                                elif code in THROTTLE_CODES and not XBOX_USE_TRIGGERS:
                                    ax = 'y'
                            else:
                                # T80 or generic controller mapping
                                if code in STEERING_CODES: 
                                    ax = 'x'
                                elif code in THROTTLE_CODES: 
                                    ax = 'y'
                            
                            if ax:
                                ax_min[ax] = min(ax_min.get(ax, val), val)
                                ax_max[ax] = max(ax_max.get(ax, val), val)
                                ax_val[ax] = val
                        
                        # Handle button events (pedals)
                        elif event.type == ecodes.EV_KEY and USE_SEPARATE_PEDALS and PEDAL_MODE == "buttons":
                            code = event.code
                            pressed = event.value == 1
                            
                            # Handle buttons based on controller type
                            if controller_type == "xbox":
                                # Xbox controller button mapping
                                if code in [ecodes.BTN_A, ecodes.BTN_SOUTH, ecodes.BTN_X, ecodes.BTN_WEST]:
                                    button_states['forward'] = pressed
                                    print(f"Xbox Forward: {'PRESSED' if pressed else 'RELEASED'}")
                                elif code in [ecodes.BTN_B, ecodes.BTN_EAST, ecodes.BTN_Y, ecodes.BTN_NORTH]:
                                    button_states['reverse'] = pressed
                                    print(f"Xbox Reverse: {'PRESSED' if pressed else 'RELEASED'}")
                            else:
                                # T80 or generic controller
                                if code in FORWARD_PEDAL_CODES:
                                    button_states['forward'] = pressed
                                    print(f"Forward pedal: {'PRESSED' if pressed else 'RELEASED'}")
                                elif code in REVERSE_PEDAL_CODES:
                                    button_states['reverse'] = pressed
                                    print(f"Reverse pedal: {'PRESSED' if pressed else 'RELEASED'}")
                
                except BlockingIOError:
                    # No more events available, which is normal
                    pass

            # Process at specified rate (this now runs continuously)
            now = time.time()
            if now - last >= period:
                last = now
                
                # Process steering
                x = normalize(ax_val['x'], ax_min['x'], ax_max['x'])
                x = expo(apply_deadzone(x, DEADZONE), EXPO)
                if INVERT_STEERING: x = -x
                
                # Process throttle based on mode
                if USE_SEPARATE_PEDALS and PEDAL_MODE == "buttons":
                    # Duration-based throttle for button pedals
                    forward_pressed = button_states['forward']
                    reverse_pressed = button_states['reverse']
                    
                    current_time = time.time()
                    
                    # Handle forward pedal
                    if forward_pressed and not reverse_pressed:
                        # Forward button is held - track duration and calculate throttle
                        if button_press_start_time['forward'] is None:
                            # Button just pressed - start timing
                            button_press_start_time['forward'] = current_time
                        
                        # Calculate throttle based on how long button has been held
                        press_duration = current_time - button_press_start_time['forward']
                        linear_progress = min(1.0, press_duration / throttle_ramp_duration)
                        y = apply_acceleration_curve(linear_progress)
                        
                    # Handle reverse pedal  
                    elif reverse_pressed and not forward_pressed:
                        # Reverse button - immediate full reverse (no curve for safety)
                        y = -1.0
                        # Reset timing (not used for reverse, but keep clean)
                        button_press_start_time['reverse'] = None
                        
                    else:
                        # No buttons pressed OR both pressed (safety) = instant zero
                        y = 0.0
                        button_press_start_time['forward'] = None
                        button_press_start_time['reverse'] = None
                else:
                    # Process throttle based on controller type and mode
                    if controller_type == "xbox" and XBOX_USE_TRIGGERS and PEDAL_MODE == "axes":
                        # Xbox triggers: Convert from 0-255 range to -1 to +1
                        forward_raw = ax_val.get('forward', 0)
                        reverse_raw = ax_val.get('reverse', 0)
                        
                        # Normalize triggers from their typical 0-255 range
                        forward_norm = max(0, min(1, forward_raw / 255.0))
                        reverse_norm = max(0, min(1, reverse_raw / 255.0))
                        
                        # Combine: forward gives positive, reverse gives negative
                        y = forward_norm - reverse_norm
                        
                        # Skip deadzone and expo processing for raw output mode
                        if not XBOX_RAW_OUTPUT:
                            y = expo(apply_deadzone(y, DEADZONE), EXPO)
                    else:
                        # Traditional single axis throttle
                        y = normalize(ax_val['y'], ax_min['y'], ax_max['y'])
                        if not XBOX_RAW_OUTPUT:
                            y = expo(apply_deadzone(y, DEADZONE), EXPO)
                
                if INVERT_THROTTLE: y = -y
                
                # Apply output smoothing for stable output (unless raw output is enabled)
                if XBOX_RAW_OUTPUT and controller_type == "xbox" and XBOX_USE_TRIGGERS:
                    # Raw output mode: send values directly without smoothing
                    dac_st.write(to_dac12(x))
                    dac_th.write(to_dac12(y))
                else:
                    # Normal mode: use smoothing filters
                    # Update circular buffer
                    steering_filter[filter_index % len(steering_filter)] = x
                    throttle_filter[filter_index % len(throttle_filter)] = y
                    filter_index += 1
                    
                    # Calculate smoothed outputs
                    x_smooth = sum(steering_filter) / len(steering_filter)
                    y_smooth = sum(throttle_filter) / len(throttle_filter)

                    dac_st.write(to_dac12(x_smooth))
                    dac_th.write(to_dac12(y_smooth))
            
            # Small sleep to prevent excessive CPU usage
            time.sleep(0.001)  # 1ms sleep

    except KeyboardInterrupt:
        pass
    finally:
        try: dac_st.write(center); dac_th.write(center)
        except: pass
        try:
            if GRAB_DEVICE: dev.ungrab()
        except: pass
        bus.close()

if __name__ == "__main__":
    main()
