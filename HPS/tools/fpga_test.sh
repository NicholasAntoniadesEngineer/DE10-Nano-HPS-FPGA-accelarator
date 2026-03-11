#!/bin/bash
# FPGA Register Access Test Script
# Run from macOS to SSH into DE10-Nano and test calculator IP registers
set -euo pipefail

BOARD_IP="${1:-192.168.2.2}"
BOARD_USER="root"
BOARD_PASS="root"
LW_BASE="0xff200000"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

pass() { echo -e "  ${GREEN}PASS${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}FAIL${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}WARN${NC} $1"; ((WARN++)); }
info() { echo -e "  ${CYAN}INFO${NC} $1"; }

ssh_cmd() {
    sshpass -p "$BOARD_PASS" ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        -o LogLevel=ERROR "$BOARD_USER@$BOARD_IP" "$1" 2>/dev/null
}

echo "============================================"
echo " DE10-Nano FPGA Calculator Test Suite"
echo "============================================"
echo ""

# Check prerequisites
if ! command -v sshpass &>/dev/null; then
    echo -e "${RED}ERROR: sshpass not installed. Run: brew install sshpass${NC}"
    echo "  Or: brew install hudochenkov/sshpass/sshpass"
    exit 1
fi

# 1. Connectivity
echo "[1/7] Network Connectivity"
if ping -c 1 -W 2000 "$BOARD_IP" &>/dev/null; then
    pass "Board reachable at $BOARD_IP"
else
    fail "Board not reachable at $BOARD_IP"
    echo ""
    echo "  Ensure USB Ethernet is configured:"
    echo "    sudo ifconfig en13 192.168.2.1 netmask 255.255.255.0"
    echo "  And board is powered on with correct DIP switch (SW10) settings."
    exit 1
fi

# 2. SSH
echo "[2/7] SSH Access"
HOSTNAME=$(ssh_cmd "hostname" || echo "FAILED")
if [ "$HOSTNAME" = "de10-nano" ]; then
    pass "SSH connected (hostname: $HOSTNAME)"
else
    fail "SSH failed (got: $HOSTNAME)"
    echo "  Check: sshpass -p root ssh root@$BOARD_IP"
    exit 1
fi

# 3. System state
echo "[3/7] System State"
KERNEL=$(ssh_cmd "uname -r")
info "Kernel: $KERNEL"

FPGA_STATE=$(ssh_cmd "cat /sys/class/fpga_manager/fpga0/state 2>/dev/null || echo unknown")
if [ "$FPGA_STATE" = "operating" ]; then
    pass "FPGA manager: $FPGA_STATE"
else
    fail "FPGA manager: $FPGA_STATE (expected 'operating')"
fi

BRIDGE_STATES=$(ssh_cmd "for f in /sys/class/fpga_bridge/*/state; do echo \$(basename \$(dirname \$f))=\$(cat \$f); done")
ALL_ENABLED=true
for state in $BRIDGE_STATES; do
    if [[ "$state" == *"=enabled" ]]; then
        pass "Bridge $state"
    else
        fail "Bridge $state (expected enabled)"
        ALL_ENABLED=false
    fi
done

BRGMODRST=$(ssh_cmd "devmem2 0xffd0501c w 2>/dev/null | grep 'Value' | awk '{print \$NF}'")
if [ "$BRGMODRST" = "0x0" ]; then
    pass "BRGMODRST = 0x0 (bridge resets deasserted)"
else
    warn "BRGMODRST = $BRGMODRST (expected 0x0)"
fi

# 4. VERSION register (read-only constant, always 0x00010001)
echo "[4/7] VERSION Register (0xFF20003C)"
VERSION=$(ssh_cmd "devmem2 0xff20003c w 2>/dev/null | grep 'Value' | awk '{print \$NF}'")
if [ "$VERSION" = "0x10001" ] || [ "$VERSION" = "0x00010001" ]; then
    pass "VERSION = $VERSION (calculator IP detected)"
else
    fail "VERSION = $VERSION (expected 0x00010001)"
    echo ""
    echo "  If VERSION is 0x0, check:"
    echo "    1. DIP switch SW10 set correctly for HPS FPGA boot"
    echo "    2. Power cycle (not just reboot) after changing switches"
    echo "    3. FAT partition has correct RBF: ls -la /mnt/fat/*.rbf"
    echo "    4. boot.scr runs fpga load: strings /mnt/fat/boot.scr"
