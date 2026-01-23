# ============================================================================
# Linux Image Build System for DE10-Nano
# ============================================================================
# Builds kernel, rootfs, and creates SD card image
# ============================================================================

SHELL := /bin/bash

# Paths
LINUX_IMAGE_DIR := $(CURDIR)
HPS_DIR := $(abspath $(CURDIR)/..)
REPO_ROOT := $(abspath $(HPS_DIR)/..)
FPGA_DIR := $(REPO_ROOT)/FPGA

# Configuration
KERNEL_DIR := $(LINUX_IMAGE_DIR)/kernel
ROOTFS_DIR := $(LINUX_IMAGE_DIR)/rootfs
SCRIPTS_DIR := $(LINUX_IMAGE_DIR)/scripts
BUILD_DIR := $(LINUX_IMAGE_DIR)/build
DEPS_PACKAGES := debootstrap qemu-user-static debian-archive-keyring ca-certificates gnupg wget curl parted dosfstools e2fsprogs util-linux u-boot-tools

# FPGA project files (override if you use a different design)
FPGA_QUARTUS_QPF ?= quartus/DE10_NANO_SoC_GHRD.qpf
FPGA_QSYS_FILE ?= quartus/qsys/soc_system.qsys

# Cross-compilation
CROSS_COMPILE ?= arm-linux-gnueabihf-
ARCH := arm

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

.PHONY: all help deps deps-check fpga kernel rootfs linux-image sd-image clean

all: linux-image
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Linux image build complete$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"

help:
	@echo "Linux Image Build System for DE10-Nano"
	@echo "======================================"
	@echo ""
	@echo "Targets:"
	@echo "  all           - Build complete Linux image (kernel + rootfs + SD image)"
	@echo "  deps          - Install build-host dependencies (Debian/Ubuntu/WSL)"
	@echo "  deps-check    - Verify build-host dependencies are installed"
	@echo "  fpga          - Build FPGA artifacts needed for SD image (preloader, U-Boot, DTB, RBF)"
	@echo "  kernel        - Build Linux kernel only"
	@echo "  rootfs        - Build root filesystem only (requires root)"
	@echo "  linux-image   - Build complete Linux image (FPGA + kernel + rootfs + SD image)"
	@echo "  sd-image      - Create SD card image only (requires kernel and rootfs)"
	@echo "  clean         - Clean all build artifacts"
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make kernel        # Build kernel only"
	@echo "  sudo make rootfs   # Build rootfs only"
	@echo "  sudo make all      # Build complete image"
	@echo ""
	@echo "Deployment:"
	@echo "  cd scripts"
	@echo "  sudo ./deploy_image.sh /dev/sdX"

deps:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Installing Build-Host Dependencies$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Installing build-host dependencies...$(NC)"
	@if ! command -v apt-get >/dev/null 2>&1; then \
		echo "ERROR: apt-get not found. Install dependencies manually for your distro:"; \
		echo "  debootstrap, qemu-user-static, debian-archive-keyring, ca-certificates, gnupg (gpgv), wget/curl, parted, dosfstools, e2fsprogs, util-linux, u-boot-tools"; \
		exit 1; \
	fi
	@set -e; \
		tmp_check="$(SCRIPTS_DIR)/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\r' < "$(SCRIPTS_DIR)/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "apt repositories (build-host dependencies)" --url "https://deb.debian.org" --url "https://security.debian.org"
	@if [ "$(shell id -u)" -ne 0 ]; then \
		sudo apt-get update && sudo apt-get install -y $(DEPS_PACKAGES); \
	else \
		apt-get update && apt-get install -y $(DEPS_PACKAGES); \
	fi
	@echo -e "$(GREEN)Dependencies installed$(NC)"

deps-check:
	@bash -lc '\
		set -e; \
		missing=0; \
		command -v debootstrap >/dev/null 2>&1 || { echo "Missing: debootstrap"; missing=1; }; \
		( command -v qemu-debootstrap >/dev/null 2>&1 || command -v qemu-arm-static >/dev/null 2>&1 ) || { echo "Missing: qemu-user-static (qemu-arm-static) or qemu-debootstrap"; missing=1; }; \
		( command -v wget >/dev/null 2>&1 || command -v curl >/dev/null 2>&1 ) || { echo "Missing: wget or curl"; missing=1; }; \
		command -v gpgv >/dev/null 2>&1 || { echo "Missing: gpgv (install gnupg)"; missing=1; }; \
		test -f /usr/share/keyrings/debian-archive-keyring.gpg || { echo "Missing: /usr/share/keyrings/debian-archive-keyring.gpg (install debian-archive-keyring)"; missing=1; }; \
		for cmd in parted mkfs.vfat mkfs.ext4 losetup dd; do command -v "$$cmd" >/dev/null 2>&1 || { echo "Missing: $$cmd"; missing=1; }; done; \
		if [ $$missing -ne 0 ]; then \
			echo ""; \
			echo "Install prerequisites with:"; \
			echo "  make deps"; \
			exit 1; \
		fi; \
		echo "All build-host dependencies satisfied"; \
	'

