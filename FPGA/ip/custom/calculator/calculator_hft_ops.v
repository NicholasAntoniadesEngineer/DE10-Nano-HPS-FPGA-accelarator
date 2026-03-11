// ============================================================================
// Calculator HFT Operations Module
// ============================================================================
// Implements High-Frequency Trading calculations using price buffer
// Uses calculator_float_ops for basic arithmetic operations
// ============================================================================

module calculator_hft_ops (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Operation Control
    input  wire [3:0]  operation,           // 4=SMA, 5=EMA, 6-15=other HFT ops
    input  wire [15:0] window_size,         // Number of periods
    input  wire [31:0] ema_alpha,           // EMA smoothing factor (float)
    input  wire        start,               // Start operation (pulse)

    // Price Buffer Interface (from calculator_price_buffer)
    input  wire [31:0] price_0,             // Most recent price
    input  wire [31:0] price_1,
    input  wire [31:0] price_2,
    input  wire [31:0] price_3,
    input  wire [31:0] price_4,
    input  wire [31:0] price_5,
    input  wire [31:0] price_6,
    input  wire [31:0] price_7,
    input  wire [31:0] price_8,
    input  wire [31:0] price_9,
    input  wire [31:0] price_10,
    input  wire [31:0] price_11,
    input  wire [31:0] price_12,
    input  wire [31:0] price_13,
    input  wire [31:0] price_14,
    input  wire [31:0] price_15,
    input  wire [31:0] price_16,
    input  wire [31:0] price_17,
    input  wire [31:0] price_18,
    input  wire [31:0] price_19,
    input  wire [31:0] price_20,
    input  wire [15:0] buffer_count,        // Current buffer fill

    // Result
    output reg  [31:0] result,              // Calculation result (IEEE 754 float)
    output reg         result_valid,        // Result is valid (pulse)
    output reg         error                // Error flag
);

// ============================================================================
// Operation Codes
// ============================================================================
localparam OP_SMA        = 4'd4;   // Simple Moving Average
localparam OP_EMA        = 4'd5;   // Exponential Moving Average
localparam OP_WMA        = 4'd6;   // Weighted Moving Average
localparam OP_VWAP       = 4'd7;   // Volume-Weighted Average Price
localparam OP_STD_DEV    = 4'd8;   // Standard Deviation
localparam OP_RSI        = 4'd9;   // Relative Strength Index
localparam OP_BOLL_UP    = 4'd10;  // Bollinger Upper Band
localparam OP_BOLL_DN    = 4'd11;  // Bollinger Lower Band
localparam OP_MIN        = 4'd12;  // Minimum
localparam OP_MAX        = 4'd13;  // Maximum
localparam OP_RANGE      = 4'd14;  // Range (Max - Min)

// ============================================================================
// State Machine
// ============================================================================
localparam STATE_IDLE        = 3'b000;
localparam STATE_SMA_SUM     = 3'b001;
localparam STATE_SMA_DIV     = 3'b010;
localparam STATE_WAIT_FP     = 3'b011;
localparam STATE_DONE        = 3'b100;

reg [2:0] state, next_state;
reg [7:0] price_index;              // Current price being processed
reg [31:0] accumulator;             // Accumulator for sum
reg [3:0] fp_wait_counter;          // Wait counter for FP operations

// ============================================================================
// Floating Point Unit Interface
// ============================================================================
// We'll reuse the basic calculator_float_ops for ADD and DIV
wire [31:0] fp_result;
wire        fp_result_valid;
wire        fp_error;
reg  [1:0]  fp_operation;           // 0=ADD, 3=DIV
reg  [31:0] fp_operand_a;
reg  [31:0] fp_operand_b;
reg         fp_start;

calculator_float_ops fp_unit (
    .clk           (clk),
    .reset_n       (reset_n),
    .operation     (fp_operation),
    .operand_a     (fp_operand_a),
    .operand_b     (fp_operand_b),
    .start         (fp_start),
    .result        (fp_result),
    .result_valid  (fp_result_valid),
    .error         (fp_error)
);

// ============================================================================
// Price Selector - Mux to select current price from buffer
// ============================================================================
reg [31:0] current_price;

