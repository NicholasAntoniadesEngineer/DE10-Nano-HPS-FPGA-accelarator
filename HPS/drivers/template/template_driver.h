// ============================================================================
// Custom IP Driver - Header (TEMPLATE)
// ============================================================================
// Replace every occurrence of "template" / "TEMPLATE" with your IP name.
// The UIO infrastructure is provided by fpga_uio (shared library) — only
// IP-specific register map, types, and high-level API belong here.
// ============================================================================

#ifndef TEMPLATE_DRIVER_H
#define TEMPLATE_DRIVER_H

#include <stdint.h>
#include <stdbool.h>
#include "fpga_uio.h"

// ============================================================================
// UIO Device Name
// Must match linux,uio-name in the DTS node for this IP.
// ============================================================================
#define TEMPLATE_UIO_NAME   "fpga-template"

// ============================================================================
// Register Offsets (byte offsets; must match template_registers.v)
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
#define TEMPLATE_CTRL_START   (1U << 31)
#define TEMPLATE_CTRL_OP_MASK 0xF

// ============================================================================
// Interrupt Timeout
// ============================================================================
#define TEMPLATE_IRQ_TIMEOUT_MS  1000

// ============================================================================
// Status (re-exported from fpga_uio for convenience)
// ============================================================================
typedef fpga_uio_status_t template_status_t;

// ============================================================================
// Function Prototypes
// ============================================================================

/** Open UIO device, map registers, enable interrupt. Returns 0 on success. */
int template_init(void);

/** Disable interrupt, unmap registers, close UIO fd. */
void template_cleanup(void);

/** Write a 32-bit register (offset in bytes). */
void template_write_reg(uint32_t offset, uint32_t value);

/** Read a 32-bit register (offset in bytes). */
uint32_t template_read_reg(uint32_t offset);

/** Decode busy/error/done STATUS register. */
template_status_t template_get_status(void);

/**
 * Block until operation completes (interrupt-driven).
 * Clears hardware interrupt source and re-arms UIO on success.
 * Returns 0 on success, -1 on timeout or error.
 */
int template_wait_for_completion(void);

/** Read IP version register. */
uint32_t template_get_version(void);

#endif // TEMPLATE_DRIVER_H
