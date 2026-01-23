# Linux Image Build System for DE10-Nano

Complete Linux system build including kernel, rootfs, and SD card image with **SSH and Ethernet preconfigured**.

## Quick Start

### Build Complete Image

```bash
cd HPS/linux_image
sudo make all
```

This builds:
- Linux kernel with FPGA support
- Debian rootfs with SSH and Ethernet preconfigured
- Bootable SD card image

### Deploy to SD Card

```bash
cd scripts
sudo ./deploy_image.sh /dev/sdX
```

## Preconfigured Features

### SSH Server
- **Pre-installed**: `openssh-server` package
- **Pre-configured**: SSH server configured and enabled
- **Auto-start**: SSH service starts automatically on boot
- **Root login**: Enabled (for development)
- **Default password**: `root` (CHANGE AFTER FIRST BOOT)

### Ethernet (DHCP)
- **Pre-configured**: `eth0` interface configured for DHCP
- **Auto-start**: Network interface starts automatically on boot
- **Network service**: Enabled to start on boot

### Configuration Options

Edit `build_config.sh` to customize:

```bash
# Network mode: "dhcp" or "static"
export NETWORK_MODE="dhcp"

# Static IP (if NETWORK_MODE=static)
export STATIC_IP="192.168.1.100"
export STATIC_GATEWAY="192.168.1.1"
export STATIC_NETMASK="255.255.255.0"

# SSH configuration
export SSH_ENABLED="yes"
export SSH_ROOT_LOGIN="yes"
export ROOT_PASSWORD="root"  # Change after first boot!
```

## Build Components

### 1. Kernel Build

```bash
cd HPS/linux_image
make kernel
```

**Output**: `kernel/build/arch/arm/boot/zImage`

### 2. Rootfs Build

```bash
cd HPS/linux_image
sudo make rootfs
```

**Features**:
- Debian Bullseye (armhf)
- SSH server pre-installed and configured
- Ethernet pre-configured (DHCP by default)
- Network and SSH services enabled on boot
- Development tools (gcc, make, git, vim, etc.)

**Output**: `rootfs/build/rootfs.tar.gz`

### 3. SD Card Image

```bash
cd HPS/linux_image
sudo make sd-image
```

**Requirements**: Kernel and rootfs must be built first

**Output**: `build/de10-nano-custom.img`

## Directory Structure

```
linux_image/
├── kernel/          # Kernel build system
├── rootfs/          # Rootfs build system
│   ├── configs/     # Configuration templates
│   │   ├── network/ # Network configuration
│   │   └── ssh/     # SSH configuration
│   └── scripts/     # Post-install scripts
├── scripts/         # Build and deployment scripts
└── build_config.sh  # Build configuration
```

## First Boot

After flashing the SD card and booting:

1. **Connect via Ethernet**: Connect DE10-Nano to your network
2. **Wait for DHCP**: Board will automatically get IP address
3. **Find IP address**: Check your router/DHCP server for assigned IP
4. **SSH to board**:
   ```bash
   ssh root@<board-ip>
   # Default password: root
   ```
5. **Change password**:
   ```bash
   passwd
   ```

## Verification

### Check SSH Status

```bash
# On the board
systemctl status ssh
# Should show: active (running)
```

### Check Network Status

```bash
# On the board
ip addr show eth0
# Should show: IP address assigned

systemctl status networking
# Should show: active (running)
```

### Test Connectivity

```bash
# On the board
ping -c 3 8.8.8.8
ping -c 3 google.com
```

## Customization

### Custom Network Configuration

Edit `rootfs/configs/network/interfaces`:

```bash
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
```

### Custom SSH Configuration

Edit `rootfs/configs/ssh/sshd_config`:

```bash
# Disable root login
PermitRootLogin no

# Change port
Port 2222
```

## Troubleshooting

### SSH Not Working

1. **Check service status**:
   ```bash
   systemctl status ssh
   ```

2. **Check SSH keys**:
   ```bash
   ls -la /etc/ssh/ssh_host_*
   ```

3. **Restart SSH**:
   ```bash
   systemctl restart ssh
   ```

### Ethernet Not Working

1. **Check interface**:
   ```bash
   ip addr show eth0
   ```

2. **Check network service**:
   ```bash
   systemctl status networking
   ```

3. **Restart networking**:
   ```bash
   systemctl restart networking
   ifup eth0
   ```

4. **Check kernel driver**:
   ```bash
   dmesg | grep -i ethernet
   dmesg | grep -i gmac
   ```

## See Also

- [Main HPS README](../README.md)
- [Kernel Build Guide](kernel/README.md)
- [Rootfs Build Guide](rootfs/README.md)
- [Deployment Workflow](../../documentation/deployment/deployment_workflow.md)
