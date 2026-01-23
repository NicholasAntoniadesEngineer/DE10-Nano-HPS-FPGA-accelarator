#!/bin/bash
# ============================================================================
# System Services Setup Post-Install Script
# ============================================================================
# Enables and configures system services
# ============================================================================

set -e

echo "Setting up system services..."

# Enable networking
if command -v systemctl &> /dev/null; then
    systemctl enable networking
    echo "Networking service enabled"
fi

# Enable SSH (if not already enabled)
if command -v systemctl &> /dev/null; then
    if systemctl enable ssh; then
        echo "SSH service enabled"
    elif systemctl enable sshd; then
        echo "SSHD service enabled"
    else
        echo "ERROR: Failed to enable SSH service" >&2
        exit 1
    fi
fi

# Create /etc/hostname
if [ ! -f /etc/hostname ]; then
    echo "de10-nano" > /etc/hostname
    echo "Hostname set to: de10-nano"
fi

# Create /etc/hosts
if [ ! -f /etc/hosts ]; then
    cat > /etc/hosts << EOF
127.0.0.1	localhost
127.0.1.1	de10-nano

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF
    echo "Hosts file created"
fi

echo "System services setup complete"
