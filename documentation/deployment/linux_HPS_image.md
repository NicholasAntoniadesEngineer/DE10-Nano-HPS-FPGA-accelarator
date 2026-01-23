# Linux HPS Images - Complete Build Guide

This guide provides detailed instructions for building custom Linux images for the DE10-Nano's HPS using the project's automated build system.

## Automated Build System

This project includes a complete automated build system that handles the entire Linux image creation process. The build system is located in `HPS/linux_image/` and provides the following components:

### Prerequisites

#### Software Requirements
- **Linux environment** (WSL2 recommended for Windows users)
- **Intel Quartus Prime Lite 20.1** - FPGA tools
- **Intel SoC EDS 20.1** - HPS bootloader tools
- **ARM cross-compilation toolchain**
- **Root privileges** (for kernel and rootfs builds)

#### Hardware Requirements
- DE10-Nano development board
- MicroSD card (16GB+ recommended)
- Sufficient disk space (10GB+ free)

### Environment Setup

1. **Install Intel Quartus Prime Lite 20.1**
   - Download from Intel website
   - Install to default location

2. **Install Intel SoC EDS 20.1**
   - Download Embedded Design Suite
   - Install to default location
   - **Note:** Requires ARM DS-5 license (free community edition available)

3. **Set Environment Variables**
   ```bash
   export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
   export PATH="$PATH:$SOCEDS_DEST_ROOT/host_tools/bin:$SOCEDS_DEST_ROOT/bin"
   ```

4. **Verify Installation**
   ```bash
   which quartus
   which bsp-create-settings
   ```

## Complete Build Process

### Step 1: Build FPGA Bitstream
The FPGA bitstream must be built first as it provides the hardware interface for the HPS.

```bash
cd FPGA
make sof rbf
```

**Expected output:** `build/output_files/DE10_NANO_SoC_GHRD.rbf`

### Step 2: Build Bootloader Components
The bootloader consists of preloader, U-Boot, and device tree.

```bash
# From FPGA directory
make preloader uboot dtb
```

**Expected outputs:**
- `HPS/preloader/preloader-mkpimage.bin` - First stage bootloader
- `HPS/preloader/uboot-socfpga/u-boot.img` - U-Boot bootloader
- `generated/soc_system.dtb` - Device tree blob

### Step 3: Build Linux Kernel
Build the Linux kernel with DE10-Nano specific configuration.

```bash
cd ../HPS/linux_image
sudo make kernel
```

**Process:**
- Downloads and patches Linux kernel source
- Applies DE10-Nano specific configuration
- Cross-compiles for ARM architecture
- Builds kernel modules and device tree overlays

**Expected outputs:**
- `kernel/build/arch/arm/boot/zImage` - Compressed kernel image
- `kernel/build/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb` - Device tree

### Step 4: Build Debian Root Filesystem
Create a complete Debian root filesystem with all necessary packages.

```bash
sudo make rootfs
```

**Process:**
- Sets up Debian base system using debootstrap
- Installs required packages from `rootfs/packages.txt`
- Configures network settings
- Sets up FPGA drivers and services
- Creates compressed rootfs archive

**Expected output:** `rootfs/build/rootfs.tar.gz`

### Step 5: Create Complete SD Card Image
Combine all components into a bootable SD card image.

```bash
sudo make sd-image
```

**Process:**
- Creates partition layout (FAT32 boot + ext4 root)
- Copies bootloader files to boot partition
- Extracts rootfs to root partition
- Generates final bootable image

**Expected output:** `build/de10-nano-custom.img` (~4GB)

## SD Card Deployment

### Using the Automated Script
```bash
# Identify SD card device (be careful!)
lsblk  # Find your SD card device, e.g., /dev/sdb

# Flash the image
sudo ./scripts/deploy_image.sh /dev/sdX
```

### Manual SD Card Setup
If you prefer manual setup:

1. **Partition SD card:**
   ```bash
   sudo fdisk /dev/sdX
   # Create 100MB FAT32 partition + remaining ext4 partition
   ```

2. **Format partitions:**
   ```bash
   sudo mkfs.vfat /dev/sdX1
   sudo mkfs.ext4 /dev/sdX2
   ```

