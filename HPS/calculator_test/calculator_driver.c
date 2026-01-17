// ============================================================================
// Calculator Driver - Implementation
// ============================================================================
// Memory-mapped I/O driver for hardware calculator IP
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <string.h>
#include <errno.h>
#include "calculator_driver.h"
#include "logger.h"

// ============================================================================
// Memory Mapping Constants
// ============================================================================
#define HW_REGS_BASE  HPS_LW_BRIDGE_BASE
#define HW_REGS_SPAN  0x00200000  // 2MB span for lightweight bridge
#define HW_REGS_MASK  (HW_REGS_SPAN - 1)

// ============================================================================
// Global Variables
// ============================================================================
static void *virtual_base = NULL;
static int mem_fd = -1;
static volatile uint32_t *calculator_regs = NULL;

// Operation timeout (in polling iterations)
#define CALC_TIMEOUT 1000000

// ============================================================================
// Initialize Calculator Driver
// ============================================================================
int calculator_init(void) {
    LOG_INFO("Initializing calculator driver...");
    LOG_DEBUG("HPS_LW_BRIDGE_BASE: 0x%08X", HPS_LW_BRIDGE_BASE);
    LOG_DEBUG("CALCULATOR_0_BASE: 0x%08X", CALCULATOR_0_BASE);
    LOG_DEBUG("CALCULATOR_BASE: 0x%08X", CALCULATOR_BASE);
    LOG_DEBUG("HW_REGS_SPAN: 0x%08X (%u bytes)", HW_REGS_SPAN, HW_REGS_SPAN);
    
    // Open /dev/mem for memory mapping
    LOG_DEBUG("Opening /dev/mem for memory mapping...");
    mem_fd = open("/dev/mem", (O_RDWR | O_SYNC));
    if (mem_fd == -1) {
        LOG_ERROR("Could not open /dev/mem: %s", strerror(errno));
        LOG_ERROR("Hint: Run as root (sudo) or add user to appropriate group");
        return -1;
    }
    LOG_DEBUG("Successfully opened /dev/mem (fd=%d)", mem_fd);

    // Map physical memory into virtual address space
    LOG_DEBUG("Mapping physical memory: base=0x%08X, span=0x%08X", HW_REGS_BASE, HW_REGS_SPAN);
    virtual_base = mmap(
        NULL,
        HW_REGS_SPAN,
        (PROT_READ | PROT_WRITE),
        MAP_SHARED,
        mem_fd,
        HW_REGS_BASE
    );

    if (virtual_base == MAP_FAILED) {
        LOG_ERROR("mmap() failed: %s", strerror(errno));
        close(mem_fd);
        mem_fd = -1;
        return -1;
    }
    LOG_DEBUG("Memory mapped successfully: virtual_base=%p", virtual_base);

    // Calculate calculator register base address
    calculator_regs = (volatile uint32_t *)(
        (uint8_t *)virtual_base + (CALCULATOR_0_BASE & HW_REGS_MASK)
    );

    LOG_INFO("Calculator driver initialized successfully");
    LOG_INFO("  Physical base: 0x%08X", CALCULATOR_BASE);
    LOG_INFO("  Virtual base:  %p", (void *)calculator_regs);
    LOG_DEBUG("  Memory span:   0x%08X bytes", HW_REGS_SPAN);
    LOG_DEBUG("  Register offset: 0x%08X", CALCULATOR_0_BASE);
    
    // Verify initialization by reading version register
    uint32_t version = calculator_read_reg(CALC_REG_VERSION);
    LOG_INFO("  Hardware version: 0x%08X", version);
    
    // Dump all registers for debugging
    LOG_TRACE("Initial register state:");
    logger_register_dump(LOG_LEVEL_TRACE, "Calculator Registers", calculator_regs, 16);

    return 0;
}

