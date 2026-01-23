# Development Workflow and Build Troubleshooting

This guide covers the complete development workflow for the DE10-Nano, including detailed build sequences, environment setup, and comprehensive troubleshooting for common issues.

## Prerequisites

### Required Software
- **Quartus Prime Lite 20.1** - FPGA development tools
- **Intel SoC EDS 20.1** - HPS bootloader tools
- **Cross-compilation toolchain** - ARM GCC for Linux kernel
- **WSL2 (Windows) or Linux environment**

### Hardware Requirements
- DE10-Nano development board
- MicroSD card (16GB+ recommended)
- USB-to-UART cable for debugging

## Environment Setup

### Step 1: Install Quartus Prime Lite 20.1
1. Download from Intel website
2. Install to `C:\intelFPGA\20.1\`
3. Verify installation: `quartus --version`

### Step 2: Install SoC EDS 20.1
1. Download Intel SoC Embedded Design Suite 20.1
2. Install to `C:\intelFPGA\20.1\embedded\`
3. Note: Requires ARM DS-5 license (free community edition available)

### Step 3: Set Environment Variables
```bash
# In WSL terminal
export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
export PATH="$PATH:$SOCEDS_DEST_ROOT/host_tools/bin:$SOCEDS_DEST_ROOT/bin"

# Make permanent (optional)
echo 'export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"' >> ~/.bashrc
echo 'export PATH="$PATH:$SOCEDS_DEST_ROOT/host_tools/bin:$SOCEDS_DEST_ROOT/bin"' >> ~/.bashrc
```

### Step 4: Verify Tools
```bash
# Test Quartus
which quartus

# Test SoC EDS tools
which bsp-create-settings
which bsp-generate-files
```

## Complete Build Sequence

### Step 1: Build FPGA Bitstream
```bash
cd FPGA
make sof rbf
```
**Expected output:** `../build/output_files/DE10_NANO_SoC_GHRD.rbf`

### Step 2: Build Bootloader Components
```bash
make preloader uboot dtb
```
**Expected outputs:**
- `HPS/preloader/preloader-mkpimage.bin`
- `HPS/preloader/uboot-socfpga/u-boot.img`
- `generated/soc_system.dtb`

### Step 3: Build Linux Kernel & Rootfs
```bash
cd ../HPS/linux_image
sudo make kernel rootfs
```
**Expected outputs:**
- `kernel/build/arch/arm/boot/zImage`
- `rootfs/build/rootfs.tar.gz`

### Step 4: Create Complete SD Image
```bash
sudo make sd-image
```
**Expected output:** `build/de10-nano-custom.img` (~4GB)

### Step 5: Deploy to SD Card
```bash
sudo ./scripts/deploy_image.sh /dev/sdX
```

## Development Cycle

### Application Development
1. **Set up cross-compilation:**
   ```bash
   export CROSS_COMPILE=arm-linux-gnueabihf-
   export ARCH=arm
   ```

2. **Build and deploy:**
   ```bash
   make  # Cross-compile for ARM
   scp myapp root@de10-nano:/usr/local/bin/
   ```

3. **Test on device:**
   ```bash
   ssh root@de10-nano
   ./myapp
   ```

### FPGA-HPS Communication Development
1. **Build FPGA bitstream first**
2. **Build HPS application:**
   ```bash
   cd HPS/applications/calculator_test
   make
   scp calculator_test root@de10-nano:/root/
   ```

3. **Test communication:**
   ```bash
   ssh root@de10-nano "./calculator_test"
   ```

## Comprehensive Troubleshooting

### SoC EDS Tool Issues

#### Problem: "bsp-create-settings not found"
**Symptoms:** Build fails with "SoC EDS tools not found"

**Solutions:**
1. **Check installation:**
   ```bash
   ls -la /mnt/c/intelFPGA/20.1/embedded/host_tools/bin/bsp-create-settings*
   ```

2. **Manual PATH setup:**
   ```bash
   export PATH="$PATH:/mnt/c/intelFPGA/20.1/embedded/host_tools/bin"
   export PATH="$PATH:/mnt/c/intelFPGA/20.1/embedded/bin"
   ```

3. **Source embedded command shell:**
   ```bash
   export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
   source "$SOCEDS_DEST_ROOT/embedded_command_shell.sh"
   ```

#### Problem: "env.sh not found"
**Cause:** embedded_command_shell.sh script issues
**Solution:** Use manual PATH setup above

#### Problem: Python XML Compatibility (SoC EDS 20.1 Bug)
**Symptoms:** Preloader generation fails with XML parsing errors
**Cause:** SoC EDS 20.1 has Python 2/3 XML compatibility issues

**Solution:** Use prebuilt bootloader binaries instead:
```bash
# Get prebuilt binaries from Terasic DE10-Nano System CD
# or Intel FPGA forums

# Then use them in the build:
sudo PRELOADER_BIN=/path/to/preloader-mkpimage.bin \
     UBOOT_IMG=/path/to/u-boot.img \
     make sd-image
