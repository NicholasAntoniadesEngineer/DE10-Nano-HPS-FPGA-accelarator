# LED Control Examples

This directory contains two LED control examples demonstrating HPS-FPGA communication on the DE10-Nano board.

## Directory Structure

```
led_examples/
├── basic/          # Basic LED example using direct memory mapping
└── advanced/       # Advanced LED example using UIO (Userspace I/O)
```

## Basic LED Example

**Location:** `basic/`

Simple LED control example using direct memory mapping via `/dev/mem`. This demonstrates the fundamental approach to HPS-FPGA communication.

### Building

```bash
cd basic
make
```

### Running

```bash
sudo ./HPS_FPGA_LED
```

### Features

- Direct memory mapping to FPGA registers
- Simple LED animation (left-to-right, right-to-left)
- Uses hardware abstraction library (hwlib.h)

## Advanced LED Example

**Location:** `advanced/`

Advanced LED control example using UIO (Userspace I/O) framework. This is the recommended approach for production systems as it provides better security and resource management.

### Building

```bash
cd advanced
make
```

### Running

```bash
sudo ./hps_fpga_led_control
```

### Features

- UIO-based memory mapping
- Device tree support
- Signal handling for clean shutdown
- Configurable LED count and behavior
- Persistent device tree overlay support

### Setup

The advanced example includes a device tree overlay file (`fpga-leds.dts`) that should be compiled and loaded:

```bash
# Compile device tree overlay
dtc -@ -I dts -O dtb -o fpga-leds.dtbo fpga-leds.dts

# Load overlay (on the board)
mkdir -p /config/device-tree/overlays
cp fpga-leds.dtbo /config/device-tree/overlays/
```

## Comparison

| Feature | Basic | Advanced |
|---------|-------|----------|
| Memory Mapping | `/dev/mem` | UIO framework |
| Security | Requires root | Better isolation |
| Device Tree | Not required | Recommended |
| Complexity | Simple | More structured |
| Production Ready | No | Yes |

## Prerequisites

- FPGA must be configured with LED PIO controller
- For basic example: Root access required
- For advanced example: UIO device must be configured in device tree

## Related Documentation

- [HPS-FPGA Communication](../../Docs/hps/hps_fpga_communication.md)
- [Linux Driver Development](../../Docs/hps/linux_driver_development.md)
