// ============================================================================
// Calculator Register File
// ============================================================================
// Implements the memory-mapped register interface for calculator control
// Handles read/write operations for all calculator registers
// ============================================================================

module calculator_registers (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Avalon-MM Interface (from calculator_avalon_mm)
    input  wire [3:0]  reg_address,        // Register address (byte aligned / 4)
    input  wire        reg_write,          // Write enable
    input  wire        reg_read,           // Read enable
    input  wire [31:0] reg_writedata,      // Data to write
    output reg  [31:0] reg_readdata,       // Data read

    // Calculator Core Interface
    output reg  [3:0]  calc_operation,     // Operation: 0-3=basic, 4-15=HFT
    output reg         calc_start,         // Start calculation (pulse)
    output reg  [31:0] calc_operand_a,     // Operand A
    output reg  [31:0] calc_operand_b,     // Operand B
    input  wire [31:0] calc_result,        // Result from calculator
    input  wire        calc_busy,          // Calculator is busy
    input  wire        calc_done,          // Calculation complete
    input  wire        calc_error,         // Error flag

    // Buffer Interface
    output reg  [31:0] buffer_price_write,  // Price to write to buffer
    output reg         buffer_write_enable, // Write enable pulse
    output reg         buffer_reset,        // Reset buffer
    output reg  [15:0] buffer_window_size,  // Window size configuration
    input  wire [15:0] buffer_count,        // Current buffer count
    input  wire        buffer_full,         // Buffer full flag
    output reg  [31:0] ema_alpha,           // EMA alpha parameter

    // Interrupt
    output reg         calc_interrupt      // Interrupt output
);

// ============================================================================
// Register Map
// ============================================================================
// Address | Register         | Access | Description
// --------|------------------|--------|------------------------------------------
// 0x00    | CONTROL          | R/W    | [31]=start, [3:0]=operation
// 0x04    | OPERAND_A        | W      | 32-bit float operand A
// 0x08    | OPERAND_B        | W      | 32-bit float operand B (or window size)
// 0x0C    | RESULT           | R      | 32-bit float result
// 0x10    | STATUS           | R      | [0]=busy, [1]=error, [2]=done, [3]=buf_full
// 0x14    | INT_ENABLE       | R/W    | [0]=enable interrupt on done
// 0x18    | BUFFER_CONTROL   | R/W    | [15:0]=window_size, [16]=reset_buffer
// 0x1C    | BUFFER_WRITE     | W      | Write price to circular buffer
// 0x20    | BUFFER_COUNT     | R      | Current buffer fill count
// 0x24    | EMA_ALPHA        | R/W    | Alpha parameter for EMA (32-bit float)
// 0x28    | CONFIG_FLAGS     | R/W    | Configuration bits
// 0x2C    | ERROR_CODE       | R      | Detailed error information
// 0x3C    | VERSION          | R      | IP version (0xHFT10001)
// ============================================================================

localparam  REG_CONTROL       = 4'h0;     // 0x00 / 4 = 0
localparam  REG_OPERAND_A     = 4'h1;     // 0x04 / 4 = 1
localparam  REG_OPERAND_B     = 4'h2;     // 0x08 / 4 = 2
localparam  REG_RESULT        = 4'h3;     // 0x0C / 4 = 3
localparam  REG_STATUS        = 4'h4;     // 0x10 / 4 = 4
localparam  REG_INT_ENABLE    = 4'h5;     // 0x14 / 4 = 5
localparam  REG_BUFFER_CTRL   = 4'h6;     // 0x18 / 4 = 6
localparam  REG_BUFFER_WRITE  = 4'h7;     // 0x1C / 4 = 7
localparam  REG_BUFFER_COUNT  = 4'h8;     // 0x20 / 4 = 8
localparam  REG_EMA_ALPHA     = 4'h9;     // 0x24 / 4 = 9
localparam  REG_CONFIG_FLAGS  = 4'hA;     // 0x28 / 4 = 10
localparam  REG_ERROR_CODE    = 4'hB;     // 0x2C / 4 = 11
localparam  REG_VERSION       = 4'hF;     // 0x3C / 4 = 15

// Internal Registers
reg [31:0] control_reg;
reg [31:0] result_reg;
reg [31:0] status_reg;
reg        int_enable_reg;
reg        prev_calc_done;                // Edge detection for done signal
reg [31:0] config_flags_reg;
reg [31:0] error_code_reg;

