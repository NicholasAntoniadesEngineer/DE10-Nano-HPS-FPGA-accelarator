# DE10-Nano Deployment Workflow Guide

Complete step-by-step workflow from building all components to deploying and running the system on the DE10-Nano board.

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEVELOPMENT MACHINE                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
        ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
        │ Build FPGA       │  │ Build HPS    │  │ Prepare      │
        │ Bitstream        │  │ Software     │  │ Deployment   │
        └──────────────────┘  └──────────────┘  └──────────────┘
                    │               │               │
        ┌───────────┼───────────────┼───────────────┼───────────┐
        │           │               │               │           │
        ▼           ▼               ▼               ▼           ▼
    ┌────────┐ ┌────────┐    ┌──────────┐    ┌──────────┐ ┌──────────┐
    │Generate│ │Compile │    │Cross-    │    │Build     │ │Deployment│
    │QSys    │ │Quartus │    │Compile   │    │Userspace │ │Method    │
    │        │ │        │    │Test Suite│    │Drivers   │ │          │
    └────────┘ └────────┘    └──────────┘    └──────────┘ └──────────┘
        │           │               │               │           │
        └───────────┼───────────────┼───────────────┼───────────┘
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
            │ Create RBF   │ │ Test Suite    │ │ Drivers       │
            │ File         │ │ Binary        │ │ Binary        │
            └───────────────┘ └───────────────┘ └───────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Deployment Method    │
                        │      (Choose One)     │
                        └───────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │  SD Card     │      │    JTAG     │      │   Network    │
    │  (Permanent) │      │ (Temporary) │      │  (Dynamic)   │
    └──────────────┘      └──────────────┘      └──────────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   DE10-Nano Board     │
                        └───────────────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │  Boot Linux   │
                            └───────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ Load FPGA Bitstream   │
                        └───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   Load Drivers        │
                        └───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │     Run Tests         │
                        └───────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Runtime Control      │
                        │  & Monitoring         │
                        └───────────────────────┘
```

**Workflow Phases:**
1. **Development Machine** → Build FPGA Bitstream, HPS Software, Prepare Deployment
2. **Deployment** → Choose method (SD Card, JTAG, or Network) → Transfer to Board
3. **Board Setup** → Boot Linux → Load FPGA Bitstream → Load Drivers
4. **Execution** → Run Tests → Runtime Control & Monitoring

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Build All Components](#phase-1-build-all-components)
3. [Phase 2: Deploy to DE10-Nano](#phase-2-deploy-to-de10-nano)
4. [Phase 3: Load Drivers and Configure System](#phase-3-load-drivers-and-configure-system)
5. [Phase 4: Run Tests](#phase-4-run-tests)
6. [Phase 5: Runtime Control and Monitoring](#phase-5-runtime-control-and-monitoring)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

- Terasic DE10-Nano development board
- MicroSD card (8GB+ recommended)
- Ethernet cable (for network deployment)
- USB-to-UART cable (optional, for serial console)
- USB-Blaster II or compatible JTAG programmer (for JTAG deployment)

> **Building from Scratch?** See [Quick Start Guide](quick_start.md) for minimal build steps, or [Build Hierarchy](build_hierarchy.md) for understanding the complete build process.

### Software Requirements

- Intel Quartus Prime (for FPGA compilation)
- ARM cross-compiler: `gcc-arm-linux-gnueabihf` (for HPS software)
- SSH client (for network deployment)
- Terminal emulator (PuTTY, minicom, screen) for serial console

### Initial Board Setup

1. **Write Linux Image to SD Card**
   ```bash
   # Using custom-built image (from HPS/linux_image/build/)
   sudo dd if=HPS/linux_image/build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress conv=fsync
   
   # Windows: Use Win32DiskImager or balenaEtcher
   ```
   
   > **Note:** To build the SD image from scratch, see [Quick Start Guide](quick_start.md)

2. **Boot DE10-Nano**
   - Insert SD card
   - Connect Ethernet cable
   - Power on board
   - Wait for Linux to boot

3. **Find Board IP Address**
   ```bash
   # On board (via serial console or if you can access it)
   ip addr show
   
   # Or check your router's DHCP table
   # Or use network scanner: nmap -sn 192.168.1.0/24
   ```

4. **Configure Network (if needed)**
   - See [Network Configuration](#network-configuration) section below
   - Or refer to [Ethernet Setup](ethernet_setup.md) for detailed network setup

---

## Phase 1: Build All Components

### 1.1 Build FPGA Bitstream

**Location:** `FPGA/` directory

**Steps:**

```bash
cd FPGA