3. **Copy files:**
   ```bash
   # Mount partitions
   sudo mount /dev/sdX1 /mnt/boot
   sudo mount /dev/sdX2 /mnt/root

   # Copy boot files
   sudo cp HPS/preloader/preloader-mkpimage.bin /mnt/boot/
   sudo cp HPS/preloader/uboot-socfpga/u-boot.img /mnt/boot/
   sudo cp HPS/linux_image/kernel/build/arch/arm/boot/zImage /mnt/boot/
   sudo cp FPGA/generated/soc_system.dtb /mnt/boot/

   # Extract rootfs
   sudo tar xf HPS/linux_image/rootfs/build/rootfs.tar.gz -C /mnt/root/
   ```

## Verification and Testing

### Build Verification
After each step, verify outputs exist:

```bash
# FPGA bitstream
ls -la FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf

# Bootloader components
ls -la HPS/preloader/preloader-mkpimage.bin
ls -la HPS/preloader/uboot-socfpga/u-boot.img
ls -la FPGA/generated/soc_system.dtb

# Linux components
ls -la HPS/linux_image/kernel/build/arch/arm/boot/zImage
ls -la HPS/linux_image/rootfs/build/rootfs.tar.gz

# Final image
ls -la HPS/linux_image/build/de10-nano-custom.img
```

### Board Testing
1. **Insert SD card and power on board**
2. **Connect via UART** (115200 baud) for boot logs
3. **Check network connectivity:**
   ```bash
   ssh root@de10-nano-ip  # Default password: root
   ip addr show
   ```
4. **Test FPGA-HPS communication:**
   ```bash
   cd /root
   ./calculator_test
   ```

## Build System Architecture

### Directory Structure
```
HPS/linux_image/
├── Makefile              # Main build orchestration
├── build_config.sh       # Build configuration
├── kernel/               # Linux kernel build
│   ├── Makefile
│   └── configs/          # Kernel configurations
├── rootfs/               # Root filesystem build
│   ├── Makefile
│   ├── build_rootfs.sh
│   ├── packages.txt      # Package list
│   └── scripts/          # Setup scripts
└── scripts/              # Utility scripts
```

### Key Components

#### Kernel Build (kernel/Makefile)
- Downloads Linux 5.10 LTS with SoC FPGA patches
- Applies DE10-Nano specific configuration
- Builds with ARM cross-compiler
- Includes FPGA bridge and UIO drivers

#### Rootfs Build (rootfs/Makefile)
- Uses debootstrap for clean Debian base
- Installs packages from packages.txt
- Runs configuration scripts for:
  - Network setup
  - FPGA driver installation
  - SSH configuration
  - Service setup

#### SD Image Creation (scripts/create_sd_image.sh)
- Uses dd and parted for partition creation
- Copies bootloader files to boot partition
- Extracts rootfs to root partition
- Ensures proper boot sequence

## Alternative Build Methods

### 1. Yocto-Based Build
For production environments:

```bash
# Setup Yocto
git clone -b kirkstone git://git.yoctoproject.org/poky.git
git clone -b kirkstone git://git.yoctoproject.org/meta-intel-fpga.git

# Configure and build
source poky/oe-init-build-env build-de10-nano
bitbake core-image-minimal
```

### 2. Manual Build Process
For advanced customization:

1. **Build kernel manually:**
   ```bash
   export CROSS_COMPILE=arm-linux-gnueabihf-
   export ARCH=arm
   make socfpga_defconfig
   make zImage dtbs modules -j$(nproc)
   ```

2. **Create rootfs manually:**
   ```bash
   sudo debootstrap --foreign --arch=armhf buster /path/to/rootfs
   # Configure and install packages
   ```

### 3. Using Pre-built Components
If SoC EDS is problematic (e.g., Python XML compatibility issues in version 20.1):

#### Get Prebuilt Bootloader Binaries
**Sources:**
- Terasic DE10-Nano System CD (recommended)
- Intel FPGA forum downloads
- GitHub DE10-Nano repositories
- Community shared binaries

**Expected files:**
- `preloader-mkpimage.bin` (~262KB)
- `u-boot.img` (~238KB)

