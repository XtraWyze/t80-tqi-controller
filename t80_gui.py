#!/usr/bin/env python3
"""
T80 to TQi GUI Controller
A GUI application for controlling steering wheel and pedal inputs
with configurable mappings and real-time visualization.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import time
import math
import os
import sys
import threading
import subprocess
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from evdev import InputDevice, ecodes
from smbus2 import SMBus, i2c_msg
import json

class Config:
    """Configuration management"""
    def __init__(self):
        self.config_file = "t80_config.json"
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
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
            "swap_controls": False,
            "grab_device": True,
            "use_separate_pedals": True,
            "pedal_mode": "buttons",  # "buttons", "axes", or "split_axis"
            "forward_pedal_codes": [ecodes.BTN_TR, ecodes.BTN_TRIGGER],
            "reverse_pedal_codes": [ecodes.BTN_TL, ecodes.BTN_THUMB],
            "combined_axis_code": ecodes.ABS_Z,  # For split_axis mode
            "steering_codes": [ecodes.ABS_X, ecodes.ABS_RX],
            "throttle_codes": [ecodes.ABS_Y, ecodes.ABS_RY],
            "steering_trim": 0.0,  # Manual trim offset for steering (-1.0 to +1.0)
            "throttle_trim": 0.0,   # Manual trim offset for throttle (-1.0 to +1.0)
            "analog_pedal_feel": True,  # Enable analog-like ramping for button pedals
            "throttle_ramp_duration": 1.0,   # Time in seconds to reach full throttle when button held
            "acceleration_curve": "exponential",  # "linear", "exponential", "s_curve", "quadratic"
            "curve_strength": 2.0   # Strength of the curve effect (1.0 = linear, higher = more curved)
        }
        
        try:
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                self.__dict__.update(default_config)
                self.__dict__.update(loaded_config)
        except FileNotFoundError:
            self.__dict__.update(default_config)
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        config_dict = {k: v for k, v in self.__dict__.items() if k != 'config_file'}
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

class MCP4725:
    """MCP4725 DAC controller"""
    def __init__(self, bus, addr):
        self.bus = bus
        self.addr = addr
    
    def write(self, val):
        val = max(0, min(4095, int(val)))
        hi = (val >> 4) & 0xFF
        lo = (val & 0x0F) << 4
        try:
            self.bus.write_i2c_block_data(self.addr, 0x40, [hi, lo])
        except OSError:
            msg = i2c_msg.write(self.addr, bytes([hi, lo]))
            self.bus.i2c_rdwr(msg)

class InputController:
    """Handles input device communication"""
    def __init__(self, config):
        self.config = config
        self.device = None
        self.running = False
        self.thread = None
        
        # Input tracking
        self.ax_min = {'steering': 32767, 'throttle': 32767, 'combined_axis': 32767}
        self.ax_max = {'steering': -32768, 'throttle': -32768, 'combined_axis': -32768}
        self.ax_val = {'steering': 0, 'throttle': 0, 'combined_axis': 0}
        
        # Button states for pedals
        self.button_states = {'forward_pedal': False, 'reverse_pedal': False}
        
        # Analog pedal feel - duration-based system
        self.button_press_start_time = {'forward': None, 'reverse': None}  # When button was first pressed
        
        # Output smoothing for stable output
        self.steering_filter = [0.0] * 5  # 5-sample moving average
        self.throttle_filter = [0.0] * 3  # 3-sample moving average for faster response
        self.filter_index = 0
        
        # Binding system
        self.binding_mode = False
        self.binding_target = None  # 'forward', 'reverse', 'steering', 'throttle'
        self.binding_callback = None
        
        self.processed_values = {'steering': 0.0, 'throttle': 0.0}
        
        # I2C setup
        try:
            self.bus = SMBus(config.i2c_bus)
            self.dac_steering = MCP4725(self.bus, config.steering_addr)
            self.dac_throttle = MCP4725(self.bus, config.throttle_addr)
            self.i2c_available = True
        except Exception as e:
            print(f"I2C not available: {e}")
            self.i2c_available = False
    
    def find_input_device(self):
        """Find the Thrustmaster T80 device"""
        byid = "/dev/input/by-id"
        if os.path.isdir(byid):
            for name in os.listdir(byid):
                if "Thrustmaster" in name and "event" in name:
                    return os.path.join(byid, name)
        return "/dev/input/event0"
    
    def connect_device(self, device_path=None):
        """Connect to input device"""
        try:
            if device_path is None:
                device_path = self.find_input_device()
            
            self.device = InputDevice(device_path)
            if self.config.grab_device:
                self.device.grab()
            return True, f"Connected to {device_path}"
        except Exception as e:
            return False, f"Failed to connect: {e}"
    
    def disconnect_device(self):
        """Disconnect from input device"""
        self.stop()
        if self.device:
            try:
                if self.config.grab_device:
                    self.device.ungrab()
                self.device.close()
            except:
                pass
            self.device = None
    
    def normalize(self, value, vmin, vmax):
        """Normalize value to -1.0 to 1.0 range"""
        span = (vmax - vmin) or 1
        x = (2.0 * (value - vmin) / span) - 1.0
        return max(-1.0, min(1.0, x))
    
    def apply_deadzone(self, x, deadzone):
        """Apply deadzone to input"""
        if abs(x) <= deadzone:
            return 0.0
        sign = 1 if x >= 0 else -1
        return sign * (abs(x) - deadzone) / (1.0 - deadzone)
    
    def apply_expo(self, x, expo):
        """Apply exponential curve"""
        if expo <= 0:
            return x
        return (1 - expo) * x + expo * (x ** 3)
    
    def to_dac12(self, x):
        """Convert normalized value to 12-bit DAC value"""
        x = max(-self.config.clamp, min(self.config.clamp, x)) / self.config.clamp
        return max(0, min(4095, int(round((x + 1) * 4095 / 2))))
    
    def apply_acceleration_curve(self, progress):
        """Apply acceleration curve to throttle progress (0.0 to 1.0)"""
        if progress <= 0:
            return 0.0
        if progress >= 1:
            return 1.0
        
        curve_type = self.config.acceleration_curve
        strength = self.config.curve_strength
        
        if curve_type == "linear":
            return progress
        
        elif curve_type == "exponential":
            # Exponential curve: starts slow, accelerates faster
            return progress ** strength
        
        elif curve_type == "quadratic":
            # Quadratic curve: gentle acceleration curve
            return progress ** 2
        
        elif curve_type == "s_curve":
            # S-curve: slow start, fast middle, slow end (like real car)
            import math
            # Use a sigmoid-like function
            x = (progress - 0.5) * strength * 2  # Scale and center around 0
            return 1 / (1 + math.exp(-x))
        
        else:
            # Default to linear if unknown curve type
            return progress
    
    def process_inputs(self):
        """Process and apply input transformations"""
        # Normalize steering input
        steering_norm = self.normalize(self.ax_val['steering'], 
                                     self.ax_min['steering'], 
                                     self.ax_max['steering'])
        
        # Handle throttle based on pedal mode
        if self.config.use_separate_pedals:
            if self.config.pedal_mode == "buttons":
                # Button-based pedals with duration-based throttle
                forward_pressed = self.button_states['forward_pedal']
                reverse_pressed = self.button_states['reverse_pedal']
                
                current_time = time.time()
                
                # Handle forward pedal
                if forward_pressed and not reverse_pressed:
                    # Forward button is held - track duration and calculate throttle
                    if self.button_press_start_time['forward'] is None:
                        # Button just pressed - start timing
                        self.button_press_start_time['forward'] = current_time
                        print(f"Forward button pressed - starting timer at {current_time}")
                    
                    # Calculate throttle based on how long button has been held
                    press_duration = current_time - self.button_press_start_time['forward']
                    linear_progress = min(1.0, press_duration / self.config.throttle_ramp_duration)
                    throttle_norm = self.apply_acceleration_curve(linear_progress)
                    print(f"Forward held for {press_duration:.3f}s -> linear: {linear_progress:.3f} -> curved: {throttle_norm:.3f}")
                    
                # Handle reverse pedal  
                elif reverse_pressed and not forward_pressed:
                    # Reverse button is held - track duration and calculate throttle
                    if self.button_press_start_time['reverse'] is None:
                        # Button just pressed - start timing
                        self.button_press_start_time['reverse'] = current_time
                        print(f"Reverse button pressed - starting timer at {current_time}")
                    
                    # Calculate throttle based on how long button has been held
                    press_duration = current_time - self.button_press_start_time['reverse']
                    linear_progress = min(1.0, press_duration / self.config.throttle_ramp_duration)
                    throttle_norm = -self.apply_acceleration_curve(linear_progress)
                    print(f"Reverse held for {press_duration:.3f}s -> linear: {linear_progress:.3f} -> curved: {throttle_norm:.3f}")
                    
                else:
                    # No buttons pressed OR both pressed (safety) = instant zero
                    if self.button_press_start_time['forward'] is not None or self.button_press_start_time['reverse'] is not None:
                        print("Buttons released - throttle to zero")
                    throttle_norm = 0.0
                    self.button_press_start_time['forward'] = None
                    self.button_press_start_time['reverse'] = None
                
            elif self.config.pedal_mode == "split_axis":
                # Single axis split: center = neutral, one direction = forward, other = reverse
                combined_norm = self.normalize(self.ax_val['combined_axis'],
                                             self.ax_min['combined_axis'],
                                             self.ax_max['combined_axis'])
                # Split around center: positive = forward, negative = reverse
                throttle_norm = combined_norm
                
            else:  # "axes" mode - separate analog axes
                forward_norm = self.normalize(self.ax_val['forward'],
                                            self.ax_min['forward'],
                                            self.ax_max['forward'])
                reverse_norm = self.normalize(self.ax_val['reverse'],
                                            self.ax_min['reverse'],
                                            self.ax_max['reverse'])
                # Combine: forward gives positive, reverse gives negative
                throttle_norm = forward_norm - reverse_norm
        else:
            # Traditional single axis throttle
            throttle_norm = self.normalize(self.ax_val['throttle'],
                                         self.ax_min['throttle'],
                                         self.ax_max['throttle'])
        
        # Apply deadzone and expo
        if (self.config.pedal_mode == "buttons" and self.config.use_separate_pedals and 
            self.config.analog_pedal_feel):
            # Analog ramped buttons - apply light expo to throttle for smooth feel
            steering_processed = self.apply_expo(
                self.apply_deadzone(steering_norm, self.config.deadzone),
                self.config.expo
            )
            # Apply gentle expo to ramped throttle for smoother feel
            throttle_processed = self.apply_expo(throttle_norm, self.config.expo * 0.5)
        elif self.config.pedal_mode == "buttons" and self.config.use_separate_pedals:
            # Digital buttons - no processing on throttle
            steering_processed = self.apply_expo(
                self.apply_deadzone(steering_norm, self.config.deadzone),
                self.config.expo
            )
            throttle_processed = throttle_norm  # Keep digital values as-is
        else:
            # Apply normal processing to both
            steering_processed = self.apply_expo(
                self.apply_deadzone(steering_norm, self.config.deadzone),
                self.config.expo
            )
            throttle_processed = self.apply_expo(
                self.apply_deadzone(throttle_norm, self.config.deadzone),
                self.config.expo
            )
        
        # Apply inversions
        if self.config.invert_steering:
            steering_processed = -steering_processed
        if self.config.invert_throttle:
            throttle_processed = -throttle_processed
        
        # Apply manual trim offsets
        steering_processed = max(-1.0, min(1.0, steering_processed + self.config.steering_trim))
        throttle_processed = max(-1.0, min(1.0, throttle_processed + self.config.throttle_trim))
        
        # Store processed values
        self.processed_values['steering'] = steering_processed
        self.processed_values['throttle'] = throttle_processed
        
        # Apply swapping if enabled
        if self.config.swap_controls:
            steering_out = throttle_processed
            throttle_out = steering_processed
        else:
            steering_out = steering_processed
            throttle_out = throttle_processed
        
        # Send to DACs if available
        if self.i2c_available:
            try:
                # Apply output smoothing for stable output
                self.steering_filter[self.filter_index % len(self.steering_filter)] = steering_out
                self.throttle_filter[self.filter_index % len(self.throttle_filter)] = throttle_out
                self.filter_index += 1
                
                # Calculate smoothed outputs
                steering_smooth = sum(self.steering_filter) / len(self.steering_filter)
                throttle_smooth = sum(self.throttle_filter) / len(self.throttle_filter)
                
                self.dac_steering.write(self.to_dac12(steering_smooth))
                self.dac_throttle.write(self.to_dac12(throttle_smooth))
            except Exception as e:
                print(f"DAC write error: {e}")
    
    def input_loop(self):
        """Main input processing loop"""
        if not self.device:
            return
        
        period = 1.0 / self.config.update_hz
        last_update = time.time()
        
        try:
            import select
            
            while self.running:
                # Use select to check if input is available (non-blocking)
                ready, _, _ = select.select([self.device], [], [], 0.001)  # 1ms timeout
                
                if ready:
                    # Process available input events
                    try:
                        for event in self.device.read():
                            if event.type == ecodes.EV_ABS:
                                # Handle analog axis events
                                code = event.code
                                val = event.value
                                
                                # Check if we're in binding mode
                                if self.binding_mode and self.binding_callback:
                                    # Only bind if there's significant movement (avoid noise)
                                    if abs(val) > 1000:  # Threshold for significant movement
                                        self.binding_callback(self.binding_target, code, ecodes.EV_ABS)
                                        continue
                                
                                # Determine which axis this event belongs to
                                axis = None
                                if code in self.config.steering_codes:
                                    axis = 'steering'
                                elif code == self.config.combined_axis_code:
                                    axis = 'combined_axis'
                                elif code in self.config.throttle_codes:
                                    axis = 'throttle'
                                
                                if axis:
                                    # Update min/max for auto-calibration
                                    self.ax_min[axis] = min(self.ax_min[axis], val)
                                    self.ax_max[axis] = max(self.ax_max[axis], val)
                                    self.ax_val[axis] = val
                            
                            elif event.type == ecodes.EV_KEY:
                                # Handle button events (for pedals)
                                code = event.code
                                pressed = bool(event.value)
                                
                                # Check if we're in binding mode
                                if self.binding_mode and pressed and self.binding_callback:
                                    self.binding_callback(self.binding_target, code, ecodes.EV_KEY)
                                    continue
                                
                                if code in self.config.forward_pedal_codes:
                                    self.button_states['forward_pedal'] = pressed
                                    print(f"Forward pedal: {'PRESSED' if pressed else 'RELEASED'}")
                                elif code in self.config.reverse_pedal_codes:
                                    self.button_states['reverse_pedal'] = pressed
                                    print(f"Reverse pedal: {'PRESSED' if pressed else 'RELEASED'}")
                    
                    except BlockingIOError:
                        # No more events available, which is normal
                        pass
                
                # Process at specified rate (this now runs continuously)
                now = time.time()
                if now - last_update >= period:
                    last_update = now
                    self.process_inputs()
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.001)  # 1ms sleep
        
        except Exception as e:
            print(f"Input loop error: {e}")
    
    def start(self):
        """Start input processing"""
        if self.device and not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.input_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop input processing"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def center_outputs(self):
        """Center the DAC outputs"""
        if self.i2c_available:
            try:
                center = 2048
                self.dac_steering.write(center)
                self.dac_throttle.write(center)
            except Exception as e:
                print(f"Error centering outputs: {e}")

class T80GUI:
    """Main GUI application"""
    def __init__(self):
        self.config = Config()
        self.controller = InputController(self.config)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("T80 to TQi Controller")
        self.root.geometry("800x600")
        
        # Set up GUI
        self.setup_gui()
        
        # Start update timer
        self.update_gui()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_gui(self):
        """Set up the GUI elements"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main control tab
        self.setup_main_tab(notebook)
        
        # Configuration tab
        self.setup_config_tab(notebook)
        
        # Calibration tab
        self.setup_calibration_tab(notebook)
        
        # Binding tab
        self.setup_binding_tab(notebook)
        
        # Acceleration curve tab
        self.setup_acceleration_tab(notebook)
        
        # Service control tab
        self.setup_service_tab(notebook)
    
    def setup_main_tab(self, notebook):
        """Set up the main control tab"""
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Main Control")
        
        # Connection frame
        conn_frame = ttk.LabelFrame(main_frame, text="Device Connection")
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(conn_frame, text="Connect Device", 
                  command=self.connect_device).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(conn_frame, text="Disconnect", 
                  command=self.disconnect_device).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.connection_status = ttk.Label(conn_frame, text="Not connected")
        self.connection_status.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Start", 
                  command=self.start_controller).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="Stop", 
                  command=self.stop_controller).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="Center Outputs", 
                  command=self.center_outputs).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Quick settings
        quick_frame = ttk.LabelFrame(main_frame, text="Quick Settings")
        quick_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.swap_var = tk.BooleanVar(value=self.config.swap_controls)
        ttk.Checkbutton(quick_frame, text="Swap Steering/Throttle", 
                       variable=self.swap_var, 
                       command=self.update_swap).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.separate_pedals_var = tk.BooleanVar(value=self.config.use_separate_pedals)
        ttk.Checkbutton(quick_frame, text="Use Separate Pedals", 
                       variable=self.separate_pedals_var, 
                       command=self.update_separate_pedals).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Trim controls frame
        trim_frame = ttk.LabelFrame(main_frame, text="Manual Trim Controls")
        trim_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Steering trim
        steering_trim_frame = ttk.Frame(trim_frame)
        steering_trim_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(steering_trim_frame, text="Steering Trim:").pack(side=tk.LEFT)
        self.steering_trim_var = tk.DoubleVar(value=self.config.steering_trim)
        self.steering_trim_scale = ttk.Scale(steering_trim_frame, from_=-1.0, to=1.0, 
                                           variable=self.steering_trim_var, 
                                           orient=tk.HORIZONTAL, length=200,
                                           command=self.update_steering_trim)
        self.steering_trim_scale.pack(side=tk.LEFT, padx=5)
        self.steering_trim_label = ttk.Label(steering_trim_frame, text="0.00")
        self.steering_trim_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(steering_trim_frame, text="Reset", 
                  command=self.reset_steering_trim).pack(side=tk.LEFT, padx=5)
        
        # Throttle trim
        throttle_trim_frame = ttk.Frame(trim_frame)
        throttle_trim_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(throttle_trim_frame, text="Throttle Trim:").pack(side=tk.LEFT)
        self.throttle_trim_var = tk.DoubleVar(value=self.config.throttle_trim)
        self.throttle_trim_scale = ttk.Scale(throttle_trim_frame, from_=-1.0, to=1.0, 
                                           variable=self.throttle_trim_var, 
                                           orient=tk.HORIZONTAL, length=200,
                                           command=self.update_throttle_trim)
        self.throttle_trim_scale.pack(side=tk.LEFT, padx=5)
        self.throttle_trim_label = ttk.Label(throttle_trim_frame, text="0.00")
        self.throttle_trim_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(throttle_trim_frame, text="Reset", 
                  command=self.reset_throttle_trim).pack(side=tk.LEFT, padx=5)
        
        # Input display frame
        input_frame = ttk.LabelFrame(main_frame, text="Input Values")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create input value displays
        self.setup_input_displays(input_frame)
    
    def setup_input_displays(self, parent):
        """Set up input value display widgets"""
        # Raw values frame
        raw_frame = ttk.LabelFrame(parent, text="Raw Input Values")
        raw_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Steering
        steering_frame = ttk.Frame(raw_frame)
        steering_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(steering_frame, text="Steering:").pack(side=tk.LEFT)
        self.steering_raw_label = ttk.Label(steering_frame, text="0")
        self.steering_raw_label.pack(side=tk.LEFT, padx=10)
        self.steering_progress = ttk.Progressbar(steering_frame, length=200, mode='determinate')
        self.steering_progress.pack(side=tk.LEFT, padx=10)
        
        # Pedal displays based on mode
        if self.config.use_separate_pedals:
            if self.config.pedal_mode == "buttons":
                # Button pedals
                forward_frame = ttk.Frame(raw_frame)
                forward_frame.pack(fill=tk.X, padx=5, pady=2)
                ttk.Label(forward_frame, text="Forward Pedal:").pack(side=tk.LEFT)
                self.forward_button_label = ttk.Label(forward_frame, text="RELEASED")
                self.forward_button_label.pack(side=tk.LEFT, padx=10)
                
                reverse_frame = ttk.Frame(raw_frame)
                reverse_frame.pack(fill=tk.X, padx=5, pady=2)
                ttk.Label(reverse_frame, text="Reverse Pedal:").pack(side=tk.LEFT)
                self.reverse_button_label = ttk.Label(reverse_frame, text="RELEASED")
                self.reverse_button_label.pack(side=tk.LEFT, padx=10)
                
            elif self.config.pedal_mode == "split_axis":
                # Split combined axis
                combined_frame = ttk.Frame(raw_frame)
                combined_frame.pack(fill=tk.X, padx=5, pady=2)
                ttk.Label(combined_frame, text="Combined Axis:").pack(side=tk.LEFT)
                self.combined_raw_label = ttk.Label(combined_frame, text="0")
                self.combined_raw_label.pack(side=tk.LEFT, padx=10)
                self.combined_progress = ttk.Progressbar(combined_frame, length=200, mode='determinate')
                self.combined_progress.pack(side=tk.LEFT, padx=10)
                
            else:
                # Separate analog axes (original mode)
                forward_frame = ttk.Frame(raw_frame)
                forward_frame.pack(fill=tk.X, padx=5, pady=2)
                ttk.Label(forward_frame, text="Forward:").pack(side=tk.LEFT)
                self.forward_raw_label = ttk.Label(forward_frame, text="0")
                self.forward_raw_label.pack(side=tk.LEFT, padx=10)
                self.forward_progress = ttk.Progressbar(forward_frame, length=200, mode='determinate')
                self.forward_progress.pack(side=tk.LEFT, padx=10)
                
                reverse_frame = ttk.Frame(raw_frame)
                reverse_frame.pack(fill=tk.X, padx=5, pady=2)
                ttk.Label(reverse_frame, text="Reverse:").pack(side=tk.LEFT)
                self.reverse_raw_label = ttk.Label(reverse_frame, text="0")
                self.reverse_raw_label.pack(side=tk.LEFT, padx=10)
                self.reverse_progress = ttk.Progressbar(reverse_frame, length=200, mode='determinate')
                self.reverse_progress.pack(side=tk.LEFT, padx=10)
        else:
            # Single throttle
            throttle_frame = ttk.Frame(raw_frame)
            throttle_frame.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(throttle_frame, text="Throttle:").pack(side=tk.LEFT)
            self.throttle_raw_label = ttk.Label(throttle_frame, text="0")
            self.throttle_raw_label.pack(side=tk.LEFT, padx=10)
            self.throttle_progress = ttk.Progressbar(throttle_frame, length=200, mode='determinate')
            self.throttle_progress.pack(side=tk.LEFT, padx=10)
        
        # Processed values frame
        processed_frame = ttk.LabelFrame(parent, text="Processed Output Values")
        processed_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Processed steering
        proc_steering_frame = ttk.Frame(processed_frame)
        proc_steering_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(proc_steering_frame, text="Steering Out:").pack(side=tk.LEFT)
        self.steering_proc_label = ttk.Label(proc_steering_frame, text="0.00")
        self.steering_proc_label.pack(side=tk.LEFT, padx=10)
        self.steering_proc_progress = ttk.Progressbar(proc_steering_frame, length=200, mode='determinate')
        self.steering_proc_progress.pack(side=tk.LEFT, padx=10)
        
        # Processed throttle
        proc_throttle_frame = ttk.Frame(processed_frame)
        proc_throttle_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(proc_throttle_frame, text="Throttle Out:").pack(side=tk.LEFT)
        self.throttle_proc_label = ttk.Label(proc_throttle_frame, text="0.00")
        self.throttle_proc_label.pack(side=tk.LEFT, padx=10)
        self.throttle_proc_progress = ttk.Progressbar(proc_throttle_frame, length=200, mode='determinate')
        self.throttle_proc_progress.pack(side=tk.LEFT, padx=10)
    
    def setup_config_tab(self, notebook):
        """Set up the configuration tab"""
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuration")
        
        # I2C settings
        i2c_frame = ttk.LabelFrame(config_frame, text="I2C Settings")
        i2c_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(i2c_frame, text="I2C Bus:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.i2c_bus_var = tk.IntVar(value=self.config.i2c_bus)
        ttk.Entry(i2c_frame, textvariable=self.i2c_bus_var, width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(i2c_frame, text="Steering Address:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.steering_addr_var = tk.StringVar(value=f"0x{self.config.steering_addr:02x}")
        ttk.Entry(i2c_frame, textvariable=self.steering_addr_var, width=10).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(i2c_frame, text="Throttle Address:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.throttle_addr_var = tk.StringVar(value=f"0x{self.config.throttle_addr:02x}")
        ttk.Entry(i2c_frame, textvariable=self.throttle_addr_var, width=10).grid(row=2, column=1, padx=5, pady=2)
        
        # Control settings
        control_settings_frame = ttk.LabelFrame(config_frame, text="Control Settings")
        control_settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_settings_frame, text="Update Rate (Hz):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.update_hz_var = tk.IntVar(value=self.config.update_hz)
        ttk.Entry(control_settings_frame, textvariable=self.update_hz_var, width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(control_settings_frame, text="Deadzone:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.deadzone_var = tk.DoubleVar(value=self.config.deadzone)
        ttk.Entry(control_settings_frame, textvariable=self.deadzone_var, width=10).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(control_settings_frame, text="Expo:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.expo_var = tk.DoubleVar(value=self.config.expo)
        ttk.Entry(control_settings_frame, textvariable=self.expo_var, width=10).grid(row=2, column=1, padx=5, pady=2)
        
        # Inversion settings
        invert_frame = ttk.LabelFrame(config_frame, text="Inversion Settings")
        invert_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.invert_steering_var = tk.BooleanVar(value=self.config.invert_steering)
        ttk.Checkbutton(invert_frame, text="Invert Steering", 
                       variable=self.invert_steering_var).pack(anchor=tk.W, padx=5, pady=2)
        
        self.invert_throttle_var = tk.BooleanVar(value=self.config.invert_throttle)
        ttk.Checkbutton(invert_frame, text="Invert Throttle", 
                       variable=self.invert_throttle_var).pack(anchor=tk.W, padx=5, pady=2)
        
        # Trim settings
        trim_settings_frame = ttk.LabelFrame(config_frame, text="Trim Settings")
        trim_settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(trim_settings_frame, text="Steering Trim:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.steering_trim_config_var = tk.DoubleVar(value=self.config.steering_trim)
        ttk.Entry(trim_settings_frame, textvariable=self.steering_trim_config_var, width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(trim_settings_frame, text="Throttle Trim:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.throttle_trim_config_var = tk.DoubleVar(value=self.config.throttle_trim)
        ttk.Entry(trim_settings_frame, textvariable=self.throttle_trim_config_var, width=10).grid(row=1, column=1, padx=5, pady=2)
        
        # Pedal mode settings
        pedal_mode_frame = ttk.LabelFrame(config_frame, text="Pedal Mode Settings")
        pedal_mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(pedal_mode_frame, text="Pedal Mode:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.pedal_mode_var = tk.StringVar(value=self.config.pedal_mode)
        pedal_mode_combo = ttk.Combobox(pedal_mode_frame, textvariable=self.pedal_mode_var, 
                                       values=["buttons", "axes", "split_axis"], state="readonly")
        pedal_mode_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Mode descriptions
        mode_info = ttk.Label(pedal_mode_frame, text=
            "buttons: Button pedals (BTN_TR/BTN_TL)\n" +
            "axes: Separate analog axes\n" +
            "split_axis: Single axis split at center",
            justify=tk.LEFT, font=("TkDefaultFont", 8))
        mode_info.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Analog pedal feel settings
        analog_pedal_frame = ttk.LabelFrame(config_frame, text="Analog Pedal Feel")
        analog_pedal_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.analog_pedal_feel_var = tk.BooleanVar(value=self.config.analog_pedal_feel)
        ttk.Checkbutton(analog_pedal_frame, text="Enable Analog Feel (Gradual acceleration, instant release)", 
                       variable=self.analog_pedal_feel_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(analog_pedal_frame, text="Acceleration Speed:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.throttle_ramp_speed_var = tk.DoubleVar(value=self.config.throttle_ramp_speed)
        ttk.Entry(analog_pedal_frame, textvariable=self.throttle_ramp_speed_var, width=10).grid(row=1, column=1, padx=5, pady=2)
        
        analog_info = ttk.Label(analog_pedal_frame, text=
            "When enabled:\n" +
            "• Pedal held = gradually increases throttle\n" +
            "• Pedal released = instantly goes to zero\n" +
            "Acceleration Speed: 1.0-5.0 (higher = faster ramp up)",
            justify=tk.LEFT, font=("TkDefaultFont", 8))
        analog_info.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Save/Load buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="Save Configuration", 
                  command=self.save_configuration).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Configuration", 
                  command=self.load_configuration).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self.reset_configuration).pack(side=tk.LEFT, padx=5)
    
    def setup_calibration_tab(self, notebook):
        """Set up the calibration tab"""
        cal_frame = ttk.Frame(notebook)
        notebook.add(cal_frame, text="Calibration")
        
        # Calibration info
        info_frame = ttk.LabelFrame(cal_frame, text="Calibration Information")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = """
        The system automatically calibrates the min/max values for each input.
        Move all controls through their full range to ensure proper calibration.
        
        For best results:
        1. Connect your device and start the controller
        2. Turn steering wheel fully left and right
        3. Press forward pedal fully down
        4. Press reverse pedal fully down
        5. Check that the progress bars show full range
        """
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(padx=10, pady=10)
        
        # Calibration values display
        values_frame = ttk.LabelFrame(cal_frame, text="Current Calibration Values")
        values_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget for calibration values
        self.cal_text = tk.Text(values_frame, height=15, state=tk.DISABLED)
        self.cal_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Reset calibration button
        ttk.Button(cal_frame, text="Reset Calibration", 
                  command=self.reset_calibration).pack(pady=10)
    
    def setup_binding_tab(self, notebook):
        """Set up the input binding tab"""
        binding_frame = ttk.Frame(notebook)
        notebook.add(binding_frame, text="Input Binding")
        
        # Instructions
        instructions_frame = ttk.LabelFrame(binding_frame, text="How to Use Input Binding")
        instructions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        instructions_text = """
        Input Binding allows you to easily assign controls by clicking and pressing:
        
        1. Make sure your device is connected
        2. Click on a "Bind" button below
        3. Press the control you want to assign (wheel, pedal, button)
        4. The input will be automatically detected and assigned
        5. Click "Save Configuration" to keep your bindings
        
        This makes setup much easier than manually entering codes!
        """
        
        instructions_label = ttk.Label(instructions_frame, text=instructions_text, 
                                     justify=tk.LEFT, wraplength=400)
        instructions_label.pack(padx=10, pady=10)
        
        # Binding status
        status_frame = ttk.LabelFrame(binding_frame, text="Binding Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.binding_status_label = ttk.Label(status_frame, text="Ready to bind inputs", 
                                            foreground="green")
        self.binding_status_label.pack(pady=5)
        
        # Cancel binding button
        self.cancel_binding_button = ttk.Button(status_frame, text="Cancel Binding", 
                                              command=self.cancel_binding, state=tk.DISABLED)
        self.cancel_binding_button.pack(pady=5)
        
        # Steering binding
        steering_frame = ttk.LabelFrame(binding_frame, text="Steering Control")
        steering_frame.pack(fill=tk.X, padx=5, pady=5)
        
        steering_info_frame = ttk.Frame(steering_frame)
        steering_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(steering_info_frame, text="Current:").pack(side=tk.LEFT)
        self.steering_codes_label = ttk.Label(steering_info_frame, text=str(self.config.steering_codes))
        self.steering_codes_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(steering_info_frame, text="Bind Steering", 
                  command=lambda: self.start_binding('steering')).pack(side=tk.RIGHT, padx=5)
        
        # Forward pedal binding
        forward_frame = ttk.LabelFrame(binding_frame, text="Forward Pedal")
        forward_frame.pack(fill=tk.X, padx=5, pady=5)
        
        forward_info_frame = ttk.Frame(forward_frame)
        forward_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(forward_info_frame, text="Current:").pack(side=tk.LEFT)
        self.forward_codes_label = ttk.Label(forward_info_frame, text=str(self.config.forward_pedal_codes))
        self.forward_codes_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(forward_info_frame, text="Bind Forward", 
                  command=lambda: self.start_binding('forward')).pack(side=tk.RIGHT, padx=5)
        
        # Reverse pedal binding
        reverse_frame = ttk.LabelFrame(binding_frame, text="Reverse Pedal")
        reverse_frame.pack(fill=tk.X, padx=5, pady=5)
        
        reverse_info_frame = ttk.Frame(reverse_frame)
        reverse_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(reverse_info_frame, text="Current:").pack(side=tk.LEFT)
        self.reverse_codes_label = ttk.Label(reverse_info_frame, text=str(self.config.reverse_pedal_codes))
        self.reverse_codes_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(reverse_info_frame, text="Bind Reverse", 
                  command=lambda: self.start_binding('reverse')).pack(side=tk.RIGHT, padx=5)
        
        # Throttle axis binding (for single throttle mode)
        throttle_frame = ttk.LabelFrame(binding_frame, text="Throttle Axis (Single Mode)")
        throttle_frame.pack(fill=tk.X, padx=5, pady=5)
        
        throttle_info_frame = ttk.Frame(throttle_frame)
        throttle_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(throttle_info_frame, text="Current:").pack(side=tk.LEFT)
        self.throttle_codes_label = ttk.Label(throttle_info_frame, text=str(self.config.throttle_codes))
        self.throttle_codes_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(throttle_info_frame, text="Bind Throttle", 
                  command=lambda: self.start_binding('throttle')).pack(side=tk.RIGHT, padx=5)
        
        # Clear bindings
        clear_frame = ttk.Frame(binding_frame)
        clear_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(clear_frame, text="Reset All Bindings", 
                  command=self.reset_all_bindings).pack(side=tk.LEFT, padx=5)
        ttk.Button(clear_frame, text="Save Configuration", 
                  command=self.save_configuration).pack(side=tk.RIGHT, padx=5)
    
    def setup_acceleration_tab(self, notebook):
        """Set up the acceleration curve tab"""
        accel_frame = ttk.Frame(notebook)
        notebook.add(accel_frame, text="Acceleration")
        
        # Create main horizontal layout
        main_container = tk.Frame(accel_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Controls
        controls_frame = ttk.LabelFrame(main_container, text="Acceleration Settings")
        controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        controls_frame.config(width=300)
        
        # Curve type selection
        ttk.Label(controls_frame, text="Curve Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.curve_type_var = tk.StringVar(value=self.config.acceleration_curve)
        curve_combo = ttk.Combobox(controls_frame, textvariable=self.curve_type_var,
                                  values=["linear", "exponential", "quadratic", "s_curve"],
                                  state="readonly", width=15)
        curve_combo.grid(row=0, column=1, padx=5, pady=5)
        curve_combo.bind('<<ComboboxSelected>>', self.on_curve_change)
        
        # Curve strength
        ttk.Label(controls_frame, text="Curve Strength:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.strength_var = tk.DoubleVar(value=self.config.curve_strength)
        strength_scale = tk.Scale(controls_frame, from_=1.0, to=5.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.strength_var,
                                 command=self.on_strength_change, length=200)
        strength_scale.grid(row=1, column=1, padx=5, pady=5)
        
        # Ramp duration
        ttk.Label(controls_frame, text="Ramp Duration (s):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.duration_var = tk.DoubleVar(value=self.config.throttle_ramp_duration)
        duration_scale = tk.Scale(controls_frame, from_=0.5, to=3.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.duration_var,
                                 command=self.on_duration_change, length=200)
        duration_scale.grid(row=2, column=1, padx=5, pady=5)
        
        # Current values display
        self.curve_info_text = tk.Text(controls_frame, height=8, width=35, wrap=tk.WORD)
        self.curve_info_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # Test button
        test_button = ttk.Button(controls_frame, text="Test Current Curve",
                                command=self.test_acceleration_curve)
        test_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Right side - Graph
        graph_frame = ttk.LabelFrame(main_container, text="Acceleration Curve Visualization")
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure
        self.accel_fig = Figure(figsize=(6, 4), dpi=100)
        self.accel_plot = self.accel_fig.add_subplot(111)
        
        # Create canvas
        self.accel_canvas = FigureCanvasTkAgg(self.accel_fig, graph_frame)
        self.accel_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize the graph
        self.update_acceleration_graph()
        self.update_curve_info()
    
    def on_curve_change(self, event=None):
        """Handle curve type change"""
        self.config.acceleration_curve = self.curve_type_var.get()
        self.update_acceleration_graph()
        self.update_curve_info()
        self.config.save_config()
    
    def on_strength_change(self, value):
        """Handle curve strength change"""
        self.config.curve_strength = float(value)
        self.update_acceleration_graph()
        self.update_curve_info()
        self.config.save_config()
    
    def on_duration_change(self, value):
        """Handle duration change"""
        self.config.throttle_ramp_duration = float(value)
        self.update_curve_info()
        self.config.save_config()
    
    def apply_acceleration_curve(self, progress):
        """Apply acceleration curve to throttle progress (0.0 to 1.0)"""
        if progress <= 0:
            return 0.0
        if progress >= 1:
            return 1.0
        
        curve_type = self.config.acceleration_curve
        strength = self.config.curve_strength
        
        if curve_type == "linear":
            return progress
        
        elif curve_type == "exponential":
            # Exponential curve: starts slow, accelerates faster
            return progress ** strength
        
        elif curve_type == "quadratic":
            # Quadratic curve: gentle acceleration curve
            return progress ** 2
        
        elif curve_type == "s_curve":
            # S-curve: slow start, fast middle, slow end (like real car)
            import math
            # Use a sigmoid-like function
            x = (progress - 0.5) * strength * 2  # Scale and center around 0
            return 1 / (1 + math.exp(-x))
        
        else:
            # Default to linear if unknown curve type
            return progress
    
    def update_acceleration_graph(self):
        """Update the acceleration curve graph"""
        self.accel_plot.clear()
        
        # Generate time points (0 to 1 second)
        time_points = np.linspace(0, 1, 100)
        
        # Calculate throttle values for current settings
        throttle_values = []
        for t in time_points:
            throttle = self.apply_acceleration_curve(t)
            throttle_values.append(throttle * 100)  # Convert to percentage
        
        # Plot the curve
        self.accel_plot.plot(time_points, throttle_values, 'b-', linewidth=2, label=f'{self.config.acceleration_curve.title()} Curve')
        
        # Plot linear reference for comparison
        linear_values = [t * 100 for t in time_points]
        self.accel_plot.plot(time_points, linear_values, 'r--', alpha=0.5, label='Linear Reference')
        
        # Format the plot
        self.accel_plot.set_xlabel('Time (seconds)')
        self.accel_plot.set_ylabel('Throttle (%)')
        self.accel_plot.set_title('Acceleration Curve')
        self.accel_plot.grid(True, alpha=0.3)
        self.accel_plot.legend()
        self.accel_plot.set_xlim(0, 1)
        self.accel_plot.set_ylim(0, 100)
        
        # Refresh the canvas
        self.accel_canvas.draw()
    
    def update_curve_info(self):
        """Update the curve information text"""
        info = f"Current Settings:\n"
        info += f"Curve Type: {self.config.acceleration_curve.title()}\n"
        info += f"Strength: {self.config.curve_strength:.1f}\n"
        info += f"Duration: {self.config.throttle_ramp_duration:.1f}s\n\n"
        
        # Calculate some key points
        key_times = [0.25, 0.5, 0.75, 1.0]
        info += "Throttle at key times:\n"
        for t in key_times:
            throttle = self.apply_acceleration_curve(t) * 100
            info += f"  {t:.2f}s: {throttle:.1f}%\n"
        
        # Add curve description
        descriptions = {
            "linear": "Constant acceleration rate",
            "exponential": "Slow start, rapid acceleration",
            "quadratic": "Gentle progressive acceleration",
            "s_curve": "Car-like: slow-fast-gentle"
        }
        
        info += f"\n{descriptions.get(self.config.acceleration_curve, 'Unknown curve')}"
        
        self.curve_info_text.delete(1.0, tk.END)
        self.curve_info_text.insert(1.0, info)
    
    def test_acceleration_curve(self):
        """Test the current acceleration curve with a simulated button press"""
        messagebox.showinfo("Test Curve", 
                          "Press and hold a pedal button to see the current acceleration curve in action!\n\n"
                          "Watch the debug output in the terminal to see the progression from linear to curved values.")
    
    def setup_service_tab(self, notebook):
        """Set up the service control tab"""
        service_frame = ttk.Frame(notebook)
        notebook.add(service_frame, text="Service Control")
        
        # Service status frame
        status_frame = ttk.LabelFrame(service_frame, text="Service Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Status display
        status_info_frame = ttk.Frame(status_frame)
        status_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(status_info_frame, text="Headless Service:").pack(side=tk.LEFT)
        self.service_status_label = ttk.Label(status_info_frame, text="Checking...", foreground="orange")
        self.service_status_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(status_info_frame, text="Refresh Status", 
                  command=self.refresh_service_status).pack(side=tk.RIGHT, padx=5)
        
        # Service control buttons
        control_frame = ttk.LabelFrame(service_frame, text="Service Control")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Start Service", 
                  command=self.start_service).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop Service", 
                  command=self.stop_service).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Restart Service", 
                  command=self.restart_service).pack(side=tk.LEFT, padx=5)
        
        # Boot control
        boot_frame = ttk.Frame(control_frame)
        boot_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(boot_frame, text="Enable Auto-Start", 
                  command=self.enable_service).pack(side=tk.LEFT, padx=5)
        ttk.Button(boot_frame, text="Disable Auto-Start", 
                  command=self.disable_service).pack(side=tk.LEFT, padx=5)
        
        # Hardware test frame
        test_frame = ttk.LabelFrame(service_frame, text="Hardware Test")
        test_frame.pack(fill=tk.X, padx=5, pady=5)
        
        test_button_frame = ttk.Frame(test_frame)
        test_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(test_button_frame, text="Test I2C DACs", 
                  command=self.test_i2c).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_button_frame, text="Test T80 Wheel", 
                  command=self.test_wheel).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_button_frame, text="Full System Test", 
                  command=self.full_system_test).pack(side=tk.LEFT, padx=5)
        
        # Service logs frame
        logs_frame = ttk.LabelFrame(service_frame, text="Service Logs")
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log controls
        log_control_frame = ttk.Frame(logs_frame)
        log_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(log_control_frame, text="Refresh Logs", 
                  command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control_frame, text="Clear Display", 
                  command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(logs_frame, height=12, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initial status check
        self.refresh_service_status()
        self.refresh_logs()
    
    # Service control methods
    def run_system_command(self, command, show_output=True):
        """Run a system command and return the result"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            if show_output and result.stdout:
                self.update_log_display(f"Command: {command}\n{result.stdout}")
            if result.stderr:
                self.update_log_display(f"Error: {result.stderr}")
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out: {command}"
            if show_output:
                self.update_log_display(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Command failed: {command} - {e}"
            if show_output:
                self.update_log_display(error_msg)
            return False, "", str(e)
    
    def refresh_service_status(self):
        """Check and update the service status"""
        try:
            # Check if service is active
            success, stdout, stderr = self.run_system_command("systemctl is-active t80-headless.service", False)
            is_active = success and "active" in stdout.strip()
            
            # Check if service is enabled
            success, stdout, stderr = self.run_system_command("systemctl is-enabled t80-headless.service", False)
            is_enabled = success and "enabled" in stdout.strip()
            
            # Update status display
            if is_active and is_enabled:
                status_text = "Running (Auto-start enabled)"
                color = "green"
            elif is_active:
                status_text = "Running (Auto-start disabled)"
                color = "orange"
            elif is_enabled:
                status_text = "Stopped (Auto-start enabled)"
                color = "orange"
            else:
                status_text = "Stopped (Auto-start disabled)"
                color = "red"
            
            self.service_status_label.config(text=status_text, foreground=color)
            
        except Exception as e:
            self.service_status_label.config(text=f"Error: {e}", foreground="red")
    
    def start_service(self):
        """Start the headless service"""
        success, stdout, stderr = self.run_system_command("sudo systemctl start t80-headless.service")
        if success:
            messagebox.showinfo("Success", "Service started successfully")
        else:
            messagebox.showerror("Error", f"Failed to start service:\n{stderr}")
        self.refresh_service_status()
    
    def stop_service(self):
        """Stop the headless service"""
        success, stdout, stderr = self.run_system_command("sudo systemctl stop t80-headless.service")
        if success:
            messagebox.showinfo("Success", "Service stopped successfully")
        else:
            messagebox.showerror("Error", f"Failed to stop service:\n{stderr}")
        self.refresh_service_status()
    
    def restart_service(self):
        """Restart the headless service"""
        success, stdout, stderr = self.run_system_command("sudo systemctl restart t80-headless.service")
        if success:
            messagebox.showinfo("Success", "Service restarted successfully")
        else:
            messagebox.showerror("Error", f"Failed to restart service:\n{stderr}")
        self.refresh_service_status()
    
    def enable_service(self):
        """Enable the service to start on boot"""
        success, stdout, stderr = self.run_system_command("sudo systemctl enable t80-headless.service")
        if success:
            messagebox.showinfo("Success", "Service enabled for auto-start on boot")
        else:
            messagebox.showerror("Error", f"Failed to enable service:\n{stderr}")
        self.refresh_service_status()
    
    def disable_service(self):
        """Disable the service from starting on boot"""
        success, stdout, stderr = self.run_system_command("sudo systemctl disable t80-headless.service")
        if success:
            messagebox.showinfo("Success", "Service disabled from auto-start")
        else:
            messagebox.showerror("Error", f"Failed to disable service:\n{stderr}")
        self.refresh_service_status()
    
    def test_i2c(self):
        """Test I2C DAC connections"""
        self.update_log_display("\n=== Testing I2C DACs ===")
        success, stdout, stderr = self.run_system_command("sudo i2cdetect -y 1")
        
        # Check for specific addresses
        if "60" in stdout and "61" in stdout:
            self.update_log_display("✅ Both DACs detected at 0x60 and 0x61")
            messagebox.showinfo("I2C Test", "✅ Both DACs detected successfully!")
        else:
            self.update_log_display("❌ DACs not detected at expected addresses")
            messagebox.showwarning("I2C Test", "⚠️ DACs not detected at expected addresses 0x60 and 0x61")
    
    def test_wheel(self):
        """Test T80 wheel connection"""
        self.update_log_display("\n=== Testing T80 Wheel ===")
        success, stdout, stderr = self.run_system_command("ls -la /dev/input/by-id/ | grep Thrustmaster || echo 'No Thrustmaster devices found'")
        
        if "Thrustmaster" in stdout:
            self.update_log_display("✅ T80 wheel detected")
            messagebox.showinfo("Wheel Test", "✅ T80 wheel detected successfully!")
        else:
            self.update_log_display("❌ T80 wheel not detected")
            messagebox.showwarning("Wheel Test", "⚠️ T80 wheel not detected. Check USB connection.")
    
    def full_system_test(self):
        """Run a full system test"""
        self.update_log_display("\n=== Running Full System Test ===")
        script_path = os.path.join(os.path.dirname(__file__), "verify-setup.sh")
        if os.path.exists(script_path):
            success, stdout, stderr = self.run_system_command(f"bash {script_path}")
            if success:
                messagebox.showinfo("System Test", "✅ Full system test completed! Check logs for details.")
            else:
                messagebox.showerror("System Test", f"❌ System test failed:\n{stderr}")
        else:
            messagebox.showerror("System Test", "verify-setup.sh script not found")
    
    def refresh_logs(self):
        """Refresh the service logs display"""
        self.update_log_display("\n=== Service Logs ===")
        success, stdout, stderr = self.run_system_command("sudo journalctl -u t80-headless.service --no-pager -n 20", False)
        if success and stdout:
            self.update_log_display(stdout)
        elif stderr:
            self.update_log_display(f"Error getting logs: {stderr}")
    
    def clear_logs(self):
        """Clear the log display"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def update_log_display(self, text):
        """Update the log display with new text"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def connect_device(self):
        """Connect to the input device"""
        success, message = self.controller.connect_device()
        self.connection_status.config(text=message)
        if success:
            self.connection_status.config(foreground="green")
        else:
            self.connection_status.config(foreground="red")
    
    def disconnect_device(self):
        """Disconnect from the input device"""
        self.controller.disconnect_device()
        self.connection_status.config(text="Disconnected", foreground="red")
    
    def start_controller(self):
        """Start the input controller"""
        if self.controller.device:
            self.controller.start()
        else:
            messagebox.showwarning("Warning", "Please connect a device first")
    
    def stop_controller(self):
        """Stop the input controller"""
        self.controller.stop()
    
    def center_outputs(self):
        """Center the DAC outputs"""
        self.controller.center_outputs()
    
    def update_swap(self):
        """Update swap controls setting"""
        self.config.swap_controls = self.swap_var.get()
        self.controller.config = self.config
    
    def update_separate_pedals(self):
        """Update separate pedals setting"""
        self.config.use_separate_pedals = self.separate_pedals_var.get()
        self.controller.config = self.config
        # Rebuild input displays
        # For simplicity, just update the config and restart if needed
    
    def update_steering_trim(self, value=None):
        """Update steering trim setting"""
        trim_value = self.steering_trim_var.get()
        self.config.steering_trim = trim_value
        self.controller.config = self.config
        self.steering_trim_label.config(text=f"{trim_value:.2f}")
    
    def update_throttle_trim(self, value=None):
        """Update throttle trim setting"""
        trim_value = self.throttle_trim_var.get()
        self.config.throttle_trim = trim_value
        self.controller.config = self.config
        self.throttle_trim_label.config(text=f"{trim_value:.2f}")
    
    def reset_steering_trim(self):
        """Reset steering trim to center"""
        self.steering_trim_var.set(0.0)
        self.update_steering_trim()
    
    def reset_throttle_trim(self):
        """Reset throttle trim to center"""
        self.throttle_trim_var.set(0.0)
        self.update_throttle_trim()
    
    def start_binding(self, target):
        """Start binding mode for a specific input"""
        if not self.controller.device:
            messagebox.showwarning("Warning", "Please connect a device first")
            return
        
        self.binding_mode = True
        self.binding_target = target
        self.binding_status_label.config(
            text=f"Binding {target}... Press the control now!",
            foreground="orange"
        )
        self.cancel_binding_button.config(state=tk.NORMAL)
        
        # Store the callback to update the UI when binding is complete
        self.binding_callback = self.on_binding_complete
    
    def cancel_binding(self):
        """Cancel current binding operation"""
        self.binding_mode = False
        self.binding_target = None
        self.binding_callback = None
        self.binding_status_label.config(
            text="Binding cancelled",
            foreground="red"
        )
        self.cancel_binding_button.config(state=tk.DISABLED)
        
        # Reset to ready state after 2 seconds
        self.root.after(2000, lambda: self.binding_status_label.config(
            text="Ready to bind inputs", foreground="green"))
    
    def on_binding_complete(self, target, code, event_type):
        """Called when a binding is successfully captured"""
        self.binding_mode = False
        self.binding_target = None
        self.binding_callback = None
        self.cancel_binding_button.config(state=tk.DISABLED)
        
        # Update the configuration
        if target == 'steering':
            self.config.steering_codes = [code]
            self.steering_codes_label.config(text=str([code]))
        elif target == 'forward':
            self.config.forward_pedal_codes = [code]
            self.forward_codes_label.config(text=str([code]))
        elif target == 'reverse':
            self.config.reverse_pedal_codes = [code]
            self.reverse_codes_label.config(text=str([code]))
        elif target == 'throttle':
            self.config.throttle_codes = [code]
            self.throttle_codes_label.config(text=str([code]))
        
        # Update the controller's config
        self.controller.config = self.config
        
        # Show success message
        event_name = ecodes.KEY.get(code) if event_type == ecodes.EV_KEY else ecodes.ABS.get(code, f"Unknown_{code}")
        self.binding_status_label.config(
            text=f"Successfully bound {target} to {event_name} (code {code})",
            foreground="green"
        )
        
        # Reset status after 3 seconds
        self.root.after(3000, lambda: self.binding_status_label.config(
            text="Ready to bind inputs", foreground="green"))
    
    def reset_all_bindings(self):
        """Reset all bindings to defaults"""
        if messagebox.askyesno("Confirm", "Reset all input bindings to defaults?"):
            # Reset to default codes
            self.config.steering_codes = [ecodes.ABS_X, ecodes.ABS_RX]
            self.config.forward_pedal_codes = [ecodes.BTN_TR, ecodes.BTN_TRIGGER]
            self.config.reverse_pedal_codes = [ecodes.BTN_TL, ecodes.BTN_THUMB]
            self.config.throttle_codes = [ecodes.ABS_Y, ecodes.ABS_RY]
            
            # Update labels
            self.steering_codes_label.config(text=str(self.config.steering_codes))
            self.forward_codes_label.config(text=str(self.config.forward_pedal_codes))
            self.reverse_codes_label.config(text=str(self.config.reverse_pedal_codes))
            self.throttle_codes_label.config(text=str(self.config.throttle_codes))
            
            # Update controller config
            self.controller.config = self.config
            
            self.binding_status_label.config(
                text="All bindings reset to defaults",
                foreground="blue"
            )
    
    def save_configuration(self):
        """Save current configuration"""
        try:
            # Update config from GUI values
            self.config.i2c_bus = self.i2c_bus_var.get()
            self.config.steering_addr = int(self.steering_addr_var.get(), 16)
            self.config.throttle_addr = int(self.throttle_addr_var.get(), 16)
            self.config.update_hz = self.update_hz_var.get()
            self.config.deadzone = self.deadzone_var.get()
            self.config.expo = self.expo_var.get()
            self.config.invert_steering = self.invert_steering_var.get()
            self.config.invert_throttle = self.invert_throttle_var.get()
            self.config.pedal_mode = self.pedal_mode_var.get()
            self.config.steering_trim = self.steering_trim_config_var.get()
            self.config.throttle_trim = self.throttle_trim_config_var.get()
            self.config.analog_pedal_feel = self.analog_pedal_feel_var.get()
            self.config.throttle_ramp_speed = self.throttle_ramp_speed_var.get()
            
            # Update the controller's ramping speed
            self.controller.throttle_ramp_speed = self.config.throttle_ramp_speed
            
            self.config.save_config()
            self.controller.config = self.config
            messagebox.showinfo("Success", "Configuration saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def load_configuration(self):
        """Load configuration from file"""
        try:
            self.config.load_config()
            self.controller.config = self.config
            
            # Update GUI values
            self.i2c_bus_var.set(self.config.i2c_bus)
            self.steering_addr_var.set(f"0x{self.config.steering_addr:02x}")
            self.throttle_addr_var.set(f"0x{self.config.throttle_addr:02x}")
            self.update_hz_var.set(self.config.update_hz)
            self.deadzone_var.set(self.config.deadzone)
            self.expo_var.set(self.config.expo)
            self.invert_steering_var.set(self.config.invert_steering)
            self.invert_throttle_var.set(self.config.invert_throttle)
            self.swap_var.set(self.config.swap_controls)
            self.separate_pedals_var.set(self.config.use_separate_pedals)
            self.pedal_mode_var.set(self.config.pedal_mode)
            
            # Update trim controls
            self.steering_trim_var.set(self.config.steering_trim)
            self.throttle_trim_var.set(self.config.throttle_trim)
            self.steering_trim_config_var.set(self.config.steering_trim)
            self.throttle_trim_config_var.set(self.config.throttle_trim)
            
            # Update analog pedal controls
            self.analog_pedal_feel_var.set(self.config.analog_pedal_feel)
            self.throttle_ramp_speed_var.set(self.config.throttle_ramp_speed)
            
            # Update trim labels
            self.update_steering_trim()
            self.update_throttle_trim()
            
            messagebox.showinfo("Success", "Configuration loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")
    
    def reset_configuration(self):
        """Reset configuration to defaults"""
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            # Remove config file and reload
            try:
                os.remove(self.config.config_file)
            except:
                pass
            self.load_configuration()
    
    def reset_calibration(self):
        """Reset calibration values"""
        if messagebox.askyesno("Confirm", "Reset all calibration values?"):
            self.controller.ax_min = {'steering': 32767, 'throttle': 32767, 
                                    'forward': 32767, 'reverse': 32767}
            self.controller.ax_max = {'steering': -32768, 'throttle': -32768, 
                                    'forward': -32768, 'reverse': -32768}
    
    def update_gui(self):
        """Update GUI with current values"""
        try:
            # Update raw value displays
            steering_val = self.controller.ax_val['steering']
            self.steering_raw_label.config(text=str(steering_val))
            
            # Update progress bars (convert to 0-100 range)
            if self.controller.ax_max['steering'] > self.controller.ax_min['steering']:
                steering_percent = ((steering_val - self.controller.ax_min['steering']) / 
                                  (self.controller.ax_max['steering'] - self.controller.ax_min['steering'])) * 100
                self.steering_progress['value'] = max(0, min(100, steering_percent))
            
            # Update pedal displays based on mode
            if self.config.use_separate_pedals:
                if self.config.pedal_mode == "buttons":
                    # Update button states
                    forward_pressed = self.controller.button_states['forward_pedal']
                    reverse_pressed = self.controller.button_states['reverse_pedal']
                    
                    self.forward_button_label.config(
                        text="PRESSED" if forward_pressed else "RELEASED",
                        foreground="green" if forward_pressed else "red"
                    )
                    self.reverse_button_label.config(
                        text="PRESSED" if reverse_pressed else "RELEASED", 
                        foreground="green" if reverse_pressed else "red"
                    )
                    
                elif self.config.pedal_mode == "split_axis":
                    # Update combined axis
                    combined_val = self.controller.ax_val['combined_axis']
                    self.combined_raw_label.config(text=str(combined_val))
                    if self.controller.ax_max['combined_axis'] > self.controller.ax_min['combined_axis']:
                        combined_percent = ((combined_val - self.controller.ax_min['combined_axis']) / 
                                          (self.controller.ax_max['combined_axis'] - self.controller.ax_min['combined_axis'])) * 100
                        self.combined_progress['value'] = max(0, min(100, combined_percent))
                        
                else:
                    # Separate analog axes (original mode)
                    forward_val = self.controller.ax_val.get('forward', 0)
                    reverse_val = self.controller.ax_val.get('reverse', 0)
                    
                    if hasattr(self, 'forward_raw_label'):
                        self.forward_raw_label.config(text=str(forward_val))
                        if self.controller.ax_max.get('forward', -32768) > self.controller.ax_min.get('forward', 32767):
                            forward_percent = ((forward_val - self.controller.ax_min['forward']) / 
                                             (self.controller.ax_max['forward'] - self.controller.ax_min['forward'])) * 100
                            self.forward_progress['value'] = max(0, min(100, forward_percent))
                    
                    if hasattr(self, 'reverse_raw_label'):
                        self.reverse_raw_label.config(text=str(reverse_val))
                        if self.controller.ax_max.get('reverse', -32768) > self.controller.ax_min.get('reverse', 32767):
                            reverse_percent = ((reverse_val - self.controller.ax_min['reverse']) / 
                                             (self.controller.ax_max['reverse'] - self.controller.ax_min['reverse'])) * 100
                            self.reverse_progress['value'] = max(0, min(100, reverse_percent))
            else:
                # Single throttle
                if hasattr(self, 'throttle_raw_label'):
                    throttle_val = self.controller.ax_val['throttle']
                    self.throttle_raw_label.config(text=str(throttle_val))
                    if self.controller.ax_max['throttle'] > self.controller.ax_min['throttle']:
                        throttle_percent = ((throttle_val - self.controller.ax_min['throttle']) / 
                                          (self.controller.ax_max['throttle'] - self.controller.ax_min['throttle'])) * 100
                        self.throttle_progress['value'] = max(0, min(100, throttle_percent))
            
            # Update processed value displays
            steering_proc = self.controller.processed_values['steering']
            throttle_proc = self.controller.processed_values['throttle']
            
            # Show trim effect in processed values
            steering_before_trim = steering_proc - self.config.steering_trim
            throttle_before_trim = throttle_proc - self.config.throttle_trim
            
            self.steering_proc_label.config(text=f"{steering_proc:.2f}" + 
                                          (f" (+{self.config.steering_trim:.2f})" if self.config.steering_trim != 0 else ""))
            self.throttle_proc_label.config(text=f"{throttle_proc:.2f}" + 
                                          (f" (+{self.config.throttle_trim:.2f})" if self.config.throttle_trim != 0 else ""))
            
            # Convert to progress bar values (-1 to 1 -> 0 to 100)
            self.steering_proc_progress['value'] = (steering_proc + 1) * 50
            self.throttle_proc_progress['value'] = (throttle_proc + 1) * 50
            
            # Update calibration display
            self.update_calibration_display()
            
        except Exception as e:
            print(f"GUI update error: {e}")
        
        # Schedule next update
        self.root.after(50, self.update_gui)  # 20 FPS update rate
    
    def update_calibration_display(self):
        """Update the calibration values display"""
        try:
            cal_info = "Current Calibration Values:\n\n"
            
            for axis in ['steering', 'throttle', 'forward', 'reverse']:
                if axis in self.controller.ax_min:
                    cal_info += f"{axis.capitalize()}:\n"
                    cal_info += f"  Current: {self.controller.ax_val[axis]}\n"
                    cal_info += f"  Min: {self.controller.ax_min[axis]}\n"
                    cal_info += f"  Max: {self.controller.ax_max[axis]}\n"
                    cal_info += f"  Range: {self.controller.ax_max[axis] - self.controller.ax_min[axis]}\n\n"
            
            self.cal_text.config(state=tk.NORMAL)
            self.cal_text.delete('1.0', tk.END)
            self.cal_text.insert('1.0', cal_info)
            self.cal_text.config(state=tk.DISABLED)
        except:
            pass
    
    def on_closing(self):
        """Handle window closing"""
        self.controller.stop()
        self.controller.center_outputs()
        self.controller.disconnect_device()
        self.config.save_config()
        self.root.destroy()
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = T80GUI()
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
