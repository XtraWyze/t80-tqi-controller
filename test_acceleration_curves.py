#!/usr/bin/env python3
"""
Test script to visualize different acceleration curves.
Shows how throttle progression changes with different curve types.
"""

import math
import time

def apply_acceleration_curve(progress, curve_type="exponential", strength=2.0):
    """Apply acceleration curve to throttle progress (0.0 to 1.0)"""
    if progress <= 0:
        return 0.0
    if progress >= 1:
        return 1.0
    
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
        # Use a sigmoid-like function
        x = (progress - 0.5) * strength * 2  # Scale and center around 0
        return 1 / (1 + math.exp(-x))
    
    else:
        # Default to linear if unknown curve type
        return progress

def test_curves():
    """Test and display different acceleration curves"""
    
    print("=== Acceleration Curve Comparison ===")
    print("Time progression from 0% to 100% over 1 second\n")
    
    # Test different curves
    curves = [
        ("linear", 1.0),
        ("exponential", 2.0),
        ("quadratic", 1.0),
        ("s_curve", 4.0)
    ]
    
    test_times = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    
    # Print header
    print(f"{'Time':<6}", end="")
    for curve_name, _ in curves:
        print(f"{curve_name.capitalize():<12}", end="")
    print()
    print("-" * 60)
    
    # Print progression for each time point
    for t in test_times:
        print(f"{t:<6.1f}", end="")
        for curve_name, strength in curves:
            throttle = apply_acceleration_curve(t, curve_name, strength)
            print(f"{throttle*100:8.1f}%   ", end="")
        print()
    
    print("\n=== Curve Characteristics ===")
    print("Linear:      Constant acceleration rate")
    print("Exponential: Slow start, rapid acceleration (feels sporty)")
    print("Quadratic:   Gentle progressive acceleration")
    print("S-curve:     Real car feel - slow start, fast middle, gentle end")
    
    print("\n=== Real-time Demo ===")
    print("Simulating 1-second button hold with exponential curve...")
    
    start_time = time.time()
    duration = 1.0
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        
        if elapsed >= duration:
            break
        
        progress = elapsed / duration
        throttle = apply_acceleration_curve(progress, "exponential", 2.0)
        
        # Create progress bar
        bar_length = 20
        filled_length = int(bar_length * throttle)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        print(f"\rTime: {elapsed:.2f}s [{bar}] {throttle*100:5.1f}%", end="", flush=True)
        time.sleep(0.05)  # 20Hz update rate
    
    print(f"\rTime: {duration:.2f}s [{'█'*20}] 100.0%")
    print("\nDemo complete!")

if __name__ == "__main__":
    test_curves()
