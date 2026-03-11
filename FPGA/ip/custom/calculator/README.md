# Hardware Calculator IP Core

## Overview

Hardware-accelerated floating-point calculator IP core for DE10-Nano FPGA with IEEE 754 single precision operations.

## Features

- **Floating Point Operations:** ADD, SUB, MUL, DIV (IEEE 754 single precision)
- **Avalon-MM Interface:** Control and status registers
- **LED Display:** Real-time result visualization on LED[7:0]
- **Pipeline:** Fixed 7-stage pipeline (tied to `start_pipe[6]` in float_ops)
- **Interrupt Support:** Operation completion signaling

## Register Map (Avalon-MM)

| Offset | Register      | Access | Description |
|--------|---------------|--------|-------------|
| 0x00   | CONTROL       | R/W    | [31]=start, [3:0]=operation |
| 0x04   | OPERAND_A     | R/W    | 32-bit float operand A |
| 0x08   | OPERAND_B     | R/W    | 32-bit float operand B |
| 0x0C   | RESULT        | R      | 32-bit float result |
| 0x10   | STATUS        | R      | [0]=busy, [1]=error, [2]=done, [3]=buf_full |
| 0x14   | INT_ENABLE    | R/W    | [0]=interrupt enable on done |
| 0x18   | BUFFER_CTRL   | R/W    | [15:0]=window_size, [16]=reset_buffer |
| 0x1C   | BUFFER_WRITE  | W      | Write price to circular buffer |
| 0x20   | BUFFER_COUNT  | R      | Current buffer fill count |
| 0x24   | EMA_ALPHA     | R/W    | Alpha parameter for EMA (32-bit float) |
| 0x28   | CONFIG_FLAGS  | R/W    | Configuration bits |
| 0x2C   | ERROR_CODE    | R      | [0]=watchdog, [1]=overflow, [2]=nan, [3]=div_zero, [4]=underflow |
| 0x3C   | VERSION       | R      | IP version (0x00010001) |

## Operation Codes

- `4'h0`: No-op
- `4'h1`: ADD (A + B)
- `4'h2`: SUB (A - B)
- `4'h3`: MUL (A * B)
- `4'h4`: DIV (A / B)

## Module Hierarchy

```
calculator.v                    # Top-level wrapper
├── calculator_avalon_mm.v      # Avalon-MM slave interface
├── calculator_registers.v      # Register file
├── calculator_core.v           # Computation engine
│   └── calculator_float_ops.v  # IEEE 754 FP operation modules
├── calculator_led_display.v    # LED output driver
├── calculator_price_buffer.v   # Circular price buffer (HFT extension)
└── calculator_hft_ops.v        # HFT operation stubs (wired, no HPS driver)
```

## Usage

The HPS driver uses the Linux UIO framework (`/dev/uio0`) to access the calculator registers — not `/dev/mem` directly.

1. Write IEEE 754 float operands to OPERAND_A (0x04) and OPERAND_B (0x08)
2. Write `(1 << 31) | operation_code` to CONTROL (0x00) to set operands, operation, and assert START in one write
3. Wait for completion via interrupt (UIO `read()`) or poll STATUS (0x10) until bit[2] (DONE) is set
4. Read result from RESULT (0x0C)
5. Read ERROR_CODE (0x2C) if STATUS bit[1] (ERROR) is set
6. Observe LED[7:0] showing result[7:0] in real-time

## Timing

- Clock: 50 MHz
- Pipeline depth: 7 stages (all operations — must match `start_pipe[6]` in `calculator_float_ops.v`)
- Latency: 7 cycles from START assertion to DONE

## Integration

Connected to HPS via the Lightweight HPS-to-FPGA bridge. The QSys base address (offset from `0xFF200000`) is `0x0000` — do not use `0x00080000`, which was a legacy incorrect value. The HPS driver accesses registers through the Linux UIO framework (`/dev/uio0`), not via direct `/dev/mem` mapping.

The interrupt is wired to `hps_0.f2h_irq0` at IRQ number 0 (GIC SPI 40). The `readLatency` in `calculator_hw.tcl` is `1` (registered reads), matching the `always @(posedge clk)` read mux in `calculator_registers.v`.
