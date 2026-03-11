// ============================================================================
// Calculator Driver - UIO Implementation
// ============================================================================
// Uses the Linux UIO framework (uio_pdrv_genirq) to access the calculator IP.
// The DT node (compatible = "generic-uio") causes the kernel to create a
// /dev/uioN device. This driver:
//   1. Discovers /dev/uioN by matching linux,uio-name = "fpga-calculator"
//   2. mmaps the 64-byte register window via the UIO fd (offset = 0)
//   3. Uses blocking read() on the UIO fd to wait for IRQ (interrupt-driven)
//   4. Writes 1 to the UIO fd to re-arm the kernel IRQ handler after each op
//
// No /dev/mem, no polling, no hardcoded physical addresses.
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/mman.h>
#include <sys/select.h>
#include "calculator_driver.h"
#include "logger.h"

// ============================================================================
// Internal State
// ============================================================================
static int                  uio_fd       = -1;
static volatile uint32_t   *calc_regs    = NULL;
static size_t               mmap_size    = 0;

// ============================================================================
// Internal: Find UIO device by name
// Walks /sys/class/uio/uioN/name and returns the first matching N, or -1.
// ============================================================================
static int uio_find_by_name(const char *target_name)
{
    DIR *dir = opendir("/sys/class/uio");
    if (!dir) {
        LOG_ERROR("Cannot open /sys/class/uio: %s", strerror(errno));
        LOG_ERROR("Is CONFIG_UIO enabled in the kernel?");
        return -1;
    }

    int found = -1;
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strncmp(entry->d_name, "uio", 3) != 0) continue;

        int num = atoi(entry->d_name + 3);

        char name_path[256];
        snprintf(name_path, sizeof(name_path),
                 "/sys/class/uio/uio%d/name", num);

        FILE *f = fopen(name_path, "r");
        if (!f) continue;

        char name[128] = {0};
        if (fgets(name, sizeof(name), f)) {
            // strip trailing newline
            size_t len = strlen(name);
            if (len > 0 && name[len - 1] == '\n') name[len - 1] = '\0';

            if (strcmp(name, target_name) == 0) {
                found = num;
            }
        }
        fclose(f);
        if (found >= 0) break;
    }
    closedir(dir);
    return found;
}

// ============================================================================
// Internal: Read mmap size from sysfs map0/size
// ============================================================================
static size_t uio_get_map_size(int uio_num)
{
    char path[256];
    snprintf(path, sizeof(path),
             "/sys/class/uio/uio%d/maps/map0/size", uio_num);

    FILE *f = fopen(path, "r");
    if (!f) return 0x40;  // fallback: 64 bytes (16 registers)

    unsigned long sz = 0;
    fscanf(f, "0x%lx", &sz);
    fclose(f);
    return sz ? sz : 0x40;
}

