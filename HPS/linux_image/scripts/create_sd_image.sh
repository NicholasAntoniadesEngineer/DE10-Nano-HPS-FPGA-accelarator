#!/bin/bash
# ============================================================================
# SD Card Image Creation Script for DE10-Nano
# ============================================================================
# Altera SoC partition layout:
#   Part 1: FAT32 (type 0x0c) - U-Boot, kernel, FPGA bitstream, boot script
#   Part 2: Linux ext4 (type 0x83) - rootfs
#   Part 3: Altera preloader (type 0xa2) - u-boot-with-spl.sfp raw
#
# The Altera SPL ROM searches for the 0xa2 partition and loads the preloader
# from it. The preloader then finds u-boot.img on the FAT32 partition.
# No MBR patching needed — the partition table is never overwritten.
# ============================================================================

set -e

# Cleanup temp directory on failure
cleanup_on_error() {
    if [ -d "/tmp/de10-sdimage-tmp" ]; then
        echo -e '\033[0;31m[ERROR] Cleaning up temporary files...\033[0m'
        rm -rf /tmp/de10-sdimage-tmp
    fi
}
trap cleanup_on_error ERR

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
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
# Use /tmp for intermediate files — /workspace is macOS bind mount (no mknod support)
TEMP_DIR="/tmp/de10-sdimage-tmp"

# Source files
BOOTLOADER_BUILD_DIR="${LINUX_IMAGE_DIR}/bootloader/build"
KERNEL_DIR="${KERNEL_DIR:-$LINUX_IMAGE_DIR/kernel}"
ROOTFS_DIR="${ROOTFS_DIR:-$LINUX_IMAGE_DIR/rootfs}"

# File locations
PRELOADER_BIN="${PRELOADER_BIN:-$BOOTLOADER_BUILD_DIR/u-boot-with-spl.sfp}"
UBOOT_IMG="${UBOOT_IMG:-$BOOTLOADER_BUILD_DIR/u-boot.img}"
KERNEL_IMAGE="${KERNEL_IMAGE:-$KERNEL_DIR/build/arch/arm/boot/zImage}"
FPGA_RBF="${FPGA_RBF:-$REPO_ROOT/FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf}"
DTB_FILE="${DTB_FILE:-$KERNEL_DIR/build/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb}"

# Rootfs tarball
if [ -z "$ROOTFS_TAR" ]; then
    if [ -f "/var/lib/rootfs-build/build/rootfs.tar.xz" ]; then
        ROOTFS_TAR="/var/lib/rootfs-build/build/rootfs.tar.xz"
    else
        ROOTFS_TAR="$ROOTFS_DIR/build/rootfs.tar.xz"
    fi
fi

# Partition layout (sectors, 512 bytes each)
# The Altera boot ROM scans MBR for 0xa2 partition to find the preloader.
# sfdisk requires partitions to fit within the disk. Since FAT32+rootfs fill
# all sectors 2048+, the 0xa2 partition (sectors 2-2047) must be listed LAST
# in MBR and given an explicit size so sfdisk doesn't complain about overlap.
# MBR slot order:
#   Slot 1: FAT32 boot   (sector 2048, 100MB)  — SPL loads u-boot.img here
#   Slot 2: Linux rootfs (sector 206848, explicit size in sectors)
#   Slot 3: 0xa2 preloader (sector 2, size 2046) — boot ROM finds SPL here
PRELOADER_START=2    # Altera standard: preloader at sector 2
PRELOADER_PART_SIZE=2046  # sectors 2-2047 (1MB gap before FAT32)

BOOT_START_SECTOR=2048
BOOT_SIZE_MB=100
BOOT_SIZE_SECTOR=$((BOOT_SIZE_MB * 2048))

ROOTFS_START_SECTOR=$((BOOT_START_SECTOR + BOOT_SIZE_SECTOR))
ROOTFS_SIZE_MB=$((IMAGE_SIZE_MB - BOOT_SIZE_MB - 1))
ROOTFS_SIZE_SECTOR=$((ROOTFS_SIZE_MB * 2048))

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}DE10-Nano SD Image Creation${NC}"
echo -e "${GREEN}===========================================${NC}"
echo "Image: $IMAGE_FILE"
echo "Size: ${IMAGE_SIZE_MB}MB"
echo "Layout: preloader(raw)@sector2, FAT32(p1)@1MB(${BOOT_SIZE_MB}MB), ext4(p2)@$((BOOT_SIZE_MB+1))MB(${ROOTFS_SIZE_MB}MB)"
echo ""

# Check dependencies
echo -e "${CYAN}Checking dependencies...${NC}"
for cmd in sfdisk dd mkfs.vfat mkfs.ext4 mcopy tar; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}ERROR: $cmd not found${NC}"
        exit 1
    fi
done
echo -e "${GREEN}All dependencies found${NC}"
echo ""

