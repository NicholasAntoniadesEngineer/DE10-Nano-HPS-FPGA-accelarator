#!/bin/bash
# ============================================================================
# Verify Ethernet Configuration in Kernel Build
# ============================================================================
# Checks if Ethernet driver is enabled in kernel configuration
# ============================================================================

KERNEL_BUILD_DIR="${KERNEL_BUILD_DIR:-$(pwd)/build}"

if [ ! -f "$KERNEL_BUILD_DIR/.config" ]; then
    echo "ERROR: Kernel configuration not found: $KERNEL_BUILD_DIR/.config"
    echo "Build kernel first: make kernel-config"
    exit 1
fi

echo "Checking Ethernet driver configuration..."
echo ""

# Check for STMMAC driver
if grep -q "CONFIG_STMMAC_ETH=y" "$KERNEL_BUILD_DIR/.config"; then
    echo "✓ STMMAC Ethernet driver: ENABLED"
else
    echo "✗ STMMAC Ethernet driver: NOT ENABLED"
    echo "  Enable in kernel config: CONFIG_STMMAC_ETH=y"
fi

# Check for DWMAC Generic
if grep -q "CONFIG_DWMAC_GENERIC=y" "$KERNEL_BUILD_DIR/.config"; then
    echo "✓ DWMAC Generic support: ENABLED"
else
    echo "✗ DWMAC Generic support: NOT ENABLED"
    echo "  Enable in kernel config: CONFIG_DWMAC_GENERIC=y"
fi

# Check for DWMAC SoCFPGA
if grep -q "CONFIG_DWMAC_SOCFPGA=y" "$KERNEL_BUILD_DIR/.config"; then
    echo "✓ DWMAC SoCFPGA support: ENABLED"
else
    echo "✗ DWMAC SoCFPGA support: NOT ENABLED"
    echo "  Enable in kernel config: CONFIG_DWMAC_SOCFPGA=y"
fi

echo ""
echo "To enable Ethernet support:"
echo "  cd linux-socfpga"
echo "  make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- menuconfig"
echo "  Navigate to: Device Drivers → Network device support → Ethernet driver support"
echo "  Enable: STMicroelectronics Multi-Gigabit Ethernet driver"
