# DE10-Nano Deployment Guide

Complete guide for building, deploying, and running the DE10-Nano low-latency market analysis system.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Build Process](#build-process)
- [Parallelization](#parallelization)
- [Caching](#caching)
- [Deployment](#deployment)
- [Network Setup](#network-setup)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### One-Command Build (Recommended)

```bash
# From repository root - builds everything with parallelization
make everything
```

This runs FPGA and HPS builds in parallel, then creates the SD card image.

### Deploy & Run

```bash
# Flash SD card (replace /dev/sdX)
sudo dd if=HPS/linux_image/build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress conv=fsync

# Boot DE10-Nano and connect
ssh root@<board-ip>
./calculator_test
```

### Component Builds (Alternative)

```bash
# Build individual components from repo root
make fpga          # FPGA only (~20-30 min)
make kernel        # Kernel only (~10-20 min)
make rootfs        # Rootfs only (~15-25 min)
make sd-image      # SD image (requires FPGA artifacts)
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
- **ARM cross-compiler**: `gcc-arm-linux-gnueabihf`
- **SSH client**

### Known Issues
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
Makefile (repo root)     → Top-level orchestration
├── FPGA/Makefile        → FPGA build (QSys, Quartus, DTB)
└── HPS/
    ├── Makefile         → HPS orchestration
    └── linux_image/
        ├── Makefile     → Kernel + rootfs + SD image
        ├── kernel/      → Kernel with ccache support
        └── rootfs/      → Rootfs with base caching
```

### Build Commands

| Command | Description | Time |
|---------|-------------|------|
| `make everything` | Full parallel build | ~35-50 min |
| `make fpga` | FPGA only (QSys + Quartus + RBF + DTB) | ~20-30 min |
| `make kernel` | Linux kernel only | ~10-20 min |
| `make rootfs` | Root filesystem only | ~15-25 min |
| `make sd-image` | SD card image | ~2-5 min |
| `make sd-image-update` | Incremental SD update | ~1-2 min |

### Status and Diagnostics

```bash
make status          # Show all build artifact status
make timing-report   # Show build timing statistics
make help            # Show all available targets
```

---

## Parallelization

The build system uses multiple levels of parallelization:

### Level 1: FPGA + HPS Parallel
```bash
make everything              # FPGA and HPS build simultaneously
make everything-sequential   # Force sequential (low memory systems)
```
**Configuration:** `PARALLEL_EVERYTHING=1/0`

### Level 2: Kernel + Rootfs Parallel
```bash
make sd-image    # Kernel and rootfs build simultaneously
```
**Configuration:** `PARALLEL_BUILD=1/0`, `PARALLEL_JOBS=N`

### Level 3: Quartus Parallel Compilation
Quartus uses all CPU cores automatically for FPGA synthesis.
**Configuration:** `QUARTUS_PARALLEL_JOBS=N` (default: auto-detect)

### Level 4: Applications Parallel
```bash
make applications   # All apps build simultaneously
```
**Configuration:** `PARALLEL_APPS=1/0`

### Build Time Comparison

| Mode | Estimated Time | Use Case |
|------|----------------|----------|
| Full parallel | ~35-50 min | Normal builds |
| Sequential | ~60-90 min | Low memory, debugging |
| Incremental | ~5-15 min | After small changes |

---

## Caching

### Tool Detection Cache
Quartus/QSys paths are cached for 60 minutes to avoid slow filesystem searches.
```bash
make clear-tool-cache   # Force re-detection
make show-tool-cache    # Display cached paths
```

### Rootfs Base Cache
Debootstrap base image is cached and reused. Only rebuilds when `packages.txt` changes.
```bash
make show-cache-status  # Check cache validity
make clean-base         # Force base rebuild
```

### Kernel ccache
Install ccache for 50-80% faster kernel rebuilds:
```bash
sudo apt install ccache
# Automatically enabled if available
```
**Configuration:** `USE_CCACHE=1/0`

### Build Outputs

| Component | Output | Build Time |
|-----------|--------|------------|
| FPGA RBF | `FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf` | 15-25 min |
| Device Tree | `FPGA/generated/soc_system.dtb` | 1 min |
| Kernel | `HPS/linux_image/kernel/build/arch/arm/boot/zImage` | 10-20 min |
| Rootfs | `HPS/linux_image/rootfs/build/rootfs.tar.gz` | 15-25 min |
| SD Image | `HPS/linux_image/build/de10-nano-custom.img` | 2-5 min |

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
| **Quartus not found** | `export PATH="$PATH:/mnt/c/intelFPGA/20.1/quartus/bin"` |
| **Build deps missing** | `make deps` |
| **SD card issues** | Check `lsblk`, try different card |
| **No network** | `sudo dhclient eth0` |
| **FPGA not loaded** | Check `/sys/class/fpga_manager/fpga0/state` |
| **Tests fail** | Ensure bridges enabled, run as root |

### Recovery Commands

```bash
# From repo root - check status
make status          # Show what's built/missing
make timing-report   # Show last build times

# Clean operations (parallel by default)
make clean           # Clean artifacts, preserve caches
make clean-all       # Deep clean including all caches

# Force rebuilds
make everything FORCE_REBUILD=1  # Force full rebuild

# Individual component rebuilds
make fpga-clean && make fpga     # FPGA only
make kernel FORCE_REBUILD=1      # Force kernel rebuild
make rootfs clean-base           # Force rootfs base rebuild
```

### WSL-Specific Issues

| Issue | Solution |
|-------|----------|
| **tar failed (debootstrap)** | Build on native Linux filesystem or increase WSL memory |
| **Clock skew** | Run `sudo hwclock -s` |
| **Slow builds** | Use WSL native fs (`~/`) not Windows fs (`/mnt/c/`) |
| **Line endings** | Build system auto-normalizes (handled) |

### Performance Tuning

```bash
# Low memory systems
make everything PARALLEL_EVERYTHING=0 PARALLEL_BUILD=0

# Maximum performance
sudo apt install ccache
make everything PARALLEL_JOBS=4

# Skip FPGA rebuild (use existing artifacts)
make sd-image  # Only checks for FPGA artifacts, doesn't rebuild
```

### Known Limitations
- **WSL on /mnt/c/**: Slower and may have tar issues (use native fs when possible)
- **First build**: No cache benefits, subsequent builds much faster
