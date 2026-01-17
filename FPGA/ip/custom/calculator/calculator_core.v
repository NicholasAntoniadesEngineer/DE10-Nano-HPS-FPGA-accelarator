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
    input  wire [3:0]  operation,          // Operation code (0-3=basic, 4-15=HFT)
    input  wire [31:0] operand_a,          // Operand A
    input  wire [31:0] operand_b,          // Operand B
    input  wire        start,              // Start calculation

    // Status and Result
    output reg  [31:0] result,             // Result output
    output reg         busy,               // Calculator is busy
    output reg         done,               // Operation complete (pulse)
    output reg         error               // Error occurred
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

// Operation pipeline depths (cycles)
localparam PIPELINE_ADD = 4'd7;
localparam PIPELINE_SUB = 4'd7;
localparam PIPELINE_MUL = 4'd5;
localparam PIPELINE_DIV = 4'd6;

// ============================================================================
// Floating Point Operations Module
// ============================================================================
wire [31:0] fp_result;
wire        fp_result_valid;
wire        fp_error;

calculator_float_ops fp_ops (
    .clk           (clk),
    .reset_n       (reset_n),
    .operation     (operation[1:0]),  // Only pass lower 2 bits for basic ops
    .operand_a     (operand_a),
    .operand_b     (operand_b),
    .start         (start),
    .result        (fp_result),
    .result_valid  (fp_result_valid),
    .error         (fp_error)
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
    // Note: HFT operations (4-15) will use separate pipeline tracking
end

// ============================================================================
// State Machine - Sequential Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        state <= STATE_IDLE;
        cycle_counter <= 4'h0;
    end else begin
        state <= next_state;

        // Cycle counter for pipeline tracking
        if (state == STATE_COMPUTING) begin
            if (cycle_counter < pipeline_depth) begin
                cycle_counter <= cycle_counter + 1'b1;
            end
        end else begin
            cycle_counter <= 4'h0;
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
            // Wait for pipeline to complete
            if (cycle_counter >= pipeline_depth) begin
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
        result <= 32'h0;
        busy   <= 1'b0;
        done   <= 1'b0;
        error  <= 1'b0;
    end else begin
        // Busy signal
        busy <= (state == STATE_COMPUTING);

        // Done signal (pulse for one cycle)
        done <= (state == STATE_DONE);

        // Capture result when floating point operation completes
        if (fp_result_valid) begin
            result <= fp_result;
            error  <= fp_error;
        end

        // Clear error on new operation
        if (start && (state == STATE_IDLE)) begin
            error <= 1'b0;
        end
    end
end

endmodule
