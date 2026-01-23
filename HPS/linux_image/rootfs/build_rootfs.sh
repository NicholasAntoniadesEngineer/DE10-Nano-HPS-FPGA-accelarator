#!/bin/bash
# ============================================================================
# Root Filesystem Build Script for DE10-Nano
# ============================================================================
# Creates Debian-based rootfs with network and SSH pre-configured
# ============================================================================

set -e  # Exit on error

# Cleanup function for temp directory
cleanup_on_exit() {
    if [ "$USE_LINUX_TEMP" -eq 1 ] && [ -n "$LINUX_TEMP_ROOTFS" ] && [ -d "$LINUX_TEMP_ROOTFS" ]; then
        echo -e "${YELLOW}Cleaning up temp directory on exit...${NC}" >&2
        cleanup_rootfs "$LINUX_TEMP_ROOTFS" 2>/dev/null || true
    fi
}

# Register cleanup on exit
trap cleanup_on_exit EXIT INT TERM

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Detect if we're on WSL and if ROOTFS_DIR is on Windows filesystem
# If so, use a Linux-native temp directory for building (better performance)
USE_LINUX_TEMP=0
if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
    # We're on WSL
    if [ -n "${ROOTFS_DIR}" ] && echo "${ROOTFS_DIR}" | grep -q "^/mnt/"; then
        # ROOTFS_DIR is on Windows filesystem, use Linux temp instead
        USE_LINUX_TEMP=1
    elif [ -z "${ROOTFS_DIR}" ] && echo "${SCRIPT_DIR}" | grep -q "^/mnt/"; then
        # Default ROOTFS_DIR would be on Windows filesystem
        USE_LINUX_TEMP=1
    fi
fi

# Configuration
if [ "$USE_LINUX_TEMP" -eq 1 ]; then
    # Use Linux-native temp directory for building (better performance on WSL)
    LINUX_TEMP_ROOTFS="/tmp/de10-nano-rootfs-$$"
    ROOTFS_DIR="${ROOTFS_DIR:-$LINUX_TEMP_ROOTFS}"
    ROOTFS_TAR="${ROOTFS_TAR:-$SCRIPT_DIR/build/rootfs.tar.gz}"
    echo -e "${YELLOW}Note: Using Linux-native temp directory for rootfs build (WSL detected)${NC}"
    echo -e "${YELLOW}Build directory: $ROOTFS_DIR${NC}"
    echo -e "${YELLOW}Final archive will be: $ROOTFS_TAR${NC}"
else
ROOTFS_DIR="${ROOTFS_DIR:-$SCRIPT_DIR/build/rootfs}"
ROOTFS_TAR="${ROOTFS_TAR:-$SCRIPT_DIR/build/rootfs.tar.gz}"
fi
ROOTFS_DISTRO="${ROOTFS_DISTRO:-debian}"
ROOTFS_VERSION="${ROOTFS_VERSION:-stable}"
ROOTFS_ARCH="${ROOTFS_ARCH:-armhf}"
PACKAGES_FILE="${PACKAGES_FILE:-$SCRIPT_DIR/packages.txt}"
CONFIG_DIR="${CONFIG_DIR:-$SCRIPT_DIR/configs}"
SCRIPTS_DIR="${SCRIPTS_DIR:-$SCRIPT_DIR/scripts}"

# Network configuration
NETWORK_MODE="${NETWORK_MODE:-dhcp}"
STATIC_IP="${STATIC_IP:-192.168.1.100}"
STATIC_GATEWAY="${STATIC_GATEWAY:-192.168.1.1}"
STATIC_NETMASK="${STATIC_NETMASK:-255.255.255.0}"

# SSH configuration
SSH_ENABLED="${SSH_ENABLED:-yes}"
SSH_ROOT_LOGIN="${SSH_ROOT_LOGIN:-yes}"
ROOT_PASSWORD="${ROOT_PASSWORD:-root}"

# ============================================================================
# Functions
# ============================================================================

print_header() {
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}===========================================${NC}"
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}" >&2
}

print_banner() {
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}===========================================${NC}"
}

