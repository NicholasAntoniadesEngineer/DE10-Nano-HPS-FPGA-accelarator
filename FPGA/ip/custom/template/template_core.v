// ============================================================================
// Custom IP - Core Logic (TEMPLATE)
// ============================================================================
// Replace this with your actual computation logic.
// This placeholder passes input_a through as the result after 1 cycle.
// ============================================================================

module template_core (
    input  wire        clk,
    input  wire        reset_n,

    // Control
    input  wire [31:0] input_a,
    input  wire [31:0] input_b,
    input  wire [3:0]  operation,
    input  wire        start,

    // Status and Result
    output reg  [31:0] result,
    output reg         busy,
    output reg         done,
    output reg         error
);

// ============================================================================
// State Machine
// ============================================================================
localparam STATE_IDLE = 2'd0;
localparam STATE_EXEC = 2'd1;
localparam STATE_DONE = 2'd2;

reg [1:0] state;
reg [31:0] op_a, op_b;
reg [3:0]  op_code;

always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        state   <= STATE_IDLE;
        result  <= 32'h0;
        busy    <= 1'b0;
        done    <= 1'b0;
        error   <= 1'b0;
        op_a    <= 32'h0;
        op_b    <= 32'h0;
        op_code <= 4'h0;
    end else begin
        case (state)
            STATE_IDLE: begin
                done  <= 1'b0;
                error <= 1'b0;
                if (start) begin
                    op_a    <= input_a;
                    op_b    <= input_b;
                    op_code <= operation;
                    busy    <= 1'b1;
                    state   <= STATE_EXEC;
                end
            end

            STATE_EXEC: begin
                // ============================================================
                // YOUR COMPUTATION GOES HERE
                // Replace this with your actual logic (pipeline, FSM, etc.)
                // ============================================================
                result <= op_a;  // Placeholder: pass-through
                state  <= STATE_DONE;
            end

            STATE_DONE: begin
                busy  <= 1'b0;
                done  <= 1'b1;
                state <= STATE_IDLE;
            end

            default: state <= STATE_IDLE;
        endcase
    end
end

endmodule