// HFT Version constant
localparam VERSION_CODE = 32'h00010001;   // HFT v1.0001 (version 1.0001)

// ============================================================================
// Register Write Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        control_reg          <= 32'h0;
        calc_operand_a       <= 32'h0;
        calc_operand_b       <= 32'h0;
        calc_operation       <= 4'b0000;
        calc_start           <= 1'b0;
        int_enable_reg       <= 1'b0;
        buffer_window_size   <= 16'd20;      // Default window = 20
        buffer_reset         <= 1'b0;
        buffer_write_enable  <= 1'b0;
        buffer_price_write   <= 32'h0;
        ema_alpha            <= 32'h3E4CCCCD; // Default α=0.2 (IEEE 754)
        config_flags_reg     <= 32'h0;
        error_code_reg       <= 32'h0;
    end else begin
        // Default: start and write_enable are pulses, clear after one cycle
        calc_start          <= 1'b0;
        buffer_write_enable <= 1'b0;
        buffer_reset        <= 1'b0;

        if (reg_write) begin
            case (reg_address)
                REG_CONTROL: begin
                    control_reg    <= reg_writedata;
                    calc_operation <= reg_writedata[3:0];
                    calc_start     <= reg_writedata[31];  // Start bit triggers calculation
                end

                REG_OPERAND_A: begin
                    calc_operand_a <= reg_writedata;
                end

                REG_OPERAND_B: begin
                    calc_operand_b <= reg_writedata;
                end

                REG_INT_ENABLE: begin
                    int_enable_reg <= reg_writedata[0];
                end

                REG_BUFFER_CTRL: begin
                    buffer_window_size <= reg_writedata[15:0];
                    buffer_reset       <= reg_writedata[16];
                end

                REG_BUFFER_WRITE: begin
                    buffer_price_write  <= reg_writedata;
                    buffer_write_enable <= 1'b1;  // Pulse for one cycle
                end

                REG_EMA_ALPHA: begin
                    ema_alpha <= reg_writedata;
                end

                REG_CONFIG_FLAGS: begin
                    config_flags_reg <= reg_writedata;
                end

                default: begin
                    // Read-only or invalid registers - no action
                end
            endcase
        end
    end
end

// ============================================================================
// Register Read Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        reg_readdata <= 32'h0;
    end else begin
        if (reg_read) begin
            case (reg_address)
                REG_CONTROL: begin
                    reg_readdata <= {31'h0, calc_operation};
                end

                REG_OPERAND_A: begin
                    reg_readdata <= calc_operand_a;
                end

                REG_OPERAND_B: begin
                    reg_readdata <= calc_operand_b;
                end

                REG_RESULT: begin
                    reg_readdata <= result_reg;
                end

                REG_STATUS: begin
                    reg_readdata <= {28'h0, buffer_full, calc_done, calc_error, calc_busy};
                end

                REG_INT_ENABLE: begin
                    reg_readdata <= {31'h0, int_enable_reg};
                end

                REG_BUFFER_CTRL: begin
                    reg_readdata <= {15'h0, buffer_reset, buffer_window_size};
                end

                REG_BUFFER_COUNT: begin
                    reg_readdata <= {16'h0, buffer_count};
                end

                REG_EMA_ALPHA: begin
                    reg_readdata <= ema_alpha;
                end

                REG_CONFIG_FLAGS: begin
                    reg_readdata <= config_flags_reg;
                end

                REG_ERROR_CODE: begin
                    reg_readdata <= error_code_reg;
                end

                REG_VERSION: begin
                    reg_readdata <= VERSION_CODE;
                end

                default: begin
                    reg_readdata <= 32'h0;
                end
            endcase
        end
    end
end

// ============================================================================
// Result Register Update
// ============================================================================
// Capture result when calculation completes
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        result_reg <= 32'h0;
    end else begin
        if (calc_done && !calc_error) begin
            result_reg <= calc_result;
        end
    end
end

// ============================================================================
// Interrupt Generation
// ============================================================================
// Generate interrupt on rising edge of calc_done
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        prev_calc_done <= 1'b0;
        calc_interrupt <= 1'b0;
    end else begin
        prev_calc_done <= calc_done;

        // Rising edge of calc_done triggers interrupt if enabled
        if (int_enable_reg && calc_done && !prev_calc_done) begin
            calc_interrupt <= 1'b1;
        end else begin
            calc_interrupt <= 1'b0;
        end
    end
end

endmodule
