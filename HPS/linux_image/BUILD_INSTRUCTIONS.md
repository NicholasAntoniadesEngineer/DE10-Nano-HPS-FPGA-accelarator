# Linux Image Build Guide

Complete guide for building DE10-Nano Linux image with SSH and Ethernet preconfigured.

## Prerequisites

### Install All Dependencies

```bash
sudo apt-get update && sudo apt-get install -y \
    gcc-arm-linux-gnueabihf flex bison libssl-dev libncurses-dev bc \
    debootstrap qemu-user-static parted dosfstools e2fsprogs \
    make git build-essential
```

**Dependencies**: `gcc-arm-linux-gnueabihf` (cross-compiler), `flex/bison` (kernel config), `libssl-dev/libncurses-dev/bc` (kernel build), `debootstrap/qemu-user-static` (rootfs), `parted/dosfstools/e2fsprogs` (SD image)

### Verify Installation

```bash
arm-linux-gnueabihf-gcc --version && flex --version && debootstrap --version
```

### FPGA Tools (For Complete SD Image)

To build a complete bootable SD image, you'll also need:

#### 1. Intel Quartus Prime (for FPGA bitstream)

**Required for:** QSys generation, FPGA compilation, RBF generation

**Installation:**
1. Download from: https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html
2. Install Quartus Prime Lite (free edition is sufficient)
3. **On Windows/WSL:** Build system automatically detects installations in:
   - `C:\intelFPGA_lite\20.1\quartus\`
   - `C:\intelFPGA\20.1\quartus\`
4. **On Linux:** Add to PATH:
   ```bash
   export PATH=$PATH:/path/to/intelFPGA/20.1/quartus/bin64
   ```

**Verify:**
```bash
cd ../FPGA && make check-tools
```

#### 2. Intel SoC EDS (for bootloader components)

**Required for:** Preloader, U-Boot, Device Tree generation

**Installation:**
1. Download from: https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html
   - Search for "SoC Embedded Design Suite" matching your Quartus version
   - Example: SoC EDS 20.1 for Quartus Prime 20.1
2. **On Windows:** Run installer, install to:
   - `C:\intelFPGA\20.1\embedded` (recommended)
   - Or `C:\intelFPGA_lite\20.1\embedded`
3. **On WSL:** After installation, configure:
   ```bash
   cd ../FPGA
   make soceds-find
   # Follow the printed instructions to set SOCEDS_DEST_ROOT
   ```
   Or manually:
   ```bash
   export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
   # Add SoC EDS tools to PATH (tools are in altera/preloadergen/ not bin/):
   export PATH="$PATH:$SOCEDS_DEST_ROOT/host_tools/altera/preloadergen"
   source "$SOCEDS_DEST_ROOT/embedded_command_shell.sh"
   ```

**Verify:**
```bash
cd ../FPGA && make check-tools
# Should show: ✓ Found: /path/to/bsp-create-settings
```

**Alternative:** If you don't install SoC EDS, you can use prebuilt bootloader binaries:
```bash
sudo PRELOADER_BIN=/path/to/preloader-mkpimage.bin \
     UBOOT_IMG=/path/to/u-boot.img \
     make sd-image
```

See `../FPGA/SOC_EDS_SETUP.md` for detailed SoC EDS installation guide.

## Build Process

### Complete Build (Recommended)

```bash
cd HPS/linux_image
sudo make all
```

**Time**: ~45-85 minutes (kernel: 30-60min, rootfs: 10-20min, image: 5min)

### Build Components Separately

```bash
make kernel              # Kernel only (~30-60 min)
sudo make rootfs         # Rootfs only (~10-20 min, requires root)
sudo make sd-image       # SD image only (~5 min, requires kernel+rootfs)
```

## Output Files

- **Kernel**: `kernel/build/arch/arm/boot/zImage`
- **Device Tree**: `kernel/build/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb`
- **Rootfs**: `rootfs/build/rootfs.tar.gz`
- **SD Image**: `build/de10-nano-custom.img`

## Deploy to SD Card

```bash
cd HPS/linux_image/scripts
sudo ./deploy_image.sh /dev/sdX  # Replace /dev/sdX with your SD card device
```

**WARNING**: This overwrites all data on the SD card!

## First Boot

1. Insert SD card → Power on DE10-Nano
2. Connect Ethernet → Wait for DHCP (auto-assigns IP)
3. Find IP address (check router/DHCP server)
4. SSH: `ssh root@<board-ip>` (password: `root`)
5. Change password: `passwd`

## Configuration

Edit `build_config.sh` to customize:

```bash
# Network: "dhcp" (default) or "static"
export NETWORK_MODE="dhcp"
export STATIC_IP="192.168.1.100"      # If static
export STATIC_GATEWAY="192.168.1.1"   # If static

