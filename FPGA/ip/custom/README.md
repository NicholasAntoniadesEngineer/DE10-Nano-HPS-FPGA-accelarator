# Custom IP Directory

This directory contains custom Platform Designer (QSys) IP components that connect to the HPS via the Lightweight HPS-to-FPGA bridge (base address `0xFF200000`).

## Directory Structure

```
ip/custom/
├── README.md                          # This file
├── template/                          # Template — copy this to start a new IP
│   ├── template_hw.tcl                    # Platform Designer component definition
│   ├── template.v                         # Top-level wrapper
│   ├── template_avalon_mm.v              # Avalon-MM slave interface
│   ├── template_registers.v              # Register file
│   └── template_core.v                   # Core logic placeholder
├── calculator/                        # Calculator IP (working example)
│   ├── calculator_hw.tcl
│   ├── calculator.v
│   ├── calculator_avalon_mm.v
│   ├── calculator_registers.v
│   ├── calculator_core.v
│   ├── calculator_float_ops.v
│   ├── calculator_led_display.v
│   ├── calculator_price_buffer.v
│   └── calculator_hft_ops.v
└── moving_average/                    # Example: your new IP would go here
    ├── moving_average_hw.tcl
    ├── moving_average.v
    └── ...
```

## Auto-Discovery

The build system **automatically discovers** all custom IP directories. Any subdirectory under `ip/custom/` that contains a `_hw.tcl` file is picked up — no Makefile edits needed.

The `template/` directory is explicitly excluded from discovery so it does not interfere with QSys generation.

How it works:
- `mk/qsys.mk` uses `$(wildcard ip/custom/*/_hw.tcl)` to find all IPs
- The discovered paths are passed to `qsys_check.sh` as space-separated directories
- `qsys_check.sh` builds the `--search-path` argument (comma-separated) for `qsys-generate`
- After generation, all custom IP source files are overlaid onto `generated/` submodules

This means: **just create your IP directory with a `_hw.tcl` file and it will be found automatically.**

## Quick Start: Adding a New IP

### Option A: Automated (recommended)

Run the scaffold script from the project root:

```bash
./scripts/new_ip.sh moving_average
```

This single command:
1. Copies and renames all FPGA template files (`ip/custom/moving_average/`)
2. Copies and renames the HPS driver template (`HPS/drivers/moving_average/`)
3. Patches `soc_system.qsys` with the module, connections, and auto-assigned base address + IRQ
4. Sets the driver header's base offset to match QSys

After running, review what changed:

```bash
git diff                                          # See all changes
git diff FPGA/quartus/qsys/soc_system.qsys       # QSys XML specifically
```

Then implement your logic in `FPGA/ip/custom/moving_average/moving_average_core.v`.

**Options:**

| Flag | Effect |
|------|--------|
| `--no-qsys` | Skip QSys XML patching (use if you prefer the GUI or manual XML) |
| `--no-driver` | Skip HPS driver creation |
| `--help` | Show usage |

### Option B: Manual (step-by-step)

If you prefer full control, follow the steps below.

### Step 1: Copy the template

```bash
cd FPGA/ip/custom/
cp -r template/ moving_average/
cd moving_average/
```

Rename all files and internal references from `template` to your IP name:

```bash
for f in template*; do mv "$f" "${f/template/moving_average}"; done
sed -i 's/template/moving_average/g; s/MYIP/MOVING_AVG/g' *.v *.tcl
```

The template includes:
- **`template.v`** — Top-level wrapper wiring Avalon-MM, registers, and core
- **`template_avalon_mm.v`** — Bus interface (usually unchanged)
- **`template_registers.v`** — Register file with control/status/result pattern
- **`template_core.v`** — Placeholder computation (replace with your logic)
- **`template_hw.tcl`** — Platform Designer component definition

### Step 2: Implement your core logic

Edit `moving_average_core.v` — replace the placeholder pass-through with your actual computation. The register file and Avalon-MM interface handle bus communication; your core just needs to respond to `start`, drive `result`, and signal `done`.

### Step 3: Add to Platform Designer (QSys)

#### With GUI (Quartus on Windows/Linux)

1. Run `make qsys_edit` to open Platform Designer
2. Your IP appears in the IP Catalog under its `DISPLAY_NAME`
3. Add an instance (e.g., `moving_average_0`)
4. Connect the four required interfaces:
   - **Clock**: `clk_0.clk` → `moving_average_0.clock`
   - **Reset**: `hps_0.h2f_reset` → `moving_average_0.reset`
   - **Avalon-MM**: `hps_0.h2f_lw_axi_master` → `moving_average_0.s0`
   - **Interrupt** (optional): `hps_0.f2h_irq0` → `moving_average_0.irq`
