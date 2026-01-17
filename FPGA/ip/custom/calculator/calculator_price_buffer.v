// ============================================================================
// Calculator Price Buffer Module
// ============================================================================
// Circular buffer for storing price history for HFT calculations
// Implemented using on-chip M10K RAM blocks
// ============================================================================

module calculator_price_buffer (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Write Interface
    input  wire [31:0] price_in,           // New price to add
    input  wire        write_enable,        // Write pulse
    input  wire        buffer_reset,        // Clear buffer

    // Configuration
    input  wire [15:0] window_size,         // Configurable window (1-256)

    // Read Interface (entire buffer output)
    output wire [31:0] price_out_0,         // Price[0] - most recent
    output wire [31:0] price_out_1,         // Price[1]
    output wire [31:0] price_out_2,         // Price[2]
    output wire [31:0] price_out_3,         // Price[3]
    output wire [31:0] price_out_4,         // Price[4]
    output wire [31:0] price_out_5,         // Price[5]
    output wire [31:0] price_out_6,         // Price[6]
    output wire [31:0] price_out_7,         // Price[7]
    output wire [31:0] price_out_8,         // Price[8]
    output wire [31:0] price_out_9,         // Price[9]
    output wire [31:0] price_out_10,        // Price[10]
    output wire [31:0] price_out_11,        // Price[11]
    output wire [31:0] price_out_12,        // Price[12]
    output wire [31:0] price_out_13,        // Price[13]
    output wire [31:0] price_out_14,        // Price[14]
    output wire [31:0] price_out_15,        // Price[15]
    output wire [31:0] price_out_16,        // Price[16]
    output wire [31:0] price_out_17,        // Price[17]
    output wire [31:0] price_out_18,        // Price[18]
    output wire [31:0] price_out_19,        // Price[19]
    output wire [31:0] price_out_20,        // Price[20] - for SMA(20)
    // ... extend up to 255 if needed for larger windows

    // Status
    output reg  [15:0] count,               // Current fill count
    output reg         buffer_full          // Buffer filled to window_size
);

// ============================================================================
// RAM Storage
// ============================================================================
// Using register array for prices (will be inferred as M10K RAM by Quartus)
// Supporting up to 256 prices (8-bit address)
reg [31:0] price_ram [0:255];

// Write pointer (circular)
reg [7:0] write_ptr;

// ============================================================================
// Buffer Management Logic
// ============================================================================
always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        write_ptr <= 8'h0;
        count <= 16'h0;
        buffer_full <= 1'b0;
    end else begin
        if (buffer_reset) begin
            // Reset buffer
            write_ptr <= 8'h0;
            count <= 16'h0;
            buffer_full <= 1'b0;
        end else if (write_enable) begin
            // Write new price to buffer
            price_ram[write_ptr] <= price_in;

            // Increment write pointer (circular)
            write_ptr <= write_ptr + 1'b1;

            // Update count (saturate at window_size)
            if (count < window_size) begin
                count <= count + 1'b1;
            end

            // Update buffer_full flag
            if (count >= (window_size - 1)) begin
                buffer_full <= 1'b1;
            end
        end
    end
end

// ============================================================================
// Read Interface - Output Recent Prices
// ============================================================================
// Output the most recent N prices in circular buffer order
// price_out_0 is always the most recent, price_out_1 is second most recent, etc.

assign price_out_0  = price_ram[(write_ptr - 1) & 8'hFF];  // Most recent
assign price_out_1  = price_ram[(write_ptr - 2) & 8'hFF];
assign price_out_2  = price_ram[(write_ptr - 3) & 8'hFF];
assign price_out_3  = price_ram[(write_ptr - 4) & 8'hFF];
assign price_out_4  = price_ram[(write_ptr - 5) & 8'hFF];
assign price_out_5  = price_ram[(write_ptr - 6) & 8'hFF];
assign price_out_6  = price_ram[(write_ptr - 7) & 8'hFF];
assign price_out_7  = price_ram[(write_ptr - 8) & 8'hFF];
assign price_out_8  = price_ram[(write_ptr - 9) & 8'hFF];
assign price_out_9  = price_ram[(write_ptr - 10) & 8'hFF];
assign price_out_10 = price_ram[(write_ptr - 11) & 8'hFF];
assign price_out_11 = price_ram[(write_ptr - 12) & 8'hFF];
assign price_out_12 = price_ram[(write_ptr - 13) & 8'hFF];
assign price_out_13 = price_ram[(write_ptr - 14) & 8'hFF];
assign price_out_14 = price_ram[(write_ptr - 15) & 8'hFF];
assign price_out_15 = price_ram[(write_ptr - 16) & 8'hFF];
assign price_out_16 = price_ram[(write_ptr - 17) & 8'hFF];
assign price_out_17 = price_ram[(write_ptr - 18) & 8'hFF];
assign price_out_18 = price_ram[(write_ptr - 19) & 8'hFF];
assign price_out_19 = price_ram[(write_ptr - 20) & 8'hFF];
assign price_out_20 = price_ram[(write_ptr - 21) & 8'hFF];

// Note: For larger windows (up to 256), additional outputs can be added
// or a read address interface can be implemented

endmodule
