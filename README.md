# DE10-Nano FPGA-Accelerated Market Analysis

Complete hardware-software platform for low-latency FPGA-accelerated computing on the Terasic DE10-Nano SoC board.

## Quick Workflow

1. **Build FPGA Hardware** → Generate bitstream for calculator IP
2. **Build HPS Software** → Compile Linux kernel and applications
3. **Create Boot Image** → Assemble SD card with FPGA + Linux
4. **Deploy & Run** → Flash to DE10-Nano and execute tests

---

## Prerequisites

- **Hardware**: DE10-Nano board + MicroSD card (8GB+)
- **Software**: Quartus Prime Lite 20.1 + ARM cross-compiler
- **OS**: Windows with WSL2 or Linux environment
- **Optional**: DE10-Nano System CD (for prebuilt bootloaders)

---

## 1. FPGA Build Process

**Location**: `FPGA/` directory

### Generate Hardware Design
```bash
cd FPGA
make qsys-generate    # Create QSys system (calculator IP + bridges)
make sof             # Synthesize FPGA design (~5-15 min)
make rbf             # Convert to RBF format for Linux
```

**Output**: `build/output_files/DE10_NANO_SoC_GHRD.rbf`

### What Gets Built
- **Calculator IP**: Hardware-accelerated floating-point operations
- **HPS-FPGA Bridges**: Lightweight (LW) and heavyweight (HW) bridges
- **Device Tree**: Hardware description for Linux kernel
- **Bitstream**: Programmable FPGA configuration

---

## 2. HPS Build Process

**Location**: `HPS/` directory

### Build Linux System
```bash
cd HPS/linux_image
sudo make kernel     # Cross-compile Linux kernel with FPGA drivers
sudo make rootfs     # Build Debian rootfs with SSH/networking
sudo make sd-image   # Combine kernel + rootfs + FPGA bitstream
```

**Output**: `build/de10-nano-custom.img` (~4GB bootable image)

### What Gets Built
- **Custom Linux Kernel**: SoC FPGA kernel with FPGA bridge drivers
- **Debian Rootfs**: ARMhf Debian with SSH, networking, development tools
- **Calculator Application**: Test suite for HPS-FPGA communication
- **Bootloaders**: Preloader + U-Boot (from DE10-Nano System CD)

---

## 3. Deploy to DE10-Nano

### Flash SD Card
```bash
# Find your SD card device
lsblk

# Flash the complete image (replace /dev/sdX)
sudo dd if=HPS/linux_image/build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress conv=fsync
```

**Windows**: Use balenaEtcher, Win32DiskImager, or Rufus

### Boot Sequence
1. Insert SD card into DE10-Nano
2. Power on board (LEDs will cycle during boot)
3. Wait 30-60 seconds for Linux to initialize
4. FPGA bitstream loads automatically
5. SSH server starts (IP assigned via DHCP)

---

## 4. Run & Test

### Connect to Board
```bash
# Find board IP (check router DHCP table)
# Or use network scanner: nmap -sn 192.168.1.0/24

# SSH connect (password: root)
ssh root@<board-ip>
```

### Execute Tests
```bash
# Run calculator test suite (30 tests)
cd /root && ./calculator_test

# Expected: All tests pass with HPS-FPGA communication
# Watch LEDs change during calculations
```

### System Verification
```bash
# Check FPGA status
cat /sys/class/fpga_manager/fpga0/state  # Should show "operating"

# Check bridges
cat /sys/class/fpga_bridge/*/state       # Should show "enabled"

# Check network
ip addr show eth0 && ping -c 3 8.8.8.8
```

---

## Project Structure

```
FPGA/                 # Quartus FPGA design (calculator IP, QSys system)
├── qsys/            # QSys Platform Designer files
├── hdl/             # Verilog/VHDL source files
├── ip/              # Custom IP cores (calculator)
└── Makefile         # FPGA build targets

HPS/                  # Hard Processor System (Linux + apps)
├── linux_image/     # Linux kernel, rootfs, SD image build
├── applications/    # HPS applications (calculator_test, LEDs)
└── drivers/         # Linux driver integration

documentation/        # Build guides and references
examples/            # FPGA-HPS communication examples
```

---

## Key Features

- **Hardware Acceleration**: FPGA-based floating-point calculator IP
- **Low-Latency Communication**: Direct HPS-FPGA memory-mapped I/O
- **Automated Build System**: Makefiles handle complete toolchain
- **Cross-Platform Development**: Windows/WSL/Linux compatibility
- **Production Ready**: SSH-enabled Debian with networking

---

## Documentation

- **[Complete Deployment Guide](documentation/deployment_guide.md)** - Step-by-step build and troubleshooting
- **[FPGA-HPS Communication](documentation/hps_fpga_communication.md)** - Hardware interface details
- **[SoC EDS Setup](FPGA/SOC_EDS_SETUP.md)** - Intel SoC EDS configuration

---

## Getting Help

- Check the [Deployment Guide](documentation/deployment_guide.md) first
- Review Makefile help: `make help`
- For build issues: `make deps` to install dependencies
- Check kernel logs: `dmesg | grep fpga`

---

## References

### OEM Documentation
- [DE10-Nano CD Download](https://download.terasic.com/downloads/cd-rom/de10-nano/)
- [Terasic DE10-Nano](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046#contents)
- [Cyclone V HPS Register Address Map](https://www.intel.com/content/www/us/en/programmable/hps/cyclone-v/hps.html#sfo1418687413697.html)

### Hardware Manuals
- [DE10-Nano User Manual](documentation/references/DE10-Nano_User_manual_a_b.pdf)
- [Cyclone V Handbook](documentation/references/Cyclone_V_handbook.pdf)

### Community Resources
- [Building Embedded Linux for DE10-Nano](https://bitlog.it/20170820_building_embedded_linux_for_the_terasic_de10-nano.html)
- [zangman/de10-nano](https://github.com/zangman/de10-nano)

### Cornell University ECE5760
- [Linux Image](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/DE1-SoC-UP-Linux/linux_sdcard_image.zip)
- [FPGA Design](https://people.ece.cornell.edu/land/courses/ece5760/)
- [HPS Peripherals](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/HPS_peripherals/linux_index.html)