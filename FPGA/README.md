# DE10-Nano SoC GHRD FPGA Project

Hardware Reference Design for the DE10-Nano SoC board with custom calculator IP core.

## Quick Start

**IMPORTANT BUILD WORKFLOW:**
1. **First:** Generate QSys system in Platform Designer (creates `soc_system` module)
2. **Then:** Compile in Quartus Prime (uses the generated QSys system)

```bash
# Build everything that's possible with available tools
make everything

# Or build specific components
make qsys-generate    # Generate QSys system (from .qsys source file) - MUST DO FIRST
make sof              # Build FPGA bitstream (SOF) - REQUIRES QSys generation first
make rbf              # Convert to RBF format
make preloader        # Build preloader
make uboot            # Build U-Boot
make dts dtb          # Generate device tree
make sd-fat           # Create SD card image
```

**Note:** QSys generation must be completed before Quartus compilation. The QSys system generates the `soc_system` module that the top-level design instantiates.

## QSys Files (.qsys) - Source Files

**CRITICAL:** `.qsys` files are **SOURCE FILES** (like `.v` or `.vhd` files) and are **NEVER cleaned** by `make clean` or `make scrub_clean`. They **MUST** be kept in version control.

**What gets cleaned:**
- Generated files: `generated/*/synthesis/*.qip`, `generated/*.sopcinfo` (outputs from QSys generation)
- Build artifacts: `build/`, `db/`, `*.sof`, `*.rbf`

**What does NOT get cleaned:**
- Source files: `*.qsys`, `*.v`, `*.vhd`, `*.qpf`, `*.qsf` (these are your source code)

### How QSys Files Are Created

QSys files can be created in two ways:

#### Method 1: Platform Designer GUI (Interactive)
```bash
# Launch Platform Designer
make qsys_edit

# Or directly:
qsys-edit
```
Then create your system design and save as `.qsys` file in the `quartus/qsys/` directory.

#### Method 2: TCL Script (Command-Line, No IDE Required)
```bash
# Generate .qsys file from TCL script
make qsys_generate_qsys

# This looks for create_*_qsys.tcl scripts and runs:
qsys-script --script=create_*_qsys.tcl
```

**Creating a QSys Generation Script:**
1. Create a TCL script named `create_*_qsys.tcl` (e.g., `create_system_qsys.tcl`)
2. Use QSys TCL commands to build your system programmatically
3. Run `make qsys_generate_qsys` to generate the `.qsys` file

**Example TCL script structure:**
```tcl
# Create a new QSys system
package require ::quartus::project
load_system my_system.qsys

# Add components
add_instance hps_0 altera_hps
add_instance my_custom_ip my_custom_ip

# Connect components
add_connection hps_0.h2f_axi_master my_custom_ip.s0

# Generate the system
save_system my_system.qsys
```

### QSys File Locations

The build system searches for `.qsys` files in:
1. `fpga/qsys/` directory

### QSys File Lifecycle

- **Source:** `.qsys` files are source files (never cleaned)
- **Generated:** Running `make qsys-generate` creates:
  - `generated/<system_name>/synthesis/<system_name>.qip` - Quartus IP file
  - `generated/<system_name>.sopcinfo` - System information file
  - These generated files ARE cleaned by `make clean`

### Command-Line Workflow (No IDE)

You can do everything from command-line:

```bash
# 1. Generate .qsys file from TCL script (if you have one)
make qsys_generate_qsys

# 2. Or create .qsys manually using qsys-edit (GUI) or TCL scripts

# 3. Generate QSys system (creates .qip and .sopcinfo)
#    CRITICAL: This MUST be done before Quartus compilation
make qsys-generate

# 4. Build FPGA bitstream (requires QSys generation from step 3)
make sof rbf

# 5. Build HPS software (if SoC EDS available)
make preloader uboot dts dtb sd-fat
```

**Platform Designer (QSys) GUI Workflow:**

If using Quartus GUI instead of command-line:

1. **Generate QSys System:**
   - Open Quartus Prime
   - Tools → Platform Designer (or `qsys-edit`)
   - Open `quartus/qsys/soc_system.qsys`
   - Click "Generate HDL" button (or File → Generate → Generate HDL)
   - Wait for generation to complete
   - **This creates the `soc_system` module that your top-level design needs**

2. **Compile in Quartus:**
   - Open `quartus/DE10_NANO_SoC_GHRD.qpf` in Quartus
   - Processing → Start Compilation
   - The compilation will now find the `soc_system` entity

