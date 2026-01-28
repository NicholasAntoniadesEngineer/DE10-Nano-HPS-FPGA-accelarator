# DE10-Nano-HPS-FPGA-Accelerated 

Complete hardware-software platform for low-latency FPGA-accelerated computing on the Terasic DE10-Nano SoC board. Features Intel Cyclone V SoC (5CSEBA6U23I7) with dual-core ARM Cortex-A9 HPS running Linux, FPGA fabric with custom IP cores, and high-bandwidth Avalon-MM bridges for FPGA-HPS communication. 

Includes parallelized build system (Quartus Prime Lite 20.1 + ARM cross-compiler), custom Linux drivers, and complete SD card image generation for deployment. 

The system is designed to be used for low-latency analysis and calculations, where the FPGA is used to accelerate the computation and analysis.

---

## Project Structure

```
Makefile               # Top-level orchestration (recommended entry point)
build/                 # Common build infrastructure
├── build_common.mk    # Shared macros, timing, logging
└── output_files/      # Build artifacts (RBF, SOF, etc.)

FPGA/                  # Quartus FPGA design
├── Makefile           # FPGA build (QSys, Quartus, DTB)
├── quartus/           # Quartus project files
├── hdl/               # Verilog/VHDL source files
├── ip/                # Custom IP cores (calculator)
└── generated/         # Generated HDL from QSys

HPS/                   # Hard Processor System
├── Makefile           # HPS orchestration
├── linux_image/       # Linux build system
├── applications/      # HPS applications (parallel build)
└── drivers/           # Linux driver integration

docker/                # Docker build environment
├── Dockerfile         # Container image definition
├── docker-compose.yml # Docker Compose configuration
├── setup.sh           # Container setup script
└── scripts/           # Build scripts for containerized builds

examples/              # Example projects and reference designs
├── fpga_examples/     # Standalone FPGA examples
├── hps_examples/      # HPS-only examples (GPIO, sensors, etc.)
└── hps_fpga_examples/ # Combined HPS-FPGA examples

documentation/         # Build guides and references
├── deployment_guide.md
├── hps_fpga_communication.md
└── references/        # Hardware manuals, schematics, images
```

## Hardware Overview

### System Block Diagram

![System Block Diagram](documentation/references/images/System%20Block%20Diagram.png)

The system architecture showing the interconnection between the FPGA and HPS (Hard Processor System) components, including peripherals and communication bridges.

## Documentation

- **[Complete Deployment Guide](documentation/deployment_guide.md)** - Step-by-step build and troubleshooting
- **[FPGA-HPS Communication](documentation/hps_fpga_communication.md)** - Hardware interface details
- **[Docker Build Environment](docker/README.md)** - Automated build system for FPGA + HPS

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

### DE10-Nano Board Views

#### Top View

![DE10-Nano Top View](documentation/references/images/Tope%20View.png)

Top-down view of the DE10-Nano development board showing all major components, including the Cyclone V FPGA with ARM Cortex-A9, HPS DDR3 memory, Ethernet, USB ports, GPIO headers, HDMI, LEDs, switches, and other peripherals.

#### Bottom View

![DE10-Nano Bottom View](documentation/references/images/Bottom%20View.png)

Bottom view of the DE10-Nano board showing the underside components, including the EPCS128 configuration device and MicroSD card socket.


---

## Prerequisites

- **Hardware**: DE10-Nano board + MicroSD card (8GB+)
- **Software**: Quartus Prime Lite 20.1 + ARM cross-compiler
- **OS**: Windows with WSL2 or Linux environment
- **Optional**: DE10-Nano System CD (for prebuilt bootloaders)

---

## Quick Start

```bash
# From repository root - build everything with parallelization
make everything    # FPGA + HPS build in parallel, then creates SD image

# Or build individual components
make fpga          # Build FPGA bitstream only
make kernel        # Build Linux kernel only
make rootfs        # Build root filesystem only
make sd-image      # Create SD card image (requires FPGA artifacts)
```

---

## Build Commands

### Full Build (Recommended)
```bash
make everything          # Parallel FPGA + HPS build (~35-50 min)
make everything-parallel  # Force parallel mode
make everything-sequential # Force sequential mode (low memory)
```

### FPGA Build
```bash
make fpga              # Complete FPGA build (QSys + Quartus + RBF + DTB)
make fpga-qsys         # Generate QSys system only
make fpga-sof          # Compile FPGA bitstream
make fpga-rbf          # Convert to RBF format
make fpga-dtb          # Generate device tree from QSys
```

### HPS Build
```bash
make kernel            # Build Linux kernel (with ccache if available)
make rootfs            # Build root filesystem (uses base cache)
make applications      # Build HPS applications
make sd-image          # Create complete SD card image
make sd-image-update   # Incremental update (faster)
```

### Status and Diagnostics
```bash
make help              # Show all available targets
make status            # Show build artifact status
make timing-report     # Show build timing statistics
```

---

## Build Outputs

| Component | Output Location | Build Time |
|-----------|-----------------|------------|
| FPGA RBF | `FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf` | 15-25 min |
| Device Tree | `FPGA/generated/soc_system.dtb` | 1 min |
| Kernel | `HPS/linux_image/kernel/build/arch/arm/boot/zImage` | 10-20 min |
| Rootfs | `HPS/linux_image/rootfs/build/rootfs.tar.gz` | 15-25 min |
| SD Image | `HPS/linux_image/build/de10-nano-custom.img` | 2-5 min |

---

## Deploy to DE10-Nano

### Flash SD Card
```bash
# Find your SD card device
lsblk

# Flash the complete image (replace /dev/sdX)
sudo dd if=HPS/linux_image/build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress conv=fsync
```

**Windows**: Use balenaEtcher, Win32DiskImager, or Rufus

### Boot & Connect
```bash
# SSH connect (default password: root)
ssh root@<board-ip>

# Run calculator tests
./calculator_test
```

### Verify System
```bash
cat /sys/class/fpga_manager/fpga0/state  # Should show "operating"
cat /sys/class/fpga_bridge/*/state       # Should show "enabled"
```

---

## Configuration

### Parallelization Options
```bash
PARALLEL_EVERYTHING=1/0  # FPGA + HPS parallel (default: 1)
PARALLEL_BUILD=1/0       # Kernel + Rootfs parallel (default: 1)
PARALLEL_JOBS=N          # Parallel job count (default: 2)
QUARTUS_PARALLEL_JOBS=N  # Quartus jobs (default: auto-detect CPU count)
PARALLEL_APPS=1/0        # Applications parallel (default: 1)
```

### Performance Options
```bash
USE_CCACHE=1/0           # Enable ccache for kernel (default: 1 if available)
TOOL_CACHE_DISABLE=1     # Disable Quartus/QSys path caching
```

### Clean Operations
```bash
make clean               # Clean build artifacts (parallel, preserves caches)
make clean-all           # Deep clean including all caches
```

---