fpga:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)FPGA / Preloader / U-Boot / DTB / RBF$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Checking for existing FPGA artifacts...$(NC)"
	@bash -c '\
		echo "Looking for FPGA bitstream (RBF) files..."; \
		latest_rbf=""; \
		latest_time=0; \
		\
		# Check repo root build directory (primary location) \
		if [ -d "../../build/output_files" ]; then \
			for rbf in ../../build/output_files/*.rbf; do \
				if [ -f "$$rbf" ] && [ -s "$$rbf" ]; then \
					file_time=$$(stat -c %Y "$$rbf" 2>/dev/null || stat -f %m "$$rbf" 2>/dev/null || echo 0); \
					if [ $$file_time -gt $$latest_time ]; then \
						latest_rbf="$$rbf"; \
						latest_time=$$file_time; \
					fi; \
				fi; \
			done; \
		fi; \
		\
		# Check FPGA build directory (secondary location) \
		if [ -d "$(FPGA_DIR)/build/output_files" ]; then \
			for rbf in $(FPGA_DIR)/build/output_files/*.rbf; do \
				if [ -f "$$rbf" ] && [ -s "$$rbf" ]; then \
					file_time=$$(stat -c %Y "$$rbf" 2>/dev/null || stat -f %m "$$rbf" 2>/dev/null || echo 0); \
					if [ $$file_time -gt $$latest_time ]; then \
						latest_rbf="$$rbf"; \
						latest_time=$$file_time; \
					fi; \
				fi; \
			done; \
		fi; \
		\
		if [ -n "$$latest_rbf" ]; then \
			rbf_size=$$(du -h "$$latest_rbf" | cut -f1); \
			rbf_date=$$(date -r "$$latest_rbf" "+%Y-%m-%d %H:%M"); \
			echo "[OK] Found FPGA bitstream: $$latest_rbf"; \
			echo "  Size: $$rbf_size | Modified: $$rbf_date"; \
			\
			# Check if RBF is older than 24 hours \
			current_time=$$(date +%s); \
			age_hours=$$(( (current_time - latest_time) / 3600 )); \
			if [ $$age_hours -gt 24 ]; then \
				echo "[WARN] RBF file is $$age_hours hours old"; \
				echo "   Consider rebuilding FPGA bitstream if design changes were made"; \
			fi; \
		else \
			echo "[NOT FOUND] No FPGA bitstream (RBF) files found"; \
			echo "  Searched locations:"; \
			echo "    - ../../build/output_files/*.rbf"; \
			echo "    - $(FPGA_DIR)/build/output_files/*.rbf"; \
			echo "  To build FPGA bitstream: cd $(FPGA_DIR) && make rbf"; \
			echo "  Continuing with SD image build (will fail if RBF required)..."; \
		fi; \
	'
	@echo -e "$(YELLOW)Verifying required artifacts for SD image...$(NC)"
	@bash -lc '\
		set -e; \
		missing=0; \
		preloader="$${PRELOADER_BIN:-$(HPS_DIR)/preloader/preloader-mkpimage.bin}"; \
		uboot="$${UBOOT_IMG:-$(HPS_DIR)/preloader/uboot-socfpga/u-boot.img}"; \
		if [ ! -f "$$preloader" ]; then echo "ERROR: Preloader not found: $$preloader"; missing=1; fi; \
		if [ ! -f "$$uboot" ]; then echo "ERROR: U-Boot not found: $$uboot"; missing=1; fi; \
		if ! ls "$(FPGA_DIR)/generated/"*.dtb >/dev/null 2>&1; then echo "WARNING: No DTB found under: $(FPGA_DIR)/generated/ (kernel DTB may be used instead)"; fi; \
		if ! ls "$(FPGA_DIR)/build/output_files/"*.rbf >/dev/null 2>&1 && ! ls "$(REPO_ROOT)/build/output_files/"*.rbf >/dev/null 2>&1; then \
			echo "ERROR: No RBF found under: $(FPGA_DIR)/build/output_files/ or $(REPO_ROOT)/build/output_files/"; \
			missing=1; \
		fi; \
		if [ $$missing -ne 0 ]; then \
			echo ""; \
			echo "FPGA artifacts are missing; SD image creation cannot proceed."; \
			echo "Common causes:"; \
			echo "  - Quartus not installed/in PATH (needed for RBF)"; \
			echo "  - SoC EDS not installed or SOCEDS_DEST_ROOT not set (needed for preloader/U-Boot)"; \
			echo ""; \
			echo "Try:"; \
			echo "  cd FPGA && make check-tools"; \
			echo "  # If SoC EDS is installed: export SOCEDS_DEST_ROOT=..."; \
			echo "  cd FPGA && make preloader uboot rbf"; \
			echo ""; \
			echo "Or provide prebuilt bootloader binaries:"; \
			echo "  PRELOADER_BIN=/path/to/preloader-mkpimage.bin UBOOT_IMG=/path/to/u-boot.img sudo make sd-image"; \
			exit 1; \
		fi; \
		echo "FPGA artifacts verified"; \
	'

