#!/usr/bin/env bash
# ============================================================================
# share-internet.sh — Share Mac internet with DE10-Nano over USB Ethernet
# ============================================================================
# Usage: ./scripts/share-internet.sh [--stop] [--help]
#
# Sets up:
#   1. USB Ethernet interface (192.168.2.1)
#   2. IP forwarding (sysctl)
#   3. NAT via PF (packet filter)
#   4. Board default route and DNS (via SSH)
#
# Requires sudo on macOS. Run --stop to tear down.
# ============================================================================

set -euo pipefail

# ============================================================================
# Defaults
# ============================================================================
BOARD_IP="192.168.2.2"
HOST_IP="192.168.2.1"
NETMASK="255.255.255.0"
BOARD_USER="root"
BOARD_PASS="root"
STOP_MODE=false
DNS_SERVER="8.8.8.8"

# ============================================================================
# Colors
# ============================================================================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERR]${NC}  $1" >&2; }

# ============================================================================
# Parse arguments
# ============================================================================
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stop)
            STOP_MODE=true
            shift
            ;;
        --dns)
            DNS_SERVER="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--stop] [--dns SERVER] [--help]"
            echo ""
            echo "Share your Mac's internet with the DE10-Nano over USB Ethernet."
            echo ""
            echo "Options:"
            echo "  --stop       Tear down internet sharing (disable NAT + forwarding)"
            echo "  --dns ADDR   DNS server for the board (default: 8.8.8.8)"
            echo "  --help, -h   Show this help and exit"
            echo ""
            echo "Requires sudo. The board must already be booted and reachable."
            exit 0
            ;;
        *)
            log_err "Unknown option '$1'. Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

# ============================================================================
# macOS-only check
# ============================================================================
if [[ "$(uname -s)" != "Darwin" ]]; then
    log_err "This script is macOS-only. On Linux, use iptables for NAT."
    exit 1
fi

# ============================================================================
# Stop mode — tear down
# ============================================================================
if [[ "$STOP_MODE" == true ]]; then
    echo ""
    echo -e "${BOLD}Tearing down internet sharing${NC}"
    echo "=============================="
    echo ""

    log_info "Disabling IP forwarding..."
    sudo sysctl -w net.inet.ip.forwarding=0 > /dev/null 2>&1
    log_ok "IP forwarding disabled"

    log_info "Disabling PF NAT rules..."
    sudo pfctl -d 2>/dev/null || true
    log_ok "PF disabled"

    echo ""
    log_ok "Internet sharing stopped."
    exit 0
fi

# ============================================================================
# Detect internet-facing interface
# ============================================================================
echo ""
echo -e "${BOLD}DE10-Nano Internet Sharing Setup${NC}"
echo "=================================="
echo ""

log_info "Detecting internet-facing interface..."
INET_IFACE="$(route get 8.8.8.8 2>/dev/null | awk '/interface:/{print $2}')" || true

if [[ -z "$INET_IFACE" ]]; then
    log_err "No internet connection detected on this Mac."
    exit 1
fi

log_ok "Internet via: $INET_IFACE"

# ============================================================================
# Detect USB Ethernet adapter
# ============================================================================
log_info "Detecting USB Ethernet adapter..."

USB_IFACE=""
while IFS= read -r line; do
    if [[ "$line" == Hardware\ Port:* ]]; then
        current_port="${line#Hardware Port: }"
        current_device=""
    elif [[ "$line" == Device:* ]]; then
        current_device="${line#Device: }"
        if echo "$current_port" | grep -qiE "USB.*(Ethernet|LAN)|Realtek|ASIX|AX88|RTL|Ethernet.*USB"; then
            USB_IFACE="$current_device"
            break
        fi
    fi
done < <(networksetup -listallhardwareports 2>/dev/null)

if [[ -z "$USB_IFACE" ]]; then
    log_err "No USB Ethernet adapter found."
    echo "  Connect the DE10-Nano USB Ethernet cable and try again." >&2
    echo "  Available ports:" >&2
    networksetup -listallhardwareports 2>/dev/null | grep -E "^(Hardware Port|Device):" | sed 's/^/    /' >&2
    exit 1
fi

log_ok "USB Ethernet: $USB_IFACE"