# Step 1: Generate QSys system (REQUIRED FIRST)
make qsys-generate

# Step 2: Compile FPGA design
make sof

# Step 3: Convert to RBF format for SD card boot
make rbf
```

**Outputs:**
- `FPGA/build/output_files/DE10_NANO_SoC_GHRD.sof` - For JTAG programming
- `FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf` - For SD card boot

**Build Time:** ~10-30 minutes depending on design complexity

**Important Notes:**
- QSys generation **MUST** be completed before Quartus compilation
- The QSys system generates the `soc_system` module that the top-level design instantiates
- If you see "undefined entity 'soc_system'" error, run `make qsys-generate` first

### 1.2 Build HPS Software

**Location:** `HPS/` directory

**Steps:**

```bash
cd HPS

# Build all HPS components (cross-compiled for ARM)
make

# Or build specific components:
make calculator_test
make led_examples
```

**Outputs:**
- `HPS/calculator_test/calculator_test` - ARM executable
- `HPS/led_examples/basic/HPS_FPGA_LED` - Basic LED example
- `HPS/led_examples/advanced/hps_fpga_led_control` - Advanced LED example

**Build Time:** ~1-2 minutes

**Important Notes:**
- Requires ARM cross-compiler: `gcc-arm-linux-gnueabihf`
- Can also build natively on board: `make CROSS_COMPILE=`

---

## Phase 2: Deploy to DE10-Nano

### 2.1 Initial Setup (One-Time)

**Prerequisites:**
1. Prebuilt Linux image written to SD card
2. DE10-Nano booted and accessible via network (SSH) or serial console
3. Board IP address known (if using network)

**Connect to Board:**

```bash
# Option 1: SSH (if Ethernet connected)
ssh root@<board-ip-address>

# Option 2: Serial console (USB-to-UART cable)
# Use PuTTY, minicom, or screen:
# Windows: PuTTY (COM port, 115200 baud)
# Linux: screen /dev/ttyUSB0 115200
```

**Find Board IP Address:**
```bash
# On board (via serial console or if accessible)
ip addr show

# Or check your router's DHCP table
# Or use network scanner: nmap -sn 192.168.1.0/24
```

### 2.2 Deploy FPGA Bitstream

Choose one of three deployment methods based on your needs:

#### Method 1: SD Card (Permanent - Recommended)

**Best for:** Production deployments, permanent configurations

**Steps:**

```bash
# On development machine
# 1. Mount SD card FAT partition
# Windows: SD card appears as removable drive
# Linux: mount /dev/sdX1 /mnt/sdcard

# 2. Copy RBF file
cp FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf /mnt/sdcard/soc_system.rbf

# 3. Unmount SD card
# Windows: Safely eject
# Linux: umount /mnt/sdcard

# 4. Set MSEL switches on board to 001000 (MSEL=8)
# 5. Power cycle board - FPGA configures automatically
```

**Advantages:**
- Permanent configuration (survives power cycles)
- Automatic loading on boot
- No network or JTAG required

**Disadvantages:**
- Requires physical access to SD card
- Slower update cycle

#### Method 2: JTAG (Temporary - Development)

**Best for:** Rapid development, testing, debugging

**Steps:**

```bash
# On development machine
cd FPGA
make program_fpga

# Or manually:
quartus_pgm --mode=jtag --operation=p\;build/output_files/DE10_NANO_SoC_GHRD.sof@2
```

**Advantages:**
- Fast deployment (~10-30 seconds)
- No SD card access needed
- Good for iterative development

**Disadvantages:**
- Configuration lost on power cycle
- Requires JTAG hardware
- Must be done from development machine

#### Method 3: Runtime Load from HPS (Dynamic)

**Best for:** Remote updates, testing without physical access

**Steps:**

```bash
# On DE10-Nano board
# 1. Transfer RBF file to board (via network or SD card)
scp FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf root@<board-ip>:/root/soc_system.rbf

