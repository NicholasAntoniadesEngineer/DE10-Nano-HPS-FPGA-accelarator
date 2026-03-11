// ============================================================================
// Custom IP - Register File (TEMPLATE)
// ============================================================================
// Implements memory-mapped registers for control, status, and data.
// Registered reads (readLatency=1 in _hw.tcl) — data valid 1 cycle after read.
// ============================================================================
//
// Register Map (customize for your IP):
// Address | Register    | Access | Description
// --------|-------------|--------|-------------------------------------------
// 0x00    | CONTROL     | R/W    | [31]=start, [3:0]=operation
// 0x04    | INPUT_A     | W      | 32-bit input operand A
// 0x08    | INPUT_B     | W      | 32-bit input operand B
// 0x0C    | RESULT      | R      | 32-bit output result
// 0x10    | STATUS      | R      | [0]=busy, [1]=error, [2]=done
// 0x14    | INT_ENABLE  | R/W    | [0]=interrupt enable
// 0x3C    | VERSION     | R      | IP version identifier
// ============================================================================

module template_registers (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Register Interface (from Avalon-MM)
    input  wire [3:0]  reg_address,
    input  wire        reg_write,
    input  wire        reg_read,
    input  wire [31:0] reg_writedata,
    output reg  [31:0] reg_readdata,

    // Core Interface
    output reg  [31:0] core_input_a,
    output reg  [31:0] core_input_b,
    output reg  [3:0]  core_operation,
    output reg         core_start,
    input  wire [31:0] core_result,
    input  wire        core_busy,
    input  wire        core_done,
    input  wire        core_error,

    // Interrupt
    output reg         irq_out
);

// Register addresses
localparam REG_CONTROL    = 4'h0;   // 0x00
localparam REG_INPUT_A    = 4'h1;   // 0x04
localparam REG_INPUT_B    = 4'h2;   // 0x08
localparam REG_RESULT     = 4'h3;   // 0x0C
localparam REG_STATUS     = 4'h4;   // 0x10
localparam REG_INT_ENABLE = 4'h5;   // 0x14
localparam REG_VERSION    = 4'hF;   // 0x3C

// Version: update this when you change your IP
localparam VERSION_CODE = 32'h00010000;  // v1.0

// Internal state
reg [31:0] result_reg;
reg        int_enable_reg;
reg        prev_done;

// ============================================================================
// Write Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        core_input_a    <= 32'h0;
        core_input_b    <= 32'h0;
        core_operation  <= 4'h0;
        core_start      <= 1'b0;
        int_enable_reg  <= 1'b0;
    end else begin
        // Start is a one-cycle pulse
        core_start <= 1'b0;

        if (reg_write) begin
            case (reg_address)
                REG_CONTROL: begin
                    if (!core_busy) begin
                        core_operation <= reg_writedata[3:0];
                        core_start     <= reg_writedata[31];
                    end
                end
                REG_INPUT_A: begin
                    if (!core_busy)
                        core_input_a <= reg_writedata;
                end
                REG_INPUT_B: begin
                    if (!core_busy)
                        core_input_b <= reg_writedata;
                end
                REG_INT_ENABLE: begin
                    int_enable_reg <= reg_writedata[0];
                end
                default: ;  // Read-only or reserved
            endcase
        end
    end
end

// ============================================================================
// Read Logic — Registered (readLatency=1)
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        reg_readdata <= 32'h0;
    end else begin
        case (reg_address)
            REG_CONTROL:    reg_readdata <= {28'h0, core_operation};
            REG_INPUT_A:    reg_readdata <= core_input_a;
            REG_INPUT_B:    reg_readdata <= core_input_b;
            REG_RESULT:     reg_readdata <= result_reg;
            REG_STATUS:     reg_readdata <= {29'h0, core_done, core_error, core_busy};
            REG_INT_ENABLE: reg_readdata <= {31'h0, int_enable_reg};
            REG_VERSION:    reg_readdata <= VERSION_CODE;
            default:        reg_readdata <= 32'h0;
        endcase
    end
end

// ============================================================================
// Result Capture
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        result_reg <= 32'h0;
    end else if (core_done && !core_error) begin
        result_reg <= core_result;
    end
end

// ============================================================================
// Interrupt — Level-sensitive, clear on STATUS read
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        prev_done <= 1'b0;
        irq_out   <= 1'b0;
    end else begin
        prev_done <= core_done;
        if (int_enable_reg && core_done && !prev_done)
            irq_out <= 1'b1;
        if (reg_read && reg_address == REG_STATUS)
            irq_out <= 1'b0;
    end
end

endmodule
