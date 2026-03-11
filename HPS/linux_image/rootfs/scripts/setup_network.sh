#!/bin/bash
# ============================================================================
# Network Setup Post-Install Script
# ============================================================================
# Configures network interfaces and services
# ============================================================================

set -e

echo "Setting up network configuration..."

# Ensure network interfaces file exists
if [ ! -f /etc/network/interfaces ]; then
    echo "Creating /etc/network/interfaces..."
    mkdir -p /etc/network
    cat > /etc/network/interfaces << EOF
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
EOF
fi

# Enable networking service
if command -v systemctl &> /dev/null; then
    systemctl enable networking
fi

echo "Network configuration complete"
