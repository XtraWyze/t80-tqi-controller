# T80 Racing Wheel to TQi Controller

A comprehensive Python application that converts Thrustmaster T80 racing wheel inputs to TQi (Tarot Gimbal Interface) compatible DAC outputs for RC aircraft control. Features realistic acceleration curves, auto-start capabilities, and a full-featured GUI for configuration and testing.

## 🏁 Features

### Core Functionality
- **Racing Wheel Input**: Supports Thrustmaster T80 racing wheel with steering and pedal inputs
- **TQi Output**: Converts inputs to I2C DAC signals compatible with TQi gimbals
- **Dual Mode Operation**: GUI version for configuration and headless version for auto-start
- **Plug & Play**: Auto-starts on boot without requiring a display

### Advanced Input Processing
- **Duration-Based Throttle**: Realistic acceleration - button held gradually increases throttle over 1 second, instant zero on release
- **Acceleration Curves**: Multiple curve types (linear, exponential, quadratic, S-curve) with adjustable strength
- **Visual Curve Editor**: Real-time graph showing acceleration curves with interactive controls
- **Input Smoothing**: Moving average filtering for stable outputs
- **Auto-Calibration**: Automatic min/max detection for analog inputs

### Professional GUI
- **Real-time Visualization**: Live steering and throttle displays
- **Configuration Management**: Save/load settings with JSON configuration
- **Input Binding**: Easy button and axis remapping
- **Service Control**: Start/stop/manage the headless auto-start service
- **Hardware Testing**: Built-in I2C DAC testing and verification

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/t80-tqi-controller.git
cd t80-tqi-controller

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python3 t80_gui.py
# OR use the simple launcher
./run_gui.sh
```

### Auto-Start Setup
```bash
# Install as system service (auto-start on boot)
sudo ./setup_pi.sh

# Check service status
sudo systemctl status t80-headless.service
```

### Launch Options
After setup, you can launch the GUI multiple ways:
- **Desktop Icon**: Double-click T80_Controller on desktop
- **Simple Script**: `./run_gui.sh`
- **Direct Command**: `.venv/bin/python t80_gui.py`
- **System Python**: `python3 t80_gui.py` (if dependencies installed globally)

### Uninstall
```bash
# Remove service and system integration
sudo ./uninstall.sh

# For complete removal (including source files)
sudo ./uninstall.sh --complete
```

## 📋 Hardware Requirements

- **Raspberry Pi 5** (or compatible single-board computer)
- **Thrustmaster T80 Racing Wheel**
- **Dual MCP4725 I2C DAC modules**
  - Steering DAC: Address 0x60
  - Throttle DAC: Address 0x61
- **I2C Connection**: Connect DACs to Pi's I2C bus (GPIO 2/3)

## 🎮 Usage

### GUI Mode (Interactive)
```bash
python3 t80_gui.py
```
- **Main Control**: Real-time input monitoring and output control
- **Configuration**: Adjust deadzone, expo, trim, and inversion settings
- **Acceleration**: Visual curve editor with real-time preview
- **Calibration**: Input range calibration and testing
- **Binding**: Remap buttons and axes
- **Service Control**: Manage auto-start service

### Headless Mode (Auto-Start)
The system automatically starts on boot via systemd service:
- No display required
- Immediate operation when powered on
- Same acceleration curves and input processing as GUI mode
- Status monitoring via `systemctl` commands

## ⚙️ Configuration

### Acceleration Curves
The system supports multiple acceleration curve types for realistic throttle feel:

- **Linear**: Constant acceleration rate (traditional)
- **Exponential**: Slow start, rapid acceleration (sporty feel)
- **Quadratic**: Gentle progressive acceleration
- **S-Curve**: Real car feel - slow start, fast middle, gentle end

Curves can be adjusted in real-time via the GUI's Acceleration tab with visual feedback.

### Input Modes
- **Button Pedals**: Use wheel trigger buttons as gas/brake
- **Analog Axes**: Use separate analog inputs for pedals
- **Split Axis**: Use single axis with center as neutral

### Configuration Files
- `t80_config.json`: Main configuration (auto-saved by GUI)
- `t80-headless.service`: Systemd service configuration
- `requirements.txt`: Python dependencies

## 🔧 Technical Details

### Input Processing Pipeline
1. **Event Capture**: evdev captures raw input events at 200Hz
2. **Button State Tracking**: Duration-based throttle calculation
3. **Curve Application**: Selected acceleration curve applied to linear progress
4. **Smoothing**: Moving average filter for stable output
5. **DAC Output**: 12-bit I2C DAC values (0-4095)

### Architecture
- **Non-blocking Input Loop**: Continuous processing regardless of input events
- **Threaded Design**: Separate threads for GUI and input processing
- **Configuration Management**: JSON-based settings with live updates
- **Service Integration**: Seamless GUI ↔ headless service interaction

## 📊 Performance
- **Update Rate**: 200Hz input processing
- **Latency**: <5ms input to output
- **Stability**: Moving average filtering eliminates jitter
- **CPU Usage**: <5% on Raspberry Pi 5

## 📁 Project Structure
```
t80-tqi-controller/
├── t80_gui.py                 # Main GUI application
├── t80_to_tqi.py             # Headless auto-start version
├── t80_config.json           # Configuration file
├── setup_pi.sh               # Auto-start installation script
├── requirements.txt          # Python dependencies
├── t80-headless.service      # Systemd service file
├── test_*.py                 # Testing and validation scripts
└── docs/                     # Documentation and guides
```

## 🧪 Testing
```bash
# Test acceleration curves
python3 test_acceleration_curves.py

# Test pedal response
python3 test_pedals.py

# Test DAC output
python3 debug_input.py
```

## 🛠️ Development

### Adding New Acceleration Curves
1. Add curve type to `acceleration_curve` options in config
2. Implement curve function in `apply_acceleration_curve()`
3. Add description to GUI curve information
4. Update both GUI and headless versions

### Customizing Input Mapping
- Use the GUI's Binding tab for interactive remapping
- Manually edit button/axis codes in configuration
- Test with the built-in input monitoring tools

## 🐛 Troubleshooting

### Common Issues
- **No input detected**: Check wheel connection and /dev/input permissions
- **Service won't start**: Verify I2C is enabled and DACs are connected
- **Curve not working**: Ensure both GUI and headless versions are updated

### Debug Tools
- GUI provides real-time input monitoring
- Service logs: `sudo journalctl -u t80-headless.service`
- Hardware test: Use GUI's calibration tab

## 📜 License
MIT License - See LICENSE file for details

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🙏 Acknowledgments
- Thrustmaster for the T80 racing wheel
- Tarot for the TQi gimbal system
- Raspberry Pi Foundation
- Python evdev and I2C libraries

---

**Ready to race! 🏎️** This project transforms your racing wheel into a professional RC aircraft controller with realistic throttle curves and plug-and-play operation.