# Check required files
echo -e "${CYAN}Checking required files...${NC}"
for file in "$PRELOADER_BIN" "$KERNEL_IMAGE" "$FPGA_RBF" "$DTB_FILE" "$ROOTFS_TAR"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}ERROR: Required file not found: $file${NC}"
        exit 1
    fi
    echo "✓ $(basename $file): $(du -h "$file" | cut -f1)"
done
echo ""

# Check mkimage
if ! command -v mkimage &> /dev/null; then
    echo -e "${RED}ERROR: mkimage not found — cannot create u-boot.scr${NC}"
    exit 1
fi

mkdir -p "$BUILD_DIR" "$TEMP_DIR"

# Step 1: Create empty image
echo -e "${CYAN}[1/7] Creating ${IMAGE_SIZE_MB}MB image file...${NC}"
dd if=/dev/zero of="$IMAGE_FILE" bs=1M count=$IMAGE_SIZE_MB status=progress
echo -e "${GREEN}✓ Image file created${NC}"
echo ""

# Step 2: Create partition table
# Three partitions: FAT32 boot, Linux rootfs, Altera preloader (0xa2)
# The 0xa2 partition physically overlaps with the start of the disk but
# the Altera boot ROM uses it as a pointer to find the preloader binary.
echo -e "${CYAN}[2/7] Creating partition table...${NC}"
# Create FAT32 + rootfs with sfdisk (2 partitions), then patch MBR slot 3
# with the 0xa2 preloader entry using Python (sfdisk rejects non-sequential).
sfdisk "$IMAGE_FILE" << EOF
label: dos
start=${BOOT_START_SECTOR}, size=${BOOT_SIZE_SECTOR}, type=c, bootable
start=${ROOTFS_START_SECTOR}, size=${ROOTFS_SIZE_SECTOR}, type=83
EOF

# Patch MBR slot 3 (offset 478) with the 0xa2 preloader partition entry.
# MBR partition entry: status(1) + CHS_start(3) + type(1) + CHS_end(3) + LBA_start(4) + LBA_size(4)
# We write LBA start/size only; CHS set to 0xFE (LBA-only mode).
python3 << PYEOF
import struct, sys
with open("${IMAGE_FILE}", "r+b") as f:
    # Slot 3 starts at MBR offset 446 + 2*16 = 478
    f.seek(478)
    status = 0x00          # not bootable
    chs_dummy = b'\xfe\xff\xff'  # LBA mode indicator
    ptype = 0xa2
    lba_start = ${PRELOADER_START}
    lba_size  = ${PRELOADER_PART_SIZE}
    entry = struct.pack('<B3sB3sII', status, chs_dummy, ptype, chs_dummy, lba_start, lba_size)
    f.write(entry)
print("Patched MBR slot 3: type=0xa2, start=${PRELOADER_START}, size=${PRELOADER_PART_SIZE}")
PYEOF
echo -e "${GREEN}✓ Partition table created${NC}"
echo ""

# Step 3: Write preloader into the 0xa2 partition area (sector 2)
echo -e "${CYAN}[3/7] Writing preloader (0xa2 partition)...${NC}"
dd if="$PRELOADER_BIN" of="$IMAGE_FILE" bs=512 seek=${PRELOADER_START} conv=notrunc
echo -e "${GREEN}✓ Preloader written at sector ${PRELOADER_START}${NC}"
echo ""

# Step 4: Create and populate FAT32 boot partition
echo -e "${CYAN}[4/7] Creating boot partition (FAT32)...${NC}"
BOOT_IMG="$TEMP_DIR/boot.img"
dd if=/dev/zero of="$BOOT_IMG" bs=1M count=$BOOT_SIZE_MB
mkfs.vfat -F 32 -n "BOOT" "$BOOT_IMG"

echo "Copying boot files..."
if [ -f "$UBOOT_IMG" ]; then
    mcopy -i "$BOOT_IMG" "$UBOOT_IMG" ::u-boot.img
fi
mcopy -i "$BOOT_IMG" "$KERNEL_IMAGE" ::zImage
mcopy -i "$BOOT_IMG" "$FPGA_RBF" ::DE10_NANO_SoC_GHRD.rbf
mcopy -i "$BOOT_IMG" "$DTB_FILE" ::socfpga.dtb

# Create boot script
cat > "$TEMP_DIR/boot.script" << 'BOOTSCRIPT'
setenv ethaddr 02:00:DE:10:00:00
echo ""
echo "DE10-Nano HPS-FPGA Boot"
echo "NOTE: DIP switch SW10 (MSEL) must be set for HPS FPGA programming."
echo "      If FPGA registers return 0, check SW10 and power cycle."
echo ""
echo "Loading FPGA bitstream..."
fatload mmc 0:1 0x03000000 DE10_NANO_SoC_GHRD.rbf
fpga load 0 0x03000000 ${filesize}
echo "Enabling HPS-to-FPGA bridges..."
bridge enable
echo "Loading device tree..."
fatload mmc 0:1 0x02000000 socfpga.dtb
echo "Loading kernel..."
fatload mmc 0:1 0x01000000 zImage
setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p2 rw rootwait quiet loglevel=3
echo "Booting..."
bootz 0x01000000 - 0x02000000
BOOTSCRIPT

