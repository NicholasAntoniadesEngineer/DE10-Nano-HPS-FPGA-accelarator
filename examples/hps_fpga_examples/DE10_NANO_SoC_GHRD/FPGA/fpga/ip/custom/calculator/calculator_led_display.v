// ============================================================================
// Calculator LED Display Module
// ============================================================================
// Displays the lower 8 bits of the calculator result register on LEDs
// Provides real-time visual feedback of calculation results
// ============================================================================

module calculator_led_display (
    input  wire        clk,
    input  wire        reset_n,
    input  wire [31:0] result_register,    // 32-bit float result
    input  wire        result_valid,       // Result is valid
    output reg  [7:0]  led_output          // LED[7:0] output
);

// ============================================================================
// LED Output Logic
// ============================================================================
// Display lower 8 bits of result register
// Updates immediately when result is valid

always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        led_output <= 8'h00;
    end else begin
        if (result_valid) begin
            // Display result[7:0] on LEDs
            led_output <= result_register[7:0];
        end
        // Note: LEDs maintain last valid result until new calculation completes
    end
end

endmodule
