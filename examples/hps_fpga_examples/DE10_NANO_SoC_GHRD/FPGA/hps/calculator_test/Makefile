# ============================================================================
# Calculator Test Suite - Makefile
# ============================================================================
# Cross-compilation Makefile for ARM (HPS on DE10-Nano)
# ============================================================================

# Target executable
TARGET = calculator_test

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
STRIP = $(CROSS_COMPILE)strip

# Library paths
LOGGER_DIR = ../libs/logger

# Compiler flags
CFLAGS = -Wall -Wextra -O2 -g
CFLAGS += -std=gnu99
CFLAGS += -D_GNU_SOURCE
CFLAGS += -I$(LOGGER_DIR)

# Linker flags
LDFLAGS = -lm  # Link math library for fabsf()

# Source files
SRCS = main.c calculator_driver.c test_cases.c $(LOGGER_DIR)/logger.c
OBJS = main.o calculator_driver.o test_cases.o logger.o

# Header dependencies
DEPS = calculator_driver.h test_cases.h $(LOGGER_DIR)/logger.h

# ============================================================================
# Build Rules
# ============================================================================

.PHONY: all clean install help

# Default target
all: $(TARGET)

# Link executable
$(TARGET): $(OBJS)
	@echo "Linking $@..."
	$(CC) $(LDFLAGS) $^ -o $@
	@echo "Build complete: $(TARGET)"
	@echo ""
	@echo "To deploy to DE10-Nano:"
	@echo "  scp $(TARGET) root@<board-ip>:/root/"
	@echo ""
	@echo "To run on DE10-Nano:"
	@echo "  ssh root@<board-ip>"
	@echo "  ./calculator_test"

# Compile local source files
%.o: %.c $(DEPS)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

# Compile logger library
logger.o: $(LOGGER_DIR)/logger.c $(LOGGER_DIR)/logger.h
	@echo "Compiling logger library..."
	$(CC) $(CFLAGS) -c $(LOGGER_DIR)/logger.c -o $@

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(TARGET) $(OBJS) *~
	@echo "Clean complete"

# Install to SD card (if mounted)
install: $(TARGET)
	@if [ -d "/media/$(USER)/rootfs" ]; then \
		echo "Installing to SD card /media/$(USER)/rootfs..."; \
		cp $(TARGET) /media/$(USER)/rootfs/root/; \
		echo "Installed successfully"; \
	elif [ -d "/mnt/sd" ]; then \
		echo "Installing to SD card /mnt/sd..."; \
		cp $(TARGET) /mnt/sd/; \
		echo "Installed successfully"; \
	else \
		echo "SD card not found. Please mount SD card or use:"; \
		echo "  scp $(TARGET) root@<board-ip>:/root/"; \
	fi

# Strip debug symbols (smaller binary)
strip: $(TARGET)
	@echo "Stripping debug symbols..."
	$(STRIP) $(TARGET)
	@echo "Stripped binary size:"
	@ls -lh $(TARGET)

# Help target
help:
	@echo "Calculator Test Suite - Makefile Help"
	@echo "======================================"
	@echo ""
	@echo "Targets:"
	@echo "  all      - Build the test suite (default)"
	@echo "  clean    - Remove build artifacts"
	@echo "  install  - Install to mounted SD card"
	@echo "  strip    - Strip debug symbols for smaller binary"
	@echo "  help     - Show this help message"
	@echo ""
	@echo "Cross-Compilation:"
	@echo "  Toolchain: $(CROSS_COMPILE)"
	@echo "  Compiler:  $(CC)"
	@echo ""
	@echo "To use a different toolchain:"
	@echo "  make CROSS_COMPILE=arm-none-linux-gnueabihf-"
	@echo ""
	@echo "Native compilation (on DE10-Nano):"
	@echo "  make CROSS_COMPILE="
	@echo ""
	@echo "Deployment:"
	@echo "  1. Build: make"
	@echo "  2. Deploy: scp $(TARGET) root@<board-ip>:/root/"
	@echo "  3. Run: ssh root@<board-ip> './$(TARGET)'"
	@echo ""
	@echo "Or use SD card:"
	@echo "  1. Mount SD card"
	@echo "  2. make install"
	@echo "  3. Boot DE10-Nano and run './$(TARGET)'"

# ============================================================================
# Dependencies
# ============================================================================
main.o: main.c calculator_driver.h test_cases.h $(LOGGER_DIR)/logger.h
calculator_driver.o: calculator_driver.c calculator_driver.h $(LOGGER_DIR)/logger.h
test_cases.o: test_cases.c test_cases.h
logger.o: $(LOGGER_DIR)/logger.c $(LOGGER_DIR)/logger.h