mkimage -A arm -O linux -T script -C none -a 0 -e 0 -n "Boot Script" \
    -d "$TEMP_DIR/boot.script" "$TEMP_DIR/boot.scr"
# Copy as both boot.scr (distro_bootcmd) and u-boot.scr (legacy)
mcopy -i "$BOOT_IMG" "$TEMP_DIR/boot.scr" ::boot.scr
mcopy -i "$BOOT_IMG" "$TEMP_DIR/boot.scr" ::u-boot.scr

dd if="$BOOT_IMG" of="$IMAGE_FILE" bs=512 seek=$BOOT_START_SECTOR conv=notrunc
echo -e "${GREEN}✓ Boot partition written${NC}"
echo ""

# Step 4b: Write U-Boot environment block
# Bakes bootcmd into the image so the board boots automatically without saveenv.
# U-Boot 2020.04 on DE10-Nano stores env at MMC offset 0x200000 (sector 1024),
# size 0x2000 (16KB). Format: 4-byte CRC32 + null-terminated key=value pairs.
echo -e "${CYAN}[4b/7] Writing U-Boot environment...${NC}"
UBOOT_ENV_FILE="$TEMP_DIR/uboot.env"
UBOOT_ENV_TXT="$TEMP_DIR/uboot_env.txt"
# Write environment variables (null-separated, ending with double-null)
cat > "$UBOOT_ENV_TXT" << 'ENVEOF'
bootcmd=fatload mmc 0:1 0x01000000 u-boot.scr; source 0x01000000
bootdelay=2
ethaddr=02:00:DE:10:00:00
ENVEOF
# Use mkenvimage to create U-Boot env block (16KB)
if command -v mkenvimage &> /dev/null; then
    mkenvimage -s 0x2000 -o "$UBOOT_ENV_FILE" "$UBOOT_ENV_TXT"
    # U-Boot env offset: sector 1024 (0x80000 bytes = 512KB from start)
    dd if="$UBOOT_ENV_FILE" of="$IMAGE_FILE" bs=512 seek=1024 conv=notrunc 2>/dev/null
    echo -e "${GREEN}✓ U-Boot environment written (bootcmd pre-configured)${NC}"
else
    echo -e "${YELLOW}Warning: mkenvimage not found — U-Boot env not pre-configured (saveenv needed on first boot)${NC}"
fi
echo ""

# Step 5: Create and populate ext4 rootfs partition
echo -e "${CYAN}[5/7] Creating rootfs partition (ext4)...${NC}"
ROOTFS_IMG="$TEMP_DIR/rootfs.img"
EXTRACT_DIR="$TEMP_DIR/rootfs_extract"
mkdir -p "$EXTRACT_DIR"
echo "Extracting rootfs tarball..."
tar -xf "$ROOTFS_TAR" -C "$EXTRACT_DIR"
echo "Creating ext4 image from rootfs directory..."
mkfs.ext4 -F -L "rootfs" -d "$EXTRACT_DIR" -b 4096 "$ROOTFS_IMG" "${ROOTFS_SIZE_MB}M"
rm -rf "$EXTRACT_DIR"
dd if="$ROOTFS_IMG" of="$IMAGE_FILE" bs=512 seek=$ROOTFS_START_SECTOR conv=notrunc status=progress
echo -e "${GREEN}✓ Rootfs partition written${NC}"
echo ""

# Step 6: Verify partition table is intact
echo -e "${CYAN}[6/7] Verifying partition table...${NC}"
sfdisk -l "$IMAGE_FILE" 2>&1 | grep -E "img[0-9]"
echo -e "${GREEN}✓ Partition table verified${NC}"
echo ""

# Step 7: Generate checksum and cleanup
echo -e "${CYAN}[7/7] Finalizing...${NC}"
sha256sum "$IMAGE_FILE" > "${IMAGE_FILE}.sha256"
CHECKSUM=$(cut -d' ' -f1 "${IMAGE_FILE}.sha256")
rm -rf "$TEMP_DIR"
echo -e "${GREEN}✓ Done. Checksum: ${CHECKSUM:0:16}...${NC}"
echo ""

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}SD Card Image Created Successfully!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo "Image file: $IMAGE_FILE"
echo "Size: $(du -h "$IMAGE_FILE" | cut -f1)"
echo ""
echo "To write to SD card:"
echo "  Linux: sudo dd if=$IMAGE_FILE of=/dev/sdX bs=4M status=progress"
echo "  macOS: diskutil unmountDisk force diskN && sudo dd if=$IMAGE_FILE of=/dev/rdiskN bs=4m"
echo ""
echo -e "${CYAN}IMPORTANT: Before powering on the DE10-Nano:${NC}"
echo "  Set DIP switch SW10 (MSEL) for HPS FPGA programming mode."
echo "  MSEL is sampled at power-on — changing it requires a power cycle."
echo "  Verify after boot: devmem2 0xff20003c w  (expect 0x00010001)"
