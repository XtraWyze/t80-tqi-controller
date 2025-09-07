#!/usr/bin/env python3
import time, math, os, sys
from evdev import InputDevice, ecodes
from smbus2 import SMBus, i2c_msg

# ---- Config ----
I2C_BUS = 1
STEERING_ADDR = 0x60     # set after testing
THROTTLE_ADDR = 0x61
UPDATE_HZ = 200
DEADZONE = 0.02
EXPO = 0.25
CLAMP = 0.98
INVERT_THROTTLE = True   # flip if gas/brake reversed
INVERT_STEERING = False
GRAB_DEVICE = True

# Pedal configuration
USE_SEPARATE_PEDALS = True  # True for button pedals, False for single axis
PEDAL_MODE = "buttons"      # "buttons", "axes", or "split_axis"

# Analog pedal feel settings
ANALOG_PEDAL_FEEL = True    # Enable car-like acceleration ramping
ACCELERATION_CURVE = "exponential"  # "linear", "exponential", "s_curve", "quadratic"
CURVE_STRENGTH = 2.0        # Strength of the curve effect (1.0 = linear, higher = more curved)

# Button codes for pedals (adjust these based on your T80 wheel)
FORWARD_PEDAL_CODES = {ecodes.BTN_TR, ecodes.BTN_TRIGGER}
REVERSE_PEDAL_CODES = {ecodes.BTN_TL, ecodes.BTN_THUMB}

# Map your input device automatically:
DEFAULT_INPUT = "/dev/input/event0"
def find_t80():
    byid = "/dev/input/by-id"
    if os.path.isdir(byid):
        for name in os.listdir(byid):
            if "Thrustmaster" in name and "event" in name:
                return os.path.join(byid, name)
    return DEFAULT_INPUT

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
    dev_path = find_t80() if len(sys.argv) < 2 else sys.argv[1]
    print("Using input:", dev_path)
    
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
    ax_min = {'x': +32767, 'y': +32767}
    ax_max = {'x': -32768, 'y': -32768}
    ax_val = {'x': 0, 'y': 0}
    
    # Button states for pedals
    button_states = {'forward': False, 'reverse': False}
    
    # Duration-based throttle system
    button_press_start_time = {'forward': None, 'reverse': None}
    throttle_ramp_duration = 1.0  # Time to reach full throttle (1 second)
    
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
                        # Handle axis events (steering)
                        if event.type == ecodes.EV_ABS:
                            code = event.code; val = event.value
                            if code in STEERING_CODES: ax = 'x'
                            elif code in THROTTLE_CODES: ax = 'y'
                            else: continue

                            ax_min[ax] = min(ax_min[ax], val)
                            ax_max[ax] = max(ax_max[ax], val)
                            ax_val[ax] = val
                        
                        # Handle button events (pedals)
                        elif event.type == ecodes.EV_KEY and USE_SEPARATE_PEDALS and PEDAL_MODE == "buttons":
                            code = event.code
                            pressed = event.value == 1
                            
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
                        # Reverse button is held - track duration and calculate throttle
                        if button_press_start_time['reverse'] is None:
                            # Button just pressed - start timing
                            button_press_start_time['reverse'] = current_time
                        
                        # Calculate throttle based on how long button has been held
                        press_duration = current_time - button_press_start_time['reverse']
                        linear_progress = min(1.0, press_duration / throttle_ramp_duration)
                        y = -apply_acceleration_curve(linear_progress)
                        
                    else:
                        # No buttons pressed OR both pressed (safety) = instant zero
                        y = 0.0
                        button_press_start_time['forward'] = None
                        button_press_start_time['reverse'] = None
                else:
                    # Traditional single axis throttle
                    y = normalize(ax_val['y'], ax_min['y'], ax_max['y'])
                    y = expo(apply_deadzone(y, DEADZONE), EXPO)
                
                if INVERT_THROTTLE: y = -y
                
                # Apply output smoothing for stable output
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
