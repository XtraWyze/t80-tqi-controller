#!/bin/bash
# T80 Headless Controller Management Script

SERVICE_NAME="t80-headless.service"

case "$1" in
    start)
        echo "Starting T80 controller..."
        sudo systemctl start $SERVICE_NAME
        ;;
    stop)
        echo "Stopping T80 controller..."
        sudo systemctl stop $SERVICE_NAME
        ;;
    restart)
        echo "Restarting T80 controller..."
        sudo systemctl restart $SERVICE_NAME
        ;;
    status)
        sudo systemctl status $SERVICE_NAME
        ;;
    logs)
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    enable)
        echo "Enabling T80 controller to start on boot..."
        sudo systemctl enable $SERVICE_NAME
        ;;
    disable)
        echo "Disabling T80 controller from starting on boot..."
        sudo systemctl disable $SERVICE_NAME
        ;;
    test)
        echo "Testing I2C DAC connections..."
        sudo i2cdetect -y 1
        echo ""
        echo "Checking T80 wheel connection..."
        ls -la /dev/input/by-id/*Thrustmaster* 2>/dev/null || echo "T80 wheel not found"
        echo ""
        echo "Service status:"
        sudo systemctl is-enabled $SERVICE_NAME 2>/dev/null || echo "Service not enabled"
        sudo systemctl is-active $SERVICE_NAME 2>/dev/null || echo "Service not running"
        ;;
    *)
        echo "T80 Headless Controller Management"
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable|test}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the T80 controller service"
        echo "  stop     - Stop the T80 controller service"
        echo "  restart  - Restart the T80 controller service"
        echo "  status   - Show service status"
        echo "  logs     - Show live service logs"
        echo "  enable   - Enable service to start on boot"
        echo "  disable  - Disable service from starting on boot"
        echo "  test     - Test hardware connections and service status"
        ;;
esac
