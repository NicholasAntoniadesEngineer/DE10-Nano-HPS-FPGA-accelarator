# ============================================================================
# Calculator Driver - Makefile
# ============================================================================
# Builds calculator driver as a static library
# ============================================================================

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

# Paths
DRIVER_DIR := $(CURDIR)
HPS_DIR := $(abspath $(DRIVER_DIR)/../..)
LIBS_DIR := $(HPS_DIR)/libs

# Output
TARGET = libcalculator.a

# Compiler flags
CFLAGS = -Wall -Wextra -O2 -g
CFLAGS += -std=gnu99
CFLAGS += -D_GNU_SOURCE
CFLAGS += -I$(LIBS_DIR)/logger

# Source files
SRCS = calculator_driver.c
OBJS = $(SRCS:.c=.o)

# Header dependencies
DEPS = calculator_driver.h $(LIBS_DIR)/logger/logger.h

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
	@echo "Cleaning calculator driver..."
	rm -f $(TARGET) $(OBJS) *~
	@echo "Clean complete"
