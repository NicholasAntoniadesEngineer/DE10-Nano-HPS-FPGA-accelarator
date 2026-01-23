# HPS Quick Start Guide

## Prerequisites

### Build Dependencies

Install build dependencies first:

```bash
sudo apt-get update && sudo apt-get install -y \
    gcc-arm-linux-gnueabihf flex bison libssl-dev libncurses-dev bc \
    debootstrap qemu-user-static parted dosfstools e2fsprogs \
    make git build-essential
```

### FPGA Tools (Optional but Recommended)

For complete SD image creation, you'll need:

1. **Intel Quartus Prime** - For FPGA bitstream (RBF) generation
   - Download from: https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html
   - Install Quartus Prime Lite (free)
   - **On WSL:** Build system auto-detects Windows installations

2. **Intel SoC EDS** - For preloader and U-Boot bootloader generation
   - Download from: https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html
   - Install matching your Quartus version (e.g., SoC EDS 20.1 for Quartus 20.1)
   - **On WSL:** After installation, run:
     ```bash
     cd FPGA && make soceds-find
     # Follow the printed instructions to set SOCEDS_DEST_ROOT
     ```
   - See `FPGA/SOC_EDS_SETUP.md` for detailed installation guide

**Note:** If you don't install SoC EDS, you can still build kernel and rootfs, but you'll need to provide prebuilt bootloader binaries for SD image creation.

## Build and Flash SD Card

### Complete Workflow

1. **Install dependencies** (see above)

2. **Build FPGA bitstream** (if needed):
   ```bash
   cd ../FPGA
   make qsys-generate sof rbf
   ```

3. **Build complete Linux image**:
   ```bash
   cd ../HPS
   sudo make linux-image
   ```
   This builds:
   - Linux kernel (~30-60 minutes)
   - Root filesystem (Debian with network/SSH) (~10-20 minutes)
   - SD card image (~5 minutes)
   
   **Total time: ~45-85 minutes (first build)**

3. **Flash SD card**:
   ```bash
   cd linux_image/scripts
   sudo ./deploy_image.sh /dev/sdX
   ```
   Replace `/dev/sdX` with your SD card device (e.g., `/dev/sdb`, `/dev/mmcblk0`)

4. **Boot DE10-Nano**:
   - Insert SD card
   - Power on board
   - Connect via Ethernet
   - SSH: `ssh root@<board-ip>` (default password: `root`)

## Independent Builds (Save Time)

### Build Applications Only (Fast)
```bash
cd HPS
make                    # Build all applications
make calculator_test    # Build calculator test only
make led_examples       # Build LED examples only
```

### Build Kernel Only
```bash
cd HPS
make kernel
```

### Build Rootfs Only
```bash
cd HPS
sudo make rootfs
```

### Create SD Image Only (requires kernel + rootfs)
```bash
cd HPS
sudo make sd-image
```

## Directory Structure

```
HPS/
├── linux_image/      # Complete Linux system
│   ├── kernel/       # Kernel build
│   ├── rootfs/       # Rootfs build
│   └── scripts/      # Build/deploy scripts
├── drivers/          # Driver integration tools
└── applications/     # User applications
```

## Common Commands

```bash
# From HPS/ directory:

# Build everything (applications)
make

# Build Linux image (requires root)
sudo make linux-image

# Build specific component
make kernel
sudo make rootfs
sudo make sd-image
make calculator_test
make led_examples

# Clean builds
make clean

# Help
make help
```

## Troubleshooting

- **Permission denied**: Use `sudo` for rootfs and image builds
- **Toolchain not found**: Install `gcc-arm-linux-gnueabihf`
- **flex/bison not found**: Install kernel build dependencies: `sudo apt-get install flex bison libssl-dev libncurses-dev bc`
- **Image not found**: Build kernel and rootfs first: `sudo make linux-image`
- **Kernel source incomplete**: Run `cd HPS/linux_image/kernel && make kernel-distclean && make kernel-download`
- **No defconfig found**: The build system will automatically find the correct defconfig

See [linux_image/BUILD_INSTRUCTIONS.md](linux_image/BUILD_INSTRUCTIONS.md) for detailed troubleshooting.