# SSH
export SSH_ENABLED="yes"
export SSH_ROOT_LOGIN="yes"
export ROOT_PASSWORD="root"  # ⚠️ Change after first boot!
```

## Troubleshooting

### Missing Dependencies

**Error**: `flex: not found` or similar

**Fix**: Install missing packages:
```bash
sudo apt-get install -y flex bison libssl-dev libncurses-dev bc
```

### ARM Architecture Errors

**Error**: `Error: selected processor does not support 'dmb ish' in ARM mode` or similar ARMv7 instruction errors

**Fix**: The Makefile now automatically adds the correct assembler flags (`-Wa,-mcpu=cortex-a9`). If you still see these errors, clean and rebuild:

```bash
cd HPS/linux_image/kernel
make kernel-clean
make kernel-config
make kernel-build
```

The build system will automatically:
- Clean old build artifacts that may have been compiled with wrong flags
- Pass `-march=armv7-a -mtune=cortex-a9 -mfpu=vfpv3` to the compiler
- Pass `-Wa,-mcpu=cortex-a9` to the assembler (via `KBUILD_AFLAGS`)

If errors persist after cleaning, verify the cross-compiler supports ARMv7-A:
```bash
arm-linux-gnueabihf-gcc -march=armv7-a -E -dM - < /dev/null | grep __ARM_ARCH
# Should show: #define __ARM_ARCH 7
```

### FPU Error

**Error**: `cc1: error: '-mfloat-abi=hard': selected architecture lacks an FPU`

**Fix**: The Makefile now automatically adds `-mfpu=vfpv3` for the Cortex-A9's VFPv3 FPU. If you still see this error, clean and rebuild:

```bash
cd HPS/linux_image/kernel
make kernel-clean
make kernel-build
```

The build system will automatically add `-mfpu=vfpv3` to both compiler and assembler flags.

### Kernel Branch Not Found

**Error**: `fatal: Remote branch socfpga-5.15.64-lts not found`

**Fix**: Build system auto-tries multiple branches. If it fails:
```bash
cd HPS/linux_image/kernel
make kernel-distclean && make kernel-download
```

### Kernel Source Incomplete

**Error**: `ERROR: Kernel source appears incomplete - 'arch' directory not found`

**Fix**: Re-download kernel source:
```bash
cd HPS/linux_image/kernel
make kernel-distclean  # Remove incomplete source
make kernel-download   # Re-download and checkout files
```

### No Defconfig Found

**Error**: `ERROR: No suitable defconfig found`

**Fix**: Build system auto-searches. Check available defconfigs:
```bash
cd HPS/linux_image/kernel/linux-socfpga
ls arch/arm/configs/*defconfig | grep -i socfpga
```

### Permission Denied

**Error**: `Permission denied` during rootfs/image creation

**Fix**: Use `sudo`:
```bash
sudo make rootfs
sudo make sd-image
sudo make all
```

### Rootfs Build Fails

**Error**: `debootstrap` or `qemu-user-static` not found

**Fix**: Install rootfs dependencies:
```bash
sudo apt-get install -y debootstrap qemu-user-static
```

### Network Issues During Rootfs Build

**Error**: `Failed to fetch` during debootstrap

**Fix**: Ensure internet connection:
```bash
ping -c 3 deb.debian.org
```

## Verification

### Check SSH Status
```bash
systemctl status ssh  # Should show: active (running)
```

### Check Network Status
```bash
ip addr show eth0              # Should show IP address
systemctl status networking    # Should show: active (running)
ping -c 3 8.8.8.8             # Test connectivity
```

## Windows Users

Use WSL2:
```powershell
wsl --install
```

Then in WSL:
```bash
cd /mnt/c/Users/nicka/Documents/GitHub/low-latency-market-analysis
cd HPS/linux_image
sudo make all
```

## Quick Reference

```bash
# Clean and rebuild
cd HPS/linux_image
make clean && sudo make all

# Clean kernel only
cd kernel && make kernel-distclean

# Clean rootfs only
cd rootfs && make clean
```

## See Also

- [Main HPS README](../README.md)
- [Kernel Build Guide](kernel/README.md)
- [Rootfs Build Guide](rootfs/README.md)
