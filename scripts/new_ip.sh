#!/usr/bin/env bash
# ============================================================================
# new_ip.sh — Scaffold a new custom FPGA IP and HPS driver
# ============================================================================
# Usage: ./scripts/new_ip.sh <ip_name> [--no-qsys] [--no-driver]
#
# Creates:
#   FPGA/ip/custom/<ip_name>/         — Verilog template + _hw.tcl
#   HPS/drivers/<ip_name>/            — C driver template + Makefile
#   Patches soc_system.qsys           — Module + connections (unless --no-qsys)
#
# After running, review changes with:
#   git diff
#
# Then implement your core logic in:
#   FPGA/ip/custom/<ip_name>/<ip_name>_core.v
# ============================================================================

set -euo pipefail

# ============================================================================
# Parse arguments
# ============================================================================
SKIP_QSYS=false
SKIP_DRIVER=false
IP_NAME=""

for arg in "$@"; do
    case "$arg" in
        --no-qsys)   SKIP_QSYS=true ;;
        --no-driver)  SKIP_DRIVER=true ;;
        --help|-h)
            echo "Usage: $0 <ip_name> [--no-qsys] [--no-driver]"
            echo ""
            echo "Scaffolds a new custom FPGA IP with Verilog templates, QSys integration,"
            echo "and an HPS C driver."
            echo ""
            echo "Options:"
            echo "  --no-qsys    Skip patching soc_system.qsys (do it manually or via GUI)"
            echo "  --no-driver  Skip creating HPS driver template"
            echo "  --help       Show this help"
            exit 0
            ;;
        -*)
            echo "Error: unknown option '$arg'" >&2
            exit 1
            ;;
        *)
            if [ -n "$IP_NAME" ]; then
                echo "Error: multiple IP names given ('$IP_NAME' and '$arg')" >&2
                exit 1
            fi
            IP_NAME="$arg"
            ;;
    esac
done

if [ -z "$IP_NAME" ]; then
    echo "Error: IP name required" >&2
    echo "Usage: $0 <ip_name> [--no-qsys] [--no-driver]" >&2
    exit 1
fi

# Validate name: lowercase alphanumeric + underscores only
if ! echo "$IP_NAME" | grep -qE '^[a-z][a-z0-9_]*$'; then
    echo "Error: IP name must be lowercase alphanumeric with underscores (e.g., moving_average)" >&2
    exit 1
fi

# ============================================================================
# Resolve paths
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FPGA_DIR="$PROJECT_ROOT/FPGA"
TEMPLATE_DIR="$FPGA_DIR/ip/custom/template"
IP_DIR="$FPGA_DIR/ip/custom/$IP_NAME"
QSYS_FILE="$FPGA_DIR/quartus/qsys/soc_system.qsys"

DRIVER_TEMPLATE_DIR="$PROJECT_ROOT/HPS/drivers/template"
DRIVER_DIR="$PROJECT_ROOT/HPS/drivers/$IP_NAME"

# Uppercase version for C macros (e.g., moving_average -> MOVING_AVERAGE)
IP_UPPER=$(echo "$IP_NAME" | tr '[:lower:]' '[:upper:]')

# ============================================================================
# Pre-flight checks
# ============================================================================
if [ -d "$IP_DIR" ]; then
    echo "Error: $IP_DIR already exists" >&2
    exit 1
fi

if [ ! "$SKIP_DRIVER" = true ] && [ -d "$DRIVER_DIR" ]; then
    echo "Error: $DRIVER_DIR already exists" >&2
    exit 1
fi

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "Error: FPGA template not found at $TEMPLATE_DIR" >&2
    exit 1
fi

