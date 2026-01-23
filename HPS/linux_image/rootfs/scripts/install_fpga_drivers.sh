#!/bin/bash
# ============================================================================
# FPGA Driver Installation Post-Install Script
# ============================================================================
# Sets up FPGA driver access and permissions
# ============================================================================

set -e

echo "Setting up FPGA driver access..."

# Create udev rules for /dev/mem access (if needed)
UDEV_RULES="/etc/udev/rules.d/99-fpga.rules"
if [ ! -f "$UDEV_RULES" ]; then
    echo "Creating udev rules for FPGA access..."
    mkdir -p "$(dirname "$UDEV_RULES")"
    cat > "$UDEV_RULES" << EOF
# FPGA device access rules
# Allow access to /dev/mem for FPGA communication
KERNEL=="mem", MODE="0666"
EOF
    echo "Udev rules created: $UDEV_RULES"
fi

# Ensure UIO modules are available (if using UIO)
if [ -d /lib/modules ]; then
    echo "UIO modules will be available after kernel modules are installed"
fi

echo "FPGA driver setup complete"
