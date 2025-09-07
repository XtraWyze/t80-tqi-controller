# Duration-Based Throttle System - Implementation Summary

## Overview
The T80 Racing Wheel controller now uses a duration-based throttle system that provides realistic car-like acceleration behavior. This replaces the previous complex ramping system with a simpler, more intuitive approach.

## How It Works

### Key Behavior
- **Button Held**: Throttle gradually increases from 0% to 100% over exactly 1 second
- **Button Released**: Throttle instantly drops to 0% (simulates lifting off the gas pedal)
- **Both Buttons Pressed**: Safety feature - instant zero throttle

### Technical Implementation
```python
# When button is pressed, start timing
if button_pressed and not other_button:
    if button_press_start_time is None:
        button_press_start_time = current_time
    
    # Calculate throttle based on how long button has been held
    press_duration = current_time - button_press_start_time
    throttle = min(1.0, press_duration / 1.0)  # 1 second to full throttle

# When button is released, instant zero
else:
    throttle = 0.0
    button_press_start_time = None
```

## Throttle Progression Timeline
```
Time:     0.00s  0.25s  0.50s  0.75s  1.00s  1.50s
Forward:   0%    25%    50%    75%   100%   100%
Reverse:   0%   -25%   -50%   -75%  -100%  -100%
Released:  0% (instant)
```

## Files Updated

### t80_gui.py
- Added duration-based throttle logic in analog pedal processing
- Button press timing tracks when each pedal button is first pressed
- Throttle calculation: `min(1.0, press_duration / 1.0_second)`

### t80_to_tqi.py (Headless Version)
- Matching duration-based throttle implementation
- Same timing logic for consistent behavior
- Removed old ramping variables (`THROTTLE_RAMP_SPEED`, `current_throttle`, etc.)

### t80_config.json
- Updated configuration to reflect new system
- Replaced `throttle_ramp_speed` and `brake_ramp_speed` with `throttle_ramp_duration`
- Simplified to single 1-second duration parameter

## Testing

### Validation Script
Created `test_duration_throttle.py` to verify the timing calculations work correctly:
- Tests throttle progression from 0% to 100% over 1 second
- Validates both forward and reverse directions
- Confirms instant zero behavior on release

### Service Integration
- Headless service (`t80-headless.service`) restarted with new logic
- Auto-start on boot functionality maintained
- No errors in system logs - smooth operation confirmed

## Benefits

### User Experience
1. **Intuitive Control**: Button hold time directly correlates to throttle output
2. **Realistic Feel**: Mimics real car acceleration behavior
3. **Safety**: Instant release for emergency stopping
4. **Consistent**: Both GUI and headless versions behave identically

### Technical Advantages
1. **Simplified Code**: Removed complex ramping algorithms
2. **Predictable Behavior**: Linear progression over fixed time period
3. **Responsive**: Instant zero on release for precise control
4. **Maintainable**: Easier to understand and modify

## Configuration

The system is configured via `t80_config.json`:
```json
{
  "analog_pedal_feel": true,
  "throttle_ramp_duration": 1.0
}
```

- `analog_pedal_feel`: Enable/disable duration-based throttle
- `throttle_ramp_duration`: Time in seconds to reach full throttle (default: 1.0)

## Usage

### With GUI
- Start `t80_gui.py` for interactive control and testing
- Service Control tab allows managing the headless auto-start service
- Real-time throttle visualization shows duration-based progression

### Headless Auto-Start
- System automatically starts on boot via `t80-headless.service`
- No screen required - plug and play operation
- Duration-based throttle active immediately

The implementation provides the exact behavior requested: throttle only active while button is physically held down, gradually increasing over 1 second, with instant zero on release.
