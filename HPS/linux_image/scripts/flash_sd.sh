#!/bin/bash
# ============================================================================
# SD Card Flash Script for DE10-Nano
# ============================================================================
# Flashes SD card image (compressed or uncompressed) to SD card
# Supports: .img, .img.xz, .img.gz
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINUX_IMAGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$LINUX_IMAGE_DIR/build"

# Default image (prefer compressed)
if [ -f "$BUILD_DIR/de10-nano-custom.img.xz" ]; then
    DEFAULT_IMAGE="$BUILD_DIR/de10-nano-custom.img.xz"
elif [ -f "$BUILD_DIR/de10-nano-custom.img" ]; then
    DEFAULT_IMAGE="$BUILD_DIR/de10-nano-custom.img"
else
    DEFAULT_IMAGE=""
fi

usage() {
    cat << EOF
Usage: $0 <SD_CARD_DEVICE> [OPTIONS]

Flashes DE10-Nano SD card image to an SD card.
Supports compressed (.img.xz, .img.gz) and uncompressed (.img) images.

Arguments:
  SD_CARD_DEVICE    SD card device (e.g., /dev/sdb, /dev/disk2, /dev/mmcblk0)

Options:
  -i, --image FILE  Image file path (default: auto-detect in build/)
  -f, --force       Skip confirmation prompts
  -l, --list        List available SD card devices
  -h, --help        Show this help message

Examples:
  $0 /dev/sdb                           # Flash to /dev/sdb (Linux)
  $0 /dev/disk2                         # Flash to /dev/disk2 (macOS)
  $0 /dev/sdb -i custom.img.xz          # Flash specific image
  $0 --list                             # List available devices

Compression:
  The script automatically handles compressed images:
  - .img.xz: Decompressed on-the-fly with xz (no extra disk space needed)
  - .img.gz: Decompressed on-the-fly with gzip
  - .img:    Written directly

WARNING: This will OVERWRITE ALL DATA on the target device!
EOF
}

list_devices() {
    echo -e "${CYAN}Available block devices:${NC}"
    echo ""

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "Device           Size       Type"
        echo "----------------------------------------------"
        diskutil list | grep -E "^/dev/disk|external|internal" | head -20
        echo ""
        echo -e "${YELLOW}Tip: Use 'diskutil list' for more details${NC}"
        echo -e "${YELLOW}     SD cards are usually /dev/disk2 or higher${NC}"
    else
        # Linux
        echo "Device           Size       Model"
        echo "----------------------------------------------"
        lsblk -d -o NAME,SIZE,MODEL | grep -v "loop" | tail -n +2
        echo ""
        echo -e "${YELLOW}Tip: Use 'lsblk' for partition details${NC}"
        echo -e "${YELLOW}     SD cards are usually /dev/sdb, /dev/sdc, or /dev/mmcblk0${NC}"
    fi
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}ERROR: This script must be run as root${NC}"
        echo "Run with: sudo $0 $*"
        exit 1
    fi
}