// ============================================================================
// Cleanup Calculator Driver
// ============================================================================
void calculator_cleanup(void) {
    LOG_INFO("Cleaning up calculator driver...");
    
    if (virtual_base != NULL && virtual_base != MAP_FAILED) {
        LOG_DEBUG("Unmapping virtual memory: %p", virtual_base);
        if (munmap(virtual_base, HW_REGS_SPAN) != 0) {
            LOG_WARN("munmap() failed: %s", strerror(errno));
        } else {
            LOG_DEBUG("Memory unmapped successfully");
        }
        virtual_base = NULL;
    } else {
        LOG_DEBUG("No virtual memory to unmap");
    }

    if (mem_fd >= 0) {
        LOG_DEBUG("Closing /dev/mem (fd=%d)", mem_fd);
        if (close(mem_fd) != 0) {
            LOG_WARN("close() failed: %s", strerror(errno));
        }
        mem_fd = -1;
    } else {
        LOG_DEBUG("No file descriptor to close");
    }

    calculator_regs = NULL;
    LOG_INFO("Calculator driver cleanup complete");
}

// ============================================================================
// Write Calculator Register
// ============================================================================
void calculator_write_reg(uint32_t offset, uint32_t value) {
    if (calculator_regs == NULL) {
        LOG_ERROR("Calculator not initialized - cannot write register");
        return;
    }

    if (offset > 0x3C) {
        LOG_WARN("Register offset out of range: 0x%02X (max: 0x3C)", offset);
        return;
    }

    uint32_t reg_index = offset / 4;
    uint32_t old_value = calculator_regs[reg_index];
    
    LOG_REG_WRITE(offset, value);
    calculator_regs[reg_index] = value;
    
    // Verify write (read back)
    uint32_t readback = calculator_regs[reg_index];
    if (readback != value) {
        LOG_ERROR("Register write verification failed: wrote 0x%08X, read 0x%08X", value, readback);
    } else if (old_value != value) {
        LOG_TRACE("Register changed: 0x%08X -> 0x%08X", old_value, value);
    }
}

// ============================================================================
// Read Calculator Register
// ============================================================================
uint32_t calculator_read_reg(uint32_t offset) {
    if (calculator_regs == NULL) {
        LOG_ERROR("Calculator not initialized - cannot read register");
        return 0;
    }

    if (offset > 0x3C) {
        LOG_WARN("Register offset out of range: 0x%02X (max: 0x3C)", offset);
        return 0;
    }

    uint32_t value = calculator_regs[offset / 4];
    LOG_REG_READ(offset, value);
    
    return value;
}

// ============================================================================
// Get Calculator Status
// ============================================================================
calculator_status_t calculator_get_status(void) {
    calculator_status_t status = {0};

    if (calculator_regs == NULL) {
        return status;
    }

    uint32_t status_reg = calculator_read_reg(CALC_REG_STATUS);

    status.busy  = (status_reg & CALC_STATUS_BUSY) != 0;
    status.error = (status_reg & CALC_STATUS_ERROR) != 0;
    status.done  = (status_reg & CALC_STATUS_DONE) != 0;

    return status;
}

// ============================================================================
// Wait for Calculation Completion
// ============================================================================
int calculator_wait_for_completion(void) {
    calculator_status_t status;
    int timeout = CALC_TIMEOUT;
    int poll_count = 0;

    LOG_DEBUG("Waiting for calculation completion (timeout: %d iterations)", CALC_TIMEOUT);

    // Poll until done or timeout
    do {
        status = calculator_get_status();
        poll_count++;

        if (status.done || !status.busy) {
            LOG_DEBUG("Calculation completed after %d polls", poll_count);
            if (status.done) {
                LOG_TRACE("Status: DONE flag set");
            }
            return 0;  // Success
        }

        if (status.error) {
            LOG_ERROR("Calculator error detected during wait");
            uint32_t error_code = calculator_read_reg(CALC_REG_ERROR_CODE);
            LOG_ERROR("Error code: 0x%08X", error_code);
            return -1;
        }

        if (--timeout == 0) {
            LOG_ERROR("Calculator operation timeout after %d polls", poll_count);
            LOG_ERROR("Final status: busy=%d, error=%d, done=%d", 
                     status.busy, status.error, status.done);
            logger_register_dump(LOG_LEVEL_ERROR, "Register state at timeout", calculator_regs, 16);
            return -1;
        }

        // Log progress every 10000 polls
        if (poll_count % 10000 == 0) {
            LOG_DEBUG("Still waiting... (poll %d, timeout remaining: %d)", poll_count, timeout);
        }

        // Small delay to avoid hammering the bus
        usleep(1);

    } while (status.busy);

    return 0;
}

