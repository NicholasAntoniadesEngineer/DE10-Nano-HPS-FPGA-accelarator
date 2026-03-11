# ============================================================================
# U-Boot Bootloader Build for DE10-Nano
# ============================================================================
# Builds U-Boot with SPL (replaces Intel preloader) using built-in DE10-Nano
# support. Does NOT require Intel SoC EDS.
#
# Output files:
#   - u-boot-with-spl.sfp : Combined SPL + U-Boot (write to A2 partition)
#   - u-boot.img          : U-Boot image only
# ============================================================================

SHELL := /bin/bash

# Paths
BOOTLOADER_DIR := $(CURDIR)
BUILD_DIR := $(BOOTLOADER_DIR)/build
UBOOT_SRC := $(BOOTLOADER_DIR)/u-boot-socfpga

# U-Boot version - using v2020.04 for compatibility with Debian Stretch's OpenSSL
# v2020.04 has good DE10-Nano support and works with OpenSSL 1.0.x
UBOOT_VERSION ?= v2020.04
UBOOT_REPO ?= https://github.com/u-boot/u-boot.git

# Cross-compilation
CROSS_COMPILE ?= arm-linux-gnueabihf-
ARCH := arm

# Configuration
UBOOT_DEFCONFIG := socfpga_de10_nano_defconfig

# Output files
UBOOT_SPL := $(BUILD_DIR)/u-boot-with-spl.sfp
UBOOT_IMG := $(BUILD_DIR)/u-boot.img

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
CYAN := \033[0;36m
NC := \033[0m

.PHONY: all help download configure build clean distclean

all: build

help:
	@echo "U-Boot Bootloader Build for DE10-Nano"
	@echo "======================================"
	@echo ""
	@echo "Targets:"
	@echo "  all       - Download, configure, and build U-Boot (default)"
	@echo "  download  - Download U-Boot source"
	@echo "  configure - Configure U-Boot for DE10-Nano"
	@echo "  build     - Build U-Boot"
	@echo "  clean     - Clean build artifacts"
	@echo "  distclean - Remove everything including source"
	@echo ""
	@echo "Output files (after build):"
	@echo "  $(UBOOT_SPL)"
	@echo "  $(UBOOT_IMG)"

# Download U-Boot source
download: $(UBOOT_SRC)/.git

$(UBOOT_SRC)/.git:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Downloading U-Boot $(UBOOT_VERSION)$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@if [ -d "$(UBOOT_SRC)" ]; then \
		echo "U-Boot source exists, updating..."; \
		cd $(UBOOT_SRC) && git fetch origin; \
	else \
		echo "Cloning U-Boot repository..."; \
		git clone --depth 1 --branch $(UBOOT_VERSION) $(UBOOT_REPO) $(UBOOT_SRC); \
	fi
	@cd $(UBOOT_SRC) && git checkout $(UBOOT_VERSION)
	@echo -e "$(GREEN)U-Boot source ready$(NC)"

# Configure U-Boot
configure: $(BUILD_DIR)/.config

$(BUILD_DIR)/.config: $(UBOOT_SRC)/.git
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Configuring U-Boot for DE10-Nano$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@mkdir -p $(BUILD_DIR)
	$(MAKE) -C $(UBOOT_SRC) O=$(BUILD_DIR) CROSS_COMPILE=$(CROSS_COMPILE) $(UBOOT_DEFCONFIG)
	@echo -e "$(CYAN)Enabling maximum SPL + U-Boot debug logging...$(NC)"
	# Append debug options on top of defconfig using scripts/config
	@$(UBOOT_SRC)/scripts/config --file $(BUILD_DIR)/.config \
		--enable  CONFIG_SPL_LIBCOMMON_SUPPORT \
		--enable  CONFIG_SPL_SERIAL_SUPPORT \
		--enable  CONFIG_MMC_VERBOSE \
		--enable  CONFIG_SPL_MMC_VERBOSE \
		--enable  CONFIG_LOGLEVEL \
		--set-val CONFIG_LOGLEVEL 7 \
		--enable  CONFIG_SPL_LOGLEVEL \
		--set-val CONFIG_SPL_LOGLEVEL 7 \
		--enable  CONFIG_LOG \
		--enable  CONFIG_SPL_LOG \
		--enable  CONFIG_SPL_LOG_MAX_LEVEL \
		--set-val CONFIG_SPL_LOG_MAX_LEVEL 7 \
		--enable  CONFIG_LOG_MAX_LEVEL \
		--set-val CONFIG_LOG_MAX_LEVEL 7 \
		--enable  CONFIG_SPL_FS_FAT \
		--enable  CONFIG_SPL_FAT_SUPPORT \
		--enable  CONFIG_FAT_WRITE \
		--enable  CONFIG_SPL_LIBDISK_SUPPORT \
		2>/dev/null || true
	# Sync config (resolve any dependency issues from above overrides)
	$(MAKE) -C $(UBOOT_SRC) O=$(BUILD_DIR) CROSS_COMPILE=$(CROSS_COMPILE) olddefconfig
	@echo -e "$(GREEN)U-Boot configured with maximum debug logging$(NC)"

# Build U-Boot
build: $(UBOOT_SPL)

$(UBOOT_SPL): $(BUILD_DIR)/.config
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Building U-Boot$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	$(MAKE) -C $(UBOOT_SRC) O=$(BUILD_DIR) CROSS_COMPILE=$(CROSS_COMPILE) -j$$(nproc)
	@echo ""
	@echo -e "$(GREEN)U-Boot build complete$(NC)"
	@echo -e "$(CYAN)Output files:$(NC)"
	@ls -la $(BUILD_DIR)/u-boot-with-spl.sfp 2>/dev/null || echo "  SPL+U-Boot: not found (check build log)"
	@ls -la $(BUILD_DIR)/u-boot.img 2>/dev/null || echo "  U-Boot img: not found"
	@echo ""
	@echo -e "$(CYAN)=== Key SPL Boot Config ===$(NC)"
	@grep -E 'SPL_FS_FAT|SPL_MMC|MMCSD_RAW_MODE|SPL_SERIAL|SPL_LOG' $(BUILD_DIR)/.config | grep -v '^#'
	@echo -e "$(CYAN)===========================$(NC)"

clean:
	@echo "Cleaning U-Boot build..."
	@if [ -d "$(BUILD_DIR)" ]; then \
		$(MAKE) -C $(UBOOT_SRC) O=$(BUILD_DIR) clean 2>/dev/null || true; \
	fi
	@rm -rf $(BUILD_DIR)

distclean: clean
	@echo "Removing U-Boot source..."
	@rm -rf $(UBOOT_SRC)
