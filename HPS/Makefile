# ============================================================================
# HPS Software Build System for DE10-Nano
# ============================================================================
# Main orchestrator for all HPS components
# ============================================================================
# 
# Organization:
#   - linux_image/  : Kernel, rootfs, and SD card image
#   - drivers/      : Linux driver integration tools
#   - applications/ : User-space applications (calculator_test, led_examples)
# ============================================================================

SHELL := /bin/bash

# Paths
HPS_DIR := $(CURDIR)
REPO_ROOT := $(abspath $(CURDIR)/..)

# Component directories
LINUX_IMAGE_DIR := $(HPS_DIR)/linux_image
DRIVERS_DIR := $(HPS_DIR)/drivers
APPLICATIONS_DIR := $(HPS_DIR)/applications

# Cross-compilation
CROSS_COMPILE ?= arm-linux-gnueabihf-

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

.PHONY: all help clean clean-all everything \
        linux-image kernel rootfs sd-image \
        drivers applications calculator_test led_examples

# Default target - build applications only (fastest)
all: applications
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)HPS build complete$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo ""
	@echo -e "$(YELLOW)To build Linux image:$(NC)"
	@echo "  make linux-image"
	@echo "  Or: cd linux_image && sudo make all"

help:
	@echo "HPS Software Build System for DE10-Nano"
	@echo "========================================"
	@echo ""
	@echo "Organization:"
	@echo "  linux_image/  - Kernel, rootfs, and SD card image"
	@echo "  drivers/      - Linux driver integration tools"
	@echo "  applications/ - User-space applications"
	@echo ""
	@echo "Application Targets (Fast - no root required):"
	@echo "  all              - Build all applications (default)"
	@echo "  applications     - Build all applications"
	@echo "  calculator_test  - Build calculator test suite"
	@echo "  led_examples     - Build LED control examples"
	@echo ""
	@echo "Linux Image Targets (Slow - requires root for rootfs/image):"
	@echo "  linux-image      - Build complete Linux image (kernel + rootfs + SD image)"
	@echo "  kernel           - Build Linux kernel only"
	@echo "  rootfs           - Build root filesystem only (requires root)"
	@echo "  sd-image         - Create SD card image (requires kernel, rootfs, and root)"
	@echo ""
	@echo "Driver Targets:"
	@echo "  drivers          - Show driver integration information"
	@echo ""
	@echo "Other Targets:"
	@echo "  everything       - Build everything (applications + Linux image)"
	@echo "  clean            - Remove all build artifacts"
	@echo "  clean-all        - Deep clean (removes kernel source too)"
	@echo "  help             - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  # Build everything (applications + Linux image, requires root)"
	@echo "  sudo make everything"
	@echo ""
	@echo "  # Build applications only (fast)"
	@echo "  make"
	@echo ""
	@echo "  # Build kernel only"
	@echo "  make kernel"
	@echo ""
	@echo "  # Build complete Linux image (requires root)"
	@echo "  sudo make linux-image"
	@echo ""
	@echo "  # Clean all build artifacts"
	@echo "  make clean"
	@echo ""
	@echo "  # Deep clean (removes kernel source too)"
	@echo "  sudo make clean-all"
	@echo ""
	@echo "  # Build from specific component directory"
	@echo "  cd linux_image && sudo make all"
	@echo "  cd applications && make"
	@echo ""
	@echo "Cross-Compilation:"
	@echo "  Toolchain: $(CROSS_COMPILE)"
	@echo "  Override:  make CROSS_COMPILE=arm-none-linux-gnueabihf-"

# ============================================================================
# Linux Image Targets
# ============================================================================

linux-image:
	@echo -e "$(BLUE)Building complete Linux image...$(NC)"
	@if [ -f "$(LINUX_IMAGE_DIR)/Makefile" ]; then \
		if [ "$(shell id -u)" -eq 0 ]; then \
			$(MAKE) -C $(LINUX_IMAGE_DIR) CROSS_COMPILE=$(CROSS_COMPILE) all; \
		else \
			echo -e "$(YELLOW)Linux image build requires root access$(NC)"; \
			echo "Run with: sudo make linux-image"; \
			sudo $(MAKE) -C $(LINUX_IMAGE_DIR) CROSS_COMPILE=$(CROSS_COMPILE) all; \
		fi \
	else \
		echo "ERROR: Linux image Makefile not found"; \
		exit 1; \
	fi

kernel:
	@echo -e "$(YELLOW)Building Linux kernel...$(NC)"
	@if [ -f "$(LINUX_IMAGE_DIR)/Makefile" ]; then \
		$(MAKE) -C $(LINUX_IMAGE_DIR) CROSS_COMPILE=$(CROSS_COMPILE) kernel; \
	else \
		echo "ERROR: Linux image Makefile not found"; \
		exit 1; \
	fi

rootfs:
	@echo -e "$(YELLOW)Building root filesystem...$(NC)"
	@echo -e "$(YELLOW)Note: Rootfs build requires root access$(NC)"
	@if [ -f "$(LINUX_IMAGE_DIR)/Makefile" ]; then \
		if [ "$(shell id -u)" -eq 0 ]; then \
			$(MAKE) -C $(LINUX_IMAGE_DIR) CROSS_COMPILE=$(CROSS_COMPILE) rootfs; \
		else \
			echo "Run with: sudo make rootfs"; \
			sudo $(MAKE) -C $(LINUX_IMAGE_DIR) CROSS_COMPILE=$(CROSS_COMPILE) rootfs; \
		fi \
	else \
		echo "ERROR: Linux image Makefile not found"; \
		exit 1; \
	fi

