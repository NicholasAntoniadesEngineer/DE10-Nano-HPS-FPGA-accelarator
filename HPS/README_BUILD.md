# Complete Linux Image Build for DE10-Nano

This document describes how to build a complete Linux image for DE10-Nano from scratch, including FPGA drivers, network configuration, and SSH access.

## Overview

The build system creates a bootable SD card image with:
- ✅ FPGA bitstream (RBF)
- ✅ Preloader and U-Boot bootloader
- ✅ Linux kernel with FPGA driver support
- ✅ Root filesystem with network and SSH pre-configured
- ✅ All required boot files

## Quick Start

```bash
# From repository root - Build everything
./Scripts/build_linux_image.sh

# Deploy to SD card
sudo ./Scripts/deploy_image.sh /dev/sdb
```

## Prerequisites

### Required Tools

Check dependencies:
```bash
./Scripts/check_dependencies.sh
```

Essential tools:
- Cross-compilation toolchain: `arm-linux-gnueabihf-`
- Build tools: `make`, `git`, `bash`
- Rootfs tools: `debootstrap`, `qemu-user-static` (for rootfs build)
- Image tools: `parted`, `mkfs.vfat`, `mkfs.ext4` (for image creation)

Install on Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install build-essential git bash \
    gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf \
    debootstrap qemu-user-static \
    parted dosfstools e2fsprogs
```

### Optional Tools

#### Intel Quartus Prime (for FPGA bitstream generation)

**Required for:** QSys generation, FPGA compilation, SOF/RBF generation

**Installation:**
1. Download Quartus Prime from [Intel FPGA Software](https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html)
2. Install Quartus Prime (Lite Edition is sufficient)
3. **On Windows/WSL:** The build system automatically detects Windows Quartus installations in:
   - `C:\intelFPGA_lite\20.1\quartus\`
   - `C:\intelFPGA\20.1\quartus\`
4. **On Linux:** Add Quartus to PATH:
   ```bash
   export PATH=$PATH:/path/to/intelFPGA/20.1/quartus/bin64
   ```

**Verify installation:**
```bash
cd FPGA && make check-tools
# Should show: ✓ Found: /path/to/quartus_sh.exe
```

#### Intel SoC EDS (for preloader and U-Boot build)

**Required for:** Preloader, U-Boot, Device Tree generation, SD card image creation

**Installation:**
1. Download SoC EDS from [Intel FPGA Software](https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html)
   - Search for "SoC Embedded Design Suite" matching your Quartus version
   - Example: `SoC EDS v20.1` for Quartus Prime 20.1
2. **On Windows:** Run the installer and install to:
   - `C:\intelFPGA\20.1\embedded` (recommended)
   - Or `C:\intelFPGA_lite\20.1\embedded` (if using Lite edition)
3. **On Linux/WSL:** After installation, set environment variable:
   ```bash
   export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
   # Or if installed to Lite directory:
   # export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA_lite/20.1/embedded"

   # Add SoC EDS tools to PATH (SoC EDS 20.1 tools are in altera/preloadergen/):
   export PATH="$PATH:$SOCEDS_DEST_ROOT/host_tools/altera/preloadergen"

   # Source the embedded command shell:
   source "$SOCEDS_DEST_ROOT/embedded_command_shell.sh"
   ```

**Auto-detect installation (WSL/Windows):**
```bash
cd FPGA
make soceds-find
# This will print the exact commands to run
```

**Verify installation:**
```bash
cd FPGA && make check-tools
# Should show: ✓ Found: /path/to/bsp-create-settings
```

**Make it permanent (optional):**
Add to `~/.bashrc`:
```bash
export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
source "$SOCEDS_DEST_ROOT/embedded_command_shell.sh" 2>/dev/null || true
```

**Alternative:** If you don't want to install SoC EDS, you can use prebuilt bootloader binaries:
```bash
sudo PRELOADER_BIN=/path/to/preloader-mkpimage.bin \
     UBOOT_IMG=/path/to/u-boot.img \
     make sd-image
```

See `FPGA/SOC_EDS_SETUP.md` for detailed SoC EDS installation guide.

#### Device Tree Compiler

Usually included with kernel build tools. If missing:
```bash
sudo apt-get install device-tree-compiler
```

## Build Process

### Step 1: Check Dependencies

```bash
./Scripts/check_dependencies.sh
```

### Step 2: Configure Build

Edit `HPS/build_config.sh` or set environment variables:

```bash
# Network configuration
export NETWORK_MODE=dhcp  # or "static"
export STATIC_IP=192.168.1.100  # if static

# SSH configuration
export SSH_ENABLED=yes
export ROOT_PASSWORD=root  # CHANGE THIS!

# Image configuration
export IMAGE_SIZE=4096  # MB
```

### Step 3: Build Complete Image

```bash
# Build everything
./Scripts/build_linux_image.sh

# Or build incrementally
./Scripts/build_linux_image.sh --skip-existing
```

This will:
1. Build FPGA bitstream (if BUILD_FPGA=yes)
2. Build preloader and U-Boot (if SoC EDS available)
3. Generate device tree
4. Build Linux kernel with FPGA drivers
5. Build root filesystem with network/SSH
6. Create complete SD card image

### Step 4: Deploy to SD Card

```bash
# Find SD card device
lsblk