# 2. Load FPGA bitstream
echo soc_system.rbf > /sys/class/fpga_manager/fpga0/firmware

# 3. Verify FPGA is configured
cat /sys/class/fpga_manager/fpga0/state
# Should show: "operating"
```

**Advantages:**
- Remote deployment
- No physical access needed
- Can be scripted/automated

**Disadvantages:**
- Requires network connection
- Configuration lost on power cycle (unless also on SD card)
- Requires Linux to be running

### 2.3 Deploy HPS Software

**Transfer Files to Board:**

```bash
# On development machine
# Transfer test suite
scp HPS/calculator_test/calculator_test root@<board-ip>:/root/

# Transfer LED examples (optional)
scp HPS/led_examples/basic/HPS_FPGA_LED root@<board-ip>:/root/
scp HPS/led_examples/advanced/hps_fpga_led_control root@<board-ip>:/root/

# Make executable
ssh root@<board-ip> "chmod +x /root/calculator_test"
```

**Or Clone Entire Repository on Board:**

```bash
# SSH to board
ssh root@<board-ip>
cd /root
git clone <repository-url>
cd low-latency-market-analysis/HPS
make CROSS_COMPILE=  # Native compilation on board
```

**Automated Deployment (Recommended):**

```bash
# From repository root
./Scripts/deploy_to_board.sh -i <board-ip>
```

---

## Phase 3: Load Drivers and Configure System

### 3.1 Verify FPGA Configuration

**On DE10-Nano board:**

```bash
# Check FPGA state
cat /sys/class/fpga_manager/fpga0/state
# Should show: "operating" when configured

# Check memory mapping
cat /proc/iomem | grep -i fpga
# Should show: ff200000-ff3fffff : ff200000.lw-bridge
```

**If FPGA is not configured:**
- For SD card method: Check MSEL switches and RBF file on FAT partition
- For JTAG method: Re-run `make program_fpga`
- For runtime method: Reload bitstream: `echo soc_system.rbf > /sys/class/fpga_manager/fpga0/firmware`

### 3.2 Load UIO Drivers (For Advanced Examples)

**On DE10-Nano board:**

```bash
# Load UIO kernel modules
modprobe uio
modprobe uio_pdrv_genirq

# Verify modules loaded
lsmod | grep uio

# Make persistent (add to /etc/modules)
echo "uio" >> /etc/modules
echo "uio_pdrv_genirq" >> /etc/modules
```

**Note:** UIO drivers are only needed for advanced LED example. Basic examples use `/dev/mem` directly.

### 3.3 Device Tree Overlay (If Using UIO)

**On DE10-Nano board:**

```bash
# Compile device tree overlay (if using advanced LED example)
cd HPS/led_examples/advanced
dtc -@ -I dts -O dtb -o fpga-leds.dtbo fpga-leds.dts

# Load overlay
mkdir -p /config/device-tree/overlays
cp fpga-leds.dtbo /config/device-tree/overlays/

# Verify overlay loaded
ls /config/device-tree/overlays/
```

---

## Phase 4: Run Tests

### 4.1 Run Calculator Test Suite

**On DE10-Nano board:**

```bash
cd /root
chmod +x calculator_test

# Run with default output (INFO level)
sudo ./calculator_test

# Run with verbose output (DEBUG level)
sudo ./calculator_test -v

# Run with trace output (TRACE level - maximum detail)
sudo ./calculator_test -vv

# Quick mode (no delays between tests)
sudo ./calculator_test -q
```

**Expected Output:**
```
========================================================================
                   FPGA CALCULATOR TEST SUITE
========================================================================
Hardware-Accelerated Floating Point Calculator Verification
DE10-Nano SoC - HPS to FPGA Communication Test
========================================================================

Initializing calculator driver...
Calculator driver initialized
  Physical base: 0xFF280000
  Virtual base:  0xb6f80000

✓ Calculator driver initialized successfully

Running 30 test cases...

[Test 1/30] Basic addition: 1.0 + 2.0 = 3.0
  Status:       ✓ PASS

[... 29 more tests ...]

========================================================================
                        TEST SUMMARY
