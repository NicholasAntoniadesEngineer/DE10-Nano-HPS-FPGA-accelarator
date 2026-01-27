#!/bin/bash
# ============================================================================
# SD Card Image Creation Script for DE10-Nano (No Loop Devices)
# ============================================================================
# Creates bootable SD card image without using loop devices
# Compatible with Docker on macOS
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
HPS_DIR="$(cd "$LINUX_IMAGE_DIR/.." && pwd)"
REPO_ROOT="$(cd "$HPS_DIR/.." && pwd)"

# Configuration
IMAGE_NAME="${IMAGE_NAME:-de10-nano-custom.img}"
IMAGE_SIZE_MB="${IMAGE_SIZE:-4096}"
IMAGE_FILE="${IMAGE_FILE:-$LINUX_IMAGE_DIR/build/$IMAGE_NAME}"
BUILD_DIR="$(dirname "$IMAGE_FILE")"
TEMP_DIR="$BUILD_DIR/sdimage_tmp"

# Source files
BOOTLOADER_BUILD_DIR="${LINUX_IMAGE_DIR}/bootloader/build"
KERNEL_DIR="${KERNEL_DIR:-$LINUX_IMAGE_DIR/kernel}"
ROOTFS_DIR="${ROOTFS_DIR:-$LINUX_IMAGE_DIR/rootfs}"
FPGA_DIR="${FPGA_DIR:-$REPO_ROOT/FPGA}"

# File locations
PRELOADER_BIN="${PRELOADER_BIN:-$BOOTLOADER_BUILD_DIR/u-boot-with-spl.sfp}"
UBOOT_IMG="${UBOOT_IMG:-$BOOTLOADER_BUILD_DIR/u-boot.img}"
KERNEL_IMAGE="${KERNEL_IMAGE:-$KERNEL_DIR/build/arch/arm/boot/zImage}"
FPGA_RBF="${FPGA_RBF:-$REPO_ROOT/build/output_files/DE10_NANO_SoC_GHRD.rbf}"

# Rootfs tarball - check multiple locations
if [ -z "$ROOTFS_TAR" ]; then
    if [ -f "/var/lib/rootfs-build/build/rootfs.tar.xz" ]; then
        ROOTFS_TAR="/var/lib/rootfs-build/build/rootfs.tar.xz"
    else
        ROOTFS_TAR="$ROOTFS_DIR/build/rootfs.tar.xz"
    fi
fi

# Partition configuration (in MB)
BOOT_SIZE_MB=100
BOOT_START_MB=1
ROOTFS_START_MB=$((BOOT_START_MB + BOOT_SIZE_MB))
ROOTFS_END_MB=$IMAGE_SIZE_MB

# Convert to sectors (512 bytes)
BOOT_START_SECTOR=$((BOOT_START_MB * 2048))
BOOT_SIZE_SECTOR=$((BOOT_SIZE_MB * 2048))
ROOTFS_START_SECTOR=$((ROOTFS_START_MB * 2048))

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}DE10-Nano SD Image Creation (No Loop Devices)${NC}"
echo -e "${GREEN}===========================================${NC}"
echo "Image: $IMAGE_FILE"
echo "Size: ${IMAGE_SIZE_MB}MB"
echo "Boot partition: ${BOOT_SIZE_MB}MB at ${BOOT_START_MB}MB"
echo "Rootfs partition: $((ROOTFS_END_MB - ROOTFS_START_MB))MB at ${ROOTFS_START_MB}MB"
echo ""

# Check dependencies
echo -e "${CYAN}Checking dependencies...${NC}"
for cmd in sfdisk dd mkfs.vfat mkfs.ext4 mcopy mmd tar; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}ERROR: $cmd not found${NC}"
        exit 1
    fi
done
echo -e "${GREEN}All dependencies found${NC}"
echo ""

# Check required files
echo -e "${CYAN}Checking required files...${NC}"
for file in "$PRELOADER_BIN" "$KERNEL_IMAGE" "$FPGA_RBF" "$ROOTFS_TAR"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}ERROR: Required file not found: $file${NC}"
        exit 1
    fi
    echo "✓ $(basename $file): $(du -h "$file" | cut -f1)"
done
echo ""

# Create build and temp directories
mkdir -p "$BUILD_DIR" "$TEMP_DIR"

# Step 1: Create empty image
echo -e "${CYAN}[1/7] Creating ${IMAGE_SIZE_MB}MB image file...${NC}"
dd if=/dev/zero of="$IMAGE_FILE" bs=1M count=$IMAGE_SIZE_MB status=progress
echo -e "${GREEN}✓ Image file created${NC}"
echo ""

# Step 2: Create partition table with sfdisk
echo -e "${CYAN}[2/7] Creating partition table...${NC}"
sfdisk "$IMAGE_FILE" << EOF
label: dos
start=${BOOT_START_SECTOR}, size=${BOOT_SIZE_SECTOR}, type=c, bootable
start=${ROOTFS_START_SECTOR}, type=83
EOF
echo -e "${GREEN}✓ Partition table created${NC}"
echo ""

