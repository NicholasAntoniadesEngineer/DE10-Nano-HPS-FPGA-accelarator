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

# ============================================================================
# Device Tree Strategy (Option A: QSys-Generated)
# ============================================================================
# The DTB (Device Tree Blob) describes hardware to the Linux kernel.
#
# Option A (CURRENT - Recommended for custom FPGA designs):
#   - DTB is generated from QSys .sopcinfo using sopc2dts
#   - Accurately describes FPGA peripheral addresses and interrupts
#   - Must be regenerated when FPGA QSys design changes
#   - Location: FPGA/generated/soc_system.dtb
#
# Option B (Alternative - Device Tree Overlays):
#   - Use kernel's generic socfpga DTB as base
#   - Apply device tree overlays at runtime for custom peripherals
#   - More flexible but requires overlay management
#   - To switch: Set DTB_SOURCE=kernel and uncomment kernel DTB below
#
# Configuration:
#   DTB_SOURCE=qsys  : Use QSys-generated DTB (default, Option A)
#   DTB_SOURCE=kernel: Use kernel DTB (Option B)
# ============================================================================
DTB_SOURCE="${DTB_SOURCE:-qsys}"

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

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
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

detect_wsl() {
    # Detect if running in WSL
    if grep -qi microsoft /proc/version 2>/dev/null; then
        return 0  # WSL detected
    fi
    return 1  # Not WSL
}

check_dependencies() {
    print_header "Checking Dependencies"
    
    local missing=0
    local warnings=0
    
    # Required tools
    echo "Checking required tools..."
    for cmd in parted mkfs.vfat mkfs.ext4 losetup dd sync; do
        if command -v $cmd &> /dev/null; then
            echo "  [OK] $cmd found: $(which $cmd)"
        else
            print_error "$cmd not found. Install required tools."
            missing=1
        fi
    done
    
    # Optional but helpful tools for WSL
    echo ""
    echo "Checking WSL compatibility tools..."
    for cmd in partprobe partx udevadm; do
        if command -v $cmd &> /dev/null; then
            echo "  [OK] $cmd found: $(which $cmd)"
        else
            echo "  [WARN] $cmd not found (optional, may affect WSL compatibility)"
            warnings=1
        fi
    done
    
    # Check for root
    echo ""
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (for loop device and mounting)"
        print_error "Run with: sudo $0"
        missing=1
    else
        echo "  [OK] Running as root (EUID=$EUID)"
    fi
    
    # Check WSL environment
    echo ""
    if detect_wsl; then
        echo "  [INFO] WSL environment detected"
        echo "  [INFO] Using enhanced partition handling for WSL compatibility"
    else
        echo "  [INFO] Native Linux environment detected"
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Missing required dependencies - cannot continue"
        exit 1
    fi
    
    if [ $warnings -eq 1 ]; then
        print_warning "Some optional tools missing - script will use fallback methods"
    fi
    
    echo ""
    echo -e "${GREEN}All required dependencies satisfied${NC}"
}