always @(*) begin
    case (price_index)
        8'd0:  current_price = price_0;
        8'd1:  current_price = price_1;
        8'd2:  current_price = price_2;
        8'd3:  current_price = price_3;
        8'd4:  current_price = price_4;
        8'd5:  current_price = price_5;
        8'd6:  current_price = price_6;
        8'd7:  current_price = price_7;
        8'd8:  current_price = price_8;
        8'd9:  current_price = price_9;
        8'd10: current_price = price_10;
        8'd11: current_price = price_11;
        8'd12: current_price = price_12;
        8'd13: current_price = price_13;
        8'd14: current_price = price_14;
        8'd15: current_price = price_15;
        8'd16: current_price = price_16;
        8'd17: current_price = price_17;
        8'd18: current_price = price_18;
        8'd19: current_price = price_19;
        8'd20: current_price = price_20;
        default: current_price = 32'h0;
    endcase
end

// ============================================================================
// State Machine - Sequential Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        state <= STATE_IDLE;
        price_index <= 8'h0;
        accumulator <= 32'h0;
        fp_wait_counter <= 4'h0;
        result <= 32'h0;
        result_valid <= 1'b0;
        error <= 1'b0;
        fp_start <= 1'b0;
    end else begin
        state <= next_state;

        // Default: fp_start is a pulse
        fp_start <= 1'b0;

        case (state)
            STATE_IDLE: begin
                result_valid <= 1'b0;
                error <= 1'b0;
                price_index <= 8'h0;
                accumulator <= 32'h0;
                fp_wait_counter <= 4'h0;
            end

            STATE_SMA_SUM: begin
                // Sum prices iteratively
                if (price_index == 8'h0) begin
                    // First price: initialize accumulator
                    accumulator <= current_price;
                    price_index <= price_index + 1'b1;
                end else if (price_index < window_size) begin
                    // Add next price using FP unit
                    fp_operation <= 2'b00;  // ADD
                    fp_operand_a <= accumulator;
                    fp_operand_b <= current_price;
                    fp_start <= 1'b1;
                    state <= STATE_WAIT_FP;
                end
            end

            STATE_WAIT_FP: begin
                // Wait for FP operation to complete
                if (fp_result_valid) begin
                    if (next_state == STATE_SMA_SUM) begin
                        // Store sum result and continue
                        accumulator <= fp_result;
                        price_index <= price_index + 1'b1;
                    end else if (next_state == STATE_DONE) begin
                        // Final result ready
                        result <= fp_result;
                        result_valid <= 1'b1;
                        error <= fp_error;
                    end
                end
            end

            STATE_SMA_DIV: begin
                // Divide sum by window_size
                // Convert window_size (uint16) to float for division
                // For now, simplified: assume window_size as float bits
                fp_operation <= 2'b11;  // DIV
                fp_operand_a <= accumulator;  // sum
                fp_operand_b <= {16'h0, window_size};  // FIXME: Need uint to float conversion
                fp_start <= 1'b1;
                state <= STATE_WAIT_FP;
            end

            STATE_DONE: begin
                result_valid <= 1'b1;
                state <= STATE_IDLE;
            end
        endcase
    end
end

// ============================================================================
// State Machine - Combinational Logic
// ============================================================================
always @(*) begin
    next_state = state;

    case (state)
        STATE_IDLE: begin
            if (start) begin
                // Check if buffer has enough data
                if (buffer_count < window_size) begin
                    // Error: insufficient data
                    next_state = STATE_DONE;  // Will set error flag
                end else begin
                    case (operation)
                        OP_SMA: begin
                            next_state = STATE_SMA_SUM;
                        end

                        OP_EMA: begin
                            // EMA: alpha × price_0 + (1-alpha) × prev_EMA
                            // Simplified implementation (needs extension)
                            next_state = STATE_DONE;
                        end

                        OP_MIN, OP_MAX: begin
                            // MIN/MAX: iterate through window finding min/max
                            next_state = STATE_DONE;  // Placeholder
                        end

                        default: begin
                            // Unsupported operation
                            next_state = STATE_DONE;
                        end
                    endcase
                end
            end
        end

        STATE_SMA_SUM: begin
            if (price_index >= window_size) begin
                // All prices summed, now divide
                next_state = STATE_SMA_DIV;
            end
            // Stay in SMA_SUM or go to WAIT_FP if FP operation started
        end

        STATE_WAIT_FP: begin
            if (fp_result_valid) begin
                if (price_index < window_size) begin
                    // More prices to sum
                    next_state = STATE_SMA_SUM;
                end else begin
                    // Division complete, done
                    next_state = STATE_DONE;
                end
            end
        end

        STATE_SMA_DIV: begin
            // Transition handled in sequential logic
        end

        STATE_DONE: begin
            next_state = STATE_IDLE;
        end

        default: begin
            next_state = STATE_IDLE;
        end
    endcase
end

endmodule