// ============================================================================
// Initialize Calculator Driver
// ============================================================================
int calculator_init(void)
{
    LOG_INFO("Initializing calculator driver (UIO)...");

    // Discover /dev/uioN for the calculator
    int uio_num = uio_find_by_name(CALC_UIO_NAME);
    if (uio_num < 0) {
        LOG_ERROR("UIO device '%s' not found.", CALC_UIO_NAME);
        LOG_ERROR("Check: ls /sys/class/uio/*/name");
        LOG_ERROR("Ensure kernel has CONFIG_UIO_PDRV_GENIRQ=y and FPGA is programmed.");
        return -1;
    }

    char uio_path[64];
    snprintf(uio_path, sizeof(uio_path), "/dev/uio%d", uio_num);
    LOG_INFO("Found calculator at %s", uio_path);

    uio_fd = open(uio_path, O_RDWR | O_SYNC);
    if (uio_fd < 0) {
        LOG_ERROR("Cannot open %s: %s", uio_path, strerror(errno));
        return -1;
    }

    // Map register window — offset 0 = first DT reg entry (0xff200000, 0x40)
    mmap_size = uio_get_map_size(uio_num);
    calc_regs = (volatile uint32_t *)mmap(
        NULL, mmap_size,
        PROT_READ | PROT_WRITE, MAP_SHARED,
        uio_fd, 0 /* = map index 0 * getpagesize() */);

    if (calc_regs == MAP_FAILED) {
        LOG_ERROR("mmap failed: %s", strerror(errno));
        close(uio_fd);
        uio_fd = -1;
        calc_regs = NULL;
        return -1;
    }

    LOG_DEBUG("Registers mapped: virtual=%p, size=0x%zx", (void *)calc_regs, mmap_size);

    // Verify hardware is responding
    uint32_t version = calculator_read_reg(CALC_REG_VERSION);
    LOG_INFO("Hardware version: 0x%08X", version);

    if (version == 0x0) {
        LOG_ERROR("FPGA registers returning 0 — calculator IP not responding.");
        LOG_ERROR("Check DIP switch SW10 (MSEL) and power-cycle the board.");
        LOG_ERROR("Verify: devmem2 0xff20003c w  (should return 0x00010001)");
        calculator_cleanup();
        return -1;
    }

    // Enable FPGA interrupt output — the kernel UIO handler will arm the GIC
    calculator_set_interrupt_enable(true);

    // Arm the UIO kernel handler so the first read() can block correctly.
    // Writing 1 to the UIO fd enables the IRQ at the GIC level.
    uint32_t arm = 1;
    if (write(uio_fd, &arm, sizeof(arm)) < 0) {
        LOG_WARN("UIO arm write failed: %s (interrupts may not work)", strerror(errno));
    }

    LOG_INFO("Calculator driver initialized (UIO, interrupt-driven).");
    logger_register_dump(LOG_LEVEL_TRACE, "Initial registers", calc_regs, CALC_REG_COUNT);
    return 0;
}

// ============================================================================
// Cleanup Calculator Driver
// ============================================================================
void calculator_cleanup(void)
{
    LOG_INFO("Cleaning up calculator driver...");

    if (calc_regs != NULL && calc_regs != MAP_FAILED) {
        calculator_set_interrupt_enable(false);
        munmap((void *)calc_regs, mmap_size);
        calc_regs = NULL;
    }

    if (uio_fd >= 0) {
        close(uio_fd);
        uio_fd = -1;
    }

    LOG_INFO("Calculator driver cleanup complete.");
}

// ============================================================================
// Write Calculator Register
// ============================================================================
void calculator_write_reg(uint32_t offset, uint32_t value)
{
    if (calc_regs == NULL) {
        LOG_ERROR("Driver not initialized.");
        return;
    }
    if (offset > 0x3C || (offset & 0x3)) {
        LOG_WARN("Invalid register offset: 0x%02X", offset);
        return;
    }
    LOG_REG_WRITE(offset, value);
    calc_regs[offset / 4] = value;
}

// ============================================================================
// Read Calculator Register
// ============================================================================
uint32_t calculator_read_reg(uint32_t offset)
{
    if (calc_regs == NULL) {
        LOG_ERROR("Driver not initialized.");
        return 0;
    }
    if (offset > 0x3C || (offset & 0x3)) {
        LOG_WARN("Invalid register offset: 0x%02X", offset);
        return 0;
    }
    uint32_t value = calc_regs[offset / 4];
    LOG_REG_READ(offset, value);
    return value;
}

// ============================================================================
// Get Calculator Status
// ============================================================================
calculator_status_t calculator_get_status(void)
{
    calculator_status_t s = {0};
    if (calc_regs == NULL) return s;

    uint32_t sr = calculator_read_reg(CALC_REG_STATUS);
    s.busy  = (sr & CALC_STATUS_BUSY)  != 0;
    s.error = (sr & CALC_STATUS_ERROR) != 0;
    s.done  = (sr & CALC_STATUS_DONE)  != 0;
    return s;
}

