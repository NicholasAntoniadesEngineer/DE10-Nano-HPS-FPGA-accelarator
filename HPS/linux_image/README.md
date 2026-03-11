# Linux Image Build System

This directory builds the complete bootable SD card image for the DE10-Nano, including the bootloader, Linux kernel, and root filesystem.

## System Overview

```
SD Card Layout (4 GB):
┌─────────────────────────────────────────────────┐
│ MBR (sector 0)                                  │
├─────────────────────────────────────────────────┤
│ Partition 3: Altera preloader (0xa2)            │  sectors 2–2047 (1 MB)
│   u-boot-with-spl.sfp (raw)                    │  Boot ROM loads SPL from here
├─────────────────────────────────────────────────┤
│ Partition 1: FAT32 (0x0c)                       │  sector 2048, 100 MB
│   zImage, socfpga_cyclone5_de10_nano.dtb,       │  SPL loads u-boot.img,
│   DE10_NANO_SoC_GHRD.rbf, u-boot.img,           │  U-Boot loads zImage + DTB + RBF
│   boot.scr, extlinux/extlinux.conf              │
├─────────────────────────────────────────────────┤
│ Partition 2: ext4 (0x83)                        │  ~3.9 GB
│   Debian root filesystem                        │  Mounted as /
└─────────────────────────────────────────────────┘
```

### Boot Sequence

```
Power-on
  → Cyclone V Boot ROM reads MBR, finds 0xa2 partition
  → Loads SPL (Secondary Program Loader) from raw partition
  → SPL initializes DDR3, loads u-boot.img from FAT32
  → U-Boot runs boot.scr:
      1. Loads FPGA bitstream (RBF) into FPGA fabric
      2. Enables HPS-FPGA bridges
      3. Loads zImage + DTB
      4. Boots Linux kernel
  → Linux mounts ext4 rootfs, runs systemd
```

## Component Versions

