# ============================================================================
# Linux Image Build System for DE10-Nano
# ============================================================================
# Builds kernel, rootfs, and creates SD card image
# Supports parallel builds for kernel and rootfs
# ============================================================================

SHELL := /bin/bash

# Paths
LINUX_IMAGE_DIR := $(CURDIR)
HPS_DIR := $(abspath $(CURDIR)/..)
REPO_ROOT := $(abspath $(HPS_DIR)/..)
FPGA_DIR := $(REPO_ROOT)/FPGA

# Include common build infrastructure
-include $(REPO_ROOT)/build/build_common.mk

# Configuration
KERNEL_DIR := $(LINUX_IMAGE_DIR)/kernel
ROOTFS_DIR := $(LINUX_IMAGE_DIR)/rootfs
BOOTLOADER_DIR := $(LINUX_IMAGE_DIR)/bootloader
SCRIPTS_DIR := $(LINUX_IMAGE_DIR)/scripts
BUILD_DIR := $(LINUX_IMAGE_DIR)/build
DEPS_PACKAGES := debootstrap qemu-user-static debian-archive-keyring ca-certificates gnupg wget curl parted dosfstools e2fsprogs util-linux u-boot-tools

# Bootloader paths (U-Boot with built-in DE10-Nano support)
UBOOT_BUILD_DIR := $(BOOTLOADER_DIR)/build
PRELOADER_BIN := $(UBOOT_BUILD_DIR)/u-boot-with-spl.sfp
UBOOT_IMG := $(UBOOT_BUILD_DIR)/u-boot.img

# FPGA project files (override if you use a different design)
FPGA_QUARTUS_QPF ?= quartus/DE10_NANO_SoC_GHRD.qpf
FPGA_QSYS_FILE ?= quartus/qsys/soc_system.qsys

# Cross-compilation
CROSS_COMPILE ?= arm-linux-gnueabihf-
ARCH := arm

# ============================================================================
# Parallel Build Configuration
# ============================================================================
# PARALLEL_BUILD=1 : Enable parallel kernel+rootfs builds (default)
# PARALLEL_BUILD=0 : Force serial builds (useful for debugging)
# PARALLEL_JOBS=N  : Number of parallel jobs (default: 2)
# ============================================================================
PARALLEL_BUILD ?= 1
PARALLEL_JOBS ?= 2

