// ============================================================================
// Calculator Floating Point Operations Module
// ============================================================================
// Implements IEEE 754 single-precision floating point operations
// Uses Intel/Altera ALTFP_* megafunctions for optimized performance
// ============================================================================

module calculator_float_ops (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Operation Control
    input  wire [1:0]  operation,          // 00=ADD, 01=SUB, 10=MUL, 11=DIV
    input  wire [31:0] operand_a,          // IEEE 754 single precision
    input  wire [31:0] operand_b,          // IEEE 754 single precision
    input  wire        start,              // Start operation (pulse)

    // Result
    output reg  [31:0] result,             // IEEE 754 single precision result
    output reg         result_valid,       // Result is valid
    output reg         error,              // Error flag (combined)

    // Individual error flags
    output reg         error_overflow,
    output reg         error_underflow,
    output reg         error_nan,
    output reg         error_div_zero
);

// ============================================================================
// Operation Codes
// ============================================================================
localparam OP_ADD = 2'b00;
localparam OP_SUB = 2'b01;
localparam OP_MUL = 2'b10;
localparam OP_DIV = 2'b11;

// ============================================================================
// Internal Signals for ALTFP Outputs
// ============================================================================
wire [31:0] add_result, sub_result, mul_result, div_result;
wire        add_overflow, sub_overflow, mul_overflow, div_overflow;
wire        add_underflow, sub_underflow, mul_underflow, div_underflow;
wire        add_nan, sub_nan, mul_nan, div_nan;
wire        add_valid, sub_valid, mul_valid, div_valid;
wire        div_zero;  // Division by zero flag from ALTFP divider

// Pipeline delay tracking
reg [2:0]   operation_pipe [0:6];          // Pipeline for operation tracking
reg         start_pipe [0:6];              // Pipeline for valid signal

