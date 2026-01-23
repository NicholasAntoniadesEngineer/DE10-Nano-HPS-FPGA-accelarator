# DE10-Nano Low-Latency Market Analysis Platform

A complete FPGA-accelerated development environment for the Terasic DE10-Nano board, featuring HPS-FPGA communication, custom Linux kernel, and automated build system.

## Quick Start

### Prerequisites
- Windows 10/11 with WSL2
- Quartus Prime Lite 20.1 (for FPGA compilation)
- DE10-Nano System CD (for prebuilt bootloaders)

### Build Everything
```bash
# Build FPGA bitstream + Linux image + SD card
cd HPS && sudo make everything
```

### Deploy and Boot
```bash
# Flash to SD card (replace /dev/sdX)
sudo ./scripts/deploy_image.sh /dev/sdX

# Boot DE10-Nano, then SSH in
ssh root@<board-ip>  # Password: root
```

## Project Structure

```
FPGA/              # Quartus/QSys FPGA design
HPS/               # Hard Processor System (Linux + applications)
Scripts/           # Build and deployment utilities
documentation/     # Comprehensive build guides
examples/          # FPGA-HPS communication examples
```

## Documentation

- **[Deployment Guide](documentation/deployment/deployment_guide.md)** - Complete build, deployment, and troubleshooting guide
- **[SoC EDS Setup](FPGA/SOC_EDS_SETUP.md)** - Intel SoC EDS configuration
- **[FPGA-HPS Communication](documentation/hps/hps_fpga_communication.md)** - Hardware interface guide

## Key Features

- **FPGA Compilation**: Quartus Prime integration with automated bitstream generation
- **Custom Linux Kernel**: ARM cross-compilation with FPGA drivers
- **Debian Rootfs**: SSH-enabled Linux environment with networking
- **SD Card Imaging**: Automated bootable image creation
- **Cross-Platform**: Windows/WSL compatibility with error recovery
- **HPS-FPGA Bridge**: Direct hardware communication examples

## References

### OEM Documentation
- [DE10-Nano CD Download](https://download.terasic.com/downloads/cd-rom/de10-nano/)
- [Terasic DE10-Nano](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046#contents)
- [Cyclone V HPS Register Address Map](https://www.intel.com/content/www/us/en/programmable/hps/cyclone-v/hps.html#sfo1418687413697.html)

### Community Resources
- [Building Embedded Linux for DE10-Nano](https://bitlog.it/20170820_building_embedded_linux_for_the_terasic_de10-nano.html)
- [zangman/de10-nano](https://github.com/zangman/de10-nano)

### Cornell University ECE5760
- [Linux Image](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/DE1-SoC-UP-Linux/linux_sdcard_image.zip)
- [FPGA Design](https://people.ece.cornell.edu/land/courses/ece5760/)
- [HPS Peripherals](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/HPS_peripherals/linux_index.html)