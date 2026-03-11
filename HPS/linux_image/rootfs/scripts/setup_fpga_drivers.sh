#!/bin/bash
# ============================================================================
# FPGA Driver Setup Post-Install Script
# ============================================================================
# Sets up FPGA driver access and permissions.
# This script runs INSIDE the chroot during rootfs build.
# ============================================================================

set -e

echo "Setting up FPGA driver access..."

# udev rule: allow /dev/mem access without root for FPGA register access
UDEV_RULES="/etc/udev/rules.d/99-fpga.rules"
mkdir -p "$(dirname "$UDEV_RULES")"
cat > "$UDEV_RULES" << 'EOF'
# FPGA device access — allow root (group 0) read/write access to /dev/mem
KERNEL=="mem", MODE="0660", GROUP="kmem"
EOF
echo "Udev rule written: $UDEV_RULES"

# ============================================================================
# FPGA Bridge Enable Service
# ============================================================================
# The Cyclone V HPS-to-FPGA bridges are controlled by:
#   1. U-Boot: 'bridge enable' command (primary — in boot.scr)
#   2. Linux DT: bridge-enable = <1> in socfpga_cyclone5_de10_nano.dts (secondary)
#   3. This service: runtime fallback via L3 REMAP register write (tertiary)
#
# Linux kernel research (drivers/fpga/fpga-bridge.c, v5.4–v5.10):
#   - sysfs class: /sys/class/fpga_bridge/
#   - devices named br0, br1, ... by registration order
#   - 'state' attribute is READ-ONLY: "enabled" or "disabled"
#   - NO writable enable sysfs attribute in mainline Linux
#   - kernel uses fpga_bridge_enable() API at probe (DT bridge-enable=<1>)
#
# L3 REMAP register (Cyclone V Technical Reference Manual, Table 11-2):
#   Address: 0xFF800000 (l3regs syscon, offset 0x0)
#   Bit 0: MPUZERO (always set when enabling any bridge)
#   Bit 3: HPS2FPGA bridge enable
#   Bit 4: LWHPS2FPGA bridge enable (the one we need for calculator IP)
#
# To enable LW bridge: write 0x19 (bits 4|3|0) to 0xFF800000
# To check bridge state: cat /sys/class/fpga_bridge/br*/state
# ============================================================================

mkdir -p /etc/systemd/system

cat > /etc/systemd/system/fpga-bridge-enable.service << 'BRIDGE_SVC'
[Unit]
Description=Enable Altera HPS-to-FPGA Bridges
# Run after FPGA manager has time to load the bitstream
After=local-fs.target
DefaultDependencies=no
# Only meaningful with FPGA fabric (bitstream must be loaded first by U-Boot)
ConditionPathExists=/sys/class/fpga_bridge

[Service]
Type=oneshot
RemainAfterExit=yes

# Check bridge state and report
ExecStart=/bin/bash -c '\
    echo "FPGA Bridge Status:"; \
    for state_file in /sys/class/fpga_bridge/*/state; do \
        bridge=$(basename $(dirname $state_file)); \
        name_file=$(dirname $state_file)/name; \
        name=$(cat $name_file 2>/dev/null || echo "unknown"); \
        state=$(cat $state_file 2>/dev/null || echo "unreadable"); \
        echo "  $bridge ($name): $state"; \
    done; \
    all_enabled=true; \
    for state_file in /sys/class/fpga_bridge/*/state; do \
        [ -f "$state_file" ] || continue; \
        state=$(cat "$state_file" 2>/dev/null); \
        if [ "$state" != "enabled" ]; then \
            all_enabled=false; \
            break; \
        fi; \
    done; \
    if $all_enabled; then \
        echo "All FPGA bridges enabled (DT bridge-enable=<1> or U-Boot bridge enable succeeded)"; \
        if [ -x /usr/local/bin/devmem2 ]; then \
            ver=$(devmem2 0xff20003c w 2>/dev/null | grep -o "0x[0-9A-Fa-f]*$" || echo "0x0"); \
            if [ "$ver" = "0x0" ] || [ "$ver" = "0x00000000" ]; then \
                echo "WARNING: VERSION register returns 0 — FPGA IP not responding."; \
                echo "  Check DIP switch SW10 (MSEL) is set for HPS FPGA programming."; \
                echo "  Power cycle required after changing MSEL (reboot is not enough)."; \
            else \
                echo "FPGA calculator IP responding (VERSION=$ver)"; \
            fi; \
        fi; \
    else \
        echo "WARNING: Some bridges not enabled via DT. Attempting L3 REMAP fallback..."; \
        if [ -x /usr/local/bin/devmem2 ]; then \
            devmem2 0xff800000 w 0x00000019 && echo "L3 REMAP written: LW+HPS2FPGA bridges enabled" \
            || echo "ERROR: devmem2 L3 REMAP write failed"; \
        else \
            echo "devmem2 not available, cannot apply fallback"; \
        fi; \
    fi'

[Install]
WantedBy=multi-user.target
BRIDGE_SVC

# Enable at boot
if command -v systemctl &>/dev/null; then
    systemctl enable fpga-bridge-enable.service 2>/dev/null || true
else
    mkdir -p /etc/systemd/system/multi-user.target.wants
    ln -sf /etc/systemd/system/fpga-bridge-enable.service \
           /etc/systemd/system/multi-user.target.wants/fpga-bridge-enable.service
fi

echo "FPGA bridge enable service installed (fpga-bridge-enable.service)"
echo "FPGA driver setup complete"
