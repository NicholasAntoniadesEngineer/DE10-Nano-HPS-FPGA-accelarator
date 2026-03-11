#!/bin/bash
# ============================================================================
# SD Card Image Deployment Script for DE10-Nano
# ============================================================================
# Writes pre-built image to SD card with verification
# ============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINUX_IMAGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HPS_DIR="$(cd "$LINUX_IMAGE_DIR/.." && pwd)"
REPO_ROOT="$(cd "$HPS_DIR/.." && pwd)"

# Default image location
IMAGE_NAME="${IMAGE_NAME:-de10-nano-custom.img}"
IMAGE_FILE="${IMAGE_FILE:-$LINUX_IMAGE_DIR/build/$IMAGE_NAME}"

# ============================================================================
# Functions
# ============================================================================

print_header() {
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}===========================================${NC}"
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

usage() {
    cat << EOF
Usage: $0 <SD_CARD_DEVICE> [OPTIONS]

Deploys DE10-Nano Linux image to SD card.

Arguments:
  SD_CARD_DEVICE    SD card device (e.g., /dev/sdb, /dev/mmcblk0)

Options:
  -i, --image FILE  Image file path (default: $IMAGE_FILE)
  -f, --force       Skip confirmation prompts
  -h, --help        Show this help message

Examples:
  $0 /dev/sdb
  $0 /dev/mmcblk0 -i /path/to/custom.img
  $0 /dev/sdb --force

WARNING: This will overwrite all data on the SD card!
EOF
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        print_error "Run with: sudo $0 $*"
        exit 1
    fi
}

check_image() {
    if [ ! -f "$IMAGE_FILE" ]; then
        print_error "Image file not found: $IMAGE_FILE"
        print_error "Build image first: cd HPS/linux_image && make linux-image"
        exit 1
    fi
    
    echo -e "${GREEN}Image file found: $IMAGE_FILE${NC}"
    SIZE=$(du -h "$IMAGE_FILE" | cut -f1)
    echo -e "${GREEN}Image size: $SIZE${NC}"
}

verify_device() {
    local device=$1
    
    if [ ! -b "$device" ]; then
        print_error "Device not found or not a block device: $device"
        exit 1
    fi
    
    # Check if device is mounted
    if mount | grep -q "$device"; then
        print_warning "Device $device appears to be mounted"
        print_warning "Unmounting partitions..."
        for partition in $(lsblk -ln -o NAME "$device" | grep -v "^$(basename $device)$"); do
            umount "/dev/$partition" 2>/dev/null || true
        done
    fi
    
    # Get device info
    local size=$(lsblk -b -d -o SIZE -n "$device")
    local size_gb=$((size / 1024 / 1024 / 1024))
    
    echo -e "${GREEN}Device: $device${NC}"
    echo -e "${GREEN}Size: ${size_gb}GB${NC}"
    
    # List partitions
    echo -e "${YELLOW}Current partitions:${NC}"
    lsblk "$device" || true
}

confirm_deployment() {
    local device=$1
    
    if [ "$FORCE" = "yes" ]; then
        return 0
    fi
    
    echo ""
    print_warning "WARNING: This will overwrite all data on $device!"
    echo ""
    echo -e "${YELLOW}Are you sure you want to continue? (yes/no):${NC} "
    read -r response
    
    if [ "$response" != "yes" ]; then
        echo "Deployment cancelled"
        exit 0
    fi
}

write_image() {
    local device=$1
    
    print_header "Writing Image to SD Card"
    
    print_step "Writing $IMAGE_FILE to $device..."
    print_step "This may take several minutes..."
    
    # Write image
    dd if="$IMAGE_FILE" of="$device" bs=4M status=progress conv=fsync
    
    # Sync to ensure data is written
    sync
    
    echo -e "${GREEN}Image written successfully${NC}"
}

verify_deployment() {
    local device=$1
    
    print_header "Verifying Deployment"
    
    print_step "Checking partitions..."
    
    # Wait for partitions to be recognized
    sleep 2
    
    # List partitions
    lsblk "$device"
    
    # Check if partitions exist
    local boot_part=""
    local rootfs_part=""
    
    if [[ "$device" == *"mmcblk"* ]] || [[ "$device" == *"loop"* ]]; then
        boot_part="${device}p1"
        rootfs_part="${device}p2"
    else
        boot_part="${device}1"
        rootfs_part="${device}2"
    fi
    
    if [ -b "$boot_part" ]; then
        echo -e "${GREEN}✓ Boot partition found: $boot_part${NC}"
    else
        print_warning "Boot partition not found: $boot_part"
    fi
    
    if [ -b "$rootfs_part" ]; then
        echo -e "${GREEN}✓ Rootfs partition found: $rootfs_part${NC}"
    else
        print_warning "Rootfs partition not found: $rootfs_part"
    fi
    
    echo -e "${GREEN}Deployment verification complete${NC}"
}

# ============================================================================
# Main
# ============================================================================

main() {
    local device=""
    FORCE="no"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--image)
                IMAGE_FILE="$2"
                shift 2
                ;;
            -f|--force)
                FORCE="yes"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            /dev/*)
                device="$1"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    if [ -z "$device" ]; then
        print_error "SD card device not specified"
        usage
        exit 1
    fi
    
    print_header "DE10-Nano SD Card Deployment"
    
    check_root
    check_image
    verify_device "$device"
    confirm_deployment "$device"
    write_image "$device"
    verify_deployment "$device"
    
    print_header "Deployment Complete"
    echo -e "${GREEN}SD card is ready to boot!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Insert SD card into DE10-Nano"
    echo "  2. Power on the board"
    echo "  3. Connect via SSH: ssh root@<board-ip>"
    echo "     (Default password: root - CHANGE THIS!)"
}

# Run main function
main "$@"