**Important:** Always generate QSys system BEFORE compiling in Quartus. Quartus compilation will fail with "undefined entity soc_system" if QSys generation hasn't been run.

## Prerequisites

### 1. Quartus Prime (for FPGA bitstream)

**Required for:** QSys generation, FPGA compilation, SOF/RBF generation

**Installation:**
1. Download Quartus Prime from [Intel FPGA Software](https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html)
2. Install Quartus Prime (Lite Edition is sufficient)
3. Add Quartus to PATH:
   ```bash
   export PATH=$PATH:/path/to/intelFPGA/20.1/quartus/bin
   ```

**Verify installation:**
```bash
which quartus
quartus --version
```

### 2. SoC EDS (Embedded Design Suite) - **REQUIRED FOR STEP 3**

**Required for:** Preloader, U-Boot, Device Tree generation, SD card image creation

**Installation:**
1. Download SoC EDS from [Intel FPGA Software](https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html)
   - Look for "SoC Embedded Design Suite" matching your Quartus version
   - Example: `SoC EDS v20.1` for Quartus Prime 20.1
2. Extract and install:
   ```bash
   tar -xzf SoCEDS-*.tar.gz
   cd SoCEDS-*/
   ./install
   ```
3. Set environment variable:
   ```bash
   export SOCEDS_DEST_ROOT=/path/to/intelFPGA/20.1/embedded
   ```
4. Source the embedded command shell (add to `~/.bashrc`):
   ```bash
   source $SOCEDS_DEST_ROOT/env.sh
   ```
   Or add to PATH:
   ```bash
   export PATH=$PATH:$SOCEDS_DEST_ROOT/host_tools/bin
   ```

**Verify installation:**
```bash
which bsp-create-settings
which bsp-generate-files
bsp-create-settings --version
```

### 3. ARM Cross-Compiler (for HPS test suite)

**Required for:** Building HPS software test suite

