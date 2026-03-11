#!/usr/bin/env bash
# ============================================================================
# ssh-to-board.sh — Configure USB Ethernet and SSH into the DE10-Nano board
# ============================================================================
# Usage: ./scripts/ssh-to-board.sh [--serial] [--ip BOARD_IP] [--host-ip HOST_IP]
#                                   [--netmask MASK] [--help]
#
# Default connection (Ethernet):
#   Detects USB Ethernet adapter, assigns host IP, waits for board, then SSHes.
#
# Serial connection:
#   ./scripts/ssh-to-board.sh --serial
#   Auto-detects USB serial device and opens a screen session at 115200 baud.
#
# Defaults:
#   Board IP:  192.168.2.2
#   Host IP:   192.168.2.1
#   Netmask:   255.255.255.0
#   SSH user:  root
#
# Notes:
#   - On macOS, sudo is required to configure the network interface.
#   - The SSH flags suppress host-key errors when the SD card is reflashed.
#   - Re-run after each reboot if the host IP was not made persistent.
# ============================================================================

set -euo pipefail

# ============================================================================
# Defaults
# ============================================================================
BOARD_IP="192.168.2.2"
HOST_IP="192.168.2.1"
NETMASK="255.255.255.0"
SERIAL_MODE=false

# ============================================================================
# Parse arguments
# ============================================================================
while [[ $# -gt 0 ]]; do
    case "$1" in
        --serial)
            SERIAL_MODE=true
            shift
            ;;
        --ip)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --ip requires an address argument" >&2
                exit 1
            fi
            BOARD_IP="$2"
            shift 2
            ;;
        --host-ip)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --host-ip requires an address argument" >&2
                exit 1
            fi
            HOST_IP="$2"
            shift 2
            ;;
        --netmask)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --netmask requires a mask argument" >&2
                exit 1
            fi
            NETMASK="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--serial] [--ip BOARD_IP] [--host-ip HOST_IP] [--netmask MASK]"
            echo ""
            echo "Connect to the DE10-Nano board over USB Ethernet (default) or serial."
            echo ""
            echo "Options:"
            echo "  --serial          Open a serial console (screen at 115200 baud)"
            echo "  --ip ADDR         Board IP address       (default: 192.168.2.2)"
            echo "  --host-ip ADDR    Host IP to assign      (default: 192.168.2.1)"
            echo "  --netmask MASK    Subnet mask            (default: 255.255.255.0)"
            echo "  --help, -h        Show this help and exit"
            exit 0
            ;;
        *)
            echo "Error: unknown option '$1'" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
    esac
done

# ============================================================================
# Helpers
# ============================================================================
OS="$(uname -s)"

