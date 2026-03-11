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
#define CALCULATOR_0_BASE 0x00000000  // Base address 0x0 in LW bridge (physical: 0xFF200000)
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
    CALC_OP_ADD = 0,           // Addition
    CALC_OP_SUB = 1,           // Subtraction
    CALC_OP_MUL = 2,           // Multiplication
    CALC_OP_DIV = 3,           // Division
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

/**
 * Get the IP version
 *
 * Returns: 32-bit version code (e.g., 0x00010001 for v1.0001)
 */
uint32_t calculator_get_version(void);

#endif // CALCULATOR_DRIVER_H
