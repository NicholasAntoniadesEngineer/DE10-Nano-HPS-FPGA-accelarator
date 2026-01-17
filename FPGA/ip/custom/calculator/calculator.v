// ============================================================================
// Hardware Calculator IP - Top Level Module
// ============================================================================
// Top-level wrapper for hardware-accelerated floating-point calculator
// Integrates Avalon-MM interface, register file, computation core, and LED display
// ============================================================================
// Author: Claude Code
// Date: 2026-01-16
// Version: 1.0
// ============================================================================

module calculator (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Avalon-MM Slave Interface
    input  wire [5:0]  avs_s0_address,     // Extended to 6 bits (64 bytes) for HFT
    input  wire        avs_s0_read,
    input  wire        avs_s0_write,
    input  wire [31:0] avs_s0_writedata,
    output wire [31:0] avs_s0_readdata,
    output wire        avs_s0_waitrequest,

    // Conduit: LED Output
    output wire [7:0]  coe_led_output_export,

    // Interrupt Sender
    output wire        ins_irq_irq
);

// ============================================================================
// Internal Signals - Register Interface
// ============================================================================
wire [3:0]  reg_address;        // Extended to 4 bits (16 registers)
wire        reg_write;
wire        reg_read;
wire [31:0] reg_writedata;
wire [31:0] reg_readdata;

// ============================================================================
// Internal Signals - Calculator Core
// ============================================================================
wire [3:0]  calc_operation;     // Extended to 4 bits (16 operations)
wire        calc_start;
wire [31:0] calc_operand_a;
wire [31:0] calc_operand_b;
wire [31:0] calc_result;
wire        calc_busy;
wire        calc_done;
wire        calc_error;

// ============================================================================
// Internal Signals - Price Buffer
// ============================================================================
wire [31:0] buffer_price_write;
wire        buffer_write_enable;
wire        buffer_reset;
wire [15:0] buffer_window_size;
wire [15:0] buffer_count;
wire        buffer_full;

// Price buffer outputs (21 most recent prices)
wire [31:0] price_0, price_1, price_2, price_3, price_4;
wire [31:0] price_5, price_6, price_7, price_8, price_9;
wire [31:0] price_10, price_11, price_12, price_13, price_14;
wire [31:0] price_15, price_16, price_17, price_18, price_19;
wire [31:0] price_20;

// ============================================================================
// Internal Signals - HFT Operations
// ============================================================================
wire [31:0] ema_alpha;

// ============================================================================
// Avalon-MM Slave Interface
// ============================================================================
calculator_avalon_mm avalon_interface (
    .clk               (clk),
    .reset_n           (reset_n),

    // Avalon-MM Slave
    .avs_address       (avs_s0_address),
    .avs_read          (avs_s0_read),
    .avs_write         (avs_s0_write),
    .avs_writedata     (avs_s0_writedata),
    .avs_readdata      (avs_s0_readdata),
    .avs_waitrequest   (avs_s0_waitrequest),

    // Register Interface
    .reg_address       (reg_address),
    .reg_write         (reg_write),
    .reg_read          (reg_read),
    .reg_writedata     (reg_writedata),
    .reg_readdata      (reg_readdata)
);

// ============================================================================
// Register File (Extended for HFT)
// ============================================================================
calculator_registers register_file (
    .clk               (clk),
    .reset_n           (reset_n),

    // Register Access Interface
    .reg_address       (reg_address),
    .reg_write         (reg_write),
    .reg_read          (reg_read),
    .reg_writedata     (reg_writedata),
    .reg_readdata      (reg_readdata),

    // Calculator Core Interface
    .calc_operation    (calc_operation),
    .calc_start        (calc_start),
    .calc_operand_a    (calc_operand_a),
    .calc_operand_b    (calc_operand_b),
    .calc_result       (calc_result),
    .calc_busy         (calc_busy),
    .calc_done         (calc_done),
    .calc_error        (calc_error),

    // Buffer Interface
    .buffer_price_write   (buffer_price_write),
    .buffer_write_enable  (buffer_write_enable),
    .buffer_reset         (buffer_reset),
    .buffer_window_size   (buffer_window_size),
    .buffer_count         (buffer_count),
    .buffer_full          (buffer_full),

    // HFT Parameters
    .ema_alpha         (ema_alpha),

    // Interrupt Output
    .calc_interrupt    (ins_irq_irq)
);

// ============================================================================
// Calculator Core (Computation Engine)
// ============================================================================
calculator_core core (
    .clk               (clk),
    .reset_n           (reset_n),

    // Control Interface
    .operation         (calc_operation),
    .operand_a         (calc_operand_a),
    .operand_b         (calc_operand_b),
    .start             (calc_start),

    // Status and Result
    .result            (calc_result),
    .busy              (calc_busy),
    .done              (calc_done),
    .error             (calc_error)
);

// ============================================================================
// LED Display Module
// ============================================================================
calculator_led_display led_display (
    .clk               (clk),
    .reset_n           (reset_n),
    .result_register   (calc_result),
    .result_valid      (calc_done),
    .led_output        (coe_led_output_export)
);

// ============================================================================
// Price Buffer Module (HFT Extension)
// ============================================================================
calculator_price_buffer price_buffer (
    .clk               (clk),
    .reset_n           (reset_n),

    // Write Interface
    .price_in          (buffer_price_write),
    .write_enable      (buffer_write_enable),
    .buffer_reset      (buffer_reset),

    // Configuration
    .window_size       (buffer_window_size),

    // Price Outputs (21 most recent prices)
    .price_out_0       (price_0),
    .price_out_1       (price_1),
    .price_out_2       (price_2),
    .price_out_3       (price_3),
    .price_out_4       (price_4),
    .price_out_5       (price_5),
    .price_out_6       (price_6),
    .price_out_7       (price_7),
    .price_out_8       (price_8),
    .price_out_9       (price_9),
    .price_out_10      (price_10),
    .price_out_11      (price_11),
    .price_out_12      (price_12),
    .price_out_13      (price_13),
    .price_out_14      (price_14),
    .price_out_15      (price_15),
    .price_out_16      (price_16),
    .price_out_17      (price_17),
    .price_out_18      (price_18),
    .price_out_19      (price_19),
    .price_out_20      (price_20),

    // Status Outputs
    .count             (buffer_count),
    .buffer_full       (buffer_full)
);

// ============================================================================
// HFT Operations Module (Future Extension)
// ============================================================================
// Note: HFT operations module will be instantiated here when implemented
// It will receive:
//   - operation (calc_operation)
//   - price buffer outputs (price_0 through price_20)
//   - window_size (buffer_window_size)
//   - ema_alpha
//   - buffer_count
// And will provide:
//   - HFT result output (to be muxed with calc_result)
//   - HFT done/error signals

endmodule
