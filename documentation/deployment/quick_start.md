# DE10-Nano Quick Start Guide

Minimal steps to build, deploy, and run the system on the DE10-Nano board.

## Prerequisites

- DE10-Nano development board
- MicroSD card (8GB+)
- WSL2 or Linux environment
- Intel Quartus Prime (for FPGA builds)
- ARM cross-compiler: `arm-linux-gnueabihf-gcc`

## Quick Build (3 Steps)

### Step 1: Build FPGA Bitstream

```bash
cd FPGA
make qsys-generate    # Generate QSys system
make sof              # Compile FPGA design (~10-15 min)
make rbf              # Convert to RBF format
```

**Output:** `build/output_files/DE10_NANO_SoC_GHRD.rbf`

### Step 2: Build Linux System

```bash
cd HPS/linux_image
sudo make kernel      # Build kernel (~10-15 min)
sudo make rootfs      # Build Debian rootfs (~15-20 min)
```

### Step 3: Create SD Card Image

```bash
cd HPS/linux_image
sudo make sd-image    # Create bootable image (~2-3 min)
```

**Output:** `HPS/linux_image/build/de10-nano-custom.img` (4GB)

## Deploy to SD Card

```bash
# Find SD card device
lsblk

# Write image (replace /dev/sdX with your device)
sudo dd if=HPS/linux_image/build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress conv=fsync
```

Or on Windows: Use **balenaEtcher** or **Win32DiskImager**.

## Boot and Connect

1. Insert SD card into DE10-Nano
2. Connect Ethernet cable
3. Power on board
4. Wait ~30 seconds for Linux to boot

### Find Board IP

```bash
# Check router DHCP table, or scan network:
nmap -sn 192.168.1.0/24
```

### SSH Access

```bash
ssh root@<board-ip>
# Password: root
```

## Run Tests

```bash
# On the DE10-Nano board
cd /root
./calculator_test
```

**Expected:** All 30 tests pass (HPS-FPGA communication verified).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| FPGA not configured | Check `cat /sys/class/fpga_manager/fpga0/state` - should show "operating" |
| No network | Run `sudo dhclient eth0` to request DHCP |
| Tests fail | Ensure FPGA is configured and running as root |
| Build fails | Run `make deps` first to install dependencies |

## Next Steps

- [Deployment Workflow](deployment_workflow.md) - Detailed deployment guide
- [Build Hierarchy](build_hierarchy.md) - Understanding the build system
- [Ethernet Setup](ethernet_setup.md) - Network configuration
