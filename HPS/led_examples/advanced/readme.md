# HPS-FPGA Enhanced LED Control

This is an enhanced implementation of the HPS-FPGA LED control example that demonstrates best practices for hardware interaction on the DE10-Nano SoC platform.

## Key Improvements

1. Uses the UIO (Userspace I/O) framework instead of direct memory mapping
2. Proper error handling and resource management
3. Clean separation of concerns (hardware access vs. business logic)
4. Configuration through a separate configuration file
5. Proper signal handling for clean shutdown
6. Logging support

## Prerequisites

1. Linux kernel with UIO support enabled
2. FPGA must be programmed with the GHRD (Golden Hardware Reference Design)
3. Device tree compiler (dtc) installed:
   ```bash
   sudo apt-get install device-tree-compiler
   ```

## Initial Setup (One-Time Only)

There are two ways to set up the application:

### Option 1: Automatic Setup (Recommended)
1. Run the setup script (requires root privileges):
   ```bash
   ./setup_persistent.sh
   ```
2. Reboot your system:
   ```bash
   sudo reboot
   ```

### Option 2: Manual Setup
If you prefer to set up manually or the automatic setup doesn't work:

1. Load the UIO drivers manually:
   ```bash
   sudo modprobe uio
   sudo modprobe uio_pdrv_genirq
   ```

2. Compile and apply the device tree overlay:
   ```bash
   make dtbo
   sudo mkdir -p /boot/overlays
   sudo cp fpga-leds.dtbo /boot/overlays/
   ```

To make these changes persistent across reboots:
1. Add these lines to `/etc/modules`:
   ```
   uio
   uio_pdrv_genirq
   ```
2. Add this line to `/boot/config.txt`:
   ```
   dtoverlay=fpga-leds
   ```

## Building the Application

1. Compile the application:
   ```bash
   make
   ```

## Running the Application

1. After initial setup and building, you can run the application with:
   ```bash
   sudo ./hps_fpga_led_control
   ```

2. The LED animation will start automatically
3. Press Ctrl+C to stop the animation cleanly

## Troubleshooting

If the application fails to start:

1. Check if UIO drivers are loaded:
   ```bash
   lsmod | grep uio
   ```

2. Verify the device tree overlay is applied:
   ```bash
   ls -l /dev/uio*
   ```

3. Check system logs for errors:
   ```bash
   dmesg | grep uio
   ```

## Files

- `main.c` - Main application logic
- `fpga_uio.h/c` - UIO hardware interface layer
- `led_controller.h/c` - LED control logic
- `config.h` - Configuration constants
- `fpga-leds.dts` - Device Tree Overlay source
- `Makefile` - Build system
- `setup_persistent.sh` - Automatic setup script 