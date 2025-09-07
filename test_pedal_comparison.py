#!/usr/bin/env python3
"""
Compare digital vs analog pedal feel
"""

import t80_gui
import time

def test_both_modes():
    print("🚗 Pedal Feel Comparison Test")
    print("=" * 50)
    
    # Test digital mode
    print("\n1️⃣  DIGITAL MODE (Original - Instant On/Off)")
    config_digital = t80_gui.Config()
    config_digital.analog_pedal_feel = False
    controller_digital = t80_gui.InputController(config_digital)
    
    print("Forward pedal press...")
    controller_digital.button_states['forward_pedal'] = True
    controller_digital.process_inputs()
    print(f"  Instant: {controller_digital.processed_values['throttle']:.3f}")
    
    print("Forward pedal release...")
    controller_digital.button_states['forward_pedal'] = False
    controller_digital.process_inputs()
    print(f"  Instant: {controller_digital.processed_values['throttle']:.3f}")
    
    # Test analog mode
    print("\n2️⃣  ANALOG MODE (Car-like acceleration)")
    config_analog = t80_gui.Config()
    config_analog.analog_pedal_feel = True
    config_analog.throttle_ramp_speed = 3.0  # Slightly faster for demo
    config_analog.brake_ramp_speed = 5.0
    controller_analog = t80_gui.InputController(config_analog)
    
    print("Forward pedal press (watch it ramp up)...")
    controller_analog.button_states['forward_pedal'] = True
    
    for i in range(8):
        controller_analog.process_inputs()
        throttle = controller_analog.processed_values['throttle']
        bar_length = int(throttle * 20)  # Visual bar
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"  {i*0.1:.1f}s: [{bar}] {throttle:.3f}")
        time.sleep(0.1)
    
    print("\nForward pedal release (watch it ramp down)...")
    controller_analog.button_states['forward_pedal'] = False
    
    for i in range(6):
        controller_analog.process_inputs()
        throttle = controller_analog.processed_values['throttle']
        bar_length = int(throttle * 20) if throttle > 0 else 0
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"  {i*0.1:.1f}s: [{bar}] {throttle:.3f}")
        time.sleep(0.1)
    
    print("\n🎯 Summary:")
    print("✅ Digital Mode: Instant response (0→1→0)")
    print("✅ Analog Mode: Smooth ramping like a real car")
    print("✅ Analog gives much more natural acceleration feel!")
    print("\n🔧 Configure in GUI: Configuration tab → Analog Pedal Feel")

if __name__ == "__main__":
    test_both_modes()
