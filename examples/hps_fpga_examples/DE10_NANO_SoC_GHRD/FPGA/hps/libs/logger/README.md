# Logger Library

Reusable logging library for HPS applications on the DE10-Nano.

## Overview

The logger library provides comprehensive logging with:
- Multiple log levels (ERROR, WARN, INFO, DEBUG, TRACE)
- Timestamps with millisecond precision
- File and line number tracking
- Colored terminal output
- Hex dump and register dump utilities

## Integration

### Include Path

Add to your Makefile:

```makefile
LOGGER_DIR = ../libs/logger
CFLAGS += -I$(LOGGER_DIR)
SRCS += $(LOGGER_DIR)/logger.c
```

### Source Code

```c
#include "logger.h"

int main() {
    // Initialize logging
    logger_init(LOG_LEVEL_INFO, stderr);
    
    // Use logging macros
    LOG_INFO("Application started");
    LOG_DEBUG("Debug message: value=%d", 42);
    LOG_ERROR("Something went wrong");
    
    return 0;
}
```

## Log Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| ERROR | Critical errors that prevent operation | Driver failures, hardware errors |
| WARN | Warnings that don't stop execution | Resource busy, unexpected values |
| INFO | Important operational messages | Init/cleanup, operation status |
| DEBUG | Detailed debugging information | Register operations, state changes |
| TRACE | Maximum verbosity | Register dumps, hex dumps |

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
// Register operations (logged at DEBUG level)
LOG_REG_READ(offset, value);
LOG_REG_WRITE(offset, value);

// Operation tracking (logged at INFO level)
LOG_OP_START(operation, operand_a, operand_b);
LOG_OP_COMPLETE(operation, result);
LOG_OP_ERROR(operation, error_code);
```

### Data Dumps

```c
// Hex dump of memory/data
uint8_t buffer[64];
logger_hex_dump(LOG_LEVEL_DEBUG, "Buffer contents", buffer, sizeof(buffer));

// Register dump
logger_register_dump(LOG_LEVEL_TRACE, "Calculator Registers", regs, 16);
```

## API Reference

### Initialization

```c
// Initialize with level and output file
void logger_init(log_level_t level, FILE *output_file);

// Initialize with defaults (INFO level, stderr)
LOGGER_INIT_DEFAULT();

// Initialize with custom level
LOGGER_INIT_LEVEL(LOG_LEVEL_DEBUG);

// Initialize with file output
LOGGER_INIT_FILE(log_file);
```

### Configuration

```c
// Change log level at runtime
void logger_set_level(log_level_t level);

// Get current log level
log_level_t logger_get_level(void);

// Enable/disable logging
void logger_enable(bool enable);

// Redirect output
void logger_set_output(FILE *output_file);
```

### Utilities

```c
// Get log level name as string
const char *logger_level_name(log_level_t level);

// Format timestamp
void logger_format_timestamp(char *buffer, size_t buffer_size);
```

## Output Format

```
[2026-01-16 18:37:33.123] [filename.c:45] INFO  Message here
```

Components:
- Timestamp with millisecond precision
- Source file and line number
- Log level (color-coded in terminal)
- Message

## Colors

When output is a terminal:
- **ERROR**: Red
- **WARN**: Yellow
- **INFO**: Green
- **DEBUG**: Cyan
- **TRACE**: Magenta

## Performance

| Level | Overhead | Recommended Use |
|-------|----------|-----------------|
| NONE | 0% | Production (no logging) |
| ERROR | minimal | Production |
| WARN | minimal | Production |
| INFO | minimal | Normal operation |
| DEBUG | 1-2% | Development |
| TRACE | 5-10% | Deep debugging |

## Files

- `logger.h` - Header file with API and macros
- `logger.c` - Implementation
- `README.md` - This documentation

## See Also

- [Calculator Test Suite](../../calculator_test/README.md) - Example usage
