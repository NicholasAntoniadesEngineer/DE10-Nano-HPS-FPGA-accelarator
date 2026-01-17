# Linux HPS Images

This guide covers the different approaches for building and deploying Linux images for the DE10-Nano's HPS.

## 1. Full Custom Debian Build
For a full-featured development environment with maximum flexibility:

### Prerequisites
- Linux development machine
- Cross-compilation toolchain for ARM
- SD card (16GB+ recommended)
- USB-to-UART cable

### Build Process
1. **Preloader & Bootloader Setup**
   - Download and install Intel SoC EDS
   - Generate preloader using BSP Editor
   - Build U-Boot bootloader
   ```bash
   make CROSS_COMPILE=arm-linux-gnueabihf- ARCH=arm
   ```

2. **Kernel Build**
   - Clone Linux kernel source
   - Apply DE10-Nano specific patches
   - Configure kernel:
   ```bash
   make ARCH=arm socfpga_defconfig
   make ARCH=arm menuconfig  # Optional: Custom configuration
   ```
   - Build kernel and modules:
   ```bash
   make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- zImage dtbs modules -j$(nproc)
   ```

3. **Root Filesystem**
   - Set up Debian base system using debootstrap
   - Add required packages and configurations
   - Configure network interfaces
   - Set up custom services

4. **Custom Kernel Modules**
   - Create module source in `drivers/` directory
   - Set up Makefile with cross-compilation support
   - Build against kernel headers
   - Install to rootfs

## 2. Yocto-Based Build
For a streamlined, production-focused build:

1. **Setup Yocto Environment**
   ```bash
   git clone -b kirkstone git://git.yoctoproject.org/poky.git
   git clone -b kirkstone git://git.yoctoproject.org/meta-intel-fpga.git
   ```

2. **Configure Build**
   ```bash
   source poky/oe-init-build-env build-de10-nano
   # Edit conf/local.conf and bblayers.conf
   ```

3. **Build Image**
   ```bash
   bitbake core-image-minimal  # or custom image recipe
   ```

## SD Card Creation

1. **Partition Layout**
   ```
   Partition 1: FAT32, 100MB (boot)
   Partition 2: ext4 (rootfs)
   ```

2. **Required Files**
   - Partition 1:
     - preloader-mkpimage.bin
     - u-boot.img
     - zImage
     - socfpga_cyclone5_de10_nano.dtb
   - Partition 2:
     - Root filesystem

3. **Flashing Process**
   ```bash
   # Flash preloader
   dd if=preloader-mkpimage.bin of=/dev/sdX3 bs=64k seek=0
   
   # Copy boot files
   cp u-boot.img zImage *.dtb /mount/boot/
   
   # Extract rootfs
   tar xf rootfs.tar.gz -C /mount/rootfs/
   ```