| Component | Version | Source | Notes |
|-----------|---------|--------|-------|
| **Linux kernel** | 5.15.0 (`socfpga-5.15` branch) | [altera-opensource/linux-socfpga](https://github.com/altera-opensource/linux-socfpga) | Tag: `rel_socfpga-5.15_22.06.01_pr`. Intel/Altera's fork with SoCFPGA platform support (FPGA manager, bridges, etc.) |
| **U-Boot** | v2020.04 | [u-boot/u-boot](https://github.com/u-boot/u-boot) | Built-in `socfpga_de10_nano_defconfig`. Replaces Intel preloader (no SoC EDS needed) |
| **Root filesystem** | Debian Bullseye (stable) | `debootstrap` | armhf architecture. Built via QEMU user-mode emulation in Docker |
| **Toolchain** | `arm-linux-gnueabihf-gcc` | Linaro / Debian cross-tools | ARMv7 hard-float ABI |
| **Device tree** | `socfpga_cyclone5_de10_nano.dtb` | Compiled from kernel source | Board-specific DTS with FPGA bridge nodes |

### Why these versions?

- **Kernel 5.15**: LTS kernel with mature SoCFPGA FPGA manager support. The `socfpga-5.15` branch includes Intel-specific patches for Cyclone V that aren't in mainline.
- **U-Boot v2020.04**: Last version with straightforward `socfpga_de10_nano_defconfig` that works with the Docker build environment's OpenSSL. Newer versions require OpenSSL 1.1+.
- **Debian Bullseye**: Current Debian stable with good armhf package availability. Uses systemd.

## Kernel Configuration

The kernel is configured for a headless embedded system with FPGA accelerator support:

**Key enabled features:**
- `CONFIG_FPGA` — FPGA framework
- `CONFIG_FPGA_MGR_SOCFPGA` — Cyclone V FPGA manager (programs FPGA from Linux)
- `CONFIG_FPGA_BRIDGE` — FPGA bridge framework
- `CONFIG_ALTERA_MBOX` — Altera mailbox driver
- `CONFIG_NET` + `CONFIG_STMMAC_ETH` — DesignWare Ethernet (Gigabit)
- `CONFIG_SERIAL_8250_DW` — DesignWare UART (serial console on ttyS0)
- `CONFIG_MMC_DW` — DesignWare SD/MMC
- `CONFIG_USB_DWC2` — USB OTG
- `CONFIG_I2C_DESIGNWARE` — I2C controller
- `CONFIG_FRAMEBUFFER_CONSOLE` — Framebuffer console (for future HDMI use)

**Not enabled (headless build):**
- No DRM/KMS graphics drivers
- No ADV7511/ADV7513 HDMI transmitter driver
- No audio/ALSA
- No WiFi/Bluetooth

The full kernel config is at `kernel/build/.config`.

### Modifying the kernel config

```bash
# Inside the Docker container:
cd /workspace/HPS/linux_image/kernel/linux-socfpga
make O=../build ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- menuconfig
# Then rebuild:
cd /workspace/HPS/linux_image && make kernel
```

## U-Boot Bootloader

U-Boot is built from mainline with the `socfpga_de10_nano_defconfig`. This replaces Intel's proprietary preloader (SoC EDS is not required).

**Build output:**
- `bootloader/build/u-boot-with-spl.sfp` — Combined SPL + U-Boot, written raw to the 0xa2 partition
- `bootloader/build/u-boot.img` — U-Boot proper (loaded by SPL from FAT32)

**SPL responsibilities:**
1. Initialize DDR3 memory controller (timings are compiled into SPL)
2. Initialize UART for serial console
3. Load `u-boot.img` from FAT32 partition

**U-Boot responsibilities:**
1. Load FPGA bitstream: `fatload mmc 0:1 ... DE10_NANO_SoC_GHRD.rbf`
2. Program FPGA: `fpga load 0 ...`
3. Enable bridges: `bridge enable`
4. Load kernel + DTB
5. Boot Linux: `bootz`

**Debug logging:** SPL and U-Boot are configured with maximum log verbosity (`LOGLEVEL=7`). Serial console at 115200 baud on `ttyS0`.

### Rebuilding U-Boot

```bash
cd HPS/linux_image/bootloader
make                  # Downloads, configures, and builds
make clean            # Clean build artifacts
make distclean        # Remove source + build
```

## Root Filesystem

Debian Bullseye (armhf) built via `debootstrap` + QEMU user-mode emulation inside Docker.

### Pre-installed packages

See `rootfs/packages.txt` for the full list. Key packages:
- `openssh-server` — SSH access (pre-configured, root login enabled)
- `build-essential`, `gcc`, `make`, `git` — On-target development
- `python3` — Scripting
- `device-tree-compiler`, `u-boot-tools` — FPGA/boot utilities
- `htop`, `vim`, `nano` — System utilities

### Pre-configured services

| Service | Description |
|---------|-------------|
| `calculator-demo.service` | Runs calculator FPGA demo at boot |
| `boot-led.service` | LED heartbeat pattern at boot |
| `de10-serial-console.service` | Serial console on ttyS0 (autologin root) |
| `fpga-bridge-enable.service` | Fallback: enables FPGA bridges via L3 REMAP if DT/U-Boot didn't |
| `sshd` | OpenSSH server (enabled by default) |

### Network configuration

- **Default**: Static IP `192.168.2.2/24` on USB Ethernet
- Mac-side: `sudo ifconfig en13 192.168.2.1 netmask 255.255.255.0`
- SSH: `ssh root@192.168.2.2` (password: `root`)
- Hostname: `de10-nano`

### Overlay system

The rootfs build has two phases:
1. **Base build** (`build_rootfs.sh`): `debootstrap` + package installation
2. **Overlay** (Makefile): Copies config files, install scripts, and pre-compiled application binaries

Install scripts (`rootfs/scripts/install_*.sh`) copy host-built binaries into the rootfs.
Setup scripts (`rootfs/scripts/setup_*.sh`) configure system state (run inside chroot).

Applications must be cross-compiled **before** the rootfs build so binaries exist for installation.

## HDMI on the DE10-Nano

The DE10-Nano's HDMI output goes through the **FPGA fabric**, not the HPS:

```
FPGA fabric ──(24-bit parallel video bus)──> ADV7513 ──> HDMI connector
                                              ↑
                                          I2C config
                                          (from FPGA)
```

The **ADV7513** is an Analog Devices HDMI 1.4 transmitter chip. It connects to the FPGA via:
- 24-bit parallel video data bus (directly to FPGA pins, active at up to 165 MHz)
- I2C control interface (active directly to FPGA pins, not HPS I2C)
- Active pixel clock, HSYNC, VSYNC, DE signals (active all FPGA-fabric)

**This means HDMI is entirely an FPGA-side peripheral.** The HPS has no direct connection to the ADV7513. To use HDMI, you would need:

1. **FPGA video pipeline** — Implement a framebuffer controller or video IP in the FPGA fabric that drives the parallel video signals to the ADV7513
2. **ADV7513 I2C initialization** — Configure resolution, color depth, etc. via the FPGA-side I2C (or route I2C through a QSys conduit so the HPS can configure it via the LW bridge)
3. **Linux DRM/KMS driver** (optional) — If you want Linux to drive a display, you'd need to:
   - Add an FPGA framebuffer IP that the HPS can write pixel data to via the HPS-to-FPGA bridge
   - Enable `CONFIG_DRM`, `CONFIG_DRM_ADV7511` (the ADV7513 is register-compatible), and a matching DRM bridge driver in the kernel
   - Add the ADV7513 to the device tree with I2C connection details

The current project does **not** include HDMI support because it's designed as a headless accelerator platform. The HDMI-related FPGA pins are not declared in the QSF or top-level HDL. Terasic provides example FPGA projects with HDMI support on their website (see Chapter 5.3 of the user manual).

### HDMI Pin Assignments (for reference)

| Signal | FPGA Pin | Signal | FPGA Pin |
|--------|----------|--------|----------|
| `HDMI_TX_D[0]` | PIN_AD12 | `HDMI_TX_D[12]` | PIN_AE7 |
| `HDMI_TX_D[1]` | PIN_AE12 | `HDMI_TX_D[13]` | PIN_AF6 |
| `HDMI_TX_D[2]` | PIN_W8 | `HDMI_TX_D[14]` | PIN_AF8 |
| `HDMI_TX_D[3]` | PIN_Y8 | `HDMI_TX_D[15]` | PIN_AF5 |
| `HDMI_TX_D[4]` | PIN_AD11 | `HDMI_TX_D[16]` | PIN_AE4 |
| `HDMI_TX_D[5]` | PIN_AD10 | `HDMI_TX_D[17]` | PIN_AH2 |
| `HDMI_TX_D[6]` | PIN_AE11 | `HDMI_TX_D[18]` | PIN_AH4 |
| `HDMI_TX_D[7]` | PIN_Y5 | `HDMI_TX_D[19]` | PIN_AH5 |
| `HDMI_TX_D[8]` | PIN_AF10 | `HDMI_TX_D[20]` | PIN_AH6 |
| `HDMI_TX_D[9]` | PIN_Y4 | `HDMI_TX_D[21]` | PIN_AG6 |
| `HDMI_TX_D[10]` | PIN_AE9 | `HDMI_TX_D[22]` | PIN_AF9 |
| `HDMI_TX_D[11]` | PIN_AB4 | `HDMI_TX_D[23]` | PIN_AE8 |

| Signal | FPGA Pin | Description |
|--------|----------|-------------|
| `HDMI_TX_CLK` | PIN_AG5 | Pixel clock |
| `HDMI_TX_DE` | PIN_AD19 | Data enable |
| `HDMI_TX_HS` | PIN_T8 | Horizontal sync |
| `HDMI_TX_VS` | PIN_V13 | Vertical sync |
| `HDMI_TX_INT` | PIN_AF11 | Interrupt (active low) |
| `HDMI_I2C_SCL` | PIN_U10 | I2C clock (FPGA-side) |
| `HDMI_I2C_SDA` | PIN_AA4 | I2C data (FPGA-side) |

All HDMI pins use 3.3-V LVTTL I/O standard.

## Build Targets

```bash
# Full build (inside Docker):
make all                    # Builds bootloader + kernel + rootfs + SD image

# Individual targets:
make bootloader             # U-Boot SPL + u-boot.img
make kernel                 # Linux kernel (zImage + DTB + modules)
make rootfs                 # Debian rootfs (requires root/sudo)
make sd-image               # Assemble SD card image from built components
make sd-image-compress      # Create .img.xz for distribution

# Utilities:
make deps                   # Install build-host dependencies
make deps-check             # Verify dependencies
make flash-sd               # Show SD card flashing instructions
make help                   # Full target list
```

### Build order

The Makefile handles dependencies automatically. When building `all`:

1. Cross-compile HPS applications (calculator_demo, boot_led, calculator_test, devmem2)
2. Build U-Boot bootloader (download → configure → compile)
3. Build Linux kernel (zImage + DTB + modules) — runs in parallel with rootfs
4. Build rootfs (debootstrap + packages + overlay with pre-compiled binaries)
5. Assemble SD card image (partition + copy files)
6. Compress image (.img.xz)

### Parallel builds

Kernel and rootfs build in parallel by default (`PARALLEL_BUILD=1`). Use `PARALLEL_BUILD=0` for serial builds (useful for debugging).

## Flashing to SD Card

### macOS

```bash
# Find your SD card disk number:
diskutil list

# Unmount and flash (replace diskN with your disk number):
diskutil unmountDisk force diskN
sudo dd if=build/de10-nano-custom.img of=/dev/rdiskN bs=4m
```

Terminal must have Full Disk Access (System Settings → Privacy → Full Disk Access). The SD card disk number changes on replug — always run `diskutil list` first.

### Linux

```bash
sudo dd if=build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress
sync
```

## Directory Structure

```
linux_image/
├── Makefile              # Top-level build orchestration
├── README.md             # This file
├── bootloader/
│   ├── Makefile          # U-Boot build (download, configure, compile)
│   ├── u-boot-socfpga/   # U-Boot source (cloned at build time)
│   └── build/            # Build output (u-boot-with-spl.sfp, u-boot.img)
├── kernel/
│   ├── linux-socfpga/    # Kernel source (git submodule, socfpga-5.15)
│   └── build/            # Out-of-tree build (.config, zImage, DTB, modules)
├── rootfs/
│   ├── build_rootfs.sh   # Rootfs builder (debootstrap + packages)
│   ├── packages.txt      # Package list for rootfs
│   ├── scripts/          # Install/setup scripts (copied into rootfs)
│   └── build/            # Build output (rootfs.tar.xz)
├── scripts/
│   ├── build_config.sh   # Central build configuration (versions, paths)
│   ├── create_sd_image.sh # SD card image assembler
│   ├── flash_sd.sh       # SD card flashing helper
│   └── deploy_image.sh   # Image deployment script
└── build/                # Final output (de10-nano-custom.img, .img.xz)
```