**Installation (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install gcc-arm-linux-gnueabihf
```

**Verify installation:**
```bash
arm-linux-gnueabihf-gcc --version
```

## Project Structure

**Functional Organization (Consistent Grouping):**
```
FPGA/
├── fpga/                # All FPGA-related (consistent with hps/)
│   ├── hdl/            # HDL source files (top-level, intermediate)
│   ├── ip/              # IP cores (reusable components)
│   │   ├── custom/     # Custom IP (calculator)
│   │   └── vendor/     # Vendor IP (Altera/Terasic)
│   ├── qsys/            # QSys system files (Platform Designer)
│   │   └── *.qsys      # System-on-chip architecture definitions
│   └── quartus/         # Quartus project files
│       ├── *.qpf       # Quartus project file
│       └── *.qsf       # Quartus settings file
├── hps/                 # All HPS-related (software, drivers, tests)
│   ├── calculator_test/ # Test suite
│   └── integration/     # Linux integration scripts
├── generated/          # Generated files (QSys output)
├── build/              # Build artifacts
└── Makefile            # Build system
```

**Why This Structure?**

This structure uses **functional organization** for consistency:

1. **`fpga/`** - All FPGA hardware-related files grouped together
   - `hdl/` - Pure HDL source files (Verilog/VHDL modules)
   - `ip/` - IP cores (reusable components with HDL + TCL + metadata)
   - `quartus/qsys/` - Platform Designer system files (system-level integration)
   - `quartus/` - Quartus project configuration files

2. **`hps/`** - All HPS software-related files grouped together
   - `calculator_test/` - Test suite and drivers
   - `integration/` - Linux kernel integration tools

This provides clear separation between FPGA hardware design and HPS software, making the project structure more intuitive and maintainable.

## Build Targets

### Main Targets

- `make everything` - Build all components (QSys, FPGA, HPS software, test suite)
- `make all` - Build all components conditionally based on available tools
- `make clean` - Remove all build artifacts
- `make help` - Show all available targets

### FPGA Targets

**Build Order (IMPORTANT):**
1. **First:** `make qsys-generate` - Generate QSys system (creates `soc_system` module)
2. **Then:** `make sof` or compile in Quartus GUI (uses generated QSys system)

- `make qsys-generate` - Generate QSys system (**MUST run before Quartus compilation**)
- `make qsys_compile` - Compile QSys (alias for qsys-generate)
- `make sof` - Build FPGA bitstream (.sof file) - **Requires QSys generation first**
- `make rbf` - Convert SOF to RBF format (.rbf file)
- `make quartus-compile` - Full Quartus compilation - **Requires QSys generation first**

### HPS Software Targets (require SoC EDS)

- `make preloader` - Build preloader BSP
- `make uboot` - Build U-Boot bootloader
- `make dts` - Generate device tree source (.dts)
- `make dtb` - Generate device tree blob (.dtb)
- `make sd-fat` - Create SD card FAT partition image

### Fast Targets (FPGA only, no HPS)

- `make fast` - Quick FPGA build (QSys + Quartus)
- `make fast-flash` - Build and program FPGA via JTAG
- `make fast-rbf` - Build and generate RBF file

## File Discovery

The build system automatically searches for required files in multiple locations:

### QSys Files
- `fpga/qsys/` directory (priority: *top*.qsys, *main*.qsys, *soc*.qsys, *.qsys)

### Quartus Project Files
- `quartus/` directory (*.qpf)

### SoC EDS Tools
- PATH (bsp-create-settings, bsp-generate-files)
- `$SOCEDS_DEST_ROOT/host_tools/bin/`
- `$SOCEDS_DEST_ROOT/bin/`
- Recursive search in `$SOCEDS_DEST_ROOT` (Windows)

## Troubleshooting

### QSys file not found
- **.qsys files are source files** - they must be created first (see "QSys Files" section above)
- Check if QSys file exists in `quartus/qsys/` directory
- Create one using `make qsys_edit` (GUI) or `make qsys_generate_qsys` (from TCL script)
- **Note:** `.qsys` files are never cleaned - if missing, they need to be created

### "Node instance 'u0' instantiates undefined entity 'soc_system'"
- **Cause:** QSys system has not been generated yet
- **Solution:** 
  1. Generate QSys system first: `make qsys-generate` OR
  2. In Quartus GUI: Tools → Platform Designer → Open `fpga/qsys/soc_system.qsys` → Click "Generate HDL"
  3. Then compile in Quartus
- **Remember:** Always generate QSys system BEFORE compiling in Quartus

### Quartus/QSys not found
- **On Linux/WSL:** Ensure Quartus is installed and in PATH
  - Verify with `which quartus_sh` or `which quartus_sh.exe`
  - Verify QSys with `which qsys-generate` or `which qsys-generate.exe`
  - Check Quartus version compatibility
- **On WSL with Windows Quartus:** The Makefile automatically detects Windows Quartus and QSys installations in common locations:
  - Quartus: `/mnt/c/intelFPGA_lite/*/quartus/bin64/quartus_sh.exe`
  - QSys: `/mnt/c/intelFPGA_lite/*/quartus/sopc_builder/bin/qsys-generate.exe`
  - Also searches: `/mnt/c/intelFPGA/*/` and `/mnt/c/altera/*/`
  - If not auto-detected, you can manually add to PATH:
    ```bash
    export PATH=$PATH:/mnt/c/intelFPGA_lite/20.1/quartus/bin64
    ```
- **Alternative:** Use Windows Command Prompt or PowerShell instead of WSL

### SoC EDS tools not found
- Verify `SOCEDS_DEST_ROOT` is set correctly
- Check that `bsp-create-settings` is in PATH
- Source `$SOCEDS_DEST_ROOT/env.sh` or add to PATH manually
- See installation instructions above

### Cross-compiler not found
- Install ARM cross-compiler: `sudo apt-get install gcc-arm-linux-gnueabihf`
- Verify with `arm-linux-gnueabihf-gcc --version`
- Test suite build will be skipped if compiler is missing (non-fatal)

## Build Output

### FPGA Bitstream
- **SOF file:** `build/output_files/*.sof` - For JTAG programming
- **RBF file:** `build/output_files/*.rbf` - For SD card boot

### HPS Software
- **Preloader:** `hps/preloader/` directory
- **U-Boot:** `hps/preloader/uboot-socfpga/`
- **Device Tree:** `generated/*.dts` and `generated/*.dtb`
- **SD Card Image:** `sd_fat.tar.gz`

### Test Suite
- **Executable:** `hps/calculator_test/calculator_test`

## Additional Resources

- [HPS Software Documentation](hps/README.md)
- [Calculator Test Suite](hps/calculator_test/README.md)
- [Calculator IP Core](ip/custom/calculator/README.md)
- [Intel Quartus Prime Documentation](https://www.intel.com/content/www/us/en/programmable/documentation/)
