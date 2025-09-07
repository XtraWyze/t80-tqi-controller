#!/usr/bin/env python3
"""
Test script to demonstrate the new forward/reverse throttle behavior.
Forward: Curved acceleration over time
Reverse: Immediate full response
"""

import time

def apply_acceleration_curve(progress, curve_type="exponential", strength=2.1):
    """Apply acceleration curve to throttle progress (0.0 to 1.0)"""
    if progress <= 0:
        return 0.0
    if progress >= 1:
        return 1.0
    
    if curve_type == "linear":
        return progress
    elif curve_type == "exponential":
        return progress ** strength
    elif curve_type == "quadratic":
        return progress ** 2
    elif curve_type == "s_curve":
        import math
        x = (progress - 0.5) * strength * 2
        return 1 / (1 + math.exp(-x))
    else:
        return progress

def test_forward_reverse_behavior():
    """Test and display the difference between forward and reverse throttle"""
    
    print("=== Forward vs Reverse Throttle Behavior ===")
    print("Forward: Gradual acceleration with curve")
    print("Reverse: Immediate full response for safety\n")
    
    # Test forward throttle progression
    print("🚗 FORWARD THROTTLE (Exponential Curve, Strength 2.1):")
    print("Time    Linear    Curved    Description")
    print("-" * 45)
    
    test_times = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    
    for t in test_times:
        linear = t * 100
        curved = apply_acceleration_curve(t, "exponential", 2.1) * 100
        
        if t == 0.0:
            desc = "Button pressed"
        elif t <= 0.3:
            desc = "Slow start"
        elif t <= 0.7:
            desc = "Building power"
        elif t < 1.0:
            desc = "Rapid acceleration"
        else:
            desc = "Full throttle"
            
        print(f"{t:4.1f}s   {linear:5.1f}%    {curved:5.1f}%    {desc}")
    
    print("\n🛑 REVERSE THROTTLE:")
    print("Time    Throttle  Description")
    print("-" * 30)
    print("0.0s    100%      Immediate full reverse")
    print("                  (No curve for safety)")
    
    print("\n=== Key Benefits ===")
    print("✅ Forward: Realistic car-like acceleration")
    print("✅ Reverse: Instant response for emergency stops")
    print("✅ Safety: No delay when you need to reverse quickly")
    print("✅ Realism: Natural throttle progression for normal driving")
    
    print("\n=== Real-time Demo ===")
    print("Simulating forward acceleration...")
    
    start_time = time.time()
    duration = 1.0
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        
        if elapsed >= duration:
            break
        
        progress = elapsed / duration
        curved_throttle = apply_acceleration_curve(progress, "exponential", 2.1)
        linear_throttle = progress
        
        # Create progress bars
        bar_length = 15
        curved_filled = int(bar_length * curved_throttle)
        linear_filled = int(bar_length * linear_throttle)
        
        curved_bar = "█" * curved_filled + "░" * (bar_length - curved_filled)
        linear_bar = "█" * linear_filled + "░" * (bar_length - linear_filled)
        
        print(f"\rTime: {elapsed:.2f}s | Linear: [{linear_bar}] {linear_throttle*100:5.1f}% | Curved: [{curved_bar}] {curved_throttle*100:5.1f}%", end="", flush=True)
        time.sleep(0.05)
    
    print(f"\nForward complete! Reverse would be instant 100% 🛑")

if __name__ == "__main__":
    test_forward_reverse_behavior()