check_files() {
    print_header "Checking Required Build Artifacts"
    
    local missing=0

    resolve_fpga_dtb || true
    resolve_fpga_rbf || true
    
    # Check preloader
    if [ -f "$PRELOADER_BIN" ]; then
        echo "✓ Preloader found: $PRELOADER_BIN ($(du -h "$PRELOADER_BIN" | cut -f1))"
    else
        print_error "Preloader not found: $PRELOADER_BIN"
        print_error "Build preloader first: cd FPGA && make preloader"
        missing=1
    fi
    
    # Check U-Boot
    if [ -f "$UBOOT_IMG" ]; then
        echo "✓ U-Boot found: $UBOOT_IMG ($(du -h "$UBOOT_IMG" | cut -f1))"
    else
        print_error "U-Boot not found: $UBOOT_IMG"
        print_error "Build U-Boot first: cd FPGA && make uboot"
        missing=1
    fi
    
    # Check kernel image (required)
    if [ -f "$KERNEL_IMAGE" ]; then
        echo "✓ Kernel image found: $KERNEL_IMAGE"
    else
        print_error "Kernel image not found: $KERNEL_IMAGE"
        print_error "Build kernel first: cd HPS/linux_image/kernel && make"
        missing=1
    fi
    
    # Check device tree based on configured strategy
    echo ""
    echo "Device Tree Strategy: $DTB_SOURCE"
    if [ "$DTB_SOURCE" = "qsys" ]; then
        # Option A: QSys-generated DTB (recommended)
        if [ -f "$FPGA_DTB" ]; then
            echo "[Option A] Using QSys-generated DTB: $FPGA_DTB"
            echo "  This DTB describes FPGA peripherals from QSys design"
            echo "  Rebuild with: cd FPGA && make dtb"
        elif [ -f "$KERNEL_DTB" ]; then
            print_warning "QSys DTB not found, falling back to kernel DTB"
            print_warning "Kernel DTB may not include custom FPGA peripherals"
            echo "  QSys DTB expected at: $FPGA_DTB"
            echo "  Build with: cd FPGA && make dtb"
        else
            print_warning "No device tree blob (DTB) found"
            print_warning "Build QSys DTB with: cd FPGA && make qsys-generate dtb"
            echo "Continuing without DTB (kernel may have built-in support)..."
        fi
    else
        # Option B: Kernel DTB with overlays
        if [ -f "$KERNEL_DTB" ]; then
            echo "[Option B] Using kernel DTB: $KERNEL_DTB"
            echo "  For custom FPGA peripherals, use device tree overlays"
            echo "  Load overlays at runtime: dtoverlay <overlay.dtbo>"
        elif [ -f "$FPGA_DTB" ]; then
            print_warning "Kernel DTB not found, falling back to QSys DTB"
            echo "  Kernel DTB expected at: $KERNEL_DTB"
        else
            print_warning "No device tree blob (DTB) found"
            echo "Continuing without DTB..."
        fi
    fi
    echo ""
    
    # Check FPGA bitstream
    if [ -f "$FPGA_RBF" ]; then
        echo "✓ FPGA bitstream found: $FPGA_RBF ($(du -h "$FPGA_RBF" | cut -f1))"
    else
        print_error "FPGA RBF not found"
        print_error "Searched:"
        print_error "  - $FPGA_DIR/build/output_files/*.rbf"
        print_error "  - $REPO_ROOT/build/output_files/*.rbf"
        print_error "Build FPGA bitstream first: cd FPGA && make rbf"
        missing=1
    fi
    
    # Check rootfs
    if [ -f "$ROOTFS_TAR" ]; then
        echo "✓ Rootfs tarball found: $ROOTFS_TAR ($(du -h "$ROOTFS_TAR" | cut -f1))"
    else
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

wait_for_partition_devices() {
    local loop_device="$1"
    local max_attempts=10
    local attempt=0
    
    echo "Waiting for partition devices to appear..." >&2
    
    while [ $attempt -lt $max_attempts ]; do
        if [ -b "${loop_device}p1" ] && [ -b "${loop_device}p2" ]; then
            echo "Partition devices found after $attempt attempts" >&2
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "  Attempt $attempt/$max_attempts - waiting for ${loop_device}p1 and ${loop_device}p2..." >&2
        
        # Try different methods to trigger partition scan
        partprobe "$loop_device" 2>/dev/null || true
        partx -u "$loop_device" 2>/dev/null || true
        
        sleep 1
    done
    
    return 1
}

setup_loop_device() {
    # NOTE: All logging goes to stderr (&2), only the final device path goes to stdout
    
    echo "Setting up loop device..." >&2
    
    local is_wsl=0
    if detect_wsl; then
        is_wsl=1
        echo "WSL environment detected - using enhanced partition handling" >&2
    fi

    # Find available loop device
    local loop_dev=$(losetup -f)
    echo "Using loop device: $loop_dev" >&2

    # Attach image to loop device with partition scanning enabled
    echo "Attaching image to loop device..." >&2
    losetup -P "$loop_dev" "$IMAGE_FILE"
    
    # Give the kernel time to process
    sync
    sleep 1
    
    # Try to force partition table re-read using multiple methods
    echo "Triggering partition table scan..." >&2
    partprobe "$loop_dev" 2>/dev/null || true
    partx -a "$loop_dev" 2>/dev/null || true
    
    # Wait for udev to process
    udevadm settle 2>/dev/null || sleep 2
    
    # Check if partition devices exist
    if wait_for_partition_devices "$loop_dev"; then
        echo "Standard partition devices available: ${loop_dev}p1, ${loop_dev}p2" >&2
        # Return ONLY the device path to stdout
        echo "$loop_dev"
        return 0
    fi
    
    # If we're here, partition devices didn't appear
    # Use offset-based loop device approach
    echo "Partition devices not available - using offset-based approach..." >&2
    echo "This is common in WSL environments" >&2
    
    # Detach the main loop device first (we'll re-attach it for preloader)
    losetup -d "$loop_dev" 2>/dev/null || true
    
    # Get fresh loop devices for offset-based access
    loop_dev=$(losetup -f)
    
    # Re-attach main device (for preloader flashing)
    losetup "$loop_dev" "$IMAGE_FILE"
    
    # Calculate partition offsets and sizes based on parted layout:
    # Partition 1 (boot): 1MiB to BOOT_PARTITION_SIZE MiB (FAT32)
    # Partition 2 (rootfs): BOOT_PARTITION_SIZE MiB to end (ext4)
    
    local boot_offset_bytes=$((1 * 1024 * 1024))  # 1MiB start
    local boot_size_bytes=$(((BOOT_PARTITION_SIZE - 1) * 1024 * 1024))  # Size = (100-1) MiB
    local rootfs_offset_bytes=$((BOOT_PARTITION_SIZE * 1024 * 1024))  # 100MiB start
    
    echo "Boot partition: offset=${boot_offset_bytes} bytes, size=${boot_size_bytes} bytes" >&2
    echo "Rootfs partition: offset=${rootfs_offset_bytes} bytes" >&2
    
    # Set up loop device for boot partition
    local loop_dev_boot=$(losetup -f)
    echo "Setting up boot partition loop device: $loop_dev_boot" >&2
    losetup -o "$boot_offset_bytes" --sizelimit "$boot_size_bytes" "$loop_dev_boot" "$IMAGE_FILE"
    
    # Set up loop device for rootfs partition
    local loop_dev_rootfs=$(losetup -f)
    echo "Setting up rootfs partition loop device: $loop_dev_rootfs" >&2
    losetup -o "$rootfs_offset_bytes" "$loop_dev_rootfs" "$IMAGE_FILE"
    
    # Verify the loop devices are set up
    echo "Verifying offset-based loop devices..." >&2
    if [ ! -b "$loop_dev_boot" ]; then
        print_error "Failed to set up boot partition loop device"
        return 1
    fi
    if [ ! -b "$loop_dev_rootfs" ]; then
        print_error "Failed to set up rootfs partition loop device"
        return 1
    fi
    
    echo "Offset-based loop devices configured successfully" >&2
    echo "  Main device: $loop_dev" >&2
    echo "  Boot partition: $loop_dev_boot" >&2
    echo "  Rootfs partition: $loop_dev_rootfs" >&2
    
    # Return ONLY the device string to stdout (format: main:boot:rootfs)
    echo "${loop_dev}:${loop_dev_boot}:${loop_dev_rootfs}"
}

format_partitions() {
    print_header "Formatting Partitions"

    LOOP_DEVICES=$1

    # Check if we have separate loop devices (format: main:boot:rootfs)
    if [[ "$LOOP_DEVICES" == *:* ]]; then
        IFS=':' read -r LOOP_DEV LOOP_DEV_BOOT LOOP_DEV_ROOTFS <<< "$LOOP_DEVICES"

        print_step "Formatting boot partition (FAT32)..."
        mkfs.vfat -F 32 -n BOOT "$LOOP_DEV_BOOT"

        print_step "Formatting rootfs partition (ext4)..."
        mkfs.ext4 -F -L rootfs "$LOOP_DEV_ROOTFS"
    else
        # Original partition device approach
        if [ ! -b "${LOOP_DEVICES}p1" ]; then
            echo -e "${RED}ERROR: Boot partition device ${LOOP_DEVICES}p1 not found${NC}" >&2
            echo -e "${YELLOW}Available devices:${NC}" >&2
            ls -la "${LOOP_DEVICES}"* 2>/dev/null || true >&2
            return 1
        fi

        print_step "Formatting boot partition (FAT32)..."
        mkfs.vfat -F 32 -n BOOT "${LOOP_DEVICES}p1"

        print_step "Formatting rootfs partition (ext4)..."
        mkfs.ext4 -F -L rootfs "${LOOP_DEVICES}p2"
    fi

    echo -e "${GREEN}Partitions formatted${NC}"
}

copy_boot_files() {
    print_header "Copying Boot Files"

    LOOP_DEVICES=$1
    MOUNT_POINT="/mnt/de10-boot"

    # Check if we have separate loop devices
    if [[ "$LOOP_DEVICES" == *:* ]]; then
        IFS=':' read -r LOOP_DEV LOOP_DEV_BOOT LOOP_DEV_ROOTFS <<< "$LOOP_DEVICES"
        BOOT_DEVICE="$LOOP_DEV_BOOT"
    else
        BOOT_DEVICE="${LOOP_DEVICES}p1"
    fi

    print_step "Mounting boot partition..."
    mkdir -p "$MOUNT_POINT"
    mount "$BOOT_DEVICE" "$MOUNT_POINT"
    
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
    
    # Copy device tree based on strategy (Option A or B)
    # ============================================================================
    # DTB Selection Logic:
    #   Option A (DTB_SOURCE=qsys): Prefer QSys-generated DTB
    #     - Contains accurate FPGA peripheral descriptions
    #     - Required when FPGA design has custom peripherals
    #   
    #   Option B (DTB_SOURCE=kernel): Prefer kernel DTB
    #     - Generic socfpga DTB from kernel source
    #     - Use with device tree overlays for custom peripherals
    # ============================================================================
    DTB_COPIED=0
    if [ "$DTB_SOURCE" = "qsys" ]; then
        # Option A: Prefer QSys-generated DTB
        if [ -f "$FPGA_DTB" ]; then
            print_step "Copying device tree [Option A: QSys-generated]..."
            cp "$FPGA_DTB" "$MOUNT_POINT/soc_system.dtb"
            echo "  Source: $FPGA_DTB"
            echo "  Destination: soc_system.dtb"
            DTB_COPIED=1
        elif [ -f "$KERNEL_DTB" ]; then
            print_step "Copying device tree [Fallback: kernel]..."
            print_warning "QSys DTB not found, using kernel DTB"
            cp "$KERNEL_DTB" "$MOUNT_POINT/socfpga_cyclone5_de10_nano.dtb"
            echo "  Source: $KERNEL_DTB"
            DTB_COPIED=1
        fi
    else
        # Option B: Prefer kernel DTB
        if [ -f "$KERNEL_DTB" ]; then
            print_step "Copying device tree [Option B: kernel]..."
            cp "$KERNEL_DTB" "$MOUNT_POINT/socfpga_cyclone5_de10_nano.dtb"
            echo "  Source: $KERNEL_DTB"
            echo "  Note: Use device tree overlays for custom FPGA peripherals"
            DTB_COPIED=1
        elif [ -f "$FPGA_DTB" ]; then
            print_step "Copying device tree [Fallback: QSys]..."
            print_warning "Kernel DTB not found, using QSys DTB"
            cp "$FPGA_DTB" "$MOUNT_POINT/soc_system.dtb"
            echo "  Source: $FPGA_DTB"
            DTB_COPIED=1
        fi
    fi
    
    if [ $DTB_COPIED -eq 0 ]; then
        print_warning "No DTB copied - kernel must have built-in device tree"
    fi
    
    # Copy FPGA bitstream
    if [ -f "$FPGA_RBF" ]; then
        print_step "Copying FPGA bitstream..."
        cp "$FPGA_RBF" "$MOUNT_POINT/soc_system.rbf"
    fi
    
    # Create U-Boot boot script with correct DTB filename
    print_step "Creating U-Boot boot script..."
    
    # Determine DTB filename based on what was copied
    if [ "$DTB_SOURCE" = "qsys" ] && [ -f "$FPGA_DTB" ]; then
        DTB_FILENAME="soc_system.dtb"
    else
        DTB_FILENAME="socfpga_cyclone5_de10_nano.dtb"
    fi
    
    cat > "$MOUNT_POINT/boot.script" << EOF
# U-Boot boot script for DE10-Nano
# DTB Strategy: ${DTB_SOURCE}
# Generated: $(date)

# Load FPGA bitstream
fatload mmc 0:1 \${fpgadata} soc_system.rbf
fpga load 0 \${fpgadata} \${filesize}

# Set device tree image
setenv fdtimage ${DTB_FILENAME}

# Enable HPS-FPGA bridges and boot Linux
run bridge_enable_handoff
run mmcload
run mmcboot
EOF
    echo "  U-Boot configured to use DTB: $DTB_FILENAME"
    
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

    LOOP_DEVICES=$1
    MOUNT_POINT="/mnt/de10-rootfs"

    # Check if we have separate loop devices
    if [[ "$LOOP_DEVICES" == *:* ]]; then
        IFS=':' read -r LOOP_DEV LOOP_DEV_BOOT LOOP_DEV_ROOTFS <<< "$LOOP_DEVICES"
        ROOTFS_DEVICE="$LOOP_DEV_ROOTFS"
    else
        ROOTFS_DEVICE="${LOOP_DEVICES}p2"
    fi

    print_step "Mounting rootfs partition..."
    mkdir -p "$MOUNT_POINT"
    mount "$ROOTFS_DEVICE" "$MOUNT_POINT"
    
    print_step "Extracting rootfs tarball..."
    tar -xzf "$ROOTFS_TAR" -C "$MOUNT_POINT"
    
    print_step "Unmounting rootfs partition..."
    umount "$MOUNT_POINT"
    rmdir "$MOUNT_POINT"
    
    echo -e "${GREEN}Rootfs extracted${NC}"
}

flash_preloader() {
    print_header "Flashing Preloader"
    
    LOOP_DEVICES=$1
    
    # Extract main loop device (handles both single device and multi-device format)
    if [[ "$LOOP_DEVICES" == *:* ]]; then
        IFS=':' read -r MAIN_LOOP_DEV BOOT_DEV ROOTFS_DEV <<< "$LOOP_DEVICES"
    else
        MAIN_LOOP_DEV="$LOOP_DEVICES"
    fi
    
    print_step "Flashing preloader to image (raw area before first partition)..."
    echo "Target device: $MAIN_LOOP_DEV"
    echo "Preloader binary: $PRELOADER_BIN"
    echo "Preloader size: $(du -h "$PRELOADER_BIN" | cut -f1)"
    
    # The preloader goes to the raw area at the beginning of the disk
    # This is the MBR boot code area (first 512 bytes is MBR, preloader after)
    # For Cyclone V, preloader is typically at sector 0
    dd if="$PRELOADER_BIN" of="$MAIN_LOOP_DEV" bs=64k seek=0 conv=notrunc status=progress
    
    # Sync to ensure data is written
    sync
    
    echo -e "${GREEN}Preloader flashed successfully${NC}"
}

cleanup_loop_device() {
    LOOP_DEVICES=$1

    # Check if we have separate loop devices (format: main:boot:rootfs)
    if [[ "$LOOP_DEVICES" == *:* ]]; then
        IFS=':' read -r LOOP_DEV LOOP_DEV_BOOT LOOP_DEV_ROOTFS <<< "$LOOP_DEVICES"

        # Clean up all loop devices
        for dev in "$LOOP_DEV_ROOTFS" "$LOOP_DEV_BOOT" "$LOOP_DEV"; do
            if [ -n "$dev" ] && [ -b "$dev" ]; then
                print_step "Cleaning up loop device $dev..."
                losetup -d "$dev" || true
            fi
        done
    else
        # Single loop device
        if [ -n "$LOOP_DEVICES" ] && [ -b "$LOOP_DEVICES" ]; then
            print_step "Cleaning up loop device..."
            losetup -d "$LOOP_DEVICES" || true
        fi
    fi
}

# ============================================================================
# Main
# ============================================================================

cleanup_on_exit() {
    local exit_code=$?
    
    if [ -n "$LOOP_DEV" ]; then
        echo ""
        echo "Cleaning up loop devices..."
        cleanup_loop_device "$LOOP_DEV"
    fi
    
    # Unmount any leftover mount points
    for mp in /mnt/de10-boot /mnt/de10-rootfs; do
        if mountpoint -q "$mp" 2>/dev/null; then
            echo "Unmounting $mp..."
            umount "$mp" 2>/dev/null || true
            rmdir "$mp" 2>/dev/null || true
        fi
    done
    
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}Script exited with error code: $exit_code${NC}"
    fi
}

