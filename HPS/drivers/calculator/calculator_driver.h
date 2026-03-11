// ============================================================================
// Calculator Driver - Header File
// ============================================================================
// UIO-based driver for accessing hardware calculator IP from HPS.
// The kernel binds /dev/uioN to the DT node via uio_pdrv_genirq.
// Userspace opens /dev/uioN, mmaps registers, and waits for interrupts
// via blocking read() — no /dev/mem, no polling, no root requirement.
// ============================================================================

#ifndef CALCULATOR_DRIVER_H
#define CALCULATOR_DRIVER_H

#include <stdint.h>
#include <stdbool.h>

// ============================================================================
// Register Offsets (byte offsets from register base)
// ============================================================================
#define CALC_REG_CONTROL       0x00  // [31]=start, [3:0]=operation
#define CALC_REG_OPERAND_A     0x04  // 32-bit float operand A
#define CALC_REG_OPERAND_B     0x08  // 32-bit float operand B
#define CALC_REG_RESULT        0x0C  // 32-bit float result (read-only)
#define CALC_REG_STATUS        0x10  // [0]=busy, [1]=error, [2]=done, [3]=buf_full
#define CALC_REG_INT_ENABLE    0x14  // [0]=interrupt enable
#define CALC_REG_ERROR_CODE    0x2C  // Detailed error information
#define CALC_REG_VERSION       0x3C  // IP version
#define CALC_REG_COUNT         16    // Total 32-bit registers (64 bytes)

// ============================================================================
// Control Register Bit Fields
// ============================================================================
#define CALC_CTRL_START_BIT  31
#define CALC_CTRL_OP_MASK    0xF
#define CALC_CTRL_START      (1U << CALC_CTRL_START_BIT)

// ============================================================================
// Status Register Bit Fields
// ============================================================================
#define CALC_STATUS_BUSY      0x01
#define CALC_STATUS_ERROR     0x02
#define CALC_STATUS_DONE      0x04
#define CALC_STATUS_BUF_FULL  0x08

// UIO device name — must match linux,uio-name in DTS
#define CALC_UIO_NAME  "fpga-calculator"

// Interrupt wait timeout in milliseconds
#define CALC_IRQ_TIMEOUT_MS  1000

// ============================================================================
// Calculator Operation Types
// ============================================================================
typedef enum {
    CALC_OP_ADD = 0,
    CALC_OP_SUB = 1,
    CALC_OP_MUL = 2,
    CALC_OP_DIV = 3,
} calculator_operation_t;

// ============================================================================
// Calculator Status Structure
// ============================================================================
typedef struct {
    bool busy;
    bool error;
    bool done;
} calculator_status_t;

// ============================================================================
// Function Prototypes
// ============================================================================

/**
 * Initialize the calculator driver.
 * Discovers the UIO device by name, opens /dev/uioN, and mmaps registers.
 * Enables FPGA interrupts.
 *
 * Returns: 0 on success, -1 on failure.
 */
int calculator_init(void);

/**
 * Cleanup and close the calculator driver.
 * Disables FPGA interrupts, unmaps registers, closes UIO fd.
 */
void calculator_cleanup(void);

/**
 * Perform a calculation operation.
 * Writes operands, starts the operation, waits for IRQ (blocking),
 * reads and returns the result.
 *
 * Returns: 0 on success, -1 on error or timeout.
 */
int calculator_perform_operation(
    calculator_operation_t op,
    float operand_a,
    float operand_b,
    float *result
);

/**
 * Get current calculator status (non-blocking register read).
 */
calculator_status_t calculator_get_status(void);

/**
 * Wait for current calculation to complete.
 * Uses blocking read() on UIO fd with select() timeout.
 * On success, clears hardware interrupt so UIO is ready for the next op.
 *
 * Returns: 0 on success, -1 on timeout or error.
 */
int calculator_wait_for_completion(void);

/**
 * Write a 32-bit value to a calculator register.
 */
void calculator_write_reg(uint32_t offset, uint32_t value);

/**
 * Read a 32-bit value from a calculator register.
 */
uint32_t calculator_read_reg(uint32_t offset);

/**
 * Enable or disable FPGA-level interrupts.
 * When enabled, the FPGA asserts IRQ on DONE — UIO delivers it via read().
 */
void calculator_set_interrupt_enable(bool enable);

/**
 * Convert operation enum to human-readable string.
 */
const char *calculator_operation_to_string(calculator_operation_t op);

/**
 * Read the IP version register.
 * Returns: 32-bit version code (e.g., 0x00010001 for v1.1).
 */
uint32_t calculator_get_version(void);

#endif // CALCULATOR_DRIVER_H