kernel:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Kernel Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Building Linux kernel...$(NC)"
	@if [ -f "$(KERNEL_DIR)/Makefile" ]; then \
		set -e; \
		tmp_check="$(SCRIPTS_DIR)/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\r' < "$(SCRIPTS_DIR)/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "kernel sources (git)" --url "https://github.com" --url "https://raw.githubusercontent.com"; \
		$(MAKE) -C $(KERNEL_DIR) CROSS_COMPILE=$(CROSS_COMPILE) ARCH=$(ARCH); \
	else \
		echo "ERROR: Kernel Makefile not found: $(KERNEL_DIR)/Makefile"; \
		exit 1; \
	fi

rootfs:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Root Filesystem Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Building root filesystem...$(NC)"
	@echo -e "$(YELLOW)Note: Rootfs build requires root access$(NC)"
	@if [ -f "$(ROOTFS_DIR)/Makefile" ]; then \
		set -e; \
		tmp_check="$(SCRIPTS_DIR)/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\r' < "$(SCRIPTS_DIR)/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "Debian mirrors (debootstrap/apt)" --url "https://deb.debian.org" --url "https://security.debian.org"; \
		if [ "$(shell id -u)" -eq 0 ]; then \
			$(MAKE) -C $(ROOTFS_DIR); \
		else \
			echo "Run with: sudo make rootfs"; \
			echo -e "$(YELLOW)If it looks stuck, sudo is waiting for your password (input is hidden).$(NC)"; \
			sudo -v; \
			sudo $(MAKE) -C $(ROOTFS_DIR); \
		fi \
	else \
		echo "ERROR: Rootfs Makefile not found: $(ROOTFS_DIR)/Makefile"; \
		exit 1; \
	fi

linux-image:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Complete Linux Image Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@$(MAKE) fpga
	@$(MAKE) kernel
	@$(MAKE) rootfs
	@$(MAKE) sd-image
	@echo -e "$(GREEN)Complete Linux image built$(NC)"

sd-image: fpga
	@if [ ! -f "$(KERNEL_DIR)/build/arch/arm/boot/zImage" ]; then \
		echo -e "$(YELLOW)Kernel not found, building...$(NC)"; \
		$(MAKE) kernel; \
	else \
		echo -e "$(GREEN)[OK] Kernel already built$(NC)"; \
	fi
	@echo -e "$(YELLOW)Checking rootfs (incremental build)...$(NC)"
	@$(MAKE) rootfs
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)SD Card Image Creation$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Creating SD card image...$(NC)"
	@echo -e "$(YELLOW)Normalizing scripts for WSL compatibility...$(NC)"
	@bash -c '\
		set -e; \
		wrapper_script="create_sd_image_wrapper.sh"; \
		main_script="$(SCRIPTS_DIR)/create_sd_image.sh"; \
		tmp_wrapper=".create_sd_image_wrapper.normalized.$$$$"; \
		tmp_main="$(SCRIPTS_DIR)/.create_sd_image.normalized.$$$$"; \
		trap "rm -f \"$$tmp_wrapper\" \"$$tmp_main\"" EXIT; \
		\
		if [ ! -f "$$wrapper_script" ]; then \
			echo "ERROR: SD image wrapper script not found: $$wrapper_script"; \
			exit 1; \
		fi; \
		if [ ! -f "$$main_script" ]; then \
			echo "ERROR: Main SD image script not found: $$main_script"; \
			exit 1; \
		fi; \
		\
		echo "Normalizing $$wrapper_script -> $$tmp_wrapper"; \
		tr -d "\\r" < "$$wrapper_script" > "$$tmp_wrapper"; \
		chmod +x "$$tmp_wrapper"; \
		\
		echo "Normalizing $$main_script -> $$tmp_main"; \
		tr -d "\\r" < "$$main_script" > "$$tmp_main"; \
		chmod +x "$$tmp_main"; \
		\
		export NORMALIZED_MAIN_SCRIPT="$$tmp_main"; \
		\
		echo ""; \
		echo "Scripts normalized successfully"; \
		echo ""; \
		\
		if [ "$$(id -u)" -eq 0 ]; then \
			echo "Running as root..."; \
			bash "$$tmp_wrapper"; \
		else \
			echo "Image creation requires root access"; \
			echo "Run with: sudo make sd-image"; \
			echo -e "$(YELLOW)NOTE: If it looks stuck, sudo is waiting for your password (input is hidden).$(NC)"; \
			echo ""; \
			sudo -v && sudo bash "$$tmp_wrapper"; \
		fi \
	'

clean:
	@echo -e "$(YELLOW)Cleaning Linux image build artifacts...$(NC)"
	@if [ -f "$(KERNEL_DIR)/Makefile" ]; then \
		$(MAKE) -C $(KERNEL_DIR) kernel-clean || true; \
	fi
	@if [ -f "$(ROOTFS_DIR)/Makefile" ]; then \
		$(MAKE) -C $(ROOTFS_DIR) clean || true; \
	fi
	@rm -rf $(BUILD_DIR)
	@echo -e "$(GREEN)Clean complete$(NC)"
