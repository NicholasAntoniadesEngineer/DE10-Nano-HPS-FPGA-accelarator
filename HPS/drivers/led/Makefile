# ============================================================================
# LED Controller Driver - Makefile
# ============================================================================
# Builds LED controller driver as a static library
# ============================================================================

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

# Paths
DRIVER_DIR := $(CURDIR)
HPS_DIR := $(abspath $(DRIVER_DIR)/../..)

# Output
TARGET = libled.a

# Compiler flags
CFLAGS = -Wall -Wextra -O2 -g
CFLAGS += -std=gnu99
CFLAGS += -D_GNU_SOURCE
CFLAGS += -I$(HPS_DIR)/drivers/fpga_uio

# Source files
SRCS = led_controller.c
OBJS = $(SRCS:.c=.o)

# Header dependencies
DEPS = led_controller.h $(HPS_DIR)/drivers/fpga_uio/fpga_uio.h

.PHONY: all clean

# Default target
all: $(TARGET)

# Create static library
$(TARGET): $(OBJS)
	@echo "Creating static library $@..."
	$(AR) rcs $@ $^
	@echo "Build complete: $(TARGET)"

# Compile source files
%.o: %.c $(DEPS)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

# Clean build artifacts
clean:
	@echo "Cleaning LED driver..."
	rm -f $(TARGET) $(OBJS) *~
	@echo "Clean complete"