sd-image: kernel rootfs
	@echo -e "$(YELLOW)Creating SD card image...$(NC)"
	@if [ -f "$(LINUX_IMAGE_DIR)/Makefile" ]; then \
		if [ "$(shell id -u)" -eq 0 ]; then \
			$(MAKE) -C $(LINUX_IMAGE_DIR) CROSS_COMPILE=$(CROSS_COMPILE) sd-image; \
		else \
			echo "Image creation requires root access"; \
			echo "Run with: sudo make sd-image"; \
			sudo $(MAKE) -C $(LINUX_IMAGE_DIR) CROSS_COMPILE=$(CROSS_COMPILE) sd-image; \
		fi \
	else \
		echo "ERROR: Linux image Makefile not found"; \
		exit 1; \
	fi

# ============================================================================
# Application Targets
# ============================================================================

applications: calculator_test led_examples
	@echo -e "$(GREEN)All applications built$(NC)"

calculator_test:
	@echo -e "$(YELLOW)Building calculator test suite...$(NC)"
	@if [ -f "$(APPLICATIONS_DIR)/Makefile" ]; then \
		$(MAKE) -C $(APPLICATIONS_DIR) CROSS_COMPILE=$(CROSS_COMPILE) calculator_test; \
	else \
		echo "ERROR: Applications Makefile not found"; \
		exit 1; \
	fi

led_examples:
	@echo -e "$(YELLOW)Building LED examples...$(NC)"
	@if [ -f "$(APPLICATIONS_DIR)/Makefile" ]; then \
		$(MAKE) -C $(APPLICATIONS_DIR) CROSS_COMPILE=$(CROSS_COMPILE) led_examples; \
	else \
		echo "ERROR: Applications Makefile not found"; \
		exit 1; \
	fi

# ============================================================================
# Driver Targets
# ============================================================================

drivers:
	@echo -e "$(YELLOW)Driver integration tools are in drivers/integration/$(NC)"
	@if [ -f "$(DRIVERS_DIR)/Makefile" ]; then \
		$(MAKE) -C $(DRIVERS_DIR) integration; \
	fi

# ============================================================================
# Everything Target - Build All Components
# ============================================================================

everything:
	@echo -e "$(BLUE)===========================================$(NC)"
	@echo -e "$(BLUE)Building Everything (Applications + Linux Image)$(NC)"
	@echo -e "$(BLUE)===========================================$(NC)"
	@echo ""
	@echo -e "$(YELLOW)Step 1/2: Building applications...$(NC)"
	@$(MAKE) applications
	@echo ""
	@echo -e "$(YELLOW)Step 2/2: Building Linux image (kernel + rootfs + SD card)...$(NC)"
	@echo -e "$(YELLOW)This may take 30-60 minutes...$(NC)"
	@$(MAKE) linux-image
	@echo ""
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Everything built successfully!$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"

# ============================================================================
# Clean Targets
# ============================================================================

clean:
	@echo -e "$(YELLOW)Cleaning all HPS build artifacts...$(NC)"
	@echo -e "$(YELLOW)Cleaning Linux image build artifacts...$(NC)"
	@if [ -f "$(LINUX_IMAGE_DIR)/Makefile" ]; then \
		$(MAKE) -C $(LINUX_IMAGE_DIR) clean || true; \
	else \
		echo -e "$(GREEN)✓ Linux image Makefile not found, skipping$(NC)"; \
	fi
	@echo -e "$(YELLOW)Cleaning application build artifacts...$(NC)"
	@if [ -f "$(APPLICATIONS_DIR)/Makefile" ]; then \
		$(MAKE) -C $(APPLICATIONS_DIR) clean || true; \
	else \
		echo -e "$(GREEN)✓ Applications Makefile not found, skipping$(NC)"; \
	fi
	@echo -e "$(YELLOW)Cleaning driver build artifacts...$(NC)"
	@if [ -f "$(DRIVERS_DIR)/Makefile" ]; then \
		$(MAKE) -C $(DRIVERS_DIR) clean || true; \
	else \
		echo -e "$(GREEN)✓ Drivers Makefile not found, skipping$(NC)"; \
	fi
	@echo -e "$(YELLOW)Removing top-level build directory...$(NC)"
	@rm -rf build
	@echo -e "$(GREEN)✓ Clean complete$(NC)"

clean-all: clean
	@echo -e "$(YELLOW)===========================================$(NC)"
	@echo -e "$(YELLOW)Performing deep clean...$(NC)"
	@echo -e "$(YELLOW)===========================================$(NC)"
	@echo -e "$(YELLOW)Step 1/2: Removing kernel source...$(NC)"
	@if [ -f "$(LINUX_IMAGE_DIR)/kernel/Makefile" ]; then \
		$(MAKE) -C $(LINUX_IMAGE_DIR)/kernel kernel-distclean || true; \
	else \
		echo -e "$(GREEN)✓ Kernel Makefile not found, skipping$(NC)"; \
	fi
	@echo ""
	@echo -e "$(YELLOW)Step 2/2: Cleaning debootstrap cache...$(NC)"
	@if [ -d "/var/cache/debootstrap" ]; then \
		CACHE_SIZE=$$(du -sh /var/cache/debootstrap 2>/dev/null | cut -f1 || echo "unknown"); \
		echo -e "$(YELLOW)Debootstrap cache size: $$CACHE_SIZE$(NC)"; \
		sudo rm -rf /var/cache/debootstrap/* 2>/dev/null || true; \
		echo -e "$(GREEN)✓ Debootstrap cache cleaned$(NC)"; \
	else \
		echo -e "$(GREEN)✓ Debootstrap cache not found (already clean)$(NC)"; \
	fi
	@echo ""
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Deep clean complete!$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Note: Kernel source will be re-downloaded on next build$(NC)"
