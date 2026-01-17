# Calculator Driver Logging Guide

**Version:** 1.1  
**Last Updated:** 2026-01-16

---

## Overview

The calculator driver and test suite include comprehensive logging to help debug issues and understand system behavior. All logging is timestamped, includes file/line information, and supports multiple verbosity levels.

---

## Log Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| **ERROR** | Critical errors that prevent operation | Driver initialization failures, hardware errors |
| **WARN** | Warnings that don't stop execution | Busy calculator, register out of range |
| **INFO** | Important operational messages | Driver init/cleanup, operation start/complete |
| **DEBUG** | Detailed debugging information | Register reads/writes, operation details |
| **TRACE** | Maximum verbosity | Register dumps, hex dumps, all state changes |

---

## Usage

### Command Line Options

```bash
# Default (INFO level)
./calculator_test

# Verbose (DEBUG level)
./calculator_test -v

# Trace (TRACE level - maximum detail)
./calculator_test -vv
```

### Programmatic Control

```c
#include "logger.h"

// Initialize with default level (INFO)
logger_init(LOG_LEVEL_INFO, stderr);

// Or set custom level
logger_init(LOG_LEVEL_DEBUG, stderr);

// Change level at runtime
logger_set_level(LOG_LEVEL_TRACE);

// Disable logging temporarily
logger_enable(false);

// Re-enable
logger_enable(true);

// Redirect to file
FILE *log_file = fopen("calculator.log", "w");
logger_set_output(log_file);
```

---

## Log Macros

### Standard Logging

```c
LOG_ERROR("Operation failed: %d", error_code);
LOG_WARN("Calculator is busy, waiting...");
LOG_INFO("Driver initialized successfully");
LOG_DEBUG("Register read: offset=0x%02X, value=0x%08X", offset, value);
LOG_TRACE("State change: idle -> computing");
```

### Specialized Macros

```c
// Register operations (automatically logged at DEBUG level)
LOG_REG_READ(offset, value);
LOG_REG_WRITE(offset, value);

// Operation tracking (automatically logged at INFO level)
LOG_OP_START(op, operand_a, operand_b);
LOG_OP_COMPLETE(op, result);
LOG_OP_ERROR(op, error_code);
```

### Data Dumps

```c
// Hex dump of memory/data
uint8_t buffer[64];
logger_hex_dump(LOG_LEVEL_DEBUG, "Buffer contents", buffer, sizeof(buffer));

// Register dump (all calculator registers)
logger_register_dump(LOG_LEVEL_TRACE, "Calculator Registers", calculator_regs, 16);
```

---

## Log Output Format

### Standard Format

```
[2026-01-16 18:37:33.123] [calculator_driver.c:45] INFO  Driver initialized successfully
[2026-01-16 18:37:33.124] [calculator_driver.c:102] DEBUG REG WRITE: offset=0x00, value=0x80000001
[2026-01-16 18:37:33.125] [calculator_driver.c:170] DEBUG REG READ:  offset=0x0C, value=0x40400000
```

### With Colors (Terminal)

- **ERROR**: Red text
- **WARN**: Yellow text
- **INFO**: Green text
- **DEBUG**: Cyan text
- **TRACE**: Magenta text

---

## Example Log Output

### INFO Level (Default)

```
[2026-01-16 18:37:33.123] [calculator_driver.c:37] INFO  Initializing calculator driver...
[2026-01-16 18:37:33.125] [calculator_driver.c:78] INFO  Calculator driver initialized successfully
[2026-01-16 18:37:33.125] [calculator_driver.c:79] INFO    Physical base: 0xFF280000
[2026-01-16 18:37:33.125] [calculator_driver.c:80] INFO    Virtual base:  0x7f8a5c0000
[2026-01-16 18:37:33.125] [calculator_driver.c:86] INFO    Hardware version: 0x00010001
[2026-01-16 18:37:33.200] [calculator_driver.c:270] INFO  OP START:  operation=0x0, operand_a=1.000000, operand_b=2.000000
[2026-01-16 18:37:33.201] [calculator_driver.c:321] INFO  OP COMPLETE: operation=0x0, result=3.000000
```

### DEBUG Level (-v)

```
[2026-01-16 18:37:33.123] [calculator_driver.c:37] INFO  Initializing calculator driver...
[2026-01-16 18:37:33.123] [calculator_driver.c:39] DEBUG HPS_LW_BRIDGE_BASE: 0xFF200000
[2026-01-16 18:37:33.123] [calculator_driver.c:40] DEBUG CALCULATOR_0_BASE: 0x00080000
[2026-01-16 18:37:33.123] [calculator_driver.c:41] DEBUG CALCULATOR_BASE: 0xFF280000
[2026-01-16 18:37:33.123] [calculator_driver.c:42] DEBUG HW_REGS_SPAN: 0x00200000 (2097152 bytes)
[2026-01-16 18:37:33.124] [calculator_driver.c:45] DEBUG Opening /dev/mem for memory mapping...
[2026-01-16 18:37:33.124] [calculator_driver.c:52] DEBUG Successfully opened /dev/mem (fd=3)
[2026-01-16 18:37:33.124] [calculator_driver.c:55] DEBUG Mapping physical memory: base=0xFF200000, span=0x00200000
[2026-01-16 18:37:33.125] [calculator_driver.c:71] DEBUG Memory mapped successfully: virtual_base=0x7f8a5c0000
[2026-01-16 18:37:33.125] [calculator_driver.c:144] DEBUG REG WRITE: offset=0x00, value=0x80000001
[2026-01-16 18:37:33.125] [calculator_driver.c:170] DEBUG REG READ:  offset=0x10, value=0x00000001
[2026-01-16 18:37:33.200] [calculator_driver.c:198] DEBUG Waiting for calculation completion (timeout: 1000000 iterations)
[2026-01-16 18:37:33.201] [calculator_driver.c:211] DEBUG Calculation completed after 7 polls
```

