# DE10-Nano Board Bringup Guide

Step-by-step walkthrough of the full software stack, from building the Docker image to verifying the first-boot LED heartbeat on real hardware.

---

## Table of Contents

1. [Hardware Setup](#1-hardware-setup)
2. [Docker Build Environment](#2-docker-build-environment)
3. [FPGA Bitstream — Quartus → .rbf](#3-fpga-bitstream--quartus--rbf)
4. [U-Boot SPL + Device Tree](#4-u-boot-spl--device-tree)
5. [Kernel + Config Fragment + DTB](#5-kernel--config-fragment--dtb)
6. [Root Filesystem + Systemd Services](#6-root-filesystem--systemd-services)
7. [SD Card Image Creation & Flashing](#7-sd-card-image-creation--flashing)
8. [First Boot Verification](#8-first-boot-verification)
9. [LED Heartbeat Service](#9-led-heartbeat-service)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Hardware Setup

### Bill of Materials

| Item | Notes |
|------|-------|
| Terasic DE10-Nano | Cyclone V SoC (ARM Cortex-A9 + FPGA fabric) |
| MicroSD card | 8 GB minimum, Class 10 recommended |
| USB-A to mini-USB cable | UART console via FTDI on J8 |
| Ethernet cable | HPS EMAC1 (RJ45 on board) |
| 5V 2A power supply | Barrel jack |
| USB Blaster II *(optional)* | JTAG programming / SignalTap |

### DIP Switch Configuration (CRITICAL)

**SW10 (MSEL pins)** controls how the FPGA configuration source is selected at power-on.
This project uses U-Boot to load the `.rbf` from the SD card FAT32 partition.

| SW10 | Setting |
|------|---------|
| MSEL[4:0] | `01010` (HPS-controlled, Fast Passive Parallel x16) |

> **Warning**: Wrong MSEL causes the FPGA fabric to appear loaded (FPGA manager shows
> "operating", bridges show "enabled") but all Lightweight HPS-to-FPGA bridge reads
> return `0x0`. A **power cycle** is required after changing DIP switches — reboot is
> not sufficient, MSEL is sampled only at power-on.

### Physical Connections

```
DE10-Nano J8 (mini-USB) ──► USB-UART adapter ──► host /dev/tty.usbserial-*
DE10-Nano RJ45           ──► Ethernet ──► host (static IP, see §8)
MicroSD                  ──► slot on underside of board
```

---

## 2. Docker Build Environment

All build tools (Quartus 18.1, ARM cross-compiler, debootstrap, QEMU) run inside a
Docker container. macOS has no native Quartus or ARM toolchain — Docker is mandatory.

### One-Time Setup

```bash
cd docker
./scripts/setup.sh          # builds de10-nano-dev image (~20 min, download once)
```

The image contains:
- **Quartus Prime Lite 18.1** + SoC EDS
- **arm-linux-gnueabihf-** GCC cross-compiler
- **debootstrap** + **qemu-user-static** (ARM rootfs build in chroot)
- Make 4.3, ccache, git, wget

### Running Builds Inside the Container

```bash
# Full end-to-end build (~35–60 min, parallel)
cd docker && ./scripts/docker-build.sh

# Or run individual make targets
./scripts/docker-make.sh fpga
./scripts/docker-make.sh kernel
./scripts/docker-make.sh rootfs
./scripts/docker-make.sh sd-image
```

Artifacts land on the host filesystem via bind mount — no `docker cp` needed.

---

## 3. FPGA Bitstream — Quartus → .rbf

### Build Pipeline

```
FPGA/quartus/qsys/soc_system.qsys
    │
    ├── QSys generation  →  FPGA/generated/soc_system/
    │       calculator_0.s0 @ LW bridge offset 0x0000, IRQ 0
    │
    └── Quartus synthesis + fit + asm
            ↓
    FPGA/build/output_files/DE10_NANO_SoC_GHRD.sof   (JTAG format)
    FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf   (SD card format)
```

### Build

```bash
make fpga       # QSys gen → compile → RBF conversion (~20–30 min)
```

Internally:
1. `qsys_check.sh` — incremental QSys generation; overlays `ip/custom/calculator/`
   onto the QSys-generated submodule copies so Quartus always compiles the canonical IP
2. Quartus `map` / `fit` / `asm` — full place-and-route
3. `quartus_cpf -c -o bitstream_compression=on` — produces compressed `.rbf`

> **Note**: `hps_sdram_p0_pin_assignments.tcl` may print a "resource deadlock" warning
> under Docker Desktop (bind-mount limitation). This is non-fatal — the SOF is correct.

### Output

```
FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf
```

Copied to the FAT32 boot partition. U-Boot loads it at boot with `fpga load` then
opens the bridges with `bridge enable`.

---

## 4. U-Boot SPL + Device Tree

### Boot Chain

```
Power-on
  └── BootROM reads SPL from A2 partition (raw sector)
        └── SPL initialises DDR3, HPS clocks, MUX
              └── U-Boot proper loaded from FAT32 (u-boot.img)
                    └── boot.scr executes:
                          fpga load  0 ${rbf_file}   ← FPGA configured
                          bridge enable               ← LW + H2F bridges opened
                          bootz ${kernel} - ${fdt}   ← Linux starts
```

### Source & Defconfig

| Item | Value |
|------|-------|
| Repository | `u-boot/u-boot.git` |
| Tag | `v2020.04` |
| Defconfig | `socfpga_de10_nano_defconfig` |
| Output | `HPS/linux_image/bootloader/build/u-boot-with-spl.sfp` |

> v2020.04 is pinned for compatibility with Debian Stretch's OpenSSL 1.0.x in the
> rootfs build chroot.

### Build

```bash
make bootloader     # download, configure, cross-compile (~5 min with ccache)
```

`u-boot-with-spl.sfp` is written raw to the SD card A2 partition (not a filesystem —
raw sector write at a fixed offset by `create_sd_image.sh`).

### U-Boot Device Tree

U-Boot embeds its own DTB at compile time from
`HPS/linux_image/bootloader/build/arch/arm/dts/socfpga_cyclone5_de10_nano.dtb`.
This is separate from the Linux kernel DTB and only needs to describe hardware
U-Boot itself touches: DDR, UART, MMC, FPGA manager.

---

## 5. Kernel + Config Fragment + DTB

### Source

| Item | Value |
|------|-------|
| Repository | `altera-opensource/linux-socfpga` |
| Branch | `socfpga-5.15` |
| Base defconfig | `socfpga_defconfig` |
| Config fragment | `HPS/linux_image/kernel/configs/de10_nano.cfg` |

### Config Fragment

`de10_nano.cfg` is merged on top of `socfpga_defconfig` via `merge_config.sh`:

```
# UIO — userspace I/O, required for FPGA IP access via /dev/uioN
CONFIG_UIO=y
CONFIG_UIO_PDRV_GENIRQ=y
```

The calculator DTS node uses `compatible = "generic-uio"` so `uio_pdrv_genirq` binds
and creates `/dev/uio0`. The HPS driver discovers the device by matching
`linux,uio-name = "fpga-calculator"` in `/sys/class/uio/*/name`, then mmaps registers
and receives interrupts via the UIO fd — no `/dev/mem`, no hardcoded addresses.

### Device Tree Source Chain

```
HPS/linux_image/kernel/dts/
├── socfpga.dtsi                    ← SoC base (all bridges disabled by default)
├── socfpga_cyclone5.dtsi           ← Cyclone V family (osc1=25 MHz, watchdog)
└── socfpga_cyclone5_de10_nano.dts  ← Board-level (this project)
```

Key overrides in `socfpga_cyclone5_de10_nano.dts`:

```dts
/* Enable FPGA bridges */
&fpga_bridge0 { status = "okay"; bridge-enable = <1>; };  /* LW  0xFF200000 2 MB */
&fpga_bridge1 { status = "okay"; bridge-enable = <1>; };  /* H2F 0xC0000000 960 MB */

/* Calculator IP — placed directly under &soc so uio_pdrv_genirq probes it at boot.
 * DO NOT use &base_fpga_region: that is an fpga-region node whose children are only
 * instantiated when Linux programs the FPGA via the FPGA Manager firmware API.
 * Since U-Boot programs the FPGA before Linux boots, the region never fires. */
&soc {
    calculator0: calculator@ff200000 {
        compatible = "generic-uio";
        reg = <0xff200000 0x40>;
        interrupts = <0 40 4>;        /* GIC SPI = f2h_irq0 IRQ0 + 40 offset */
        interrupt-parent = <&intc>;
        linux,uio-name = "fpga-calculator";
        status = "okay";
    };
};
```

> **Why `&soc` not `&base_fpga_region`**: `base_fpga_region` is an `fpga-region` whose
> child devices are only instantiated after the Linux FPGA Manager programs the FPGA
> through its firmware API. Since U-Boot programs the FPGA before Linux boots, the region
> never fires and `uio_pdrv_genirq` never probes. Direct placement under `&soc` is the
> correct pattern for all FPGA IP on this board.

### UIO Driver Binding — Kernel Bootarg

`uio_pdrv_genirq`'s OF match table is **empty by default** in Linux 5.x. Without the
`of_id` parameter the driver exists but won't bind to any DT node. The parameter is
set in `create_sd_image.sh` inside the U-Boot `boot.scr`:

```
setenv bootargs ... uio_pdrv_genirq.of_id=generic-uio
```

> Note: U-Boot `setenv bootargs` **overrides** DTS `chosen { bootargs }`. The DTS
> bootargs value is documentation only; the boot script is authoritative.

Bridge enable order (most to least preferred):
1. U-Boot `bridge enable` in `boot.scr` — primary
2. `bridge-enable = <1>` DT property at kernel probe — secondary
3. `fpga-bridge-enable.service` writing L3 REMAP `0xFF800000` — tertiary fallback

### Build

```bash
make kernel     # ~10–20 min first build; fast on rebuilds with ccache
```

The Makefile glob-copies all `dts/*.dts` and `dts/*.dtsi` into the kernel source tree
before every build. **Never edit files inside `linux-socfpga/` directly** — `dts/` is
the single source of truth.

### Outputs

```
HPS/linux_image/kernel/build/arch/arm/boot/zImage
HPS/linux_image/kernel/build/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb
```

`create_sd_image.sh` copies these to the FAT32 partition as `zImage` and `socfpga.dtb`.

---

## 6. Root Filesystem + Systemd Services

### Base Rootfs

Built with `debootstrap` (Debian armhf, Stretch) using QEMU user-static for ARM
emulation in chroot. The base image is cached at
`rootfs/build/rootfs_base.tar.xz` and reused on incremental builds.

Key packages: `openssh-server`, `iproute2`, `systemd`, `kmod`, `libatomic1`,
`devmem2` (cross-compiled from source — not in Debian repos).

### Application Services

| Service file | Binary | Behaviour |
|---|---|---|
| `calculator-demo.service` | `/usr/local/bin/calculator_demo` | Interactive FPGA calculator; starts at `multi-user.target` |
| `boot-led.service` | `/usr/local/bin/boot_led` | LED heartbeat via calculator; starts after demo service |

Both run as root (required for `/dev/uio` access) and restart on failure with a 2 s delay.

### Rootfs Overlay Scripts

| Script | Runs on | Purpose |
|--------|---------|---------|
| `install_boot_led.sh` | host | Copy binary + service file into rootfs staging area |
| `install_calculator_demo.sh` | host | Copy binary + service file |
| `setup_network.sh` | chroot | Static IP `192.168.2.2/24` on eth0 |
| `setup_ssh.sh` | chroot | Enable sshd, permit root login |
| `setup_fpga_drivers.sh` | chroot | UIO module config, FPGA bridge setup |
| `setup_services.sh` | chroot | `systemctl enable` all services |

### Serial Console

A standalone `de10-serial-console.service` provides an autologin root shell on
`ttyS0` (115200 8N1) without PAM. `serial-getty@ttyS0.service` is masked to prevent
racing with it. This is necessary because the DesignWare 8250 UART is a platform
device created before udev, causing `dev-ttyS0.device` to always time out.

### Build

```bash
make rootfs     # debootstrap + chroot config + app install (~15–25 min)
```

Output: `HPS/linux_image/rootfs/build/rootfs.tar.xz`

---

## 7. SD Card Image Creation & Flashing

### Partition Layout

| Partition | Type | Contents |
|-----------|------|---------|
| A2 (raw) | — | `u-boot-with-spl.sfp` (raw sector write, no filesystem) |
| FAT32 | boot | `zImage`, `socfpga.dtb`, `DE10_NANO_SoC_GHRD.rbf`, `boot.scr` |
| ext4 | rootfs | Debian armhf root filesystem + applications |

### Build the Image

```bash
make sd-image   # assembles all artifacts into a single .img (~5 min)
```

Outputs:
```
HPS/linux_image/build/de10-nano-custom.img
HPS/linux_image/build/de10-nano-custom.img.xz    (compressed, ~95% smaller)
HPS/linux_image/build/de10-nano-custom.img.sha256
```

### Flash (macOS)

```bash
# 1. Find disk number — run after inserting SD card
diskutil list

# 2. Unmount all partitions
diskutil unmountDisk force disk2        # replace disk2 with your disk number

# 3. Write image  (rdisk = raw device, significantly faster than /dev/disk)
sudo dd if=HPS/linux_image/build/de10-nano-custom.img \
        of=/dev/rdisk2 bs=4m
```

> **macOS permission**: Terminal needs **Full Disk Access** — System Settings →
> Privacy & Security → Full Disk Access. Without it `dd` fails silently.
>
> The disk number changes on every replug — always run `diskutil list` first.

---

## 8. First Boot Verification

### Host Network (macOS, run once per session)

```bash
sudo ifconfig en13 192.168.2.1 netmask 255.255.255.0   # adjust interface name as needed
```

### Serial Console

```bash
screen /dev/tty.usbserial-* 115200
```

Expected U-Boot sequence:
```
U-Boot SPL 2020.04 ...
U-Boot 2020.04 ...
Loading: DE10_NANO_SoC_GHRD.rbf ... FPGA configuration success
bridge enable ... success
Booting Linux ...
```

### SSH

```bash
ssh root@192.168.2.2    # password: root
```

### FPGA Bridge Status

```bash
cat /sys/bus/platform/devices/ff400000.fpga_bridge/fpga_bridge/br0/state
# expected: enabled

cat /sys/bus/platform/devices/ffc25000.fpga_bridge/fpga_bridge/br1/state
# expected: enabled
```

### Calculator Smoke Test

```bash
# Read VERSION register (LW bridge base + offset 0x3C)
devmem2 0xff20003c w
# expected: non-zero, e.g. 0x00010001

# Full test suite
/usr/local/bin/calculator_test
# expected: 33/33 tests passed
```

---

## 9. LED Heartbeat Service

`boot-led.service` drives the 8 on-board LEDs (LEDR[7:0]) by chaining floating-point
calculations through the FPGA calculator IP at ~30 Hz. Each result's lower 8 bits map
directly to the LED bank via the `calculator_led_display` module in FPGA fabric.

### Service Control

```bash
systemctl status boot-led.service
journalctl -u boot-led.service -f
systemctl restart boot-led.service
```

### Expected Behaviour

On a successful bringup:
- LEDs begin animating within ~2 s of `multi-user.target` being reached
- Pattern cycles pseudo-randomly at ~30 Hz (driven by FPGA computation results)
- `calculator-demo.service` starts first; `boot-led.service` follows

If LEDs are dark and the service is in `failed` state:
1. Verify FPGA bridges are enabled (§8)
2. Verify calculator IP responds (`devmem2 0xff20003c w` → non-zero)
3. Verify MSEL DIP switches and power cycle if recently changed

---

## 10. Troubleshooting

### All LW Bridge Reads Return 0x0

**Cause**: SW10 MSEL incorrectly set. The FPGA loads but Avalon-MM slaves don't
respond because the configuration mode doesn't match.

**Fix**: Set MSEL[4:0] = `01010`, then **power cycle** (reboot is not enough).

### FPGA Bridges Show "disabled" After Boot

U-Boot `bridge enable` didn't run. Manual fallback:

```bash
# Check the L3 REMAP fallback service
systemctl status fpga-bridge-enable.service

# Or enable bridges directly via devmem2
devmem2 0xFF800000 w 0x19
```

### Boot Hangs After "Starting kernel..."

DTB mismatch between kernel and U-Boot. Verify `socfpga.dtb` on the FAT32 partition
was produced by this project's `dts/socfpga_cyclone5_de10_nano.dts`, not an upstream
copy without the bridge or calculator nodes.

### Serial Console Login Loop

Two getty instances racing on `ttyS0`. Verify:

```bash
systemctl is-enabled serial-getty@ttyS0.service   # should print: masked
systemctl status de10-serial-console.service       # should be: active (running)
```

### Kernel Build Fails: No defconfig Found

The `linux-socfpga` submodule is in an empty or detached state:

```bash
cd HPS/linux_image/kernel
make kernel-distclean
make kernel-download    # re-clones socfpga-5.15
make kernel-build
```

### ccache Miss on First Docker Build

Expected — cache is cold. First kernel build takes 20–30 min. Subsequent builds
with a warm cache take 3–5 min.

```bash
cd HPS/linux_image/kernel && make ccache-stats
```
