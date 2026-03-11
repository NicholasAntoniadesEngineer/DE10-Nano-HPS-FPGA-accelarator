# ============================================================================
# Boot LED Indicator - Makefile
# ============================================================================
# Cross-compilation Makefile for ARM (HPS on DE10-Nano)
# ============================================================================

TARGET = boot_led

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
STRIP = $(CROSS_COMPILE)strip

# Shared library paths
LOGGER_DIR   = ../../libs/logger
DRIVER_DIR   = ../../drivers/calculator
FPGA_UIO_DIR = ../../drivers/fpga_uio

# Compiler flags
CFLAGS = -Wall -Wextra -O2 -std=gnu99 -D_GNU_SOURCE
CFLAGS += -I$(LOGGER_DIR) -I$(DRIVER_DIR) -I$(FPGA_UIO_DIR)

LDFLAGS = -lm

# Source files
SRCS = boot_led.c \
       $(DRIVER_DIR)/calculator_driver.c \
       $(FPGA_UIO_DIR)/fpga_uio.c \
       $(LOGGER_DIR)/logger.c

OBJS = boot_led.o calculator_driver.o fpga_uio.o logger.o

DEPS = $(DRIVER_DIR)/calculator_driver.h $(FPGA_UIO_DIR)/fpga_uio.h $(LOGGER_DIR)/logger.h

.PHONY: all clean strip help

all: $(TARGET)

$(TARGET): $(OBJS)
	@echo "Linking $@..."
	$(CC) $(LDFLAGS) $^ -o $@
	@echo "Build complete: $(TARGET)"

boot_led.o: boot_led.c $(DEPS)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

calculator_driver.o: $(DRIVER_DIR)/calculator_driver.c $(DRIVER_DIR)/calculator_driver.h
	@echo "Compiling calculator driver..."
	$(CC) $(CFLAGS) -c $(DRIVER_DIR)/calculator_driver.c -o $@

fpga_uio.o: $(FPGA_UIO_DIR)/fpga_uio.c $(FPGA_UIO_DIR)/fpga_uio.h
	@echo "Compiling fpga_uio..."
	$(CC) $(CFLAGS) -c $(FPGA_UIO_DIR)/fpga_uio.c -o $@

logger.o: $(LOGGER_DIR)/logger.c $(LOGGER_DIR)/logger.h
	@echo "Compiling logger..."
	$(CC) $(CFLAGS) -c $(LOGGER_DIR)/logger.c -o $@

clean:
	rm -f $(TARGET) $(OBJS) *~
	@echo "Clean complete"

strip: $(TARGET)
	$(STRIP) $(TARGET)
	@echo "Stripped size:"; ls -lh $(TARGET)

help:
	@echo "Boot LED Indicator Makefile"
	@echo "  make          - Build ARM binary"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make strip    - Strip debug symbols"
	@echo "  make CROSS_COMPILE=  - Native build on DE10-Nano"