// ============================================================================
// Wait for Calculation Completion (interrupt-driven via UIO)
// ============================================================================
int calculator_wait_for_completion(void)
{
    if (uio_fd < 0) {
        LOG_ERROR("Driver not initialized.");
        return -1;
    }

    // Use select() so we can enforce a hard timeout
    struct timeval tv = {
        .tv_sec  = CALC_IRQ_TIMEOUT_MS / 1000,
        .tv_usec = (CALC_IRQ_TIMEOUT_MS % 1000) * 1000,
    };
    fd_set rfds;
    FD_ZERO(&rfds);
    FD_SET(uio_fd, &rfds);

    int ret = select(uio_fd + 1, &rfds, NULL, NULL, &tv);
    if (ret < 0) {
        LOG_ERROR("select() failed: %s", strerror(errno));
        return -1;
    }
    if (ret == 0) {
        LOG_ERROR("Interrupt timeout after %d ms", CALC_IRQ_TIMEOUT_MS);
        LOG_ERROR("Status: busy=%d error=%d done=%d",
                  (int)calculator_get_status().busy,
                  (int)calculator_get_status().error,
                  (int)calculator_get_status().done);
        logger_register_dump(LOG_LEVEL_ERROR, "Register state at timeout",
                             calc_regs, CALC_REG_COUNT);
        return -1;
    }

    // Read interrupt count (clears the pending UIO event)
    uint32_t irq_count = 0;
    if (read(uio_fd, &irq_count, sizeof(irq_count)) < 0) {
        LOG_ERROR("UIO read failed: %s", strerror(errno));
        return -1;
    }
    LOG_DEBUG("IRQ received (count=%u)", irq_count);

    // Check for hardware error
    calculator_status_t s = calculator_get_status();
    if (s.error) {
        uint32_t ec = calculator_read_reg(CALC_REG_ERROR_CODE);
        LOG_ERROR("Calculator hardware error: code=0x%08X", ec);
        // Clear interrupt source before re-arming
        calculator_set_interrupt_enable(false);
        calculator_set_interrupt_enable(true);
        uint32_t arm = 1;
        write(uio_fd, &arm, sizeof(arm));
        return -1;
    }

    // Clear interrupt source: pulse INT_ENABLE so FPGA deasserts the level.
    // This must happen BEFORE re-arming the kernel IRQ, otherwise the
    // level-sensitive line would immediately re-trigger.
    calculator_set_interrupt_enable(false);
    calculator_set_interrupt_enable(true);

    // Re-arm the kernel IRQ handler for the next operation
    uint32_t arm = 1;
    if (write(uio_fd, &arm, sizeof(arm)) < 0) {
        LOG_WARN("UIO re-arm write failed: %s", strerror(errno));
    }

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
    if (calc_regs == NULL) { LOG_ERROR("Driver not initialized."); return -1; }
    if (result == NULL)    { LOG_ERROR("result is NULL.");          return -1; }
    if (op > CALC_OP_DIV)  { LOG_ERROR("Invalid op: %d", op);      return -1; }

    LOG_OP_START(op, operand_a, operand_b);

    // Write operands (IEEE 754 bit-exact)
    uint32_t a_bits, b_bits;
    memcpy(&a_bits, &operand_a, 4);
    memcpy(&b_bits, &operand_b, 4);
    calculator_write_reg(CALC_REG_OPERAND_A, a_bits);
    calculator_write_reg(CALC_REG_OPERAND_B, b_bits);

    // Start — control register: bit31=start, bits[3:0]=op
    calculator_write_reg(CALC_REG_CONTROL,
                         CALC_CTRL_START | (op & CALC_CTRL_OP_MASK));

    // Block until IRQ fires (or timeout)
    if (calculator_wait_for_completion() != 0) {
        LOG_OP_ERROR(op, calculator_read_reg(CALC_REG_ERROR_CODE));
        return -1;
    }

    // Final error check
    calculator_status_t s = calculator_get_status();
    if (s.error) {
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
// Set Interrupt Enable (FPGA-side)
// ============================================================================
void calculator_set_interrupt_enable(bool enable)
{
    calculator_write_reg(CALC_REG_INT_ENABLE, enable ? 1 : 0);
}

// ============================================================================
// Get IP Version
// ============================================================================
uint32_t calculator_get_version(void)
{
    return calculator_read_reg(CALC_REG_VERSION);
}

// ============================================================================
// Convert Operation to String
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
