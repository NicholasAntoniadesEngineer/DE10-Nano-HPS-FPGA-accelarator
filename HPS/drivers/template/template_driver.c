// ============================================================================
// Custom IP Driver - Implementation (TEMPLATE)
// ============================================================================
// Replace every occurrence of "template" / "TEMPLATE" with your IP name.
// All UIO plumbing (device discovery, mmap, IRQ wait, re-arm) is handled
// by fpga_uio. This file contains only IP-specific logic.
// ============================================================================

#include <stdio.h>
#include "template_driver.h"
#include "fpga_uio.h"

static fpga_uio_dev_t g_dev = {-1, NULL, 0};

// ============================================================================
// Initialize
// ============================================================================
int template_init(void)
{
    if (fpga_uio_open(&g_dev, TEMPLATE_UIO_NAME) != 0)
        return -1;

    uint32_t version = template_read_reg(TEMPLATE_REG_VERSION);
    printf("template: version 0x%08X\n", version);

    if (version == 0x0) {
        fprintf(stderr, "template: FPGA registers returning 0 — IP not responding\n");
        fprintf(stderr, "template: check MSEL DIP switches and power-cycle the board\n");
        template_cleanup();
        return -1;
    }

    // Enable FPGA interrupt output and arm the kernel IRQ handler
    template_write_reg(TEMPLATE_REG_INT_ENABLE, 1);
    fpga_uio_arm(&g_dev);
    return 0;
}

// ============================================================================
// Cleanup
// ============================================================================
void template_cleanup(void)
{
    if (g_dev.regs != NULL)
        template_write_reg(TEMPLATE_REG_INT_ENABLE, 0);
    fpga_uio_close(&g_dev);
}

// ============================================================================
// Register Access
// ============================================================================
void template_write_reg(uint32_t offset, uint32_t value)
{
    fpga_uio_write(&g_dev, offset, value);
}

uint32_t template_read_reg(uint32_t offset)
{
    return fpga_uio_read(&g_dev, offset);
}

// ============================================================================
// Status
// ============================================================================
template_status_t template_get_status(void)
{
    return fpga_uio_get_status(&g_dev, TEMPLATE_REG_STATUS);
}

// ============================================================================
// Wait for Completion
// ============================================================================
int template_wait_for_completion(void)
{
    if (fpga_uio_wait_irq(&g_dev, TEMPLATE_IRQ_TIMEOUT_MS) != 0)
        return -1;

    template_status_t s = template_get_status();
    if (s.error) {
        fprintf(stderr, "template: hardware error\n");
        template_write_reg(TEMPLATE_REG_INT_ENABLE, 0);
        template_write_reg(TEMPLATE_REG_INT_ENABLE, 1);
        fpga_uio_arm(&g_dev);
        return -1;
    }

    // Clear level-sensitive interrupt before re-arming GIC
    template_write_reg(TEMPLATE_REG_INT_ENABLE, 0);
    template_write_reg(TEMPLATE_REG_INT_ENABLE, 1);
    fpga_uio_arm(&g_dev);
    return 0;
}

// ============================================================================
// Version
// ============================================================================
uint32_t template_get_version(void)
{
    return template_read_reg(TEMPLATE_REG_VERSION);
}
