# HPS Software Directory

**Purpose:** Software that runs on the Hard Processor System (HPS - ARM Cortex-A9) on the DE10-Nano board.

---

## Directory Structure

```
HPS/
├── calculator_test/          # Calculator driver and test suite
│   ├── calculator_driver.h  # Driver API header
│   ├── calculator_driver.c  # Driver implementation (with logging)
│   ├── logger.h             # Logging system header
│   ├── logger.c              # Logging system implementation
│   ├── test_cases.h/c        # Basic operation test cases (30 tests)
│   ├── hft_test_cases.h/c    # HFT operation test cases (29 tests)
│   ├── main.c                # Test harness (with logging)
│   ├── Makefile              # Build system
│   ├── README.md             # Test suite documentation
│   └── LOGGING_GUIDE.md      # Comprehensive logging guide
├── integration/              # Linux kernel integration tools
│   ├── integrate_linux_driver.sh    # Integration script (Linux/WSL)
│   ├── integrate_linux_driver.bat   # Integration script (Windows)
│   ├── example_userspace_makefile   # Example Makefile template
│   └── test_integration.sh          # Integration test suite
└── led_examples/             # LED control examples
    ├── basic/                # Basic LED example (HPS_LED)
    └── advanced/             # Advanced LED example with UIO (HPS_LED_update)
```

---

## Quick Start

### Build Test Suite

```bash
cd HPS/calculator_test
make

# For native compilation (on DE10-Nano)
make CROSS_COMPILE=
```

### Run Tests

```bash
# Normal output (INFO level)
./calculator_test

# Verbose (DEBUG level)
./calculator_test -v

# Trace (TRACE level - maximum detail)
./calculator_test -vv
```

### Linux Integration

```bash
# Integrate into Linux kernel
cd ../integration
./integrate_linux_driver.sh -k /path/to/linux-kernel

# Test integration
./test_integration.sh
```

---

## Features

### Comprehensive Logging

- **5 log levels**: ERROR, WARN, INFO, DEBUG, TRACE
- **Timestamps**: All messages include timestamps
- **File/Line tracking**: Know exactly where logs come from
- **Color-coded output**: Easy to scan in terminal
- **Register dumps**: See all register states
- **Hex dumps**: Debug data buffers

### Driver Features

- Memory-mapped I/O via `/dev/mem`
- Register-level access with verification
- Operation tracking and error reporting
- Timeout detection with detailed diagnostics
- Status polling with progress reporting

### Test Suite

- **30 basic operation tests**: ADD, SUB, MUL, DIV
- **29 HFT operation tests**: SMA, EMA, statistical functions
- **Comprehensive error handling**: All failures logged
- **Real-time LED observation**: Watch results on hardware

---

## Documentation

- **[LOGGING_GUIDE.md](calculator_test/LOGGING_GUIDE.md)** - Complete logging system guide
- **[calculator_test/README.md](calculator_test/README.md)** - Test suite documentation
- **[../Docs/hps/linux_driver_development.md](../Docs/hps/linux_driver_development.md)** - Linux integration guide

---

## Integration

See `integration/` directory for Linux kernel integration tools and tests.

---

## Using Prebuilt Linux Image

This section covers using a prebuilt Linux image on the SD card with the repository.

### Prerequisites

1. **Prebuilt Linux Image:**
   - Download a prebuilt Linux image for DE10-Nano from Terasic/Intel
   - Write it to SD card using `dd` (Linux) or Win32DiskImager (Windows):
     ```bash
     # Linux - BE CAREFUL: Replace /dev/sdX with your SD card device
     sudo dd if=de10-nano-image.img of=/dev/sdX bs=4M status=progress
     ```

2. **Repository on Board:**
   - Boot the DE10-Nano with the SD card
   - Connect via SSH or serial console
   - Clone or pull the repository to the board:
     ```bash
     git clone <repository-url>
     # Or if already cloned, pull updates:
     cd low-latency-market-analysis
     git pull
     ```

### Building HPS Software

```bash
# Navigate to HPS directory
cd HPS

# Build all HPS components
make

# Or build specific components:
make calculator_test
make led_examples
```

### Updating FPGA Bitstream

The FPGA bitstream must be updated on the SD card for the hardware to work correctly.

**Method 1: Update RBF on SD Card (Recommended for Permanent Configuration)**

1. Build the FPGA bitstream on your development machine:
   ```bash
   cd ../FPGA
   make rbf
   # Creates: build/output_files/DE10_NANO_SoC_GHRD.rbf
   ```

2. Copy the RBF file to the SD card FAT partition:
   - Mount the SD card FAT partition (usually the first partition)
   - Copy `../FPGA/build/output_files/DE10_NANO_SoC_GHRD.rbf` to the FAT partition
   - Rename it to `soc_system.rbf` (if your boot script expects this name)

3. Set board MSEL switches:
   - **MSEL[5:0]**: Set to `001000` (MSEL = 8) for FPGA configuration from SD card
   - Check DE10-Nano manual for exact switch positions

4. Power cycle the board - FPGA will configure automatically from SD card

**Method 2: Program via JTAG (Temporary - Lost on Power Cycle)**

```bash
# On development machine
   cd ../FPGA
make program_fpga

# Or manually:
quartus_pgm --mode=jtag --operation=p\;build/output_files/DE10_NANO_SoC_GHRD.sof@2
```

**Method 3: Load from HPS at Runtime**

```bash
# On the DE10-Nano board
# Copy RBF file to board (via network or SD card)
# Load using fpga_manager:
echo soc_system.rbf > /sys/class/fpga_manager/fpga0/firmware
cat /sys/class/fpga_manager/fpga0/state
# Should show: "operating" when loaded
```

### Running Tests

After FPGA is configured and HPS software is built:

```bash
# Run calculator test suite
cd HPS/calculator_test
sudo ./calculator_test

# Or with verbose output:
sudo ./calculator_test -v

# Run LED examples
cd ../led_examples/basic
sudo ./HPS_FPGA_LED

# Or advanced example:
cd ../advanced
sudo ./hps_fpga_led_control
```

### Verifying FPGA Configuration

```bash
# Check if FPGA is configured
cat /sys/class/fpga_manager/fpga0/state
# Should show: "operating"

# Check memory mapping
sudo cat /proc/iomem | grep -i fpga
# Should show FPGA bridge addresses
```

---

**Last Updated:** 2026-01-17
