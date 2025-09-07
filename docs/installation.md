# Software Installation Guide

## Prerequisites

### Operating System
- **Raspberry Pi OS** (Bookworm recommended)
- **Ubuntu** 22.04+ (for other SBCs)
- **Debian** 12+ (Bookworm)

### Python Requirements
- **Python 3.8+** (3.11+ recommended)
- **pip** package manager
- **venv** for virtual environments

## Quick Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/t80-tqi-controller.git
cd t80-tqi-controller
```

### 2. Automatic Setup (Recommended)
```bash
sudo chmod +x setup_pi.sh
sudo ./setup_pi.sh
```

This script will:
- Install Python dependencies
- Enable I2C interface
- Create systemd service
- Configure auto-start

### 3. Manual Installation

#### Install Dependencies
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install packages
pip install -r requirements.txt
```

#### Enable I2C
```bash
sudo raspi-config
# Enable I2C in Interfacing Options
```

#### Install Service
```bash
sudo cp t80-headless.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable t80-headless.service
sudo systemctl start t80-headless.service
```

## Configuration

### User Permissions
Add user to input and i2c groups:
```bash
sudo usermod -a -G input,i2c $USER
```

### Device Permissions
Create udev rule for input device access:
```bash
sudo nano /etc/udev/rules.d/99-input.rules
```
Add:
```
SUBSYSTEM=="input", GROUP="input", MODE="0664"
```

## Testing Installation

### Check Service Status
```bash
sudo systemctl status t80-headless.service
```

### Test GUI
```bash
python3 t80_gui.py
```

### Verify Hardware
```bash
# Check I2C devices
sudo i2cdetect -y 1

# Check input devices
ls /dev/input/by-id/
```

## Troubleshooting

### Common Issues
- **Permission denied**: Ensure user is in input/i2c groups
- **Module not found**: Activate virtual environment
- **Service fails**: Check I2C enabled and DACs connected
- **No input**: Verify T80 wheel connection
