# Hardware Setup Guide

## Required Components

### Main Hardware
- **Raspberry Pi 5** (recommended) or Pi 4/3B+
- **Thrustmaster T80 Racing Wheel**
- **2x MCP4725 I2C DAC Modules** (12-bit, 3.3V)
- **MicroSD Card** (16GB+ recommended)
- **Power Supply** for Raspberry Pi

### Wiring
Connect the MCP4725 DAC modules to the Raspberry Pi I2C bus:

```
Raspberry Pi GPIO    MCP4725 Module
GPIO 2 (SDA)   →     SDA
GPIO 3 (SCL)   →     SCL
3.3V           →     VCC
GND            →     GND
```

### I2C Addresses
- **Steering DAC**: 0x60 (96 decimal)
- **Throttle DAC**: 0x61 (97 decimal)

Configure DAC addresses using the A0 pin:
- A0 = GND: Address 0x60
- A0 = VCC: Address 0x61

## Pi Configuration

### Enable I2C
```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
```

Or manually edit `/boot/config.txt`:
```
dtparam=i2c_arm=on
```

### Check I2C Devices
```bash
sudo i2cdetect -y 1
```
Should show devices at addresses 60 and 61.

## T80 Wheel Connection
The T80 wheel connects via USB and should appear as `/dev/input/eventX`. The system automatically detects the wheel using device identifiers.

## Testing Hardware
Use the GUI's Calibration tab to test:
1. I2C DAC connectivity
2. Input device detection
3. Signal output verification
