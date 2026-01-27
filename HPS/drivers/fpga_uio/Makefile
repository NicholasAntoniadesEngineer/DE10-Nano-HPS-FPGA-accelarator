# ============================================================================
# FPGA UIO Driver - Makefile
# ============================================================================
# Builds FPGA UIO driver as a static library
# ============================================================================

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

# Output
TARGET = libfpga_uio.a

# Compiler flags
CFLAGS = -Wall -Wextra -O2 -g
CFLAGS += -std=gnu99
CFLAGS += -D_GNU_SOURCE

# Source files
SRCS = fpga_uio.c
OBJS = $(SRCS:.c=.o)

# Header dependencies
DEPS = fpga_uio.h

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
	@echo "Cleaning FPGA UIO driver..."
	rm -f $(TARGET) $(OBJS) *~
	@echo "Clean complete"