pick_from_list() {
    # pick_from_list <prompt> <item1> [item2 ...]
    # Prints the chosen item to stdout.
    local prompt="$1"
    shift
    local items=("$@")

    if [[ ${#items[@]} -eq 1 ]]; then
        echo "${items[0]}"
        return
    fi

    echo "$prompt" >&2
    local i=1
    for item in "${items[@]}"; do
        echo "  $i) $item" >&2
        ((i++))
    done
    printf "Enter number [1]: " >&2
    read -r choice
    choice="${choice:-1}"

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || \
       [[ "$choice" -lt 1 ]] || \
       [[ "$choice" -gt ${#items[@]} ]]; then
        echo "Error: invalid selection '$choice'" >&2
        exit 1
    fi

    echo "${items[$((choice - 1))]}"
}

# ============================================================================
# Serial mode
# ============================================================================
if [[ "$SERIAL_MODE" == true ]]; then
    echo ""
    echo "Serial console mode"
    echo "==================="
    echo ""

    if ! command -v screen &>/dev/null; then
        echo "Error: 'screen' is not installed." >&2
        if [[ "$OS" == "Darwin" ]]; then
            echo "  Install with:  brew install screen" >&2
        else
            echo "  Install with:  sudo apt install screen" >&2
        fi
        exit 1
    fi

    echo "Detecting serial device..."

    candidates=()
    if [[ "$OS" == "Darwin" ]]; then
        while IFS= read -r dev; do
            candidates+=("$dev")
        done < <(ls /dev/tty.usbserial-* 2>/dev/null || true)
    else
        # Linux: check ttyUSB* first, fall back to ttyS0
        while IFS= read -r dev; do
            candidates+=("$dev")
        done < <(ls /dev/ttyUSB* 2>/dev/null || true)
        if [[ ${#candidates[@]} -eq 0 ]]; then
            [[ -e /dev/ttyS0 ]] && candidates+=("/dev/ttyS0")
        fi
    fi

    if [[ ${#candidates[@]} -eq 0 ]]; then
        echo "" >&2
        echo "Error: No serial device found." >&2
        if [[ "$OS" == "Darwin" ]]; then
            echo "  Expected: /dev/tty.usbserial-*" >&2
        else
            echo "  Expected: /dev/ttyUSB* or /dev/ttyS0" >&2
        fi
        echo "  Ensure the DE10-Nano USB UART cable is connected." >&2
        exit 1
    fi

    SERIAL_DEV="$(pick_from_list "Multiple serial devices found — which one?" "${candidates[@]}")"

    echo ""
    echo "Opening serial console: $SERIAL_DEV at 115200 baud"
    echo "(Press Ctrl-A then Ctrl-D to detach from screen)"
    echo ""
    exec screen "$SERIAL_DEV" 115200
fi

# ============================================================================
# Ethernet mode — detect USB Ethernet adapter
# ============================================================================
echo ""
echo "DE10-Nano board connection"
echo "=========================="
echo ""
echo "Detecting USB Ethernet adapter..."

USB_IFACE=""

if [[ "$OS" == "Darwin" ]]; then
    # Parse networksetup output.  Hardware ports are listed in blocks:
    #   Hardware Port: <name>
    #   Device: <iface>
    # We want blocks where the port name contains USB + Ethernet keywords.
    candidates=()
    current_port=""
    current_device=""
    while IFS= read -r line; do
        if [[ "$line" == Hardware\ Port:* ]]; then
            current_port="${line#Hardware Port: }"
            current_device=""
        elif [[ "$line" == Device:* ]]; then
            current_device="${line#Device: }"
            # Match common USB Ethernet adapter descriptions
            if echo "$current_port" | grep -qiE "USB.*(Ethernet|LAN)|Realtek|ASIX|AX88|RTL|Ethernet.*USB"; then
                candidates+=("$current_device ($current_port)")
            fi
        fi
    done < <(networksetup -listallhardwareports 2>/dev/null)

    if [[ ${#candidates[@]} -eq 0 ]]; then
        echo "" >&2
        echo "Error: No USB Ethernet adapter detected." >&2
        echo "  Connect the DE10-Nano USB Ethernet cable and try again." >&2
        echo "" >&2
        echo "  Available hardware ports:" >&2
        networksetup -listallhardwareports 2>/dev/null | grep -E "^(Hardware Port|Device):" | \
            sed 's/^/    /' >&2 || true
        exit 1
    fi

    chosen="$(pick_from_list "Multiple USB Ethernet adapters found — which one?" "${candidates[@]}")"
    # Extract just the interface name (before the first space)
    USB_IFACE="${chosen%% *}"

else
    # Linux: scan /sys/class/net for USB-backed interfaces
    candidates=()
    for iface_path in /sys/class/net/*/; do
        iface="$(basename "$iface_path")"
        driver_path="$iface_path/device/driver"
        if [[ -L "$driver_path" ]]; then
            driver_name="$(basename "$(readlink "$driver_path")")"
            # Common USB Ethernet driver names
            if echo "$driver_name" | grep -qiE "ax88179|asix|r8152|rtl8152|usbnet|cdc_ether|smsc75xx|smsc95xx|lan78xx"; then
                candidates+=("$iface ($driver_name)")
            fi
        fi
    done

    if [[ ${#candidates[@]} -eq 0 ]]; then
        echo "" >&2
        echo "Error: No USB Ethernet adapter detected." >&2
        echo "  Connect the DE10-Nano USB Ethernet cable and try again." >&2
        echo "" >&2
        echo "  To list all network interfaces:" >&2
        echo "    ip link show" >&2
        exit 1
    fi

    chosen="$(pick_from_list "Multiple USB Ethernet adapters found — which one?" "${candidates[@]}")"
    USB_IFACE="${chosen%% *}"
fi

echo "  Found: $USB_IFACE"

# ============================================================================
# Configure the interface
# ============================================================================
echo ""
echo "Configuring interface..."
echo "  Interface: $USB_IFACE"
echo "  Host IP:   $HOST_IP"
echo "  Netmask:   $NETMASK"
echo ""

if [[ "$OS" == "Darwin" ]]; then
    sudo ifconfig "$USB_IFACE" "$HOST_IP" netmask "$NETMASK"
else
    sudo ifconfig "$USB_IFACE" "$HOST_IP" netmask "$NETMASK" up
fi

echo "  Interface configured."

# ============================================================================
# Wait for board to respond
# ============================================================================
echo ""
echo "Waiting for board at $BOARD_IP..."
printf " "

MAX_ATTEMPTS=15
board_up=false

for ((attempt = 1; attempt <= MAX_ATTEMPTS; attempt++)); do
    if ping -c 1 -W 1 "$BOARD_IP" &>/dev/null 2>&1; then
        board_up=true
        break
    fi
    printf "."
    sleep 1
done

echo ""

if [[ "$board_up" == true ]]; then
    echo "  Board is up!"
else
    echo "  Warning: board did not respond after $MAX_ATTEMPTS seconds."
    echo "  It may still be booting — attempting SSH anyway."
fi

# ============================================================================
# SSH into the board
# ============================================================================
echo ""
echo "Connecting via SSH..."
echo "  ssh root@${BOARD_IP}"
echo ""

exec ssh \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "root@${BOARD_IP}"
