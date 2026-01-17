#!/bin/bash
# ============================================================================
# Linux Driver Integration Script
# ============================================================================
# Integrates calculator driver into existing Linux kernel build system
# Supports both kernel module and userspace driver integration
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DRIVER_SRC="$REPO_ROOT/HPS/calculator_test"

# Default values
KERNEL_DIR=""
INTEGRATION_TYPE="userspace"  # userspace or kernel
DEVICE_TREE_DIR=""
OUTPUT_DIR=""
BASE_ADDRESS="0x00080000"  # Default calculator base address

# ============================================================================
# Usage
# ============================================================================
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Integrates calculator driver into Linux kernel build system.

Options:
    -k, --kernel-dir DIR       Linux kernel source directory (required)
    -t, --type TYPE            Integration type: userspace (default) or kernel
    -d, --dtb-dir DIR          Device tree source directory (optional)
    -o, --output-dir DIR       Output directory for generated files (optional)
    -a, --base-address ADDR    Calculator base address (default: 0x00080000)
    -h, --help                 Show this help message

Examples:
    # Userspace driver integration (default)
    $0 -k /path/to/linux-kernel

    # Kernel module integration
    $0 -k /path/to/linux-kernel -t kernel

    # With device tree directory
    $0 -k /path/to/linux-kernel -d /path/to/device-tree

    # Custom base address
    $0 -k /path/to/linux-kernel -a 0x00100000

EOF
}

# ============================================================================
# Parse Arguments
# ============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        -k|--kernel-dir)
            KERNEL_DIR="$2"
            shift 2
            ;;
        -t|--type)
            INTEGRATION_TYPE="$2"
            shift 2
            ;;
        -d|--dtb-dir)
            DEVICE_TREE_DIR="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -a|--base-address)
            BASE_ADDRESS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# ============================================================================
# Validate Arguments
# ============================================================================
if [[ -z "$KERNEL_DIR" ]]; then
    echo -e "${RED}ERROR: Kernel directory is required${NC}"
    usage
    exit 1
fi

if [[ ! -d "$KERNEL_DIR" ]]; then
    echo -e "${RED}ERROR: Kernel directory does not exist: $KERNEL_DIR${NC}"
    exit 1
fi

if [[ "$INTEGRATION_TYPE" != "userspace" && "$INTEGRATION_TYPE" != "kernel" ]]; then
    echo -e "${RED}ERROR: Invalid integration type: $INTEGRATION_TYPE${NC}"
    echo "Must be 'userspace' or 'kernel'"
    exit 1
fi

if [[ ! -d "$DRIVER_SRC" ]]; then
    echo -e "${RED}ERROR: Driver source directory not found: $DRIVER_SRC${NC}"
    exit 1
fi

# ============================================================================
# Print Configuration
# ============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Calculator Driver Integration${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Kernel Directory:    $KERNEL_DIR"
echo "Integration Type:    $INTEGRATION_TYPE"
echo "Device Tree Dir:      ${DEVICE_TREE_DIR:-Not specified}"
echo "Output Directory:    ${OUTPUT_DIR:-Default}"
echo "Base Address:        $BASE_ADDRESS"
echo "Driver Source:       $DRIVER_SRC"
echo ""

# ============================================================================
# Integration Functions
# ============================================================================

# Create userspace driver integration
integrate_userspace() {
    local target_dir="${OUTPUT_DIR:-$KERNEL_DIR/drivers/misc/calculator}"
    
    echo -e "${YELLOW}Integrating userspace driver...${NC}"
    
    # Create target directory
    mkdir -p "$target_dir"
    
    # Copy driver files
    echo "  Copying driver files..."
    cp "$DRIVER_SRC/calculator_driver.h" "$target_dir/"
    cp "$DRIVER_SRC/calculator_driver.c" "$target_dir/"
    cp "$DRIVER_SRC/logger.h" "$target_dir/"
    cp "$DRIVER_SRC/logger.c" "$target_dir/"
    
    # Create Makefile for userspace
    cat > "$target_dir/Makefile" << EOF
# Calculator Driver - Userspace Build
# This Makefile builds the calculator driver as a userspace library

CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -fPIC
LDFLAGS ?= -shared

TARGET_LIB = libcalculator.so
TARGET_STATIC = libcalculator.a
SOURCES = calculator_driver.c logger.c
OBJECTS = \$(SOURCES:.c=.o)
HEADERS = calculator_driver.h logger.h

.PHONY: all clean install

all: \$(TARGET_LIB) \$(TARGET_STATIC)

\$(TARGET_LIB): \$(OBJECTS)
	\$(CC) \$(LDFLAGS) -o \$@ \$^
	@echo "Built shared library: \$@"

\$(TARGET_STATIC): \$(OBJECTS)
	ar rcs \$@ \$^
	@echo "Built static library: \$@"

%.o: %.c \$(HEADERS)
	\$(CC) \$(CFLAGS) -c \$< -o \$@

clean:
	rm -f \$(OBJECTS) \$(TARGET_LIB) \$(TARGET_STATIC)

install: \$(TARGET_LIB) \$(TARGET_STATIC)
	install -d \$(DESTDIR)/usr/lib
	install -d \$(DESTDIR)/usr/include
	install -m 644 \$(TARGET_LIB) \$(DESTDIR)/usr/lib/
	install -m 644 \$(TARGET_STATIC) \$(DESTDIR)/usr/lib/
	install -m 644 \$(HEADERS) \$(DESTDIR)/usr/include/
	ldconfig

EOF
    
    # Create pkg-config file
    cat > "$target_dir/calculator.pc" << EOF
prefix=/usr
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: Calculator Driver
Description: Hardware calculator IP driver library
Version: 1.1
Libs: -L\${libdir} -lcalculator
Cflags: -I\${includedir}
EOF
    
    echo -e "${GREEN}  Userspace driver integrated to: $target_dir${NC}"
    echo "  Build with: cd $target_dir && make"
}