// ============================================================================
// Perform Calculation Operation
// ============================================================================
int calculator_perform_operation(
    calculator_operation_t op,
    float operand_a,
    float operand_b,
    float *result
) {
    if (calculator_regs == NULL) {
        LOG_ERROR("Calculator not initialized");
        return -1;
    }

    if (result == NULL) {
        LOG_ERROR("Result pointer is NULL");
        return -1;
    }

    if (op > CALC_OP_DIV) {
        LOG_ERROR("Invalid operation code: %d (max: %d)", op, CALC_OP_DIV);
        return -1;
    }

    LOG_OP_START(op, operand_a, operand_b);
    LOG_DEBUG("Operation: %s", calculator_operation_to_string(op));

    // Check if calculator is already busy
    calculator_status_t status = calculator_get_status();
    if (status.busy) {
        LOG_WARN("Calculator is busy, waiting for previous operation to complete...");
        if (calculator_wait_for_completion() != 0) {
            LOG_ERROR("Previous operation did not complete");
            return -1;
        }
        LOG_DEBUG("Previous operation completed, proceeding");
    }

    // Write operands
    // Cast float to uint32_t to preserve bit pattern
    uint32_t operand_a_bits = *((uint32_t *)&operand_a);
    uint32_t operand_b_bits = *((uint32_t *)&operand_b);

    LOG_DEBUG("Writing operands: A=0x%08X (%.6f), B=0x%08X (%.6f)", 
             operand_a_bits, operand_a, operand_b_bits, operand_b);
    calculator_write_reg(CALC_REG_OPERAND_A, operand_a_bits);
    calculator_write_reg(CALC_REG_OPERAND_B, operand_b_bits);

    // Start operation
    // Control register: [31]=start bit, [3:0]=operation
    uint32_t control = (1U << CALC_CTRL_START_BIT) | (op & CALC_CTRL_OP_MASK);
    LOG_DEBUG("Starting operation: control=0x%08X (start=1, op=0x%X)", control, op);
    calculator_write_reg(CALC_REG_CONTROL, control);

    // Wait for completion
    LOG_DEBUG("Waiting for operation to complete...");
    if (calculator_wait_for_completion() != 0) {
        LOG_OP_ERROR(op, calculator_read_reg(CALC_REG_ERROR_CODE));
        return -1;
    }

    // Check for errors
    status = calculator_get_status();
    if (status.error) {
        uint32_t error_code = calculator_read_reg(CALC_REG_ERROR_CODE);
        LOG_OP_ERROR(op, error_code);
        LOG_ERROR("Calculator reported an error (code: 0x%08X)", error_code);
        LOG_ERROR("This may indicate overflow, underflow, NaN, or division by zero");
        return -1;
    }

    // Read result
    uint32_t result_bits = calculator_read_reg(CALC_REG_RESULT);
    *result = *((float *)&result_bits);
    
    LOG_OP_COMPLETE(op, *result);
    LOG_DEBUG("Result: 0x%08X (%.6f)", result_bits, *result);

    return 0;
}

// ============================================================================
// Set Interrupt Enable
// ============================================================================
void calculator_set_interrupt_enable(bool enable) {
    LOG_DEBUG("Setting interrupt enable: %s", enable ? "true" : "false");
    uint32_t int_enable = enable ? 1 : 0;
    calculator_write_reg(CALC_REG_INT_ENABLE, int_enable);
    LOG_DEBUG("Interrupt enable set to: %u", int_enable);
}

// ============================================================================
// Convert Operation to String
// ============================================================================
const char* calculator_operation_to_string(calculator_operation_t op) {
    switch (op) {
        case CALC_OP_ADD: return "ADD";
        case CALC_OP_SUB: return "SUB";
        case CALC_OP_MUL: return "MUL";
        case CALC_OP_DIV: return "DIV";
        default:          return "UNKNOWN";
    }
}
