#!/bin/bash
# ============================================================================
# SD Card Image Creation Script for DE10-Nano
# ============================================================================
# Creates complete bootable SD card image with all components
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

# Configuration
IMAGE_NAME="${IMAGE_NAME:-de10-nano-custom.img}"
IMAGE_SIZE="${IMAGE_SIZE:-4096}"  # MB
IMAGE_FILE="${IMAGE_FILE:-$LINUX_IMAGE_DIR/build/$IMAGE_NAME}"

# Source directories
FPGA_DIR="${FPGA_DIR:-$REPO_ROOT/FPGA}"
KERNEL_DIR="${KERNEL_DIR:-$LINUX_IMAGE_DIR/kernel}"
ROOTFS_DIR="${ROOTFS_DIR:-$LINUX_IMAGE_DIR/rootfs}"

# File locations
PRELOADER_BIN="${PRELOADER_BIN:-$HPS_DIR/preloader/preloader-mkpimage.bin}"
UBOOT_IMG="${UBOOT_IMG:-$HPS_DIR/preloader/uboot-socfpga/u-boot.img}"
KERNEL_IMAGE="${KERNEL_IMAGE:-$KERNEL_DIR/build/arch/arm/boot/zImage}"
KERNEL_DTB="${KERNEL_DTB:-$KERNEL_DIR/build/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb}"
FPGA_DTB="${FPGA_DTB:-$FPGA_DIR/generated/soc_system.dtb}"
FPGA_RBF="${FPGA_RBF:-}"
ROOTFS_TAR="${ROOTFS_TAR:-$ROOTFS_DIR/build/rootfs.tar.gz}"

# Partition sizes (MB)
BOOT_PARTITION_SIZE=100
PRELOADER_OFFSET=2048  # 1MB in 512-byte sectors

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

