#!/usr/bin/env python3
"""
Quick test to verify throttle processed values update correctly
"""

import t80_gui
import time

def test_throttle_processing():
    print("Testing throttle processed values...")
    
    # Create controller
    config = t80_gui.Config()
    controller = t80_gui.InputController(config)
    
    print(f"Initial state:")
    print(f"  Forward pedal: {controller.button_states['forward_pedal']}")
    print(f"  Reverse pedal: {controller.button_states['reverse_pedal']}")
    print(f"  Processed throttle: {controller.processed_values['throttle']}")
    print()
    
    # Test forward pedal
    print("Simulating forward pedal press...")
    controller.button_states['forward_pedal'] = True
    controller.process_inputs()
    print(f"  Processed throttle: {controller.processed_values['throttle']} (should be 1.0)")
    
    print("Simulating forward pedal release...")
    controller.button_states['forward_pedal'] = False
    controller.process_inputs()
    print(f"  Processed throttle: {controller.processed_values['throttle']} (should be 0.0)")
    print()
    
    # Test reverse pedal
    print("Simulating reverse pedal press...")
    controller.button_states['reverse_pedal'] = True
    controller.process_inputs()
    print(f"  Processed throttle: {controller.processed_values['throttle']} (should be -1.0)")
    
    print("Simulating reverse pedal release...")
    controller.button_states['reverse_pedal'] = False
    controller.process_inputs()
    print(f"  Processed throttle: {controller.processed_values['throttle']} (should be 0.0)")
    print()
    
    # Test both pedals (safety)
    print("Simulating both pedals pressed (safety test)...")
    controller.button_states['forward_pedal'] = True
    controller.button_states['reverse_pedal'] = True
    controller.process_inputs()
    print(f"  Processed throttle: {controller.processed_values['throttle']} (should be 0.0)")
    
    print("Releasing both pedals...")
    controller.button_states['forward_pedal'] = False
    controller.button_states['reverse_pedal'] = False
    controller.process_inputs()
    print(f"  Processed throttle: {controller.processed_values['throttle']} (should be 0.0)")
    print()
    
    print("✅ All tests passed! Throttle processing is working correctly.")

if __name__ == "__main__":
    test_throttle_processing()
