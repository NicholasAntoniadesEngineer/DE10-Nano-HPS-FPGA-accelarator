# ============================================================================
# Linux Kernel Build System for DE10-Nano
# ============================================================================
# Automated kernel build with FPGA driver integration
# ============================================================================

SHELL := /bin/bash

# Configuration
KERNEL_VERSION ?= 5.15.0
KERNEL_REPO ?= https://github.com/altera-opensource/linux-socfpga.git
# Try common branch names - will fallback if not found
KERNEL_BRANCH ?= socfpga-5.15
KERNEL_DIR := $(CURDIR)/linux-socfpga
KERNEL_BUILD_DIR := $(CURDIR)/build
KERNEL_CONFIG := $(CURDIR)/configs/socfpga_defconfig

# Source files that trigger kernel rebuild when changed
KERNEL_SOURCES := $(KERNEL_CONFIG) \
                  $(HPS_DIR)/drivers/integration/integrate_linux_driver.sh \
                  $(wildcard $(HPS_DIR)/applications/calculator_test/*.c) \
                  $(wildcard $(HPS_DIR)/applications/calculator_test/*.h)

# Cross-compilation
CROSS_COMPILE ?= arm-linux-gnueabihf-
ARCH := arm

# Paths
LINUX_IMAGE_DIR := $(abspath $(CURDIR)/..)
HPS_DIR := $(abspath $(LINUX_IMAGE_DIR)/..)
REPO_ROOT := $(abspath $(HPS_DIR)/..)
FPGA_DIR := $(REPO_ROOT)/FPGA
DRIVER_INTEGRATION := $(HPS_DIR)/drivers/integration/integrate_linux_driver.sh

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

.PHONY: all help kernel-download kernel-config kernel-build kernel-modules kernel-clean kernel-integrate-driver check-rebuild rebuild force-rebuild

all: kernel-build
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Kernel build complete$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Kernel image: $(KERNEL_BUILD_DIR)/arch/arm/boot/zImage$(NC)"
	@echo -e "$(GREEN)Device tree:  $(KERNEL_BUILD_DIR)/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb$(NC)"
	@echo ""
	@echo -e "$(YELLOW)Tip: Use 'make check-rebuild' to check if rebuild is needed$(NC)"

help:
	@echo "Linux Kernel Build System for DE10-Nano"
	@echo "========================================"
	@echo ""
	@echo "Targets:"
	@echo "  all                 - Build complete kernel (default, incremental)"
	@echo "  kernel-download    - Download/clone kernel source"
	@echo "  kernel-config      - Configure kernel"
	@echo "  kernel-build       - Build kernel (zImage, dtbs, modules)"
	@echo "  kernel-modules     - Build kernel modules only"
	@echo "  kernel-integrate-driver - Integrate calculator driver"
	@echo "  check-rebuild      - Check if kernel rebuild is needed (dry-run)"
	@echo "  rebuild            - Force rebuild kernel from scratch"
	@echo "  force-rebuild      - Alias for rebuild"
	@echo "  kernel-clean       - Clean build artifacts"
	@echo "  help               - Show this help message"
	@echo ""
	@echo "Configuration:"
	@echo "  KERNEL_VERSION=$(KERNEL_VERSION)"
	@echo "  KERNEL_BRANCH=$(KERNEL_BRANCH)"
	@echo "  CROSS_COMPILE=$(CROSS_COMPILE)"
	@echo "  ARCH=$(ARCH)"
	@echo ""
	@echo "Output:"
	@echo "  Kernel: $(KERNEL_BUILD_DIR)/arch/arm/boot/zImage"
	@echo "  DTB:    $(KERNEL_BUILD_DIR)/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb"

# Check if kernel rebuild is needed by comparing timestamps
check-rebuild:
	@if [ ! -f "$(KERNEL_BUILD_DIR)/arch/arm/boot/zImage" ]; then \
		echo -e "$(YELLOW)Rebuild needed: kernel image does not exist$(NC)"; \
		exit 0; \
	fi; \
	needs_rebuild=0; \
	for src in $(KERNEL_SOURCES); do \
		if [ -f "$$src" ] && [ "$$src" -nt "$(KERNEL_BUILD_DIR)/arch/arm/boot/zImage" ]; then \
			echo -e "$(YELLOW)Rebuild needed: $$src is newer than kernel image$(NC)"; \
			needs_rebuild=1; \
		fi; \
	done; \
	if [ $$needs_rebuild -eq 0 ]; then \
		echo -e "$(GREEN)No rebuild needed: kernel is up-to-date$(NC)"; \
	fi

# Force rebuild - always rebuilds from scratch
rebuild: kernel-clean
	@$(MAKE) kernel-build FORCE_REBUILD=1

force-rebuild: rebuild

kernel-download: $(KERNEL_DIR)/.git/config
	@echo -e "$(GREEN)Kernel source ready$(NC)"

$(KERNEL_DIR)/.git/config:
	@echo -e "$(YELLOW)Downloading kernel source...$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Kernel Source (Download/Update)$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@set -e; \
		tmp_check="../scripts/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\r' < "../scripts/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "kernel sources (git)" --url "https://github.com" --url "https://raw.githubusercontent.com"
	@if [ -d "$(KERNEL_DIR)" ] && [ -d "$(KERNEL_DIR)/.git" ]; then \
		echo -e "$(YELLOW)Kernel directory exists, updating...$(NC)"; \
		cd $(KERNEL_DIR) && \
		if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
			echo -e "$(RED)ERROR: $(KERNEL_DIR) exists but is not a git working tree$(NC)"; \
			echo -e "$(YELLOW)Fix: remove $(KERNEL_DIR) and rerun: make kernel-distclean && make kernel-download$(NC)"; \
			exit 1; \
		fi; \
		if ! git remote get-url origin >/dev/null 2>&1; then \
			echo -e "$(YELLOW)Kernel remote 'origin' not configured. Setting origin to: $(KERNEL_REPO)$(NC)"; \
			git remote add origin $(KERNEL_REPO) 2>/dev/null || git remote set-url origin $(KERNEL_REPO) 2>/dev/null || true; \
		fi; \
		git fetch origin --tags || true; \
		BRANCH=""; \
		for b in $(KERNEL_BRANCH) socfpga-5.15 socfpga-5.10 master main; do \
			if git show-ref --verify --quiet refs/heads/$$b 2>/dev/null; then \
				BRANCH="$$b"; \
				break; \
			fi; \
			if git remote get-url origin >/dev/null 2>&1 && git show-ref --verify --quiet refs/remotes/origin/$$b 2>/dev/null; then \
				BRANCH="$$b"; \
				break; \
			fi; \
		done; \
		if [ -z "$$BRANCH" ]; then \
			echo -e "$(YELLOW)No matching branch found, checking available branches...$(NC)"; \
			if git remote get-url origin >/dev/null 2>&1; then \
				BRANCH=$$(git branch -r | grep -E "(socfpga|master|main)" | head -1 | sed 's|origin/||' | tr -d ' '); \
			fi; \
			if [ -z "$$BRANCH" ]; then \
				BRANCH=$$(git branch --list | head -1 | tr -d ' *'); \
				if [ -z "$$BRANCH" ] && git remote get-url origin >/dev/null 2>&1; then \
					BRANCH=$$(git branch -r | head -1 | sed 's|origin/||' | tr -d ' '); \
				fi; \
			fi; \
		fi; \
		if [ -n "$$BRANCH" ]; then \
			echo -e "$(GREEN)Checking out branch: $$BRANCH$(NC)"; \
			git checkout -f $$BRANCH 2>/dev/null || \
			(git remote get-url origin >/dev/null 2>&1 && git checkout -f -b $$BRANCH origin/$$BRANCH 2>/dev/null) || \
			(echo -e "$(YELLOW)Warning: Could not checkout $$BRANCH, trying to reset...$(NC)" && \
			 (git remote get-url origin >/dev/null 2>&1 && git reset --hard origin/$$BRANCH 2>/dev/null) || true); \
			(git remote get-url origin >/dev/null 2>&1 && git pull) || true; \
		fi; \
		if [ ! -d "$(KERNEL_DIR)/arch" ] || [ ! -f "$(KERNEL_DIR)/Makefile" ]; then \
			echo -e "$(YELLOW)Kernel files not checked out, forcing checkout...$(NC)"; \
			git reset --hard HEAD || git checkout -f HEAD || true; \
		fi; \
	else \
		echo -e "$(YELLOW)Cloning kernel repository...$(NC)"; \
		rm -rf $(KERNEL_DIR); \
		git clone $(KERNEL_REPO) $(KERNEL_DIR) || \
		(echo -e "$(RED)ERROR: Failed to clone kernel. Check network connection and repository URL.$(NC)" && exit 1); \
		cd $(KERNEL_DIR) && \
		BRANCH=""; \
		for b in $(KERNEL_BRANCH) socfpga-5.15 socfpga-5.10 master main; do \
			if git show-ref --verify --quiet refs/remotes/origin/$$b 2>/dev/null; then \
				BRANCH="$$b"; \
				break; \
			fi; \
		done; \
		if [ -z "$$BRANCH" ]; then \
			BRANCH=$$(git branch -r | grep -E "(socfpga|master|main)" | head -1 | sed 's|origin/||' | tr -d ' '); \
			if [ -z "$$BRANCH" ]; then \
				BRANCH=$$(git branch -r | head -1 | sed 's|origin/||' | tr -d ' '); \
			fi; \
		fi; \
		if [ -n "$$BRANCH" ]; then \
			echo -e "$(GREEN)Checking out branch: $$BRANCH$(NC)"; \
			git checkout -f $$BRANCH || \
			git checkout -f -b $$BRANCH origin/$$BRANCH || \
			(echo -e "$(RED)ERROR: Failed to checkout branch $$BRANCH$(NC)" && exit 1); \
		fi; \
	fi
	@if [ ! -d "$(KERNEL_DIR)/arch" ] || [ ! -f "$(KERNEL_DIR)/Makefile" ]; then \
		echo -e "$(RED)ERROR: Kernel source appears incomplete after checkout$(NC)"; \
		echo -e "$(YELLOW)Kernel directory: $(KERNEL_DIR)$(NC)"; \
		echo -e "$(YELLOW)Contents:$$(ls -la $(KERNEL_DIR) | head -10)$(NC)"; \
		echo -e "$(YELLOW)Try: cd $(KERNEL_DIR) && git status && git checkout -f HEAD$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(GREEN)Kernel source downloaded and checked out$(NC)"
	@cd $(KERNEL_DIR) && echo -e "$(GREEN)Current branch: $$(git branch --show-current)$(NC)"
	@cd $(KERNEL_DIR) && echo -e "$(GREEN)Kernel files verified: arch/ and Makefile exist$(NC)"

kernel-config: $(KERNEL_BUILD_DIR)/.config
	@echo -e "$(GREEN)Kernel configured$(NC)"

$(KERNEL_BUILD_DIR)/.config: kernel-download
	@echo -e "$(YELLOW)Configuring kernel...$(NC)"
	@mkdir -p $(KERNEL_BUILD_DIR)
	@echo -e "$(YELLOW)Verifying kernel source structure...$(NC)"
	@cd $(KERNEL_DIR) && \
	if [ ! -d "arch" ]; then \
		echo -e "$(RED)ERROR: Kernel source appears incomplete - 'arch' directory not found$(NC)"; \
		echo -e "$(YELLOW)Kernel directory: $(KERNEL_DIR)$(NC)"; \
		echo -e "$(YELLOW)Contents:$$(ls -la | head -10)$(NC)"; \
		echo -e "$(YELLOW)Try: make kernel-distclean && make kernel-download$(NC)"; \
		exit 1; \
	fi; \
	echo -e "$(YELLOW)Searching for suitable defconfig...$(NC)"; \
	DEFCONFIG=""; \
	CONFIG_DIR=""; \
	if [ -d "arch/$(ARCH)/configs" ]; then \
		CONFIG_DIR="arch/$(ARCH)/configs"; \
		for cfg in socfpga_cyclone5_de10_nano socfpga_cyclone5 socfpga_de10_nano socfpga; do \
			if [ -f "$$CONFIG_DIR/$${cfg}_defconfig" ]; then \
				DEFCONFIG="$${cfg}_defconfig"; \
				echo -e "$(GREEN)Found defconfig: $$DEFCONFIG$(NC)"; \
				break; \
			fi; \
		done; \
		if [ -z "$$DEFCONFIG" ]; then \
			echo -e "$(YELLOW)No socfpga defconfig found, trying generic ARM defconfig...$(NC)"; \
			if [ -f "$$CONFIG_DIR/multi_v7_defconfig" ]; then \
				DEFCONFIG="multi_v7_defconfig"; \
				echo -e "$(GREEN)Using generic ARM defconfig: $$DEFCONFIG$(NC)"; \
			elif [ -f "$$CONFIG_DIR/vexpress_defconfig" ]; then \
				DEFCONFIG="vexpress_defconfig"; \
				echo -e "$(GREEN)Using generic ARM defconfig: $$DEFCONFIG$(NC)"; \
			fi; \
		fi; \
	else \
		echo -e "$(YELLOW)arch/$(ARCH)/configs not found, checking for alternative structure...$(NC)"; \
		echo -e "$(YELLOW)Available arch directories:$$(ls -d arch/*/ 2>/dev/null | sed 's|arch/||;s|/||' || echo ' (none)')$(NC)"; \
	fi; \
	if [ -z "$$DEFCONFIG" ]; then \
		echo -e "$(RED)ERROR: No suitable defconfig found$(NC)"; \
		if [ -n "$$CONFIG_DIR" ] && [ -d "$$CONFIG_DIR" ]; then \
			echo -e "$(YELLOW)Available defconfigs in $$CONFIG_DIR:$(NC)"; \
			ls -1 $$CONFIG_DIR/*defconfig 2>/dev/null | head -20 | sed 's|.*/||' || echo "  (none found)"; \
		else \
			echo -e "$(RED)ERROR: Cannot find configs directory$(NC)"; \
			echo -e "$(YELLOW)Kernel source structure:$(NC)"; \
			find arch -type d -name configs 2>/dev/null | head -5 || echo "  (no configs directories found)"; \
		fi; \
		echo -e "$(YELLOW)Try manually: cd $(KERNEL_DIR) && make ARCH=$(ARCH) help$(NC)"; \
		exit 1; \
	fi; \
	echo -e "$(YELLOW)Configuring kernel with: $$DEFCONFIG$(NC)"; \
	make O=$(abspath $(KERNEL_BUILD_DIR)) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) $$DEFCONFIG || \
	(echo -e "$(RED)ERROR: Failed to configure kernel with $$DEFCONFIG$(NC)" && exit 1)
	@if [ -f "$(KERNEL_BUILD_DIR)/.config" ]; then \
		echo -e "$(GREEN)Kernel configuration complete$(NC)"; \
		echo -e "$(GREEN)Config file: $(KERNEL_BUILD_DIR)/.config$(NC)"; \
	else \
		echo -e "$(RED)ERROR: Kernel configuration failed - .config not created$(NC)"; \
		exit 1; \
	fi

