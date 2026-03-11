#!/bin/bash
# ============================================================================
# Calculator Demo Installation Script
# ============================================================================
# Installs the calculator_demo binary and its systemd service into the rootfs.
# Called during rootfs build from build_rootfs.sh: install_hps_applications().
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOTFS_DIR="${ROOTFS_DIR:-${SCRIPT_DIR}/../build/rootfs}"

HPS_DIR="$(cd "${SCRIPT_DIR}/../../../" && pwd)"
DEMO_DIR="${HPS_DIR}/applications/calculator_demo"
DEMO_BIN="${DEMO_DIR}/calculator_demo"
DEMO_SERVICE="${DEMO_DIR}/calculator-demo.service"

echo "Installing calculator demo..."

# Build the binary if not already built
if [ ! -f "$DEMO_BIN" ]; then
    echo "  Building calculator_demo..."
    if [ -f "${DEMO_DIR}/Makefile" ]; then
        make -C "$DEMO_DIR" CROSS_COMPILE=arm-linux-gnueabihf- || {
            echo "Warning: Failed to build calculator_demo, skipping installation"
            exit 0
        }
    else
        echo "Warning: calculator_demo Makefile not found, skipping installation"
        exit 0
    fi
fi

# Verify rootfs exists
if [ ! -d "$ROOTFS_DIR" ]; then
    echo "Error: Rootfs directory not found: $ROOTFS_DIR"
    exit 1
fi

# Install binary
mkdir -p "${ROOTFS_DIR}/usr/local/bin"
echo "  Copying calculator_demo to /usr/local/bin..."
cp "$DEMO_BIN" "${ROOTFS_DIR}/usr/local/bin/"
chmod 755 "${ROOTFS_DIR}/usr/local/bin/calculator_demo"

# Install systemd service and enable it
if [ -f "$DEMO_SERVICE" ]; then
    mkdir -p "${ROOTFS_DIR}/etc/systemd/system"
    echo "  Copying calculator-demo.service..."
    cp "$DEMO_SERVICE" "${ROOTFS_DIR}/etc/systemd/system/"
    chmod 644 "${ROOTFS_DIR}/etc/systemd/system/calculator-demo.service"

    # Enable service (symlink into multi-user.target.wants)
    mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
    ln -sf /etc/systemd/system/calculator-demo.service \
           "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants/calculator-demo.service"
    echo "  calculator-demo.service enabled on boot"
else
    echo "Warning: calculator-demo.service not found, service not installed"
fi

echo "Calculator demo installation complete"
