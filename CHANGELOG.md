# Changelog

All notable changes to the T80-TQi Controller project will be documented in this file.

## [1.0.0] - 2025-09-06

### Added
- **Initial Release**: Complete T80 Racing Wheel to TQi controller system
- **Dual Mode Operation**: GUI and headless versions for different use cases
- **Duration-Based Throttle**: Realistic acceleration with button hold timing
- **Acceleration Curves**: Multiple curve types (linear, exponential, quadratic, S-curve)
- **Visual Curve Editor**: Real-time graph with interactive controls
- **Auto-Start Service**: Systemd service for plug-and-play operation
- **Professional GUI**: Multi-tab interface with comprehensive controls
- **Input Binding**: Easy button and axis remapping system
- **Service Control**: GUI-based management of headless service
- **Hardware Testing**: Built-in DAC testing and calibration tools

### Features
- **Main Control Tab**: Real-time input monitoring and output visualization
- **Configuration Tab**: Complete settings management with live updates
- **Acceleration Tab**: Visual curve editor with strength and duration controls
- **Calibration Tab**: Input range calibration and hardware testing
- **Binding Tab**: Interactive input remapping with click-to-bind functionality
- **Service Control Tab**: Headless service management and log monitoring

### Technical Implementation
- **Non-blocking Input Loop**: 200Hz processing with select()-based event handling
- **Threaded Architecture**: Separate GUI and input processing threads
- **JSON Configuration**: Auto-saving configuration with live updates
- **Moving Average Filtering**: Stable output with jitter elimination
- **I2C DAC Control**: 12-bit precision output (0-4095 range)

### Hardware Support
- **Raspberry Pi 5**: Optimized for latest Pi hardware
- **Thrustmaster T80**: Full wheel and pedal support
- **MCP4725 DACs**: Dual I2C DAC configuration (0x60, 0x61)
- **Auto-detection**: Automatic T80 device discovery

### Performance
- **Low Latency**: <5ms input to output processing
- **Efficient CPU Usage**: <5% CPU utilization on Pi 5
- **High Update Rate**: 200Hz input processing
- **Stable Operation**: Robust error handling and recovery

### Documentation
- **Comprehensive README**: Full setup and usage instructions
- **Code Documentation**: Inline comments and docstrings
- **Testing Scripts**: Validation and debugging tools
- **Setup Automation**: One-command installation script

### Development Tools
- **Test Scripts**: Acceleration curve testing and pedal validation
- **Debug Output**: Real-time linear vs curved throttle values
- **Service Logs**: Comprehensive logging for troubleshooting
- **Hardware Verification**: I2C and device connectivity testing
