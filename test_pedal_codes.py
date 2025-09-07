#!/usr/bin/env python3
"""
Simple test script to identify button codes for your pedals
Run this to see what codes your pedals generate
"""

import sys
import time
from evdev import InputDevice, ecodes, list_devices

def find_input_device():
    """Find available input devices"""
    devices = list_devices()
    print("Available input devices:")
    for i, device_path in enumerate(devices):
        try:
            device = InputDevice(device_path)
            print(f"{i}: {device_path} - {device.name}")
        except:
            print(f"{i}: {device_path} - (Cannot access)")
    
    if not devices:
        print("No input devices found!")
        return None
    
    # Try to find Thrustmaster device automatically
    for device_path in devices:
        try:
            device = InputDevice(device_path)
            if "Thrustmaster" in device.name:
                print(f"\nAuto-selected: {device_path} - {device.name}")
                return device_path
        except:
            continue
    
    # Ask user to select
    try:
        choice = int(input(f"\nEnter device number (0-{len(devices)-1}): "))
        if 0 <= choice < len(devices):
            return devices[choice]
    except:
        pass
    
    return devices[0] if devices else None

def monitor_events(device_path):
    """Monitor events from the device"""
    try:
        device = InputDevice(device_path)
        print(f"\nMonitoring events from: {device.name}")
        print("Press your pedals to see their button codes...")
        print("Press Ctrl+C to exit\n")
        
        for event in device.read_loop():
            if event.type == ecodes.EV_KEY:
                # Button events
                action = "PRESSED" if event.value else "RELEASED"
                print(f"Button Event: code={event.code} ({ecodes.KEY[event.code] if event.code in ecodes.KEY else 'UNKNOWN'}), value={event.value} ({action})")
                
                # Show specific pedal codes we're looking for
                if event.code == ecodes.BTN_TR:
                    print("  -> This is BTN_TR (Right Trigger) - good for forward pedal!")
                elif event.code == ecodes.BTN_TL:
                    print("  -> This is BTN_TL (Left Trigger) - good for reverse pedal!")
                elif event.code == ecodes.BTN_TRIGGER:
                    print("  -> This is BTN_TRIGGER - alternative trigger button")
                elif event.code == ecodes.BTN_THUMB:
                    print("  -> This is BTN_THUMB - thumb button")
                
            elif event.type == ecodes.EV_ABS:
                # Analog axis events
                if event.code in [ecodes.ABS_X, ecodes.ABS_RX]:
                    print(f"Steering Axis: code={event.code} ({ecodes.ABS[event.code]}), value={event.value}")
                elif event.code in [ecodes.ABS_Y, ecodes.ABS_RY, ecodes.ABS_Z, ecodes.ABS_RZ, 
                                   ecodes.ABS_THROTTLE, ecodes.ABS_BRAKE]:
                    print(f"Throttle/Pedal Axis: code={event.code} ({ecodes.ABS[event.code]}), value={event.value}")
                else:
                    print(f"Other Axis: code={event.code} ({ecodes.ABS[event.code] if event.code in ecodes.ABS else 'UNKNOWN'}), value={event.value}")
            
            elif event.type == ecodes.EV_SYN:
                # Sync events (end of event group) - usually ignore these
                pass
            else:
                # Other event types
                print(f"Other Event: type={event.type}, code={event.code}, value={event.value}")
                
    except KeyboardInterrupt:
        print("\nStopped monitoring.")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("T80 Pedal Button Code Finder")
    print("="*40)
    
    device_path = find_input_device()
    if not device_path:
        print("No device selected. Exiting.")
        return
    
    monitor_events(device_path)

if __name__ == "__main__":
    main()
