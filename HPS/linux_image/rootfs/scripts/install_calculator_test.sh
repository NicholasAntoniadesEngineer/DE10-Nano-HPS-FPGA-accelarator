#!/bin/bash
# ============================================================================
# Calculator Test Suite Installation Script
# ============================================================================
# Installs the calculator_test binary into the rootfs.
# Called during rootfs build to embed calculator_test into the image.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOTFS_DIR="${ROOTFS_DIR:-${SCRIPT_DIR}/../build/rootfs}"

HPS_DIR="$(cd "${SCRIPT_DIR}/../../../" && pwd)"
TEST_DIR="${HPS_DIR}/applications/calculator_test"
TEST_BIN="${TEST_DIR}/calculator_test"

echo "Installing calculator_test..."

if [ ! -f "$TEST_BIN" ]; then
    echo "  Building calculator_test..."
    if [ -f "${TEST_DIR}/Makefile" ]; then
        make -C "$TEST_DIR" CROSS_COMPILE=arm-linux-gnueabihf- || {
            echo "Warning: Failed to build calculator_test, skipping installation"
            exit 0
        }
    else
        echo "Warning: calculator_test Makefile not found, skipping installation"
        exit 0
    fi
fi

if [ ! -d "$ROOTFS_DIR" ]; then
    echo "Error: Rootfs directory not found: $ROOTFS_DIR"
    exit 1
fi

mkdir -p "${ROOTFS_DIR}/usr/local/bin"
echo "  Copying calculator_test to /usr/local/bin..."
cp "$TEST_BIN" "${ROOTFS_DIR}/usr/local/bin/"
chmod 755 "${ROOTFS_DIR}/usr/local/bin/calculator_test"

echo "Calculator test installation complete"
