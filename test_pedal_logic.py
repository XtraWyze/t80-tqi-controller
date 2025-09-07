#!/usr/bin/env python3
"""
Test script to demonstrate the new pedal logic
Shows real-time pedal states and throttle output values
"""

import time
from evdev import InputDevice, ecodes

# Find T80 device
def find_t80():
    byid = "/dev/input/by-id"
    import os
    if os.path.isdir(byid):
        for name in os.listdir(byid):
            if "Thrustmaster" in name and "event" in name:
                return os.path.join(byid, name)
    return "/dev/input/event0"

def main():
    dev_path = find_t80()
    print(f"Testing pedal logic with: {dev_path}")
    print("\nPedal Logic Test:")
    print("- Forward pedal only: Output = +1.0 (FORWARD)")
    print("- Reverse pedal only: Output = -1.0 (REVERSE)")  
    print("- Both pedals:        Output =  0.0 (NEUTRAL - Safety)")
    print("- No pedals:          Output =  0.0 (NEUTRAL)")
    print("\nPress pedals to test... (Ctrl+C to exit)")
    print("-" * 50)
    
    # Button codes
    FORWARD_CODES = {ecodes.BTN_TR, ecodes.BTN_TRIGGER}
    REVERSE_CODES = {ecodes.BTN_TL, ecodes.BTN_THUMB}
    
    # Button states
    forward_pressed = False
    reverse_pressed = False
    
    dev = InputDevice(dev_path)
    
    try:
        for event in dev.read_loop():
            if event.type == ecodes.EV_KEY:
                code = event.code
                pressed = event.value == 1
                
                if code in FORWARD_CODES:
                    forward_pressed = pressed
                elif code in REVERSE_CODES:
                    reverse_pressed = pressed
                else:
                    continue
                
                # Calculate throttle output using your requested logic
                if forward_pressed and reverse_pressed:
                    throttle_output = 0.0
                    status = "NEUTRAL (Both pressed - Safety)"
                elif forward_pressed:
                    throttle_output = 1.0
                    status = "FORWARD"
                elif reverse_pressed:
                    throttle_output = -1.0
                    status = "REVERSE"
                else:
                    throttle_output = 0.0
                    status = "NEUTRAL (No pedals)"
                
                print(f"Forward: {'ON ' if forward_pressed else 'OFF'} | "
                      f"Reverse: {'ON ' if reverse_pressed else 'OFF'} | "
                      f"Output: {throttle_output:+4.1f} | {status}")
                
    except KeyboardInterrupt:
        print("\nTest completed!")

if __name__ == "__main__":
    main()
