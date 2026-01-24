# DE10-Nano Deployment Guide

Complete guide for building, deploying, and running the DE10-Nano low-latency market analysis system.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Build Process](#build-process)
- [Deployment](#deployment)
- [Network Setup](#network-setup)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 3-Step Build Process

```bash
# 1. Build FPGA bitstream
cd FPGA && make qsys-generate && make sof && make rbf

# 2. Build Linux system
cd ../HPS/linux_image && sudo make kernel && sudo make rootfs

# 3. Create SD card image
sudo make sd-image
```

### Deploy & Run

```bash
# Flash SD card (replace /dev/sdX)
sudo dd if=build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress

# Boot DE10-Nano and connect
ssh root@<board-ip> && cd /root && ./calculator_test
```

---

## Prerequisites

### Hardware
- **DE10-Nano board**
- **MicroSD card** (8GB+)
- **Ethernet cable**
- **USB-to-UART cable** (optional, for debugging)
- **USB-Blaster II** (optional, for JTAG)

### Software
- **Linux environment** (WSL2 recommended for Windows)
- **Intel Quartus Prime Lite 20.1**
- **Intel SoC EDS 20.1** (optional, use prebuilt bootloaders)
- **ARM cross-compiler**: `gcc-arm-linux-gnueabihf`
- **SSH client**

### Known Issues
- **SoC EDS 20.1**: Python XML bugs → Use prebuilt bootloader binaries
- **CRLF line endings**: Build system auto-normalizes scripts

### Setup
```bash
cd HPS/linux_image && make deps  # Install dependencies
which quartus  # Verify Quartus installation
```

---

## Build Process

### Build Hierarchy
```
FPGA/ → Quartus FPGA project (HDL, QSys, bitstreams)
HPS/linux_image/ → Linux build system (kernel, rootfs, SD image)
```

### Build Options

**Complete build:**
```bash
cd HPS && make everything  # FPGA + Linux + SD image
```

**Component builds:**
```bash
# FPGA
cd FPGA && make qsys-generate && make sof && make rbf

# Linux components
cd ../HPS/linux_image
sudo make kernel     # Kernel (~5-15min)
sudo make rootfs     # Rootfs (~10-20min)
sudo make sd-image   # SD image (~2-5min)
```

### Build Features
- **Incremental builds** (massive time savings - only rebuilds when sources change)
- **Automatic error recovery** (CRLF normalization, internet checks)
- **Cross-platform support** (Windows/WSL/Linux path handling)
- **Flexible targets** (individual component builds)
- **Dependency management** (`make deps`)

**Check for rebuilds before building:**
```bash
# Check if kernel needs rebuild
cd HPS/linux_image && make check-rebuild

# Check if rootfs needs rebuild
cd rootfs && make check-rebuild
```

### Build Outputs

| Component | Output | Time |
|-----------|--------|------|
| FPGA | `FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf` | 5-15min |
| Kernel | `HPS/linux_image/kernel/build/arch/arm/boot/zImage` | 5-15min |
| Rootfs | `HPS/linux_image/rootfs/build/rootfs.tar.gz` | 10-20min |
| SD Image | `HPS/linux_image/build/de10-nano-custom.img` | 2-5min |

---

## Deployment

### SD Card (Primary Method)
```bash
lsblk  # Find SD card device
sudo dd if=HPS/linux_image/build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress conv=fsync
```

**Windows:** Use balenaEtcher, Win32DiskImager, or Rufus

### JTAG (Development)
```bash
# Load FPGA via JTAG
quartus_pgm -c "USB-Blaster" -m JTAG -o "p;FPGA/build/output_files/DE10_NANO_SoC_GHRD.sof"

# Deploy via network
scp zImage root@<board-ip>:/boot/
scp rootfs.tar.gz root@<board-ip>:/tmp/ && ssh root@<board-ip> "tar xzf /tmp/rootfs.tar.gz -C /"
```

### Boot Sequence
1. Power on DE10-Nano (with SD card or JTAG)
2. Wait 30-60s for Linux boot
3. FPGA bitstream loads automatically
4. HPS-FPGA communication initializes

---

## Network Setup

### Automatic Configuration
- **DHCP**: Enabled by default
- **SSH**: Pre-installed and running
- **Hostname**: `de10-nano`

### Finding Board IP
```bash
# Router DHCP table or network scan
nmap -sn 192.168.1.0/24

# Via serial console
ip addr show eth0
```

### SSH Access
```bash
ssh root@<board-ip>  # Password: root
```

### Manual Configuration
```bash
# Static IP (on board)
sudo nano /etc/network/interfaces
# Add: iface eth0 inet static; address 192.168.1.100; netmask 255.255.255.0; gateway 192.168.1.1
sudo systemctl restart networking
```

### Architecture Notes
- Uses **HPS Ethernet** (not FPGA Ethernet)
- **GMAC controller** at `0xFF702000`
- **STMMAC driver** in Linux kernel

---

## Network Configuration

### Ethernet Architecture

The DE10-Nano uses **HPS Ethernet** (not FPGA Ethernet):
- **Hardware**: Gigabit Ethernet MAC (GMAC) in HPS
- **Address**: `0xFF702000` (GMAC1)
- **Interface**: RGMII to RJ-45 connector
- **Driver**: STMMAC Ethernet driver

### Automatic Configuration

The build system pre-configures networking:
- **DHCP client** enabled by default
- **SSH server** pre-installed and running
- **Hostname**: `de10-nano`
- **Firewall**: Basic configuration applied

### Finding Board IP Address

```bash
# Method 1: Check router DHCP table
# Look for hostname: de10-nano

# Method 2: Network scan
nmap -sn 192.168.1.0/24

# Method 3: Via serial console (if connected)
ip addr show eth0
```

### SSH Access

```bash
ssh root@<board-ip>
# Password: root (change after first login)
```

### Manual Network Configuration

**Static IP (on the board):**
```bash
# Edit /etc/network/interfaces
sudo nano /etc/network/interfaces

# Add:
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1

# Restart networking
sudo systemctl restart networking
```

**Internet sharing (via USB Ethernet dongle):**
- Enable Internet Sharing on host machine
- Connect dongle to DE10-Nano USB port
- DHCP will assign IP automatically

---

## Testing and Validation

### Build Verification

**Check all components exist:**
```bash
# FPGA bitstream
ls -la FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf

# Linux kernel
ls -la HPS/linux_image/kernel/build/arch/arm/boot/zImage

# Root filesystem
ls -la HPS/linux_image/rootfs/build/rootfs.tar.gz

# SD image
ls -la HPS/linux_image/build/de10-nano-custom.img
```

### Runtime Validation

**FPGA status:**
```bash
# Check FPGA manager state
cat /sys/class/fpga_manager/fpga0/state
# Should show: operating

# Check FPGA bridges
ls /sys/class/fpga_bridge/
cat /sys/class/fpga_bridge/*/state
# Should show: enabled
```

**Network connectivity:**
```bash
# Check interface
ip addr show eth0

# Test connectivity
ping -c 3 8.8.8.8
ping -c 3 google.com
```

**HPS-FPGA communication:**
```bash
# Run calculator tests
cd /root
./calculator_test

# Expected: All 30 tests pass
```

### System Health
```bash
# Resources & logs
top && df -h && dmesg | tail -10

# FPGA access
ls /dev/uio* /dev/fpga*
```

---

## Troubleshooting

### Quick Issue Resolution

| Issue | Quick Fix |
|-------|-----------|
| **CRLF errors** | Build system auto-normalizes; use Linux editors |
| **SoC EDS fails** | Use prebuilt bootloaders (recommended) |
| **Quartus not found** | `export PATH="$PATH:/mnt/c/intelFPGA/20.1/quartus/bin"` |
| **Build deps missing** | `make deps` |
| **SD card issues** | Check `lsblk`, try different card |
| **No network** | `sudo dhclient eth0` |
| **FPGA not loaded** | Check `/sys/class/fpga_manager/fpga0/state` |
| **Tests fail** | Ensure bridges enabled, run as root |

### SoC EDS Workarounds

**For SoC EDS 20.1 Python XML bugs:**
```bash
# Get prebuilt binaries from Terasic System CD
cp preloader-mkpimage.bin HPS/preloader/
cp u-boot.img HPS/preloader/uboot-socfpga/

# Build with prebuilts
sudo PRELOADER_BIN=HPS/preloader/preloader-mkpimage.bin \
     UBOOT_IMG=HPS/preloader/uboot-socfpga/u-boot.img \
     make sd-image
```

### Recovery Commands

```bash
# Check if rebuild is needed (recommended first step)
make check-rebuild  # Shows what changed, if anything

# Complete rebuild (when changes detected)
cd HPS/linux_image && sudo make clean && sudo make linux-image

# Force rebuilds (ignore incremental detection)
sudo make rebuild   # Force kernel rebuild
sudo make force-rebuild  # Alias for rebuild

# Component rebuilds
sudo make clean-kernel && sudo make kernel    # Kernel only
sudo make clean-rootfs && sudo make rootfs    # Rootfs only
sudo make clean-sd-image && sudo make sd-image # SD image only

# FPGA rebuild
cd FPGA && make clean && make qsys-generate sof rbf
```

### Known Limitations
- **SoC EDS 20.1**: Use prebuilt bootloaders (recommended workaround)
- **Windows/WSL**: Path handling requires careful setup
- **FPGA management**: Manual bitstream handling required
