#include "fpga_uio.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <errno.h>
#include <string.h>

int fpga_uio_init(fpga_uio_dev_t* dev, const char* device_path, size_t map_size) {
    if (!dev || !device_path) {
        errno = EINVAL;
        return -1;
    }

    // Initialize structure
    dev->fd = -1;
    dev->map_base = NULL;
    dev->map_size = map_size;
    dev->is_initialized = false;

    // Open UIO device
    dev->fd = open(device_path, O_RDWR);
    if (dev->fd < 0) {
        fprintf(stderr, "Failed to open UIO device %s: %s\n", 
                device_path, strerror(errno));
        return -1;
    }

    // Map device memory
    dev->map_base = mmap(NULL, map_size, PROT_READ | PROT_WRITE, 
                        MAP_SHARED, dev->fd, 0);
    if (dev->map_base == MAP_FAILED) {
        fprintf(stderr, "Failed to map device memory: %s\n", 
                strerror(errno));
        close(dev->fd);
        dev->fd = -1;
        return -1;
    }

    dev->is_initialized = true;
    return 0;
}

int fpga_uio_write32(fpga_uio_dev_t* dev, size_t offset, uint32_t value) {
    if (!dev || !dev->is_initialized || offset >= dev->map_size) {
        errno = EINVAL;
        return -1;
    }

    volatile uint32_t* addr = (volatile uint32_t*)((char*)dev->map_base + offset);
    *addr = value;
    return 0;
}

int fpga_uio_read32(fpga_uio_dev_t* dev, size_t offset, uint32_t* value) {
    if (!dev || !dev->is_initialized || !value || offset >= dev->map_size) {
        errno = EINVAL;
        return -1;
    }

    volatile uint32_t* addr = (volatile uint32_t*)((char*)dev->map_base + offset);
    *value = *addr;
    return 0;
}

void fpga_uio_cleanup(fpga_uio_dev_t* dev) {
    if (!dev || !dev->is_initialized) {
        return;
    }

    if (dev->map_base != NULL && dev->map_base != MAP_FAILED) {
        munmap(dev->map_base, dev->map_size);
        dev->map_base = NULL;
    }

    if (dev->fd >= 0) {
        close(dev->fd);
        dev->fd = -1;
    }

    dev->is_initialized = false;
} 