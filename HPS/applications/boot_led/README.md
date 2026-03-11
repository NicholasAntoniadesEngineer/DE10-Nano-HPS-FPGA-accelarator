# Boot LED Indicator

Visual indicator that the custom Linux image is running on the DE10-Nano.

## Overview

This application drives the DE10-Nano's user LEDs via the FPGA calculator IP to provide visual confirmation that:
- The custom Linux image has booted successfully
- The HPS-FPGA bridge is functional
- The calculator IP is responding

It generates pseudo-random calculator operations at ~30 Hz. Each completed calculation causes the FPGA `calculator_led_display` module to latch `result[7:0]` onto the board's LEDs, producing a continuous random flicker pattern.

## Features

- Random 30 Hz LED pattern driven by FPGA calculator computations
- Uses the shared `calculator_driver` library (UIO-based — no `/dev/mem`)
- Runs automatically as a systemd service
- Clean shutdown on SIGTERM/SIGINT

## Building

```bash
# Cross-compile for ARM
make

# Native compile on DE10-Nano
make CROSS_COMPILE=
```

## Installation

### Manual Installation

```bash
# Copy binary to DE10-Nano
scp boot_led root@<board-ip>:/usr/local/bin/

# Copy service file
scp boot-led.service root@<board-ip>:/etc/systemd/system/

# On DE10-Nano: enable and start service
ssh root@<board-ip>
systemctl daemon-reload
systemctl enable boot-led.service
systemctl start boot-led.service
```

### Automatic Installation

The boot_led service is automatically included in the rootfs build. When you build a new SD card image with `make sd-image`, the boot LED indicator will be installed and enabled.

## Usage

### As Systemd Service (Recommended)

```bash
# Start the service
systemctl start boot-led

# Stop the service
systemctl stop boot-led

# Check status
systemctl status boot-led

# Enable on boot
systemctl enable boot-led

# Disable on boot
systemctl disable boot-led
```

### Manual Execution

```bash
# Run continuously (random LED flicker via FPGA calculator)
./boot_led

# Run for ~5 seconds then exit
./boot_led --oneshot

# Fork into background
./boot_led --daemon

# Show help
./boot_led --help
```

## LED Behavior

LEDs display `result[7:0]` from each FPGA calculator operation. A software xorshift32 PRNG seeds pseudo-random operands and operations (ADD/SUB/MUL/DIV) every ~33 ms (~30 Hz). The FPGA `calculator_led_display` module latches the low byte of each result onto `LED[7:0]` on each `calc_done` pulse, producing a random flicker pattern for as long as the service runs.

## Hardware Requirements

- DE10-Nano with FPGA programmed with the calculator design
- Calculator IP connected to the lightweight HPS-to-FPGA bridge
- UIO kernel driver enabled (`CONFIG_UIO_PDRV_GENIRQ=y`) with a device tree node for the calculator IP

## Troubleshooting

### LEDs not responding

1. Check FPGA is programmed with a design that includes the calculator IP
2. Verify the UIO device exists: `ls /sys/class/uio/*/name` (expect `fpga-calculator`)
3. Check HPS-to-FPGA bridges are enabled: `cat /sys/class/fpga_bridge/*/state`

### Service fails to start

Check logs:
```bash
journalctl -u boot-led -f
```

The service does not require root — it accesses hardware via `/dev/uioN`.

## Files

| File | Description |
|------|-------------|
| `boot_led.c` | Main application source (30 Hz PRNG loop via FPGA calculator) |
| `Makefile` | Cross-compilation build system (`arm-linux-gnueabihf-`) |
| `boot-led.service` | Systemd service unit |
| `README.md` | This documentation |

## See Also

- [Deployment Workflow](../../../documentation/deployment/deployment_workflow.md) - Full deployment guide
