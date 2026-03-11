#!/bin/bash
# ============================================================================
# SSH Setup Post-Install Script
# ============================================================================
# Configures SSH server and enables service
# ============================================================================

set -e

echo "Setting up SSH server..."

# Generate SSH host keys if they don't exist
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    echo "Generating SSH host keys..."
    ssh-keygen -A
fi

# Ensure SSH directory exists
mkdir -p /etc/ssh

# Enable SSH service
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

echo "SSH configuration complete"