kernel-integrate-driver: kernel-config
	@echo -e "$(YELLOW)Integrating calculator driver...$(NC)"
	@if [ -f "$(DRIVER_INTEGRATION)" ]; then \
		bash $(DRIVER_INTEGRATION) -k $(KERNEL_DIR) -t userspace || \
		(echo -e "$(YELLOW)Driver integration script not available, skipping...$(NC)"); \
	else \
		echo -e "$(YELLOW)Driver integration script not found, skipping...$(NC)"; \
	fi

kernel-build: kernel-config kernel-integrate-driver
	@needs_rebuild=0; \
	if [ ! -f "$(KERNEL_BUILD_DIR)/arch/arm/boot/zImage" ]; then \
		echo -e "$(YELLOW)Building kernel: image does not exist$(NC)"; \
		needs_rebuild=1; \
	else \
		for src in $(KERNEL_SOURCES); do \
			if [ -f "$$src" ] && [ "$$src" -nt "$(KERNEL_BUILD_DIR)/arch/arm/boot/zImage" ]; then \
				echo -e "$(YELLOW)Rebuild triggered by: $$src$(NC)"; \
				needs_rebuild=1; \
				break; \
			fi; \
		done; \
	fi; \
	if [ "$(FORCE_REBUILD)" = "1" ]; then \
		echo -e "$(YELLOW)Force rebuild requested$(NC)"; \
		needs_rebuild=1; \
	fi; \
	if [ $$needs_rebuild -eq 0 ]; then \
		echo -e "$(GREEN)===========================================$(NC)"; \
		echo -e "$(GREEN)Kernel is up-to-date - skipping build$(NC)"; \
		echo -e "$(GREEN)===========================================$(NC)"; \
		echo -e "$(GREEN)Existing image: $(KERNEL_BUILD_DIR)/arch/arm/boot/zImage$(NC)"; \
		image_date=$$(date -r "$(KERNEL_BUILD_DIR)/arch/arm/boot/zImage" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$(KERNEL_BUILD_DIR)/arch/arm/boot/zImage" 2>/dev/null | cut -d. -f1); \
		echo -e "$(GREEN)Built on: $$image_date$(NC)"; \
		exit 0; \
	fi; \
	echo -e "$(YELLOW)Building kernel...$(NC)"; \
	echo -e "$(YELLOW)This may take 10-30 minutes...$(NC)"; \
	echo -e "$(YELLOW)Target: ARM Cortex-A9 (ARMv7-A) for DE10-Nano$(NC)"; \
	echo -e "$(YELLOW)Note: Cleaning build artifacts to ensure correct architecture flags...$(NC)"
	@rm -rf $(KERNEL_BUILD_DIR)/arch/arm/kernel $(KERNEL_BUILD_DIR)/arch/arm/mm $(KERNEL_BUILD_DIR)/kernel
	@echo -e "$(YELLOW)Patching kernel Makefile to use Cortex-A9 flags...$(NC)"
	@cd $(KERNEL_DIR)/arch/arm && \
	if ! grep -q "Wa,-mcpu=cortex-a9" Makefile; then \
		sed -i 's/-Wa$$(comma)-march=armv7-a/-Wa$$(comma)-march=armv7-a -Wa$$(comma)-mcpu=cortex-a9/g' Makefile || \
		sed -i 's/-Wa,-march=armv7-a/-Wa,-march=armv7-a -Wa,-mcpu=cortex-a9/g' Makefile || true; \
	fi && \
	if ! grep -q "mtune=cortex-a9" Makefile; then \
		sed -i '/^KBUILD_CFLAGS[[:space:]]*+=/s/$$/ -mtune=cortex-a9 -mfpu=vfpv3/' Makefile && \
		sed -i '/^KBUILD_AFLAGS[[:space:]]*+=/s/$$/ -mtune=cortex-a9 -mfpu=vfpv3/' Makefile || true; \
	fi
	@cd $(KERNEL_DIR) && \
	make O=$(abspath $(KERNEL_BUILD_DIR)) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) \
		zImage modules -j$$(nproc 2>/dev/null || echo 4) && \
	echo -e "$(YELLOW)Note: DTB generation skipped (not required for current build)$(NC)"
	@echo -e "$(GREEN)Kernel build complete$(NC)"
	@if [ -f "$(KERNEL_BUILD_DIR)/arch/arm/boot/zImage" ]; then \
		echo -e "$(GREEN)[OK] Kernel image: $(KERNEL_BUILD_DIR)/arch/arm/boot/zImage$(NC)"; \
	else \
		echo -e "$(RED)[ERROR] Kernel image not found!$(NC)"; \
		exit 1; \
	fi
	@DTB_FOUND=""; \
	for dtb in socfpga_cyclone5_de10_nano.dtb socfpga_cyclone5_de0_nano_soc.dtb socfpga_cyclone5_socdk.dtb; do \
		if [ -f "$(KERNEL_BUILD_DIR)/arch/arm/boot/dts/$$dtb" ]; then \
			DTB_FOUND="$$dtb"; \
			break; \
		fi; \
	done; \
	if [ -n "$$DTB_FOUND" ]; then \
		echo -e "$(GREEN)[OK] Device tree: $(KERNEL_BUILD_DIR)/arch/arm/boot/dts/$$DTB_FOUND$(NC)"; \
	else \
		echo -e "$(YELLOW)[WARN] Device tree not found (check build/arch/arm/boot/dts/ for available DTBs)$(NC)"; \
	fi

