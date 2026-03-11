# Boot LED Indicator

Visual indicator that the custom Linux image is running on the DE10-Nano.

## Overview

This application displays LED patterns on the DE10-Nano's user LEDs to provide visual confirmation that:
- The custom Linux image has booted successfully
- The HPS-FPGA bridge is functional
- The system is running

## Features

- Startup animation (LEDs fill and flash)
- Multiple continuous patterns:
  - Heartbeat (double-pulse like a heartbeat)
  - Knight Rider (bouncing light)
  - Binary counter
- Runs automatically as systemd service
- Clean shutdown on SIGTERM/SIGINT
- No external dependencies (uses direct /dev/mem access)

## Building

```bash
# Cross-compile for ARM
make

# Native compile on DE10-Nano
make CROSS_COMPILE=

# Custom LED offset (if your QSys design differs)
make LED_OFFSET=0x10010
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
# Run startup pattern and continue with heartbeat
sudo ./boot_led

# Run startup pattern only, then exit
sudo ./boot_led --oneshot

# Run as background daemon
sudo ./boot_led --daemon

# Select different patterns
sudo ./boot_led --pattern 0    # Heartbeat (default)
sudo ./boot_led --pattern 1    # Knight Rider
sudo ./boot_led --pattern 2    # Binary counter

# Show help
./boot_led --help
```

## LED Patterns

### Startup Pattern

On boot, the LEDs display:
1. LEDs fill from right to left (one at a time)
2. All LEDs flash 3 times
3. Transition to continuous pattern

### Heartbeat Pattern (Default)

A double-pulse pattern resembling a heartbeat:
- Center LEDs light briefly
- Pause
- Wider center LEDs light
- Longer pause
- Repeat

This pattern indicates the system is alive and responsive.

### Knight Rider Pattern

Classic bouncing light effect:
- Two LEDs move back and forth
- Creates a scanning appearance

### Binary Counter Pattern

LEDs display an incrementing 8-bit counter:
- Counts from 0 to 255
- Wraps around
- Good for debugging

## Hardware Requirements

- DE10-Nano with FPGA programmed
- LED PIO connected to lightweight HPS-FPGA bridge
- Default offset assumes standard GHRD configuration

## Customization

### LED PIO Offset

If your FPGA design uses a different LED offset, specify it at compile time:

```bash
make LED_OFFSET=0x10010
```

Or modify `LED_PIO_OFFSET` in boot_led.c.

### Pattern Timing

Timing constants can be adjusted in boot_led.c:
- `STARTUP_PATTERN_DELAY_US` - Startup animation speed
- `HEARTBEAT_ON_US` / `HEARTBEAT_OFF_US` - Heartbeat timing
- `KNIGHT_RIDER_DELAY_US` - Knight rider speed

## Troubleshooting

### LEDs not responding

1. Check FPGA is programmed with a design that has LED PIO
2. Verify LED PIO offset matches your QSys configuration
3. Ensure running as root (needed for /dev/mem)

### Permission denied

Run as root:
```bash
sudo ./boot_led
```

### Service fails to start

Check logs:
```bash
journalctl -u boot-led -f
```

## Files

| File | Description |
|------|-------------|
| `boot_led.c` | Main application source |
| `Makefile` | Build system |
| `boot-led.service` | Systemd service unit |
| `README.md` | This documentation |

## See Also

- [Deployment Workflow](../../../documentation/deployment/deployment_workflow.md) - Full deployment guide
