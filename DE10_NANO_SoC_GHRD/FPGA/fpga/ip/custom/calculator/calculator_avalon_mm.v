// ============================================================================
// Calculator Avalon-MM Slave Interface
// ============================================================================
// Implements Avalon Memory-Mapped slave interface for HPS communication
// Provides register access for configuration, control, and status
// ============================================================================

module calculator_avalon_mm (
    // Clock and Reset
    input  wire        clk,
    input  wire        reset_n,

    // Avalon-MM Slave Interface
    input  wire [5:0]  avs_address,        // Byte address (6 bits = 64 bytes = 16 registers)
    input  wire        avs_read,           // Read request
    input  wire        avs_write,          // Write request
    input  wire [31:0] avs_writedata,      // Write data
    output wire [31:0] avs_readdata,       // Read data
    output wire        avs_waitrequest,    // Wait request (not used - zero wait states)

    // Calculator Register Interface
    output wire [3:0]  reg_address,        // Register address (word aligned)
    output wire        reg_write,          // Register write enable
    output wire        reg_read,           // Register read enable
    output wire [31:0] reg_writedata,      // Data to write to register
    input  wire [31:0] reg_readdata        // Data read from register
);

// ============================================================================
// Address Decoding
// ============================================================================
// Convert byte address to word address (divide by 4)
// avs_address[5:2] selects register (0-15)
assign reg_address = avs_address[5:2];

// ============================================================================
// Control Signals
// ============================================================================
// Direct pass-through with minimal latency
assign reg_write     = avs_write;
assign reg_read      = avs_read;
assign reg_writedata = avs_writedata;
assign avs_readdata  = reg_readdata;

// No wait states - single cycle read/write
assign avs_waitrequest = 1'b0;

// ============================================================================
// Register Map Summary
// ============================================================================
// Address (byte) | Register         | Access | Description
// ---------------|------------------|--------|----------------------------------
// 0x00           | CONTROL          | R/W    | [31]=start, [3:0]=operation
// 0x04           | OPERAND_A        | W      | 32-bit float operand A
// 0x08           | OPERAND_B        | W      | 32-bit float operand B
// 0x0C           | RESULT           | R      | 32-bit float result
// 0x10           | STATUS           | R      | [3:0]=buf_full,done,error,busy
// 0x14           | INT_ENABLE       | R/W    | [0]=interrupt enable
// 0x18           | BUFFER_CONTROL   | R/W    | [15:0]=window, [16]=reset
// 0x1C           | BUFFER_WRITE     | W      | Write price to buffer
// 0x20           | BUFFER_COUNT     | R      | Current buffer count
// 0x24           | EMA_ALPHA        | R/W    | EMA alpha parameter (float)
// 0x28           | CONFIG_FLAGS     | R/W    | Configuration bits
// 0x2C           | ERROR_CODE       | R      | Detailed error info
// 0x30-0x38      | Reserved         | -      | Future use
// 0x3C           | VERSION          | R      | IP version
// ============================================================================

endmodule
