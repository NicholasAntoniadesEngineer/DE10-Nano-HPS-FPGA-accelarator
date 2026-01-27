# Docker Build Environment for DE10-Nano

Fully automated build system for DE10-Nano FPGA + HPS development. Runs on **Apple Silicon Macs** via Rosetta 2.

## Fresh Setup (2 Steps)

### Step 1: Prerequisites (5 minutes)

1. **Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)**

2. **Enable Rosetta** (Apple Silicon only):
   - Docker Desktop → Settings → Features in development
   - Enable **"Use Rosetta for x86/amd64 emulation"**
   - Apply & Restart

3. **Allocate Resources**:
   - Docker Desktop → Settings → Resources
   - CPUs: **14** | Memory: **16GB** | Disk: **50GB+**

### Step 2: Build Everything (~60 min first time)

```bash
cd docker

# One-time setup (builds Docker image, ~10-20 min)
./scripts/setup.sh

# Build complete system (FPGA + Linux + Apps)
./scripts/docker-build.sh

# Done! SD card image ready in: ../output/
```

The build is fully automated and produces a bootable SD card image with:
- FPGA bitstream (.rbf)
- U-Boot bootloader
- Linux kernel (zImage)
- Root filesystem
- Device tree
- Applications

## Build Scripts

All scripts run from your **host machine** (no need to enter container):

### Build Everything
```bash
./scripts/docker-build.sh              # Complete system (~60 min first time)
```

### Build Specific Components
```bash
./scripts/docker-build.sh fpga         # FPGA bitstream only (~30-40 min)
./scripts/docker-build.sh kernel       # Linux kernel (~10-15 min)
./scripts/docker-build.sh applications # HPS apps (<1 min)
```

### Clean
```bash
./scripts/docker-clean.sh              # Clean artifacts (keeps downloads)
./scripts/docker-clean.sh --all        # Deep clean (removes kernel source)
```



