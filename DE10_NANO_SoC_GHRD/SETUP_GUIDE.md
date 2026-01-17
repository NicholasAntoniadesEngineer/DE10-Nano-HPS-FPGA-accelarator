# DE10-Nano Setup Guide - Getting the GHRD Running

This guide will walk you through getting the DE10-NANO SoC GHRD running on your board.

## Prerequisites

### Required Software

1. **Intel Quartus Prime** (Version 20.1 or compatible)
   - Download from Intel/Altera website
   - Install with Cyclone V device support
   - Includes Platform Designer (QSys)

2. **SoC Embedded Design Suite (SoC EDS)**
   - Download from Intel/Altera website (same version as Quartus)
   - Required for preloader/U-Boot generation
   - Includes cross-compilation tools

3. **Linux SD Card Image**
   - Pre-built image from Terasic or Intel
   - Or build your own using Yocto/Buildroot
   - Must support the DE10-Nano board

4. **Device Tree Compiler (dtc)**
   - Usually included with Linux distributions
   - Install with: `sudo apt-get install device-tree-compiler` (Ubuntu/Debian)

### Hardware

- DE10-Nano development board
- MicroSD card (8GB or larger, Class 10 recommended)
- USB Blaster II or compatible JTAG programmer
- USB cable for JTAG
- Ethernet cable (for network access)
- Power supply for DE10-Nano

---

## Step 1: Set Up Environment Variables

### Windows (PowerShell/CMD):
```powershell
# Set Quartus path (adjust version/path as needed)
$env:QUARTUS_ROOTDIR = "C:\intelFPGA\20.1\quartus"

# Set SoC EDS path
$env:SOCEDS_DEST_ROOT = "C:\intelFPGA\20.1\embedded"

# Add to PATH
$env:PATH = "$env:QUARTUS_ROOTDIR\bin64;$env:SOCEDS_DEST_ROOT\host_tools\bin;$env:PATH"
```

### Linux:
```bash
# Source the embedded command shell
source /path/to/intelFPGA/20.1/embedded/embedded_command_shell.sh

# Or set manually
export QUARTUS_ROOTDIR=/path/to/intelFPGA/20.1/quartus
export SOCEDS_DEST_ROOT=/path/to/intelFPGA/20.1/embedded
export PATH=$QUARTUS_ROOTDIR/bin:$SOCEDS_DEST_ROOT/host_tools/bin:$PATH
```

---

## Step 2: Build the FPGA Bitstream

### Option A: Using Makefile (Recommended)

**Important:** The Makefile is in the `FPGA/` subdirectory. You must run commands from there.

```bash
# Navigate to FPGA directory first
cd FPGA

# Generate QSys system and compile FPGA
make sof

# This will:
# 1. Generate the Platform Designer system
# 2. Compile the Quartus project
# 3. Create output_files/DE10_NANO_SoC_GHRD.sof
```

**Alternative:** Run from root directory:
```bash
make -C FPGA sof
```

### Option B: Using Quartus GUI

1. Open Quartus Prime
2. Open project: `File → Open Project → DE10_NANO_SoC_GHRD.qpf`
3. Generate QSys system first:
   - `Tools → Platform Designer` (or run `qsys-generate soc_system.qsys --synthesis=VERILOG`)
4. Compile: `Processing → Start Compilation`
5. Wait for compilation to complete (can take 30-60 minutes)

### Generate RBF File (for SD card boot)

```bash
# Make sure you're in the FPGA directory
cd FPGA
make rbf
# Creates: output_files/DE10_NANO_SoC_GHRD.rbf
```

---

## Step 3: Build Preloader and U-Boot

```bash
# Make sure you're in the FPGA directory
cd FPGA

# Build preloader BSP
make preloader

# Build U-Boot
make uboot

# This creates:
# - software/spl_bsp/preloader-mkpimage.bin
# - software/spl_bsp/uboot-socfpga/u-boot.img
```

**Note:** If you get errors about `bsp-create-settings` not found:
- Ensure SoC EDS is installed
- Set `SOCEDS_DEST_ROOT` environment variable
- Or run `./find_soceds.sh` to locate it

---

## Step 4: Generate Device Tree

```bash
# Make sure you're in the FPGA directory
cd FPGA

# Generate device tree source (.dts)
make dts

# Compile to device tree blob (.dtb)
make dtb

# Creates: soc_system.dtb
```

---

## Step 5: Prepare SD Card

### Option A: Using Pre-built SD Card Image

1. Download a pre-built Linux image for DE10-Nano from Terasic/Intel
2. Write it to SD card using `dd` (Linux) or Win32DiskImager (Windows):
   ```bash
   # Linux - BE CAREFUL: Replace /dev/sdX with your SD card device
   sudo dd if=de10-nano-image.img of=/dev/sdX bs=4M status=progress
   ```

### Option B: Update Existing SD Card

If you already have a working SD card:

```bash
cd FPGA

# Create FAT partition files
make sd-fat

# This creates: sd_fat.tar.gz containing:
# - soc_system.rbf (FPGA bitstream)
# - soc_system.dtb (device tree)
# - u-boot.scr (boot script)

# Extract to SD card FAT partition:
# 1. Mount SD card FAT partition
# 2. Extract sd_fat.tar.gz contents to FAT partition
# 3. Or manually copy:
#    - output_files/soc_system.rbf → FAT partition
#    - soc_system.dtb → FAT partition
#    - u-boot.scr → FAT partition
```

### Update Preloader and U-Boot on SD Card

