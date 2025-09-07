#!/bin/bash

# T80 Racing Wheel Controller - Uninstall Script
# This script removes the T80 controller service and all related components

set -e

echo "========================================"
echo "T80 Controller - Uninstall Script"
echo "========================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for some operations
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script needs sudo privileges for some operations."
        print_status "Please run with: sudo ./uninstall.sh"
        exit 1
    fi
}

# Function to confirm uninstall
confirm_uninstall() {
    echo -e "${YELLOW}WARNING: This will completely remove the T80 Controller system!${NC}"
    echo
    echo "This will remove:"
    echo "  • Systemd service (t80-headless.service)"
    echo "  • Service files from /etc/systemd/system/"
    echo "  • User from input and i2c groups"
    echo "  • Udev rules for input devices"
    echo "  • Desktop launcher (if exists)"
    echo "  • Virtual environment (optional)"
    echo
    echo "This will NOT remove:"
    echo "  • Source code files"
    echo "  • Configuration files (t80_config.json)"
    echo "  • I2C interface settings"
    echo
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Uninstall cancelled."
        exit 0
    fi
}

# Stop and disable the service
remove_service() {
    print_status "Stopping and disabling T80 headless service..."
    
    if systemctl is-active --quiet t80-headless.service; then
        systemctl stop t80-headless.service
        print_success "Service stopped"
    else
        print_warning "Service was not running"
    fi
    
    if systemctl is-enabled --quiet t80-headless.service 2>/dev/null; then
        systemctl disable t80-headless.service
        print_success "Service disabled"
    else
        print_warning "Service was not enabled"
    fi
    
    # Remove service file
    if [ -f "/etc/systemd/system/t80-headless.service" ]; then
        rm /etc/systemd/system/t80-headless.service
        print_success "Service file removed"
    else
        print_warning "Service file not found"
    fi
    
    # Reload systemd
    systemctl daemon-reload
    systemctl reset-failed
    print_success "Systemd configuration reloaded"
}

# Remove udev rules
remove_udev_rules() {
    print_status "Removing udev rules..."
    
    if [ -f "/etc/udev/rules.d/99-t80-controller.rules" ]; then
        rm /etc/udev/rules.d/99-t80-controller.rules
        print_success "Udev rules removed"
        udevadm control --reload-rules
        print_success "Udev rules reloaded"
    else
        print_warning "Udev rules file not found"
    fi
}

# Remove user from groups
remove_user_from_groups() {
    print_status "Removing user from input and i2c groups..."
    
    # Get the original user (not root)
    ORIGINAL_USER=${SUDO_USER:-$USER}
    
    if id -nG "$ORIGINAL_USER" | grep -qw "input"; then
        gpasswd -d "$ORIGINAL_USER" input
        print_success "User removed from input group"
    else
        print_warning "User was not in input group"
    fi
    
    if id -nG "$ORIGINAL_USER" | grep -qw "i2c"; then
        gpasswd -d "$ORIGINAL_USER" i2c
        print_success "User removed from i2c group"
    else
        print_warning "User was not in i2c group"
    fi
}

# Remove desktop launcher
remove_desktop_launcher() {
    print_status "Removing desktop launcher..."
    
    # Get the original user's home directory
    ORIGINAL_USER=${SUDO_USER:-$USER}
    USER_HOME=$(eval echo ~$ORIGINAL_USER)
    
    DESKTOP_FILE="$USER_HOME/Desktop/T80_Controller.desktop"
    
    if [ -f "$DESKTOP_FILE" ]; then
        rm "$DESKTOP_FILE"
        print_success "Desktop launcher removed"
    else
        print_warning "Desktop launcher not found"
    fi
}

# Remove virtual environment (optional)
remove_venv() {
    print_status "Checking for virtual environment..."
    
    # Get current directory and check for .venv
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    VENV_PATH="$SCRIPT_DIR/.venv"
    
    if [ -d "$VENV_PATH" ]; then
        echo
        read -p "Remove virtual environment (.venv)? This will delete all installed Python packages. (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_PATH"
            print_success "Virtual environment removed"
        else
            print_warning "Virtual environment kept"
        fi
    else
        print_warning "Virtual environment not found"
    fi
}

# Clean up any running processes
cleanup_processes() {
    print_status "Cleaning up any running T80 processes..."
    
    # Kill any running GUI instances
    if pgrep -f "t80_gui.py" > /dev/null; then
        pkill -f "t80_gui.py"
        print_success "Stopped GUI processes"
    fi
    
    # Kill any running headless instances
    if pgrep -f "t80_to_tqi.py" > /dev/null; then
        pkill -f "t80_to_tqi.py"
        print_success "Stopped headless processes"
    fi
}

# Display final status
show_completion_status() {
    echo
    echo "========================================"
    echo -e "${GREEN}Uninstall Complete!${NC}"
    echo "========================================"
    echo
    echo "The following have been removed:"
    echo "  ✓ T80 headless service"
    echo "  ✓ Systemd service files"
    echo "  ✓ Udev rules"
    echo "  ✓ User group memberships"
    echo "  ✓ Desktop launcher"
    echo "  ✓ Running processes"
    
    if [ -d "$(dirname "${BASH_SOURCE[0]}")/.venv" ]; then
        echo "  • Virtual environment (kept)"
    else
        echo "  ✓ Virtual environment"
    fi
    
    echo
    echo "Still present:"
    echo "  • Source code files"
    echo "  • Configuration files (t80_config.json)"
    echo "  • I2C interface (still enabled)"
    echo
    print_warning "Reboot recommended to ensure all changes take effect."
    echo
    print_status "To completely remove source files, manually delete this directory:"
    print_status "rm -rf $(dirname "${BASH_SOURCE[0]}")"
}

# Main uninstall process
main() {
    # Check for sudo
    check_sudo
    
    # Confirm uninstall
    confirm_uninstall
    
    echo
    print_status "Starting uninstall process..."
    echo
    
    # Clean up processes first
    cleanup_processes
    
    # Remove service
    remove_service
    
    # Remove udev rules
    remove_udev_rules
    
    # Remove user from groups
    remove_user_from_groups
    
    # Remove desktop launcher
    remove_desktop_launcher
    
    # Optionally remove virtual environment
    remove_venv
    
    # Show completion status
    show_completion_status
}

# Run main function
main "$@"
