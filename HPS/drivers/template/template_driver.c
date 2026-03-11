// ============================================================================
// Custom IP Driver - Implementation (TEMPLATE)
// ============================================================================
// Memory-mapped I/O driver for custom FPGA IP.
// Uses /dev/mem + mmap to access registers on the Lightweight HPS-to-FPGA bridge.
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <string.h>
#include <errno.h>
#include "template_driver.h"

// ============================================================================
// Private State
// ============================================================================
static void *virtual_base = NULL;
static int mem_fd = -1;
static volatile uint32_t *template_regs = NULL;

#define TEMPLATE_TIMEOUT 1000000  // Polling iterations before timeout

// ============================================================================
// Initialize Driver
// ============================================================================
int template_init(void) {
    mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (mem_fd == -1) {
        fprintf(stderr, "template: could not open /dev/mem: %s\n", strerror(errno));
        fprintf(stderr, "template: hint: run as root (sudo)\n");
        return -1;
    }

    virtual_base = mmap(
        NULL,
        HPS_LW_BRIDGE_SPAN,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        mem_fd,
        HPS_LW_BRIDGE_BASE
    );

    if (virtual_base == MAP_FAILED) {
        fprintf(stderr, "template: mmap failed: %s\n", strerror(errno));
        close(mem_fd);
        mem_fd = -1;
        return -1;
    }

    template_regs = (volatile uint32_t *)(
        (uint8_t *)virtual_base + (TEMPLATE_BASE_OFFSET & (HPS_LW_BRIDGE_SPAN - 1))
    );

    // Verify by reading version register
    uint32_t version = template_read_reg(TEMPLATE_REG_VERSION);
    printf("template: initialized at 0x%08X, version 0x%08X\n", TEMPLATE_BASE, version);

    if (version == 0x0) {
        fprintf(stderr, "template: FPGA registers returning 0 — IP not responding\n");
        fprintf(stderr, "template: check MSEL DIP switches and power-cycle the board\n");
        template_cleanup();
        return -1;
    }

    return 0;
}

// ============================================================================
// Cleanup Driver
// ============================================================================
void template_cleanup(void) {
    if (virtual_base != NULL && virtual_base != MAP_FAILED) {
        munmap(virtual_base, HPS_LW_BRIDGE_SPAN);
        virtual_base = NULL;
    }
    if (mem_fd >= 0) {
        close(mem_fd);
        mem_fd = -1;
    }
    template_regs = NULL;
}

// ============================================================================
// Register Access
// ============================================================================
void template_write_reg(uint32_t offset, uint32_t value) {
    if (template_regs == NULL) {
        fprintf(stderr, "template: not initialized\n");
        return;
    }
    template_regs[offset / 4] = value;
}

uint32_t template_read_reg(uint32_t offset) {
    if (template_regs == NULL) {
        fprintf(stderr, "template: not initialized\n");
        return 0;
    }
    return template_regs[offset / 4];
}

// ============================================================================
// Status
// ============================================================================
template_status_t template_get_status(void) {
    template_status_t status = {0};
    if (template_regs == NULL) return status;

    uint32_t reg = template_read_reg(TEMPLATE_REG_STATUS);
    status.busy  = (reg & TEMPLATE_STATUS_BUSY)  != 0;
    status.error = (reg & TEMPLATE_STATUS_ERROR) != 0;
    status.done  = (reg & TEMPLATE_STATUS_DONE)  != 0;
    return status;
}

// ============================================================================
// Wait for Completion
// ============================================================================
int template_wait_for_completion(void) {
    int timeout = TEMPLATE_TIMEOUT;
    template_status_t status;

    do {
        status = template_get_status();
        if (status.done || !status.busy) return 0;
        if (status.error) return -1;
        usleep(1);
    } while (--timeout > 0);

    fprintf(stderr, "template: operation timeout\n");
    return -1;
}

// ============================================================================
// Version
// ============================================================================
uint32_t template_get_version(void) {
    return template_read_reg(TEMPLATE_REG_VERSION);
}
