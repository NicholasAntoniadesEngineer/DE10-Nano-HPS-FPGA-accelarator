# ============================================================================
# HPS Drivers Build System for DE10-Nano
# ============================================================================
# Builds user-space hardware drivers and kernel driver integration
# ============================================================================

SHELL := /bin/bash

# Paths
DRIVERS_DIR := $(CURDIR)
HPS_DIR := $(abspath $(CURDIR)/..)
REPO_ROOT := $(abspath $(HPS_DIR)/..)

# Cross-compilation toolchain
CROSS_COMPILE ?= arm-linux-gnueabihf-

# User-space driver subdirectories
USERSPACE_DRIVERS = calculator fpga_uio led

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

.PHONY: all help clean userspace $(USERSPACE_DRIVERS) integration

# Default: build user-space drivers
all: userspace
	@echo -e "$(GREEN)All drivers built successfully$(NC)"

# Build all user-space drivers
userspace: $(USERSPACE_DRIVERS)

# Build individual user-space drivers
calculator:
	@echo -e "$(YELLOW)Building calculator driver...$(NC)"
	@$(MAKE) -C calculator CROSS_COMPILE=$(CROSS_COMPILE)

fpga_uio:
	@echo -e "$(YELLOW)Building FPGA UIO driver...$(NC)"
	@$(MAKE) -C fpga_uio CROSS_COMPILE=$(CROSS_COMPILE)

led: fpga_uio
	@echo -e "$(YELLOW)Building LED driver...$(NC)"
	@$(MAKE) -C led CROSS_COMPILE=$(CROSS_COMPILE)

# Kernel driver integration
integration:
	@echo -e "$(YELLOW)Driver integration tools are in integration/ directory$(NC)"
	@echo "See integration/README.md for usage"

# Clean all drivers
clean:
	@echo -e "$(YELLOW)Cleaning all drivers...$(NC)"
	@for dir in $(USERSPACE_DRIVERS); do \
		if [ -f $$dir/Makefile ]; then \
			$(MAKE) -C $$dir clean || true; \
		fi \
	done
	@rm -rf build
	@echo -e "$(GREEN)Clean complete$(NC)"

help:
	@echo "HPS Drivers Build System for DE10-Nano"
	@echo "========================================"
	@echo ""
	@echo "User-Space Drivers:"
	@echo "  calculator  - Calculator hardware driver"
	@echo "  fpga_uio    - FPGA UIO device driver"
	@echo "  led         - LED controller driver"
	@echo ""
	@echo "Targets:"
	@echo "  all         - Build all user-space drivers (default)"
	@echo "  userspace   - Build all user-space drivers"
	@echo "  clean       - Clean all build artifacts"
	@echo "  integration - Kernel driver integration tools"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Cross-Compilation:"
	@echo "  Toolchain: $(CROSS_COMPILE)"
	@echo ""
	@echo "Kernel Driver Integration:"
	@echo "  cd integration"
	@echo "  ./integrate_linux_driver.sh -k /path/to/linux-kernel"
	@echo ""
	@echo "Note: Driver integration is typically done during kernel build"
	@echo "      See: HPS/linux_image/kernel/Makefile"