5. Assign a base address that doesn't overlap with existing IPs
6. Export any conduit interfaces (LEDs, GPIO, etc.)
7. Save and generate

#### Without GUI (Docker / command-line only)

Edit `quartus/qsys/soc_system.qsys` XML directly:

**1. Add the module instance** (after the existing `calculator_0` module):

```xml
<module name="moving_average_0" kind="moving_average" version="1.0" enabled="1">
  <parameter name="AUTO_CLOCK_CLOCK_RATE" value="50000000" />
</module>
```

**2. Add the four connections** (in the `<connection>` section):

```xml
<connection kind="clock" version="20.1"
  start="clk_0.clk"
  end="moving_average_0.clock" />

<connection kind="reset" version="20.1"
  start="hps_0.h2f_reset"
  end="moving_average_0.reset" />

<connection kind="avalon" version="20.1"
  start="hps_0.h2f_lw_axi_master"
  end="moving_average_0.s0">
  <parameter name="baseAddress" value="0x0100" />
</connection>

<connection kind="interrupt" version="20.1"
  start="hps_0.f2h_irq0"
  end="moving_average_0.irq">
  <parameter name="irqNumber" value="1" />
</connection>
```

**3. Export conduits** (optional — only if your IP has conduit interfaces):

Add an `<interface>` in the `<module name="$system">` section at the top:

```xml
<interface name="moving_average_0_output" internal="moving_average_0.output_conduit" />
```

**Connection rules:**
- Reset source must be `hps_0.h2f_reset` (not `clk_0.clk_in_reset`)
- Interrupt: `start` = receiver (HPS), `end` = sender (your IP) — counterintuitive
- Base address must not overlap existing IPs (see address map below)
- IRQ number must be unique per `f2h_irq0` (calculator uses 0, so use 1+)

### Step 4: Wire conduit exports in top-level HDL (if any)

**When do you need to edit `hdl/DE10_NANO_SoC_GHRD.v`?**

Only if your IP has **conduit exports** — signals that leave the QSys interconnect and connect to physical FPGA pins (LEDs, GPIO, external interfaces). The other four interface types are handled entirely inside QSys:

| Interface Type | Needs HDL wiring? | Example |
|---------------|-------------------|---------|
| Clock | No | Internal to QSys interconnect |
| Reset | No | Internal to QSys interconnect |
| Avalon-MM | No | Internal to QSys interconnect |
| Interrupt | No | Internal to QSys interconnect |
| **Conduit** | **Yes** | LEDs, GPIO, external I/O |

If your IP only uses Avalon-MM + interrupt (no conduit exports), **no HDL changes are needed**.

**How to find the exact port names:**

After QSys generation (`make qsys-generate`), open `generated/soc_system/synthesis/soc_system.v` and search for your instance name. The generated top-level module will have ports for every exported conduit. The naming convention is:

```
.<instance>_<interface>_<signal>(<fpga_pin>)
```

For example, the calculator IP exports an LED conduit. In `soc_system.v` you'll find a port like:

```verilog
.calculator_0_led_output_export    // <instance>_<interface>_<signal>
```

And in `hdl/DE10_NANO_SoC_GHRD.v` (line 197), it's wired to the physical LED pins:

```verilog
.calculator_0_led_output_export(LED)
```

**Step-by-step for a new IP with conduit exports:**

1. Add and connect your IP in QSys (Step 3), including exporting the conduit interface
2. Run `make qsys-generate` to regenerate the system
3. Open `generated/soc_system/synthesis/soc_system.v` and find your new exported port(s)
4. Add matching port connections in the `soc_system u0` instantiation block in `hdl/DE10_NANO_SoC_GHRD.v`
5. If the signal connects to a physical pin (LED, GPIO), ensure the pin is declared in the module's port list and constrained in the `.qsf` pin assignment file

**Example — adding a `moving_average` IP with a `result_valid` output conduit:**

In `hdl/DE10_NANO_SoC_GHRD.v`, add to the `soc_system u0` instantiation:

```verilog
.moving_average_0_result_valid_export(SOME_GPIO_PIN)
```

Where `SOME_GPIO_PIN` is declared in the module port list and assigned to a physical FPGA pin.

**Example — IP with no conduit exports (pure register-based):**

If your IP communicates only via Avalon-MM registers and optionally an interrupt, no changes to `DE10_NANO_SoC_GHRD.v` are needed at all. The HPS accesses your IP entirely through memory-mapped reads/writes.

### Step 5: Write the HPS driver

