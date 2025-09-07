#!/usr/bin/env python3
"""
Quick test script to verify duration-based throttle logic.
This simulates the button press behavior to test the timing calculations.
"""

import time

def test_duration_throttle():
    """Test the duration-based throttle calculation"""
    
    # Simulate the duration-based throttle logic
    button_press_start_time = {'forward': None, 'reverse': None}
    throttle_ramp_duration = 1.0  # 1 second to reach full throttle
    
    print("Testing duration-based throttle logic:")
    print("- Button held = gradual increase over 1 second")
    print("- Button released = instant zero")
    print()
    
    # Test Case 1: Forward button held for various durations
    print("=== Forward Button Test ===")
    test_times = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]  # seconds
    
    for test_time in test_times:
        # Simulate button press at time 0
        button_press_start_time['forward'] = 0.0
        current_time = test_time
        
        # Calculate throttle based on duration
        press_duration = current_time - button_press_start_time['forward']
        throttle = min(1.0, press_duration / throttle_ramp_duration)
        
        print(f"Time {test_time:4.2f}s: throttle = {throttle:5.3f} ({throttle*100:5.1f}%)")
    
    print()
    print("=== Button Release Test ===")
    print("Button released: throttle = 0.000 (instant)")
    
    print()
    print("=== Reverse Button Test ===")
    for test_time in test_times:
        # Simulate reverse button press
        button_press_start_time['reverse'] = 0.0
        current_time = test_time
        
        # Calculate reverse throttle
        press_duration = current_time - button_press_start_time['reverse']
        throttle = -min(1.0, press_duration / throttle_ramp_duration)
        
        print(f"Time {test_time:4.2f}s: throttle = {throttle:6.3f} ({throttle*100:5.1f}%)")

if __name__ == "__main__":
    test_duration_throttle()