# ============================================================================
# Auto-assign base address and IRQ number from existing QSys XML
# ============================================================================
auto_assign_address() {
    local qsys="$1"
    # Find all existing baseAddress values, pick the next 0x100-aligned slot
    local max_addr=0
    while IFS= read -r line; do
        # Extract hex value from baseAddress parameter lines
        addr=$(echo "$line" | sed -n 's/.*value="0x\([0-9a-fA-F]*\)".*/\1/p')
        [ -z "$addr" ] && continue
        dec=$((16#$addr))
        if [ "$dec" -gt "$max_addr" ]; then
            max_addr=$dec
        fi
    done < <(grep 'baseAddress' "$qsys" 2>/dev/null | grep 'value="0x' || true)

    # Round up to next 0x100 boundary (each IP gets 256 bytes = 64 word-registers)
    local next=$(( ((max_addr / 256) + 1) * 256 ))
    printf "0x%04X" "$next"
}

auto_assign_irq() {
    local qsys="$1"
    local max_irq=-1
    while IFS= read -r line; do
        irq=$(echo "$line" | sed -n 's/.*value="\([0-9]*\)".*/\1/p')
        [ -z "$irq" ] && continue
        if [ "$irq" -gt "$max_irq" ]; then
            max_irq=$irq
        fi
    done < <(grep 'irqNumber' "$qsys" 2>/dev/null | grep 'value="' || true)
    echo $(( max_irq + 1 ))
}

BASE_ADDR="0x0100"
IRQ_NUM="1"

if [ ! "$SKIP_QSYS" = true ] && [ -f "$QSYS_FILE" ]; then
    BASE_ADDR=$(auto_assign_address "$QSYS_FILE")
    IRQ_NUM=$(auto_assign_irq "$QSYS_FILE")
fi

# ============================================================================
# Step 1: Copy and rename FPGA template
# ============================================================================
echo "Creating FPGA IP:  $IP_DIR"
cp -r "$TEMPLATE_DIR" "$IP_DIR"

# Rename files: template_* -> <ip_name>_*, template_ip.v -> <ip_name>.v
cd "$IP_DIR"
for f in template_ip.v; do
    [ -f "$f" ] && mv "$f" "${IP_NAME}.v"
done
for f in template_*.v template_*.tcl; do
    [ -f "$f" ] || continue
    mv "$f" "${f/template_/${IP_NAME}_}"
done
# Rename _hw.tcl: template_hw.tcl -> <ip_name>_hw.tcl
[ -f "template_hw.tcl" ] && mv "template_hw.tcl" "${IP_NAME}_hw.tcl"

# Replace content references
for f in *.v *.tcl; do
    [ -f "$f" ] || continue
    # Replace module/instance names
    sed -i.bak "s/template_ip/${IP_NAME}/g" "$f"
    sed -i.bak "s/template/${IP_NAME}/g" "$f"
    sed -i.bak "s/TEMPLATE/${IP_UPPER}/g" "$f"
    rm -f "$f.bak"
done

# ============================================================================
# Step 2: Create HPS driver from template
# ============================================================================
if [ ! "$SKIP_DRIVER" = true ]; then
    if [ -d "$DRIVER_TEMPLATE_DIR" ]; then
        echo "Creating HPS driver: $DRIVER_DIR"
        cp -r "$DRIVER_TEMPLATE_DIR" "$DRIVER_DIR"

        cd "$DRIVER_DIR"
        for f in template_*; do
            [ -f "$f" ] || continue
            mv "$f" "${f/template_/${IP_NAME}_}"
        done

        for f in *.c *.h Makefile; do
            [ -f "$f" ] || continue
            sed -i.bak "s/template/${IP_NAME}/g" "$f"
            sed -i.bak "s/TEMPLATE/${IP_UPPER}/g" "$f"
            sed -i.bak "s/libtemplate/lib${IP_NAME}/g" "$f"
            rm -f "$f.bak"
        done

        # Set the auto-assigned base address in the driver header
        local_offset=$(echo "$BASE_ADDR" | tr '[:upper:]' '[:lower:]')
        header_file="${IP_NAME}_driver.h"
        if [ -f "$header_file" ]; then
            sed -i.bak "s/0x0100/$BASE_ADDR/g" "$header_file"
            rm -f "$header_file.bak"
        fi
    else
        echo "Warning: HPS driver template not found at $DRIVER_TEMPLATE_DIR (skipping)"
    fi
fi

# ============================================================================
# Step 3: Patch soc_system.qsys
# ============================================================================
if [ ! "$SKIP_QSYS" = true ] && [ -f "$QSYS_FILE" ]; then
    echo "Patching QSys:     $QSYS_FILE"

    # Compute next sortIndex for bonusData
    max_sort=$(grep 'value = "' "$QSYS_FILE" | sed -n 's/.*value = "\([0-9]*\)".*/\1/p' | sort -n | tail -1)
    max_sort=${max_sort:-0}
    next_sort=$((max_sort + 1))

    # Write insertion fragments to temp files (avoids awk multi-line variable issues on macOS)
    TMPDIR_PATCH=$(mktemp -d)
    trap "rm -rf '$TMPDIR_PATCH'" EXIT

    # --- bonusData fragment ---
    cat > "$TMPDIR_PATCH/bonus.txt" <<BONUS_EOF
   element ${IP_NAME}_0
   {
      datum _sortIndex
      {
         value = "${next_sort}";
         type = "int";
      }
      datum sopceditor_expanded
      {
         value = "1";
         type = "boolean";
      }
   }
   element ${IP_NAME}_0.s0
   {
      datum baseAddress
      {
         value = "${BASE_ADDR}";
         type = "String";
      }
   }
BONUS_EOF

    # --- module fragment ---
    cat > "$TMPDIR_PATCH/module.txt" <<MODULE_EOF
 <module name="${IP_NAME}_0" kind="${IP_NAME}" version="1.0" enabled="1">
  <parameter name="AUTO_CLOCK_CLOCK_RATE" value="50000000" />
 </module>
MODULE_EOF

    # --- connections fragment ---
    cat > "$TMPDIR_PATCH/connections.txt" <<CONN_EOF
 <connection
   kind="clock"
   version="20.1"
   start="clk_0.clk"
   end="${IP_NAME}_0.clock" />
 <connection
   kind="reset"
   version="20.1"
   start="hps_0.h2f_reset"
   end="${IP_NAME}_0.reset" />
 <connection
   kind="avalon"
   version="20.1"
   start="hps_0.h2f_lw_axi_master"
   end="${IP_NAME}_0.s0">
  <parameter name="baseAddress" value="${BASE_ADDR}" />
 </connection>
 <connection
   kind="interrupt"
   version="20.1"
   start="hps_0.f2h_irq0"
   end="${IP_NAME}_0.irq">
  <parameter name="irqNumber" value="${IRQ_NUM}" />
 </connection>
CONN_EOF

    # Insert bonusData before the closing "}" in the CDATA block
    # (the lone "}" line before "]]>" in the bonusData parameter)
    awk '
    /^}$/ && !done { while ((getline line < "'"$TMPDIR_PATCH/bonus.txt"'") > 0) print line; done=1 }
    { print }
    ' "$QSYS_FILE" > "$QSYS_FILE.tmp" && mv "$QSYS_FILE.tmp" "$QSYS_FILE"

    # Insert module before the first <connection tag
    awk '
    !done && /<connection/ { while ((getline line < "'"$TMPDIR_PATCH/module.txt"'") > 0) print line; done=1 }
    { print }
    ' "$QSYS_FILE" > "$QSYS_FILE.tmp" && mv "$QSYS_FILE.tmp" "$QSYS_FILE"

    # Insert connections before first <interconnectRequirement>
    awk '
    !done && /<interconnectRequirement/ { while ((getline line < "'"$TMPDIR_PATCH/connections.txt"'") > 0) print line; done=1 }
    { print }
    ' "$QSYS_FILE" > "$QSYS_FILE.tmp" && mv "$QSYS_FILE.tmp" "$QSYS_FILE"

    echo ""
    echo "QSys integration:"
    echo "  Instance:     ${IP_NAME}_0"
    echo "  Base address: ${BASE_ADDR} (LW bridge offset)"
    echo "  IRQ number:   ${IRQ_NUM}"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "============================================"
echo "  Scaffold complete: ${IP_NAME}"
echo "============================================"
echo ""
echo "Files created:"
echo "  FPGA/ip/custom/${IP_NAME}/"
for f in "$IP_DIR"/*; do
    echo "    $(basename "$f")"
done
if [ ! "$SKIP_DRIVER" = true ] && [ -d "$DRIVER_DIR" ]; then
    echo "  HPS/drivers/${IP_NAME}/"
    for f in "$DRIVER_DIR"/*; do
        echo "    $(basename "$f")"
    done
fi
echo ""
echo "Next steps:"
echo "  1. Implement your logic in FPGA/ip/custom/${IP_NAME}/${IP_NAME}_core.v"
echo "  2. Review QSys changes:  git diff FPGA/quartus/qsys/soc_system.qsys"
echo "  3. Review all changes:   git diff"
echo "  4. Build:                cd FPGA && make everything"
echo ""
echo "  If your IP has conduit exports (LEDs, GPIO), also:"
echo "  5. Uncomment conduit in ${IP_NAME}_hw.tcl"
echo "  6. Wire ports in FPGA/hdl/DE10_NANO_SoC_GHRD.v (see README Step 4)"
