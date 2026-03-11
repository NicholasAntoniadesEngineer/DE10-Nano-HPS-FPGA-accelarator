# DE10-Nano HPS-FPGA Accelerator

FPGA-accelerated IEEE 754 floating-point calculator on the Intel Cyclone V SoC (DE10-Nano). The FPGA fabric implements ADD, SUB, MUL, and DIV in pure RTL with a 7-cycle pipeline. The HPS (dual-core ARM Cortex-A9) runs Debian Linux and communicates with the calculator IP over the Lightweight HPS-to-FPGA Avalon-MM bridge.

![System Block Diagram](documentation/references/images/System%20Block%20Diagram.png)

## Prerequisites

- **Docker Desktop** (with Rosetta 2 on Apple Silicon)
- **Git** (with LFS: `git lfs install`)
- **50 GB+ free disk space** (Quartus 18.1 image + build artifacts)
- **DE10-Nano** + MicroSD card (8 GB+)

## Build

All builds run inside a Docker container (Quartus 18.1 + ARM GCC). No native toolchain needed.

```bash
cd docker

# First time: build the Docker image (~20 min)
./scripts/setup.sh

# Full system build: FPGA + kernel + rootfs + SD image (~60 min first time)
./scripts/docker-build.sh

# Or build individual components
./scripts/docker-build.sh fpga          # FPGA bitstream only (~23 min)
./scripts/docker-build.sh applications  # HPS applications only (~1 min)
```

**Output**: `HPS/linux_image/build/de10-nano-custom.img`

## Flash SD Card (macOS)

```bash
diskutil list                                            # identify SD card (e.g. /dev/disk4)
diskutil unmountDisk force /dev/diskN                     # unmount all partitions
sudo dd if=HPS/linux_image/build/de10-nano-custom.img of=/dev/rdiskN bs=4m
```

> Terminal must have **Full Disk Access** (System Settings > Privacy & Security > Full Disk Access).
> The disk number changes on replug -- always run `diskutil list` first.

## Prepare DE10-Nano

1. **Set MSEL DIP switch (SW10)** for HPS FPGA programming mode. Wrong MSEL = FPGA loads but registers return 0x0.
2. Insert SD card, connect USB cable (Ethernet + UART), power on.
3. Boot takes ~10 seconds. LEDs animate during `boot-led` startup.

> After changing DIP switches, **power cycle** the board (reboot is not enough -- MSEL is sampled at power-on).

## Connect via SSH

```bash
# Configure USB Ethernet on Mac (must re-run each session)
sudo ifconfig en13 192.168.2.1 netmask 255.255.255.0

# SSH to DE10-Nano (password: root)
ssh root@192.168.2.2
```

> `en13` may vary -- check `ifconfig` output for the USB Ethernet adapter name.

## Run Applications

### Calculator Test Suite
```bash
calculator_test        # run all tests with 500 ms LED delays
calculator_test -q     # quick mode (no delays)
calculator_test -v     # verbose (register-level output)
```

### Calculator Demo (auto-starts at boot)
```bash
systemctl status calculator-demo     # check status
journalctl -u calculator-demo -f     # watch live output
```

### Boot LED (runs once at boot)
```bash
systemctl status boot-led            # check status
journalctl -u boot-led               # view log
```

### Register Access
```bash
devmem2 0xff20003c w    # read VERSION register (expect 0x00010001)
```

### Verify FPGA Bridges
```bash
cat /sys/class/fpga_bridge/*/state   # expect: "enabled"
```

## Project Structure

```
Makefile                  # Top-level orchestration
FPGA/
  quartus/                # Quartus project files + QSys system
  hdl/                    # Top-level Verilog (DE10_NANO_SoC_GHRD.v)
  ip/custom/calculator/   # Calculator IP (8 Verilog files + _hw.tcl)
  ip/custom/template/     # Template IP scaffold for new accelerators
  mk/                     # Modular Makefile fragments (qsys, quartus, etc.)
  generated/              # QSys-generated HDL (overlaid by qsys_check.sh)
  build/output_files/     # Quartus output (.rbf for SD card)
HPS/
  drivers/calculator/     # UIO-based calculator driver (/dev/uioN + mmap)
  drivers/template/       # UIO driver template for new IP
  libs/logger/            # Shared logging library
  applications/
    calculator_test/      # Test suite (33 test cases)
    calculator_demo/      # Demo service (systemd, auto-start)
    boot_led/             # LED heartbeat at boot (systemd)
    devmem2/              # /dev/mem read/write tool (cross-compiled)
  linux_image/
    kernel/               # Linux kernel (socfpga_defconfig)
    kernel/dts/           # Device tree sources (single source of truth)
    rootfs/               # Debian rootfs (debootstrap + overlays)
    bootloader/           # U-Boot + SPL + device tree
    scripts/              # SD image creation, rootfs build
scripts/
  new_ip.sh               # End-to-end scaffold for a new FPGA IP + UIO driver
docker/
  scripts/                # setup.sh, docker-build.sh, docker-clean.sh
  Dockerfile              # Quartus 18.1 + ARM GCC container
documentation/
  deployment_guide.md     # Detailed deployment walkthrough
  hps_fpga_communication.md
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `devmem2 0xff20003c w` returns `0x00000000` | MSEL DIP switch wrong | Set SW10 correctly, **power cycle** |
| All bridges show "disabled" | U-Boot didn't enable bridges | Check boot.scr, verify FPGA loaded |
| `calculator_test` all fail same result | Calculator not responding | Check bridge state, re-flash FPGA |
| SSH connection refused | USB Ethernet not configured | Run `ifconfig en13 192.168.2.1 ...` |
| `dd: permission denied` | Missing Full Disk Access | Add Terminal to Full Disk Access |

## References

- [Deployment Guide](documentation/deployment_guide.md) -- step-by-step build and flash
- [Docker Build Environment](docker/README.md) -- container setup and scripts
- [FPGA-HPS Communication](documentation/hps_fpga_communication.md) -- register map and bridge details
- [DE10-Nano User Manual](documentation/references/DE10-Nano_User_manual_a_b.pdf)
- [Terasic DE10-Nano](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046#contents)
- [Cyclone V HPS Register Map](https://www.intel.com/content/www/us/en/programmable/hps/cyclone-v/hps.html#sfo1418687413697.html)