resolve_first_match() {
    local pattern_to_match="$1"

    shopt -s nullglob
    local matches=( $pattern_to_match )
    shopt -u nullglob

    if [ ${#matches[@]} -gt 0 ]; then
        echo "${matches[0]}"
        return 0
    fi

    return 1
}

resolve_fpga_rbf() {
    if [ -n "$FPGA_RBF" ] && [ -f "$FPGA_RBF" ]; then
        return 0
    fi

    local detected_rbf=""

    detected_rbf="$(resolve_first_match "$FPGA_DIR/build/output_files/"'*.rbf' || true)"
    if [ -n "$detected_rbf" ] && [ -f "$detected_rbf" ]; then
        FPGA_RBF="$detected_rbf"
        return 0
    fi

    detected_rbf="$(resolve_first_match "$REPO_ROOT/build/output_files/"'*.rbf' || true)"
    if [ -n "$detected_rbf" ] && [ -f "$detected_rbf" ]; then
        FPGA_RBF="$detected_rbf"
        return 0
    fi

    return 1
}

resolve_fpga_dtb() {
    if [ -n "$FPGA_DTB" ] && [ -f "$FPGA_DTB" ]; then
        return 0
    fi

    local detected_dtb=""
    detected_dtb="$(resolve_first_match "$FPGA_DIR/generated/"'*.dtb' || true)"
    if [ -n "$detected_dtb" ] && [ -f "$detected_dtb" ]; then
        FPGA_DTB="$detected_dtb"
        return 0
    fi

    return 1
}

check_dependencies() {
    print_step "Checking dependencies..."
    
    local missing=0
    
    for cmd in parted mkfs.vfat mkfs.ext4 losetup dd; do
        if ! command -v $cmd &> /dev/null; then
            print_error "$cmd not found. Install required tools."
            missing=1
        fi
    done
    
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (for loop device and mounting)"
        print_error "Run with: sudo $0"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
    
    echo -e "${GREEN}All dependencies satisfied${NC}"
}

check_files() {
    print_header "Checking Required Build Artifacts"
    
    local missing=0

    resolve_fpga_dtb || true
    resolve_fpga_rbf || true
    
    # Check preloader
    if [ ! -f "$PRELOADER_BIN" ]; then
        print_error "Preloader not found: $PRELOADER_BIN"
        print_error "Build preloader first: cd FPGA && make preloader"
        missing=1
    fi
    
    # Check U-Boot
    if [ ! -f "$UBOOT_IMG" ]; then
        print_error "U-Boot not found: $UBOOT_IMG"
        print_error "Build U-Boot first: cd FPGA && make uboot"
        missing=1
    fi
    
    # Check kernel (try kernel build first, then FPGA DTB)
    if [ ! -f "$KERNEL_IMAGE" ]; then
        if [ -f "$FPGA_DIR/generated/soc_system.dtb" ]; then
            print_error "Kernel image not found: $KERNEL_IMAGE"
            print_error "Build kernel first: cd HPS/linux_image/kernel && make"
            print_error "Or use prebuilt kernel image"
            missing=1
        fi
    fi
    
    # Check device tree (prefer kernel DTB, fallback to FPGA DTB)
    if [ ! -f "$KERNEL_DTB" ] && [ ! -f "$FPGA_DTB" ]; then
        print_error "Device tree not found"
        print_error "Build device tree first: cd FPGA && make dtb"
        missing=1
    fi
    
    # Check FPGA bitstream
    if [ ! -f "$FPGA_RBF" ]; then
        print_error "FPGA RBF not found"
        print_error "Searched:"
        print_error "  - $FPGA_DIR/build/output_files/*.rbf"
        print_error "  - $REPO_ROOT/build/output_files/*.rbf"
        print_error "Build FPGA bitstream first: cd FPGA && make rbf"
        missing=1
    fi
    
    # Check rootfs
    if [ ! -f "$ROOTFS_TAR" ]; then
        print_error "Rootfs tarball not found: $ROOTFS_TAR"
        print_error "Build rootfs first: cd HPS/linux_image/rootfs && sudo make"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
    
    echo -e "${GREEN}All required files found${NC}"
}

create_image_file() {
    print_header "Creating Image File"
    
    print_step "Creating ${IMAGE_SIZE}MB image file: $IMAGE_FILE..."
    
    mkdir -p "$(dirname "$IMAGE_FILE")"
    
    # Create empty image file
    dd if=/dev/zero of="$IMAGE_FILE" bs=1M count=$IMAGE_SIZE status=progress
    
    echo -e "${GREEN}Image file created${NC}"
}

create_partitions() {
    print_header "Creating Partition Table"
    
    print_step "Creating MBR partition table..."
    
    # Create MBR partition table
    parted "$IMAGE_FILE" --script mklabel msdos
    
    # Create boot partition (FAT32, 100MB)
    print_step "Creating boot partition (FAT32, ${BOOT_PARTITION_SIZE}MB)..."
    parted "$IMAGE_FILE" --script mkpart primary fat32 1MiB ${BOOT_PARTITION_SIZE}MiB
    parted "$IMAGE_FILE" --script set 1 boot on
    
    # Create rootfs partition (ext4, remaining space)
    print_step "Creating rootfs partition (ext4)..."
    parted "$IMAGE_FILE" --script mkpart primary ext4 ${BOOT_PARTITION_SIZE}MiB 100%
    
    echo -e "${GREEN}Partition table created${NC}"
}

setup_loop_device() {
    print_step "Setting up loop device..."
    
    # Find available loop device
    LOOP_DEV=$(losetup -f)
    
    # Attach image to loop device
    losetup -P "$LOOP_DEV" "$IMAGE_FILE"
    
    echo "$LOOP_DEV"
}

format_partitions() {
    print_header "Formatting Partitions"
    
    LOOP_DEV=$1
    
    print_step "Formatting boot partition (FAT32)..."
    mkfs.vfat -F 32 -n BOOT "${LOOP_DEV}p1"
    
    print_step "Formatting rootfs partition (ext4)..."
    mkfs.ext4 -F -L rootfs "${LOOP_DEV}p2"
    
    echo -e "${GREEN}Partitions formatted${NC}"
}

copy_boot_files() {
    print_header "Copying Boot Files"
    
    LOOP_DEV=$1
    MOUNT_POINT="/mnt/de10-boot"
    
    print_step "Mounting boot partition..."
    mkdir -p "$MOUNT_POINT"
    mount "${LOOP_DEV}p1" "$MOUNT_POINT"
    
    # Copy U-Boot
    if [ -f "$UBOOT_IMG" ]; then
        print_step "Copying U-Boot..."
        cp "$UBOOT_IMG" "$MOUNT_POINT/u-boot.img"
    fi
    
    # Copy kernel
    if [ -f "$KERNEL_IMAGE" ]; then
        print_step "Copying kernel..."
        cp "$KERNEL_IMAGE" "$MOUNT_POINT/zImage"
    fi
    
    # Copy device tree (prefer kernel DTB, fallback to FPGA DTB)
    if [ -f "$KERNEL_DTB" ]; then
        print_step "Copying device tree (from kernel build)..."
        cp "$KERNEL_DTB" "$MOUNT_POINT/socfpga_cyclone5_de10_nano.dtb"
    elif [ -f "$FPGA_DTB" ]; then
        print_step "Copying device tree (from FPGA build)..."
        cp "$FPGA_DTB" "$MOUNT_POINT/soc_system.dtb"
    fi
    
    # Copy FPGA bitstream
    if [ -f "$FPGA_RBF" ]; then
        print_step "Copying FPGA bitstream..."
        cp "$FPGA_RBF" "$MOUNT_POINT/soc_system.rbf"
    fi
    
    # Create U-Boot boot script
    print_step "Creating U-Boot boot script..."
    cat > "$MOUNT_POINT/boot.script" << 'EOF'
# U-Boot boot script for DE10-Nano
fatload mmc 0:1 ${fpgadata} soc_system.rbf
fpga load 0 ${fpgadata} ${filesize}
setenv fdtimage socfpga_cyclone5_de10_nano.dtb
run bridge_enable_handoff
run mmcload
run mmcboot
EOF
    
    # Compile boot script (if mkimage available)
    if command -v mkimage &> /dev/null; then
        mkimage -A arm -O linux -T script -C none -a 0 -e 0 -n "bootscript" \
            -d "$MOUNT_POINT/boot.script" "$MOUNT_POINT/u-boot.scr" || true
    fi
    
    print_step "Unmounting boot partition..."
    umount "$MOUNT_POINT"
    rmdir "$MOUNT_POINT"
    
    echo -e "${GREEN}Boot files copied${NC}"
}

extract_rootfs() {
    print_header "Extracting Root Filesystem"
    
    LOOP_DEV=$1
    MOUNT_POINT="/mnt/de10-rootfs"
    
    print_step "Mounting rootfs partition..."
    mkdir -p "$MOUNT_POINT"
    mount "${LOOP_DEV}p2" "$MOUNT_POINT"
    
    print_step "Extracting rootfs tarball..."
    tar -xzf "$ROOTFS_TAR" -C "$MOUNT_POINT"
    
    print_step "Unmounting rootfs partition..."
    umount "$MOUNT_POINT"
    rmdir "$MOUNT_POINT"
    
    echo -e "${GREEN}Rootfs extracted${NC}"
}

flash_preloader() {
    print_header "Flashing Preloader"
    
    LOOP_DEV=$1
    
    print_step "Flashing preloader to partition 3 (raw)..."
    # Preloader goes to raw partition 3 (not mounted)
    # Offset: 1MB = 2048 sectors of 512 bytes
    dd if="$PRELOADER_BIN" of="$LOOP_DEV" bs=64k seek=0 conv=notrunc
    
    echo -e "${GREEN}Preloader flashed${NC}"
}

cleanup_loop_device() {
    LOOP_DEV=$1
    
    if [ -n "$LOOP_DEV" ] && [ -b "$LOOP_DEV" ]; then
        print_step "Cleaning up loop device..."
        losetup -d "$LOOP_DEV" || true
    fi
}

# ============================================================================
# Main
# ============================================================================

main() {
    print_header "DE10-Nano SD Card Image Creation"
    
    check_dependencies
    check_files
    
    LOOP_DEV=""
    
    # Trap to cleanup loop device on exit
    trap 'cleanup_loop_device "$LOOP_DEV"' EXIT
    
    create_image_file
    create_partitions
    LOOP_DEV=$(setup_loop_device)
    format_partitions "$LOOP_DEV"
    copy_boot_files "$LOOP_DEV"
    extract_rootfs "$LOOP_DEV"
    flash_preloader "$LOOP_DEV"
    cleanup_loop_device "$LOOP_DEV"
    
    print_header "SD Card Image Creation Complete"
    echo -e "${GREEN}Image file: $IMAGE_FILE${NC}"
    SIZE=$(du -h "$IMAGE_FILE" | cut -f1)
    echo -e "${GREEN}Image size: $SIZE${NC}"
    echo ""
    echo -e "${YELLOW}To write to SD card:${NC}"
    echo "  sudo dd if=$IMAGE_FILE of=/dev/sdX bs=4M status=progress"
    echo ""
    echo -e "${YELLOW}Or use deployment script:${NC}"
    echo "  ./Scripts/deploy_image.sh /dev/sdX"
}

# Run main function
main "$@"