Copy the driver template and rename:

```bash
cd HPS/drivers/
cp -r template/ moving_average/
cd moving_average/
for f in template*; do mv "$f" "${f/template/moving_average}"; done
sed -i 's/template/moving_average/g; s/MYIP/MOVING_AVG/g' *.c *.h Makefile
```

Update `MOVING_AVG_BASE_OFFSET` in the header to match the QSys base address, and update `REG_*` offsets to match your Verilog register map.

See `HPS/drivers/README.md` for full driver integration details.

### Step 6: Build and test

```bash
# Docker build (full end-to-end):
cd docker && ./scripts/docker-build.sh

# Or incremental:
cd FPGA && make qsys-generate   # Regenerate QSys (auto-discovers new IP)
cd FPGA && make sof rbf          # Compile FPGA bitstream
```

## Address Map

Keep this table updated as you add IPs to avoid collisions:

| IP Instance     | Base Address | Size    | Address Range         |
|-----------------|-------------|---------|----------------------|
| calculator_0    | 0x0000      | 64 B    | 0x0000 – 0x003F     |
| *(next IP)*     | 0x0100      | —       | 0x0100 – ...         |

All addresses are offsets within the Lightweight HPS-to-FPGA bridge (`0xFF200000`).

## Important `_hw.tcl` Settings

| Setting | Value | Meaning |
|---------|-------|---------|
| `readLatency` | `1` | Registered reads (data valid 1 cycle after read). Use `0` for combinational. |
| `addressUnits` | `WORDS` | Each address increment = one 32-bit register. `SYMBOLS` = per byte. |
| `readWaitTime` | `0` | No wait states on read. |
| `writeWaitTime` | `0` | No wait states on write. |

**The `readLatency` in `_hw.tcl` MUST match your Verilog.** If your register read uses `always @(posedge clk)` (registered mux), use `readLatency 1`. If it uses `assign` (combinational), use `readLatency 0`. A mismatch causes reads to return stale or incorrect data.

## Physical Pin Reference (DE10-Nano)

When your IP has conduit exports, you need to connect them to physical FPGA pins. Four files must agree for any physical pin connection:

```
_hw.tcl                  → declares the conduit interface (port width, direction)
soc_system.qsys          → exports the conduit (creates a top-level port on soc_system)
DE10_NANO_SoC_GHRD.v     → wires the QSys port to the physical FPGA pin signal
DE10_NANO_SoC_GHRD.qsf   → maps the signal name to a physical ball/pin location
```

### Available FPGA-side I/O

These are the user-accessible I/O resources already declared in the QSF and top-level HDL:

| Signal | Width | Direction | Pins | Current Status |
|--------|-------|-----------|------|----------------|
| `LED[7:0]` | 8 | output | W15, AA24, V16, V15, AF26, AE26, Y16, AA23 | Used by `calculator_0` conduit |
| `KEY[1:0]` | 2 | input | AH17, AH16 | Unused (available) |
| `SW[3:0]` | 4 | input | Y24, W24, W21, W20 | Unused (available) |
| `FPGA_CLK2_50` | 1 | input | Y13 | Unused spare clock |
| `FPGA_CLK3_50` | 1 | input | E11 | Unused spare clock |

All `HPS_*` pins are consumed by the HPS block — do not use them for custom IP.

### Scenario 1: Using an unused pin (KEY or SW)

`KEY` and `SW` already have pin assignments in the `.qsf` and port declarations in the top-level HDL. To use them:

1. **`_hw.tcl`** — uncomment and define the conduit:
   ```tcl
   add_interface input_conduit conduit end
   set_interface_property input_conduit associatedClock clock
   set_interface_property input_conduit associatedReset reset
   set_interface_property input_conduit ENABLED true
   add_interface_port input_conduit coe_switches_export export Input 4
   ```

2. **`soc_system.qsys`** — export the conduit (GUI does this automatically, or add to XML):
   ```xml
   <interface name="moving_average_0_input" internal="moving_average_0.input_conduit" type="conduit" dir="end" />
   ```

3. **`DE10_NANO_SoC_GHRD.v`** — wire the port and remove from tie-off:
   ```verilog
   // In the soc_system u0 instantiation:
   .moving_average_0_input_export(SW)

   // Update the tie-off line (remove SW):
   wire _unused_ok = &{1'b0, KEY, FPGA_CLK2_50, FPGA_CLK3_50};
   ```

4. **`.qsf`** — no changes needed (KEY/SW pins already assigned)

### Scenario 2: Sharing an existing pin (LED splitting)

