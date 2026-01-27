# ============================================================================
# Root Filesystem Build Makefile
# ============================================================================
# Automated rootfs build with configuration management
# Supports:
#   - Incremental builds (only rebuilds when source files change)
#   - Base image caching (dramatically speeds up repeated builds)
#   - Layered architecture (base system + overlays)
#   - WSL native filesystem building (avoids tar failures on /mnt/c/)
# ============================================================================

SHELL := /bin/bash

# ============================================================================
# WSL Native Filesystem Building
# ============================================================================
# WSL has known issues with debootstrap/tar on Windows filesystems (/mnt/c/).
# This feature automatically builds in native Linux filesystem for reliability.
#
# Detection:
#   - Checks if running on WSL AND path starts with /mnt/
#   - If so, builds in WSL_BUILD_DIR (default: ~/de10-rootfs-build)
#
# Configuration:
#   WSL_NATIVE_BUILD=1   : Force native filesystem build
#   WSL_NATIVE_BUILD=0   : Disable (build in current directory)
#   WSL_BUILD_DIR=path   : Custom native build directory
# ============================================================================

# Detect WSL and Windows filesystem
IS_WSL := $(shell grep -qi microsoft /proc/version 2>/dev/null && echo 1 || echo 0)
IS_WINDOWS_FS := $(shell echo "$(CURDIR)" | grep -q "^/mnt/" && echo 1 || echo 0)

# Auto-enable native build if on WSL with Windows filesystem
ifeq ($(IS_WSL),1)
ifeq ($(IS_WINDOWS_FS),1)
WSL_NATIVE_BUILD ?= 1
else
WSL_NATIVE_BUILD ?= 0
endif
else
WSL_NATIVE_BUILD ?= 0
endif

# Native build directory (in WSL's native filesystem)
WSL_BUILD_DIR ?= $(HOME)/de10-rootfs-build

# Configuration
BUILD_DIR := $(CURDIR)/build
ROOTFS_DIR := $(BUILD_DIR)/rootfs
ROOTFS_TAR := $(BUILD_DIR)/rootfs.tar.xz
BUILD_SCRIPT := $(CURDIR)/build_rootfs.sh
DEPS_PACKAGES := debootstrap qemu-user-static debian-archive-keyring ca-certificates gnupg wget

# ============================================================================
# Base Image Caching
# ============================================================================
# The rootfs build is split into two layers:
#   1. BASE: debootstrap + packages (slow, ~15-20 min, cached)
#   2. OVERLAY: configs, scripts, apps (fast, ~1-2 min, always applied)
#
# The base image is cached because:
#   - debootstrap is very slow (downloads ~500MB from internet)
#   - packages.txt rarely changes
#   - Base image is NOT affected by FPGA changes
#
# Overlay is always applied because:
#   - Configs and scripts change more frequently
#   - Very fast to apply (<2 min)
# ============================================================================

ROOTFS_BASE_TAR := $(BUILD_DIR)/rootfs_base.tar.xz
ROOTFS_BASE_HASH := $(BUILD_DIR)/.rootfs_base_hash

# Sources that trigger BASE rebuild (slow operations)
BASE_SOURCES := $(CURDIR)/packages.txt