# ============================================================================
# Step 1: Configure USB Ethernet interface
# ============================================================================
echo ""
log_info "Step 1: Configuring $USB_IFACE → $HOST_IP"
sudo ifconfig "$USB_IFACE" "$HOST_IP" netmask "$NETMASK"
log_ok "Interface configured"

# ============================================================================
# Step 2: Enable IP forwarding
# ============================================================================
log_info "Step 2: Enabling IP forwarding"

CURRENT_FWD="$(sysctl -n net.inet.ip.forwarding 2>/dev/null)"
if [[ "$CURRENT_FWD" == "1" ]]; then
    log_ok "IP forwarding already enabled"
else
    sudo sysctl -w net.inet.ip.forwarding=1 > /dev/null 2>&1
    log_ok "IP forwarding enabled"
fi

# ============================================================================
# Step 3: Enable NAT via PF
# ============================================================================
log_info "Step 3: Enabling NAT ($USB_IFACE → $INET_IFACE)"

PF_RULES="nat on $INET_IFACE from ${BOARD_IP}/24 to any -> ($INET_IFACE)"
echo "$PF_RULES" | sudo pfctl -ef - 2>/dev/null
log_ok "NAT enabled"

# ============================================================================
# Step 4: Wait for board
# ============================================================================
echo ""
log_info "Step 4: Waiting for board at $BOARD_IP..."

BOARD_UP=false
for i in $(seq 1 15); do
    if ping -c 1 -W 1 "$BOARD_IP" &>/dev/null; then
        BOARD_UP=true
        break
    fi
    printf "." >&2
    sleep 1
done
echo "" >&2

if [[ "$BOARD_UP" != true ]]; then
    log_err "Board not reachable at $BOARD_IP after 15 seconds."
    echo "  Internet sharing is configured on the Mac side." >&2
    echo "  Once the board boots, SSH in and run:" >&2
    echo "    ip route add default via $HOST_IP" >&2
    echo "    echo 'nameserver $DNS_SERVER' > /etc/resolv.conf" >&2
    exit 1
fi

log_ok "Board is up"

# ============================================================================
# Step 5: Configure board routing and DNS via SSH
# ============================================================================
log_info "Step 5: Configuring board route and DNS..."

# Use sshpass if available, otherwise try key-based auth
SSH_CMD="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR"

if command -v sshpass &>/dev/null; then
    SSH_CMD="sshpass -p '$BOARD_PASS' $SSH_CMD"
fi

BOARD_SCRIPT="
# Add default route if not present
if ! ip route show | grep -q 'default via $HOST_IP'; then
    ip route replace default via $HOST_IP
fi

# Set DNS
echo 'nameserver $DNS_SERVER' > /etc/resolv.conf
"

eval $SSH_CMD "${BOARD_USER}@${BOARD_IP}" "$BOARD_SCRIPT" 2>/dev/null
log_ok "Board route and DNS configured"

# ============================================================================
# Step 6: Verify connectivity
# ============================================================================
echo ""
log_info "Step 6: Testing internet from board..."

PING_RESULT="$(eval $SSH_CMD "${BOARD_USER}@${BOARD_IP}" "ping -c 2 -W 3 $DNS_SERVER 2>&1" 2>/dev/null)" || true

if echo "$PING_RESULT" | grep -q "bytes from"; then
    log_ok "Internet working! Board can reach $DNS_SERVER"
else
    log_warn "Ping to $DNS_SERVER failed from board."
    echo "  NAT is configured — this may be a firewall issue." >&2
    echo "  Try: sudo pfctl -s nat   (check NAT rules)" >&2
fi

# Test DNS resolution
DNS_RESULT="$(eval $SSH_CMD "${BOARD_USER}@${BOARD_IP}" "ping -c 1 -W 3 google.com 2>&1" 2>/dev/null)" || true

if echo "$DNS_RESULT" | grep -q "bytes from"; then
    log_ok "DNS working! Board can resolve google.com"
else
    log_warn "DNS resolution failed. IP connectivity may still work."
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo -e "${BOLD}Internet Sharing Active${NC}"
echo "========================"
echo "  Mac internet:    $INET_IFACE"
echo "  USB Ethernet:    $USB_IFACE ($HOST_IP)"
echo "  Board:           $BOARD_IP"
echo "  DNS:             $DNS_SERVER"
echo ""
echo "  To stop:  $0 --stop"
echo "  To SSH:   ssh root@$BOARD_IP"
echo ""
