// ============================================================================
// Calculator Driver - Header File
// ============================================================================
// Driver for accessing hardware calculator IP from HPS (ARM processor)
// Provides C API for memory-mapped register access
// ============================================================================

#ifndef CALCULATOR_DRIVER_H
#define CALCULATOR_DRIVER_H

#include <stdint.h>
#include <stdbool.h>

// ============================================================================
// Calculator Base Address
// ============================================================================
// This will be defined in the generated hps_0.h after QSys generation
// If not defined, use the default lightweight bridge offset
#ifndef CALCULATOR_0_BASE
#define CALCULATOR_0_BASE 0x00080000  // Default: 512KB offset in LW bridge
#endif

// Full address calculation
// HPS lightweight bridge starts at 0xFF200000
#define HPS_LW_BRIDGE_BASE  0xFF200000
#define CALCULATOR_BASE     (HPS_LW_BRIDGE_BASE + CALCULATOR_0_BASE)

// ============================================================================
// Register Offsets
// ============================================================================
#define CALC_REG_CONTROL       0x00  // [31]=start, [3:0]=operation
#define CALC_REG_OPERAND_A     0x04  // 32-bit float operand A
#define CALC_REG_OPERAND_B     0x08  // 32-bit float operand B (or window size)
#define CALC_REG_RESULT        0x0C  // 32-bit float result (read-only)
#define CALC_REG_STATUS        0x10  // [0]=busy, [1]=error, [2]=done, [3]=buf_full
#define CALC_REG_INT_ENABLE    0x14  // [0]=interrupt enable
#define CALC_REG_BUFFER_CTRL   0x18  // [15:0]=window_size, [16]=reset_buffer
#define CALC_REG_BUFFER_WRITE  0x1C  // Write price to circular buffer
#define CALC_REG_BUFFER_COUNT  0x20  // Current buffer fill count
#define CALC_REG_EMA_ALPHA     0x24  // Alpha parameter for EMA (32-bit float)
#define CALC_REG_CONFIG_FLAGS  0x28  // Configuration bits
#define CALC_REG_ERROR_CODE    0x2C  // Detailed error information
#define CALC_REG_VERSION       0x3C  // IP version

// ============================================================================
// Control Register Bit Fields
// ============================================================================
#define CALC_CTRL_START_BIT  31
#define CALC_CTRL_OP_MASK    0xF  // 4-bit operation code
#define CALC_CTRL_START      (1 << CALC_CTRL_START_BIT)

// ============================================================================
// Status Register Bit Fields
// ============================================================================
#define CALC_STATUS_BUSY      0x01
#define CALC_STATUS_ERROR     0x02
#define CALC_STATUS_DONE      0x04
#define CALC_STATUS_BUF_FULL  0x08

// ============================================================================
// Calculator Operation Types
// ============================================================================
typedef enum {
    // Basic floating-point operations (0-3)
    CALC_OP_ADD = 0,           // Addition
    CALC_OP_SUB = 1,           // Subtraction
    CALC_OP_MUL = 2,           // Multiplication
    CALC_OP_DIV = 3,           // Division
    // High-Frequency Trading operations (4-15)
    CALC_OP_SMA = 4,           // Simple Moving Average
    CALC_OP_EMA = 5,           // Exponential Moving Average
    CALC_OP_WMA = 6,           // Weighted Moving Average
    CALC_OP_VWAP = 7,          // Volume-Weighted Average Price
    CALC_OP_STD_DEV = 8,       // Standard Deviation
    CALC_OP_RSI = 9,           // Relative Strength Index
    CALC_OP_BOLLINGER_UP = 10, // Bollinger Upper Band
    CALC_OP_BOLLINGER_DN = 11, // Bollinger Lower Band
    CALC_OP_MIN = 12,          // Minimum over window
    CALC_OP_MAX = 13,          // Maximum over window
    CALC_OP_RANGE = 14         // Range (Max - Min)
} calculator_operation_t;

// ============================================================================
// Calculator Status Structure
// ============================================================================
typedef struct {
    bool busy;   // Calculator is currently computing
    bool error;  // Error occurred (overflow, underflow, NaN, etc.)
    bool done;   // Calculation complete
} calculator_status_t;

// ============================================================================
// Function Prototypes
// ============================================================================

/**
 * Initialize the calculator driver
 * Opens /dev/mem and maps calculator registers into virtual memory
 *
 * Returns: 0 on success, -1 on failure
 *
 * Note: Must be run as root or with appropriate permissions
 */
int calculator_init(void);

/**
 * Cleanup and close the calculator driver
 * Unmaps memory and closes file descriptors
 */
