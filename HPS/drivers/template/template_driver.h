// ============================================================================
// Custom IP Driver - Header File (TEMPLATE)
// ============================================================================
// Copy this directory and rename all files/types to match your IP name.
// Example: cp -r template/ moving_average/
//          then rename template -> moving_average, TEMPLATE -> MOVING_AVG
//
// This driver provides a C API for accessing custom FPGA IP from the HPS
// (ARM processor) via the Lightweight HPS-to-FPGA bridge and /dev/mem.
// ============================================================================

#ifndef TEMPLATE_DRIVER_H
#define TEMPLATE_DRIVER_H

#include <stdint.h>
#include <stdbool.h>

// ============================================================================
// Base Address Configuration
// ============================================================================
// The HPS lightweight bridge maps to physical address 0xFF200000.
// Your IP's base offset is set in Platform Designer (QSys).
// Update TEMPLATE_BASE_OFFSET to match the baseAddress in soc_system.qsys.

#define HPS_LW_BRIDGE_BASE    0xFF200000
#define HPS_LW_BRIDGE_SPAN    0x00200000  // 2 MB

#ifndef TEMPLATE_BASE_OFFSET
#define TEMPLATE_BASE_OFFSET   0x0100     // <-- CHANGE THIS to match QSys base address
#endif

#define TEMPLATE_BASE          (HPS_LW_BRIDGE_BASE + TEMPLATE_BASE_OFFSET)

// ============================================================================
// Register Offsets (must match Verilog register map in template_registers.v)
// ============================================================================
#define TEMPLATE_REG_CONTROL      0x00  // [31]=start, [3:0]=operation
#define TEMPLATE_REG_INPUT_A      0x04  // 32-bit input A
#define TEMPLATE_REG_INPUT_B      0x08  // 32-bit input B
#define TEMPLATE_REG_RESULT       0x0C  // 32-bit result (read-only)
#define TEMPLATE_REG_STATUS       0x10  // [0]=busy, [1]=error, [2]=done
#define TEMPLATE_REG_INT_ENABLE   0x14  // [0]=interrupt enable
#define TEMPLATE_REG_VERSION      0x3C  // IP version (read-only)

// ============================================================================
// Control Register Bit Fields
// ============================================================================
#define TEMPLATE_CTRL_START_BIT   31
#define TEMPLATE_CTRL_OP_MASK     0xF
#define TEMPLATE_CTRL_START       (1U << TEMPLATE_CTRL_START_BIT)

// ============================================================================
// Status Register Bit Fields
// ============================================================================
#define TEMPLATE_STATUS_BUSY      0x01
#define TEMPLATE_STATUS_ERROR     0x02
#define TEMPLATE_STATUS_DONE      0x04

// ============================================================================
// Status Structure
// ============================================================================
typedef struct {
    bool busy;
    bool error;
    bool done;
} template_status_t;

// ============================================================================
// Function Prototypes
// ============================================================================

/**
 * Initialize the driver.
 * Opens /dev/mem and maps IP registers into virtual memory.
 * Must be run as root or with appropriate permissions.
 *
 * Returns: 0 on success, -1 on failure
 */
int template_init(void);

/**
 * Cleanup: unmap memory and close file descriptors.
 */
void template_cleanup(void);

/**
 * Write a 32-bit value to a register.
 * @param offset  Register offset (use TEMPLATE_REG_* constants)
 * @param value   Value to write
 */
void template_write_reg(uint32_t offset, uint32_t value);

/**
 * Read a 32-bit value from a register.
 * @param offset  Register offset (use TEMPLATE_REG_* constants)
 * Returns: Register value
 */
uint32_t template_read_reg(uint32_t offset);

/**
 * Get current status flags.
 */
template_status_t template_get_status(void);

/**
 * Wait for the current operation to complete.
 * Returns: 0 on success, -1 on timeout
 */
int template_wait_for_completion(void);

/**
 * Read the IP version register.
 */
uint32_t template_get_version(void);

#endif // TEMPLATE_DRIVER_H
