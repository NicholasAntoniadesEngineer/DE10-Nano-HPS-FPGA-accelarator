# DE10-Nano Build System - Final Build Instructions

> **See Also**: [Build Hierarchy & Component Purposes](build_hierarchy.md) for detailed explanation of what gets built at each stage.

## Prebuilt Bootloader Binaries

Prebuilt bootloader binaries from the DE10-Nano System CD are included in the repository:

- **Preloader:** `HPS/preloader/preloader-mkpimage.bin` (256KB)
- **U-Boot:** `HPS/preloader/uboot-socfpga/u-boot.img` (233KB)

## Complete SD Image Build

### Step 1: Build Kernel & Rootfs (if not already built)
```bash
cd HPS/linux_image
sudo make kernel rootfs
```

### Step 2: Create Complete SD Image
```bash
cd HPS/linux_image
sudo make sd-image
```

The wrapper script automatically detects the preloader and U-Boot binaries.

**Expected Result:** `build/de10-nano-custom.img` (~4GB bootable SD image)
**Build Time:** ~2-3 minutes (after kernel/rootfs are built)

## 📋 **Final File Inventory**

Your complete DE10-Nano system will include:

```
✅ build/output_files/DE10_NANO_SoC_GHRD.rbf          # FPGA bitstream
✅ HPS/preloader/preloader-mkpimage.bin              # Preloader (prebuilt)
✅ HPS/preloader/uboot-socfpga/u-boot.img           # U-Boot (prebuilt)
✅ HPS/linux_image/kernel/build/arch/arm/boot/zImage # Linux kernel
✅ HPS/linux_image/rootfs/build/rootfs.tar.gz        # Debian rootfs
✅ HPS/linux_image/build/de10-nano-custom.img        # Complete SD image
```

## 🎯 **Deploy & Boot**

1. **Find your SD card device:**
   ```bash
   lsblk  # Look for ~4GB device like /dev/sdb
   ```

2. **Flash the image:**
   ```bash
   sudo ./scripts/deploy_image.sh /dev/sdX  # Replace /dev/sdX with your SD card
   ```

3. **Boot DE10-Nano:**
   - Insert SD card
   - Power on board
   - Wait ~30 seconds for Linux boot

4. **SSH Access:**
   ```bash
   ssh root@<board-ip>  # Password: root
   ```

5. **Test FPGA Communication:**
   ```bash
   cd /root
   ./calculator_test  # Test HPS ↔ FPGA link
   ```

## 🏆 **Achievement Unlocked!**

You now have a **complete, production-ready DE10-Nano development environment** that:

- ✅ **Compiles FPGA designs** from Quartus source
- ✅ **Builds custom Linux kernels** with FPGA drivers
- ✅ **Creates Debian root filesystems** with networking/SSH
- ✅ **Generates bootable SD card images**
- ✅ **Handles Windows/WSL compatibility**
- ✅ **Includes comprehensive error recovery**

## 🚀 **Your DE10-Nano is Ready for Development!**

**Next:** Run the SD image creation command above, then deploy and start developing FPGA-accelerated Linux applications! 🎉