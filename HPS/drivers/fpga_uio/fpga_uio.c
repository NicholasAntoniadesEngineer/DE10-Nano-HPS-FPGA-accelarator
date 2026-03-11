// ============================================================================
// FPGA UIO Shared Library - Implementation
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/mman.h>
#include <sys/select.h>
#include "fpga_uio.h"

// ============================================================================
// Internal: Find UIO device number by linux,uio-name
// Returns device number (0, 1, ...) or -1 if not found.
// ============================================================================
static int uio_find_by_name(const char *target_name)
{
    DIR *dir = opendir("/sys/class/uio");
    if (!dir) {
        fprintf(stderr, "fpga_uio: cannot open /sys/class/uio: %s\n", strerror(errno));
        fprintf(stderr, "fpga_uio: is CONFIG_UIO enabled in the kernel?\n");
        return -1;
    }

    int found = -1;
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strncmp(entry->d_name, "uio", 3) != 0) continue;

        int num = atoi(entry->d_name + 3);

        char path[256];
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/name", num);

        FILE *f = fopen(path, "r");
        if (!f) continue;

        char name[128] = {0};
        if (fgets(name, sizeof(name), f)) {
            size_t len = strlen(name);
            if (len > 0 && name[len - 1] == '\n') name[len - 1] = '\0';
            if (strcmp(name, target_name) == 0)
                found = num;
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
// Open UIO Device
// ============================================================================
int fpga_uio_open(fpga_uio_dev_t *dev, const char *uio_name)
{
    dev->fd       = -1;
    dev->regs     = NULL;
    dev->map_size = 0;

    int uio_num = uio_find_by_name(uio_name);
    if (uio_num < 0) {
        fprintf(stderr, "fpga_uio: device '%s' not found in /sys/class/uio/*/name\n",
                uio_name);
        fprintf(stderr, "fpga_uio: check that FPGA is programmed and "
                "uio_pdrv_genirq.of_id=generic-uio is in kernel bootargs\n");
        return -1;
    }

    char uio_path[64];
    snprintf(uio_path, sizeof(uio_path), "/dev/uio%d", uio_num);

    dev->fd = open(uio_path, O_RDWR | O_SYNC);
    if (dev->fd < 0) {
        fprintf(stderr, "fpga_uio: cannot open %s: %s\n", uio_path, strerror(errno));
        return -1;
    }

    dev->map_size = uio_get_map_size(uio_num);
    dev->regs = (volatile uint32_t *)mmap(
        NULL, dev->map_size,
        PROT_READ | PROT_WRITE, MAP_SHARED,
        dev->fd, 0);

    if (dev->regs == MAP_FAILED) {
        fprintf(stderr, "fpga_uio: mmap failed for %s: %s\n",
                uio_path, strerror(errno));
        close(dev->fd);
        dev->fd   = -1;
        dev->regs = NULL;
        return -1;
    }

    return 0;
}

// ============================================================================
// Close UIO Device
// ============================================================================
void fpga_uio_close(fpga_uio_dev_t *dev)
{
    if (dev->regs != NULL && dev->regs != MAP_FAILED) {
        munmap((void *)dev->regs, dev->map_size);
        dev->regs = NULL;
    }
    if (dev->fd >= 0) {
        close(dev->fd);
        dev->fd = -1;
    }
    dev->map_size = 0;
}

// ============================================================================
// Register Access
// ============================================================================
void fpga_uio_write(fpga_uio_dev_t *dev, uint32_t offset, uint32_t value)
{
    if (!dev->regs) {
        fprintf(stderr, "fpga_uio: write to uninitialised device (offset=0x%02X)\n",
                offset);
        return;
    }
    dev->regs[offset / 4] = value;
}

uint32_t fpga_uio_read(fpga_uio_dev_t *dev, uint32_t offset)
{
    if (!dev->regs) {
        fprintf(stderr, "fpga_uio: read from uninitialised device (offset=0x%02X)\n",
                offset);
        return 0;
    }
    return dev->regs[offset / 4];
}

// ============================================================================
// Wait for Interrupt
// ============================================================================
int fpga_uio_wait_irq(fpga_uio_dev_t *dev, int timeout_ms)
{
    if (dev->fd < 0) {
        fprintf(stderr, "fpga_uio: wait_irq on uninitialised device\n");
        return -1;
    }

    fd_set rfds;
    FD_ZERO(&rfds);
    FD_SET(dev->fd, &rfds);

    struct timeval tv;
    struct timeval *tvp = NULL;
    if (timeout_ms >= 0) {
        tv.tv_sec  = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        tvp = &tv;
    }

    int ret = select(dev->fd + 1, &rfds, NULL, NULL, tvp);
    if (ret < 0) {
        fprintf(stderr, "fpga_uio: select() failed: %s\n", strerror(errno));
        return -1;
    }
    if (ret == 0) {
        fprintf(stderr, "fpga_uio: interrupt timeout after %d ms\n", timeout_ms);
        return -1;
    }

    uint32_t irq_count = 0;
    if (read(dev->fd, &irq_count, sizeof(irq_count)) < 0) {
        fprintf(stderr, "fpga_uio: UIO read failed: %s\n", strerror(errno));
        return -1;
    }

    return 0;
}

// ============================================================================
// Re-arm Kernel IRQ Handler
// ============================================================================
void fpga_uio_arm(fpga_uio_dev_t *dev)
{
    if (dev->fd < 0) return;
    uint32_t arm = 1;
    if (write(dev->fd, &arm, sizeof(arm)) < 0)
        fprintf(stderr, "fpga_uio: arm write failed: %s\n", strerror(errno));
}

// ============================================================================
// Decode Standard Status Register
// ============================================================================
fpga_uio_status_t fpga_uio_get_status(fpga_uio_dev_t *dev, uint32_t status_offset)
{
    fpga_uio_status_t s = {0};
    if (!dev->regs) return s;

    uint32_t reg = fpga_uio_read(dev, status_offset);
    s.busy  = (reg & FPGA_UIO_STATUS_BUSY)  != 0;
    s.error = (reg & FPGA_UIO_STATUS_ERROR) != 0;
    s.done  = (reg & FPGA_UIO_STATUS_DONE)  != 0;
    return s;
}
