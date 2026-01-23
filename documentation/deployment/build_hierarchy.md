# Build System Hierarchy & Component Purposes

## 🎯 Overview

This document outlines what gets built at each stage of the DE10-Nano build system, organized by Makefile targets and their purposes.

## 📋 Build Hierarchy

### Level 1: Main Project (`HPS/Makefile`)

#### `make everything` - Complete System Build
**Purpose**: Build FPGA bitstream, Linux kernel, Debian rootfs, and create bootable SD card image

**Components Built:**
1. **FPGA System** (calls `FPGA/Makefile`)
2. **Linux Kernel** (calls `HPS/linux_image/Makefile`)
3. **Debian Rootfs** (calls `HPS/linux_image/Makefile`)
4. **SD Card Image** (calls `HPS/linux_image/Makefile`)

---

### Level 2: FPGA Components (`FPGA/Makefile`)

#### `make everything` - Complete FPGA Build
**Purpose**: Generate all FPGA-related artifacts for HPS-FPGA communication

**Stages:**
1. **QSys Generation** - System generation from `.qsys` file
   - **Purpose**: Create Verilog/VHDL from IP cores and system configuration
   - **Output**: `FPGA/generated/` directory with IP interfaces
   - **Time**: ~10-30 seconds

2. **FPGA Bitstream Compilation** - Quartus synthesis & place/route
   - **Purpose**: Convert HDL design to programmable bitstream
   - **Input**: Quartus project (`.qpf`), QSys output
   - **Output**: `.sof` (SRAM Object File) + `.rbf` (Raw Binary File)
   - **Location**: `../build/output_files/`
   - **Time**: 5-15 minutes
   - **Tools**: Quartus Prime

3. **HPS Software Generation** - Preloader, U-Boot, Device Tree
   - **Purpose**: Create bootloader and hardware description for Linux
   - **Input**: Quartus handoff files (`.sopcinfo`)
   - **Output**: Preloader binary, U-Boot image, Device Tree Blob
   - **Time**: 2-5 minutes (if SoC EDS available)
   - **Tools**: Intel SoC EDS (bsp-create-settings)
   - **Status**: ⚠️ **Skipped** (SoC EDS compatibility issues)

4. **Test Suite Compilation** - HPS-FPGA communication tests
   - **Purpose**: Build example applications for hardware validation
   - **Input**: C/C++ source code
   - **Output**: Executables for HPS-FPGA bridge testing
   - **Location**: `HPS/applications/`
   - **Time**: ~1 minute

---

### Level 2: Linux Image Components (`HPS/linux_image/Makefile`)

#### `make linux-image` - Complete Linux System
**Purpose**: Build kernel and root filesystem, then create SD card image

**Components:**

1. **FPGA Artifact Verification** - Check existing bitstreams
   - **Purpose**: Verify FPGA bitstream availability without rebuilding
   - **Checks**: RBF file existence, freshness, and location
   - **Behavior**: Finds latest RBF, warns if outdated (>24h), logs details
   - **Locations**: `../../build/output_files/`, `FPGA/build/output_files/`
   - **Time**: ~5 seconds
   - **Fallback**: Continues build but may fail if RBF required

2. **Linux Kernel Build** - Custom kernel with FPGA drivers
   - **Purpose**: Compile Linux kernel with DE10-Nano and FPGA support
   - **Input**: Kernel source (`linux-socfpga` submodule)
   - **Output**: `zImage` (compressed kernel), `socfpga_cyclone5_de10_nano.dtb`
   - **Location**: `HPS/linux_image/kernel/build/arch/arm/boot/`
   - **Time**: 5-15 minutes
   - **Configuration**: `socfpga_defconfig` + FPGA bridge drivers

3. **Debian Root Filesystem** - Linux user environment
   - **Purpose**: Create Debian-based root filesystem with SSH/networking
   - **Input**: Debian packages, post-install scripts
   - **Output**: `rootfs.tar.gz` (compressed root filesystem)
   - **Location**: `HPS/linux_image/rootfs/build/`
   - **Time**: 10-20 minutes
   - **Features**: SSH server, FPGA device access, networking tools

4. **SD Card Image Creation** - Bootable media assembly
   - **Purpose**: Combine all components into bootable SD card image
   - **Inputs**:
     - FPGA bitstream (`.rbf`) - verified/found in step 1
     - Linux kernel (`zImage`)
     - Device tree (`.dtb`) - optional, kernel may have built-in DTB
     - Root filesystem (`rootfs.tar.gz`)
     - Preloader & U-Boot (prebuilt bootloaders from `HPS/preloader/`)
   - **Output**: `de10-nano-custom.img` (~4GB bootable image)
   - **Location**: `HPS/linux_image/build/`
   - **Time**: 2-3 minutes
   - **Process**: 
     1. Create 4GB image file
     2. Partition (100MB FAT32 boot + ext4 rootfs)
     3. Format partitions (WSL-compatible offset-based loop devices)
     4. Copy boot files (kernel, RBF, U-Boot)
     5. Extract root filesystem
     6. Flash preloader to raw boot area
   - **Scripts**: `create_sd_image_wrapper.sh` (simplified entry point), `scripts/create_sd_image.sh` (main logic)

---

## 🔄 Build Dependencies & Data Flow

```
Quartus Project (.qpf)
        ↓
    QSys Generation
        ↓
FPGA Bitstream (.rbf) ← Quartus Compilation
        ↓
    Linux Kernel
        ↓
 Debian Rootfs
        ↓
  SD Card Image ← Assembly of all components
```

## ⚠️ Component Status & Notes

### ✅ **Always Built Fresh:**
- FPGA artifact verification (checks existing RBF)
- Linux kernel compilation
- Debian root filesystem
- SD card image assembly

### 🔄 **Conditionally Built (Manual):**
- FPGA bitstream (requires Quartus: `cd FPGA && make rbf`)
- QSys generation (requires QSys: `cd FPGA && make qsys-generate`)
- HPS software (requires SoC EDS: `cd FPGA && make preloader uboot`)

### 📦 **Prebuilt/External:**
- Preloader binary (from DE10-Nano System CD)
- U-Boot image (from DE10-Nano System CD)
- Device tree blob (fallback to kernel DTB)
- FPGA bitstream (reuse existing RBF files)

## 🎯 Quick Reference

| Component | Location | Purpose | Build Time | Dependencies |
|-----------|----------|---------|------------|--------------|
| FPGA Verify | `../../build/output_files/` | Check RBF availability | ~5s | Existing RBF |
| QSys Gen | `FPGA/generated/` | IP interfaces | ~30s | QSys file |
| FPGA RBF | `../../build/output_files/` | Bitstream | 5-15min | Quartus |
| Linux Kernel | `kernel/build/` | OS core | 5-15min | Cross-compiler |
| Rootfs | `rootfs/build/` | User space | 10-20min | Debian repos |
| SD Image | `build/` | Bootable media | 2-5min | All components |

## Build Commands

```bash
# Complete system (from HPS/linux_image/)
sudo make linux-image    # Kernel + Rootfs + SD image

# Individual components (from HPS/linux_image/)
make fpga           # Verify FPGA artifacts (RBF)
make kernel         # Kernel only
sudo make rootfs    # Rootfs only (requires root)
sudo make sd-image  # SD image only (requires root)

# After SD image creation, write to SD card:
sudo dd if=build/de10-nano-custom.img of=/dev/sdX bs=4M status=progress conv=fsync
```