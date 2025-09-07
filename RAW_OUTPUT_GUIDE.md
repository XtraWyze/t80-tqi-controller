# Xbox Raw Output Mode

## Overview

The Xbox Raw Output Mode provides maximum responsiveness and precision for Xbox controllers by bypassing signal processing that can introduce latency or reduce smoothness.

## What Raw Output Mode Does

### **Normal Mode (Default)**
- **Deadzone Applied**: Small input movements are filtered out
- **Exponential Response**: Input curves can be applied for different feels
- **Smoothing Filters**: Multiple samples are averaged for stable output
- **Acceleration Curves**: Non-linear throttle response curves

### **Raw Output Mode**
- **No Deadzone**: Every micro-movement is transmitted
- **Linear Response**: Direct 1:1 input-to-output mapping
- **No Smoothing**: Instant response without averaging
- **No Processing Delay**: Minimal input lag

## When to Use Raw Output Mode

### ✅ **Recommended For:**
- **Precision Racing**: When you need exact throttle control
- **Professional Gaming**: Competitive scenarios requiring instant response
- **Flight Simulation**: Precise aircraft control inputs
- **Fine Control Work**: Applications requiring micro-adjustments

### ⚠️ **Consider Normal Mode For:**
- **Casual Gaming**: When smoothness is preferred over precision
- **Noisy Environments**: If electrical interference affects controllers
- **Older Controllers**: Controllers with worn analog components
- **Beginner Users**: Those who prefer more forgiving input curves

## Configuration

### Via GUI
1. Open **Configuration** tab
2. Find **Xbox Controller Settings** section
3. Check ✅ **"Raw output mode (no deadzone/smoothing for maximum responsiveness)"**
4. Click **Save Configuration**

### Via JSON Config
Edit `t80_config.json`:
```json
{
  "xbox_raw_output": true,
  "xbox_use_triggers": true,
  "deadzone": 0.0,
  "expo": 0.0
}
```

## Technical Details

### Input Processing Pipeline

#### Normal Mode
```
Controller Input → Deadzone → Expo Curve → Smoothing Filter → DAC Output
     Raw         Filtered    Shaped       Averaged        Final
```

#### Raw Output Mode
```
Controller Input → DAC Output
     Raw            Final
```

### Performance Characteristics

| Aspect | Normal Mode | Raw Output Mode |
|--------|-------------|-----------------|
| **Input Lag** | ~3-5ms | ~1ms |
| **Precision** | Good | Excellent |
| **Smoothness** | Very Good | Variable |
| **Responsiveness** | Good | Excellent |
| **Noise Rejection** | Excellent | None |

### Trigger Mapping

Xbox controller triggers are mapped as follows in raw mode:

- **Right Trigger (RT)**: Forward/Throttle (0-255 range)
- **Left Trigger (LT)**: Reverse/Brake (0-255 range)
- **Combined Output**: `throttle_value = (RT_value - LT_value) / 255`

## Troubleshooting

### Issue: Jittery Output
**Cause**: Controller noise or worn components
**Solutions**:
- Disable raw output mode
- Increase deadzone setting
- Consider controller replacement

### Issue: Still Not Responsive Enough
**Cause**: Other system settings interfering
**Solutions**:
- Set `"deadzone": 0.0` in config
- Set `"expo": 0.0` in config  
- Set `"acceleration_curve": "linear"`
- Ensure `"analog_pedal_feel": false`

### Issue: Output Too Sensitive
**Cause**: Raw mode may be too direct for some applications
**Solutions**:
- Disable raw output mode
- Increase deadzone slightly (0.02-0.05)
- Use exponential curves for smoother feel

## Compatibility

### Xbox Controllers
- ✅ **Xbox Series X|S Controllers** (Best performance)
- ✅ **Xbox One Controllers** (Excellent)
- ✅ **Xbox 360 Controllers** (Good, via USB)

### Connection Types
- ✅ **USB Wired**: Lowest latency, most stable
- ✅ **Bluetooth**: Good performance, slight latency increase
- ✅ **Xbox Wireless Adapter**: Excellent performance

## Advanced Usage

### Combining with Other Settings

For **Maximum Responsiveness**:
```json
{
  "xbox_raw_output": true,
  "xbox_use_triggers": true,
  "deadzone": 0.0,
  "expo": 0.0,
  "acceleration_curve": "linear",
  "analog_pedal_feel": false,
  "update_hz": 200
}
```

For **Precision with Stability**:
```json
{
  "xbox_raw_output": false,
  "deadzone": 0.01,
  "expo": 0.1,
  "acceleration_curve": "linear"
}
```

### Performance Monitoring

Monitor input latency with:
```bash
# Check system input events
sudo evtest /dev/input/event5

# Monitor DAC output timing
journalctl -f | grep t80
```

## Integration Notes

- Raw output mode only affects Xbox controllers when `xbox_use_triggers: true`
- T80 racing wheel inputs are unaffected by this setting
- All other filtering and processing options remain available
- Can be toggled in real-time via GUI without restart

## Future Enhancements

Planned improvements:
- **Per-axis raw mode**: Separate settings for steering vs throttle
- **Adaptive filtering**: Smart noise reduction that doesn't affect responsiveness
- **Latency measurement**: Built-in input lag testing
- **Controller-specific profiles**: Optimized settings per controller model
