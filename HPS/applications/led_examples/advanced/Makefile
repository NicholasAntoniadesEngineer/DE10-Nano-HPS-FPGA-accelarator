# ============================================================================
# LED Examples - Advanced - Makefile
# ============================================================================
# Cross-compilation Makefile for ARM (HPS on DE10-Nano)
# ============================================================================

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc

# Paths
APP_DIR := $(CURDIR)
HPS_DIR := $(abspath $(APP_DIR)/../../..)
DRIVER_UIO_DIR := $(HPS_DIR)/drivers/fpga_uio
DRIVER_LED_DIR := $(HPS_DIR)/drivers/led

# Target executable
TARGET = hps_fpga_led_control

# Compiler flags
CFLAGS = -Wall -Wextra -O2
CFLAGS += -I$(DRIVER_UIO_DIR)
CFLAGS += -I$(DRIVER_LED_DIR)

# Linker flags
LDFLAGS =

# Source files
SRCS = main.c $(DRIVER_UIO_DIR)/fpga_uio.c $(DRIVER_LED_DIR)/led_controller.c
OBJS = main.o fpga_uio.o led_controller.o

# Header dependencies
DEPS = config.h $(DRIVER_UIO_DIR)/fpga_uio.h $(DRIVER_LED_DIR)/led_controller.h

.PHONY: all clean dtbo install

# Default target
all: $(TARGET)

# Link executable
$(TARGET): $(OBJS)
	@echo "Linking $@..."
	$(CC) $(OBJS) -o $(TARGET) $(LDFLAGS)
	@echo "Build complete: $(TARGET)"

# Compile main.c
main.o: main.c $(DEPS)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

# Compile fpga_uio driver
fpga_uio.o: $(DRIVER_UIO_DIR)/fpga_uio.c $(DRIVER_UIO_DIR)/fpga_uio.h
	@echo "Compiling FPGA UIO driver..."
	$(CC) $(CFLAGS) -c $(DRIVER_UIO_DIR)/fpga_uio.c -o $@

# Compile LED controller driver
led_controller.o: $(DRIVER_LED_DIR)/led_controller.c $(DRIVER_LED_DIR)/led_controller.h
	@echo "Compiling LED controller..."
	$(CC) $(CFLAGS) -c $(DRIVER_LED_DIR)/led_controller.c -o $@

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(TARGET) $(OBJS) *~
	@echo "Clean complete"

# Compile device tree overlay
dtbo: fpga-leds.dts
	@echo "Compiling device tree overlay..."
	dtc -I dts -O dtb -o fpga-leds.dtbo fpga-leds.dts

# Install device tree overlay
install: dtbo
	@echo "Installing device tree overlay..."
	sudo cp fpga-leds.dtbo /boot/overlays/
	sudo modprobe uio
	sudo modprobe uio_pdrv_genirq
	@echo "Installed successfully"