#### Build with Prebuilt Binaries
```bash
# Copy binaries to repository
cp /path/to/preloader-mkpimage.bin HPS/preloader/
cp /path/to/u-boot.img HPS/preloader/uboot-socfpga/

# Build FPGA (if not already done)
cd FPGA
make sof rbf

# Build Linux system
cd ../HPS/linux_image
sudo PRELOADER_BIN=HPS/preloader/preloader-mkpimage.bin \
     UBOOT_IMG=HPS/preloader/uboot-socfpga/u-boot.img \
     make linux-image
```

#### Complete File Inventory
After successful build:
```
build/output_files/DE10_NANO_SoC_GHRD.rbf          # FPGA bitstream ✓
HPS/preloader/preloader-mkpimage.bin              # Preloader ✓ (prebuilt)
HPS/preloader/uboot-socfpga/u-boot.img           # U-Boot ✓ (prebuilt)
HPS/linux_image/kernel/build/arch/arm/boot/zImage # Linux kernel ✓
HPS/linux_image/rootfs/build/rootfs.tar.gz        # Debian rootfs ✓
HPS/linux_image/build/de10-nano-custom.img        # Complete SD image ✓
```

## Troubleshooting

### Common Build Issues

#### SoC EDS License Errors
- Get free ARM DS-5 Community Edition license
- Use 30-day evaluation license
- Skip SoC EDS and use prebuilt bootloaders

#### Disk Space Issues
- Ensure 10GB+ free space
- Clean build directory: `make clean`

#### Network Issues During Rootfs Build
- Check internet connectivity
- Verify Debian mirror accessibility
- Use local package cache if available

#### Cross-Compiler Issues
- Verify ARM toolchain installation
- Check PATH includes cross-compiler bin directory

### Recovery Options

#### Clean Rebuild
```bash
cd HPS/linux_image
sudo make clean
sudo make kernel rootfs sd-image
```

#### Partial Rebuild
```bash
# Rebuild only kernel
sudo make clean-kernel
sudo make kernel

# Rebuild only rootfs
sudo make clean-rootfs
sudo make rootfs
```

## Performance Optimization

### Build Speed
- Use multiple cores: Build system automatically detects `nproc`
- Incremental builds: Only rebuild changed components
- Use SSD storage for faster I/O

### Image Size Optimization
- Review packages.txt for unnecessary packages
- Use compressed filesystem (already enabled)
- Strip debug symbols from production builds

## Build System Achievements

### ✅ Robust Build Infrastructure
- **Multi-stage error handling** and recovery options
- **Automatic internet connectivity checks**
- **CRLF line ending normalization** for cross-platform compatibility
- **Comprehensive documentation** and troubleshooting guides
- **Support for both SoC EDS and prebuilt binaries**

### ✅ Complete Toolchain Integration
- **Quartus Prime FPGA compilation** with QSys system generation
- **ARM cross-compilation** for Linux kernel and modules
- **Debian rootfs generation** with SSH, networking, and FPGA drivers
- **SD card image creation** with proper partition layout
- **Automated deployment scripts** for flashing

### ✅ Advanced Features
- **Build dependency management** and parallel compilation
- **Incremental build capabilities** for faster development
- **Prebuilt binary support** for SoC EDS compatibility issues
- **Cross-platform compatibility** (Windows/WSL/Linux)
- **FPGA-HPS communication testing** included

## Final Testing and Deployment

### Board Boot Test
1. **Flash SD card:**
   ```bash
   sudo ./scripts/deploy_image.sh /dev/sdX
   ```

2. **Boot the board:**
   - Insert SD card into DE10-Nano
   - Power on the board
   - Wait for Linux boot (~30 seconds)

3. **SSH access:**
   ```bash
   ssh root@<board-ip>  # Default password: root
   ```

4. **Test FPGA communication:**
   ```bash
   cd /root
   ./calculator_test  # Test HPS ↔ FPGA communication
   ```

### Success Indicators
- ✅ **Board boots successfully** with Linux kernel
- ✅ **Network connectivity** available
- ✅ **SSH access** working
- ✅ **FPGA-HPS communication** functional
- ✅ **All system services** running properly

## Security Considerations

### Default Configuration
- Root login enabled (change password after first boot)
- SSH service enabled
- Basic firewall configuration applied

### Production Hardening
- Disable root SSH login
- Configure user accounts
- Apply security updates
- Set up proper firewall rules