The `LED[7:0]` bus is currently fully assigned to the calculator's conduit. To share it:

1. Change the calculator's conduit width (e.g., 4 bits for `LED[3:0]`)
2. Add a new conduit on your IP for `LED[7:4]`
3. Wire them separately in the top-level HDL:
   ```verilog
   .calculator_0_led_output_export(LED[3:0])
   .moving_average_0_led_output_export(LED[7:4])
   ```

### Scenario 3: Adding a new GPIO header pin

The DE10-Nano has three FPGA-fabric GPIO expansion headers with pins **not yet declared** in this project. These connect directly to the Cyclone V FPGA (not to the HPS) and are freely available for custom IP conduit exports.

To use a GPIO header pin:

1. Pick a pin from the tables below
2. Add to `DE10_NANO_SoC_GHRD.v` module port list:
   ```verilog
   output MY_GPIO_PIN
   ```
3. Add pin assignment to `DE10_NANO_SoC_GHRD.qsf`:
   ```tcl
   set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to MY_GPIO_PIN
   set_location_assignment PIN_V12 -to MY_GPIO_PIN
   ```
4. Wire the conduit export to the new pin in the `soc_system u0` instantiation
5. All DE10-Nano user I/O uses **3.3-V LVTTL** — use this IO_STANDARD unless you know otherwise

#### GPIO0 Header (JP1) — 36 pins

| Signal | FPGA Pin | Signal | FPGA Pin |
|--------|----------|--------|----------|
| `GPIO_0[0]` | PIN_V12 | `GPIO_0[1]` | PIN_E8 |
| `GPIO_0[2]` | PIN_W12 | `GPIO_0[3]` | PIN_D11 |
| `GPIO_0[4]` | PIN_D8 | `GPIO_0[5]` | PIN_AH13 |
| `GPIO_0[6]` | PIN_AF7 | `GPIO_0[7]` | PIN_AH14 |
| `GPIO_0[8]` | PIN_AF4 | `GPIO_0[9]` | PIN_AH3 |
| `GPIO_0[10]` | PIN_AD5 | `GPIO_0[11]` | PIN_AG14 |
| `GPIO_0[12]` | PIN_AE23 | `GPIO_0[13]` | PIN_AE6 |
| `GPIO_0[14]` | PIN_AD23 | `GPIO_0[15]` | PIN_AE24 |
| `GPIO_0[16]` | PIN_D12 | `GPIO_0[17]` | PIN_AD20 |
| `GPIO_0[18]` | PIN_C12 | `GPIO_0[19]` | PIN_AD17 |
| `GPIO_0[20]` | PIN_AC23 | `GPIO_0[21]` | PIN_AC22 |
| `GPIO_0[22]` | PIN_Y19 | `GPIO_0[23]` | PIN_AB23 |
| `GPIO_0[24]` | PIN_AA19 | `GPIO_0[25]` | PIN_W11 |
| `GPIO_0[26]` | PIN_AA18 | `GPIO_0[27]` | PIN_W14 |
| `GPIO_0[28]` | PIN_Y18 | `GPIO_0[29]` | PIN_Y17 |
| `GPIO_0[30]` | PIN_AB25 | `GPIO_0[31]` | PIN_AB26 |
| `GPIO_0[32]` | PIN_Y11 | `GPIO_0[33]` | PIN_AA26 |
| `GPIO_0[34]` | PIN_AA13 | `GPIO_0[35]` | PIN_AA11 |

#### GPIO1 Header (JP7) — 36 pins

| Signal | FPGA Pin | Signal | FPGA Pin |
|--------|----------|--------|----------|
| `GPIO_1[0]` | PIN_Y15 | `GPIO_1[1]` | PIN_AC24 |
| `GPIO_1[2]` | PIN_AA15 | `GPIO_1[3]` | PIN_AD26 |
| `GPIO_1[4]` | PIN_AG28 | `GPIO_1[5]` | PIN_AF28 |
| `GPIO_1[6]` | PIN_AE25 | `GPIO_1[7]` | PIN_AF27 |
| `GPIO_1[8]` | PIN_AG26 | `GPIO_1[9]` | PIN_AH27 |
| `GPIO_1[10]` | PIN_AG25 | `GPIO_1[11]` | PIN_AH26 |
| `GPIO_1[12]` | PIN_AH24 | `GPIO_1[13]` | PIN_AF25 |
| `GPIO_1[14]` | PIN_AG23 | `GPIO_1[15]` | PIN_AF23 |
| `GPIO_1[16]` | PIN_AG24 | `GPIO_1[17]` | PIN_AH22 |
| `GPIO_1[18]` | PIN_AH21 | `GPIO_1[19]` | PIN_AG21 |
| `GPIO_1[20]` | PIN_AH23 | `GPIO_1[21]` | PIN_AA20 |
| `GPIO_1[22]` | PIN_AF22 | `GPIO_1[23]` | PIN_AE22 |
| `GPIO_1[24]` | PIN_AG20 | `GPIO_1[25]` | PIN_AF21 |
| `GPIO_1[26]` | PIN_AG19 | `GPIO_1[27]` | PIN_AH19 |
| `GPIO_1[28]` | PIN_AG18 | `GPIO_1[29]` | PIN_AH18 |
| `GPIO_1[30]` | PIN_AF18 | `GPIO_1[31]` | PIN_AF20 |
| `GPIO_1[32]` | PIN_AG15 | `GPIO_1[33]` | PIN_AE20 |
| `GPIO_1[34]` | PIN_AE19 | `GPIO_1[35]` | PIN_AE17 |