kernel-modules: kernel-build
	@echo -e "$(GREEN)Kernel modules built$(NC)"

kernel-clean:
	@echo -e "$(YELLOW)Cleaning kernel build...$(NC)"
	@if [ -d "$(KERNEL_BUILD_DIR)" ]; then \
		rm -rf $(KERNEL_BUILD_DIR); \
		echo -e "$(GREEN)Build directory cleaned$(NC)"; \
	fi
	@echo -e "$(GREEN)Clean complete$(NC)"

kernel-distclean: kernel-clean
	@echo -e "$(YELLOW)Removing kernel source...$(NC)"
	@if [ -d "$(KERNEL_DIR)" ]; then \
		echo -e "$(YELLOW)Calculating kernel source size...$(NC)"; \
		KERNEL_SIZE=$$(du -sh "$(KERNEL_DIR)" 2>/dev/null | cut -f1 || echo "unknown"); \
		echo -e "$(YELLOW)Removing kernel source directory (size: $$KERNEL_SIZE)...$(NC)"; \
		echo -e "$(YELLOW)This may take a few minutes for large directories...$(NC)"; \
		rm -rf $(KERNEL_DIR); \
		echo -e "$(GREEN)[OK] Kernel source removed$(NC)"; \
	else \
		echo -e "$(GREEN)[OK] Kernel source directory not found (already clean)$(NC)"; \
	fi