========================================================================
Total tests:    30
Passed:         30
Failed:         0
Success rate:   100.0%
========================================================================
✓ ALL TESTS PASSED!
```

### 4.2 Run LED Examples

**Basic LED Example:**

```bash
# On DE10-Nano board
sudo ./HPS_FPGA_LED
```

**Advanced LED Example (Requires UIO Setup):**

```bash
# On DE10-Nano board
cd HPS/led_examples/advanced
sudo ./hps_fpga_led_control
```

**Remote Test Execution:**

```bash
# From development machine
./Scripts/remote_test.sh -i <board-ip>

# With verbose output
./Scripts/remote_test.sh -i <board-ip> -a "-v"

# Run LED examples
./Scripts/remote_test.sh -i <board-ip> -t led_basic
./Scripts/remote_test.sh -i <board-ip> -t led_advanced
```

---

## Phase 5: Runtime Control and Monitoring

### 5.1 Network Interface (SSH)

**Primary interface for development:**

**Connect to Board:**
```bash
# Basic connection
ssh root@<board-ip>

# Default password is usually "root" or "altera"
# Change password after first login:
passwd
```

**Transfer Files:**
```bash
# Copy file to board
scp file.txt root@<board-ip>:/root/

# Copy directory
scp -r HPS/calculator_test root@<board-ip>:/root/

# Copy from board to development machine
scp root@<board-ip>:/root/log.txt ./
```

**Execute Commands Remotely:**
```bash
# Run single command
ssh root@<board-ip> "cd /root && ./calculator_test"

# Run with output
ssh root@<board-ip> "./calculator_test -v"

# Interactive session
ssh root@<board-ip>
```

### 5.2 Network Configuration

**Setup Network Connection:**

```bash
# On board - check network configuration
ip addr show

# If not configured, set static IP (optional)
# Edit /etc/network/interfaces:
# auto eth0
# iface eth0 inet static
#     address 192.168.1.100
#     netmask 255.255.255.0
#     gateway 192.168.1.1
# 
# Restart network
# /etc/init.d/networking restart
```

**Ethernet via USB-C Dongle (Mac):**

For detailed Ethernet setup via USB-C dongle, see [Ethernet Setup](ethernet_setup.md).

**Quick Setup:**
```bash
# On board - initialize network via DHCP
sudo dhclient eth0

# Test connection
timeout 5s ping google.com

# Install SSH server (if not present)
sudo apt-get install openssh-server
```

### 5.3 Serial Console (USB-to-UART)

**For low-level debugging and boot monitoring:**

**Hardware Setup:**
- Connect USB-to-UART cable to J7 connector on DE10-Nano
- Connect to development machine USB port

**Windows (PuTTY):**
1. Open PuTTY
2. Connection type: Serial
3. Serial line: COM3 (check Device Manager for correct port)
4. Speed: 115200
5. Data bits: 8, Stop bits: 1, Parity: None
6. Flow control: None
7. Click "Open"

**Linux:**
```bash
# Install screen or minicom
sudo apt-get install screen

# Connect
screen /dev/ttyUSB0 115200

# Exit: Ctrl+A then K, then Y to confirm
```

**Use Cases:**
- Boot monitoring and debugging
- Kernel message viewing
- Recovery when network is down
- Low-level system access

### 5.4 Real-Time Monitoring

**Monitor FPGA State:**
```bash
# Continuous monitoring
watch -n 1 'cat /sys/class/fpga_manager/fpga0/state'

# Check once
cat /sys/class/fpga_manager/fpga0/state
# Should show: "operating" when configured
```

**Monitor System Resources:**
```bash
# Install htop if not available
apt-get install htop

# Monitor CPU, memory, processes
htop
```

**Monitor Kernel Messages:**
```bash
# View recent messages
dmesg | tail -50

# Follow messages in real-time
dmesg -w

# Clear messages
dmesg -C
```

**Check Memory Mappings:**
```bash
# View FPGA memory regions
cat /proc/iomem | grep -i fpga

# Should show: ff200000-ff3fffff : ff200000.lw-bridge
```

**Monitor Test Execution:**
```bash
# Trace system calls
strace -e trace=open,read,write,mmap ./calculator_test

# Monitor file access
strace ./calculator_test 2>&1 | grep -E "(open|read|write)"
```

### 5.5 Remote Development Workflow

**Recommended Setup:**
1. **Development Machine:** Build all components
2. **Network Connection:** SSH for file transfer and remote execution
3. **Serial Console:** For boot debugging (optional)
4. **Version Control:** Clone repo on board for easy updates

**Workflow:**

```bash
# On development machine - build
cd FPGA && make rbf
cd ../HPS && make