### TRACE Level (-vv)

Includes all DEBUG output plus:
- Register dumps showing all 16 registers
- Hex dumps of data buffers
- All state transitions
- Detailed timing information

---

## Logging in Driver Functions

### Initialization

```c
int calculator_init(void) {
    LOG_INFO("Initializing calculator driver...");
    LOG_DEBUG("HPS_LW_BRIDGE_BASE: 0x%08X", HPS_LW_BRIDGE_BASE);
    // ... initialization code ...
    LOG_INFO("Calculator driver initialized successfully");
    logger_register_dump(LOG_LEVEL_TRACE, "Initial register state", calculator_regs, 16);
    return 0;
}
```

### Register Operations

All register reads and writes are automatically logged at DEBUG level:

```c
void calculator_write_reg(uint32_t offset, uint32_t value) {
    LOG_REG_WRITE(offset, value);  // Logs: "REG WRITE: offset=0x00, value=0x80000001"
    calculator_regs[offset / 4] = value;
}
```

### Operations

```c
int calculator_perform_operation(...) {
    LOG_OP_START(op, operand_a, operand_b);  // Logs operation start
    // ... perform operation ...
    LOG_OP_COMPLETE(op, *result);  // Logs successful completion
    // OR
    LOG_OP_ERROR(op, error_code);  // Logs error
}
```

---

## Debugging Workflows

### Issue: Driver won't initialize

**Enable TRACE logging:**
```bash
./calculator_test -vv 2>&1 | tee debug.log
```

**Look for:**
- `/dev/mem` open errors
- `mmap()` failures
- Address calculation issues
- Register readback verification failures

### Issue: Operations return wrong results

**Enable DEBUG logging:**
```bash
./calculator_test -v 2>&1 | grep -E "(OP START|OP COMPLETE|REG WRITE|REG READ)"
```

**Check:**
- Operand values written correctly
- Operation code correct
- Result register read correctly
- No errors in status register

### Issue: Timeout errors

**Enable DEBUG logging:**
```bash
./calculator_test -v 2>&1 | grep -E "(waiting|timeout|poll)"
```

**Check:**
- Poll count (should be low for basic ops: ~7 for ADD)
- Status register state at timeout
- Register dump at timeout (TRACE level)

---

## Log File Analysis

### Save logs to file

```bash
# Redirect to file
./calculator_test -v > calculator.log 2>&1

# Or use tee to see output and save
./calculator_test -vv 2>&1 | tee calculator_trace.log
```

### Filter logs

```bash
# Only errors
grep ERROR calculator.log

# Only register operations
grep "REG " calculator.log

# Operation timeline
grep -E "(OP START|OP COMPLETE|OP ERROR)" calculator.log

# Timing information
grep -E "(poll|timeout|waiting)" calculator.log
```

---

## Performance Impact

| Log Level | Overhead | Use Case |
|-----------|----------|----------|
| NONE | 0% | Production (no logging) |
| ERROR | <0.1% | Production (errors only) |
| WARN | <0.1% | Production (warnings + errors) |
| INFO | <0.5% | Normal operation |
| DEBUG | 1-2% | Development/debugging |
| TRACE | 5-10% | Deep debugging (register dumps) |

**Recommendation:**
- Production: INFO or WARN level
- Development: DEBUG level
- Troubleshooting: TRACE level

---

## Integration with Your Application

### Include Logger

```c
#include "calculator_driver.h"
#include "logger.h"

int main() {
    // Initialize logging first
    logger_init(LOG_LEVEL_INFO, stderr);
    
    // Initialize driver (uses logger internally)
    if (calculator_init() != 0) {
        LOG_ERROR("Failed to initialize driver");
        return 1;
    }
    
    // Your application code
    float result;
    calculator_add(1.0f, 2.0f, &result);
    LOG_INFO("Result: %.2f", result);
    
    calculator_cleanup();
    return 0;
}
```

### Custom Log Handler

You can redirect logs to your own logging system:

```c
void my_log_handler(log_level_t level, const char *file, int line, const char *format, ...) {
    // Call logger_log, then forward to your system
    logger_log(level, file, line, format, ...);
    // ... your custom logging ...
}
```

---

## Troubleshooting with Logs

### Common Issues and Log Patterns

**Issue: Permission denied**
```
ERROR: Could not open /dev/mem: Permission denied
```
**Solution:** Run as root or fix permissions

**Issue: Wrong base address**
```
DEBUG: CALCULATOR_BASE: 0xFF280000
ERROR: Register write verification failed: wrote 0x80000001, read 0x00000000
```
**Solution:** Check QSys base address matches driver

**Issue: Hardware not responding**
```
DEBUG: Still waiting... (poll 10000, timeout remaining: 990000)
ERROR: Calculator operation timeout after 1000000 polls
```
**Solution:** Verify FPGA is programmed, check connections

---

## Best Practices

1. **Start with INFO level** - See what's happening without noise
2. **Use DEBUG for development** - Detailed but manageable
3. **Use TRACE only when needed** - Very verbose, impacts performance
4. **Save logs for analysis** - Use `tee` or redirect to file
5. **Filter logs** - Use `grep` to find specific patterns
6. **Check timestamps** - Understand timing and sequence of events

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-16  
**Status:** Complete ✅
