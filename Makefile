# ============================================================================
# DE10-Nano Low-Latency Market Analysis - Top Level Makefile
# ============================================================================
# 
# This Makefile orchestrates the complete build process with:
#   - Full dependency tracking between FPGA and HPS components
#   - Detailed logging with timestamps
#   - Parallel builds where possible
#   - Build timing and profiling
#
# Build Architecture:
#   FPGA/  -> QSys system, Quartus bitstream, Device Tree, Bootloaders
#   HPS/   -> Linux kernel, Root filesystem, Applications, SD card image
#
# Dependency Chain:
#   QSys (.qsys) -> sopcinfo -> DTB (hardware description)
#                -> synthesis -> SOF -> RBF (FPGA bitstream)
#   
#   Kernel source -> zImage (kernel binary)
#   packages.txt  -> rootfs base -> rootfs.tar.gz
#   
#   RBF + DTB + zImage + rootfs -> SD card image
#
# ============================================================================

SHELL := /bin/bash

# ============================================================================
# Directory Structure
# ============================================================================

REPO_ROOT := $(CURDIR)
FPGA_DIR := $(REPO_ROOT)/FPGA
HPS_DIR := $(REPO_ROOT)/HPS
BUILD_DIR := $(REPO_ROOT)/build
DOCUMENTATION_DIR := $(REPO_ROOT)/documentation

# ============================================================================
# Build Artifacts (with full paths)
# ============================================================================

# FPGA Artifacts
FPGA_QSYS_FILE := $(FPGA_DIR)/quartus/qsys/soc_system.qsys
FPGA_SOPCINFO := $(FPGA_DIR)/generated/soc_system.sopcinfo
FPGA_SOF := $(FPGA_DIR)/build/output_files/DE10_NANO_SoC_GHRD.sof
FPGA_RBF := $(FPGA_DIR)/build/output_files/DE10_NANO_SoC_GHRD.rbf

# Device Tree (built by U-Boot for DE10-Nano)
# DTB_SOURCE controls which DTB generation method to use:
#   uboot - Use U-Boot's built-in DE10-Nano device tree (recommended, no SoC EDS needed)
#   qsys  - Generate from QSys sopcinfo (requires SoC EDS)
DTB_SOURCE ?= uboot
FPGA_DTB := $(HPS_DIR)/linux_image/bootloader/build/arch/arm/dts/socfpga_cyclone5_de10_nano.dtb

# Bootloaders (built by U-Boot with DE10-Nano support)
PRELOADER_BIN := $(HPS_DIR)/linux_image/bootloader/build/u-boot-with-spl.sfp
UBOOT_IMG := $(HPS_DIR)/linux_image/bootloader/build/u-boot.img

# HPS Artifacts
KERNEL_ZIMAGE := $(HPS_DIR)/linux_image/kernel/build/arch/arm/boot/zImage
ROOTFS_TAR := $(HPS_DIR)/linux_image/rootfs/build/rootfs.tar.xz
ROOTFS_BASE_TAR := $(HPS_DIR)/linux_image/rootfs/build/rootfs_base.tar.xz

# Final Output
SD_IMAGE := $(HPS_DIR)/linux_image/build/de10-nano-custom.img

# ============================================================================
# Build Configuration
# ============================================================================

# Parallel build settings
PARALLEL_BUILD ?= 1
PARALLEL_JOBS ?= 2

# Cross-compilation
CROSS_COMPILE ?= arm-linux-gnueabihf-
ARCH := arm

# ============================================================================
# Colors and Logging
# ============================================================================

GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
RED := \033[0;31m
BOLD := \033[1m
NC := \033[0m

TIMESTAMP = $(shell date '+%Y-%m-%d %H:%M:%S')

# Logging macros
define log_header
	@echo ""
	@echo -e "$(BOLD)============================================================================$(NC)"
	@echo -e "$(BOLD) $1$(NC)"
	@echo -e "$(BOLD)============================================================================$(NC)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | $1"
endef

define log_step
	@echo -e "$(BLUE)[STEP]$(NC) $(TIMESTAMP) | $1"
endef

define log_info
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | $1"
endef

define log_ok
	@echo -e "$(GREEN)[OK]$(NC)   $(TIMESTAMP) | $1"
endef

define log_warn
	@echo -e "$(YELLOW)[WARN]$(NC) $(TIMESTAMP) | $1"
endef

define log_error
	@echo -e "$(RED)[ERROR]$(NC) $(TIMESTAMP) | $1"
endef

# ============================================================================
# Timing Infrastructure
# ============================================================================

TIMING_DIR := $(BUILD_DIR)/.timing

define start_timer
	@mkdir -p $(TIMING_DIR)
	@date +%s > $(TIMING_DIR)/$1.start
endef

define end_timer
	@if [ -f "$(TIMING_DIR)/$1.start" ]; then \
		start=$$(cat $(TIMING_DIR)/$1.start); \
		end=$$(date +%s); \
		duration=$$((end - start)); \
		mins=$$((duration / 60)); \
		secs=$$((duration % 60)); \
		echo -e "$(GREEN)[TIME]$(NC) $(TIMESTAMP) | $1: $${mins}m $${secs}s"; \
		echo "$1,$$start,$$end,$$duration" >> $(TIMING_DIR)/build_times.csv; \
		rm -f $(TIMING_DIR)/$1.start; \
	fi
endef

# ============================================================================
# Phony Targets
# ============================================================================

.PHONY: all help clean clean-all
.PHONY: fpga fpga-qsys fpga-sof fpga-rbf fpga-rbf-only fpga-dtb fpga-dtb-only fpga-check
.PHONY: hps kernel rootfs applications
.PHONY: sd-image sd-image-update
.PHONY: deploy status timing-report check-deps
.PHONY: everything everything-parallel everything-sequential
.PHONY: task-fpga task-hps

# ============================================================================
# Default Target
# ============================================================================

all: sd-image
	$(call log_header,Build Complete)
	$(call log_ok,SD card image ready: $(SD_IMAGE))
	@echo ""
	@echo -e "$(YELLOW)To deploy:$(NC)"
	@echo "  sudo dd if=$(SD_IMAGE) of=/dev/sdX bs=4M status=progress conv=fsync"
	@echo ""
	@$(MAKE) --no-print-directory timing-report

# ============================================================================
# Help
# ============================================================================

help:
	@echo "DE10-Nano Low-Latency Market Analysis Build System"
	@echo "==================================================="
	@echo ""
	@echo "Main Targets:"
	@echo "  all                  - Build complete SD card image (default)"
	@echo "  everything           - Build all (FPGA + HPS in parallel)"
	@echo "  everything-parallel  - Force parallel FPGA + HPS builds"
	@echo "  everything-sequential- Force sequential builds"
	@echo "  status               - Show build status and artifact locations"
	@echo "  timing-report        - Show build timing statistics"
	@echo "  help                 - Show this help message"
	@echo ""
	@echo "FPGA Targets:"
	@echo "  fpga             - Build all FPGA components"
	@echo "  fpga-qsys        - Generate QSys system (sopcinfo)"
	@echo "  fpga-sof         - Compile FPGA bitstream (SOF)"
	@echo "  fpga-rbf         - Convert SOF to RBF"
	@echo "  fpga-dtb         - Generate device tree from QSys"
	@echo "  fpga-check       - Verify FPGA artifacts exist"
	@echo ""
	@echo "HPS Targets:"
	@echo "  hps              - Build all HPS components"
	@echo "  kernel           - Build Linux kernel"
	@echo "  rootfs           - Build root filesystem"
	@echo "  applications     - Build HPS applications"
	@echo ""
	@echo "Image Targets:"
	@echo "  sd-image         - Create complete SD card image"
	@echo "  sd-image-update  - Update existing image (incremental)"
	@echo ""
	@echo "Clean Targets:"
	@echo "  clean            - Clean build artifacts (keep caches)"
	@echo "  clean-all        - Deep clean including all caches"
	@echo ""
	@echo "Parallelization Options:"
	@echo "  PARALLEL_EVERYTHING=1/0 - FPGA + HPS parallel (default: 1)"
	@echo "  PARALLEL_BUILD=1/0      - Kernel + Rootfs parallel (default: 1)"
	@echo "  PARALLEL_JOBS=N         - Jobs for kernel/rootfs (default: 2)"
	@echo "  QUARTUS_PARALLEL_JOBS=N - Quartus compile jobs (default: auto)"
	@echo "  PARALLEL_APPS=1/0       - Applications parallel (default: 1)"
	@echo ""
	@echo "Other Configuration:"
	@echo "  CROSS_COMPILE=...   - Cross-compiler prefix"
	@echo "  USE_CCACHE=1/0      - Enable ccache for kernel"
	@echo ""
	@echo "DTB Strategy: $(DTB_SOURCE)"
	@echo "  Current: QSys-generated (Option A)"
	@echo "  See Makefile comments for Option B (kernel overlays)"

# ============================================================================
# Status and Diagnostics
# ============================================================================

status:
	$(call log_header,Build Status)
	@echo ""
	@echo "FPGA Artifacts:"
	@if [ -f "$(FPGA_SOPCINFO)" ]; then \
		echo -e "  $(GREEN)[OK]$(NC) QSys sopcinfo: $(FPGA_SOPCINFO)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) QSys sopcinfo: Not built"; \
	fi
	@if [ -f "$(FPGA_SOF)" ]; then \
		echo -e "  $(GREEN)[OK]$(NC) FPGA SOF: $(FPGA_SOF)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) FPGA SOF: Not built"; \
	fi
	@if [ -f "$(FPGA_RBF)" ]; then \
		size=$$(du -h "$(FPGA_RBF)" | cut -f1); \
		echo -e "  $(GREEN)[OK]$(NC) FPGA RBF: $(FPGA_RBF) ($$size)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) FPGA RBF: Not built"; \
	fi
	@if [ -f "$(FPGA_DTB)" ]; then \
		echo -e "  $(GREEN)[OK]$(NC) Device Tree: $(FPGA_DTB) ($(DTB_SOURCE)-generated)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) Device Tree: Not built"; \
	fi
	@echo ""
	@echo "Bootloaders:"
	@if [ -f "$(PRELOADER_BIN)" ]; then \
		echo -e "  $(GREEN)[OK]$(NC) Preloader: $(PRELOADER_BIN)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) Preloader: Not found"; \
	fi
	@if [ -f "$(UBOOT_IMG)" ]; then \
		echo -e "  $(GREEN)[OK]$(NC) U-Boot: $(UBOOT_IMG)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) U-Boot: Not found"; \
	fi
	@echo ""
	@echo "HPS Artifacts:"
	@if [ -f "$(KERNEL_ZIMAGE)" ]; then \
		size=$$(du -h "$(KERNEL_ZIMAGE)" | cut -f1); \
		echo -e "  $(GREEN)[OK]$(NC) Kernel: $(KERNEL_ZIMAGE) ($$size)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) Kernel: Not built"; \
	fi
	@if [ -f "$(ROOTFS_BASE_TAR)" ]; then \
		size=$$(du -h "$(ROOTFS_BASE_TAR)" | cut -f1); \
		echo -e "  $(GREEN)[OK]$(NC) Rootfs base (cached): $(ROOTFS_BASE_TAR) ($$size)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) Rootfs base: Not cached"; \
	fi
	@if [ -f "$(ROOTFS_TAR)" ]; then \
		size=$$(du -h "$(ROOTFS_TAR)" | cut -f1); \
		echo -e "  $(GREEN)[OK]$(NC) Rootfs: $(ROOTFS_TAR) ($$size)"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) Rootfs: Not built"; \
	fi
	@echo ""
	@echo "Final Output:"
	@if [ -f "$(SD_IMAGE)" ]; then \
		size=$$(du -h "$(SD_IMAGE)" | cut -f1); \
		mtime=$$(date -r "$(SD_IMAGE)" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$(SD_IMAGE)" 2>/dev/null | cut -d. -f1); \
		echo -e "  $(GREEN)[OK]$(NC) SD Image: $(SD_IMAGE)"; \
		echo "       Size: $$size | Built: $$mtime"; \
	else \
		echo -e "  $(YELLOW)[--]$(NC) SD Image: Not created"; \
	fi

timing-report:
	@echo ""
	@echo -e "$(BOLD)Build Timing Summary$(NC)"
	@echo "---------------------------------------------"
	@if [ -f "$(TIMING_DIR)/build_times.csv" ]; then \
		total=0; \
		while IFS=, read -r phase start end duration; do \
			mins=$$((duration / 60)); \
			secs=$$((duration % 60)); \
			printf "  %-25s %3dm %02ds\n" "$$phase:" "$$mins" "$$secs"; \
			total=$$((total + duration)); \
		done < $(TIMING_DIR)/build_times.csv; \
		echo "---------------------------------------------"; \
		total_mins=$$((total / 60)); \
		total_secs=$$((total % 60)); \
		printf "  %-25s %3dm %02ds\n" "TOTAL:" "$$total_mins" "$$total_secs"; \
	else \
		echo "  No timing data available"; \
	fi
	@echo ""

# ============================================================================
# FPGA Build Targets
# ============================================================================
# 
# Parallelization: After SOF is compiled, DTB and RBF generation can run
# in parallel since they're independent operations.
# ============================================================================

fpga: fpga-sof
	$(call log_header,FPGA Post-Compile (RBF + DTB in parallel))
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Generating RBF and DTB in parallel..."
	@$(MAKE) -j2 fpga-rbf-only fpga-dtb-only
	$(call log_ok,FPGA build complete)

fpga-qsys:
	$(call log_header,QSys Generation)
	$(call start_timer,qsys)
	@$(MAKE) -C $(FPGA_DIR) qsys-generate
	$(call end_timer,qsys)

fpga-sof: fpga-qsys
	$(call log_header,FPGA Compilation (SOF))
	$(call log_info,Quartus parallel jobs: $(NPROC))
	$(call start_timer,fpga-compile)
	@$(MAKE) -C $(FPGA_DIR) sof
	$(call end_timer,fpga-compile)

# RBF generation (called from fpga target, runs in parallel with DTB)
fpga-rbf-only:
	@$(MAKE) -C $(FPGA_DIR) rbf
	$(call log_ok,RBF created: $(FPGA_RBF))

# DTB generation (called from fpga target, runs in parallel with RBF)
fpga-dtb-only:
ifeq ($(DTB_SOURCE),uboot)
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Using U-Boot generated DTB (skipping QSys DTB generation)"
	@if [ ! -f "$(FPGA_DTB)" ]; then \
		echo -e "$(RED)[ERROR]$(NC) DTB file not found: $(FPGA_DTB)"; \
		exit 1; \
	fi
	$(call log_ok,DTB verified: $(FPGA_DTB))
else
	@$(MAKE) -C $(FPGA_DIR) dtb
	$(call log_ok,DTB created: $(FPGA_DTB))
endif

# Standalone targets (for manual use)
fpga-rbf: fpga-sof
	$(call log_header,FPGA RBF Generation)
	@$(MAKE) -C $(FPGA_DIR) rbf
	$(call log_ok,RBF created: $(FPGA_RBF))

fpga-dtb: fpga-qsys
	$(call log_header,Device Tree Generation (from QSys))
	$(call log_info,DTB Source: $(DTB_SOURCE))
	$(call log_info,This DTB describes FPGA peripherals from QSys design)
	@$(MAKE) -C $(FPGA_DIR) dtb
	$(call log_ok,DTB created: $(FPGA_DTB))

fpga-check:
	$(call log_header,Checking FPGA Artifacts)
	@missing=0; \
	if [ ! -f "$(FPGA_RBF)" ]; then \
		echo -e "$(RED)[MISSING]$(NC) FPGA RBF: $(FPGA_RBF)"; \
		missing=1; \
	else \
		echo -e "$(GREEN)[OK]$(NC) FPGA RBF: $(FPGA_RBF)"; \
	fi; \
	if [ ! -f "$(FPGA_DTB)" ]; then \
		echo -e "$(YELLOW)[MISSING]$(NC) Device Tree: $(FPGA_DTB)"; \
		echo "  (Optional - kernel may have built-in DTB)"; \
	else \
		echo -e "$(GREEN)[OK]$(NC) Device Tree: $(FPGA_DTB)"; \
	fi; \
	if [ ! -f "$(PRELOADER_BIN)" ]; then \
		echo -e "$(RED)[MISSING]$(NC) Preloader: $(PRELOADER_BIN)"; \
		missing=1; \
	else \
		echo -e "$(GREEN)[OK]$(NC) Preloader: $(PRELOADER_BIN)"; \
	fi; \
	if [ ! -f "$(UBOOT_IMG)" ]; then \
		echo -e "$(RED)[MISSING]$(NC) U-Boot: $(UBOOT_IMG)"; \
		missing=1; \
	else \
		echo -e "$(GREEN)[OK]$(NC) U-Boot: $(UBOOT_IMG)"; \
	fi; \
	if [ $$missing -eq 1 ]; then \
		echo ""; \
		echo -e "$(RED)Some required FPGA artifacts are missing$(NC)"; \
		echo "Run: make fpga"; \
		exit 1; \
	fi

# ============================================================================
# HPS Build Targets
# ============================================================================

hps: kernel rootfs applications
	$(call log_ok,HPS build complete)

kernel:
	$(call log_header,Linux Kernel Build)
	$(call start_timer,kernel)
	@$(MAKE) -C $(HPS_DIR)/linux_image kernel CROSS_COMPILE=$(CROSS_COMPILE) ARCH=$(ARCH)
	$(call end_timer,kernel)

rootfs:
	$(call log_header,Root Filesystem Build)
	$(call start_timer,rootfs)
	@$(MAKE) -C $(HPS_DIR)/linux_image rootfs
	$(call end_timer,rootfs)

applications:
	$(call log_header,HPS Applications Build)
	$(call start_timer,applications)
	@$(MAKE) -C $(HPS_DIR) applications CROSS_COMPILE=$(CROSS_COMPILE)
	$(call end_timer,applications)

# ============================================================================
# SD Card Image Targets
# ============================================================================

sd-image: fpga
	$(call log_header,SD Card Image Creation)
	$(call log_info,Building kernel and rootfs (parallel=$(PARALLEL_BUILD)))
	$(call start_timer,sd-image-total)
	@$(MAKE) -C $(HPS_DIR)/linux_image linux-image \
		PARALLEL_BUILD=$(PARALLEL_BUILD) \
		PARALLEL_JOBS=$(PARALLEL_JOBS) \
		CROSS_COMPILE=$(CROSS_COMPILE) \
		ARCH=$(ARCH) \
		PRELOADER_BIN=$(PRELOADER_BIN) \
		UBOOT_IMG=$(UBOOT_IMG)
	$(call end_timer,sd-image-total)
	$(call log_ok,SD image created: $(SD_IMAGE))

sd-image-update:
	$(call log_header,SD Card Image Update (Incremental))
	$(call start_timer,sd-image-update)
	@$(MAKE) -C $(HPS_DIR)/linux_image sd-image-update
	$(call end_timer,sd-image-update)

# ============================================================================
# Everything Target - Maximum Parallelization
# ============================================================================
# 
# Build Parallelization Strategy:
#   FPGA and HPS builds are largely independent until SD image creation.
#   Running them in parallel can save 15-30 minutes on a full build.
#
#   Sequential (old):  FPGA -> Kernel -> Rootfs -> SD Image  (~60-90 min)
#   Parallel (new):    [FPGA] -----> [SD Image]              (~35-50 min)
#                      [Kernel + Rootfs] ->
#
# Configuration:
#   PARALLEL_EVERYTHING=1 : Run FPGA and HPS builds in parallel (default)
#   PARALLEL_EVERYTHING=0 : Run sequentially (for debugging/low memory)
# ============================================================================

PARALLEL_EVERYTHING ?= 1

# Task wrappers for parallel execution
task-fpga:
	@echo -e "$(CYAN)[TASK]$(NC) $(TIMESTAMP) | Starting FPGA build task"
	$(call start_timer,fpga-task)
	@$(MAKE) --no-print-directory fpga
	$(call end_timer,fpga-task)

task-hps:
	@echo -e "$(CYAN)[TASK]$(NC) $(TIMESTAMP) | Starting HPS build task (kernel + rootfs)"
	$(call start_timer,hps-task)
	@$(MAKE) -C $(HPS_DIR)/linux_image kernel rootfs \
		PARALLEL_BUILD=$(PARALLEL_BUILD) \
		PARALLEL_JOBS=$(PARALLEL_JOBS) \
		CROSS_COMPILE=$(CROSS_COMPILE) \
		ARCH=$(ARCH)
	$(call end_timer,hps-task)

# Default: parallel FPGA + HPS, then SD image
everything: 
	$(call log_header,Building Everything)
	@rm -f $(TIMING_DIR)/build_times.csv
	$(call start_timer,everything)
	@echo ""
	@if [ "$(PARALLEL_EVERYTHING)" = "1" ]; then \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | PARALLEL mode: FPGA and HPS building simultaneously"; \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Set PARALLEL_EVERYTHING=0 for sequential builds"; \
		echo ""; \
		$(MAKE) -j2 task-fpga task-hps; \
	else \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | SEQUENTIAL mode: Building FPGA then HPS"; \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Set PARALLEL_EVERYTHING=1 for parallel builds"; \
		echo ""; \
		$(MAKE) --no-print-directory fpga; \
		echo ""; \
		$(MAKE) --no-print-directory kernel; \
		$(MAKE) --no-print-directory rootfs; \
	fi
	@echo ""
	$(call log_step,Final Step: Creating SD Image...)
	$(call start_timer,sd-image-final)
	@$(MAKE) -C $(HPS_DIR)/linux_image sd-image-internal
	$(call end_timer,sd-image-final)
	@echo ""
	$(call log_step,Compressing SD Image for Git LFS...)
	$(call start_timer,sd-image-compress)
	@$(MAKE) -C $(HPS_DIR)/linux_image sd-image-compress
	$(call end_timer,sd-image-compress)
	$(call end_timer,everything)
	@echo ""
	$(call log_header,Everything Built Successfully)
	@$(MAKE) --no-print-directory timing-report

# Explicit parallel build (same as everything with PARALLEL_EVERYTHING=1)
everything-parallel:
	@$(MAKE) everything PARALLEL_EVERYTHING=1

# Explicit sequential build
everything-sequential:
	@$(MAKE) everything PARALLEL_EVERYTHING=0

# ============================================================================
# Clean Targets (Parallelized)
# ============================================================================
# FPGA and HPS clean operations are independent and can run in parallel.
# ============================================================================

.PHONY: clean-fpga clean-hps clean-fpga-all clean-hps-all

# Individual clean tasks for parallel execution
clean-fpga:
	@$(MAKE) -C $(FPGA_DIR) clean || true

clean-hps:
	@$(MAKE) -C $(HPS_DIR) clean || true

clean-fpga-all:
	@$(MAKE) -C $(FPGA_DIR) clean-all || true

clean-hps-all:
	@$(MAKE) -C $(HPS_DIR) clean-all || true
	@$(MAKE) -C $(HPS_DIR)/linux_image/rootfs clean-all || true

clean:
	$(call log_header,Cleaning Build Artifacts (Parallel))
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Cleaning FPGA and HPS in parallel..."
	@$(MAKE) -j2 clean-fpga clean-hps
	@rm -f $(TIMING_DIR)/build_times.csv
	$(call log_ok,Clean complete)

clean-all:
	$(call log_header,Deep Clean Including Caches (Parallel))
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Deep cleaning FPGA and HPS in parallel..."
	@$(MAKE) -j2 clean-fpga-all clean-hps-all
	@rm -rf $(BUILD_DIR)
	$(call log_ok,Deep clean complete)