# Step 3: Create and populate FAT32 boot partition
echo -e "${CYAN}[3/7] Creating boot partition (FAT32)...${NC}"
BOOT_IMG="$TEMP_DIR/boot.img"
dd if=/dev/zero of="$BOOT_IMG" bs=1M count=$BOOT_SIZE_MB
mkfs.vfat -F 32 -n "BOOT" "$BOOT_IMG"

# Copy files to FAT32 using mtools (no mounting needed)
echo "Copying boot files using mtools..."
if [ -f "$UBOOT_IMG" ]; then
    mcopy -i "$BOOT_IMG" "$UBOOT_IMG" ::u-boot.img
fi
mcopy -i "$BOOT_IMG" "$KERNEL_IMAGE" ::zImage
mcopy -i "$BOOT_IMG" "$FPGA_RBF" ::DE10_NANO_SoC_GHRD.rbf

# Create boot script
cat > "$TEMP_DIR/boot.script" << 'BOOTSCRIPT'
# U-Boot boot script for DE10-Nano
echo "Loading FPGA bitstream..."
fatload mmc 0:1 ${loadaddr} DE10_NANO_SoC_GHRD.rbf
fpga load 0 ${loadaddr} ${filesize}

echo "Loading kernel..."
fatload mmc 0:1 ${loadaddr} zImage
setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p2 rw rootwait

echo "Booting kernel..."
bootz ${loadaddr}
BOOTSCRIPT

# Create U-Boot script image if mkimage is available
if command -v mkimage &> /dev/null; then
    mkimage -A arm -O linux -T script -C none -a 0 -e 0 -n "Boot Script" -d "$TEMP_DIR/boot.script" "$TEMP_DIR/u-boot.scr"
    mcopy -i "$BOOT_IMG" "$TEMP_DIR/u-boot.scr" ::u-boot.scr
fi

echo -e "${GREEN}✓ Boot partition created${NC}"
echo ""

# Step 4: Create and populate ext4 rootfs partition
echo -e "${CYAN}[4/7] Creating rootfs partition (ext4)...${NC}"
ROOTFS_IMG="$TEMP_DIR/rootfs.img"
ROOTFS_SIZE_MB=$((ROOTFS_END_MB - ROOTFS_START_MB))
ROOTFS_MOUNT="$TEMP_DIR/rootfs_mount"

# Create empty ext4 image
dd if=/dev/zero of="$ROOTFS_IMG" bs=1M count=$ROOTFS_SIZE_MB
mkfs.ext4 -F -L "rootfs" "$ROOTFS_IMG"

# Mount and extract rootfs (this is safe, we're mounting a file not a loop device)
mkdir -p "$ROOTFS_MOUNT"
mount -o loop "$ROOTFS_IMG" "$ROOTFS_MOUNT"

echo "Extracting rootfs..."
tar -xf "$ROOTFS_TAR" -C "$ROOTFS_MOUNT"

# Unmount
umount "$ROOTFS_MOUNT"
echo -e "${GREEN}✓ Rootfs partition created${NC}"
echo ""

# Step 5: Write partitions to image using dd with offset
echo -e "${CYAN}[5/7] Writing partitions to image...${NC}"
# Write boot partition
dd if="$BOOT_IMG" of="$IMAGE_FILE" bs=512 seek=$BOOT_START_SECTOR conv=notrunc status=progress
echo "Boot partition written"

# Write rootfs partition
dd if="$ROOTFS_IMG" of="$IMAGE_FILE" bs=512 seek=$ROOTFS_START_SECTOR conv=notrunc status=progress
echo "Rootfs partition written"
echo -e "${GREEN}✓ Partitions written${NC}"
echo ""

# Step 6: Flash bootloader to raw area (sector 0)
echo -e "${CYAN}[6/8] Flashing bootloader...${NC}"
dd if="$PRELOADER_BIN" of="$IMAGE_FILE" bs=512 seek=0 conv=notrunc status=progress
sync
echo -e "${GREEN}✓ Bootloader flashed${NC}"
echo ""

# Step 7: Generate checksum
echo -e "${CYAN}[7/8] Generating checksum...${NC}"
CHECKSUM_FILE="${IMAGE_FILE}.sha256"
sha256sum "$IMAGE_FILE" > "$CHECKSUM_FILE"
CHECKSUM=$(cut -d' ' -f1 "$CHECKSUM_FILE")
echo -e "${GREEN}✓ Checksum created: ${CHECKSUM:0:16}...${NC}"
echo ""

# Step 8: Cleanup
echo -e "${CYAN}[8/8] Cleaning up...${NC}"
rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}SD Card Image Created Successfully!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo "Image file: $IMAGE_FILE"
echo "Size: $(du -h "$IMAGE_FILE" | cut -f1)"
echo "Checksum: $CHECKSUM_FILE"
echo ""
echo "To write to SD card:"
echo "  sudo dd if=$IMAGE_FILE of=/dev/sdX bs=4M status=progress"
echo "  (Replace /dev/sdX with your SD card device)"
echo ""
