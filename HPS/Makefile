# ============================================================================
# HPS Software Build System
# ============================================================================
# Unified Makefile for all HPS software components
# ============================================================================

SHELL := /bin/bash

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
STRIP = $(CROSS_COMPILE)strip

# Default target
.PHONY: all help clean calculator_test led_examples

all: calculator_test
	@echo "==========================================="
	@echo "HPS build complete"
	@echo "==========================================="

# Calculator test suite
calculator_test:
	@echo "Building calculator test suite..."
	$(MAKE) -C calculator_test CROSS_COMPILE=$(CROSS_COMPILE)

# LED examples
led_examples:
	@echo "Building LED examples..."
	@if [ -f "led_examples/basic/Makefile" ]; then \
		$(MAKE) -C led_examples/basic CROSS_COMPILE=$(CROSS_COMPILE) || true; \
	fi
	@if [ -f "led_examples/advanced/Makefile" ]; then \
		$(MAKE) -C led_examples/advanced CROSS_COMPILE=$(CROSS_COMPILE) || true; \
	fi

# Clean all build artifacts
clean:
	@echo "Cleaning HPS build artifacts..."
	$(MAKE) -C calculator_test clean || true
	@if [ -f "led_examples/basic/Makefile" ]; then \
		$(MAKE) -C led_examples/basic clean || true; \
	fi
	@if [ -f "led_examples/advanced/Makefile" ]; then \
		$(MAKE) -C led_examples/advanced clean || true; \
	fi
	@echo "Clean complete"

# Help target
help:
	@echo "HPS Software Build System"
	@echo "========================"
	@echo ""
	@echo "Targets:"
	@echo "  all              - Build all HPS components (default)"
	@echo "  calculator_test  - Build calculator test suite"
	@echo "  led_examples     - Build LED control examples"
	@echo "  clean            - Remove all build artifacts"
	@echo "  help             - Show this help message"
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
	@echo "  2. Deploy: scp calculator_test/calculator_test root@<board-ip>:/root/"
	@echo "  3. Run: ssh root@<board-ip> './calculator_test'"
