// ============================================================================
// FPGA UIO Shared Library - Header
// ============================================================================
// Common infrastructure for all FPGA IP drivers using the Linux UIO framework
// (uio_pdrv_genirq). Each per-IP driver holds an fpga_uio_dev_t and calls
// through this API. Only IP-specific concerns (register map, operation types,
// high-level API) belong in the per-IP driver.
//
// Typical per-IP driver init:
//   fpga_uio_dev_t dev = {0};
//   fpga_uio_open(&dev, "fpga-my-ip");     // discovers /dev/uioN, mmaps regs
//   fpga_uio_write(&dev, REG_CONTROL, 1);
//   fpga_uio_wait_irq(&dev, 1000);         // blocks up to 1000 ms
//   fpga_uio_arm(&dev);                    // re-enable for next operation
//   fpga_uio_close(&dev);
// ============================================================================

#ifndef FPGA_UIO_H
#define FPGA_UIO_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

// ============================================================================
// Device Handle
// ============================================================================
typedef struct {
    int                fd;        // /dev/uioN file descriptor (-1 when closed)
    volatile uint32_t *regs;      // mmapped register window (NULL when closed)
    size_t             map_size;  // size of mapped region (from sysfs map0/size)
} fpga_uio_dev_t;

// ============================================================================
// Standard STATUS Register Bit Fields
// Matches the template register file and all generated IP cores.
// IPs with additional status bits extend beyond these in their own headers.
// ============================================================================
#define FPGA_UIO_STATUS_BUSY   0x01
#define FPGA_UIO_STATUS_ERROR  0x02
#define FPGA_UIO_STATUS_DONE   0x04

typedef struct {
    bool busy;
    bool error;
    bool done;
} fpga_uio_status_t;

// ============================================================================
// API
// ============================================================================

/**
 * Open a UIO device by its linux,uio-name and map registers.
 * Walks /sys/class/uio/uioN/name to find the matching device, opens
 * /dev/uioN, and mmaps the register window at map index 0.
 *
 * @param dev       Caller-allocated handle; zero-initialise before first use
 * @param uio_name  Must match linux,uio-name in DTS
 * @return          0 on success, -1 on failure (check stderr for reason)
 */
int fpga_uio_open(fpga_uio_dev_t *dev, const char *uio_name);

/**
 * Unmap registers and close the UIO file descriptor.
 * Safe to call on a zero-initialised or already-closed handle.
 */
void fpga_uio_close(fpga_uio_dev_t *dev);

/**
 * Write a 32-bit value to a register.
 * @param offset  Byte offset from register base (4-byte aligned)
 */
void fpga_uio_write(fpga_uio_dev_t *dev, uint32_t offset, uint32_t value);

/**
 * Read a 32-bit value from a register.
 * @param offset  Byte offset from register base (4-byte aligned)
 */
uint32_t fpga_uio_read(fpga_uio_dev_t *dev, uint32_t offset);

/**
 * Block until an interrupt arrives on the UIO fd.
 * Uses select() so a hard timeout is always enforced.
 *
 * Does NOT re-arm the kernel IRQ handler — caller must clear the hardware
 * interrupt source first, then call fpga_uio_arm().
 *
 * @param timeout_ms  Maximum wait in milliseconds; -1 = infinite
 * @return            0 on interrupt received, -1 on timeout or error
 */
int fpga_uio_wait_irq(fpga_uio_dev_t *dev, int timeout_ms);

/**
 * Re-arm the kernel IRQ handler for the next operation.
 * Writes 1 to the UIO fd, re-enabling the GIC interrupt line.
 * Must be called after the hardware interrupt source is cleared.
 */
void fpga_uio_arm(fpga_uio_dev_t *dev);

/**
 * Decode the standard busy/error/done STATUS register.
 * @param status_offset  Byte offset of the STATUS register
 */
fpga_uio_status_t fpga_uio_get_status(fpga_uio_dev_t *dev, uint32_t status_offset);

#endif // FPGA_UIO_H
