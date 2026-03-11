# Calculator Test Suite

## Overview

Comprehensive test suite for the hardware calculator IP core. Tests all operations (ADD, SUB, MUL, DIV) with various inputs including edge cases and real-world examples.

## Features

- **33 Test Cases:** Comprehensive coverage of calculator operations (ADD, SUB, MUL, DIV) including 3 IEEE 754 edge cases (div-by-zero, overflow, underflow)
- **Comprehensive Logging:** 5-level logging system (ERROR, WARN, INFO, DEBUG, TRACE)
- **Colored Output:** Easy-to-read pass/fail indicators
- **LED Observation:** Delays between tests to watch LED changes
- **Error Reporting:** Detailed failure information with register dumps
- **Cross-Platform:** Builds for ARM (cross-compile) or native x86 (simulation)
- **Debugging Tools:** Register dumps, hex dumps, operation tracking

## Files

| File | Description |
|------|-------------|
| `main.c` | Test harness with colored output, reporting, and logging |
| `test_cases.c/h` | 33 test cases (30 basic operations + 3 IEEE 754 edge cases) |
| `Makefile` | Cross-compilation build system |
| `../../drivers/calculator/` | Shared UIO-based calculator driver |
| `../../libs/logger/` | Reusable logging library (timestamps, levels, dumps) |

## Building

### Cross-Compilation (Recommended)

Build on your development machine for ARM target:

```bash
# Ensure ARM toolchain is installed
sudo apt-get install gcc-arm-linux-gnueabihf

# Build
make

# Output: calculator_test (ARM executable)
```

### Native Compilation (On DE10-Nano)

Build directly on the DE10-Nano:

```bash
make CROSS_COMPILE=
```

## Deployment

### Method 1: Network Transfer (Recommended)

```bash
# Transfer to DE10-Nano
scp calculator_test root@<board-ip>:/root/

# Run on DE10-Nano
ssh root@192.168.2.2
cd /root
./calculator_test
```

### Method 2: SD Card

```bash
# Mount SD card
# Copy to SD card
sudo cp calculator_test /media/$USER/rootfs/root/

# Unmount, insert in DE10-Nano, boot
# Then run: ./calculator_test
```

### Method 3: USB Drive

```bash
# Copy to USB drive
cp calculator_test /media/$USER/usb_drive/

# Insert USB in DE10-Nano
mount /dev/sda1 /mnt
cp /mnt/calculator_test /root/
umount /mnt
./calculator_test
```

## Running

### Basic Usage

```bash
./calculator_test
```

Hardware access uses the Linux UIO framework (`/dev/uioN`). Root is not required.

### Command-Line Options

```bash
# Show help
./calculator_test -h

# Quick mode (no delays, faster testing)
./calculator_test -q

# Verbose output (DEBUG log level)
./calculator_test -v

# Trace output (TRACE log level - maximum detail)
./calculator_test -vv
```

### Logging

The test suite includes comprehensive logging at multiple levels:

- **Default (INFO):** Normal operation messages, test results
- **Verbose (-v, DEBUG):** Register reads/writes, operation details
- **Trace (-vv, TRACE):** Register dumps, hex dumps, all state changes

See **[Logger Library](../libs/logger/README.md)** for complete logging documentation.

## Expected Output

```
========================================================================
                   FPGA CALCULATOR TEST SUITE
========================================================================
Hardware-Accelerated Floating Point Calculator Verification
DE10-Nano SoC - HPS to FPGA Communication Test
========================================================================

Initializing calculator driver...
Calculator driver initialized (UIO: /dev/uio0, fpga-calculator)
Hardware version: 0x00010001

✓ Calculator driver initialized successfully

Running 33 test cases...

Note: Watch LED[7:0] to see result register bits change in real-time!

────────────────────────────────────────────────────────────────────────
[Test 1/33] Basic addition: 1.0 + 2.0 = 3.0
────────────────────────────────────────────────────────────────────────
  Operation:    ADD
  Operand A:    1.000000
  Operand B:    2.000000
  Expected:     3.000000
  Result:       3.000000
  Status:       ✓ PASS

[... 32 more tests ...]

========================================================================
                        TEST SUMMARY
========================================================================
Total tests:    33
Passed:         33
Failed:         0
Success rate:   100.0%
========================================================================
✓ ALL TESTS PASSED!
Hardware calculator is functioning correctly.
========================================================================
```

## Test Cases

### Addition Tests (5 cases)
- Basic positive numbers
- Negative + Positive
- Zero addition
- Decimal numbers
- Negative + Negative