```bash
cd FPGA

# Update preloader (A2 partition)
make sd-update-preloader SDCARD=/dev/sdX
# Or on Windows: make sd-update-preloader SD_DRIVE_LETTER=E

# Update U-Boot
make sd-update-uboot SDCARD=/dev/sdX
```

---

## Step 6: Program FPGA

### Option A: Program via JTAG (Temporary - Lost on Power Cycle)

```bash
cd FPGA

# Program FPGA via JTAG
make program_fpga

# Or manually:
quartus_pgm --mode=jtag --operation=p\;output_files/DE10_NANO_SoC_GHRD.sof@2
```

### Option B: Boot from SD Card (Permanent)

1. Ensure `soc_system.rbf` is on SD card FAT partition
2. Set board switches:
   - **MSEL[5:0]**: Set to `001000` (MSEL = 8) for FPGA configuration from SD card
   - Check DE10-Nano manual for exact switch positions
3. Power on board - FPGA will configure automatically from SD card

---

## Step 7: Boot Linux

1. Insert SD card into DE10-Nano
2. Connect:
   - Power supply
   - Ethernet cable (optional, for network)
   - USB-to-UART cable (for console, optional)
3. Power on the board
4. Linux should boot automatically

**Verify FPGA is configured:**
```bash
# On the board, check if FPGA is configured
cat /sys/class/fpga_manager/fpga0/state
# Should show: "operating"
```

---

## Step 8: Run LED Examples

### Option A: Basic LED Example (HPS_LED)

```bash
# On the DE10-Nano board (via SSH or serial console)

# Navigate to example directory
cd /path/to/HPS_LED

# Compile (if not already compiled)
make

# Run (requires root for /dev/mem access)
sudo ./HPS_FPGA_LED
```

### Option B: Enhanced LED Example (HPS_LED_update)

#### First-Time Setup:

```bash
cd /path/to/HPS_LED_update

# Compile
make

# Setup UIO (one-time, requires reboot)
sudo ./setup_persistent.sh

# Reboot
sudo reboot
```

#### After Reboot:

```bash
cd /path/to/HPS_LED_update

# Run the application
sudo ./hps_fpga_led_control
```

**Note:** If UIO setup doesn't work, you can manually:
```bash
# Load UIO modules
sudo modprobe uio
sudo modprobe uio_pdrv_genirq

# Check UIO device exists
ls -l /dev/uio*

# Run application
sudo ./hps_fpga_led_control
```

---

## Troubleshooting

### FPGA Not Configuring

1. **Check MSEL switches:**
   - Verify MSEL[5:0] = 001000 (MSEL = 8)
   - Refer to DE10-Nano manual for exact positions

2. **Check SD card:**
   - Ensure `soc_system.rbf` is in FAT partition root
   - Verify file is not corrupted

3. **Check FPGA manager:**
   ```bash
   cat /sys/class/fpga_manager/fpga0/state
   dmesg | grep fpga
   ```

### Preloader Build Fails

1. **Check SoC EDS installation:**
   ```bash
   which bsp-create-settings
   echo $SOCEDS_DEST_ROOT
   ```

2. **Verify handoff files exist:**
   ```bash
   ls -la FPGA/hps_isw_handoff/soc_system_hps_0/
   ```

3. **Re-run Quartus compilation** to regenerate handoff files

### Application Can't Access FPGA

1. **Check permissions:**
   ```bash
   ls -l /dev/mem
   ls -l /dev/uio*
   ```

2. **Verify FPGA is configured:**
   ```bash
   cat /sys/class/fpga_manager/fpga0/state
   ```

3. **Check memory mapping:**
   ```bash
   # For /dev/mem approach
   sudo cat /proc/iomem | grep -i fpga
   
   # For UIO approach
   cat /sys/class/uio/uio0/maps/map0/addr
   ```

### LEDs Don't Work

1. **Verify FPGA bitstream is loaded:**
   ```bash
   cat /sys/class/fpga_manager/fpga0/state
   ```

2. **Check LED addresses:**
   - Default LED PIO base: `0xFF200000` (lightweight bridge)
   - Verify in `soc_system.sopcinfo` or generated headers

3. **Test with direct register write:**
   ```bash
   # Using devmem2 (if available)
   sudo devmem2 0xFF200000 w 0x55
   ```

---

## Quick Reference

### Build Everything:
```bash
# Important: Run from FPGA directory
cd FPGA
make all  # Builds: sof, rbf, preloader, uboot, dts, dtb, sd-fat
```

### Program FPGA via JTAG:
```bash
cd FPGA
make program_fpga
```

### Update SD Card:
```bash
cd FPGA
make sd-update-preloader-uboot SDCARD=/dev/sdX
# Then copy rbf, dtb, and u-boot.scr to FAT partition
```

### Run LED Example:
```bash
cd HPS_LED_update
make
sudo ./hps_fpga_led_control
```

---

## Next Steps

Once you have the basic system running:

1. **Customize the FPGA design:**
   - Modify `soc_system.qsys` in Platform Designer
   - Add your own IP cores
   - Recompile FPGA

2. **Develop custom applications:**
   - Use the LED examples as templates
   - Access other FPGA peripherals via memory mapping
   - Implement interrupt handlers for FPGA events

3. **Explore HPS peripherals:**
   - Ethernet, USB, SD card are already configured
   - Access via standard Linux drivers

---

## Additional Resources

- **DE10-Nano User Manual** - Terasic website
- **Cyclone V Hard Processor System Technical Reference Manual** - Intel/Altera
- **Platform Designer User Guide** - Intel/Altera documentation
- **SoC EDS Getting Started Guide** - Intel/Altera documentation