main() {
    local start_time=$(date +%s)
    
    print_header "DE10-Nano SD Card Image Creation"
    echo "Started at: $(date)"
    echo "Script directory: $SCRIPT_DIR"
    echo "Repository root: $REPO_ROOT"
    echo ""
    
    check_dependencies
    check_files
    
    LOOP_DEV=""
    
    # Trap to cleanup loop device on exit (normal or error)
    trap cleanup_on_exit EXIT
    
    echo ""
    echo "=== Step 1/6: Creating image file ==="
    create_image_file
    
    echo ""
    echo "=== Step 2/6: Creating partitions ==="
    create_partitions
    
    echo ""
    echo "=== Step 3/6: Setting up loop devices ==="
    LOOP_DEV=$(setup_loop_device)
    echo ""
    echo "Loop device result: $LOOP_DEV"
    
    # Validate that we got a valid device path
    if [ -z "$LOOP_DEV" ]; then
        print_error "Failed to set up loop device - no device path returned"
        exit 1
    fi
    
    echo ""
    echo "=== Step 4/6: Formatting partitions ==="
    format_partitions "$LOOP_DEV"
    
    echo ""
    echo "=== Step 5/6: Copying boot files ==="
    copy_boot_files "$LOOP_DEV"
    
    echo ""
    echo "=== Step 6/6: Extracting root filesystem ==="
    extract_rootfs "$LOOP_DEV"
    
    echo ""
    echo "=== Flashing preloader ==="
    flash_preloader "$LOOP_DEV"
    
    echo ""
    echo "=== Finalizing ==="
    # Sync all data
    sync
    
    # Clean up loop devices before final report
    cleanup_loop_device "$LOOP_DEV"
    LOOP_DEV=""  # Clear so trap doesn't try to clean up again
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    print_header "SD Card Image Creation Complete"
    echo -e "${GREEN}SUCCESS!${NC}"
    echo ""
    echo "Image Details:"
    echo "  File: $IMAGE_FILE"
    SIZE=$(du -h "$IMAGE_FILE" | cut -f1)
    echo "  Size: $SIZE"
    echo "  Duration: ${minutes}m ${seconds}s"
    echo ""
    echo -e "${YELLOW}To write to SD card:${NC}"
    echo "  sudo dd if=$IMAGE_FILE of=/dev/sdX bs=4M status=progress conv=fsync"
    echo ""
    echo -e "${YELLOW}Or use deployment script:${NC}"
    echo "  ./Scripts/deploy_image.sh /dev/sdX"
    echo ""
    echo "NOTE: Replace /dev/sdX with your actual SD card device"
    echo "      Use 'lsblk' to identify your SD card"
    
    return 0
}

# Run main function
main "$@"