### Subtraction Tests (5 cases)
- Basic subtraction
- Negative operands
- Zero minus positive
- Equal operands
- Pi-based calculation

### Multiplication Tests (6 cases)
- Basic multiplication
- Negative operands
- Fractional numbers
- Zero multiplication
- Negative × Negative
- Decimal precision

### Division Tests (6 cases)
- Basic division
- Even division
- Negative operands
- Fractional results
- Decimal results
- Repeating decimals

### Edge Cases and Special Values (4 cases)
- Large + Small numbers
- Very large × Very small
- Unity operations
- Decimal precision limits

### Real-World Examples (4 cases)
- 2π calculation
- One third (1/3)
- Temperature conversion
- Physics calculations

### IEEE 754 Edge Cases — expect hardware error (3 cases)
- Division by zero (1.0 / 0.0)
- Overflow (1e38 × 10)
- Underflow (1e-38 / 1e10)

These three cases use `expect_error = true`: the test passes only when the calculator hardware asserts the ERROR flag.

## LED Observation

During testing, observe LED[7:0] on the DE10-Nano:

- LEDs display `result[7:0]` (lower 8 bits of IEEE 754 result)
- LEDs update in real-time as calculations complete
- 500ms delay between tests allows visual observation
- Use `--quick` to skip delays for fast testing

**Note:** LED patterns may not be intuitive since they show mantissa bits of IEEE 754 format. The LEDs are for visual feedback that calculations are running, not for reading actual values.

## Troubleshooting

### Error: "Failed to open UIO device 'fpga-calculator'"

**Solution:** Verify the UIO device exists and the FPGA is programmed:
```bash
ls /sys/class/uio/*/name    # Expect: fpga-calculator
cat /sys/class/fpga_bridge/*/state   # Expect: enabled
```
If not present, check that `CONFIG_UIO_PDRV_GENIRQ=y` is set in the kernel and the DTS has the correct `compatible = "generic-uio"` node for the calculator IP.

### Error: "Calculator not initialized"

**Possible causes:**
1. FPGA not programmed with calculator design
2. Calculator IP not integrated in QSys
3. Base address mismatch

**Solutions:**
1. Program FPGA: `make fast-flash` (from FPGA directory)
2. Check QSys integration (see `../../documentation/deployment/deployment_workflow.md`)
3. Verify the UIO device name matches `CALC_UIO_NAME` in `calculator_driver.h` (`fpga-calculator`)

### Error: "Calculator operation timeout"

**Possible causes:**
1. Calculator clock not connected
2. Calculator in reset state
3. Hardware malfunction

**Solutions:**
1. Verify clock connection in QSys
2. Check reset signal is deasserted
3. Reprogram FPGA

### All Tests Fail with Same Result

**Possible causes:**
1. Calculator not performing operations
2. Register access not working
3. Result register stuck

**Solutions:**
1. Check calculator core is instantiated in QSys
2. Verify Avalon-MM connections
3. Test register access with simple reads/writes

### Results Nearly Correct but Fail

**Solution:** Adjust tolerance in main.c:
```c
#define FLOAT_TOLERANCE 0.01f  // Increase from 0.001f
```

IEEE 754 floating-point arithmetic has inherent precision limits.

## Performance

- **Test Duration:** ~15 seconds (with delays), ~1 second (quick mode)
- **Per-Test Time:** ~500ms (with delay), ~10-30ms (quick mode)
- **Calculator Latency:** 3-7 clock cycles (60-140ns @ 50MHz)
- **Memory Access:** Single-cycle Avalon-MM (no wait states)

## Integration with Other Software

### Use in Your Own Programs

```c
#include "calculator_driver.h"

int main() {
    float result;

    // Initialize
    if (calculator_init() != 0) {
        return 1;
    }

    // Perform calculation
    calculator_perform_operation(CALC_OP_ADD, 10.5f, 20.3f, &result);
    printf("Result: %f\n", result);

    // Cleanup
    calculator_cleanup();
    return 0;
}
```

Link with: `gcc -lm your_program.c ../../drivers/calculator/calculator_driver.c ../../libs/logger/logger.c -o your_program`

## License

This test suite is provided as part of the DE10-Nano FPGA calculator project.

## References

- **FPGA Design:** `../../FPGA/ip/custom/calculator/`
- **Integration Guide:** `../../documentation/deployment/deployment_workflow.md`
- **Register Map:** `../../FPGA/ip/custom/calculator/README.md`
