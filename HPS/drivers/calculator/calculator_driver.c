// ============================================================================
// Calculator Driver - Implementation
// ============================================================================
// UIO-based driver for the FPGA calculator IP.
// Uses fpga_uio (shared library) for device discovery, mmap, and IRQ handling.
// This file contains only calculator-specific logic.
// ============================================================================

#include <string.h>
#include <errno.h>
#include "calculator_driver.h"
#include "fpga_uio.h"
#include "logger.h"

// ============================================================================
// Private State
// ============================================================================
static fpga_uio_dev_t g_dev = {-1, NULL, 0};

// ============================================================================
// Initialize Calculator Driver
// ============================================================================
int calculator_init(void)
{
    LOG_INFO("Initializing calculator driver (UIO)...");

    if (fpga_uio_open(&g_dev, CALC_UIO_NAME) != 0) {
        LOG_ERROR("Failed to open UIO device '%s'.", CALC_UIO_NAME);
        LOG_ERROR("Check: ls /sys/class/uio/*/name");
        LOG_ERROR("Ensure kernel has CONFIG_UIO_PDRV_GENIRQ=y and FPGA is programmed.");
        return -1;
    }

    LOG_DEBUG("Registers mapped: virtual=%p, size=0x%zx",
              (void *)g_dev.regs, g_dev.map_size);

    uint32_t version = calculator_read_reg(CALC_REG_VERSION);
    LOG_INFO("Hardware version: 0x%08X", version);

    if (version == 0x0) {
        LOG_ERROR("FPGA registers returning 0 — calculator IP not responding.");
        LOG_ERROR("Check DIP switch SW10 (MSEL) and power-cycle the board.");
        LOG_ERROR("Verify: devmem2 0xff20003c w  (should return 0x00010001)");
        calculator_cleanup();
        return -1;
    }

    calculator_set_interrupt_enable(true);
    fpga_uio_arm(&g_dev);

    LOG_INFO("Calculator driver initialized (interrupt-driven).");
    logger_register_dump(LOG_LEVEL_TRACE, "Initial registers", g_dev.regs, CALC_REG_COUNT);
    return 0;
}

// ============================================================================
// Cleanup Calculator Driver
// ============================================================================
void calculator_cleanup(void)
{
    LOG_INFO("Cleaning up calculator driver...");

    if (g_dev.regs != NULL) {
        calculator_set_interrupt_enable(false);
    }
    fpga_uio_close(&g_dev);

    LOG_INFO("Calculator driver cleanup complete.");
}

// ============================================================================
// Register Access
// ============================================================================
void calculator_write_reg(uint32_t offset, uint32_t value)
{
    if (offset > 0x3C || (offset & 0x3)) {
        LOG_WARN("Invalid register offset: 0x%02X", offset);
        return;
    }
    LOG_REG_WRITE(offset, value);
    fpga_uio_write(&g_dev, offset, value);
}

uint32_t calculator_read_reg(uint32_t offset)
{
    if (offset > 0x3C || (offset & 0x3)) {
        LOG_WARN("Invalid register offset: 0x%02X", offset);
        return 0;
    }
    uint32_t value = fpga_uio_read(&g_dev, offset);
    LOG_REG_READ(offset, value);
    return value;
}

// ============================================================================
// Get Calculator Status
// ============================================================================
calculator_status_t calculator_get_status(void)
{
    fpga_uio_status_t s = fpga_uio_get_status(&g_dev, CALC_REG_STATUS);
    calculator_status_t cs = { s.busy, s.error, s.done };
    return cs;
}

// ============================================================================
// Wait for Completion (interrupt-driven via UIO)
// ============================================================================
int calculator_wait_for_completion(void)
{
    if (fpga_uio_wait_irq(&g_dev, CALC_IRQ_TIMEOUT_MS) != 0) {
        LOG_ERROR("Interrupt timeout after %d ms", CALC_IRQ_TIMEOUT_MS);
        LOG_ERROR("Status: busy=%d error=%d done=%d",
                  (int)calculator_get_status().busy,
                  (int)calculator_get_status().error,
                  (int)calculator_get_status().done);
        logger_register_dump(LOG_LEVEL_ERROR, "Register state at timeout",
                             g_dev.regs, CALC_REG_COUNT);
        return -1;
    }

    calculator_status_t s = calculator_get_status();
    if (s.error) {
        uint32_t ec = calculator_read_reg(CALC_REG_ERROR_CODE);
        LOG_ERROR("Calculator hardware error: code=0x%08X", ec);
        // Clear hardware interrupt then re-arm
        calculator_set_interrupt_enable(false);
        calculator_set_interrupt_enable(true);
        fpga_uio_arm(&g_dev);
        return -1;
    }

    // Clear level-sensitive interrupt source before re-arming GIC
    calculator_set_interrupt_enable(false);
    calculator_set_interrupt_enable(true);
    fpga_uio_arm(&g_dev);

    return 0;
}

// ============================================================================
// Perform Calculation Operation
// ============================================================================
int calculator_perform_operation(
    calculator_operation_t op,
    float operand_a,
    float operand_b,
    float *result)
{
    if (g_dev.regs == NULL) { LOG_ERROR("Driver not initialized."); return -1; }
    if (result == NULL)     { LOG_ERROR("result is NULL.");          return -1; }
    if (op > CALC_OP_DIV)   { LOG_ERROR("Invalid op: %d", op);      return -1; }

    LOG_OP_START(op, operand_a, operand_b);

    uint32_t a_bits, b_bits;
    memcpy(&a_bits, &operand_a, 4);
    memcpy(&b_bits, &operand_b, 4);
    calculator_write_reg(CALC_REG_OPERAND_A, a_bits);
    calculator_write_reg(CALC_REG_OPERAND_B, b_bits);
    calculator_write_reg(CALC_REG_CONTROL, CALC_CTRL_START | (op & CALC_CTRL_OP_MASK));

    if (calculator_wait_for_completion() != 0) {
        LOG_OP_ERROR(op, calculator_read_reg(CALC_REG_ERROR_CODE));
        return -1;
    }

    if (calculator_get_status().error) {
        uint32_t ec = calculator_read_reg(CALC_REG_ERROR_CODE);
        LOG_OP_ERROR(op, ec);
        return -1;
    }

    uint32_t result_bits = calculator_read_reg(CALC_REG_RESULT);
    memcpy(result, &result_bits, 4);
    LOG_OP_COMPLETE(op, *result);
    return 0;
}

// ============================================================================
// Interrupt Enable
// ============================================================================
void calculator_set_interrupt_enable(bool enable)
{
    calculator_write_reg(CALC_REG_INT_ENABLE, enable ? 1 : 0);
}

// ============================================================================
// Version
// ============================================================================
uint32_t calculator_get_version(void)
{
    return calculator_read_reg(CALC_REG_VERSION);
}

// ============================================================================
// Operation to String
// ============================================================================
const char *calculator_operation_to_string(calculator_operation_t op)
{
    switch (op) {
        case CALC_OP_ADD: return "ADD";
        case CALC_OP_SUB: return "SUB";
        case CALC_OP_MUL: return "MUL";
        case CALC_OP_DIV: return "DIV";
        default:          return "UNKNOWN";
    }
}