# Colors (fallback if build_common.mk not included)
GREEN ?= \033[0;32m
YELLOW ?= \033[1;33m
BLUE ?= \033[0;34m
CYAN ?= \033[0;36m
RED ?= \033[0;31m
NC ?= \033[0m

# Timestamp for logging
TIMESTAMP = $(shell date '+%Y-%m-%d %H:%M:%S')

.PHONY: all help deps deps-check fpga kernel rootfs bootloader linux-image sd-image clean
.PHONY: task-kernel task-rootfs parallel-build serial-build timing-report
.PHONY: sd-image-compress flash-sd

all: linux-image
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Linux image build complete$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@$(MAKE) timing-report

help:
	@echo "Linux Image Build System for DE10-Nano"
	@echo "======================================"
	@echo ""
	@echo "Targets:"
	@echo "  all              - Build complete Linux image (kernel + rootfs + SD image)"
	@echo "  deps             - Install build-host dependencies (Debian/Ubuntu/WSL)"
	@echo "  deps-check       - Verify build-host dependencies are installed"
	@echo "  bootloader       - Build U-Boot bootloader (SPL + U-Boot)"
	@echo "  kernel           - Build Linux kernel only"
	@echo "  rootfs           - Build root filesystem only (requires root)"
	@echo "  linux-image      - Build complete Linux image (bootloader + kernel + rootfs + SD image)"
	@echo "  sd-image         - Create SD card image only (requires bootloader, kernel and rootfs)"
	@echo "  sd-image-compress - Create compressed .img.xz (for distribution/git)"
	@echo "  sd-image-update  - Update existing SD image (faster, only changed files)"
	@echo "  flash-sd         - Show flash helper usage"
	@echo "  clean            - Clean all build artifacts"
	@echo "  timing-report    - Show build timing statistics"
	@echo "  help             - Show this help message"
	@echo ""
	@echo "Parallel Build Options:"
	@echo "  PARALLEL_BUILD=1  - Enable parallel kernel+rootfs (default)"
	@echo "  PARALLEL_BUILD=0  - Force serial builds (for debugging)"
	@echo "  PARALLEL_JOBS=N   - Number of parallel jobs (default: 2)"
	@echo ""
	@echo "Usage:"
	@echo "  make kernel                    # Build kernel only"
	@echo "  sudo make rootfs               # Build rootfs only"
	@echo "  sudo make all                  # Build complete image (parallel)"
	@echo "  sudo make all PARALLEL_BUILD=0 # Build complete image (serial)"
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
		tr -d '\015' < "$(SCRIPTS_DIR)/check_internet.sh" > "$$tmp_check"; \
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

# Public kernel target (standalone use)
kernel:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Kernel Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Building Linux kernel...$(NC)"
	@$(MAKE) kernel-internal

# Public bootloader target - builds U-Boot with SPL (no SoC EDS required)
bootloader:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)U-Boot Bootloader Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Building U-Boot with SPL for DE10-Nano...$(NC)"
	@$(MAKE) -C $(BOOTLOADER_DIR) CROSS_COMPILE=$(CROSS_COMPILE)
	@echo -e "$(GREEN)[OK]$(NC) Bootloader built: $(PRELOADER_BIN)"

# Public rootfs target (standalone use)
rootfs:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Root Filesystem Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Building root filesystem...$(NC)"
	@echo -e "$(YELLOW)Note: Rootfs build requires root access$(NC)"
	@$(MAKE) rootfs-internal

# ============================================================================
# Parallel Build Tasks
# ============================================================================
# These are individual tasks that can be run in parallel or serial.
# Do not call these directly; use linux-image or parallel-build instead.
# ============================================================================

# Task wrapper for kernel build (for parallel execution)
task-kernel:
	@echo -e "$(CYAN)[TASK]$(NC) $(TIMESTAMP) | Starting kernel build task"
	@mkdir -p $(BUILD_DIR)/.timing
	@date +%s > $(BUILD_DIR)/.timing/kernel.start
	@$(MAKE) kernel-internal
	@if [ -f "$(BUILD_DIR)/.timing/kernel.start" ]; then \
		start=$$(cat $(BUILD_DIR)/.timing/kernel.start); \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		mins=$$((duration / 60)); \
		secs=$$((duration % 60)); \
		echo -e "$(GREEN)[TASK]$(NC) $(TIMESTAMP) | Kernel build completed ($${mins}m $${secs}s)"; \
		echo "kernel,$$start,$$end,$$duration" >> $(BUILD_DIR)/.timing/build_times.csv; \
		rm -f $(BUILD_DIR)/.timing/kernel.start; \
	fi

# Task wrapper for rootfs build (for parallel execution)
task-rootfs:
	@echo -e "$(CYAN)[TASK]$(NC) $(TIMESTAMP) | Starting rootfs build task"
	@mkdir -p $(BUILD_DIR)/.timing
	@date +%s > $(BUILD_DIR)/.timing/rootfs.start
	@$(MAKE) rootfs-internal
	@if [ -f "$(BUILD_DIR)/.timing/rootfs.start" ]; then \
		start=$$(cat $(BUILD_DIR)/.timing/rootfs.start); \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		mins=$$((duration / 60)); \
		secs=$$((duration % 60)); \
		echo -e "$(GREEN)[TASK]$(NC) $(TIMESTAMP) | Rootfs build completed ($${mins}m $${secs}s)"; \
		echo "rootfs,$$start,$$end,$$duration" >> $(BUILD_DIR)/.timing/build_times.csv; \
		rm -f $(BUILD_DIR)/.timing/rootfs.start; \
	fi

# Internal kernel target (called by task-kernel)
kernel-internal:
	@if [ -f "$(KERNEL_DIR)/Makefile" ]; then \
		set -e; \
		tmp_check="$(SCRIPTS_DIR)/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\015' < "$(SCRIPTS_DIR)/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "kernel sources (git)" --url "https://github.com" --url "https://raw.githubusercontent.com"; \
		$(MAKE) -C $(KERNEL_DIR) CROSS_COMPILE=$(CROSS_COMPILE) ARCH=$(ARCH); \
	else \
		echo "ERROR: Kernel Makefile not found: $(KERNEL_DIR)/Makefile"; \
		exit 1; \
	fi

# Internal rootfs target (called by task-rootfs)
rootfs-internal:
	@if [ -f "$(ROOTFS_DIR)/Makefile" ]; then \
		set -e; \
		tmp_check="$(SCRIPTS_DIR)/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\015' < "$(SCRIPTS_DIR)/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "Debian mirrors (debootstrap/apt)" --url "https://deb.debian.org" --url "https://security.debian.org"; \
		if [ "$$(id -u)" -eq 0 ]; then \
			$(MAKE) -C $(ROOTFS_DIR); \
		else \
			echo "Rootfs build requires root - using sudo"; \
			sudo -E $(MAKE) -C $(ROOTFS_DIR); \
		fi \
	else \
		echo "ERROR: Rootfs Makefile not found: $(ROOTFS_DIR)/Makefile"; \
		exit 1; \
	fi

# ============================================================================
# Main Linux Image Build
# ============================================================================
# Builds kernel and rootfs in parallel (or serial if PARALLEL_BUILD=0)
# then creates the SD card image.
# ============================================================================

linux-image:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Complete Linux Image Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Build configuration:"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) |   PARALLEL_BUILD=$(PARALLEL_BUILD)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) |   PARALLEL_JOBS=$(PARALLEL_JOBS)"
	@echo ""
	@mkdir -p $(BUILD_DIR)/.timing
	@rm -f $(BUILD_DIR)/.timing/build_times.csv
	@# Step 1: Check FPGA artifacts
	@echo -e "$(BLUE)[STEP 1/3]$(NC) $(TIMESTAMP) | Checking FPGA artifacts..."
	@$(MAKE) fpga
	@# Step 2: Build kernel and rootfs (parallel or serial)
	@echo ""
	@if [ "$(PARALLEL_BUILD)" = "1" ]; then \
		echo -e "$(BLUE)[STEP 2/3]$(NC) $(TIMESTAMP) | Building kernel and rootfs in PARALLEL ($(PARALLEL_JOBS) jobs)"; \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) |   Set PARALLEL_BUILD=0 for serial builds"; \
		$(MAKE) -j$(PARALLEL_JOBS) task-kernel task-rootfs; \
	else \
		echo -e "$(BLUE)[STEP 2/3]$(NC) $(TIMESTAMP) | Building kernel and rootfs SEQUENTIALLY"; \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) |   Set PARALLEL_BUILD=1 for parallel builds"; \
		$(MAKE) task-kernel; \
		$(MAKE) task-rootfs; \
	fi
	@# Step 3: Create SD image
	@echo ""
	@echo -e "$(BLUE)[STEP 3/3]$(NC) $(TIMESTAMP) | Creating SD card image..."
	@date +%s > $(BUILD_DIR)/.timing/sd-image.start
	@$(MAKE) sd-image-internal
	@if [ -f "$(BUILD_DIR)/.timing/sd-image.start" ]; then \
		start=$$(cat $(BUILD_DIR)/.timing/sd-image.start); \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		mins=$$((duration / 60)); \
		secs=$$((duration % 60)); \
		echo -e "$(GREEN)[TASK]$(NC) $(TIMESTAMP) | SD image created ($${mins}m $${secs}s)"; \
		echo "sd-image,$$start,$$end,$$duration" >> $(BUILD_DIR)/.timing/build_times.csv; \
		rm -f $(BUILD_DIR)/.timing/sd-image.start; \
	fi
	@echo ""
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Complete Linux image built successfully$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"

# Timing report target
timing-report:
	@echo ""
	@echo -e "$(GREEN)Build Timing Summary$(NC)"
	@echo "---------------------------------------------"
	@if [ -f "$(BUILD_DIR)/.timing/build_times.csv" ]; then \
		total=0; \
		while IFS=, read -r phase start end duration; do \
			mins=$$((duration / 60)); \
			secs=$$((duration % 60)); \
			printf "  %-20s %3dm %02ds\n" "$$phase:" "$$mins" "$$secs"; \
			total=$$((total + duration)); \
		done < $(BUILD_DIR)/.timing/build_times.csv; \
		echo "---------------------------------------------"; \
		total_mins=$$((total / 60)); \
		total_secs=$$((total % 60)); \
		printf "  %-20s %3dm %02ds\n" "TOTAL:" "$$total_mins" "$$total_secs"; \
	else \
		echo "  No timing data available"; \
		echo "  Run 'make linux-image' to generate timing data"; \
	fi
	@echo ""

# Public sd-image target - checks dependencies then creates image
sd-image:
	@# Check/build bootloader
	@if [ ! -f "$(PRELOADER_BIN)" ]; then \
		echo -e "$(YELLOW)Bootloader not found, building...$(NC)"; \
		$(MAKE) bootloader; \
	else \
		echo -e "$(GREEN)[OK] Bootloader already built$(NC)"; \
	fi
	@# Check/build kernel
	@if [ ! -f "$(KERNEL_DIR)/build/arch/arm/boot/zImage" ]; then \
		echo -e "$(YELLOW)Kernel not found, building...$(NC)"; \
		$(MAKE) kernel; \
	else \
		echo -e "$(GREEN)[OK] Kernel already built$(NC)"; \
	fi
	@# Check/build rootfs
	@echo -e "$(YELLOW)Checking rootfs (incremental build)...$(NC)"
	@$(MAKE) rootfs
	@# Create SD image with our bootloader paths
	@PRELOADER_BIN="$(PRELOADER_BIN)" UBOOT_IMG="$(UBOOT_IMG)" $(MAKE) sd-image-internal

# Internal SD image creation (called by linux-image and sd-image)
sd-image-internal:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)SD Card Image Creation$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Creating SD card image (Docker-compatible, no loop devices)...$(NC)"
	@bash -c '\
		set -e; \
		main_script="$(SCRIPTS_DIR)/create_sd_image.sh"; \
		\
		if [ ! -f "$$main_script" ]; then \
			echo "ERROR: SD image script not found: $$main_script"; \
			exit 1; \
		fi; \
		\
		export PRELOADER_BIN="$(PRELOADER_BIN)"; \
		export UBOOT_IMG="$(UBOOT_IMG)"; \
		\
		if [ "$$(id -u)" -eq 0 ]; then \
			echo "Running as root..."; \
			bash "$$main_script"; \
		else \
			echo "Image creation requires root access"; \
			echo "Run with: sudo make sd-image"; \
			sudo -v && sudo bash "$$main_script"; \
		fi \
	'

# ============================================================================
# Incremental SD Image Update
# ============================================================================
# Updates an existing SD image with only changed files.
# Much faster than creating a new image from scratch.
# ============================================================================

sd-image-update:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)SD Card Image Incremental Update$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@IMAGE_FILE="$(BUILD_DIR)/de10-nano-custom.img"; \
	if [ ! -f "$$IMAGE_FILE" ]; then \
		echo -e "$(YELLOW)No existing image found at $$IMAGE_FILE$(NC)"; \
		echo -e "$(YELLOW)Creating new image instead...$(NC)"; \
		$(MAKE) sd-image; \
		exit 0; \
	fi; \
	echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Updating existing image: $$IMAGE_FILE"; \
	echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Image size: $$(du -h "$$IMAGE_FILE" | cut -f1)"; \
	echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Last modified: $$(date -r "$$IMAGE_FILE" "+%Y-%m-%d %H:%M:%S")"; \
	echo ""; \
	if [ "$$(id -u)" -ne 0 ]; then \
		echo "Image update requires root access"; \
		echo "Run with: sudo make sd-image-update"; \
		exit 1; \
	fi; \
	set -e; \
	start_time=$$(date +%s); \
	LOOP_DEV=$$(losetup -f); \
	echo -e "$(YELLOW)Setting up loop device: $$LOOP_DEV$(NC)"; \
	losetup -P "$$LOOP_DEV" "$$IMAGE_FILE"; \
	trap "losetup -d $$LOOP_DEV 2>/dev/null || true" EXIT; \
	sleep 1; \
	partprobe "$$LOOP_DEV" 2>/dev/null || true; \
	BOOT_PART="$${LOOP_DEV}p1"; \
	echo ""; \
	echo -e "$(YELLOW)Mounting boot partition...$(NC)"; \
	BOOT_MOUNT="/mnt/de10-boot-update"; \
	mkdir -p "$$BOOT_MOUNT"; \
	mount "$$BOOT_PART" "$$BOOT_MOUNT"; \
	trap "umount $$BOOT_MOUNT 2>/dev/null || true; rmdir $$BOOT_MOUNT 2>/dev/null || true; losetup -d $$LOOP_DEV 2>/dev/null || true" EXIT; \
	updated=0; \
	KERNEL_SRC="$(KERNEL_DIR)/build/arch/arm/boot/zImage"; \
	if [ -f "$$KERNEL_SRC" ] && [ "$$KERNEL_SRC" -nt "$$BOOT_MOUNT/zImage" ]; then \
		echo -e "$(YELLOW)Updating kernel (zImage)...$(NC)"; \
		cp "$$KERNEL_SRC" "$$BOOT_MOUNT/zImage"; \
		updated=1; \
	else \
		echo -e "$(GREEN)[OK] Kernel up-to-date$(NC)"; \
	fi; \
	RBF_SRC=""; \
	for rbf in $(FPGA_DIR)/build/output_files/*.rbf $(REPO_ROOT)/build/output_files/*.rbf; do \
		if [ -f "$$rbf" ]; then RBF_SRC="$$rbf"; break; fi; \
	done; \
	if [ -n "$$RBF_SRC" ] && [ "$$RBF_SRC" -nt "$$BOOT_MOUNT/soc_system.rbf" ]; then \
		echo -e "$(YELLOW)Updating FPGA bitstream (RBF)...$(NC)"; \
		cp "$$RBF_SRC" "$$BOOT_MOUNT/soc_system.rbf"; \
		updated=1; \
	else \
		echo -e "$(GREEN)[OK] FPGA bitstream up-to-date$(NC)"; \
	fi; \
	DTB_SRC="$(FPGA_DIR)/generated/soc_system.dtb"; \
	if [ -f "$$DTB_SRC" ] && [ "$$DTB_SRC" -nt "$$BOOT_MOUNT/soc_system.dtb" ]; then \
		echo -e "$(YELLOW)Updating device tree (DTB)...$(NC)"; \
		cp "$$DTB_SRC" "$$BOOT_MOUNT/soc_system.dtb"; \
		updated=1; \
	else \
		echo -e "$(GREEN)[OK] Device tree up-to-date$(NC)"; \
	fi; \
	echo ""; \
	sync; \
	umount "$$BOOT_MOUNT"; \
	rmdir "$$BOOT_MOUNT"; \
	losetup -d "$$LOOP_DEV"; \
	trap - EXIT; \
	end_time=$$(date +%s); \
	duration=$$((end_time - start_time)); \
	echo -e "$(GREEN)===========================================$(NC)"; \
	if [ $$updated -eq 1 ]; then \
		echo -e "$(GREEN)Image updated successfully ($$duration seconds)$(NC)"; \
	else \
		echo -e "$(GREEN)Image already up-to-date ($$duration seconds)$(NC)"; \
	fi; \
	echo -e "$(GREEN)===========================================$(NC)"

# ============================================================================
# Compressed SD Image
# ============================================================================
# Creates a compressed .img.xz file for distribution and git storage.
# Compression ratio is typically 95%+ (4GB -> ~180MB) since most of the
# image is empty space.
# ============================================================================

sd-image-compress: sd-image
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Compressing SD Card Image$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@IMAGE_FILE="$(BUILD_DIR)/de10-nano-custom.img"; \
	if [ ! -f "$$IMAGE_FILE" ]; then \
		echo -e "$(RED)ERROR: Image not found: $$IMAGE_FILE$(NC)"; \
		exit 1; \
	fi; \
	echo -e "$(YELLOW)Compressing with xz (level 9)...$(NC)"; \
	echo "Original size: $$(du -h "$$IMAGE_FILE" | cut -f1)"; \
	xz -9 --keep --force "$$IMAGE_FILE"; \
	echo -e "$(GREEN)Compressed size: $$(du -h "$${IMAGE_FILE}.xz" | cut -f1)$(NC)"; \
	echo ""; \
	echo -e "$(GREEN)Compressed image: $${IMAGE_FILE}.xz$(NC)"; \
	echo ""; \
	echo "To flash to SD card:"; \
	echo "  sudo ./scripts/flash_sd.sh /dev/sdX"; \
	echo ""; \
	echo "Or manually:"; \
	echo "  xz -dc $${IMAGE_FILE}.xz | sudo dd of=/dev/sdX bs=4M status=progress"

# Flash SD card helper
flash-sd:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Flash SD Card$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo ""
	@echo "Usage: sudo ./scripts/flash_sd.sh /dev/sdX"
	@echo ""
	@echo "Available images:"
	@ls -lh $(BUILD_DIR)/*.img* 2>/dev/null || echo "  (none - run 'make sd-image' first)"
	@echo ""
	@echo "List available devices:"
	@echo "  ./scripts/flash_sd.sh --list"

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
