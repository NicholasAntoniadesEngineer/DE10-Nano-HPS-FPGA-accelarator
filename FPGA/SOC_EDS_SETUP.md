# SoC EDS Setup Guide for DE10-Nano

## What is SoC EDS?

**SoC Embedded Design Suite (SoC EDS)** is Intel's toolchain for building bootloader components (preloader, U-Boot, device tree) for Cyclone V SoC devices like the DE10-Nano.

**Important:** SoC EDS is **separate from Quartus Prime**. You need both:
- **Quartus Prime** (you have this - Quartus Lite 20.1) - for FPGA bitstream generation
- **SoC EDS** (you need to install this) - for bootloader generation

## Installation Steps

### Step 1: Download SoC EDS

1. Go to Intel's download center:
   - https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html
   - Or search for "SoC EDS" + your Quartus version

2. Download **SoC EDS** matching your Quartus version:
   - You have **Quartus Prime Lite 20.1**
   - Download: **"SoC EDS" for Quartus Prime 20.1**
   - File will be something like: `SoCEDS-20.1-*.exe` or `setup_soceds_*.exe`

### Step 2: Install on Windows

1. Run the installer (as Administrator if needed)
2. Install to a standard location like:
   - `C:\intelFPGA\20.1\embedded` (recommended)
   - Or `C:\intelFPGA_lite\20.1\embedded` (if using Lite edition)

3. Complete the installation (this may take 10-20 minutes)

### Step 3: Configure in WSL

After installation, you need to set the `SOCEDS_DEST_ROOT` environment variable in WSL.

#### Option A: Auto-detect (Recommended)

Run the helper script to find your installation:

```bash
cd /mnt/c/Users/nicka/Documents/GitHub/low-latency-market-analysis/FPGA
bash scripts/find_soceds.sh
```

This will print the exact commands you need to run.

#### Option B: Manual Setup

If you know where SoC EDS is installed, set it manually:

```bash
# Example (adjust path to match your installation):
export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
# Or if you installed to Lite directory:
# export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA_lite/20.1/embedded"

# Source the embedded command shell (sets up PATH and other variables):
source "$SOCEDS_DEST_ROOT/embedded_command_shell.sh"

# If the embedded_command_shell.sh doesn't set PATH correctly, manually add it:
export PATH="$PATH:$SOCEDS_DEST_ROOT/host_tools/altera/preloadergen"

# Verify it works:
which bsp-create-settings
# Should print: /mnt/c/intelFPGA/20.1/embedded/host_tools/altera/preloadergen/bsp-create-settings

# Note: In SoC EDS 20.1, tools are in "altera/preloadergen/" not "bin/"
```

### Step 4: Build Bootloader Components

Once `SOCEDS_DEST_ROOT` is set, build the bootloader:

```bash
cd /mnt/c/Users/nicka/Documents/GitHub/low-latency-market-analysis/FPGA

# Build preloader, U-Boot, and device tree:
make preloader uboot dtb

# Or build everything:
make everything QSYS_FILE="quartus/qsys/soc_system.qsys" QUARTUS_QPF="quartus/DE10_NANO_SoC_GHRD.qpf"
```

This will create:
- `HPS/preloader/preloader-mkpimage.bin`
- `HPS/preloader/uboot-socfpga/u-boot.img`
- `FPGA/generated/soc_system.dtb`

### Step 5: Make It Permanent (Optional)

To avoid setting `SOCEDS_DEST_ROOT` every time, add it to your `~/.bashrc`:

```bash
# Add to ~/.bashrc:
export SOCEDS_DEST_ROOT="/mnt/c/intelFPGA/20.1/embedded"
# If embedded_command_shell.sh doesn't set PATH, manually add SoC EDS tools:
export PATH="$PATH:$SOCEDS_DEST_ROOT/host_tools/altera/preloadergen"
source "$SOCEDS_DEST_ROOT/embedded_command_shell.sh" 2>/dev/null || true
```

## Alternative: Use Prebuilt Binaries

If you don't want to install SoC EDS, you can use **prebuilt bootloader binaries** from:
- Terasic's DE10-Nano CD/website
- Intel's reference designs
- Other DE10-Nano projects

Then provide them when building the SD image:

```bash
cd /mnt/c/Users/nicka/Documents/GitHub/low-latency-market-analysis/HPS/linux_image

sudo PRELOADER_BIN=/path/to/preloader-mkpimage.bin \
     UBOOT_IMG=/path/to/u-boot.img \
     make sd-image
```

## Troubleshooting

### "bsp-create-settings not found"

- Verify `SOCEDS_DEST_ROOT` is set correctly
- Check that `$SOCEDS_DEST_ROOT/host_tools/bin/bsp-create-settings` exists
- Try sourcing `embedded_command_shell.sh` manually

### "SoC EDS tools not found" during build

- Make sure you've exported `SOCEDS_DEST_ROOT` in the same shell session
- Run `cd FPGA && make check-tools` to verify detection
- Check that the path uses `/mnt/c/` (WSL format), not `C:\` (Windows format)

### Installation location not found

- Check Windows: `C:\intelFPGA\20.1\embedded\` or `C:\intelFPGA_lite\20.1\embedded\`
- In WSL, this becomes: `/mnt/c/intelFPGA/20.1/embedded/` or `/mnt/c/intelFPGA_lite/20.1/embedded/`
- Run `ls /mnt/c/intelFPGA*/20.1/embedded/embedded_command_shell.sh` to find it

## Next Steps

After SoC EDS is configured:

1. Build bootloader: `cd FPGA && make preloader uboot dtb`
2. Build complete image: `cd HPS/linux_image && sudo make fpga`
3. Create SD image: `cd HPS/linux_image && sudo make sd-image`