void calculator_cleanup(void);

/**
 * Perform a calculation operation
 *
 * @param op        Operation to perform (ADD, SUB, MUL, DIV)
 * @param operand_a First operand (32-bit float)
 * @param operand_b Second operand (32-bit float)
 * @param result    Pointer to store result (32-bit float)
 *
 * Returns: 0 on success, -1 on failure
 *
 * This function:
 * 1. Writes operands to calculator registers
 * 2. Starts the calculation
 * 3. Waits for completion
 * 4. Reads and returns the result
 */
int calculator_perform_operation(
    calculator_operation_t op,
    float operand_a,
    float operand_b,
    float *result
);

/**
 * Get current calculator status
 *
 * Returns: calculator_status_t structure with busy, error, done flags
 */
calculator_status_t calculator_get_status(void);

/**
 * Wait for current calculation to complete
 * Polls status register until done flag is set or timeout occurs
 *
 * Returns: 0 on success, -1 on timeout
 */
int calculator_wait_for_completion(void);

/**
 * Write a 32-bit value to a calculator register
 *
 * @param offset Register offset (use CALC_REG_* constants)
 * @param value  Value to write
 */
void calculator_write_reg(uint32_t offset, uint32_t value);

/**
 * Read a 32-bit value from a calculator register
 *
 * @param offset Register offset (use CALC_REG_* constants)
 *
 * Returns: Register value
 */
uint32_t calculator_read_reg(uint32_t offset);

/**
 * Enable or disable calculator interrupts
 *
 * @param enable true to enable, false to disable
 */
void calculator_set_interrupt_enable(bool enable);

/**
 * Convert operation enum to string
 *
 * @param op Operation code
 *
 * Returns: String representation ("ADD", "SUB", "MUL", "DIV", etc.)
 */
const char* calculator_operation_to_string(calculator_operation_t op);

// ============================================================================
// HFT Buffer Management Functions
// ============================================================================

/**
 * Write a price to the circular price buffer
 *
 * @param price Price value to add to buffer (32-bit float)
 *
 * Returns: 0 on success, -1 if buffer is full
 */
int calculator_buffer_write_price(float price);

/**
 * Reset the price buffer (clear all stored prices)
 */
void calculator_buffer_reset(void);

/**
 * Set the window size for moving average calculations
 *
 * @param window_size Number of prices in the window (1-256)
 */
void calculator_set_window_size(uint16_t window_size);

/**
 * Get the current buffer fill count
 *
 * Returns: Number of prices currently stored in buffer
 */
uint16_t calculator_get_buffer_count(void);

/**
 * Set the EMA alpha parameter
 *
 * @param alpha Smoothing factor (0.0 to 1.0)
 *               Typically calculated as: 2 / (window + 1)
 */
void calculator_set_ema_alpha(float alpha);

/**
 * Get the IP version
 *
 * Returns: 32-bit version code (e.g., 0xHFT10001 for HFT v1.0001)
 */
uint32_t calculator_get_version(void);

// ============================================================================
// HFT Operation Functions
// ============================================================================

/**
 * Calculate Simple Moving Average (SMA)
 *
 * @param window Number of periods (must match configured window_size)
 * @param result Pointer to store SMA result
 *
 * Returns: 0 on success, -1 on failure
 *
 * Note: Buffer must contain at least 'window' prices
 */
int calculator_sma(uint16_t window, float *result);

/**
 * Calculate Exponential Moving Average (EMA)
 *
 * @param price  Current price
 * @param alpha  Smoothing factor (use calculator_set_ema_alpha first)
 * @param result Pointer to store EMA result
 *
 * Returns: 0 on success, -1 on failure
 *
 * Formula: EMA = alpha × price + (1-alpha) × EMA_previous
 */
int calculator_ema(float price, float alpha, float *result);

/**
 * Calculate Standard Deviation
 *
 * @param window Number of periods
 * @param result Pointer to store standard deviation result
 *
 * Returns: 0 on success, -1 on failure
 */
int calculator_std_dev(uint16_t window, float *result);

/**
 * Calculate Minimum value in window
 *
 * @param window Number of periods
 * @param result Pointer to store minimum value
 *
 * Returns: 0 on success, -1 on failure
 */
int calculator_min(uint16_t window, float *result);

/**
 * Calculate Maximum value in window
 *
 * @param window Number of periods
 * @param result Pointer to store maximum value
 *
 * Returns: 0 on success, -1 on failure
 */
int calculator_max(uint16_t window, float *result);

#endif // CALCULATOR_DRIVER_H
