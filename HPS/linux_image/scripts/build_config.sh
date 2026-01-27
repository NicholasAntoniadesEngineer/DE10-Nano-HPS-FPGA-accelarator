#!/bin/bash
# ============================================================================
# Build Configuration for DE10-Nano Linux Image
# ============================================================================
# Source this file to set build configuration, or set environment variables
# ============================================================================

# ============================================================================
# Kernel Configuration
# ============================================================================
export KERNEL_VERSION="${KERNEL_VERSION:-5.15.0}"
export KERNEL_REPO="${KERNEL_REPO:-https://github.com/altera-opensource/linux-socfpga.git}"
export KERNEL_BRANCH="${KERNEL_BRANCH:-socfpga-5.15}"

# ============================================================================
# Root Filesystem Configuration
# ============================================================================
export ROOTFS_DISTRO="${ROOTFS_DISTRO:-debian}"
export ROOTFS_VERSION="${ROOTFS_VERSION:-bullseye}"
export ROOTFS_ARCH="${ROOTFS_ARCH:-armhf}"

# ============================================================================
# Network Configuration
# ============================================================================
# Options: "dhcp" or "static"
export NETWORK_MODE="${NETWORK_MODE:-dhcp}"

# Static IP configuration (used if NETWORK_MODE=static)
export STATIC_IP="${STATIC_IP:-192.168.1.100}"
export STATIC_GATEWAY="${STATIC_GATEWAY:-192.168.1.1}"
export STATIC_NETMASK="${STATIC_NETMASK:-255.255.255.0}"

# ============================================================================
# SSH Configuration
# ============================================================================
export SSH_ENABLED="${SSH_ENABLED:-yes}"
export SSH_ROOT_LOGIN="${SSH_ROOT_LOGIN:-yes}"
# WARNING: Change this password after first boot!
export ROOT_PASSWORD="${ROOT_PASSWORD:-root}"

# ============================================================================
# Image Configuration
# ============================================================================
export IMAGE_SIZE="${IMAGE_SIZE:-4096}"  # MB
export IMAGE_NAME="${IMAGE_NAME:-de10-nano-custom.img}"

# ============================================================================
# Cross-Compilation Toolchain
# ============================================================================
export CROSS_COMPILE="${CROSS_COMPILE:-arm-linux-gnueabihf-}"
export ARCH="${ARCH:-arm}"

# ============================================================================
# Build Directories
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINUX_IMAGE_DIR="$(cd "$SCRIPT_DIR" && pwd)"
HPS_DIR="$(cd "$LINUX_IMAGE_DIR/.." && pwd)"
REPO_ROOT="$(cd "$HPS_DIR/.." && pwd)"

export REPO_ROOT
export FPGA_DIR="${FPGA_DIR:-$REPO_ROOT/FPGA}"
export HPS_DIR
export LINUX_IMAGE_DIR
export KERNEL_DIR="${KERNEL_DIR:-$LINUX_IMAGE_DIR/kernel}"
export ROOTFS_DIR="${ROOTFS_DIR:-$LINUX_IMAGE_DIR/rootfs}"
export BUILD_DIR="${BUILD_DIR:-$LINUX_IMAGE_DIR/build}"

# ============================================================================
# Print Configuration
# ============================================================================
print_config() {
    echo "==========================================="
    echo "Build Configuration"
    echo "==========================================="
    echo "Kernel:"
    echo "  Version: $KERNEL_VERSION"
    echo "  Branch:  $KERNEL_BRANCH"
    echo "  Repo:    $KERNEL_REPO"
    echo ""
    echo "Rootfs:"
    echo "  Distro:  $ROOTFS_DISTRO"
    echo "  Version: $ROOTFS_VERSION"
    echo "  Arch:    $ROOTFS_ARCH"
    echo ""
    echo "Network:"
    echo "  Mode:    $NETWORK_MODE"
    if [ "$NETWORK_MODE" = "static" ]; then
        echo "  IP:      $STATIC_IP"
        echo "  Gateway: $STATIC_GATEWAY"
        echo "  Netmask: $STATIC_NETMASK"
    fi
    echo ""
    echo "SSH:"
    echo "  Enabled:    $SSH_ENABLED"
    echo "  Root Login: $SSH_ROOT_LOGIN"
    echo ""
    echo "Image:"
    echo "  Size: $IMAGE_SIZE MB"
    echo "  Name: $IMAGE_NAME"
    echo ""
    echo "Toolchain:"
    echo "  CROSS_COMPILE: $CROSS_COMPILE"
    echo "  ARCH:          $ARCH"
    echo "==========================================="
}

# If script is sourced, print config
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    print_config
fi
