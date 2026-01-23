# ============================================================================
# Root Filesystem Build Makefile
# ============================================================================
# Automated rootfs build with configuration management
# ============================================================================

SHELL := /bin/bash

# Configuration
ROOTFS_DIR := $(CURDIR)/build/rootfs
ROOTFS_TAR := $(CURDIR)/build/rootfs.tar.gz
BUILD_SCRIPT := $(CURDIR)/build_rootfs.sh
DEPS_PACKAGES := debootstrap qemu-user-static debian-archive-keyring ca-certificates gnupg wget

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

.PHONY: all rootfs deps deps-check clean help

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
	@echo "  all     - Build rootfs (default)"
	@echo "  rootfs  - Build rootfs tarball"
	@echo "  deps    - Install build-host dependencies (Debian/Ubuntu/WSL)"
	@echo "  deps-check - Verify build-host dependencies are installed"
	@echo "  clean   - Clean build artifacts"
	@echo "  help    - Show this help message"
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

$(ROOTFS_TAR): deps-check $(BUILD_SCRIPT)
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
