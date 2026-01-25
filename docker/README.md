# Docker Build Environment for DE10-Nano

This Docker environment provides a complete, reproducible build system for the DE10-Nano FPGA + HPS project. It works on **Apple Silicon Macs** via x86 emulation.

## Prerequisites

### 1. Install Docker Desktop

Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).

### 2. Enable Rosetta Emulation (Apple Silicon Only)

For significantly better x86 emulation performance:

1. Open Docker Desktop
2. Go to **Settings** (gear icon)
3. Navigate to **Features in development** (or **General** in newer versions)
4. Enable **"Use Rosetta for x86/amd64 emulation on Apple Silicon"**
5. Click **Apply & Restart**

### 3. Allocate Sufficient Resources

1. In Docker Desktop, go to **Settings > Resources**
2. Allocate at least:
   - **CPUs**: 4+
   - **Memory**: 8GB+ (16GB recommended for Quartus)
   - **Disk**: 50GB+ (Quartus images are large)

## Quick Start

### Option 1: Using docker-compose (Recommended)

```bash
# Navigate to the docker directory
cd docker

# Build the image (first time only, takes 10-20 minutes)
docker-compose build

# Start the development container
docker-compose up -d

# Enter the container
docker-compose exec dev bash

# When done, stop the container
docker-compose down
```

### Option 2: Using docker directly

```bash
# Build the image
docker build --platform linux/amd64 -t de10-nano-dev ./docker

# Run interactively with project mounted
docker run --platform linux/amd64 -it -v $(pwd):/workspace de10-nano-dev
```

## Building Projects

### FPGA Compilation

Inside the container:

```bash
# Basic compilation
build-fpga.sh examples/fpga_examples/my_project/my_project.qpf

# With RBF generation for SD card boot
build-fpga.sh examples/fpga_examples/my_project/my_project.qpf --rbf

# Clean build
build-fpga.sh examples/fpga_examples/my_project/my_project.qpf --clean --rbf
```

Or manually:

```bash
cd /workspace/examples/fpga_examples/my_project
quartus_sh --flow compile my_project.qpf
quartus_cpf -c output_files/my_project.sof output_files/my_project.rbf
```

### HPS Cross-Compilation

```bash
# Build HPS application
build-hps.sh examples/hps_fpga_examples/DE10_NANO_SoC_GHRD/HPS_LED_update

# Clean build
build-hps.sh examples/hps_fpga_examples/DE10_NANO_SoC_GHRD/HPS_LED_update --clean
```

Or manually:

```bash
cd /workspace/examples/hps_fpga_examples/DE10_NANO_SoC_GHRD/HPS_LED_update
make CROSS_COMPILE=arm-linux-gnueabihf-
```

### Device Tree Compilation

```bash
# Compile DTS to DTB
dtc -I dts -O dtb -o soc_system.dtb soc_system.dts
```

## Available Tools

| Tool | Command | Purpose |
|------|---------|---------|
| Quartus Shell | `quartus_sh` | FPGA compilation, scripting |
| Quartus CPF | `quartus_cpf` | Convert SOF to RBF |
| Quartus PGM | `quartus_pgm` | JTAG programming (requires USB passthrough) |
| ARM GCC | `arm-linux-gnueabihf-gcc` | Cross-compile for HPS |
| Device Tree Compiler | `dtc` | Compile device trees |
| Make | `make` | Build automation |

## Performance Notes

### Apple Silicon (M1/M2/M3/M4)

- FPGA compilation runs via x86 emulation
- **Expected build time**: 30-60 minutes for typical Cyclone V projects
- Native x86 would be ~4x faster
- Rosetta emulation is significantly faster than pure QEMU

### Stability Tips

1. **Single-threaded compilation**: The docker-compose.yml sets `QUARTUS_NUM_PARALLEL_PROCESSORS=1` for stability
2. **Memory**: Ensure Docker has 8GB+ RAM allocated
3. **Disk space**: Quartus compilation uses temporary files; ensure 20GB+ free

## Troubleshooting

### "quartus_sh: command not found"

The base image may not have Quartus in PATH. Try:

```bash
export PATH=$PATH:/opt/intelFPGA_lite/18.1/quartus/bin
```

### Build hangs on Apple Silicon

This can be caused by TSO (Total Store Ordering) memory model differences. Solutions:

1. Limit to single CPU (already set in docker-compose.yml)
2. Use `taskset 1 quartus_sh ...` to pin to one core

### Out of memory during compilation

Increase Docker memory allocation in Docker Desktop settings.

### Image build fails

The `raetro/quartus` base image is large (~15GB). Ensure you have:
- Stable internet connection
- 50GB+ free disk space
- Patience (download can take 30+ minutes)

## File Locations

After building, find your outputs:

| File Type | Location |
|-----------|----------|
| SOF (JTAG bitstream) | `output_files/<project>.sof` |
| RBF (SD card bitstream) | `output_files/<project>.rbf` |
| HPS binaries | In the Makefile directory |
| Device tree blobs | Where you compiled them |

## Deploying to DE10-Nano

1. Copy `.rbf` to the boot partition of your SD card
2. Copy HPS binaries to the rootfs partition
3. Boot the DE10-Nano
4. The bootloader will load the FPGA configuration
5. Run your HPS application

## Updating the Environment

```bash
# Pull latest base image
docker pull raetro/quartus:18.1

# Rebuild
docker-compose build --no-cache
```
