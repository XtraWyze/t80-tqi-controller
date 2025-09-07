#!/usr/bin/env python3
"""
Bluetooth Controller Utilities
Helper functions for managing Bluetooth controller connections
"""

import subprocess
import time
import os
from evdev import InputDevice

def check_bluetooth_status():
    """Check if Bluetooth adapter is powered and available"""
    try:
        result = subprocess.run(['bluetoothctl', 'show'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return "Powered: yes" in result.stdout
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def get_bluetooth_controllers():
    """Get list of paired Bluetooth controllers with connection status"""
    controllers = []
    try:
        # Get paired devices
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
                            # Check connection status
                            info_result = subprocess.run(['bluetoothctl', 'info', mac], 
                                                       capture_output=True, text=True, timeout=3)
                            connected = "Connected: yes" in info_result.stdout if info_result.returncode == 0 else False
                            controllers.append({
                                'mac': mac,
                                'name': name,
                                'connected': connected
                            })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return controllers

def connect_controller(mac_address):
    """Connect to a specific Bluetooth controller"""
    try:
        # Try to connect
        result = subprocess.run(['bluetoothctl', 'connect', mac_address], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Connection timeout"
    except FileNotFoundError:
        return False, "", "bluetoothctl not found"

def disconnect_controller(mac_address):
    """Disconnect a specific Bluetooth controller"""
    try:
        result = subprocess.run(['bluetoothctl', 'disconnect', mac_address], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Disconnection timeout"
    except FileNotFoundError:
        return False, "", "bluetoothctl not found"

def scan_for_controllers(duration=10):
    """Scan for new Bluetooth controllers"""
    try:
        # Start discovery
        subprocess.run(['bluetoothctl', 'discoverable', 'on'], 
                      capture_output=True, text=True, timeout=3)
        subprocess.run(['bluetoothctl', 'pairable', 'on'], 
                      capture_output=True, text=True, timeout=3)
        subprocess.run(['bluetoothctl', 'scan', 'on'], 
                      capture_output=True, text=True, timeout=3)
        
        # Wait for scan duration
        time.sleep(duration)
        
        # Stop discovery
        subprocess.run(['bluetoothctl', 'scan', 'off'], 
                      capture_output=True, text=True, timeout=3)
        
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def get_connected_input_devices():
    """Get list of currently connected input devices"""
    devices = []
    for i in range(20):  # Check event0 through event19
        device_path = f"/dev/input/event{i}"
        if os.path.exists(device_path):
            try:
                device = InputDevice(device_path)
                devices.append({
                    'path': device_path,
                    'name': device.name,
                    'phys': getattr(device, 'phys', ''),
                    'vendor': getattr(device.info, 'vendor', 0),
                    'product': getattr(device.info, 'product', 0)
                })
                device.close()
            except (OSError, PermissionError):
                continue
    return devices

def is_xbox_controller(device_name):
    """Check if a device name indicates an Xbox controller"""
    xbox_indicators = ['xbox', 'microsoft', 'controller']
    return any(indicator in device_name.lower() for indicator in xbox_indicators)

def find_active_controllers():
    """Find all active game controllers (USB and Bluetooth)"""
    controllers = []
    
    # Check /dev/input/by-id for USB controllers
    byid = "/dev/input/by-id"
    if os.path.isdir(byid):
        for name in os.listdir(byid):
            if "event" in name:
                device_path = os.path.join(byid, name)
                try:
                    device = InputDevice(device_path)
                    if any(term in name.lower() for term in ["thrustmaster", "microsoft", "xbox", "controller", "gamepad"]):
                        controllers.append({
                            'path': device_path,
                            'name': device.name,
                            'type': 'usb',
                            'connection': 'wired'
                        })
                    device.close()
                except (OSError, PermissionError):
                    continue
    
    # Check input devices for Bluetooth controllers
    bluetooth_controllers = get_bluetooth_controllers()
    input_devices = get_connected_input_devices()
    
    for device in input_devices:
        # Check if this is a Bluetooth controller
        for bt_controller in bluetooth_controllers:
            if bt_controller['connected'] and (
                bt_controller['name'].lower() in device['name'].lower() or
                device['name'].lower() in bt_controller['name'].lower()
            ):
                controllers.append({
                    'path': device['path'],
                    'name': device['name'],
                    'type': 'bluetooth',
                    'connection': 'wireless',
                    'mac': bt_controller['mac']
                })
                break
    
    return controllers

if __name__ == "__main__":
    print("=== Bluetooth Controller Status ===")
    print(f"Bluetooth Active: {check_bluetooth_status()}")
    
    print("\n=== Paired Controllers ===")
    controllers = get_bluetooth_controllers()
    for controller in controllers:
        status = "🟢 Connected" if controller['connected'] else "🔴 Disconnected"
        print(f"{status} - {controller['name']} ({controller['mac']})")
    
    print("\n=== Active Input Controllers ===")
    active_controllers = find_active_controllers()
    for controller in active_controllers:
        print(f"{controller['type'].upper()} - {controller['name']} @ {controller['path']}")