# Deploy (WARNING: overwrites SD card!)
sudo ./Scripts/deploy_image.sh /dev/sdb
```

## Individual Component Builds

### Build Kernel Only

```bash
cd HPS/kernel
make
```

Output: `build/arch/arm/boot/zImage`

### Build Rootfs Only

```bash
cd HPS/rootfs
sudo make
```

Output: `build/rootfs.tar.gz`

### Create SD Image Only

```bash
cd HPS
sudo ./create_sd_image.sh
```

Output: `build/de10-nano-custom.img`

## Configuration

### Network Configuration

**DHCP (Default):**
```bash
export NETWORK_MODE=dhcp
```

**Static IP:**
```bash
export NETWORK_MODE=static
export STATIC_IP=192.168.1.100
export STATIC_GATEWAY=192.168.1.1
export STATIC_NETMASK=255.255.255.0
```

### SSH Configuration

```bash
export SSH_ENABLED=yes
export SSH_ROOT_LOGIN=yes
export ROOT_PASSWORD=root  # CHANGE AFTER FIRST BOOT!
```

### Kernel Configuration

Edit `HPS/kernel/Makefile`:
```makefile
KERNEL_VERSION ?= 5.15.0
KERNEL_BRANCH ?= socfpga-5.15.64-lts
```

### Rootfs Configuration

Edit `HPS/rootfs/packages.txt` to add/remove packages.

## Output Files

After build, you'll have:

```
HPS/
├── build/
│   └── de10-nano-custom.img    # Complete SD card image
├── kernel/
│   └── build/
│       └── arch/arm/boot/
│           ├── zImage          # Kernel image
│           └── dts/
│               └── socfpga_cyclone5_de10_nano.dtb
├── rootfs/
│   └── build/
│       └── rootfs.tar.gz       # Root filesystem
└── preloader/
    ├── preloader-mkpimage.bin  # Preloader
    └── uboot-socfpga/
        └── u-boot.img          # U-Boot
```

## Deployment

### SD Card Deployment

```bash
# Deploy using script (recommended)
sudo ./Scripts/deploy_image.sh /dev/sdb

# Or manually
sudo dd if=HPS/build/de10-nano-custom.img of=/dev/sdb bs=4M status=progress
```

### First Boot

1. Insert SD card into DE10-Nano
2. Power on board
3. Wait for Linux to boot (~30 seconds)
4. Connect via SSH:
   ```bash
   ssh root@<board-ip>
   # Default password: root (CHANGE THIS!)
   ```

### Verify Deployment

```bash
# Check FPGA state
cat /sys/class/fpga_manager/fpga0/state

# Check network
ip addr show

# Test FPGA driver
cd /root
./calculator_test
```

## Troubleshooting

### Build Fails

1. **Check dependencies:**
   ```bash
   ./Scripts/check_dependencies.sh
   ```

2. **Check disk space:**
   ```bash
   df -h
   ```
   Build requires ~10GB free space.

3. **Check build logs:**
   Review error messages in build output.

### Kernel Build Fails

- Verify cross-compilation toolchain is installed
- Check kernel source download (network connection)
- Review kernel build output for specific errors

### Rootfs Build Fails

- Ensure you have root access
- Check debootstrap is installed
- Verify network connection (for package downloads)
- Check disk space

### Image Creation Fails

- Ensure all components are built (kernel, rootfs, etc.)
- Check root access
- Verify loop device is available (Linux)
- Check disk space

### Board Won't Boot

1. **Check SD card:**
   - Verify image was written correctly
   - Try different SD card
   - Check SD card size (minimum 4GB recommended)

2. **Check MSEL switches:**
   - MSEL should be set for SD card boot
   - Refer to DE10-Nano documentation

3. **Check serial console:**
   - Connect via UART (115200 baud)
   - Check boot messages for errors

### SSH Not Working

1. **Check network:**
   ```bash
   ip addr show
   ping google.com
   ```

2. **Check SSH service:**
   ```bash
   systemctl status ssh
   ```

3. **Check firewall:**
   ```bash
   iptables -L
   ```

## Advanced Usage

### Custom Kernel Configuration

```bash
cd HPS/kernel/linux-socfpga
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- menuconfig
cp build/.config configs/my_custom_config
```

### Custom Rootfs Packages

Edit `HPS/rootfs/packages.txt` and rebuild:
```bash
cd HPS/rootfs
sudo make clean
sudo make
```

### Incremental Builds

Skip existing components:
```bash
./Scripts/build_linux_image.sh --skip-existing
```

Build only specific components:
```bash
./Scripts/build_linux_image.sh --no-fpga --no-kernel
```

## See Also

- `HPS/kernel/README.md` - Kernel build details
- `HPS/rootfs/README.md` - Rootfs build details
- `Scripts/README.md` - Deployment scripts documentation
- `documentation/implementation/automated_linux_image_build_plan.md` - Implementation plan