check_image() {
    local image="$1"

    if [ ! -f "$image" ]; then
        echo -e "${RED}ERROR: Image file not found: $image${NC}"
        echo ""
        echo "Available images in build directory:"
        ls -lh "$BUILD_DIR"/*.img* 2>/dev/null || echo "  (none found)"
        echo ""
        echo "Build an image with: make sd-image"
        exit 1
    fi

    local size=$(du -h "$image" | cut -f1)
    echo -e "${GREEN}Image: $image${NC}"
    echo -e "${GREEN}Size:  $size${NC}"

    # Detect compression
    case "$image" in
        *.img.xz)
            echo -e "${CYAN}Format: xz compressed${NC}"
            if ! command -v xz &> /dev/null; then
                echo -e "${RED}ERROR: xz not found. Install with: brew install xz (macOS) or apt install xz-utils (Linux)${NC}"
                exit 1
            fi
            ;;
        *.img.gz)
            echo -e "${CYAN}Format: gzip compressed${NC}"
            ;;
        *.img)
            echo -e "${CYAN}Format: uncompressed${NC}"
            ;;
        *)
            echo -e "${YELLOW}WARNING: Unknown format, treating as uncompressed${NC}"
            ;;
    esac
}

verify_device() {
    local device="$1"

    if [ ! -b "$device" ]; then
        echo -e "${RED}ERROR: Device not found or not a block device: $device${NC}"
        echo ""
        echo "Use '$0 --list' to see available devices"
        exit 1
    fi

    # Get device info
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        local info=$(diskutil info "$device" 2>/dev/null | grep -E "Device|Size|Media Name" | head -5)
        echo -e "${CYAN}Device information:${NC}"
        echo "$info"
    else
        # Linux
        local size=$(lsblk -b -d -o SIZE -n "$device" 2>/dev/null)
        local size_gb=$((size / 1024 / 1024 / 1024))
        local model=$(lsblk -d -o MODEL -n "$device" 2>/dev/null | xargs)
        echo -e "${CYAN}Device: $device${NC}"
        echo -e "${CYAN}Size:   ${size_gb}GB${NC}"
        echo -e "${CYAN}Model:  ${model:-unknown}${NC}"
    fi

    # Check if mounted
    if mount | grep -q "$device"; then
        echo ""
        echo -e "${YELLOW}WARNING: Device has mounted partitions${NC}"

        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${YELLOW}Unmounting with diskutil...${NC}"
            diskutil unmountDisk "$device" || true
        else
            echo -e "${YELLOW}Unmounting partitions...${NC}"
            for part in $(lsblk -ln -o NAME "$device" 2>/dev/null | tail -n +2); do
                umount "/dev/$part" 2>/dev/null || true
            done
        fi
    fi
}

confirm_flash() {
    local device="$1"
    local image="$2"

    if [ "$FORCE" = "yes" ]; then
        return 0
    fi

    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                        WARNING                             ║${NC}"
    echo -e "${RED}║   This will PERMANENTLY ERASE all data on $device    ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Type 'yes' to confirm: ${NC}"
    read -r response

    if [ "$response" != "yes" ]; then
        echo "Flash cancelled"
        exit 0
    fi
}

flash_image() {
    local device="$1"
    local image="$2"

    echo ""
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}Flashing image to SD card${NC}"
    echo -e "${GREEN}===========================================${NC}"

    local start_time=$(date +%s)

    # Determine raw device for macOS
    local raw_device="$device"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Use raw device for faster writes on macOS
        raw_device="/dev/r${device#/dev/}"
        echo -e "${CYAN}Using raw device: $raw_device${NC}"
    fi

    echo -e "${YELLOW}Writing image... (this may take several minutes)${NC}"
    echo ""

    case "$image" in
        *.img.xz)
            # Decompress and write in one step
            xz -dc "$image" | dd of="$raw_device" bs=4M status=progress conv=fsync
            ;;
        *.img.gz)
            # Decompress and write in one step
            gzip -dc "$image" | dd of="$raw_device" bs=4M status=progress conv=fsync
            ;;
        *)
            # Write directly
            dd if="$image" of="$raw_device" bs=4M status=progress conv=fsync
            ;;
    esac

    # Sync
    echo ""
    echo -e "${YELLOW}Syncing...${NC}"
    sync

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    echo ""
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}Flash completed in ${minutes}m ${seconds}s${NC}"
    echo -e "${GREEN}===========================================${NC}"

    # Eject on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo ""
        echo -e "${YELLOW}Ejecting disk...${NC}"
        diskutil eject "$device" || true
    fi

    echo ""
    echo -e "${GREEN}SD card is ready!${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "  1. Insert SD card into DE10-Nano"
    echo "  2. Set MSEL switches for SD card boot (see board documentation)"
    echo "  3. Power on the board"
    echo "  4. Connect via serial: screen /dev/ttyUSB0 115200"
    echo "  5. Or SSH after boot: ssh root@<board-ip> (password: root)"
    echo ""
    echo -e "${YELLOW}Important: Change the default root password after first login!${NC}"
}

# ============================================================================
# Main
# ============================================================================

main() {
    local device=""
    local image="$DEFAULT_IMAGE"
    FORCE="no"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--image)
                image="$2"
                shift 2
                ;;
            -f|--force)
                FORCE="yes"
                shift
                ;;
            -l|--list)
                list_devices
                exit 0
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
                echo -e "${RED}ERROR: Unknown option: $1${NC}"
                echo ""
                usage
                exit 1
                ;;
        esac
    done

    # Check device specified
    if [ -z "$device" ]; then
        echo -e "${RED}ERROR: SD card device not specified${NC}"
        echo ""
        usage
        exit 1
    fi

    # Check image specified/found
    if [ -z "$image" ]; then
        echo -e "${RED}ERROR: No image file found or specified${NC}"
        echo ""
        echo "Build an image with: make sd-image"
        echo "Or specify with: $0 $device -i /path/to/image.img"
        exit 1
    fi

    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}DE10-Nano SD Card Flash Tool${NC}"
    echo -e "${GREEN}===========================================${NC}"
    echo ""

    check_root "$@"
    check_image "$image"
    echo ""
    verify_device "$device"
    confirm_flash "$device" "$image"
    flash_image "$device" "$image"
}

main "$@"
