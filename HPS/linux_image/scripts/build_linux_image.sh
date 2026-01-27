#!/bin/bash
# ============================================================================
# Unified Linux Image Build Script for DE10-Nano
# ============================================================================
# Orchestrates complete build: FPGA, bootloader, kernel, rootfs, and image
# ============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HPS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$HPS_DIR/.." && pwd)"
LINUX_IMAGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source build configuration
if [ -f "$SCRIPT_DIR/build_config.sh" ]; then
    source "$SCRIPT_DIR/build_config.sh"
fi

# Build options
BUILD_FPGA="${BUILD_FPGA:-yes}"
BUILD_KERNEL="${BUILD_KERNEL:-yes}"
BUILD_ROOTFS="${BUILD_ROOTFS:-yes}"
CREATE_IMAGE="${CREATE_IMAGE:-yes}"
SKIP_EXISTING="${SKIP_EXISTING:-no}"

# Paths
FPGA_DIR="${FPGA_DIR:-$REPO_ROOT/FPGA}"
KERNEL_DIR="${KERNEL_DIR:-$LINUX_IMAGE_DIR/kernel}"
ROOTFS_DIR="${ROOTFS_DIR:-$LINUX_IMAGE_DIR/rootfs}"

# ============================================================================
# Functions
# ============================================================================

print_header() {
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}===========================================${NC}"
}

