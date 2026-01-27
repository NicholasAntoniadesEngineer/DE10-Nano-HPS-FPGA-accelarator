#!/bin/bash
# ============================================================================
# SD Image Creation Wrapper Script
# ============================================================================
# Simplified script to create DE10-Nano SD card image
# Sets up environment variables and runs the main script
# Comprehensive logging for debugging and progress tracking
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') - $1" >&2
}

log_header() {
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===========================================${NC}"
}

# Script directory and paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINUX_IMAGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$LINUX_IMAGE_DIR/.." && pwd)"

# Default bootloader paths - prefer modern U-Boot build, fall back to legacy
# Environment variables can override these defaults
BOOTLOADER_BUILD_DIR="$LINUX_IMAGE_DIR/bootloader/build"
if [ -z "$PRELOADER_BIN" ]; then
    if [ -f "$BOOTLOADER_BUILD_DIR/u-boot-with-spl.sfp" ]; then
        PRELOADER_PATH="$BOOTLOADER_BUILD_DIR/u-boot-with-spl.sfp"
    else
        PRELOADER_PATH="$REPO_ROOT/preloader/preloader-mkpimage.bin"
    fi
else
    PRELOADER_PATH="$PRELOADER_BIN"
fi
if [ -z "$UBOOT_IMG" ]; then
    if [ -f "$BOOTLOADER_BUILD_DIR/u-boot.img" ]; then
        UBOOT_PATH="$BOOTLOADER_BUILD_DIR/u-boot.img"
    else
        UBOOT_PATH="$REPO_ROOT/preloader/uboot-socfpga/u-boot.img"
    fi
else
    UBOOT_PATH="$UBOOT_IMG"
fi

# Use normalized script if provided by Makefile, otherwise use original
if [ -n "$NORMALIZED_MAIN_SCRIPT" ] && [ -f "$NORMALIZED_MAIN_SCRIPT" ]; then
    MAIN_SCRIPT="$NORMALIZED_MAIN_SCRIPT"
    log_info "Using pre-normalized main script: $MAIN_SCRIPT"
else
    MAIN_SCRIPT="$SCRIPT_DIR/create_sd_image.sh"
fi

# Start logging
log_header "DE10-Nano SD Image Creation Wrapper"
log_info "Script started at $(date)"
log_info "Repository root: $REPO_ROOT"
log_info "Script directory: $SCRIPT_DIR"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_success "Running as root - proceeding with SD image creation"
else
    log_error "This script must be run as root (sudo)"
    log_error "Run: sudo $0"
    exit 1
fi

# Set environment variables for bootloader binaries
log_info "Setting up environment variables..."
export PRELOADER_BIN="$PRELOADER_PATH"
export UBOOT_IMG="$UBOOT_PATH"

log_info "PRELOADER_BIN set to: $PRELOADER_BIN"
log_info "UBOOT_IMG set to: $UBOOT_IMG"

# Verify required files exist
log_info "Verifying required files..."

if [ -f "$PRELOADER_BIN" ]; then
    PRELOADER_SIZE=$(du -h "$PRELOADER_BIN" | cut -f1)
    log_success "Preloader found: $PRELOADER_BIN (${PRELOADER_SIZE})"
else
    log_error "Preloader NOT found: $PRELOADER_BIN"
    log_error "Please ensure prebuilt bootloader binaries are available"
    exit 1
fi

if [ -f "$UBOOT_IMG" ]; then
    UBOOT_SIZE=$(du -h "$UBOOT_IMG" | cut -f1)
    log_success "U-Boot found: $UBOOT_IMG (${UBOOT_SIZE})"
else
    log_error "U-Boot NOT found: $UBOOT_IMG"
    log_error "Please ensure prebuilt bootloader binaries are available"
    exit 1
fi

if [ -f "$MAIN_SCRIPT" ]; then
    log_success "Main SD creation script found: $MAIN_SCRIPT"
else
    log_error "Main SD creation script NOT found: $MAIN_SCRIPT"
    exit 1
fi

# Check other required components
log_info "Checking other required components..."

KERNEL_PATH="$LINUX_IMAGE_DIR/kernel/build/arch/arm/boot/zImage"
if [ -f "$KERNEL_PATH" ]; then
    KERNEL_SIZE=$(du -h "$KERNEL_PATH" | cut -f1)
    log_success "Linux kernel found: $KERNEL_PATH (${KERNEL_SIZE})"
else
    log_warning "Linux kernel NOT found: $KERNEL_PATH"
    log_warning "Kernel will be built if missing during SD creation"
fi

ROOTFS_PATH="$LINUX_IMAGE_DIR/rootfs/build/rootfs.tar.gz"
if [ -f "$ROOTFS_PATH" ]; then
    ROOTFS_SIZE=$(du -h "$ROOTFS_PATH" | cut -f1)
    log_success "Root filesystem found: $ROOTFS_PATH (${ROOTFS_SIZE})"
else
    log_warning "Root filesystem NOT found: $ROOTFS_PATH"
    log_warning "Rootfs will be built if missing during SD creation"
fi

RBF_PATH="$REPO_ROOT/build/output_files/DE10_NANO_SoC_GHRD.rbf"
if [ -f "$RBF_PATH" ]; then
    RBF_SIZE=$(du -h "$RBF_PATH" | cut -f1)
    log_success "FPGA bitstream found: $RBF_PATH (${RBF_SIZE})"
else
    log_warning "FPGA bitstream NOT found: $RBF_PATH"
    log_warning "Using existing RBF - if outdated, rebuild FPGA first"
fi

# Summary
log_header "Configuration Summary"
echo "Preloader:     $PRELOADER_BIN"
echo "U-Boot:        $UBOOT_IMG"
echo "Kernel:        $KERNEL_PATH"
echo "Rootfs:        $ROOTFS_PATH"
echo "FPGA RBF:      $RBF_PATH"
echo "Main Script:   $MAIN_SCRIPT"
echo "Output Dir:    $LINUX_IMAGE_DIR/build/"

# Execute main script
log_header "Starting SD Image Creation"
log_info "Executing main SD creation script..."
log_info "Main script path: $MAIN_SCRIPT"
log_info "Arguments: $@"
echo ""

# Run the main SD image creation script
bash "$MAIN_SCRIPT" "$@"

RESULT=$?

echo ""
if [ $RESULT -eq 0 ]; then
    log_success "SD image creation completed successfully"
else
    log_error "SD image creation failed with exit code $RESULT"
fi

exit $RESULT