```

### Build System Issues

#### Problem: CRLF Line Endings in Shell Scripts
**Symptoms:** `$'\r': command not found` or `syntax error near unexpected token`

**Cause:** Shell scripts edited in Windows have CRLF line endings

**Solution:** The Makefile now auto-normalizes scripts:
```makefile
tmp_script="$(QSYS_DIR)/.qsys_check_normalized.$$$$"; \
tr -d '\r' < "$(QSYS_CHECK_SCRIPT)" > "$$tmp_script"; \
chmod +x "$$tmp_script"; \
bash "$$tmp_script" ...; \
rm -f "$$tmp_script"
```

**Prevention:**
- Use `.gitattributes` to enforce LF endings: `*.sh text eol=lf`
- Edit scripts in WSL/Linux, not Windows editors

#### Problem: Preloader Path Incorrect
**Symptoms:** `bsp-create-settings` can't find handoff files

**Cause:** Wrong path to `hps_isw_handoff` directory

**Solution:** Correct path in Makefile:
```makefile
# Fixed path:
--preloader-settings-dir "quartus/hps_isw_handoff/soc_system_hps_0"
```

#### Problem: License errors during preloader build
**Cause:** ARM DS-5 license required for SoC EDS
**Solutions:**
1. Get free Community Edition license
2. Use 30-day evaluation license
3. Skip SoC EDS and provide prebuilt bootloaders

#### Problem: Build fails with disk space errors
**Solution:** Ensure 10GB+ free space, check with `df -h`

#### Problem: Makefile targets fail
**Check:**
```bash
make check-tools  # Verify environment setup
```

### FPGA Build Issues

#### Problem: Quartus not found
**Solution:**
```bash
export PATH="$PATH:/mnt/c/intelFPGA/20.1/quartus/bin"
which quartus
```

#### Problem: FPGA synthesis fails
**Check:** Project files integrity, Quartus version compatibility

### Linux Image Issues

#### Problem: Kernel build fails
**Check:** Cross-compiler installation, kernel source integrity

#### Problem: Rootfs creation fails
**Check:** Network connectivity, package repository access

### SD Card Issues

#### Problem: SD card not bootable
**Check:**
- Correct partition layout (FAT32 boot + ext4 root)
- All required files present:
  - `preloader-mkpimage.bin`
  - `u-boot.img`
  - `zImage`
  - `soc_system.dtb`
  - Root filesystem

### Deployment and Testing

#### Problem: Board doesn't boot
**Debug steps:**
1. Connect UART cable (115200 baud)
2. Check power supply
3. Verify SD card corruption
4. Check boot logs via UART

#### Problem: Network connectivity issues
**Check:**
- Ethernet cable connection
- IP address assignment: `ip addr show`
- SSH service: `systemctl status ssh`

#### Problem: FPGA-HPS communication fails
**Check:**
1. FPGA bitstream loaded: `cat /sys/class/fpga_bridge/*/state`
2. UIO device available: `ls /dev/uio*`
3. Application permissions: Run as root

### Recovery Options

#### Option 1: Skip SoC EDS (Use Prebuilt Bootloaders)
**Best for SoC EDS issues:**

1. **Locate prebuilt binaries:**
   - Terasic DE10-Nano System CD
   - Intel FPGA forum downloads
   - GitHub DE10-Nano repositories

2. **Copy to repository:**
   ```bash
   cp preloader-mkpimage.bin HPS/preloader/
   cp u-boot.img HPS/preloader/uboot-socfpga/
   ```

3. **Build with prebuilt binaries:**
   ```bash
   cd HPS/linux_image
   sudo PRELOADER_BIN=HPS/preloader/preloader-mkpimage.bin \
        UBOOT_IMG=HPS/preloader/uboot-socfpga/u-boot.img \
        make sd-image
   ```

#### Option 2: Alternative Build Methods
- Use Yocto Project for streamlined builds
- Use pre-built images with custom applications
- Cross-compile applications separately

#### Option 3: Clean Rebuild
**For persistent build issues:**
```bash
cd HPS/linux_image
sudo make clean
sudo make kernel rootfs sd-image
```

## Verification Checklist

After each build step, verify:

### FPGA Build
```bash
ls -la build/output_files/DE10_NANO_SoC_GHRD.rbf
```

### Bootloader Build
```bash
ls -la HPS/preloader/preloader-mkpimage.bin
ls -la HPS/preloader/uboot-socfpga/u-boot.img
ls -la FPGA/generated/soc_system.dtb
```

### Linux Build
```bash
ls -la HPS/linux_image/kernel/build/arch/arm/boot/zImage
ls -la HPS/linux_image/rootfs/build/rootfs.tar.gz
```

### Complete Image
```bash
ls -la HPS/linux_image/build/de10-nano-custom.img
```

## Success Indicators

✅ **Environment:** `which bsp-create-settings` finds tool
✅ **FPGA:** RBF file created successfully
✅ **Bootloader:** Preloader and U-Boot built without errors
✅ **Linux:** Kernel and rootfs created
✅ **SD Image:** Complete bootable image ready
✅ **Board:** Boots successfully, SSH accessible
✅ **Communication:** FPGA-HPS communication tested

## Next Steps After Successful Build

1. **Flash SD card and boot board**
2. **Configure network settings**
3. **Test FPGA-HPS communication**
4. **Deploy custom applications**
5. **Begin application development**