print_step() {
    echo -e "${BLUE}$1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

check_dependencies() {
    print_header "Checking Dependencies"
    
    local missing=0
    
    # Check for required tools
    for cmd in make git; do
        if ! command -v $cmd &> /dev/null; then
            print_error "$cmd not found"
            missing=1
        fi
    done
    
    # Check for cross-compilation toolchain
    if ! command -v ${CROSS_COMPILE}gcc &> /dev/null; then
        print_warning "Cross-compilation toolchain not found: ${CROSS_COMPILE}gcc"
        print_warning "Install with: sudo apt-get install gcc-arm-linux-gnueabihf"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Some dependencies are missing. Please install them and try again."
        exit 1
    fi
    
    echo -e "${GREEN}Basic dependencies satisfied${NC}"
    echo -e "${YELLOW}Note: Rootfs build and image creation require additional tools${NC}"
    echo -e "${YELLOW}      (debootstrap, qemu-user-static, parted, etc.)${NC}"
}

build_fpga() {
    if [ "$BUILD_FPGA" != "yes" ]; then
        echo -e "${YELLOW}Skipping FPGA build${NC}"
        return 0
    fi
    
    print_header "Building FPGA Components"
    
    print_step "Building FPGA bitstream, preloader, U-Boot, and device tree..."
    
    cd "$FPGA_DIR"
    
    # Build FPGA components
    if [ "$SKIP_EXISTING" = "yes" ] && [ -f "build/output_files/DE10_NANO_SoC_GHRD.rbf" ]; then
        echo -e "${YELLOW}Skipping FPGA build (output exists)${NC}"
    else
        make qsys-generate
        make sof
        make rbf
    fi
    
    # Build HPS software (preloader, U-Boot, device tree)
    if [ "$SKIP_EXISTING" = "yes" ] && [ -f "$HPS_DIR/preloader/preloader-mkpimage.bin" ]; then
        echo -e "${YELLOW}Skipping HPS software build (output exists)${NC}"
    else
        if command -v bsp-create-settings &> /dev/null || [ -n "$SOCEDS_DEST_ROOT" ]; then
            make preloader
            make uboot
            make dts
            make dtb
        else
            print_warning "SoC EDS not found, skipping preloader/U-Boot build"
            print_warning "Install SoC EDS and set SOCEDS_DEST_ROOT to build bootloader"
        fi
    fi
    
    cd "$REPO_ROOT"
    
    echo -e "${GREEN}FPGA components built${NC}"
}

build_kernel() {
    if [ "$BUILD_KERNEL" != "yes" ]; then
        echo -e "${YELLOW}Skipping kernel build${NC}"
        return 0
    fi
    
    print_header "Building Linux Kernel"
    
    print_step "Building kernel with FPGA driver integration..."
    
    cd "$KERNEL_DIR"
    
    if [ "$SKIP_EXISTING" = "yes" ] && [ -f "build/arch/arm/boot/zImage" ]; then
        echo -e "${YELLOW}Skipping kernel build (output exists)${NC}"
    else
        export CROSS_COMPILE ARCH
        make kernel-build
    fi
    
    cd "$REPO_ROOT"
    
    echo -e "${GREEN}Kernel built${NC}"
}

build_rootfs() {
    if [ "$BUILD_ROOTFS" != "yes" ]; then
        echo -e "${YELLOW}Skipping rootfs build${NC}"
        return 0
    fi
    
    print_header "Building Root Filesystem"
    
    print_step "Building rootfs with network and SSH configuration..."
    
    cd "$ROOTFS_DIR"
    
    if [ "$SKIP_EXISTING" = "yes" ] && [ -f "build/rootfs.tar.gz" ]; then
        echo -e "${YELLOW}Skipping rootfs build (output exists)${NC}"
    else
        # Export configuration
        export NETWORK_MODE STATIC_IP STATIC_GATEWAY STATIC_NETMASK
        export SSH_ENABLED SSH_ROOT_LOGIN ROOT_PASSWORD
        
        # Build rootfs (requires root)
        if [ "$EUID" -eq 0 ]; then
            make rootfs
        else
            echo -e "${YELLOW}Rootfs build requires root access${NC}"
            echo -e "${YELLOW}Run with: sudo $0${NC}"
            sudo make rootfs
        fi
    fi
    
    cd "$REPO_ROOT"
    
    echo -e "${GREEN}Rootfs built${NC}"
}

create_image() {
    if [ "$CREATE_IMAGE" != "yes" ]; then
        echo -e "${YELLOW}Skipping image creation${NC}"
        return 0
    fi
    
    print_header "Creating SD Card Image"
    
    print_step "Creating bootable SD card image..."
    
    cd "$LINUX_IMAGE_DIR/scripts"
    
    if [ "$SKIP_EXISTING" = "yes" ] && [ -f "$LINUX_IMAGE_DIR/build/$IMAGE_NAME" ]; then
        echo -e "${YELLOW}Skipping image creation (output exists)${NC}"
    else
        # Export configuration
        export IMAGE_NAME IMAGE_SIZE
        export FPGA_DIR HPS_DIR KERNEL_DIR ROOTFS_DIR
        
        # Create image (requires root)
        if [ "$EUID" -eq 0 ]; then
            bash create_sd_image.sh
        else
            echo -e "${YELLOW}Image creation requires root access${NC}"
            echo -e "${YELLOW}Run with: sudo $0${NC}"
            sudo bash create_sd_image.sh
        fi
    fi
    
    cd "$REPO_ROOT"
    
    echo -e "${GREEN}SD card image created${NC}"
}

print_summary() {
    print_header "Build Summary"
    
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo ""
    echo "Output files:"
    
    # FPGA outputs
    if [ -f "$FPGA_DIR/build/output_files/DE10_NANO_SoC_GHRD.rbf" ]; then
        echo -e "  ${GREEN}✓${NC} FPGA RBF: $FPGA_DIR/build/output_files/DE10_NANO_SoC_GHRD.rbf"
    fi
    
    if [ -f "$HPS_DIR/preloader/preloader-mkpimage.bin" ]; then
        echo -e "  ${GREEN}✓${NC} Preloader: $HPS_DIR/preloader/preloader-mkpimage.bin"
    fi
    
    if [ -f "$HPS_DIR/preloader/uboot-socfpga/u-boot.img" ]; then
        echo -e "  ${GREEN}✓${NC} U-Boot: $HPS_DIR/preloader/uboot-socfpga/u-boot.img"
    fi
    
    # Kernel outputs
    if [ -f "$KERNEL_DIR/build/arch/arm/boot/zImage" ]; then
        echo -e "  ${GREEN}✓${NC} Kernel: $KERNEL_DIR/build/arch/arm/boot/zImage"
    fi
    
    # Rootfs outputs
    if [ -f "$ROOTFS_DIR/build/rootfs.tar.gz" ]; then
        echo -e "  ${GREEN}✓${NC} Rootfs: $ROOTFS_DIR/build/rootfs.tar.gz"
    fi
    
    # Image output
    if [ -f "$LINUX_IMAGE_DIR/build/$IMAGE_NAME" ]; then
        echo -e "  ${GREEN}✓${NC} SD Image: $LINUX_IMAGE_DIR/build/$IMAGE_NAME"
        echo ""
        echo -e "${YELLOW}To deploy to SD card:${NC}"
        echo "  cd HPS/linux_image/scripts"
        echo "  sudo ./deploy_image.sh /dev/sdX"
        echo ""
        echo -e "${YELLOW}Or manually:${NC}"
        echo "  sudo dd if=$LINUX_IMAGE_DIR/build/$IMAGE_NAME of=/dev/sdX bs=4M status=progress"
    fi
}

# ============================================================================
# Main
# ============================================================================

main() {
    print_header "DE10-Nano Linux Image Build"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-fpga)
                BUILD_FPGA=no
                shift
                ;;
            --no-kernel)
                BUILD_KERNEL=no
                shift
                ;;
            --no-rootfs)
                BUILD_ROOTFS=no
                shift
                ;;
            --no-image)
                CREATE_IMAGE=no
                shift
                ;;
            --skip-existing)
                SKIP_EXISTING=yes
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --no-fpga        Skip FPGA build"
                echo "  --no-kernel      Skip kernel build"
                echo "  --no-rootfs      Skip rootfs build"
                echo "  --no-image       Skip image creation"
                echo "  --skip-existing  Skip builds if output exists"
                echo "  --help           Show this help"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    check_dependencies
    build_fpga
    build_kernel
    build_rootfs
    create_image
    print_summary
    
    print_header "Build Complete"
}

# Run main function
main "$@"