fi

# 5. Register write/read test
echo "[5/7] Register Write/Read"
RESULTS=$(ssh_cmd '
    # Write operand A
    devmem2 0xff200004 w 0x3F800000 2>/dev/null | grep -o "readback.*" || echo "write_fail"
    # Read back operand A
    A=$(devmem2 0xff200004 w 2>/dev/null | grep "Value" | awk "{print \$NF}")
    echo "OPERAND_A=$A"
    # Write operand B
    devmem2 0xff200008 w 0x40000000 2>/dev/null | grep -o "readback.*" || echo "write_fail"
    # Read back operand B
    B=$(devmem2 0xff200008 w 2>/dev/null | grep "Value" | awk "{print \$NF}")
    echo "OPERAND_B=$B"
')

A_VAL=$(echo "$RESULTS" | grep "OPERAND_A=" | cut -d= -f2)
B_VAL=$(echo "$RESULTS" | grep "OPERAND_B=" | cut -d= -f2)

if [ "$A_VAL" = "0x3F800000" ] || [ "$A_VAL" = "0x3f800000" ]; then
    pass "OPERAND_A write/read: 0x3F800000 (1.0f)"
else
    fail "OPERAND_A read: $A_VAL (expected 0x3F800000)"
fi

if [ "$B_VAL" = "0x40000000" ] || [ "$B_VAL" = "0x40000000" ]; then
    pass "OPERAND_B write/read: 0x40000000 (2.0f)"
else
    fail "OPERAND_B read: $B_VAL (expected 0x40000000)"
fi

# 6. Calculation test: 1.0 + 2.0 = 3.0
echo "[6/7] Calculation: 1.0 + 2.0"
CALC_RESULT=$(ssh_cmd '
    devmem2 0xff200004 w 0x3F800000 >/dev/null 2>&1  # A = 1.0
    devmem2 0xff200008 w 0x40000000 >/dev/null 2>&1  # B = 2.0
    devmem2 0xff200000 w 0x80000000 >/dev/null 2>&1  # CONTROL: op=ADD(0), start=1
    sleep 0.01
    STATUS=$(devmem2 0xff200010 w 2>/dev/null | grep "Value" | awk "{print \$NF}")
    RESULT=$(devmem2 0xff20000c w 2>/dev/null | grep "Value" | awk "{print \$NF}")
    echo "STATUS=$STATUS"
    echo "RESULT=$RESULT"
')

CALC_STATUS=$(echo "$CALC_RESULT" | grep "STATUS=" | cut -d= -f2)
CALC_VAL=$(echo "$CALC_RESULT" | grep "RESULT=" | cut -d= -f2)

# Status bit 1 = calc_done
if [[ "$CALC_STATUS" == *"2"* ]] || [[ "$CALC_STATUS" == *"0x2" ]]; then
    pass "STATUS shows calc_done"
elif [ "$CALC_STATUS" = "0x0" ]; then
    warn "STATUS = 0x0 (calculation may not have completed)"
else
    info "STATUS = $CALC_STATUS"
fi

if [ "$CALC_VAL" = "0x40400000" ] || [ "$CALC_VAL" = "0x40400000" ]; then
    pass "RESULT = 0x40400000 (3.0f) — ADD correct!"
else
    fail "RESULT = $CALC_VAL (expected 0x40400000 = 3.0f)"
fi

# 7. Kernel errors
echo "[7/7] Kernel Health"
ABORTS=$(ssh_cmd "dmesg | grep -c 'external abort\|Unhandled fault' 2>/dev/null || echo 0")
if [ "$ABORTS" = "0" ]; then
    pass "No bus errors in dmesg"
else
    warn "$ABORTS bus error(s) in dmesg"
    ssh_cmd "dmesg | grep 'external abort\|Unhandled fault' | tail -3" | while read -r line; do
        info "  $line"
    done
fi

# Summary
echo ""
echo "============================================"
echo -e " Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "============================================"

if [ "$FAIL" -eq 0 ]; then
    echo -e " ${GREEN}All critical tests passed.${NC}"
    exit 0
else
    echo -e " ${RED}Some tests failed. See output above.${NC}"
    exit 1
fi
