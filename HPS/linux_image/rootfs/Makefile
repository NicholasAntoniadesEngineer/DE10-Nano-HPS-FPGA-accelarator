# ============================================================================
# Root Filesystem Build Makefile
# ============================================================================
# Automated rootfs build with configuration management
# Supports incremental builds - only rebuilds when source files change
# ============================================================================

SHELL := /bin/bash

# Configuration
ROOTFS_DIR := $(CURDIR)/build/rootfs
ROOTFS_TAR := $(CURDIR)/build/rootfs.tar.gz
BUILD_SCRIPT := $(CURDIR)/build_rootfs.sh
DEPS_PACKAGES := debootstrap qemu-user-static debian-archive-keyring ca-certificates gnupg wget

# Source files that trigger a rebuild when changed
ROOTFS_SOURCES := $(BUILD_SCRIPT) \
                  $(CURDIR)/packages.txt \
                  $(wildcard $(CURDIR)/configs/network/*) \
                  $(wildcard $(CURDIR)/configs/ssh/*) \
                  $(wildcard $(CURDIR)/scripts/*.sh)

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

.PHONY: all rootfs deps deps-check clean help rebuild force-rebuild check-rebuild

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
	@echo "  all           - Build rootfs if needed (default, incremental)"
	@echo "  rootfs        - Build rootfs tarball (incremental - skips if up-to-date)"
	@echo "  rebuild       - Force rebuild rootfs from scratch"
	@echo "  force-rebuild - Alias for rebuild"
	@echo "  check-rebuild - Check if rebuild is needed (dry-run)"
	@echo "  deps          - Install build-host dependencies (Debian/Ubuntu/WSL)"
	@echo "  deps-check    - Verify build-host dependencies are installed"
	@echo "  clean         - Clean build artifacts"
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Incremental Build:"
	@echo "  The build system tracks these source files:"
	@echo "    - build_rootfs.sh"
	@echo "    - packages.txt"
	@echo "    - configs/network/*, configs/ssh/*"
	@echo "    - scripts/*.sh"
	@echo "  If none of these have changed since the last build,"
	@echo "  the existing rootfs.tar.gz will be reused."
	@echo ""
	@echo "Configuration:"
	@echo "  Set environment variables before running:"
	@echo "    NETWORK_MODE=dhcp|static"
	@echo "    STATIC_IP=192.168.1.100"
	@echo "    STATIC_GATEWAY=192.168.1.1"
	@echo "    SSH_ENABLED=yes|no"
	@echo "    ROOT_PASSWORD=root"
	@echo ""
	@echo "Example:"
	@echo "  make NETWORK_MODE=static STATIC_IP=192.168.1.100 rootfs"
	@echo "  make rebuild   # Force full rebuild"

rootfs: $(ROOTFS_TAR)
	@echo -e "$(GREEN)Rootfs built successfully$(NC)"

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

# Force rebuild - always rebuilds from scratch
rebuild: clean
	@$(MAKE) $(ROOTFS_TAR) FORCE_REBUILD=1

force-rebuild: rebuild

# Main build target with incremental support
$(ROOTFS_TAR): deps-check $(ROOTFS_SOURCES)
	@needs_rebuild=0; \
	if [ ! -f "$(ROOTFS_TAR)" ]; then \
		echo -e "$(YELLOW)Building rootfs: tarball does not exist$(NC)"; \
		needs_rebuild=1; \
	else \
		for src in $(ROOTFS_SOURCES); do \
			if [ -f "$$src" ] && [ "$$src" -nt "$(ROOTFS_TAR)" ]; then \
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
		echo -e "$(GREEN)Rootfs is up-to-date - skipping build$(NC)"; \
		echo -e "$(GREEN)===========================================$(NC)"; \
		echo -e "$(GREEN)Existing tarball: $(ROOTFS_TAR)$(NC)"; \
		tarball_size=$$(du -h "$(ROOTFS_TAR)" | cut -f1); \
		tarball_date=$$(date -r "$(ROOTFS_TAR)" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$(ROOTFS_TAR)" 2>/dev/null | cut -d. -f1); \
		echo -e "$(GREEN)Size: $$tarball_size | Built: $$tarball_date$(NC)"; \
		echo ""; \
		echo -e "$(YELLOW)To force rebuild: make rebuild$(NC)"; \
		exit 0; \
	fi
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(GREEN)Root Filesystem Build$(NC)"
	@echo -e "$(GREEN)===========================================$(NC)"
	@echo -e "$(YELLOW)Building rootfs...$(NC)"
	@echo -e "$(YELLOW)This requires root access and may take 10-20 minutes...$(NC)"
	@set -e; \
		tmp_check="../scripts/.check_internet.normalized.$$$$"; \
		trap 'rm -f "$$tmp_check"' EXIT; \
		tr -d '\r' < "../scripts/check_internet.sh" > "$$tmp_check"; \
		chmod +x "$$tmp_check"; \
		"$$tmp_check" --name "Debian mirrors (debootstrap/apt)" --url "https://deb.debian.org" --url "https://security.debian.org"
	@if [ "$(shell id -u)" -ne 0 ]; then \
		echo -e "$(YELLOW)Note: This requires root access. Run with: sudo make rootfs$(NC)"; \
		echo -e "$(YELLOW)If it looks stuck, sudo is waiting for your password (input is hidden).$(NC)"; \
		sudo -v; \
		sudo bash $(BUILD_SCRIPT); \
	else \
		bash $(BUILD_SCRIPT); \
	fi

clean:
	@echo -e "$(YELLOW)Cleaning rootfs build...$(NC)"
	@rm -rf $(CURDIR)/build
	@echo -e "$(GREEN)Clean complete$(NC)"
