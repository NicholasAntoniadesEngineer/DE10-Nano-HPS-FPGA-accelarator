# ============================================================================
# Root Filesystem Build Makefile
# ============================================================================
# Automated rootfs build with configuration management
# Supports:
#   - Incremental builds (only rebuilds when source files change)
#   - Base image caching (dramatically speeds up repeated builds)
#   - Layered architecture (base system + overlays)
# ============================================================================

SHELL := /bin/bash

# Configuration
BUILD_DIR := $(CURDIR)/build
ROOTFS_DIR := $(BUILD_DIR)/rootfs
ROOTFS_TAR := $(BUILD_DIR)/rootfs.tar.gz
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

ROOTFS_BASE_TAR := $(BUILD_DIR)/rootfs_base.tar.gz
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

all: rootfs
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Rootfs build complete$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Rootfs tarball: $(ROOTFS_TAR)$(NC)"

help:
	@echo "Root Filesystem Build System"
	@echo "============================"
	@echo ""
	@echo "Targets:"
	@echo "  all           - Build rootfs if needed (default, uses caching)"
	@echo "  rootfs        - Build rootfs tarball (with base caching)"
	@echo "  base-image    - Build/cache base image only (debootstrap + packages)"
	@echo "  overlay-only  - Apply overlays to cached base (fast rebuild)"
	@echo "  rebuild       - Force rebuild everything from scratch"
	@echo "  force-rebuild - Alias for rebuild"
	@echo "  check-rebuild - Check if rebuild is needed (dry-run)"
	@echo "  show-cache-status - Show base image cache status"
	@echo "  deps          - Install build-host dependencies"
	@echo "  deps-check    - Verify build-host dependencies"
	@echo "  clean         - Clean final rootfs only (keeps base cache)"
	@echo "  clean-base    - Clean base image cache (next build will be slow)"
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
	@echo "  Base is rebuilt only when packages.txt changes."
	@echo "  Overlays are always applied fresh."
	@echo ""
	@echo "Configuration:"
	@echo "  NETWORK_MODE=dhcp|static"
	@echo "  STATIC_IP=192.168.1.100"
	@echo "  STATIC_GATEWAY=192.168.1.1"
	@echo "  SSH_ENABLED=yes|no"
	@echo "  ROOT_PASSWORD=root"
	@echo ""
	@echo "Examples:"
	@echo "  make rootfs                    # Smart build with caching"
	@echo "  make overlay-only              # Fast: only apply configs"
	@echo "  make rebuild                   # Full rebuild (slow)"
	@echo "  make clean-base && make rootfs # Refresh base image"

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

rootfs: $(ROOTFS_TAR)
	@echo -e "$(GREEN)Rootfs built successfully$(NC)"

# Main build target - uses caching
$(ROOTFS_TAR): deps-check $(ROOTFS_BASE_TAR) $(OVERLAY_SOURCES)
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
	@tar -xzf $(ROOTFS_BASE_TAR) -C $(ROOTFS_DIR)
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Applying overlays..."
	@$(MAKE) apply-overlays
	@echo -e "$(CYAN)[INFO]$(NC) $(TIMESTAMP) | Creating final tarball..."
	@# Remove qemu-arm-static before packaging
	@rm -f $(ROOTFS_DIR)/usr/bin/qemu-arm-static
	@tar -czf $(ROOTFS_TAR) -C $(ROOTFS_DIR) .
	@echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Rootfs tarball created: $(ROOTFS_TAR)"
	@size=$$(du -h $(ROOTFS_TAR) | cut -f1); \
	echo -e "$(GREEN)[OK]$(NC) $(TIMESTAMP) | Size: $$size"

# Build base image (debootstrap + packages) - cached
base-image: $(ROOTFS_BASE_TAR)
	@echo -e "$(GREEN)Base image ready$(NC)"

