#ifndef FPGA_UIO_H
#define FPGA_UIO_H

#include <stdint.h>
#include <stdbool.h>

// Structure to hold UIO device information
typedef struct {
    int fd;              // File descriptor for UIO device
    void* map_base;      // Base address of memory mapping
    size_t map_size;     // Size of memory mapping
    bool is_initialized; // Initialization status
} fpga_uio_dev_t;

// Initialize UIO device
int fpga_uio_init(fpga_uio_dev_t* dev, const char* device_path, size_t map_size);

// Write 32-bit value to specified offset
int fpga_uio_write32(fpga_uio_dev_t* dev, size_t offset, uint32_t value);

// Read 32-bit value from specified offset
int fpga_uio_read32(fpga_uio_dev_t* dev, size_t offset, uint32_t* value);

// Cleanup UIO device
void fpga_uio_cleanup(fpga_uio_dev_t* dev);

#endif // FPGA_UIO_H 