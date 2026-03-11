# Hardware Calculator IP Core

## Overview

Hardware-accelerated floating-point calculator IP core for DE10-Nano FPGA with IEEE 754 single precision operations.

## Features

- **Floating Point Operations:** ADD, SUB, MUL, DIV (IEEE 754 single precision)
- **Avalon-MM Interface:** Control and status registers
- **LED Display:** Real-time result visualization on LED[7:0]
- **Pipeline:** Configurable depth for performance optimization
- **Interrupt Support:** Operation completion signaling

## Register Map (Avalon-MM)

| Offset | Register   | Access | Description |
|--------|------------|--------|-------------|
| 0x00   | CONTROL    | R/W    | [31]=start, [3:0]=operation |
| 0x04   | OPERAND_A  | W      | 32-bit float operand A |
| 0x08   | OPERAND_B  | W      | 32-bit float operand B |
| 0x0C   | RESULT     | R      | 32-bit float result |
| 0x10   | STATUS     | R      | [0]=busy, [1]=error, [2]=done, [3]=buf_full |
| 0x14   | INT_ENABLE | R/W    | [0]=interrupt enable |
| 0x2C   | ERROR_CODE | R      | Detailed error information |
| 0x3C   | VERSION    | R      | IP version (e.g., 0x00010001 = v1.1) |

## Operation Codes

| Code | Operation |
|------|-----------|
| 0    | ADD (A + B) |
| 1    | SUB (A - B) |
| 2    | MUL (A × B) |
| 3    | DIV (A / B) |

## Module Hierarchy

```
calculator.v                    # Top-level wrapper
├── calculator_avalon_mm.v      # Avalon-MM slave interface
├── calculator_registers.v      # Register file
├── calculator_core.v           # Computation engine
│   └── calculator_float_ops.v  # FP operation modules
└── calculator_led_display.v    # LED output driver
```

## Usage

1. Write operands to OPERAND_A (0x04) and OPERAND_B (0x08)
2. Write operation code and start bit to CONTROL (0x00)
3. Poll STATUS (0x10) until done bit is set
4. Read result from RESULT (0x0C)
5. Observe LED[7:0] showing result[7:0] in real-time

## Timing

- Clock: 50 MHz
- Pipeline depth: 3-7 stages (configurable)
- Latency: 3-7 cycles depending on operation

## Integration

Connected to HPS via lightweight Avalon-MM bridge. Base address is assigned by QSys (default: `0x0000` on the LW bridge, mapped to `0xFF200000` from HPS). Verify the actual address in your QSys project's address map.

> **Note:** This is a reference example from the original DE10-Nano GHRD. The main project uses the UIO framework (`/dev/uioN`) for hardware access. See `HPS/drivers/calculator/` for the current driver.
