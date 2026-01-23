# Deployment Scripts for DE10-Nano

This directory contains scripts for building and deploying Linux images to the DE10-Nano.

## Quick Start

```bash
# Build complete Linux image
./Scripts/build_linux_image.sh

# Deploy to SD card
sudo ./Scripts/deploy_image.sh /dev/sdX
```

## Scripts

### build_linux_image.sh

Unified build script that orchestrates the entire Linux image build process.

**Usage:**
```bash
./Scripts/build_linux_image.sh [OPTIONS]
```

**Options:**
- `--no-fpga` - Skip FPGA build
- `--no-kernel` - Skip kernel build
- `--no-rootfs` - Skip rootfs build
- `--no-image` - Skip image creation
- `--skip-existing` - Skip builds if output exists
- `--help` - Show help message

**What it builds:**
1. FPGA bitstream (if BUILD_FPGA=yes)
2. Preloader and U-Boot (if SoC EDS available)
3. Device tree
4. Linux kernel with FPGA drivers
5. Root filesystem with network/SSH
6. Complete SD card image

**Example:**
```bash
# Build everything
./Scripts/build_linux_image.sh

# Build only kernel and rootfs (skip FPGA)
./Scripts/build_linux_image.sh --no-fpga

# Build without creating image
./Scripts/build_linux_image.sh --no-image
```

### deploy_image.sh

Deploys pre-built image to SD card.

**Usage:**
```bash
sudo ./Scripts/deploy_image.sh <SD_CARD_DEVICE> [OPTIONS]
```

**Arguments:**
- `SD_CARD_DEVICE` - SD card device (e.g., `/dev/sdb`, `/dev/mmcblk0`)

**Options:**
- `-i, --image FILE` - Image file path (default: `HPS/build/de10-nano-custom.img`)
- `-f, --force` - Skip confirmation prompts
- `-h, --help` - Show help message

**Example:**
```bash
# Deploy to SD card
sudo ./Scripts/deploy_image.sh /dev/sdb

# Deploy custom image
sudo ./Scripts/deploy_image.sh /dev/sdb -i /path/to/custom.img

# Deploy without confirmation
sudo ./Scripts/deploy_image.sh /dev/sdb --force
```

**WARNING:** This will overwrite all data on the SD card!

### check_dependencies.sh

Checks if all required tools and dependencies are installed.

**Usage:**
```bash
./Scripts/check_dependencies.sh
```

**What it checks:**
- Basic build tools (make, git, bash, etc.)
- Cross-compilation toolchain
- Kernel build tools
- Rootfs build tools (debootstrap, qemu-user-static)
- SD card image tools (parted, mkfs, etc.)
- FPGA build tools (Quartus, SoC EDS)

**Example:**
```bash
# Check dependencies
./Scripts/check_dependencies.sh

# Install missing dependencies based on output
```

## Configuration

Build configuration is managed via `HPS/build_config.sh`. You can:

1. **Source the config file:**
   ```bash
   source HPS/build_config.sh
   ```

2. **Set environment variables:**
   ```bash
   export NETWORK_MODE=static
   export STATIC_IP=192.168.1.100
   export SSH_ENABLED=yes
   ./Scripts/build_linux_image.sh
   ```

3. **Edit the config file directly:**
   ```bash
   nano HPS/build_config.sh
   ```

## Workflow

### Complete Build and Deploy

```bash
# 1. Check dependencies
./Scripts/check_dependencies.sh

# 2. Build complete image
./Scripts/build_linux_image.sh

# 3. Deploy to SD card
sudo ./Scripts/deploy_image.sh /dev/sdb

# 4. Insert SD card and boot DE10-Nano
# 5. Connect via SSH: ssh root@<board-ip>
```

### Incremental Build

```bash
# Build only what changed
./Scripts/build_linux_image.sh --skip-existing

# Or build individual components
cd HPS/kernel && make
cd ../rootfs && sudo make
cd .. && sudo make sd-image
```

## Troubleshooting

### Build Fails

1. Check dependencies: `./Scripts/check_dependencies.sh`
2. Verify disk space (build requires ~10GB)
3. Check build logs for specific errors
4. Ensure required tools are in PATH

### Image Creation Fails

1. Ensure you have root access
2. Check that all components are built:
   - FPGA RBF file
   - Preloader and U-Boot
   - Kernel image
   - Rootfs tarball
3. Verify loop device is available (Linux)

### Deployment Fails

1. Verify SD card device path
2. Ensure SD card is not mounted
3. Check write permissions
4. Verify image file exists and is valid

## See Also

- `HPS/linux_image/kernel/README.md` - Kernel build documentation
- `HPS/linux_image/rootfs/README.md` - Rootfs build documentation
- `documentation/deployment/quick_start.md` - Quick start guide
- `documentation/deployment/deployment_workflow.md` - Detailed deployment workflow
