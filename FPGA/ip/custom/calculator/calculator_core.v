// ============================================================================
// Calculator Core Module
// ============================================================================
// Main computation engine that orchestrates floating-point operations
// Manages operation state machine and pipeline control
// ============================================================================

module calculator_core (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Control Interface (from register file)
    input  wire [3:0]  operation,          // Operation code (0=ADD, 1=SUB, 2=MUL, 3=DIV)
    input  wire [31:0] operand_a,          // Operand A
    input  wire [31:0] operand_b,          // Operand B
    input  wire        start,              // Start calculation

    // Status and Result
    output reg  [31:0] result,             // Result output
    output reg         busy,               // Calculator is busy
    output reg         done,               // Operation complete (pulse)
    output reg         error,              // Error occurred (combined)

    // Individual error flags for ERROR_CODE register
    output reg         error_overflow,
    output reg         error_underflow,
    output reg         error_nan,
    output reg         error_div_zero,
    output reg         error_watchdog
);

// ============================================================================
// State Machine
// ============================================================================
localparam STATE_IDLE       = 2'b00;
localparam STATE_COMPUTING  = 2'b01;
localparam STATE_DONE       = 2'b10;

reg [1:0]   state, next_state;
reg [3:0]   cycle_counter;                 // Count cycles through pipeline
reg [3:0]   pipeline_depth;                // Pipeline depth for current operation
reg [5:0]   watchdog_counter;              // Watchdog: timeout at 32 cycles
reg         watchdog_timeout;              // Watchdog fired
localparam  WATCHDOG_LIMIT = 6'd32;

// Operation pipeline depths (cycles)
localparam PIPELINE_ADD = 4'd7;
localparam PIPELINE_SUB = 4'd7;
localparam PIPELINE_MUL = 4'd7;  // Must match float_ops start_pipe[6] depth
localparam PIPELINE_DIV = 4'd7;  // Must match float_ops start_pipe[6] depth

// ============================================================================
// Floating Point Operations Module
// ============================================================================
wire [31:0] fp_result;
wire        fp_result_valid;
wire        fp_error;
wire        fp_error_overflow;
wire        fp_error_underflow;
wire        fp_error_nan;
wire        fp_error_div_zero;

calculator_float_ops fp_ops (
    .clk             (clk),
    .reset_n         (reset_n),
    .operation       (operation[1:0]),  // Only pass lower 2 bits for basic ops
    .operand_a       (operand_a),
    .operand_b       (operand_b),
    .start           (start),
    .result          (fp_result),
    .result_valid    (fp_result_valid),
    .error           (fp_error),
    .error_overflow  (fp_error_overflow),
    .error_underflow (fp_error_underflow),
    .error_nan       (fp_error_nan),
    .error_div_zero  (fp_error_div_zero)
);

// ============================================================================
// Pipeline Depth Selection
// ============================================================================
// Determine pipeline depth based on operation
always @(*) begin
    case (operation[1:0])  // Basic operations use lower 2 bits
        2'b00:   pipeline_depth = PIPELINE_ADD;   // ADD
        2'b01:   pipeline_depth = PIPELINE_SUB;   // SUB
        2'b10:   pipeline_depth = PIPELINE_MUL;   // MUL
        2'b11:   pipeline_depth = PIPELINE_DIV;   // DIV
        default: pipeline_depth = PIPELINE_ADD;
    endcase
end

// ============================================================================
// State Machine - Sequential Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        state <= STATE_IDLE;
        cycle_counter <= 4'h0;
        watchdog_counter <= 6'd0;
        watchdog_timeout <= 1'b0;
    end else begin
        state <= next_state;

        // Cycle counter and watchdog for pipeline tracking
        if (state == STATE_COMPUTING) begin
            if (cycle_counter < pipeline_depth) begin
                cycle_counter <= cycle_counter + 1'b1;
            end
            if (watchdog_counter < WATCHDOG_LIMIT) begin
                watchdog_counter <= watchdog_counter + 1'b1;
            end else begin
                watchdog_timeout <= 1'b1;
            end
        end else begin
            cycle_counter <= 4'h0;
            watchdog_counter <= 6'd0;
            if (start && (state == STATE_IDLE))
                watchdog_timeout <= 1'b0;
        end
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
                next_state = STATE_COMPUTING;
            end
        end

        STATE_COMPUTING: begin
            // Wait for pipeline to complete or watchdog timeout
            if (cycle_counter >= pipeline_depth || watchdog_counter >= WATCHDOG_LIMIT) begin
                next_state = STATE_DONE;
            end
        end

        STATE_DONE: begin
            // Single cycle done state, then return to idle
            next_state = STATE_IDLE;
        end

        default: begin
            next_state = STATE_IDLE;
        end
    endcase
end

// ============================================================================
// Output Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        result          <= 32'h0;
        busy            <= 1'b0;
        done            <= 1'b0;
        error           <= 1'b0;
        error_overflow  <= 1'b0;
        error_underflow <= 1'b0;
        error_nan       <= 1'b0;
        error_div_zero  <= 1'b0;
        error_watchdog  <= 1'b0;
    end else begin
        // Busy signal
        busy <= (state == STATE_COMPUTING);

        // Done signal (pulse for one cycle)
        done <= (state == STATE_DONE);

        // Capture result and error flags when floating point operation completes
        if (fp_result_valid) begin
            result          <= fp_result;
            error           <= fp_error;
            error_overflow  <= fp_error_overflow;
            error_underflow <= fp_error_underflow;
            error_nan       <= fp_error_nan;
            error_div_zero  <= fp_error_div_zero;
        end

        // Watchdog timeout sets error
        if (watchdog_timeout && (state == STATE_COMPUTING)) begin
            error          <= 1'b1;
            error_watchdog <= 1'b1;
        end

        // Clear errors on new operation
        if (start && (state == STATE_IDLE)) begin
            error           <= 1'b0;
            error_overflow  <= 1'b0;
            error_underflow <= 1'b0;
            error_nan       <= 1'b0;
            error_div_zero  <= 1'b0;
            error_watchdog  <= 1'b0;
        end
    end
end

endmodule