#### Arduino Header — 16 GPIO + 1 reset

| Signal | FPGA Pin | Arduino Function |
|--------|----------|-----------------|
| `ARDUINO_IO[0]` | PIN_AG13 | RXD |
| `ARDUINO_IO[1]` | PIN_AF13 | TXD |
| `ARDUINO_IO[2]` | PIN_AG10 | — |
| `ARDUINO_IO[3]` | PIN_AG9 | — |
| `ARDUINO_IO[4]` | PIN_U14 | — |
| `ARDUINO_IO[5]` | PIN_U13 | — |
| `ARDUINO_IO[6]` | PIN_AG8 | — |
| `ARDUINO_IO[7]` | PIN_AH8 | — |
| `ARDUINO_IO[8]` | PIN_AF17 | — |
| `ARDUINO_IO[9]` | PIN_AE15 | — |
| `ARDUINO_IO[10]` | PIN_AF15 | SS |
| `ARDUINO_IO[11]` | PIN_AG16 | MOSI |
| `ARDUINO_IO[12]` | PIN_AH11 | MISO |
| `ARDUINO_IO[13]` | PIN_AH12 | SCK |
| `ARDUINO_IO[14]` | PIN_AH9 | SDA |
| `ARDUINO_IO[15]` | PIN_AG11 | SCL |

> **Source**: Terasic DE10-Nano User Manual, Tables 3-10 and 3-11. All GPIO header pins use 3.3-V LVTTL.

### Scenario 4: HPS-controlled FPGA GPIO (e.g., PWM from software)

If you want the HPS (ARM) to control a GPIO header pin for something like PWM, there are two approaches:

**A. Register-based (recommended for this project):**
Your custom IP exposes Avalon-MM registers for configuration (e.g., PWM period, duty cycle). The HPS writes to these registers via the LW bridge, and the FPGA logic drives the physical pin. This is the same pattern as the calculator — no conduit changes needed beyond the output pin.

```
HPS ──(LW bridge)──> Avalon-MM registers ──> FPGA PWM logic ──> GPIO header pin
```

Example: a PWM IP with registers for `PERIOD`, `DUTY_CYCLE`, and `ENABLE`. The HPS writes the desired values, and the FPGA generates the PWM waveform in hardware with cycle-accurate timing.

**B. Direct bit-bang (simplest, but CPU-bound):**
Export a conduit that the HPS toggles via a single register bit. The HPS driver writes 1/0 in a loop with `usleep()` timing. This works for slow signals but wastes CPU and has poor timing accuracy (Linux is not real-time).

Approach A is almost always better — the FPGA handles precise timing while the HPS just sets parameters.

## Gotchas

1. **QSys overwrites submodules on regeneration.** Your source files in `ip/custom/<name>/` are canonical. The build system overlays them onto `generated/` submodules after every QSys generation automatically.

2. **IRQ direction is backwards in QSys XML.** `start` = the interrupt *receiver* (HPS), `end` = the interrupt *sender* (your IP). The GUI handles this automatically.

3. **Base address in HPS driver must match QSys.** The driver offset (e.g., `0x0100`) must exactly match `baseAddress` in `soc_system.qsys`.

4. **MSEL DIP switches.** After changing the FPGA design, you may need to power-cycle (not just reboot) if MSEL was wrong. Symptom: bridges show "enabled" but all reads return `0x0`.

5. **`_hw.tcl` file naming.** The file must end in `_hw.tcl` for Platform Designer to discover it. The `NAME` property inside must match the directory/module name.

6. **Template directory is excluded.** The `template/` directory is intentionally excluded from auto-discovery. You must copy it to a new name before it will be picked up.
