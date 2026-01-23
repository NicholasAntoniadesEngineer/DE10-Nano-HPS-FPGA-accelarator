# HPS Software for DE10-Nano

This directory contains all software for the Hard Processor System (HPS) on the DE10-Nano SoC.

## Directory Structure

```
HPS/
├── linux_image/      # Linux kernel, rootfs, and SD card image
│   ├── kernel/       # Linux kernel build system
│   ├── rootfs/       # Root filesystem build system
│   └── scripts/      # Build and deployment scripts
├── drivers/          # Linux driver integration tools
│   └── integration/ # Driver integration scripts
└── applications/    # User-space applications
    ├── calculator_test/  # Calculator IP test suite
    └── led_examples/     # LED control examples
```

## Quick Start

### Prerequisites

Install dependencies: `sudo apt-get update && sudo apt-get install -y gcc-arm-linux-gnueabihf flex bison libssl-dev libncurses-dev bc debootstrap qemu-user-static parted dosfstools e2fsprogs make git build-essential`

See [documentation/deployment/quick_start.md](../documentation/deployment/quick_start.md) for complete guide.

### Build Applications (Fast - No Root Required)

```bash
cd HPS
make
# Or build specific application:
make calculator_test
make led_examples
```

### Build Linux Image (Slow - Requires Root)

```bash
cd HPS
sudo make linux-image
# Or build components separately:
make kernel              # Build kernel only
sudo make rootfs         # Build rootfs only
sudo make sd-image       # Create SD card image
```

**Note**: First build will download kernel source (~1-2 GB) and may take 45-85 minutes total.

### Deploy to SD Card

```bash
cd HPS/linux_image/scripts
sudo ./deploy_image.sh /dev/sdX
```

## Build System Organization

The HPS build system is organized into three independent sections:

### 1. Linux Image (`linux_image/`)

Complete Linux system build:
- **Kernel**: Linux kernel with FPGA driver support
- **Rootfs**: Debian-based root filesystem with network and SSH
- **SD Image**: Bootable SD card image

**Build independently:**
```bash
cd HPS/linux_image
make kernel        # Build kernel only
sudo make rootfs   # Build rootfs only
sudo make all      # Build complete image
```

### 2. Drivers (`drivers/`)

Linux driver integration tools:
- Integration scripts for kernel modules
- Device tree overlay generation
- Driver testing utilities

**Usage:**
```bash
cd HPS/drivers/integration
./integrate_linux_driver.sh -k /path/to/linux-kernel
```

### 3. Applications (`applications/`)

User-space applications:
- **calculator_test**: Test suite for calculator IP
- **led_examples**: LED control examples

**Build independently:**
```bash
cd HPS/applications
make                    # Build all applications
make calculator_test    # Build calculator test only
make led_examples       # Build LED examples only
```

## Independent Builds

Each section can be built independently to save time:

- **Rebuild applications only**: `cd HPS/applications && make`
- **Rebuild kernel only**: `cd HPS/linux_image && make kernel`
- **Rebuild rootfs only**: `cd HPS/linux_image && sudo make rootfs`
- **Create SD image only**: `cd HPS/linux_image && sudo make sd-image` (requires kernel and rootfs)

## Main Makefile Targets

From `HPS/` directory:

```bash
# Application targets (fast, no root)
make                    # Build all applications (default)
make applications       # Build all applications
make calculator_test    # Build calculator test
make led_examples       # Build LED examples

# Linux image targets (slow, requires root)
sudo make linux-image   # Build complete Linux image
make kernel             # Build kernel only
sudo make rootfs        # Build rootfs only
sudo make sd-image      # Create SD card image

# Other targets
make clean              # Clean all build artifacts
make help               # Show help message
```

## Cross-Compilation

Default toolchain: `arm-linux-gnueabihf-`

Override toolchain:
```bash
make CROSS_COMPILE=arm-none-linux-gnueabihf-
```

Native compilation (on DE10-Nano):
```bash
make CROSS_COMPILE=
```

## Detailed Documentation

- **Linux Image Build**: See [`linux_image/README.md`](linux_image/README.md)
- **Kernel Build**: See [`linux_image/kernel/README.md`](linux_image/kernel/README.md)
- **Rootfs Build**: See [`linux_image/rootfs/README.md`](linux_image/rootfs/README.md)
- **Driver Integration**: See [`drivers/integration/`](drivers/integration/)
- **Calculator Test**: See [`applications/calculator_test/README.md`](applications/calculator_test/README.md)
- **LED Examples**: See [`applications/led_examples/README.md`](applications/led_examples/README.md)

## Deployment Workflow

1. **Build FPGA bitstream** (from `FPGA/` directory):
   ```bash
   cd ../FPGA
   make qsys-generate sof rbf
   ```

2. **Build Linux image**:
   ```bash
   cd ../HPS
   sudo make linux-image
   ```

3. **Deploy to SD card**:
   ```bash
   cd linux_image/scripts
   sudo ./deploy_image.sh /dev/sdX
   ```

4. **Boot DE10-Nano**:
   - Insert SD card
   - Power on board
   - Connect via SSH: `ssh root@<board-ip>` (default password: `root`)

## Troubleshooting

### Build Errors

- **Kernel build fails**: Check cross-compilation toolchain is installed
- **Rootfs build fails**: Requires root access and additional tools (debootstrap, qemu-user-static)
- **Image creation fails**: Requires root access and kernel/rootfs to be built first

### Runtime Issues

- **Ethernet not working**: See [`../documentation/deployment/ethernet_setup.md`](../documentation/deployment/ethernet_setup.md)
- **FPGA not configured**: See [`../documentation/deployment/deployment_workflow.md`](../documentation/deployment/deployment_workflow.md)
- **Driver issues**: See [`../documentation/hps/linux_driver_development.md`](../documentation/hps/linux_driver_development.md)

## See Also

- [Main Project README](../readme.md)
- [Quick Start Guide](../documentation/deployment/quick_start.md)
- [Deployment Workflow](../documentation/deployment/deployment_workflow.md)
