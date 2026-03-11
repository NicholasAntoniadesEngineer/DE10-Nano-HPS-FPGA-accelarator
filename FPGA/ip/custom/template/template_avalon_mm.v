// ============================================================================
// Custom IP - Avalon-MM Slave Interface (TEMPLATE)
// ============================================================================
// Translates Avalon-MM bus signals to internal register interface.
// With addressUnits=WORDS in _hw.tcl, each address increment = one 32-bit word.
// ============================================================================

module template_avalon_mm (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Avalon-MM Slave Interface
    input  wire [3:0]  avs_address,         // Word address
    input  wire        avs_read,
    input  wire        avs_write,
    input  wire [31:0] avs_writedata,
    output wire [31:0] avs_readdata,
    output wire        avs_waitrequest,

    // Internal Register Interface
    output wire [3:0]  reg_address,
    output wire        reg_write,
    output wire        reg_read,
    output wire [31:0] reg_writedata,
    input  wire [31:0] reg_readdata
);

// Direct pass-through — no address translation needed with WORDS addressing
assign reg_address   = avs_address;
assign reg_write     = avs_write;
assign reg_read      = avs_read;
assign reg_writedata = avs_writedata;
assign avs_readdata  = reg_readdata;

// No wait states for register access
assign avs_waitrequest = 1'b0;

endmodule