url_exists() {
    local url_to_check="$1"

    if command -v wget &> /dev/null; then
        wget -q --spider --timeout=15 --tries=1 "$url_to_check"
        return $?
    fi

    if command -v curl &> /dev/null; then
        curl -fsI --max-time 15 "$url_to_check" > /dev/null
        return $?
    fi

    return 1
}

wait_for_host_internet() {
    local requirement_name="$1"
    local retry_sleep_seconds="$2"
    shift 2

    local urls_to_check=("$@")
    local attempt_count=0

    if [ ${#urls_to_check[@]} -eq 0 ]; then
        print_error "No URLs provided to internet wait for: $requirement_name"
        exit 1
    fi

    print_banner "Internet Check: $requirement_name"

    while true; do
        attempt_count=$((attempt_count + 1))

        for url_to_check in "${urls_to_check[@]}"; do
            if url_exists "$url_to_check"; then
                print_step "Internet OK for $requirement_name (reachable: $url_to_check)"
                return 0
            fi
        done

        print_warning "No internet connectivity for $requirement_name. Waiting for reconnect..."
        print_warning "Checked: ${urls_to_check[*]}"
        print_warning "Retrying in ${retry_sleep_seconds}s (attempt ${attempt_count}). Press Ctrl+C to abort."
        sleep "$retry_sleep_seconds"
    done
}

add_apt_source_if_available() {
    local sources_list_path="$1"
    local mirror_base_url="$2"
    local suite_name="$3"
    local components_list="$4"

    local release_url="${mirror_base_url%/}/dists/${suite_name}/Release"
    if url_exists "$release_url"; then
        echo "deb $mirror_base_url $suite_name $components_list" >> "$sources_list_path"
        return 0
    fi

    print_step "Skipping apt source (not found): $release_url"
    return 1
}

configure_rootfs_apt_sources() {
    local rootfs_directory="$1"
    local suite_name="$2"
    local debian_mirror_url="$3"
    local components_list="main"

    local apt_dir="$rootfs_directory/etc/apt"
    local sources_list_path="$apt_dir/sources.list"

    mkdir -p "$apt_dir"
    : > "$sources_list_path"

    print_step "Configuring apt sources for suite: $suite_name"
    if ! add_apt_source_if_available "$sources_list_path" "$debian_mirror_url" "$suite_name" "$components_list"; then
        print_error "Failed to configure required apt source for suite '${suite_name}' from mirror: ${debian_mirror_url}"
        exit 1
    fi
    add_apt_source_if_available "$sources_list_path" "$debian_mirror_url" "${suite_name}-updates" "$components_list" || true

    local security_mirror_url="https://security.debian.org/debian-security"
    if echo "$debian_mirror_url" | grep -q "archive.debian.org"; then
        security_mirror_url="https://archive.debian.org/debian-security"
    fi
    add_apt_source_if_available "$sources_list_path" "$security_mirror_url" "${suite_name}-security" "$components_list" || true

    if echo "$debian_mirror_url" | grep -q "archive.debian.org"; then
        print_step "Applying apt settings for archived Debian suite (disable Valid-Until checks)"
        mkdir -p "$apt_dir/apt.conf.d"
        cat > "$apt_dir/apt.conf.d/99archive" << 'EOF'
Acquire::Check-Valid-Until "false";
EOF
    fi
}

copy_text_file_normalized() {
    local source_file_path="$1"
    local destination_file_path="$2"
    local destination_file_mode="$3"

    mkdir -p "$(dirname "$destination_file_path")"

    if ! tr -d '\r' < "$source_file_path" > "$destination_file_path"; then
        print_error "Failed to copy file: $source_file_path -> $destination_file_path"
        exit 1
    fi

    if [ -n "$destination_file_mode" ]; then
        if ! chmod "$destination_file_mode" "$destination_file_path"; then
            print_error "Failed to chmod $destination_file_mode: $destination_file_path"
            exit 1
        fi
    fi
}

check_dependencies() {
    print_step "Checking dependencies..."
    
    local missing=0
    local host_install_hint="sudo apt-get update && sudo apt-get install -y debootstrap qemu-user-static debian-archive-keyring ca-certificates gnupg wget"
    
    if ! command -v debootstrap &> /dev/null; then
        print_error "debootstrap not found. Install with: sudo apt-get install debootstrap"
        missing=1
    fi
    
    if ! command -v qemu-debootstrap &> /dev/null && ! command -v qemu-arm-static &> /dev/null; then
        print_error "qemu-user-static not found. Install with: sudo apt-get install qemu-user-static"
        missing=1
    fi

    if ! command -v wget &> /dev/null && ! command -v curl &> /dev/null; then
        print_error "Neither wget nor curl found. Install with: sudo apt-get install wget (or curl)"
        missing=1
    fi

    if ! command -v gpgv &> /dev/null; then
        print_error "gpgv not found. Install with: sudo apt-get install gnupg"
        missing=1
    fi

    if [ ! -f /usr/share/keyrings/debian-archive-keyring.gpg ]; then
        print_error "Debian archive keyring not found: /usr/share/keyrings/debian-archive-keyring.gpg"
        print_error "Install with: sudo apt-get install debian-archive-keyring ca-certificates"
        missing=1
    fi
    
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (for chroot operations)"
        print_error "Run with: sudo $0"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Build-host dependency installation (Debian/Ubuntu/WSL):"
        print_error "  $host_install_hint"
        exit 1
    fi
    
    echo -e "${GREEN}All dependencies satisfied${NC}"
}

cleanup_rootfs() {
    local dir_to_clean="${1:-$ROOTFS_DIR}"
    
    if [ -d "$dir_to_clean" ]; then
        print_step "Cleaning existing rootfs: $dir_to_clean"
        
        # Unmount any mounted filesystems first
        for mount_point in "$dir_to_clean/proc" "$dir_to_clean/sys" "$dir_to_clean/dev"; do
            if mountpoint -q "$mount_point" 2>/dev/null; then
                print_step "Unmounting $mount_point..."
                umount "$mount_point" 2>/dev/null || true
            fi
        done
        
        # Also try to unmount with lazy unmount as fallback
        for mount_point in "$dir_to_clean/proc" "$dir_to_clean/sys" "$dir_to_clean/dev"; do
            if [ -d "$mount_point" ]; then
                umount -l "$mount_point" 2>/dev/null || true
            fi
        done
        
        # Now remove the directory
        rm -rf "$dir_to_clean"
    fi
    
    # Only create directory if it's the main ROOTFS_DIR
    if [ "$dir_to_clean" = "$ROOTFS_DIR" ]; then
    mkdir -p "$ROOTFS_DIR"
    fi
}

create_base_system() {
    print_header "Creating Base Debian System"
    
    # Check disk space (need at least 1GB free)
    print_step "Checking disk space..."
    AVAILABLE_SPACE=$(df "$ROOTFS_DIR" | tail -1 | awk '{print $4}')
    if [ "$AVAILABLE_SPACE" -lt 1048576 ]; then
        print_error "Insufficient disk space. Need at least 1GB free."
        print_error "Available: $(($AVAILABLE_SPACE / 1024))MB"
        exit 1
    fi
    echo -e "${GREEN}Disk space OK: $(($AVAILABLE_SPACE / 1024))MB available${NC}"
    
    # Clean any partial debootstrap cache
    if [ -d "$ROOTFS_DIR/debootstrap" ]; then
        print_step "Cleaning partial debootstrap cache..."
        rm -rf "$ROOTFS_DIR/debootstrap"
    fi
    
    # Clean system debootstrap cache to avoid corruption issues (especially on WSL)
    print_step "Cleaning system debootstrap cache..."
    if [ -d "/var/cache/debootstrap" ]; then
        rm -rf /var/cache/debootstrap/* 2>/dev/null || true
        echo -e "${GREEN}System debootstrap cache cleaned${NC}"
    fi
    
    print_step "Running debootstrap (this may take 10-20 minutes)..."
    print_step "Note: On WSL, 'tar failed' errors may occur due to filesystem performance."
    print_step "The script will retry with cache cleaning if this happens."
    
    # Try multiple mirrors for reliability
    MIRRORS=(
        "https://deb.debian.org/debian"
        "http://deb.debian.org/debian"
        "https://archive.debian.org/debian"
        "http://archive.debian.org/debian"
        "http://ftp.debian.org/debian"
    )
    
    wait_for_host_internet "debootstrap/apt (base system)" 5 \
        "https://deb.debian.org" \
        "https://security.debian.org"

    # Enable pipefail to catch debootstrap errors even when piped through tee
    set -o pipefail

    while true; do
        DEBOOTSTRAP_SUCCESS=0
        BOOTSTRAP_MIRROR_USED=""

        for MIRROR in "${MIRRORS[@]}"; do
            print_step "Trying mirror: $MIRROR"

            if ! url_exists "${MIRROR%/}/dists/${ROOTFS_VERSION}/Release"; then
                print_step "Mirror does not provide suite '${ROOTFS_VERSION}', skipping: $MIRROR"
                continue
            fi
    
    # Use qemu-debootstrap if available, otherwise use debootstrap with qemu-arm-static
        # Use buildd variant which includes build dependencies (including libstdc++6)
        # This ensures apt-get has all required libraries
        DEBOOTSTRAP_EXIT=0
    if command -v qemu-debootstrap &> /dev/null; then
        qemu-debootstrap \
            --arch="$ROOTFS_ARCH" \
                --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
                --include=ca-certificates \
                --variant=buildd \
                --verbose \
            "$ROOTFS_VERSION" \
            "$ROOTFS_DIR" \
                "$MIRROR" 2>&1 | tee /tmp/debootstrap.log || DEBOOTSTRAP_EXIT=$?
    else
            # Copy qemu-arm-static into rootfs before debootstrap
        if [ -f /usr/bin/qemu-arm-static ]; then
            mkdir -p "$ROOTFS_DIR/usr/bin"
            cp /usr/bin/qemu-arm-static "$ROOTFS_DIR/usr/bin/"
        fi
        
        debootstrap \
            --arch="$ROOTFS_ARCH" \
                --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
                --include=ca-certificates \
                --variant=buildd \
                --verbose \
            "$ROOTFS_VERSION" \
            "$ROOTFS_DIR" \
                "$MIRROR" 2>&1 | tee /tmp/debootstrap.log || DEBOOTSTRAP_EXIT=$?
        fi
        
        # Verify debootstrap actually succeeded by checking for essential files
        if [ $DEBOOTSTRAP_EXIT -eq 0 ] && \
           [ -f "$ROOTFS_DIR/usr/bin/apt-get" ] && \
           [ -f "$ROOTFS_DIR/usr/lib/arm-linux-gnueabihf/libstdc++.so.6" ]; then
            DEBOOTSTRAP_SUCCESS=1
            BOOTSTRAP_MIRROR_USED="$MIRROR"
            break
        else
            if [ $DEBOOTSTRAP_EXIT -ne 0 ]; then
                print_error "debootstrap failed with exit code: $DEBOOTSTRAP_EXIT"
            else
                print_error "debootstrap appears incomplete - missing essential files"
            fi
            print_error "Check /tmp/debootstrap.log for details"
            DEBOOTSTRAP_SUCCESS=0
        fi
        
        # Clean up failed attempt
        if [ -d "$ROOTFS_DIR" ]; then
            print_step "Cleaning failed attempt..."
            rm -rf "$ROOTFS_DIR"/*
            rm -rf "$ROOTFS_DIR"/.[!.]* 2>/dev/null || true
        fi
        
        # Clean debootstrap cache to avoid corruption issues
        if [ -d "/var/cache/debootstrap" ]; then
            print_step "Cleaning debootstrap cache before retry..."
            rm -rf /var/cache/debootstrap/* 2>/dev/null || true
        fi
        
        sleep 2
        done
    
        if [ $DEBOOTSTRAP_SUCCESS -eq 1 ]; then
            break
        fi

        if ! url_exists "https://deb.debian.org" && ! url_exists "https://security.debian.org"; then
            print_warning "debootstrap failed while internet appears down. Waiting and retrying..."
            wait_for_host_internet "debootstrap/apt (retry after reconnect)" 5 \
                "https://deb.debian.org" \
                "https://security.debian.org"
            continue
        fi

        print_error "debootstrap failed with all mirrors"
        print_error "Last log saved to: /tmp/debootstrap.log"
        print_error ""
        print_error "Common causes:"
        print_error "  - Network connectivity issues"
        print_error "  - Insufficient disk space"
        print_error "  - Corrupted download cache"
        print_error "  - WSL filesystem performance issues (if on Windows/WSL)"
        print_error ""
        print_error "Try:"
        print_error "  1. Check internet connection: ping -c 3 deb.debian.org"
        print_error "  2. Free up disk space: df -h"
        print_error "  3. Clean debootstrap cache: sudo rm -rf /var/cache/debootstrap"
        print_error "  4. If on WSL and 'tar failed' errors persist:"
        print_error "     - Consider building on a Linux-native filesystem (not /mnt/c/)"
        print_error "     - Or use a pre-built rootfs image"
        print_error "     - WSL filesystem performance can cause extraction failures"
        exit 1
    done
    
    echo -e "${GREEN}Base system created${NC}"

    if [ -n "$BOOTSTRAP_MIRROR_USED" ]; then
        configure_rootfs_apt_sources "$ROOTFS_DIR" "$ROOTFS_VERSION" "$BOOTSTRAP_MIRROR_USED"
    fi
    
    # Ensure qemu-arm-static is available for chroot operations
    print_step "Setting up qemu-arm-static for chroot..."
    if [ -f /usr/bin/qemu-arm-static ]; then
        mkdir -p "$ROOTFS_DIR/usr/bin"
        cp /usr/bin/qemu-arm-static "$ROOTFS_DIR/usr/bin/" 2>/dev/null || true
        echo -e "${GREEN}qemu-arm-static installed${NC}"
    else
        print_error "qemu-arm-static not found at /usr/bin/qemu-arm-static"
        print_error "Install with: sudo apt-get install qemu-user-static"
        exit 1
    fi
    
    # Verify base system is complete
    print_step "Verifying base system..."
    if [ ! -f "$ROOTFS_DIR/bin/sh" ] || [ ! -f "$ROOTFS_DIR/usr/bin/apt-get" ]; then
        print_error "Base system appears incomplete"
        print_error "Missing essential files: /bin/sh or /usr/bin/apt-get"
        exit 1
    fi
    echo -e "${GREEN}Base system verified${NC}"
}

install_packages() {
    print_header "Installing Packages"
    
    if [ ! -f "$PACKAGES_FILE" ]; then
        print_error "Packages file not found: $PACKAGES_FILE"
        exit 1
    fi
    
    print_step "Installing packages from $PACKAGES_FILE..."
    
    # Ensure qemu-arm-static is available
    if [ -f /usr/bin/qemu-arm-static ] && [ ! -f "$ROOTFS_DIR/usr/bin/qemu-arm-static" ]; then
        mkdir -p "$ROOTFS_DIR/usr/bin"
        cp /usr/bin/qemu-arm-static "$ROOTFS_DIR/usr/bin/"
    fi
    
    # Mount required filesystems for chroot
    mount -t proc proc "$ROOTFS_DIR/proc" || print_error "Failed to mount proc"
    mount -t sysfs sysfs "$ROOTFS_DIR/sys" || print_error "Failed to mount sys"
    mount -o bind /dev "$ROOTFS_DIR/dev" || print_error "Failed to mount dev"
    
    # Check if apt-get can run (has libstdc++6)
    print_step "Verifying base system packages..."
    if ! chroot "$ROOTFS_DIR" /bin/sh -c "ldd /usr/bin/apt-get 2>/dev/null | grep -q libstdc++" 2>/dev/null; then
        print_step "Base system missing libstdc++6, attempting to fix..."
        # Try to install libstdc++6 using dpkg from debootstrap cache
        if [ -d "$ROOTFS_DIR/debootstrap" ]; then
            print_step "Installing libstdc++6 from debootstrap cache..."
            # Find and install libstdc++6 package
            shopt -s nullglob  # Don't expand to literal if no matches
            for pkg in "$ROOTFS_DIR/debootstrap"/*/libstdc++6*.deb; do
                if [ -f "$pkg" ]; then
                    chroot "$ROOTFS_DIR" dpkg -i "$pkg" 2>/dev/null || true
                    break
                fi
            done
            shopt -u nullglob  # Restore default behavior
        fi
        # If still not working, try to download and install manually
        if ! chroot "$ROOTFS_DIR" /bin/sh -c "test -f /usr/lib/arm-linux-gnueabihf/libstdc++.so.6" 2>/dev/null; then
            print_error "Cannot fix base system - libstdc++6 not available"
            print_error "This may indicate a problem with debootstrap"
            print_error "Try: sudo rm -rf $ROOTFS_DIR && retry build"
            exit 1
        fi
    fi
    
    # Update package lists
    print_step "Updating package lists..."
    while true; do
        if chroot "$ROOTFS_DIR" apt-get update; then
            break
        fi

        if ! url_exists "https://deb.debian.org" && ! url_exists "https://security.debian.org"; then
            print_warning "apt-get update failed while internet appears down. Waiting and retrying..."
            wait_for_host_internet "apt-get update (retry after reconnect)" 5 \
                "https://deb.debian.org" \
                "https://security.debian.org"
            continue
        fi

        print_error "Failed to update package lists"
        print_error "Base system may be incomplete"
        exit 1
    done
    
    # Install packages
    if [ -f "$PACKAGES_FILE" ]; then
        PACKAGES="$(tr -d '\r' < "$PACKAGES_FILE" | grep -v '^[[:space:]]*#' | grep -v '^[[:space:]]*$' | tr '\n' ' ')"
        if [ -z "$PACKAGES" ]; then
            print_error "No packages found in: $PACKAGES_FILE"
            print_error "Ensure the file contains package names and uses Unix line endings (LF) or CRLF-safe content."
            exit 1
        fi

        print_step "Installing $(echo "$PACKAGES" | wc -w) packages..."
        while true; do
            if chroot "$ROOTFS_DIR" apt-get install -y $PACKAGES; then
                break
            fi

            if ! url_exists "https://deb.debian.org" && ! url_exists "https://security.debian.org"; then
                print_warning "apt-get install failed while internet appears down. Waiting and retrying..."
                wait_for_host_internet "apt-get install (retry after reconnect)" 5 \
                    "https://deb.debian.org" \
                    "https://security.debian.org"
                continue
            fi

            print_error "Package installation failed. Checking which packages are unavailable..."
            for package_name in $PACKAGES; do
                if ! chroot "$ROOTFS_DIR" /bin/sh -c "apt-cache show '$package_name' 2>/dev/null | grep -q '^Package:'"; then
                    print_error "Package not found in configured apt sources: $package_name"
                fi
            done
            exit 1
        done
    fi
    
    # Clean up
    chroot "$ROOTFS_DIR" apt-get clean
    chroot "$ROOTFS_DIR" rm -rf /var/lib/apt/lists/*
    
    # Unmount
    umount "$ROOTFS_DIR/dev" || true
    umount "$ROOTFS_DIR/sys" || true
    umount "$ROOTFS_DIR/proc" || true
    
    echo -e "${GREEN}Packages installed${NC}"
}

configure_network() {
    print_header "Configuring Network"
    
    print_step "Setting up network configuration (mode: $NETWORK_MODE)..."
    
    mkdir -p "$ROOTFS_DIR/etc/network"
    
    # Mount required filesystems for chroot operations
    mount -t proc proc "$ROOTFS_DIR/proc" || true
    mount -t sysfs sysfs "$ROOTFS_DIR/sys" || true
    mount -o bind /dev "$ROOTFS_DIR/dev" || true
    
    if [ "$NETWORK_MODE" = "static" ]; then
        cat > "$ROOTFS_DIR/etc/network/interfaces" << EOF
# Network configuration for DE10-Nano
# Auto-configured during rootfs build

auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address $STATIC_IP
    netmask $STATIC_NETMASK
    gateway $STATIC_GATEWAY
EOF
        echo -e "${GREEN}Static IP configured: $STATIC_IP${NC}"
    else
        cat > "$ROOTFS_DIR/etc/network/interfaces" << EOF
# Network configuration for DE10-Nano
# Auto-configured during rootfs build
# Ethernet interface configured for DHCP

auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
EOF
        echo -e "${GREEN}DHCP configured (eth0 will auto-start)${NC}"
    fi
    
    # Copy custom network config if provided
    if [ -f "$CONFIG_DIR/network/interfaces" ]; then
        copy_text_file_normalized "$CONFIG_DIR/network/interfaces" "$ROOTFS_DIR/etc/network/interfaces" 0644
        echo -e "${GREEN}Using custom network configuration${NC}"
    fi
    
    # Enable networking service to start on boot
    print_step "Enabling networking service..."
    if [ -d "$ROOTFS_DIR/etc/systemd/system" ]; then
        chroot "$ROOTFS_DIR" systemctl enable networking 2>/dev/null || true
        
        # Create symlink if systemd service doesn't exist
        if [ ! -f "$ROOTFS_DIR/etc/systemd/system/networking.service" ]; then
            mkdir -p "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants"
            ln -sf /lib/systemd/system/networking.service \
                   "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants/networking.service" 2>/dev/null || true
        fi
    fi
    
    # Ensure ifupdown is installed (for /etc/network/interfaces)
    if ! chroot "$ROOTFS_DIR" dpkg -l | grep -q ifupdown; then
        print_step "Installing ifupdown..."
        chroot "$ROOTFS_DIR" apt-get update
        chroot "$ROOTFS_DIR" apt-get install -y ifupdown
    fi
    
    # Unmount
    umount "$ROOTFS_DIR/dev" || true
    umount "$ROOTFS_DIR/sys" || true
    umount "$ROOTFS_DIR/proc" || true
    
    echo -e "${GREEN}Network configured and enabled${NC}"
}

configure_ssh() {
    print_header "Configuring SSH"
    
    if [ "$SSH_ENABLED" != "yes" ]; then
        echo -e "${YELLOW}SSH disabled, skipping...${NC}"
        return
    fi
    
    print_step "Configuring SSH server..."
    
    # Mount required filesystems for chroot operations
    mount -t proc proc "$ROOTFS_DIR/proc" || true
    mount -t sysfs sysfs "$ROOTFS_DIR/sys" || true
    mount -o bind /dev "$ROOTFS_DIR/dev" || true
    
    # Ensure openssh-server is installed (should be in packages.txt)
    if ! chroot "$ROOTFS_DIR" dpkg -l | grep -q openssh-server; then
        print_step "Installing openssh-server..."
        chroot "$ROOTFS_DIR" apt-get update
        chroot "$ROOTFS_DIR" apt-get install -y openssh-server
    fi
    
    # Configure SSH
    mkdir -p "$ROOTFS_DIR/etc/ssh"
    
    if [ -f "$CONFIG_DIR/ssh/sshd_config" ]; then
        copy_text_file_normalized "$CONFIG_DIR/ssh/sshd_config" "$ROOTFS_DIR/etc/ssh/sshd_config" 0644
        echo -e "${GREEN}Using custom SSH configuration${NC}"
    else
        # Default SSH config
        cat > "$ROOTFS_DIR/etc/ssh/sshd_config" << EOF
# SSH Server Configuration for DE10-Nano
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

# Allow root login (for development)
PermitRootLogin yes
PasswordAuthentication yes
PubkeyAuthentication yes

# Security settings
X11Forwarding no
PermitEmptyPasswords no

# Performance
UseDNS no
TCPKeepAlive yes

# Logging
SyslogFacility AUTH
LogLevel INFO
EOF
    fi
    
    # Generate SSH host keys if they don't exist
    print_step "Generating SSH host keys..."
    if [ ! -f "$ROOTFS_DIR/etc/ssh/ssh_host_rsa_key" ]; then
        chroot "$ROOTFS_DIR" ssh-keygen -A || true
    fi
    
    # Enable SSH service to start on boot
    print_step "Enabling SSH service..."
    if [ -d "$ROOTFS_DIR/etc/systemd/system" ]; then
        # Enable SSH service (Debian uses 'ssh' service name)
        chroot "$ROOTFS_DIR" systemctl enable ssh 2>/dev/null || \
        chroot "$ROOTFS_DIR" systemctl enable sshd 2>/dev/null || \
        chroot "$ROOTFS_DIR" systemctl enable openssh-server 2>/dev/null || true
        
        # Create symlink if systemd service doesn't exist
        if [ ! -f "$ROOTFS_DIR/etc/systemd/system/ssh.service" ] && \
           [ ! -f "$ROOTFS_DIR/etc/systemd/system/sshd.service" ]; then
            mkdir -p "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants"
            ln -sf /lib/systemd/system/ssh.service \
                   "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants/ssh.service" 2>/dev/null || true
        fi
    fi
    
    # Set root password
    if [ -n "$ROOT_PASSWORD" ]; then
        print_step "Setting root password..."
        echo "root:$ROOT_PASSWORD" | chroot "$ROOTFS_DIR" chpasswd
        echo -e "${GREEN}Root password set to: $ROOT_PASSWORD${NC}"
        echo -e "${YELLOW}WARNING: Change this password after first boot!${NC}"
    fi
    
    # Unmount
    umount "$ROOTFS_DIR/dev" || true
    umount "$ROOTFS_DIR/sys" || true
    umount "$ROOTFS_DIR/proc" || true
    
    echo -e "${GREEN}SSH configured and enabled${NC}"
}

run_post_install_scripts() {
    print_header "Running Post-Install Scripts"
    
    if [ ! -d "$SCRIPTS_DIR" ]; then
        echo -e "${YELLOW}No post-install scripts directory found, skipping...${NC}"
        return
    fi
    
    # Mount required filesystems
    mount -t proc proc "$ROOTFS_DIR/proc" || true
    mount -t sysfs sysfs "$ROOTFS_DIR/sys" || true
    mount -o bind /dev "$ROOTFS_DIR/dev" || true
    
    # Run scripts in order
    for script in "$SCRIPTS_DIR"/*.sh; do
        if [ -f "$script" ]; then
            print_step "Running $(basename "$script")..."
            # Copy script to rootfs and run in chroot
            copy_text_file_normalized "$script" "$ROOTFS_DIR/tmp/$(basename "$script")" 0755
            if ! chroot "$ROOTFS_DIR" /bin/bash "/tmp/$(basename "$script")"; then
                print_error "Post-install script failed: $(basename "$script")"
                exit 1
            fi
            rm -f "$ROOTFS_DIR/tmp/$(basename "$script")"
        fi
    done
    
    # Unmount
    umount "$ROOTFS_DIR/dev" || true
    umount "$ROOTFS_DIR/sys" || true
    umount "$ROOTFS_DIR/proc" || true
    
    echo -e "${GREEN}Post-install scripts completed${NC}"
}

create_rootfs_tarball() {
    print_header "Creating Rootfs Tarball"
    
    print_step "Creating tarball: $ROOTFS_TAR..."
    
    # Remove qemu-arm-static if copied
    if [ -f "$ROOTFS_DIR/usr/bin/qemu-arm-static" ]; then
        rm -f "$ROOTFS_DIR/usr/bin/qemu-arm-static"
    fi
    
    # Create tarball
    mkdir -p "$(dirname "$ROOTFS_TAR")"
    cd "$ROOTFS_DIR"
    tar -czf "$ROOTFS_TAR" .
    cd - > /dev/null
    
    # Calculate size
    SIZE=$(du -h "$ROOTFS_TAR" | cut -f1)
    echo -e "${GREEN}Rootfs tarball created: $ROOTFS_TAR ($SIZE)${NC}"
    
    # Clean up Linux temp directory if we used one
    if [ "$USE_LINUX_TEMP" -eq 1 ] && [ -n "$LINUX_TEMP_ROOTFS" ] && [ -d "$LINUX_TEMP_ROOTFS" ]; then
        print_step "Cleaning up Linux temp directory: $LINUX_TEMP_ROOTFS"
        cleanup_rootfs "$LINUX_TEMP_ROOTFS"
        echo -e "${GREEN}Temp directory cleaned up${NC}"
    fi
}

# ============================================================================
# Main
# ============================================================================

main() {
    print_header "DE10-Nano Root Filesystem Build"
    
    check_dependencies
    cleanup_rootfs
    create_base_system
    install_packages
    configure_network
    configure_ssh
    run_post_install_scripts
    create_rootfs_tarball
    
    print_header "Root Filesystem Build Complete"
    if [ "$USE_LINUX_TEMP" -eq 1 ]; then
        echo -e "${GREEN}Rootfs built in temp directory (cleaned up)${NC}"
    else
    echo -e "${GREEN}Rootfs directory: $ROOTFS_DIR${NC}"
    fi
    echo -e "${GREEN}Rootfs tarball:   $ROOTFS_TAR${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Create SD card image: cd HPS/linux_image && sudo make sd-image"
    echo "  2. Or build everything:  cd HPS && sudo make everything"
}

# Run main function
main "$@"
