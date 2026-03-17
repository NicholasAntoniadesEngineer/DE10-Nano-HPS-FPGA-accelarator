#!/bin/bash
# ============================================================================
# devmem2 Installation Script
# ============================================================================
# Cross-compiles and installs devmem2 (/dev/mem read/write utility).
# GPL-2.0, Jan-Derk Bakker — not available in Debian armhf repos.
# Called during rootfs build to embed devmem2 into the image.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOTFS_DIR="${ROOTFS_DIR:-${SCRIPT_DIR}/../build/rootfs}"

HPS_DIR="$(cd "${SCRIPT_DIR}/../../../" && pwd)"
# Docker volume fallback: when running from /var/lib/rootfs-build, SCRIPT_DIR resolves to /
if [ ! -d "${HPS_DIR}/tools" ] && [ -d "/workspace/HPS" ]; then
    HPS_DIR="/workspace/HPS"
fi
DEVMEM2_SRC="${HPS_DIR}/tools/devmem2.c"
DEVMEM2_BIN="${HPS_DIR}/tools/devmem2"

echo "Building and installing devmem2..."

if [ ! -f "$DEVMEM2_SRC" ]; then
    echo "Warning: devmem2.c not found at $DEVMEM2_SRC, skipping installation"
    exit 0
fi

if [ ! -f "$DEVMEM2_BIN" ] || [ "$DEVMEM2_SRC" -nt "$DEVMEM2_BIN" ]; then
    if command -v arm-linux-gnueabihf-gcc &>/dev/null; then
        arm-linux-gnueabihf-gcc -O2 -o "$DEVMEM2_BIN" "$DEVMEM2_SRC" || {
            echo "Warning: Failed to cross-compile devmem2, skipping installation"
            exit 0
        }
        echo "  Cross-compiled devmem2 (ARM)"
    else
        echo "Warning: arm-linux-gnueabihf-gcc not found, skipping devmem2"
        exit 0
    fi
fi

if [ ! -f "$DEVMEM2_BIN" ]; then
    exit 0
fi

if [ ! -d "$ROOTFS_DIR" ]; then
    echo "Error: Rootfs directory not found: $ROOTFS_DIR"
    exit 1
fi

mkdir -p "${ROOTFS_DIR}/usr/local/bin"
echo "  Copying devmem2 to /usr/local/bin..."
cp "$DEVMEM2_BIN" "${ROOTFS_DIR}/usr/local/bin/devmem2"
chmod 755 "${ROOTFS_DIR}/usr/local/bin/devmem2"

echo "devmem2 installation complete"
