#!/usr/bin/env python3
"""
Test the analog pedal feel ramping
"""

import t80_gui
import time

def test_analog_ramping():
    print("Testing analog pedal ramping...")
    
    # Create controller with analog feel enabled
    config = t80_gui.Config()
    config.analog_pedal_feel = True
    config.throttle_ramp_speed = 2.5  # 2.5 units per second
    config.brake_ramp_speed = 4.0     # 4.0 units per second
    
    controller = t80_gui.InputController(config)
    
    print(f"Analog pedal feel: {config.analog_pedal_feel}")
    print(f"Acceleration speed: {config.throttle_ramp_speed} units/sec")
    print(f"Brake speed: {config.brake_ramp_speed} units/sec")
    print()
    
    print("Test 1: Forward pedal press and hold")
    controller.button_states['forward_pedal'] = True
    
    for i in range(10):
        controller.process_inputs()
        throttle = controller.processed_values['throttle']
        print(f"  {i*0.1:.1f}s: Throttle = {throttle:.3f}")
        time.sleep(0.1)
    
    print("\nTest 2: Forward pedal release")
    controller.button_states['forward_pedal'] = False
    
    for i in range(8):
        controller.process_inputs()
        throttle = controller.processed_values['throttle']
        print(f"  {i*0.1:.1f}s: Throttle = {throttle:.3f}")
        time.sleep(0.1)
    
    print("\nTest 3: Reverse pedal press")
    controller.button_states['reverse_pedal'] = True
    
    for i in range(6):
        controller.process_inputs()
        throttle = controller.processed_values['throttle']
        print(f"  {i*0.1:.1f}s: Throttle = {throttle:.3f}")
        time.sleep(0.1)
    
    print("\n✅ Analog ramping test completed!")
    print("Notice how throttle gradually increases/decreases like a real car!")

if __name__ == "__main__":
    test_analog_ramping()
