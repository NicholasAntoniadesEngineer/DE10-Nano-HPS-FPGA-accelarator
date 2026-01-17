# HPS Software Directory

**Purpose:** Software that runs on the Hard Processor System (HPS - ARM Cortex-A9) on the DE10-Nano board.

---

## Directory Structure

```
hps/
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
└── integration/              # Linux kernel integration tools
    ├── integrate_linux_driver.sh    # Integration script (Linux/WSL)
    ├── integrate_linux_driver.bat   # Integration script (Windows)
    ├── example_userspace_makefile   # Example Makefile template
    └── test_integration.sh          # Integration test suite
```

---

## Quick Start

### Build Test Suite

```bash
cd hps/calculator_test
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
- **[../docs/LINUX_INTEGRATION.md](../docs/LINUX_INTEGRATION.md)** - Linux integration guide

---

## Integration

See `integration/` directory for Linux kernel integration tools and tests.

---

**Last Updated:** 2026-01-16
