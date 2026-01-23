# Root Filesystem Build for DE10-Nano

This directory contains the automated rootfs build system for DE10-Nano.

## Quick Start

```bash
cd HPS/linux_image/rootfs

# On a fresh Debian/Ubuntu/WSL system, install build-host dependencies first:
make deps

# Build rootfs (requires root access)
sudo make

# Or run script directly
sudo ./build_rootfs.sh
```

## Configuration

### Environment Variables

Set these before building:

```bash
# Network mode (dhcp or static)
export NETWORK_MODE=dhcp

# Static IP configuration (if NETWORK_MODE=static)
export STATIC_IP=192.168.1.100
export STATIC_GATEWAY=192.168.1.1
export STATIC_NETMASK=255.255.255.0

# SSH configuration
export SSH_ENABLED=yes
export SSH_ROOT_LOGIN=yes
export ROOT_PASSWORD=root

# Build rootfs
sudo make rootfs
```

### Configuration Files

- `packages.txt` - List of packages to install
- `configs/network/interfaces` - Network configuration template
- `configs/ssh/sshd_config` - SSH server configuration template
- `scripts/` - Post-install scripts

## Build Process

1. **Base System**: Creates Debian base using debootstrap
2. **Packages**: Installs packages from `packages.txt`
3. **Network**: Configures Ethernet (DHCP or static)
4. **SSH**: Installs and configures SSH server
5. **Post-Install**: Runs scripts in `scripts/` directory
6. **Tarball**: Creates `build/rootfs.tar.gz`

## Output

After build:
- `build/rootfs/` - Complete rootfs directory
- `build/rootfs.tar.gz` - Rootfs tarball for SD card image

## Customization

### Add Packages

Edit `packages.txt` and add package names (one per line).

### Custom Network Config

Edit `configs/network/interfaces` or set environment variables.

### Custom SSH Config

Edit `configs/ssh/sshd_config`.

### Post-Install Scripts

Add scripts to `scripts/` directory. They will be executed in alphabetical order.

## Dependencies

Required tools (installed on build host):
- `debootstrap`
- `qemu-user-static` or `qemu-debootstrap`
- `debian-archive-keyring` (for Release signature verification)
- `ca-certificates` (for HTTPS mirrors)
- `gnupg` (provides `gpgv`)
- `wget` or `curl` (mirror preflight checks)
- Root access (for chroot operations)

Install dependencies:
```bash
sudo apt-get update
sudo apt-get install -y debootstrap qemu-user-static debian-archive-keyring ca-certificates gnupg wget
```

## Troubleshooting

### Permission Denied
- Rootfs build requires root access
- Run with: `sudo make rootfs` or `sudo ./build_rootfs.sh`

### Debootstrap Fails
- Check network connection
- Verify Debian mirror is accessible
- Default rootfs suite is Debian `stable`. If you explicitly set an older suite (e.g., `bullseye`), it may no longer be on the primary mirrors; the build script will fall back to `archive.debian.org` when needed.
- To pin to a specific suite, set `ROOTFS_VERSION` (example: `ROOTFS_VERSION=bookworm`)

### Package Installation Fails
- Check package names in `packages.txt`
- Verify packages exist for armhf architecture
- Review build output for specific errors

## Integration

The rootfs build is integrated with:
- Kernel build (for kernel modules installation)
- SD card image creation
- Unified build system
