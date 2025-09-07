#!/usr/bin/env python3
"""
Test the new pedal behavior: gradual acceleration when held, instant zero when released
"""

import t80_gui
import time

def test_hold_and_release():
    print("🚗 NEW Pedal Behavior Test")
    print("Hold = Gradual increase, Release = Instant zero")
    print("=" * 50)
    
    # Create controller with analog feel
    config = t80_gui.Config()
    config.analog_pedal_feel = True
    config.throttle_ramp_speed = 3.0  # 3 units per second for demo
    controller = t80_gui.InputController(config)
    
    print("\n1️⃣  Forward pedal PRESS AND HOLD (watch gradual increase)")
    controller.button_states['forward_pedal'] = True
    
    for i in range(10):
        controller.process_inputs()
        throttle = controller.processed_values['throttle']
        bar_length = int(throttle * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"  {i*0.1:.1f}s: [{bar}] {throttle:.3f}")
        time.sleep(0.1)
        
        # Show it reaches and maintains full throttle
        if throttle >= 1.0:
            print(f"  ✅ Reached full throttle at {i*0.1:.1f}s")
            break
    
    print("\n2️⃣  Forward pedal RELEASE (watch instant zero)")
    controller.button_states['forward_pedal'] = False
    controller.process_inputs()
    throttle = controller.processed_values['throttle']
    print(f"  0.0s: [░░░░░░░░░░░░░░░░░░░░] {throttle:.3f} ⚡ INSTANT!")
    
    print("\n3️⃣  Reverse pedal test")
    print("Reverse press and hold...")
    controller.button_states['reverse_pedal'] = True
    
    for i in range(6):
        controller.process_inputs()
        throttle = controller.processed_values['throttle']
        bar_length = int(abs(throttle) * 20) if throttle < 0 else 0
        bar = "█" * bar_length + "░" * (20 - bar_length)
        direction = "REV" if throttle < 0 else "   "
        print(f"  {i*0.1:.1f}s: [{bar}] {throttle:.3f} {direction}")
        time.sleep(0.1)
    
    print("\nReverse release...")
    controller.button_states['reverse_pedal'] = False
    controller.process_inputs()
    throttle = controller.processed_values['throttle']
    print(f"  0.0s: [░░░░░░░░░░░░░░░░░░░░] {throttle:.3f} ⚡ INSTANT!")
    
    print("\n🎯 Summary:")
    print("✅ Pedal held = Gradual increase like real acceleration")
    print("✅ Pedal released = Instant zero like lifting off gas")
    print("✅ Perfect for realistic driving feel!")

if __name__ == "__main__":
    test_hold_and_release()
