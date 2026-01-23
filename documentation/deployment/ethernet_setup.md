# Ethernet Configuration for DE10-Nano

## Overview

The DE10-Nano has **Ethernet built into the HPS (Hard Processor System)**, not in the FPGA fabric. For basic internet access, you only need the HPS Ethernet interface configured - no FPGA implementation is required.

## Architecture

The DE10-Nano SoC includes a **Gigabit Ethernet MAC (GMAC)** controller in the HPS:
- **Hardware**: Built into the ARM Cortex-A9 processor subsystem
- **Address**: `0xFF702000` (GMAC1)
- **Interface**: RGMII (Reduced Gigabit Media Independent Interface)
- **Physical Connection**: Connected to the Ethernet RJ-45 port on the board

The FPGA does NOT implement Ethernet - it only passes through HPS I/O pins to the physical connector.

## Configuration Status

All Ethernet configuration is handled automatically by the build system:

| Component | Status | Location |
|-----------|--------|----------|
| Hardware pins | Configured | `FPGA/hdl/DE10_NANO_SoC_GHRD.v` |
| Device tree | Auto-generated | `FPGA/quartus/qsys/hps_common_board_info.xml` |
| Network interface | Pre-configured | `HPS/rootfs/configs/network/interfaces` |
| Kernel driver | Included | STMMAC driver in default config |

## Testing Ethernet

After booting the DE10-Nano:

```bash
# Check if Ethernet interface exists
ip addr show eth0

# Check if driver is loaded
dmesg | grep -i ethernet
dmesg | grep -i gmac

# Test network connectivity
ping -c 3 google.com
```

## Network Configuration Options

### DHCP (Default)

The rootfs is pre-configured for DHCP:
```bash
auto eth0
iface eth0 inet dhcp
```

### Static IP

To configure static IP, edit `/etc/network/interfaces`:
```bash
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
```

## Internet Sharing via USB-C Dongle (Mac)

To connect DE10-Nano to internet via a Mac with USB-C Ethernet dongle:

1. **Enable Internet Sharing on Mac:**
   - Open **System Preferences** > **Sharing**
   - Select **Internet Sharing**
   - Share Wi-Fi connection to the Ethernet adapter
   - Turn on Internet Sharing

2. **Configure DE10-Nano:**
   ```bash
   # Initialize network via DHCP
   sudo dhclient eth0
   
   # Test connection
   ping -c 3 google.com
   ```

## Troubleshooting

### Ethernet Interface Not Found

```bash
# Check kernel driver
lsmod | grep stmmac
dmesg | grep -i ethernet

# Check device tree
cat /proc/device-tree/sopc@0/ethernet@ff702000/status
# Should show: "okay"

# Verify hardware - check cable connection
ethtool eth0
```

### No Network Connectivity

```bash
# Check interface configuration
ip addr show eth0

# Request DHCP address manually
sudo dhclient eth0

# Check routing
ip route show

# Test connectivity
ping -c 3 8.8.8.8      # Test basic connectivity
ping -c 3 google.com   # Test DNS resolution
```

### Force Interface Up

```bash
# Bring interface up
sudo ip link set eth0 up

# Configure static IP if DHCP fails
sudo ip addr add 192.168.1.100/24 dev eth0
sudo ip route add default via 192.168.1.1
```

## SSH Access

SSH is pre-installed and enabled in the rootfs:

```bash
# From development machine
ssh root@<board-ip>

# Default password: root
# Change after first login: passwd
```