# Transfer to board
scp FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf root@<board-ip>:/root/
scp HPS/calculator_test/calculator_test root@<board-ip>:/root/

# Or use automated script
./Scripts/deploy_to_board.sh -i <board-ip>

# On board - update and rebuild (if repo cloned)
ssh root@<board-ip>
cd /root/low-latency-market-analysis
git pull
cd HPS
make CROSS_COMPILE=  # Rebuild on board
```

---

## Quick Reference: Complete Workflow

**From scratch to running tests:**

```bash
# Phase 1: Build
cd FPGA && make qsys-generate && make sof && make rbf
cd ../HPS && make

# Phase 2: Deploy (automated)
./Scripts/deploy_to_board.sh -i <board-ip>

# Phase 3: Verify
ssh root@<board-ip> "cat /sys/class/fpga_manager/fpga0/state"

# Phase 4: Test
./Scripts/remote_test.sh -i <board-ip>
```

---

## Troubleshooting

### FPGA Not Configuring

**Symptoms:**
- `cat /sys/class/fpga_manager/fpga0/state` shows "unknown" or "power off"
- Tests fail with memory access errors

**Solutions:**
1. Check MSEL switches (should be `001000` for SD card boot)
2. Verify RBF file is on FAT partition with correct name (`soc_system.rbf`)
3. Check file size matches expected bitstream size
4. Try JTAG programming to verify bitstream is valid
5. Check boot logs: `dmesg | grep -i fpga`

### Drivers Not Working

**Symptoms:**
- Permission denied errors
- Memory mapping failures
- Tests fail immediately

**Solutions:**
1. Verify FPGA is configured: `cat /sys/class/fpga_manager/fpga0/state`
2. Check memory mapping: `cat /proc/iomem | grep fpga`
3. Ensure running as root: `sudo ./calculator_test`
4. Check `/dev/mem` exists: `ls -l /dev/mem`
5. Verify base address matches QSys configuration

### Network Connection Issues

**Symptoms:**
- Cannot SSH to board
- Network unreachable
- No IP address assigned

**Solutions:**
1. Check Ethernet cable connection
2. Verify DHCP or static IP configuration
3. Check firewall settings: `iptables -L`
4. Ping board from development machine: `ping <board-ip>`
5. Use serial console as fallback to check network status
6. Check network interface: `ip link show`
7. See [Ethernet Setup](ethernet_setup.md) for detailed setup

### Test Failures

**Symptoms:**
- All tests fail
- Incorrect results
- Timeout errors

**Solutions:**
1. Verify FPGA bitstream matches software expectations
2. Check base address matches QSys configuration
3. Review test output with `-v` or `-vv` flags
4. Check kernel messages: `dmesg | tail -50`
5. Verify calculator IP is instantiated in QSys
6. Check clock connections in QSys design
7. Verify reset signals are deasserted

### Build Failures

**FPGA Build:**
- Ensure QSys generation completed: `make qsys-generate`
- Check Quartus is in PATH: `which quartus_sh`
- Verify project files exist: `ls FPGA/quartus/*.qpf`

**HPS Build:**
- Check cross-compiler installed: `arm-linux-gnueabihf-gcc --version`
- Verify Makefile paths are correct
- Check for missing dependencies

### Performance Issues

**Symptoms:**
- Slow test execution
- High CPU usage
- System unresponsive

**Solutions:**
1. Check system load: `top` or `htop`
2. Monitor memory usage: `free -h`
3. Check for background processes
4. Verify FPGA clock frequency matches expectations
5. Check for interrupt conflicts

---

## Additional Resources

- **[Quick Start Guide](quick_start.md)** - Minimal steps for first-time deployment
- **[Build Hierarchy](build_hierarchy.md)** - Understanding the build system components
- **[Ethernet Setup](ethernet_setup.md)** - Network configuration details
- **[HPS Software Documentation](../../HPS/README.md)** - HPS software details
- **[FPGA Build Documentation](../../FPGA/README.md)** - FPGA build system details

---

**Last Updated:** 2026-01-19
