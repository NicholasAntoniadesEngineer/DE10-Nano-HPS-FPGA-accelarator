#!/bin/bash
# ============================================================================
# Boot LED Indicator Installation Script
# ============================================================================
# Installs the boot LED indicator and enables it as a systemd service
# Called during rootfs build to embed boot_led into the image
# ============================================================================

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOTFS_DIR="${SCRIPT_DIR}/../build/rootfs"

# Source locations (relative to HPS directory)
HPS_DIR="$(cd "${SCRIPT_DIR}/../../../" && pwd)"
BOOT_LED_DIR="${HPS_DIR}/applications/boot_led"
BOOT_LED_BIN="${BOOT_LED_DIR}/boot_led"
BOOT_LED_SERVICE="${BOOT_LED_DIR}/boot-led.service"

echo "Installing boot LED indicator..."

# Check if boot_led binary exists
if [ ! -f "$BOOT_LED_BIN" ]; then
    echo "Warning: boot_led binary not found at $BOOT_LED_BIN"
    echo "Building boot_led..."
    
    # Try to build it
    if [ -f "${BOOT_LED_DIR}/Makefile" ]; then
        make -C "$BOOT_LED_DIR" CROSS_COMPILE=arm-linux-gnueabihf- || {
            echo "Warning: Failed to build boot_led, skipping installation"
            exit 0
        }
    else
        echo "Warning: boot_led Makefile not found, skipping installation"
        exit 0
    fi
fi

# Check rootfs directory exists
if [ ! -d "$ROOTFS_DIR" ]; then
    echo "Error: Rootfs directory not found: $ROOTFS_DIR"
    exit 1
fi

# Create target directories
mkdir -p "${ROOTFS_DIR}/usr/local/bin"
mkdir -p "${ROOTFS_DIR}/etc/systemd/system"

# Copy boot_led binary
echo "  Copying boot_led to /usr/local/bin..."
cp "$BOOT_LED_BIN" "${ROOTFS_DIR}/usr/local/bin/"
chmod 755 "${ROOTFS_DIR}/usr/local/bin/boot_led"

# Copy systemd service file
if [ -f "$BOOT_LED_SERVICE" ]; then
    echo "  Copying boot-led.service..."
    cp "$BOOT_LED_SERVICE" "${ROOTFS_DIR}/etc/systemd/system/"
    chmod 644 "${ROOTFS_DIR}/etc/systemd/system/boot-led.service"
    
    # Create symlink to enable service on boot
    mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
    ln -sf /etc/systemd/system/boot-led.service \
           "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/boot-led.service"
    
    echo "  Boot LED service enabled"
else
    echo "Warning: boot-led.service not found, service not installed"
fi

echo "Boot LED installation complete"
