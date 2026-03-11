# HPS Drivers

User-space drivers for accessing FPGA custom IP from the DE10-Nano HPS (ARM Cortex-A9).

## How It Works

The DE10-Nano's HPS communicates with FPGA IP through the **Lightweight HPS-to-FPGA bridge**, which maps FPGA registers into the ARM physical address space starting at `0xFF200000`. Each custom IP component gets a base address offset within this 2 MB window, configured in Platform Designer (QSys).

```
ARM Virtual Memory          Physical Memory              FPGA
─────────────────          ──────────────────           ──────────────
mmap'd region    ────────► 0xFF200000 (LW bridge) ───► calculator_0    @ offset 0x0000
                           0xFF200100              ───► (next IP)       @ offset 0x0100
                           ...                          ...
                           0xFF3FFFFF (end of 2MB)
```

Each driver uses the **Linux UIO framework** (`uio_pdrv_genirq`):
1. Walks `/sys/class/uio/*/name` to find the device by its `linux,uio-name` DTS property
2. Opens `/dev/uioN` (requires root) and mmaps register window at offset 0
3. Reads/writes FPGA registers as volatile pointers
4. Waits for FPGA interrupts via blocking `read()` on the UIO fd (interrupt-driven, no polling)

No `/dev/mem`, no hardcoded physical addresses — the driver learns everything from the
DTS node via sysfs.

## Directory Structure

```
drivers/
├── README.md               # This file
├── Makefile                 # Builds all drivers
├── calculator/             # Calculator IP driver
│   ├── calculator_driver.h  # Register definitions, API
│   ├── calculator_driver.c  # UIO implementation (/dev/uioN)
│   └── Makefile
└── template/               # Template for new IP drivers
    ├── template_driver.h        # Copy and rename for your IP
    ├── template_driver.c
    └── Makefile
```

## Adding a Driver for New FPGA IP

### 1. Copy the template

```bash
cp -r template/ moving_average/
```

### 2. Rename all references

In all files, replace `template` with your IP name and `MYIP` with the uppercase version:

```bash
cd moving_average/
sed -i 's/template/moving_average/g; s/MYIP/MOVING_AVG/g' *.c *.h Makefile
mv template_driver.h moving_average_driver.h
mv template_driver.c moving_average_driver.c
```

### 3. Set the UIO device name and register addresses

In your `_driver.h`, set `MYIP_UIO_NAME` to match the `linux,uio-name` property you added to the DTS node. Also update `REG_*` offsets to match your Verilog register file:

```c
#define MOVING_AVG_UIO_NAME  "fpga-moving-average"   // must match DTS linux,uio-name
#define MA_REG_INPUT_A       0x04   // byte offset within the IP's register window
```

The physical address (`0xFF200000 + QSys offset`) belongs in the DTS `reg` property — **not** in the driver. The driver discovers the address from sysfs at runtime.

**Current address map:**

| IP Instance     | QSys Base | Physical Address | Driver Offset |
|-----------------|-----------|-----------------|---------------|
| calculator_0    | 0x0000    | 0xFF200000      | 0x00000000    |
| *(your IP)*     | 0x0100    | 0xFF200100      | 0x00000100    |

### 4. Define your register map

Update the `REG_*` constants to match your Verilog register file (`template_registers.v`). Every register offset in the driver header must correspond exactly to the localparam addresses in your Verilog.

### 5. Register the driver in the build system

Edit `HPS/drivers/Makefile` to add your new driver:

```makefile
USERSPACE_DRIVERS = calculator moving_average

moving_average:
	@echo -e "$(YELLOW)Building moving_average driver...$(NC)"
	@$(MAKE) -C moving_average CROSS_COMPILE=$(CROSS_COMPILE)
```

### 6. Link the driver into your application

In your HPS application's Makefile, link against the driver library:

```makefile
LDFLAGS += -L../../drivers/moving_average -lmoving_average
CFLAGS  += -I../../drivers/moving_average
```

Then in your application code:

```c
#include "moving_average_driver.h"

int main() {
    if (moving_average_init() != 0) return 1;

    // Write input, start operation, read result...
    moving_average_write_reg(MA_REG_INPUT_A, some_value);
    moving_average_write_reg(MA_REG_CONTROL, MA_CTRL_START | op);
    moving_average_wait_for_completion();
    uint32_t result = moving_average_read_reg(MA_REG_RESULT);

    moving_average_cleanup();
    return 0;
}
```

## Debugging

### Verify FPGA registers from the command line

Use `devmem2` (pre-installed on the rootfs) to read/write registers directly:

```bash
# Read calculator version register (should return 0x00010001)
devmem2 0xff20003c w

# Read your new IP's version register at offset 0x0100 + 0x3C = 0x013C
devmem2 0xff20013c w

# Write a value to a register
devmem2 0xff200104 w 0x3F800000   # Write 1.0 (IEEE 754) to INPUT_A
```

### Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| All reads return `0x00000000` | MSEL DIP switches wrong | Set SW10 correctly, then **power cycle** (reboot won't work) |
| All reads return `0xFFFFFFFF` | LW bridge not enabled | Check `cat /sys/class/fpga_bridge/*/state`, run `devmem2 0xff800000 w 0x19` |
| `mmap: Permission denied` | Not running as root | `/dev/uioN` requires root; use `sudo` or a systemd service |
| UIO device not found (`/sys/class/uio/` empty) | `uio_pdrv_genirq.of_id=generic-uio` missing from kernel bootargs | Verify `cat /proc/cmdline` contains the parameter; check `create_sd_image.sh` |
| Version reads OK but operation hangs | Start bit not being set | Verify CONTROL register write includes bit 31 (`0x80000001` for op 1) |
| Result is stale/wrong | Register offset mismatch | Compare driver `REG_*` offsets with Verilog `localparam` addresses |

### Register dump

To dump all registers for an IP at offset 0x0000:

```bash
for i in $(seq 0 4 60); do
    addr=$(printf "0xff2000%02x" $i)
    echo -n "[$addr] = "
    devmem2 $addr w 2>/dev/null | tail -1
done
```

## Cross-Compilation

All drivers are cross-compiled for ARM using the `arm-linux-gnueabihf-` toolchain (provided by the Docker build environment). The toolchain prefix can be overridden:

```bash
make CROSS_COMPILE=arm-linux-gnueabihf-
```

The Docker build (`docker/scripts/docker-build.sh`) handles this automatically — drivers are built before the rootfs so binaries are included in the SD card image.