// ============================================================================
// Intel ALTFP Add/Subtract Megafunction
// ============================================================================
// Configured for single precision, pipeline depth = 7
altfp_add_sub32 altfp_adder (
    .clock      (clk),
    .dataa      (operand_a),
    .datab      (operand_b),
    .add_sub    (1'b1),                    // 1=add, 0=subtract
    .result     (add_result),
    .overflow   (add_overflow),
    .underflow  (add_underflow),
    .nan        (add_nan)
);

altfp_add_sub32 altfp_subtractor (
    .clock      (clk),
    .dataa      (operand_a),
    .datab      (operand_b),
    .add_sub    (1'b0),                    // 1=add, 0=subtract
    .result     (sub_result),
    .overflow   (sub_overflow),
    .underflow  (sub_underflow),
    .nan        (sub_nan)
);

// ============================================================================
// Intel ALTFP Multiply Megafunction
// ============================================================================
// Configured for single precision, pipeline depth = 5
altfp_mult32 altfp_multiplier (
    .clock      (clk),
    .dataa      (operand_a),
    .datab      (operand_b),
    .result     (mul_result),
    .overflow   (mul_overflow),
    .underflow  (mul_underflow),
    .nan        (mul_nan)
);

// ============================================================================
// Intel ALTFP Divide Megafunction
// ============================================================================
// Configured for single precision, pipeline depth = 6
altfp_div32 altfp_divider (
    .clock      (clk),
    .dataa      (operand_a),
    .datab      (operand_b),
    .result     (div_result),
    .overflow   (div_overflow),
    .underflow  (div_underflow),
    .nan        (div_nan),
    .division_by_zero (div_zero)
);

// ============================================================================
// Pipeline for Operation Tracking
// ============================================================================
// Track which operation is in the pipeline
integer i;
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        for (i = 0; i < 7; i = i + 1) begin
            operation_pipe[i] <= 2'b00;
            start_pipe[i] <= 1'b0;
        end
    end else begin
        // Shift pipeline
        operation_pipe[0] <= operation;
        start_pipe[0] <= start;

        for (i = 1; i < 7; i = i + 1) begin
            operation_pipe[i] <= operation_pipe[i-1];
            start_pipe[i] <= start_pipe[i-1];
        end
    end
end

// ============================================================================
// Result Multiplexer
// ============================================================================
// Select result based on operation at end of pipeline
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        result <= 32'h0;
        result_valid <= 1'b0;
        error <= 1'b0;
        error_overflow <= 1'b0;
        error_underflow <= 1'b0;
        error_nan <= 1'b0;
        error_div_zero <= 1'b0;
    end else begin
        // Check if valid data is at end of pipeline
        if (start_pipe[6]) begin
            result_valid <= 1'b1;
            error_div_zero <= 1'b0;

            case (operation_pipe[6])
                OP_ADD: begin
                    result          <= add_result;
                    error           <= add_overflow | add_underflow | add_nan;
                    error_overflow  <= add_overflow;
                    error_underflow <= add_underflow;
                    error_nan       <= add_nan;
                end

                OP_SUB: begin
                    result          <= sub_result;
                    error           <= sub_overflow | sub_underflow | sub_nan;
                    error_overflow  <= sub_overflow;
                    error_underflow <= sub_underflow;
                    error_nan       <= sub_nan;
                end

                OP_MUL: begin
                    result          <= mul_result;
                    error           <= mul_overflow | mul_underflow | mul_nan;
                    error_overflow  <= mul_overflow;
                    error_underflow <= mul_underflow;
                    error_nan       <= mul_nan;
                end

                OP_DIV: begin
                    result          <= div_result;
                    error           <= div_overflow | div_underflow | div_nan | div_zero;
                    error_overflow  <= div_overflow;
                    error_underflow <= div_underflow;
                    error_nan       <= div_nan;
                    error_div_zero  <= div_zero;
                end

                default: begin
                    result          <= 32'h0;
                    error           <= 1'b1;
                    error_overflow  <= 1'b0;
                    error_underflow <= 1'b0;
                    error_nan       <= 1'b0;
                end
            endcase
        end else begin
            result_valid    <= 1'b0;
            error           <= 1'b0;
            error_overflow  <= 1'b0;
            error_underflow <= 1'b0;
            error_nan       <= 1'b0;
            error_div_zero  <= 1'b0;
        end
    end
end

endmodule

// ============================================================================
// IEEE 754 Single-Precision Floating-Point Modules
// ============================================================================
// Pure RTL implementations replacing Intel ALTFP megafunction stubs.
// Fully synthesizable on Cyclone V without IP Catalog dependencies.
// ============================================================================

// ============================================================================
// FP Add/Subtract — 7-cycle pipeline
// ============================================================================
module altfp_add_sub32 (
    input  wire        clock,
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    input  wire        add_sub,            // 1=add, 0=sub
    output reg  [31:0] result,
    output reg         overflow,
    output reg         underflow,
    output reg         nan
);

// Stage 1: Extract fields and determine effective operation
reg        s1_sign_a, s1_sign_b;
reg [7:0]  s1_exp_a, s1_exp_b;
reg [23:0] s1_mant_a, s1_mant_b;   // {implicit_1, mantissa[22:0]}
reg        s1_a_is_nan, s1_b_is_nan, s1_a_is_inf, s1_b_is_inf;
reg        s1_a_is_zero, s1_b_is_zero;
reg        s1_eff_sub;              // Effective subtraction flag
reg        s1_valid;

always @(posedge clock) begin
    s1_sign_a    <= dataa[31];
    s1_sign_b    <= add_sub ? datab[31] : ~datab[31]; // Flip sign for subtract
    s1_exp_a     <= dataa[30:23];
    s1_exp_b     <= datab[30:23];
    s1_mant_a    <= (dataa[30:23] == 8'd0) ? {1'b0, dataa[22:0]} : {1'b1, dataa[22:0]};
    s1_mant_b    <= (datab[30:23] == 8'd0) ? {1'b0, datab[22:0]} : {1'b1, datab[22:0]};
    s1_a_is_nan  <= (dataa[30:23] == 8'hFF) && (dataa[22:0] != 23'd0);
    s1_b_is_nan  <= (datab[30:23] == 8'hFF) && (datab[22:0] != 23'd0);
    s1_a_is_inf  <= (dataa[30:23] == 8'hFF) && (dataa[22:0] == 23'd0);
    s1_b_is_inf  <= (datab[30:23] == 8'hFF) && (datab[22:0] == 23'd0);
    s1_a_is_zero <= (dataa[30:23] == 8'd0) && (dataa[22:0] == 23'd0);
    s1_b_is_zero <= (datab[30:23] == 8'd0) && (datab[22:0] == 23'd0);
    s1_eff_sub   <= dataa[31] ^ (add_sub ? datab[31] : ~datab[31]);
    s1_valid     <= 1'b1;
end

// Stage 2: Compare exponents, determine shift amount and swap if needed
reg        s2_sign_a, s2_sign_b;
reg [7:0]  s2_exp_large;
reg [23:0] s2_mant_large, s2_mant_small;
reg [7:0]  s2_shift_amount;
reg        s2_a_is_nan, s2_b_is_nan, s2_a_is_inf, s2_b_is_inf;
reg        s2_a_is_zero, s2_b_is_zero, s2_eff_sub;
reg        s2_sign_large;
reg        s2_valid;

always @(posedge clock) begin
    s2_a_is_nan  <= s1_a_is_nan;
    s2_b_is_nan  <= s1_b_is_nan;
    s2_a_is_inf  <= s1_a_is_inf;
    s2_b_is_inf  <= s1_b_is_inf;
    s2_a_is_zero <= s1_a_is_zero;
    s2_b_is_zero <= s1_b_is_zero;
    s2_eff_sub   <= s1_eff_sub;
    s2_valid     <= s1_valid;

    if (s1_exp_a >= s1_exp_b) begin
        s2_exp_large    <= s1_exp_a;
        s2_mant_large   <= s1_mant_a;
        s2_mant_small   <= s1_mant_b;
        s2_shift_amount <= s1_exp_a - s1_exp_b;
        s2_sign_large   <= s1_sign_a;
        s2_sign_a       <= s1_sign_a;
        s2_sign_b       <= s1_sign_b;
    end else begin
        s2_exp_large    <= s1_exp_b;
        s2_mant_large   <= s1_mant_b;
        s2_mant_small   <= s1_mant_a;
        s2_shift_amount <= s1_exp_b - s1_exp_a;
        s2_sign_large   <= s1_sign_b;
        s2_sign_a       <= s1_sign_a;
        s2_sign_b       <= s1_sign_b;
    end
end

// Stage 3: Align mantissas (shift smaller mantissa right)
reg        s3_sign_large;
reg [7:0]  s3_exp_large;
reg [24:0] s3_mant_large, s3_mant_small; // Extra bit for carry
reg        s3_a_is_nan, s3_b_is_nan, s3_a_is_inf, s3_b_is_inf;
reg        s3_a_is_zero, s3_b_is_zero, s3_eff_sub;
reg        s3_valid;

always @(posedge clock) begin
    s3_sign_large <= s2_sign_large;
    s3_exp_large  <= s2_exp_large;
    s3_mant_large <= {1'b0, s2_mant_large};
    s3_mant_small <= (s2_shift_amount > 8'd24) ? 25'd0 : ({1'b0, s2_mant_small} >> s2_shift_amount);
    s3_a_is_nan   <= s2_a_is_nan;
    s3_b_is_nan   <= s2_b_is_nan;
    s3_a_is_inf   <= s2_a_is_inf;
    s3_b_is_inf   <= s2_b_is_inf;
    s3_a_is_zero  <= s2_a_is_zero;
    s3_b_is_zero  <= s2_b_is_zero;
    s3_eff_sub    <= s2_eff_sub;
    s3_valid      <= s2_valid;
end

// Stage 4: Add or subtract mantissas
reg        s4_sign;
reg [7:0]  s4_exp;
reg [24:0] s4_mant_sum;
reg        s4_a_is_nan, s4_b_is_nan, s4_a_is_inf, s4_b_is_inf;
reg        s4_a_is_zero, s4_b_is_zero;
reg        s4_valid;

always @(posedge clock) begin
    s4_exp       <= s3_exp_large;
    s4_sign      <= s3_sign_large;
    s4_a_is_nan  <= s3_a_is_nan;
    s4_b_is_nan  <= s3_b_is_nan;
    s4_a_is_inf  <= s3_a_is_inf;
    s4_b_is_inf  <= s3_b_is_inf;
    s4_a_is_zero <= s3_a_is_zero;
    s4_b_is_zero <= s3_b_is_zero;
    s4_valid     <= s3_valid;

    if (s3_eff_sub) begin
        if (s3_mant_large >= s3_mant_small) begin
            s4_mant_sum <= s3_mant_large - s3_mant_small;
            s4_sign     <= s3_sign_large;
        end else begin
            s4_mant_sum <= s3_mant_small - s3_mant_large;
            s4_sign     <= ~s3_sign_large;
        end
    end else begin
        s4_mant_sum <= s3_mant_large + s3_mant_small;
    end
end

// Stage 5: Count leading zeros for normalization
reg        s5_sign;
reg [7:0]  s5_exp;
reg [24:0] s5_mant;
reg [4:0]  s5_lzc;  // Leading zero count
reg        s5_a_is_nan, s5_b_is_nan, s5_a_is_inf, s5_b_is_inf;
reg        s5_a_is_zero, s5_b_is_zero;
reg        s5_valid;

// Leading zero counter function
// Iterate low-to-high so the HIGHEST set bit overwrites last,
// giving the correct count of leading zeros from bit 24.
function [4:0] count_leading_zeros;
    input [24:0] val;
    integer k;
    begin
        count_leading_zeros = 5'd25;
        for (k = 0; k <= 24; k = k + 1) begin
            if (val[k])
                count_leading_zeros = 5'd24 - k[4:0];
        end
    end
endfunction

always @(posedge clock) begin
    s5_sign      <= s4_sign;
    s5_exp       <= s4_exp;
    s5_mant      <= s4_mant_sum;
    s5_lzc       <= count_leading_zeros(s4_mant_sum);
    s5_a_is_nan  <= s4_a_is_nan;
    s5_b_is_nan  <= s4_b_is_nan;
    s5_a_is_inf  <= s4_a_is_inf;
    s5_b_is_inf  <= s4_b_is_inf;
    s5_a_is_zero <= s4_a_is_zero;
    s5_b_is_zero <= s4_b_is_zero;
    s5_valid     <= s4_valid;
end

// Stage 6: Normalize and round
reg        s6_sign;
reg [7:0]  s6_exp;
reg [22:0] s6_mant;
reg        s6_overflow, s6_underflow, s6_nan;
reg        s6_valid;

always @(posedge clock) begin
    s6_valid     <= s5_valid;
    s6_overflow  <= 1'b0;
    s6_underflow <= 1'b0;
    s6_nan       <= 1'b0;
    s6_sign      <= s5_sign;
    s6_exp       <= 8'd0;
    s6_mant      <= 23'd0;

    if (s5_a_is_nan || s5_b_is_nan) begin
        // NaN input -> NaN output
        s6_sign <= 1'b0;
        s6_exp  <= 8'hFF;
        s6_mant <= 23'h400000; // Quiet NaN
        s6_nan  <= 1'b1;
    end else if (s5_a_is_inf && s5_b_is_inf) begin
        // Inf + Inf = Inf, Inf - Inf = NaN
        if (s5_mant == 25'd0 && s5_lzc == 5'd25) begin
            // Inf - Inf case (subtraction resulted in zero mant but both were inf)
            s6_sign <= 1'b0;
            s6_exp  <= 8'hFF;
            s6_mant <= 23'h400000;
            s6_nan  <= 1'b1;
        end else begin
            s6_exp  <= 8'hFF;
            s6_mant <= 23'd0;
        end
    end else if (s5_a_is_inf || s5_b_is_inf) begin
        // Inf + finite = Inf
        s6_exp  <= 8'hFF;
        s6_mant <= 23'd0;
    end else if (s5_mant == 25'd0) begin
        // Zero result
        s6_sign <= 1'b0;
        s6_exp  <= 8'd0;
        s6_mant <= 23'd0;
    end else if (s5_mant[24]) begin
        // Carry out: shift right 1, increment exponent
        s6_exp  <= s5_exp + 8'd1;
        s6_mant <= s5_mant[23:1]; // Shift right, truncate
        if (s5_exp >= 8'd254) begin
            s6_exp      <= 8'hFF;
            s6_mant     <= 23'd0;
            s6_overflow <= 1'b1;
        end
    end else begin
        // Normalize by shifting left.
        // s5_mant is 25 bits: [24]=carry (always 0 here), [23]=implicit 1 if normalized.
        // lzc==1 means bit 23 is the leading 1 — already normalized, no shift needed.
        // lzc>1 means actual leading zeros — shift left by (lzc-1) to bring implicit
        //       1 to bit 23, and decrement exponent by the same amount.
        if (s5_lzc == 5'd1) begin
            // Already normalized: implicit 1 at bit 23, exponent unchanged.
            s6_exp  <= s5_exp;
            s6_mant <= s5_mant[22:0];
        end else if (s5_lzc > 5'd1 && (s5_lzc - 5'd1) <= {3'd0, s5_exp} && s5_lzc < 5'd25) begin
            // Shift left by (lzc-1) to normalize, adjust exponent accordingly.
            s6_exp  <= s5_exp - {3'd0, s5_lzc - 5'd1};
            s6_mant <= s5_mant << (s5_lzc - 5'd1); // Implicit 1 at bit 23 is truncated by [22:0] assignment
        end else if (s5_exp > 8'd0) begin
            // Would underflow; return denormal.
            s6_exp  <= 8'd0;
            s6_mant <= s5_mant[22:0];
            s6_underflow <= 1'b1;
        end else begin
            // Denormalized result.
            s6_exp  <= 8'd0;
            s6_mant <= s5_mant[22:0];
        end
    end
end

// Stage 7: Pack result
always @(posedge clock) begin
    result   <= {s6_sign, s6_exp, s6_mant};
    overflow  <= s6_overflow;
    underflow <= s6_underflow;
    nan       <= s6_nan;
end

endmodule

// ============================================================================
// FP Multiply — 5-cycle pipeline
// ============================================================================
module altfp_mult32 (
    input  wire        clock,
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    output reg  [31:0] result,
    output reg         overflow,
    output reg         underflow,
    output reg         nan
);

// Stage 1: Extract fields, detect special cases
reg        s1_sign;
reg [7:0]  s1_exp_a, s1_exp_b;
reg [23:0] s1_mant_a, s1_mant_b;
reg        s1_a_is_nan, s1_b_is_nan, s1_a_is_inf, s1_b_is_inf;
reg        s1_a_is_zero, s1_b_is_zero;

always @(posedge clock) begin
    s1_sign      <= dataa[31] ^ datab[31];
    s1_exp_a     <= dataa[30:23];
    s1_exp_b     <= datab[30:23];
    s1_mant_a    <= (dataa[30:23] == 8'd0) ? {1'b0, dataa[22:0]} : {1'b1, dataa[22:0]};
    s1_mant_b    <= (datab[30:23] == 8'd0) ? {1'b0, datab[22:0]} : {1'b1, datab[22:0]};
    s1_a_is_nan  <= (dataa[30:23] == 8'hFF) && (dataa[22:0] != 23'd0);
    s1_b_is_nan  <= (datab[30:23] == 8'hFF) && (datab[22:0] != 23'd0);
    s1_a_is_inf  <= (dataa[30:23] == 8'hFF) && (dataa[22:0] == 23'd0);
    s1_b_is_inf  <= (datab[30:23] == 8'hFF) && (datab[22:0] == 23'd0);
    s1_a_is_zero <= (dataa[30:23] == 8'd0) && (dataa[22:0] == 23'd0);
    s1_b_is_zero <= (datab[30:23] == 8'd0) && (datab[22:0] == 23'd0);
end

// Stage 2: Multiply mantissas (24x24 -> 48 bits) and compute exponent
reg        s2_sign;
reg [8:0]  s2_exp_sum;  // 9 bits to detect overflow
reg [47:0] s2_mant_product;
reg        s2_a_is_nan, s2_b_is_nan, s2_a_is_inf, s2_b_is_inf;
reg        s2_a_is_zero, s2_b_is_zero;

always @(posedge clock) begin
    s2_sign         <= s1_sign;
    s2_exp_sum      <= {1'b0, s1_exp_a} + {1'b0, s1_exp_b} - 9'd127; // Subtract bias
    s2_mant_product <= s1_mant_a * s1_mant_b;
    s2_a_is_nan     <= s1_a_is_nan;
    s2_b_is_nan     <= s1_b_is_nan;
    s2_a_is_inf     <= s1_a_is_inf;
    s2_b_is_inf     <= s1_b_is_inf;
    s2_a_is_zero    <= s1_a_is_zero;
    s2_b_is_zero    <= s1_b_is_zero;
end

// Stage 3: Normalize product
reg        s3_sign;
reg [8:0]  s3_exp;
reg [22:0] s3_mant;
reg        s3_overflow, s3_underflow, s3_nan;

always @(posedge clock) begin
    s3_sign      <= s2_sign;
    s3_overflow  <= 1'b0;
    s3_underflow <= 1'b0;
    s3_nan       <= 1'b0;
    s3_exp       <= 9'd0;
    s3_mant      <= 23'd0;

    if (s2_a_is_nan || s2_b_is_nan) begin
        s3_sign <= 1'b0;
        s3_exp  <= 9'd255;
        s3_mant <= 23'h400000;
        s3_nan  <= 1'b1;
    end else if ((s2_a_is_inf && s2_b_is_zero) || (s2_b_is_inf && s2_a_is_zero)) begin
        // 0 * Inf = NaN
        s3_sign <= 1'b0;
        s3_exp  <= 9'd255;
        s3_mant <= 23'h400000;
        s3_nan  <= 1'b1;
    end else if (s2_a_is_inf || s2_b_is_inf) begin
        s3_exp  <= 9'd255;
        s3_mant <= 23'd0;
    end else if (s2_a_is_zero || s2_b_is_zero) begin
        s3_exp  <= 9'd0;
        s3_mant <= 23'd0;
    end else if (s2_mant_product[47]) begin
        // Product >= 2.0, shift right, increment exponent
        s3_exp  <= s2_exp_sum + 9'd1;
        s3_mant <= s2_mant_product[46:24]; // Take top bits after leading 1
        if (s2_exp_sum >= 9'd254) begin
            s3_exp      <= 9'd255;
            s3_mant     <= 23'd0;
            s3_overflow <= 1'b1;
        end
    end else begin
        // Product in [1.0, 2.0)
        s3_exp  <= s2_exp_sum;
        s3_mant <= s2_mant_product[45:23]; // After implicit 1
        if (s2_exp_sum[8]) begin
            // Underflow (negative exponent after bias subtraction)
            s3_exp       <= 9'd0;
            s3_mant      <= 23'd0;
            s3_underflow <= 1'b1;
        end else if (s2_exp_sum >= 9'd255) begin
            s3_exp      <= 9'd255;
            s3_mant     <= 23'd0;
            s3_overflow <= 1'b1;
        end
    end
end

// Stage 4: Pack result
reg [31:0] s4_result;
reg        s4_overflow, s4_underflow, s4_nan;

always @(posedge clock) begin
    s4_result    <= {s3_sign, s3_exp[7:0], s3_mant};
    s4_overflow  <= s3_overflow;
    s4_underflow <= s3_underflow;
    s4_nan       <= s3_nan;
end

// Stage 5: Output
always @(posedge clock) begin
    result    <= s4_result;
    overflow  <= s4_overflow;
    underflow <= s4_underflow;
    nan       <= s4_nan;
end

endmodule

// ============================================================================
// FP Divide — 6-cycle pipeline
// ============================================================================
module altfp_div32 (
    input  wire        clock,
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    output reg  [31:0] result,
    output reg         overflow,
    output reg         underflow,
    output reg         nan,
    output reg         division_by_zero
);

// Stage 1: Extract fields, detect special cases
reg        s1_sign;
reg [7:0]  s1_exp_a, s1_exp_b;
reg [23:0] s1_mant_a, s1_mant_b;
reg        s1_a_is_nan, s1_b_is_nan, s1_a_is_inf, s1_b_is_inf;
reg        s1_a_is_zero, s1_b_is_zero;

always @(posedge clock) begin
    s1_sign      <= dataa[31] ^ datab[31];
    s1_exp_a     <= dataa[30:23];
    s1_exp_b     <= datab[30:23];
    s1_mant_a    <= (dataa[30:23] == 8'd0) ? {1'b0, dataa[22:0]} : {1'b1, dataa[22:0]};
    s1_mant_b    <= (datab[30:23] == 8'd0) ? {1'b0, datab[22:0]} : {1'b1, datab[22:0]};
    s1_a_is_nan  <= (dataa[30:23] == 8'hFF) && (dataa[22:0] != 23'd0);
    s1_b_is_nan  <= (datab[30:23] == 8'hFF) && (datab[22:0] != 23'd0);
    s1_a_is_inf  <= (dataa[30:23] == 8'hFF) && (dataa[22:0] == 23'd0);
    s1_b_is_inf  <= (datab[30:23] == 8'hFF) && (datab[22:0] == 23'd0);
    s1_a_is_zero <= (dataa[30:23] == 8'd0) && (dataa[22:0] == 23'd0);
    s1_b_is_zero <= (datab[30:23] == 8'd0) && (datab[22:0] == 23'd0);
end

// Stage 2: Divide mantissas (24-bit / 24-bit -> quotient with guard bits)
// Use extended numerator for precision: {mant_a, 24'b0} / mant_b
reg        s2_sign;
reg signed [9:0] s2_exp_diff;
reg [47:0] s2_quotient;
reg        s2_a_is_nan, s2_b_is_nan, s2_a_is_inf, s2_b_is_inf;
reg        s2_a_is_zero, s2_b_is_zero;

always @(posedge clock) begin
    s2_sign      <= s1_sign;
    s2_exp_diff  <= {2'b00, s1_exp_a} - {2'b00, s1_exp_b} + 10'sd127; // Add bias
    s2_quotient  <= (s1_mant_b != 24'd0) ? ({s1_mant_a, 24'd0} / {24'd0, s1_mant_b}) : 48'd0;
    s2_a_is_nan  <= s1_a_is_nan;
    s2_b_is_nan  <= s1_b_is_nan;
    s2_a_is_inf  <= s1_a_is_inf;
    s2_b_is_inf  <= s1_b_is_inf;
    s2_a_is_zero <= s1_a_is_zero;
    s2_b_is_zero <= s1_b_is_zero;
end

// Stage 3: Normalize quotient
reg        s3_sign;
reg [8:0]  s3_exp;
reg [22:0] s3_mant;
reg        s3_overflow, s3_underflow, s3_nan, s3_divzero;

// Leading zero counter for 48-bit value
// Iterate low-to-high so the HIGHEST set bit overwrites last.
function [5:0] clz48;
    input [47:0] val;
    integer k;
    begin
        clz48 = 6'd48;
        for (k = 0; k <= 47; k = k + 1) begin
            if (val[k])
                clz48 = 6'd47 - k[5:0];
        end
    end
endfunction

always @(posedge clock) begin
    s3_sign      <= s2_sign;
    s3_overflow  <= 1'b0;
    s3_underflow <= 1'b0;
    s3_nan       <= 1'b0;
    s3_divzero   <= 1'b0;
    s3_exp       <= 9'd0;
    s3_mant      <= 23'd0;

    if (s2_a_is_nan || s2_b_is_nan) begin
        s3_sign <= 1'b0;
        s3_exp  <= 9'd255;
        s3_mant <= 23'h400000;
        s3_nan  <= 1'b1;
    end else if (s2_a_is_inf && s2_b_is_inf) begin
        // Inf / Inf = NaN
        s3_sign <= 1'b0;
        s3_exp  <= 9'd255;
        s3_mant <= 23'h400000;
        s3_nan  <= 1'b1;
    end else if (s2_a_is_zero && s2_b_is_zero) begin
        // 0 / 0 = NaN
        s3_sign <= 1'b0;
        s3_exp  <= 9'd255;
        s3_mant <= 23'h400000;
        s3_nan  <= 1'b1;
    end else if (s2_b_is_zero) begin
        // x / 0 = Inf
        s3_exp     <= 9'd255;
        s3_mant    <= 23'd0;
        s3_divzero <= 1'b1;
    end else if (s2_a_is_zero || s2_b_is_inf) begin
        // 0 / x = 0 or x / Inf = 0
        s3_exp  <= 9'd0;
        s3_mant <= 23'd0;
    end else if (s2_a_is_inf) begin
        // Inf / x = Inf
        s3_exp  <= 9'd255;
        s3_mant <= 23'd0;
    end else if (s2_quotient == 48'd0) begin
        s3_exp  <= 9'd0;
        s3_mant <= 23'd0;
    end else begin
        // Normalize: quotient has implicit 1 somewhere in the 48 bits
        // The quotient of {mant_a,24'b0}/mant_b will have leading 1 near bit 24
        if (s2_quotient[24]) begin
            // Normal case: leading 1 at bit 24
            s3_exp  <= s2_exp_diff[8:0];
            s3_mant <= s2_quotient[23:1]; // Round toward zero
        end else if (s2_quotient[23]) begin
            // Shifted by 1: adjust exponent
            s3_exp  <= s2_exp_diff[8:0] - 9'd1;
            s3_mant <= s2_quotient[22:0];
        end else begin
            // Need to find leading 1 and normalize
            // Use a simplified approach for remaining cases
            s3_exp  <= s2_exp_diff[8:0] - 9'd1;
            s3_mant <= s2_quotient[22:0];
        end

        // Check for overflow/underflow
        if (s2_exp_diff > 10'sd254) begin
            s3_exp      <= 9'd255;
            s3_mant     <= 23'd0;
            s3_overflow <= 1'b1;
        end else if (s2_exp_diff < 10'sd1) begin
            s3_exp       <= 9'd0;
            s3_mant      <= 23'd0;
            s3_underflow <= 1'b1;
        end
    end
end

// Stage 4: Pack result
reg [31:0] s4_result;
reg        s4_overflow, s4_underflow, s4_nan, s4_divzero;

always @(posedge clock) begin
    s4_result    <= {s3_sign, s3_exp[7:0], s3_mant};
    s4_overflow  <= s3_overflow;
    s4_underflow <= s3_underflow;
    s4_nan       <= s3_nan;
    s4_divzero   <= s3_divzero;
end

// Stage 5: Pipeline delay
reg [31:0] s5_result;
reg        s5_overflow, s5_underflow, s5_nan, s5_divzero;

always @(posedge clock) begin
    s5_result    <= s4_result;
    s5_overflow  <= s4_overflow;
    s5_underflow <= s4_underflow;
    s5_nan       <= s4_nan;
    s5_divzero   <= s4_divzero;
end

// Stage 6: Output
always @(posedge clock) begin
    result           <= s5_result;
    overflow         <= s5_overflow;
    underflow        <= s5_underflow;
    nan              <= s5_nan;
    division_by_zero <= s5_divzero;
end

endmodule