# Create kernel module integration
integrate_kernel() {
    local target_dir="${OUTPUT_DIR:-$KERNEL_DIR/drivers/misc/calculator}"
    
    echo -e "${YELLOW}Integrating kernel module...${NC}"
    
    # Create target directory
    mkdir -p "$target_dir"
    
    # Copy and adapt driver files for kernel module
    echo "  Creating kernel module files..."
    
    # Create kernel module source
    cat > "$target_dir/calculator_module.c" << 'KERNEL_EOF'
// ============================================================================
// Calculator Kernel Module
// ============================================================================
// Linux kernel module for hardware calculator IP
// ============================================================================

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/miscdevice.h>
#include <linux/uaccess.h>
#include <linux/fs.h>

#define DRIVER_NAME "calculator"
#define CALCULATOR_VERSION "1.1"

// Base address (will be set from device tree)
static void __iomem *calculator_base = NULL;
static resource_size_t calculator_size = 64;  // 64 bytes

// Device tree compatible string
static const struct of_device_id calculator_of_match[] = {
    { .compatible = "altr,calculator-1.1" },
    { }
};
MODULE_DEVICE_TABLE(of, calculator_of_match);

// File operations
static int calculator_open(struct inode *inode, struct file *file)
{
    return 0;
}

static int calculator_release(struct inode *inode, struct file *file)
{
    return 0;
}

static ssize_t calculator_read(struct file *file, char __user *buf,
                               size_t count, loff_t *ppos)
{
    uint32_t value;
    
    if (*ppos >= calculator_size)
        return 0;
    
    if (*ppos + count > calculator_size)
        count = calculator_size - *ppos;
    
    value = ioread32(calculator_base + *ppos);
    
    if (copy_to_user(buf, &value, count))
        return -EFAULT;
    
    *ppos += count;
    return count;
}

static ssize_t calculator_write(struct file *file, const char __user *buf,
                                size_t count, loff_t *ppos)
{
    uint32_t value;
    
    if (*ppos >= calculator_size)
        return 0;
    
    if (*ppos + count > calculator_size)
        count = calculator_size - *ppos;
    
    if (copy_from_user(&value, buf, count))
        return -EFAULT;
    
    iowrite32(value, calculator_base + *ppos);
    
    *ppos += count;
    return count;
}

static const struct file_operations calculator_fops = {
    .owner = THIS_MODULE,
    .open = calculator_open,
    .release = calculator_release,
    .read = calculator_read,
    .write = calculator_write,
};

static struct miscdevice calculator_miscdev = {
    .minor = MISC_DYNAMIC_MINOR,
    .name = DRIVER_NAME,
    .fops = &calculator_fops,
};

// Platform driver probe
static int calculator_probe(struct platform_device *pdev)
{
    struct resource *res;
    int ret;
    
    // Get device tree resource
    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    if (!res) {
        dev_err(&pdev->dev, "No memory resource\n");
        return -ENODEV;
    }
    
    calculator_base = devm_ioremap_resource(&pdev->dev, res);
    if (IS_ERR(calculator_base)) {
        dev_err(&pdev->dev, "Failed to map registers\n");
        return PTR_ERR(calculator_base);
    }
    
    calculator_size = resource_size(res);
    
    // Register misc device
    ret = misc_register(&calculator_miscdev);
    if (ret) {
        dev_err(&pdev->dev, "Failed to register misc device\n");
        return ret;
    }
    
    dev_info(&pdev->dev, "Calculator driver loaded (base: %p, size: %zu)\n",
             calculator_base, calculator_size);
    
    return 0;
}

static int calculator_remove(struct platform_device *pdev)
{
    misc_deregister(&calculator_miscdev);
    dev_info(&pdev->dev, "Calculator driver unloaded\n");
    return 0;
}

static struct platform_driver calculator_driver = {
    .probe = calculator_probe,
    .remove = calculator_remove,
    .driver = {
        .name = DRIVER_NAME,
        .of_match_table = calculator_of_match,
    },
};

module_platform_driver(calculator_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Calculator IP Integration");
MODULE_DESCRIPTION("Hardware calculator IP kernel driver");
MODULE_VERSION(CALCULATOR_VERSION);
KERNEL_EOF
    
    # Create Makefile for kernel module
    cat > "$target_dir/Makefile" << EOF
# Calculator Kernel Module
obj-\$(CONFIG_CALCULATOR) += calculator_module.o

EOF
    
    # Create Kconfig entry
    cat > "$target_dir/Kconfig" << EOF
config CALCULATOR
    tristate "Hardware Calculator IP Driver"
    depends on ARCH_SOCFPGA || COMPILE_TEST
    help
      Driver for hardware-accelerated calculator IP on DE10-Nano FPGA.
      
      This driver provides access to the calculator IP via /dev/calculator
      device node. The calculator supports basic floating-point operations
      and HFT (High-Frequency Trading) calculations.
      
      Say Y here to compile the driver into the kernel, or M to compile
      it as a module named calculator_module.

EOF
    
    echo -e "${GREEN}  Kernel module integrated to: $target_dir${NC}"
    echo "  Enable in kernel config: CONFIG_CALCULATOR=y or =m"
}

# Create device tree overlay
create_device_tree() {
    if [[ -z "$DEVICE_TREE_DIR" ]]; then
        echo -e "${YELLOW}  Device tree directory not specified, skipping DTS creation${NC}"
        return
    fi
    
    echo -e "${YELLOW}Creating device tree overlay...${NC}"
    
    local dts_file="$DEVICE_TREE_DIR/calculator.dtsi"
    
    cat > "$dts_file" << EOF
// ============================================================================
// Calculator IP Device Tree Source
// ============================================================================
// Add this to your device tree or include as overlay
// ============================================================================

&h2f_lw_bus {
    calculator_0: calculator@${BASE_ADDRESS} {
        compatible = "altr,calculator-1.1";
        reg = <${BASE_ADDRESS} 0x40>;  // 64 bytes (16 registers)
        status = "okay";
    };
};

EOF
    
    echo -e "${GREEN}  Device tree source created: $dts_file${NC}"
    echo "  Include in your main device tree or compile as overlay"
}

# Update kernel Makefile
update_kernel_makefile() {
    local misc_makefile="$KERNEL_DIR/drivers/misc/Makefile"
    
    if [[ ! -f "$misc_makefile" ]]; then
        echo -e "${YELLOW}  drivers/misc/Makefile not found, skipping update${NC}"
        return
    fi
    
    if grep -q "calculator" "$misc_makefile"; then
        echo -e "${YELLOW}  Calculator already in Makefile${NC}"
        return
    fi
    
    echo -e "${YELLOW}Updating kernel Makefile...${NC}"
    
    # Add calculator entry
    echo "" >> "$misc_makefile"
    echo "# Calculator IP driver" >> "$misc_makefile"
    echo "obj-\$(CONFIG_CALCULATOR) += calculator/" >> "$misc_makefile"
    
    echo -e "${GREEN}  Makefile updated${NC}"
}

# Update kernel Kconfig
update_kernel_kconfig() {
    local misc_kconfig="$KERNEL_DIR/drivers/misc/Kconfig"
    
    if [[ ! -f "$misc_kconfig" ]]; then
        echo -e "${YELLOW}  drivers/misc/Kconfig not found, skipping update${NC}"
        return
    fi
    
    if grep -q "calculator" "$misc_kconfig"; then
        echo -e "${YELLOW}  Calculator already in Kconfig${NC}"
        return
    fi
    
    echo -e "${YELLOW}Updating kernel Kconfig...${NC}"
    
    # Find a good insertion point (before endmenu)
    if grep -q "source.*calculator" "$misc_kconfig"; then
        echo -e "${YELLOW}  Calculator entry already exists${NC}"
        return
    fi
    
    # Add source line before endmenu
    sed -i '/^endmenu/i\
source "drivers/misc/calculator/Kconfig"
' "$misc_kconfig"
    
    echo -e "${GREEN}  Kconfig updated${NC}"
}

# ============================================================================
# Main Integration
# ============================================================================
main() {
    echo -e "${GREEN}Starting integration...${NC}"
    echo ""
    
    # Perform integration based on type
    if [[ "$INTEGRATION_TYPE" == "userspace" ]]; then
        integrate_userspace
    else
        integrate_kernel
        update_kernel_makefile
        update_kernel_kconfig
    fi
    
    # Create device tree if directory specified
    if [[ -n "$DEVICE_TREE_DIR" ]]; then
        create_device_tree
    fi
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Integration Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    if [[ "$INTEGRATION_TYPE" == "kernel" ]]; then
        echo "Next steps:"
        echo "1. Configure kernel: make menuconfig"
        echo "   Navigate to: Device Drivers → Misc devices → Calculator"
        echo "2. Build kernel: make"
        echo "3. Install modules: make modules_install"
    else
        echo "Next steps:"
        echo "1. Build driver: cd <target_dir> && make"
        echo "2. Install: sudo make install"
        echo "3. Use in your application: #include <calculator_driver.h>"
        echo "   Link with: -lcalculator"
    fi
    echo ""
}

# Run main function
main