# Sources that trigger OVERLAY rebuild (fast operations)
OVERLAY_SOURCES := $(wildcard $(CURDIR)/configs/network/*) \
                   $(wildcard $(CURDIR)/configs/ssh/*) \
                   $(wildcard $(CURDIR)/scripts/*.sh)

# All sources (for backward compatibility)
ROOTFS_SOURCES := $(BUILD_SCRIPT) $(BASE_SOURCES) $(OVERLAY_SOURCES)

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
CYAN := \033[0;36m
NC := \033[0m

# Timestamp for logging
TIMESTAMP = $(shell date '+%Y-%m-%d %H:%M:%S')

.PHONY: all rootfs deps deps-check clean help rebuild force-rebuild check-rebuild
.PHONY: base-image overlay-only show-cache-status clean-base
.PHONY: rootfs-native rootfs-local wsl-status extract-rootfs compress-rootfs

all: $(ROOTFS_TAR)
	@echo ""
	@echo -e "$(GREEN)============================================================================$(NC)"
	@echo -e "$(GREEN)ROOTFS BUILD COMPLETE$(NC)"
	@echo -e "$(GREEN)============================================================================$(NC)"
	@if [ -f "$(ROOTFS_TAR)" ]; then \
		echo -e "$(GREEN)✓ Final rootfs: $(ROOTFS_TAR) ($$(du -h $(ROOTFS_TAR) | cut -f1))$(NC)"; \
	else \
		echo -e "$(RED)✗ ERROR: Final rootfs not found: $(ROOTFS_TAR)$(NC)"; \
		exit 1; \
	fi
	@if [ -f "$(ROOTFS_BASE_TAR)" ]; then \
		echo -e "$(GREEN)✓ Base cache:   $(ROOTFS_BASE_TAR) ($$(du -h $(ROOTFS_BASE_TAR) | cut -f1))$(NC)"; \
	fi
	@echo -e "$(GREEN)============================================================================$(NC)"
	@echo ""

help:
	@echo "Root Filesystem Build System"
	@echo "============================"
	@echo ""
	@echo "Targets:"
	@echo "  all           - Build rootfs if needed (default, automatic dependency tracking)"
	@echo "  rootfs        - Build rootfs tarball (auto-detects WSL, incremental builds)"
	@echo "  rootfs-native - Force build on native Linux filesystem (WSL)"
	@echo "  rootfs-local  - Force build in current directory (no WSL redirect)"
	@echo "  base-image    - Build/cache base image only (debootstrap + packages)"
	@echo "  overlay-only  - Force overlay rebuild (redundant - make rootfs handles this)"
	@echo "  rebuild       - Force rebuild everything from scratch"
	@echo "  force-rebuild - Alias for rebuild"
	@echo "  check-rebuild - Check if rebuild is needed (dry-run)"
	@echo "  wsl-status    - Show WSL detection status"
	@echo "  show-cache-status - Show base image cache status"
	@echo "  deps          - Install build-host dependencies"
	@echo "  deps-check    - Verify build-host dependencies"
	@echo "  clean         - Clean everything (fresh build, removes base cache)"
	@echo "  clean-base    - Clean base image cache only (rarely needed)"
	@echo "  extract-rootfs - Extract tarball for manual inspection/modification"
	@echo "  compress-rootfs - Compress modified rootfs directory back to tarball"
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Caching System:"
	@echo "  The build is split into two layers for efficiency:"
	@echo ""
	@echo "  BASE LAYER (cached, slow to rebuild ~15-20 min):"
	@echo "    - debootstrap Debian system"
	@echo "    - packages.txt installation"
	@echo "    Stored in: $(ROOTFS_BASE_TAR)"
	@echo ""
	@echo "  OVERLAY LAYER (fast to apply ~1-2 min):"
	@echo "    - configs/network/*, configs/ssh/*"
	@echo "    - scripts/*.sh"
	@echo "    - HPS applications"
	@echo ""
	@echo "  Base is rebuilt automatically when packages.txt changes."
	@echo "  Overlays are rebuilt automatically when configs/scripts change."
	@echo "  No manual cleanup needed - dependency tracking handles everything."
	@echo ""
	@echo "Configuration:"
	@echo "  NETWORK_MODE=dhcp|static"
	@echo "  STATIC_IP=192.168.1.100"
	@echo "  STATIC_GATEWAY=192.168.1.1"
	@echo "  SSH_ENABLED=yes|no"
	@echo "  ROOT_PASSWORD=root"
	@echo ""
	@echo "WSL Configuration:"
	@echo "  WSL_NATIVE_BUILD=1/0   - Force/disable native filesystem build"
	@echo "  WSL_BUILD_DIR=path     - Custom native build directory"
	@echo "  Current: WSL=$(IS_WSL), WindowsFS=$(IS_WINDOWS_FS), NativeBuild=$(WSL_NATIVE_BUILD)"
	@echo ""
	@echo "Examples:"
	@echo "  make rootfs                    # Smart build with automatic dependency tracking"
	@echo "  make rootfs-native             # Force native filesystem build (WSL)"
	@echo "  make rootfs-local              # Force local build (no WSL redirect)"
	@echo "  make overlay-only              # Force overlay rebuild (redundant - make rootfs does this)"
	@echo "  make rebuild                   # Full rebuild from scratch (slow)"
	@echo "  make clean                     # Clean everything for fresh build"
	@echo "  make check-rebuild            # Check what needs rebuilding (dry-run)"
	@echo "  make wsl-status                # Check WSL detection status"
	@echo "  make extract-rootfs            # Extract tarball for manual inspection/modification"
	@echo "  make compress-rootfs           # Compress modified rootfs directory back to tarball"

# Show cache status
show-cache-status:
	@echo -e "$(CYAN)===========================================$(NC)"
	@echo -e "$(CYAN)Rootfs Cache Status$(NC)"
	@echo -e "$(CYAN)===========================================$(NC)"
	@echo ""
	@echo "Base Image Cache:"
	@if [ -f "$(ROOTFS_BASE_TAR)" ]; then \
		size=$$(du -h "$(ROOTFS_BASE_TAR)" | cut -f1); \
		mtime=$$(date -r "$(ROOTFS_BASE_TAR)" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$(ROOTFS_BASE_TAR)" 2>/dev/null | cut -d. -f1); \
		echo -e "  $(GREEN)[CACHED]$(NC) $(ROOTFS_BASE_TAR)"; \
		echo "  Size: $$size | Created: $$mtime"; \
		if [ -f "$(ROOTFS_BASE_HASH)" ]; then \
			echo "  Hash: $$(cat $(ROOTFS_BASE_HASH))"; \
		fi; \
	else \
		echo -e "  $(YELLOW)[NOT CACHED]$(NC) Base image will be built on next 'make rootfs'"; \
		echo "  This will take 15-20 minutes (debootstrap + packages)"; \
	fi
	@echo ""
	@echo "Final Rootfs:"
	@if [ -f "$(ROOTFS_TAR)" ]; then \
		size=$$(du -h "$(ROOTFS_TAR)" | cut -f1); \
		mtime=$$(date -r "$(ROOTFS_TAR)" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$(ROOTFS_TAR)" 2>/dev/null | cut -d. -f1); \
		echo -e "  $(GREEN)[EXISTS]$(NC) $(ROOTFS_TAR)"; \
		echo "  Size: $$size | Created: $$mtime"; \
	else \
		echo -e "  $(YELLOW)[NOT BUILT]$(NC) Run 'make rootfs' to build"; \
	fi
	@echo ""
	@# Check if base needs rebuild
	@current_hash=$$(md5sum $(BASE_SOURCES) 2>/dev/null | md5sum | cut -d' ' -f1); \
	if [ -f "$(ROOTFS_BASE_HASH)" ]; then \
		cached_hash=$$(cat $(ROOTFS_BASE_HASH)); \
		if [ "$$current_hash" = "$$cached_hash" ]; then \
			echo -e "Base cache: $(GREEN)VALID$(NC) (packages.txt unchanged)"; \
		else \
			echo -e "Base cache: $(YELLOW)STALE$(NC) (packages.txt changed)"; \
			echo "  Next 'make rootfs' will rebuild base (~15-20 min)"; \
		fi; \
	else \
		echo -e "Base cache: $(YELLOW)NOT AVAILABLE$(NC)"; \
	fi

# ============================================================================
# WSL Status and Native Build Targets
# ============================================================================

wsl-status:
	@echo "WSL Detection Status"
	@echo "===================="
	@echo "  IS_WSL:           $(IS_WSL)"
	@echo "  IS_WINDOWS_FS:    $(IS_WINDOWS_FS)"
	@echo "  WSL_NATIVE_BUILD: $(WSL_NATIVE_BUILD)"
	@echo "  WSL_BUILD_DIR:    $(WSL_BUILD_DIR)"
	@echo "  Current dir:      $(CURDIR)"
	@echo ""
	@if [ "$(IS_WSL)" = "1" ] && [ "$(IS_WINDOWS_FS)" = "1" ]; then \
		echo -e "$(YELLOW)WARNING: Building on Windows filesystem (/mnt/c/)$(NC)"; \
		echo -e "$(YELLOW)         debootstrap may fail with 'tar' errors$(NC)"; \
		echo -e "$(GREEN)RECOMMENDED: Use 'make rootfs' (auto-redirects to native fs)$(NC)"; \
	elif [ "$(IS_WSL)" = "1" ]; then \
		echo -e "$(GREEN)Building on native Linux filesystem - optimal$(NC)"; \
	else \
		echo -e "$(GREEN)Not running on WSL - native Linux$(NC)"; \
	fi

# Force build on native filesystem (WSL)
rootfs-native:
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Building rootfs on native Linux filesystem"
	@$(MAKE) rootfs-native-internal

rootfs-native-internal:
	@# Refresh sudo session (already validated in rootfs target)
	@if [ "$$(id -u)" -ne 0 ]; then sudo -v 2>/dev/null || true; fi
	@echo ""
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo -e "$(CYAN)NATIVE FILESYSTEM BUILD - SETUP$(NC)"
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Setting up native build environment..."
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Native directory: $(WSL_BUILD_DIR)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Workspace directory: $(BUILD_DIR)"
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo ""
	@mkdir -p $(WSL_BUILD_DIR)
	@# Check base cache validity and copy if available
	@WSL_BASE_TAR="$(WSL_BUILD_DIR)/build/rootfs_base.tar.xz"; \
	WSL_BASE_HASH="$(WSL_BUILD_DIR)/build/.rootfs_base_hash"; \
	current_hash=$$(md5sum $(BASE_SOURCES) 2>/dev/null | md5sum | cut -d' ' -f1); \
	if [ -f "$(ROOTFS_BASE_TAR)" ] && [ -f "$(ROOTFS_BASE_HASH)" ]; then \
		cached_hash=$$(cat $(ROOTFS_BASE_HASH)); \
		if [ "$$current_hash" = "$$cached_hash" ]; then \
			echo -e "$(GREEN)[CACHE HIT]$(NC) Base image is valid - copying to native filesystem"; \
			mkdir -p $$(dirname $$WSL_BASE_TAR); \
			cp -f $(ROOTFS_BASE_TAR) $$WSL_BASE_TAR; \
			cp -f $(ROOTFS_BASE_HASH) $$WSL_BASE_HASH; \
		else \
			echo -e "$(YELLOW)[CACHE STALE]$(NC) packages.txt changed - will rebuild base"; \
		fi; \
	else \
		echo -e "$(YELLOW)[CACHE MISS]$(NC) No base cache found - will build from scratch"; \
	fi
	@# Copy necessary files to native filesystem
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Copying build files..."
	@cp -f $(BUILD_SCRIPT) $(WSL_BUILD_DIR)/
	@cp -f $(CURDIR)/packages.txt $(WSL_BUILD_DIR)/ 2>/dev/null || true
	@cp -rf $(CURDIR)/configs $(WSL_BUILD_DIR)/ 2>/dev/null || true
	@cp -rf $(CURDIR)/scripts $(WSL_BUILD_DIR)/ 2>/dev/null || true
	@# Create a proper Makefile for the native build with caching support
	@echo 'SHELL := /bin/bash' > $(WSL_BUILD_DIR)/Makefile.native
	@echo 'BUILD_DIR := $(WSL_BUILD_DIR)/build' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo 'ROOTFS_DIR := $$(BUILD_DIR)/rootfs' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo 'ROOTFS_TAR := $$(BUILD_DIR)/rootfs.tar.xz' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo 'ROOTFS_BASE_TAR := $$(BUILD_DIR)/rootfs_base.tar.xz' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo 'ROOTFS_BASE_HASH := $$(BUILD_DIR)/.rootfs_base_hash' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo 'BASE_SOURCES := packages.txt' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '.PHONY: build base-image' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo 'build: base-image' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '	@# Check if we can use cached base' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '	@if [ -f "$$(ROOTFS_BASE_TAR)" ]; then \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		echo "[CACHE HIT] Using cached base image"; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		mkdir -p $$(ROOTFS_DIR); \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		tar -xJf $$(ROOTFS_BASE_TAR) -C $$(ROOTFS_DIR); \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '	else \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		echo "[CACHE MISS] Base image not found - full build required"; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		$$(MAKE) base-image; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		mkdir -p $$(ROOTFS_DIR); \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		tar -xJf $$(ROOTFS_BASE_TAR) -C $$(ROOTFS_DIR); \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '	fi' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '	@export ROOTFS_DIR="$$(ROOTFS_DIR)" ROOTFS_TAR="$$(ROOTFS_TAR)" BASE_ONLY=0 && bash ./build_rootfs.sh' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo 'base-image:' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '	@set -e; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		current_hash=$$$$(md5sum $$(BASE_SOURCES) 2>/dev/null | md5sum | cut -d" " -f1); \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		if [ -f "$$(ROOTFS_BASE_TAR)" ] && [ -f "$$(ROOTFS_BASE_HASH)" ]; then \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '			cached_hash=$$$$(cat $$(ROOTFS_BASE_HASH)); \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '			if [ "$$$$current_hash" = "$$$$cached_hash" ]; then \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '				echo "[CACHE VALID] Base image is up-to-date"; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '				exit 0; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '			fi; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		fi; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		echo "Building Base Image (this takes 15-20 min)..."; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		export ROOTFS_DIR="$$(BUILD_DIR)/rootfs" ROOTFS_TAR="$$(ROOTFS_BASE_TAR)" BASE_ONLY=1 && bash ./build_rootfs.sh; \' >> $(WSL_BUILD_DIR)/Makefile.native
	@echo '		md5sum $$(BASE_SOURCES) 2>/dev/null | md5sum | cut -d" " -f1 > $$(ROOTFS_BASE_HASH)' >> $(WSL_BUILD_DIR)/Makefile.native
	@# Run build on native filesystem (sudo already validated)
	@echo ""
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo -e "$(CYAN)RUNNING BUILD IN NATIVE DOCKER VOLUME$(NC)"
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Location: $(WSL_BUILD_DIR)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | This supports device node creation for debootstrap"
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo ""
	@if [ "$$(id -u)" -eq 0 ]; then \
		cd $(WSL_BUILD_DIR) && make -f Makefile.native build; \
	else \
		cd $(WSL_BUILD_DIR) && sudo -E make -f Makefile.native build; \
	fi
	@# Copy results back and update cache
	@echo ""
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo -e "$(CYAN)COPYING ARTIFACTS TO WORKSPACE$(NC)"
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | From: $(WSL_BUILD_DIR)/build/"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | To:   $(BUILD_DIR)/"
	@echo -e "$(CYAN)============================================================================$(NC)"
	@echo ""
	@mkdir -p $(BUILD_DIR)
	@cp -f $(WSL_BUILD_DIR)/build/rootfs.tar.xz $(ROOTFS_TAR)
	@if [ -f "$(WSL_BUILD_DIR)/build/rootfs_base.tar.xz" ]; then \
		cp -f $(WSL_BUILD_DIR)/build/rootfs_base.tar.xz $(ROOTFS_BASE_TAR); \
		cp -f $(WSL_BUILD_DIR)/build/.rootfs_base_hash $(ROOTFS_BASE_HASH) 2>/dev/null || true; \
		echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Base image cached: $$(du -h $(ROOTFS_BASE_TAR) | cut -f1)"; \
	fi
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Final rootfs: $$(du -h $(ROOTFS_TAR) | cut -f1)"
	@echo ""
	@echo -e "$(GREEN)============================================================================$(NC)"
	@echo -e "$(GREEN)NATIVE BUILD COMPLETE - ARTIFACTS READY$(NC)"
	@echo -e "$(GREEN)============================================================================$(NC)"
	@echo -e "$(GREEN)Base:  $(ROOTFS_BASE_TAR)$(NC)"
	@echo -e "$(GREEN)Final: $(ROOTFS_TAR)$(NC)"
	@echo -e "$(GREEN)============================================================================$(NC)"
	@echo ""

# Force build in current directory (no WSL redirect)
rootfs-local: rootfs-local-internal
	@echo -e "$(GREEN)Rootfs built locally$(NC)"

rootfs-local-internal: deps-check $(ROOTFS_BASE_TAR) $(OVERLAY_SOURCES)
	@$(MAKE) rootfs-build-internal

# Main rootfs target - depends on the actual file
# Make will automatically skip if ROOTFS_TAR is up-to-date
rootfs: $(ROOTFS_TAR)
	@echo -e "$(GREEN)Rootfs ready: $(ROOTFS_TAR)$(NC)"
	@set -e; \
	if [ "$$(id -u)" -ne 0 ]; then \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Validating sudo access..."; \
		if ! sudo -n true 2>/dev/null; then \
			echo -e "$(YELLOW)Rootfs build requires sudo privileges.$(NC)"; \
			echo -e "$(YELLOW)Please enter your password (will be cached for this build):$(NC)"; \
			sudo -v || (echo -e "$(RED)ERROR: Sudo authentication failed$(NC)" && exit 1); \
		fi; \
		sudo -v; \
	fi; \
	if [ "$(WSL_NATIVE_BUILD)" = "1" ]; then \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | WSL detected with Windows filesystem"; \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Redirecting build to native filesystem: $(WSL_BUILD_DIR)"; \
		$(MAKE) rootfs-native; \
	else \
		$(MAKE) rootfs-local-internal; \
	fi

# Internal build target - actual rootfs creation
# Make will automatically skip this if ROOTFS_TAR is newer than all dependencies
$(ROOTFS_TAR): deps-check $(ROOTFS_BASE_TAR) $(OVERLAY_SOURCES)
	@# Make's dependency system automatically skips this if ROOTFS_TAR is newer than dependencies
	@# We need to handle WSL detection and build
	@set -e; \
	if [ "$$(id -u)" -ne 0 ]; then \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Validating sudo access..."; \
		if ! sudo -n true 2>/dev/null; then \
			echo -e "$(YELLOW)Rootfs build requires sudo privileges.$(NC)"; \
			echo -e "$(YELLOW)Please enter your password (will be cached for this build):$(NC)"; \
			sudo -v || (echo -e "$(RED)ERROR: Sudo authentication failed$(NC)" && exit 1); \
		fi; \
		sudo -v; \
	fi; \
	if [ "$(WSL_NATIVE_BUILD)" = "1" ]; then \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | WSL detected with Windows filesystem"; \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Redirecting build to native filesystem: $(WSL_BUILD_DIR)"; \
		$(MAKE) rootfs-native; \
	else \
		$(MAKE) rootfs-build-internal; \
	fi

rootfs-build-internal:
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Building final rootfs with overlays..."
	@# Check if we can use cached base
	@if [ -f "$(ROOTFS_BASE_TAR)" ]; then \
		echo -e "$(GREEN)[CACHE HIT]$(NC) Using cached base image"; \
		echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Base: $(ROOTFS_BASE_TAR)"; \
	else \
		echo -e "$(YELLOW)[CACHE MISS]$(NC) Base image not found - full build required"; \
		$(MAKE) base-image; \
	fi
	@# Extract base and apply overlays
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Extracting base image..."
	@mkdir -p $(ROOTFS_DIR)
	@if [ -d "$(ROOTFS_DIR)" ] && [ "$$(ls -A $(ROOTFS_DIR) 2>/dev/null)" ]; then \
		echo -e "$(YELLOW)Cleaning existing rootfs directory...$(NC)"; \
		for mp in $(ROOTFS_DIR)/proc $(ROOTFS_DIR)/sys $(ROOTFS_DIR)/dev; do \
			mountpoint -q "$$mp" 2>/dev/null && umount "$$mp" 2>/dev/null || true; \
		done; \
		rm -rf $(ROOTFS_DIR)/*; \
	fi
	@tar -xJf $(ROOTFS_BASE_TAR) -C $(ROOTFS_DIR)
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Applying overlays..."
	@$(MAKE) apply-overlays
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Creating final tarball..."
	@# Remove qemu-arm-static before packaging
	@rm -f $(ROOTFS_DIR)/usr/bin/qemu-arm-static
	@tar -cJf $(ROOTFS_TAR) -C $(ROOTFS_DIR) .
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Rootfs tarball created: $(ROOTFS_TAR)"
	@size=$$(du -h $(ROOTFS_TAR) | cut -f1); \
	echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Size: $$size"

# Build base image (debootstrap + packages) - cached
base-image: $(ROOTFS_BASE_TAR)
	@echo -e "$(GREEN)Base image ready$(NC)"

$(ROOTFS_BASE_TAR): deps-check $(BASE_SOURCES)
	@# If running under WSL on a Windows filesystem (/mnt/*), build the base image
	@# via the native-filesystem workflow to avoid debootstrap/tar extraction failures.
	@if [ "$(WSL_NATIVE_BUILD)" = "1" ]; then \
		echo ""; \
		echo -e "$(YELLOW)============================================================================$(NC)"; \
		echo -e "$(YELLOW)NATIVE FILESYSTEM BUILD REQUIRED$(NC)"; \
		echo -e "$(YELLOW)============================================================================$(NC)"; \
		echo -e "$(YELLOW)Docker bind mounts (macOS) don't support device nodes needed by debootstrap$(NC)"; \
		echo -e "$(YELLOW)Building in native Docker volume instead: $(WSL_BUILD_DIR)$(NC)"; \
		echo -e "$(YELLOW)This is automatic and transparent - no action needed$(NC)"; \
		echo -e "$(YELLOW)============================================================================$(NC)"; \
		echo ""; \
		$(MAKE) rootfs-native; \
		if [ ! -f "$(ROOTFS_BASE_TAR)" ]; then \
			echo -e "$(RED)============================================================================$(NC)"; \
			echo -e "$(RED)ERROR: Native build failed to produce base tarball$(NC)"; \
			echo -e "$(RED)Expected: $(ROOTFS_BASE_TAR)$(NC)"; \
			echo -e "$(RED)============================================================================$(NC)"; \
			exit 1; \
		fi; \
		echo ""; \
		echo -e "$(GREEN)============================================================================$(NC)"; \
		echo -e "$(GREEN)NATIVE BUILD SUCCESSFUL$(NC)"; \
		echo -e "$(GREEN)============================================================================$(NC)"; \
		echo -e "$(GREEN)Base image: $(ROOTFS_BASE_TAR) ($$(du -h $(ROOTFS_BASE_TAR) | cut -f1))$(NC)"; \
		echo -e "$(GREEN)Artifact successfully copied from native volume to workspace$(NC)"; \
		echo -e "$(GREEN)============================================================================$(NC)"; \
		echo ""; \
		exit 0; \
	fi
	@# Check if cached base is still valid
	@current_hash=$$(md5sum $(BASE_SOURCES) 2>/dev/null | md5sum | cut -d' ' -f1); \
	if [ -f "$(ROOTFS_BASE_TAR)" ] && [ -f "$(ROOTFS_BASE_HASH)" ]; then \
		cached_hash=$$(cat $(ROOTFS_BASE_HASH)); \
		if [ "$$current_hash" = "$$cached_hash" ]; then \
			echo -e "$(GREEN)[CACHE VALID]$(NC) Base image is up-to-date"; \
			echo "  Skipping debootstrap (use 'make clean-base' to force rebuild)"; \
			touch "$(ROOTFS_BASE_TAR)" 2>/dev/null || true; \
			exit 0; \
		else \
			echo -e "$(YELLOW)[CACHE STALE]$(NC) packages.txt changed - rebuilding base"; \
		fi; \
	fi
	@echo -e "$(CYAN)===========================================$(NC)"
	@echo -e "$(CYAN)Building Base Image (this takes 15-20 min)$(NC)"
	@echo -e "$(CYAN)===========================================$(NC)"
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Running debootstrap + package installation..."
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | This creates the cached base image"
	@echo ""
	@echo -e "$(YELLOW)WARNING: This path should not run when WSL_NATIVE_BUILD=1$(NC)"
	@echo -e "$(YELLOW)WARNING: Building in workspace - device nodes may not work$(NC)"
	@echo ""
	@# Run build script with BASE_ONLY mode
	@set -e; \
		tmp_script="$(BUILD_DIR)/.build_rootfs_base.normalized.$$$$"; \
		trap 'rm -f "$$tmp_script"' EXIT; \
		mkdir -p $(BUILD_DIR); \
		tr -d '\015' < "$(BUILD_SCRIPT)" > "$$tmp_script"; \
		chmod +x "$$tmp_script"; \
		export ROOTFS_DIR="$(ROOTFS_DIR)"; \
		export ROOTFS_TAR="$(ROOTFS_BASE_TAR)"; \
		export BASE_ONLY=1; \
		if [ "$$(id -u)" -eq 0 ]; then \
			bash "$$tmp_script"; \
		else \
			echo "Base image build requires root access"; \
			sudo -E bash "$$tmp_script"; \
		fi
	@# Save hash of sources used to build this base
	@md5sum $(BASE_SOURCES) 2>/dev/null | md5sum | cut -d' ' -f1 > $(ROOTFS_BASE_HASH)
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Base image cached: $(ROOTFS_BASE_TAR)"
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Future builds will be much faster"

# Apply overlays (configs, scripts) - fast operation
.PHONY: apply-overlays
apply-overlays:
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Applying configuration overlays..."
	@# Mount required filesystems
	@mount -t proc proc $(ROOTFS_DIR)/proc 2>/dev/null || true
	@mount -t sysfs sysfs $(ROOTFS_DIR)/sys 2>/dev/null || true
	@mount -o bind /dev $(ROOTFS_DIR)/dev 2>/dev/null || true
	@# Copy qemu for chroot
	@if [ -f /usr/bin/qemu-arm-static ]; then \
		mkdir -p $(ROOTFS_DIR)/usr/bin; \
		cp /usr/bin/qemu-arm-static $(ROOTFS_DIR)/usr/bin/; \
	fi
	@# Apply network config
	@if [ -d "$(CURDIR)/configs/network" ]; then \
		for f in $(CURDIR)/configs/network/*; do \
			if [ -f "$$f" ]; then \
				mkdir -p $(ROOTFS_DIR)/etc/network; \
				tr -d '\015' < "$$f" > $(ROOTFS_DIR)/etc/network/$$(basename "$$f"); \
			fi; \
		done; \
		echo "  Applied network configuration"; \
	fi
	@# Apply SSH config  
	@if [ -d "$(CURDIR)/configs/ssh" ]; then \
		for f in $(CURDIR)/configs/ssh/*; do \
			if [ -f "$$f" ]; then \
				mkdir -p $(ROOTFS_DIR)/etc/ssh; \
				tr -d '\015' < "$$f" > $(ROOTFS_DIR)/etc/ssh/$$(basename "$$f"); \
			fi; \
		done; \
		echo "  Applied SSH configuration"; \
	fi
	@# Run post-install scripts
	@if [ -d "$(CURDIR)/scripts" ]; then \
		for script in $(CURDIR)/scripts/*.sh; do \
			if [ -f "$$script" ]; then \
				scriptname=$$(basename "$$script"); \
				echo "  Running $$scriptname..."; \
				tr -d '\015' < "$$script" > $(ROOTFS_DIR)/tmp/$$scriptname; \
				chmod +x $(ROOTFS_DIR)/tmp/$$scriptname; \
				chroot $(ROOTFS_DIR) /bin/bash /tmp/$$scriptname 2>/dev/null || true; \
				rm -f $(ROOTFS_DIR)/tmp/$$scriptname; \
			fi; \
		done; \
	fi
	@# Unmount
	@umount $(ROOTFS_DIR)/dev 2>/dev/null || true
	@umount $(ROOTFS_DIR)/sys 2>/dev/null || true
	@umount $(ROOTFS_DIR)/proc 2>/dev/null || true
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Overlays applied"

# Fast rebuild - only apply overlays (requires existing base)
overlay-only:
	@if [ ! -f "$(ROOTFS_BASE_TAR)" ]; then \
		echo -e "$(YELLOW)No base image found - running full build$(NC)"; \
		$(MAKE) rootfs; \
		exit 0; \
	fi
	@echo -e "$(CYAN)===========================================$(NC)"
	@echo -e "$(CYAN)Fast Rebuild (overlays only)$(NC)"
	@echo -e "$(CYAN)===========================================$(NC)"
	@rm -f $(ROOTFS_TAR)
	@$(MAKE) $(ROOTFS_TAR)

deps:
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Installing Build-Host Dependencies$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Installing build-host dependencies...$(NC)"
	@if ! command -v apt-get >/dev/null 2>&1; then \
		echo "ERROR: apt-get not found. Install dependencies manually for your distro:"; \
		echo "  debootstrap, qemu-user-static (or qemu-debootstrap), debian-archive-keyring, ca-certificates, gnupg (gpgv), wget or curl"; \
		exit 1; \
	fi
	@set -e; \
		tmp_check="../scripts/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\015' < "../scripts/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "apt repositories (build-host dependencies)" --url "https://deb.debian.org" --url "https://security.debian.org"
	@if [ "$$(id -u)" -ne 0 ]; then \
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
		if [ $$missing -ne 0 ]; then \
			echo ""; \
			echo "Install prerequisites with:"; \
			echo "  make deps"; \
			exit 1; \
		fi; \
		echo "All build-host dependencies satisfied"; \
	'

# Force rebuild - always rebuilds from scratch (including base)
rebuild: clean-all
	@$(MAKE) rootfs

force-rebuild: rebuild

# Check if rebuild is needed by comparing timestamps
check-rebuild:
	@echo -e "$(CYAN)Checking if rebuild is needed...$(NC)"
	@needs_rebuild=0; \
	needs_base=0; \
	if [ ! -f "$(ROOTFS_TAR)" ]; then \
		echo -e "$(YELLOW)Rebuild needed: rootfs.tar.xz does not exist$(NC)"; \
		needs_rebuild=1; \
	fi; \
	if [ ! -f "$(ROOTFS_BASE_TAR)" ]; then \
		echo -e "$(YELLOW)Base rebuild needed: base image does not exist$(NC)"; \
		needs_base=1; \
	else \
		current_hash=$$(md5sum $(BASE_SOURCES) 2>/dev/null | md5sum | cut -d' ' -f1); \
		if [ -f "$(ROOTFS_BASE_HASH)" ]; then \
			cached_hash=$$(cat $(ROOTFS_BASE_HASH)); \
			if [ "$$current_hash" != "$$cached_hash" ]; then \
				echo -e "$(YELLOW)Base rebuild needed: packages.txt changed$(NC)"; \
				needs_base=1; \
			fi; \
		else \
			echo -e "$(YELLOW)Base rebuild needed: no hash file$(NC)"; \
			needs_base=1; \
		fi; \
	fi; \
	for src in $(OVERLAY_SOURCES); do \
		if [ -f "$$src" ] && [ -f "$(ROOTFS_TAR)" ] && [ "$$src" -nt "$(ROOTFS_TAR)" ]; then \
			echo -e "$(YELLOW)Overlay rebuild needed: $$src changed$(NC)"; \
			needs_rebuild=1; \
			break; \
		fi; \
	done; \
	if [ $$needs_base -eq 1 ]; then \
		echo -e "$(YELLOW)RESULT: Full rebuild required (~15-20 min)$(NC)"; \
	elif [ $$needs_rebuild -eq 1 ]; then \
		echo -e "$(YELLOW)RESULT: Overlay rebuild required (~1-2 min)$(NC)"; \
	else \
		echo -e "$(GREEN)RESULT: No rebuild needed - rootfs is up-to-date$(NC)"; \
	fi

# Clean rootfs and old build files (fresh build)
# Note: Normal 'make rootfs' handles incremental builds automatically via dependency tracking
# Use 'make clean' only when you want a completely fresh build
clean:
	@echo -e "$(YELLOW)Cleaning rootfs (fresh build)...$(NC)"
	@# Unmount any mounted filesystems
	@for mp in $(ROOTFS_DIR)/proc $(ROOTFS_DIR)/sys $(ROOTFS_DIR)/dev; do \
		mountpoint -q "$$mp" 2>/dev/null && umount "$$mp" 2>/dev/null || true; \
	done
	@rm -rf $(ROOTFS_DIR)
	@rm -f $(ROOTFS_TAR)
	@# Remove old .tar.gz files (no longer used, replaced by .tar.xz)
	@rm -f $(BUILD_DIR)/rootfs.tar.gz $(BUILD_DIR)/rootfs_base.tar.gz
	@# Clean base cache for truly fresh build
	@$(MAKE) clean-base
	@echo -e "$(GREEN)Clean complete (fresh build on next 'make rootfs')$(NC)"
	@echo -e "$(YELLOW)Next 'make rootfs' will do full build (~15-20 min)$(NC)"
	@echo -e "$(CYAN)Note: Normal 'make rootfs' automatically handles incremental builds$(NC)"

# Clean base image cache (forces full rebuild)
clean-base:
	@echo -e "$(YELLOW)Cleaning base image cache...$(NC)"
	@rm -f $(ROOTFS_BASE_TAR)
	@rm -f $(ROOTFS_BASE_HASH)
	@# Remove old .tar.gz base files if they exist
	@rm -f $(BUILD_DIR)/rootfs_base.tar.gz
	@echo -e "$(GREEN)Base cache cleared$(NC)"
	@echo -e "$(YELLOW)Next 'make rootfs' will do full build (~15-20 min)$(NC)"

# Clean everything (clean already includes base cache)
clean-all: clean
	@echo -e "$(GREEN)All rootfs artifacts cleaned$(NC)"

# Extract rootfs tarball to directory (for use in SD image creation)
extract-rootfs:
	@if [ ! -f "$(ROOTFS_TAR)" ]; then \
		echo -e "$(RED)ERROR: Rootfs tarball not found: $(ROOTFS_TAR)$(NC)"; \
		echo "  Run 'make rootfs' first to build the rootfs"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Extracting rootfs tarball..."
	@mkdir -p $(ROOTFS_DIR)
	@if [ -d "$(ROOTFS_DIR)" ] && [ "$$(ls -A $(ROOTFS_DIR) 2>/dev/null)" ]; then \
		echo -e "$(YELLOW)Cleaning existing rootfs directory...$(NC)"; \
		for mp in $(ROOTFS_DIR)/proc $(ROOTFS_DIR)/sys $(ROOTFS_DIR)/dev; do \
			mountpoint -q "$$mp" 2>/dev/null && umount "$$mp" 2>/dev/null || true; \
		done; \
		rm -rf $(ROOTFS_DIR)/*; \
	fi
	@tar -xJf $(ROOTFS_TAR) -C $(ROOTFS_DIR)
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Rootfs extracted to: $(ROOTFS_DIR)"

# Compress rootfs directory to tarball (after modifications)
compress-rootfs:
	@if [ ! -d "$(ROOTFS_DIR)" ] || [ -z "$$(ls -A $(ROOTFS_DIR) 2>/dev/null)" ]; then \
		echo -e "$(RED)ERROR: Rootfs directory is empty or does not exist: $(ROOTFS_DIR)$(NC)"; \
		echo "  Extract or build rootfs first"; \
		exit 1; \
	fi
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Compressing rootfs directory..."
	@# Remove qemu-arm-static before packaging
	@rm -f $(ROOTFS_DIR)/usr/bin/qemu-arm-static
	@tar -cJf $(ROOTFS_TAR) -C $(ROOTFS_DIR) .
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Rootfs tarball created: $(ROOTFS_TAR)"
	@size=$$(du -h $(ROOTFS_TAR) | cut -f1); \
	echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Size: $$size"