$(ROOTFS_BASE_TAR): deps-check $(BASE_SOURCES)
	@# Check if cached base is still valid
	@current_hash=$$(md5sum $(BASE_SOURCES) 2>/dev/null | md5sum | cut -d' ' -f1); \
	if [ -f "$(ROOTFS_BASE_TAR)" ] && [ -f "$(ROOTFS_BASE_HASH)" ]; then \
		cached_hash=$$(cat $(ROOTFS_BASE_HASH)); \
		if [ "$$current_hash" = "$$cached_hash" ]; then \
			echo -e "$(GREEN)[CACHE VALID]$(NC) Base image is up-to-date"; \
			echo "  Skipping debootstrap (use 'make clean-base' to force rebuild)"; \
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
	@# Run build script with BASE_ONLY mode
	@set -e; \
		tmp_script="$(BUILD_DIR)/.build_rootfs_base.normalized.$$$$"; \
		trap 'rm -f "$$tmp_script"' EXIT; \
		mkdir -p $(BUILD_DIR); \
		tr -d '\r' < "$(BUILD_SCRIPT)" > "$$tmp_script"; \
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
				tr -d '\r' < "$$f" > $(ROOTFS_DIR)/etc/network/$$(basename "$$f"); \
			fi; \
		done; \
		echo "  Applied network configuration"; \
	fi
	@# Apply SSH config  
	@if [ -d "$(CURDIR)/configs/ssh" ]; then \
		for f in $(CURDIR)/configs/ssh/*; do \
			if [ -f "$$f" ]; then \
				mkdir -p $(ROOTFS_DIR)/etc/ssh; \
				tr -d '\r' < "$$f" > $(ROOTFS_DIR)/etc/ssh/$$(basename "$$f"); \
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
				tr -d '\r' < "$$script" > $(ROOTFS_DIR)/tmp/$$scriptname; \
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
		tr -d '\r' < "../scripts/check_internet.sh" > "$$tmp_check"; \
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

# Check if rebuild is needed by comparing timestamps
check-rebuild:
	@if [ ! -f "$(ROOTFS_TAR)" ]; then \
		echo -e "$(YELLOW)Rebuild needed: rootfs.tar.gz does not exist$(NC)"; \
		exit 0; \
	fi; \
	needs_rebuild=0; \
	for src in $(ROOTFS_SOURCES); do \
		if [ -f "$$src" ] && [ "$$src" -nt "$(ROOTFS_TAR)" ]; then \
			echo -e "$(YELLOW)Rebuild needed: $$src is newer than rootfs.tar.gz$(NC)"; \
			needs_rebuild=1; \
		fi; \
	done; \
	if [ $$needs_rebuild -eq 0 ]; then \
		echo -e "$(GREEN)No rebuild needed: rootfs.tar.gz is up-to-date$(NC)"; \
	fi

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
		echo -e "$(YELLOW)Rebuild needed: rootfs.tar.gz does not exist$(NC)"; \
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

# Clean only final rootfs (keeps base cache for fast rebuilds)
clean:
	@echo -e "$(YELLOW)Cleaning rootfs (keeping base cache)...$(NC)"
	@# Unmount any mounted filesystems
	@for mp in $(ROOTFS_DIR)/proc $(ROOTFS_DIR)/sys $(ROOTFS_DIR)/dev; do \
		mountpoint -q "$$mp" 2>/dev/null && umount "$$mp" 2>/dev/null || true; \
	done
	@rm -rf $(ROOTFS_DIR)
	@rm -f $(ROOTFS_TAR)
	@echo -e "$(GREEN)Clean complete (base cache preserved)$(NC)"
	@if [ -f "$(ROOTFS_BASE_TAR)" ]; then \
		echo -e "$(GREEN)Base cache: $(ROOTFS_BASE_TAR)$(NC)"; \
		echo -e "$(YELLOW)Next 'make rootfs' will be fast (~1-2 min)$(NC)"; \
	fi

# Clean base image cache (forces full rebuild)
clean-base:
	@echo -e "$(YELLOW)Cleaning base image cache...$(NC)"
	@rm -f $(ROOTFS_BASE_TAR)
	@rm -f $(ROOTFS_BASE_HASH)
	@echo -e "$(GREEN)Base cache cleared$(NC)"
	@echo -e "$(YELLOW)Next 'make rootfs' will do full build (~15-20 min)$(NC)"

# Clean everything including base cache
clean-all: clean clean-base
	@echo -e "$(GREEN)All rootfs artifacts cleaned$(NC)"
