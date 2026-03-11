// ============================================================================
// Custom IP - Top Level Module (TEMPLATE)
// ============================================================================
// Copy this directory and rename all files/modules to match your IP name.
// Example: cp -r template/ moving_average/
//          then rename template_ip -> moving_average everywhere
// ============================================================================
//
// This template provides:
//   - Avalon-MM slave interface (clock, reset, read, write, waitrequest)
//   - Register file with example control/status/result registers
//   - Interrupt sender (active-high level, directly from register file)
//   - Placeholder core logic (replace with your computation)
//
// Port naming conventions must match the _hw.tcl interface definitions:
//   avs_s0_*       -> Avalon-MM slave "s0"
//   ins_irq_irq    -> Interrupt sender "irq"
//   coe_<name>_*   -> Conduit export (optional, for GPIO/LED/etc.)
// ============================================================================

module template_ip (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Avalon-MM Slave Interface
    input  wire [3:0]  avs_s0_address,      // Word address (4 bits = 16 registers)
    input  wire        avs_s0_read,
    input  wire        avs_s0_write,
    input  wire [31:0] avs_s0_writedata,
    output wire [31:0] avs_s0_readdata,
    output wire        avs_s0_waitrequest,

    // Interrupt Sender (active-high level-sensitive)
    output wire        ins_irq_irq
);

// ============================================================================
// Internal Signals
// ============================================================================
wire [3:0]  reg_address;
wire        reg_write;
wire        reg_read;
wire [31:0] reg_writedata;
wire [31:0] reg_readdata;

// Core interface signals (connect register file <-> your core logic)
wire [31:0] core_input_a;
wire [31:0] core_input_b;
wire [3:0]  core_operation;
wire        core_start;
wire [31:0] core_result;
wire        core_busy;
wire        core_done;
wire        core_error;

// ============================================================================
// Avalon-MM Slave Interface
// ============================================================================
template_avalon_mm avalon_interface (
    .clk             (clk),
    .reset_n         (reset_n),
    .avs_address     (avs_s0_address),
    .avs_read        (avs_s0_read),
    .avs_write       (avs_s0_write),
    .avs_writedata   (avs_s0_writedata),
    .avs_readdata    (avs_s0_readdata),
    .avs_waitrequest (avs_s0_waitrequest),
    .reg_address     (reg_address),
    .reg_write       (reg_write),
    .reg_read        (reg_read),
    .reg_writedata   (reg_writedata),
    .reg_readdata    (reg_readdata)
);

// ============================================================================
// Register File
// ============================================================================
template_registers register_file (
    .clk             (clk),
    .reset_n         (reset_n),
    .reg_address     (reg_address),
    .reg_write       (reg_write),
    .reg_read        (reg_read),
    .reg_writedata   (reg_writedata),
    .reg_readdata    (reg_readdata),
    // Core interface
    .core_input_a    (core_input_a),
    .core_input_b    (core_input_b),
    .core_operation  (core_operation),
    .core_start      (core_start),
    .core_result     (core_result),
    .core_busy       (core_busy),
    .core_done       (core_done),
    .core_error      (core_error),
    // Interrupt
    .irq_out         (ins_irq_irq)
);

// ============================================================================
// Core Logic (REPLACE THIS with your actual computation)
// ============================================================================
template_core core (
    .clk             (clk),
    .reset_n         (reset_n),
    .input_a         (core_input_a),
    .input_b         (core_input_b),
    .operation       (core_operation),
    .start           (core_start),
    .result          (core_result),
    .busy            (core_busy),
    .done            (core_done),
    .error           (core_error)
);

endmodule
