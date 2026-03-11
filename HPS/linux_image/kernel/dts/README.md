# Device Tree Sources

This directory owns the Device Tree Source files for the DE10-Nano. They are
copied into the kernel source tree before every kernel build — this directory
is the **single source of truth**. Never edit files inside `linux-socfpga/` directly.

## File Include Chain

```
socfpga_cyclone5_de10_nano.dts   ← board-level (edit this to add custom IP)
  └── socfpga_cyclone5.dtsi      ← Cyclone V family (osc1 = 25 MHz, watchdog)
        └── socfpga.dtsi         ← SoC base (all HPS peripherals, clocks, bridges)
```

## Adding a New FPGA IP Node

Edit `socfpga_cyclone5_de10_nano.dts` and add a node inside `&soc`:

```dts
&soc {
    myip0: myip@ff210000 {
        compatible = "generic-uio";            /* or your driver's compatible string */
        reg = <0xff210000 0x40>;               /* LW HPS-to-FPGA base 0xFF200000 + QSys offset */
        interrupts = <0 41 4>;                 /* GIC SPI = QSys IRQ# + 40 for f2h_irq0 */
        interrupt-parent = <&intc>;
        linux,uio-name = "my-custom-ip";       /* name in /sys/class/uio/*/name */
        status = "okay";
    };
};
```

> **Why `&soc` and not `&base_fpga_region`?**
> `base_fpga_region` is an `fpga-region` node — Linux only instantiates its children
> after programming the FPGA through the Linux FPGA Manager firmware API. Since U-Boot
> programs the FPGA before Linux boots, the region never fires and UIO never probes.
> Placing nodes directly under `&soc` causes the kernel to probe them at boot, which
> is the correct approach when U-Boot handles FPGA configuration.

### Address

Lightweight HPS-to-FPGA bridge base: `0xFF200000`.
Add the QSys slave base offset — e.g. QSys offset `0x00010000` → reg `0xFF210000`.

### Interrupt

`hps_0.f2h_irq0` QSys IRQ 0 → GIC SPI 40. Each additional QSys IRQ increments by 1.

## Rebuild DTB

```bash
# Full build (inside Docker):
make kernel

# Kernel-only (inside the kernel sub-directory):
cd HPS/linux_image/kernel && make
```

Output DTB: `HPS/linux_image/kernel/build/arch/arm/boot/dts/socfpga_cyclone5_de10_nano.dtb`

`create_sd_image.sh` copies this to the FAT32 boot partition as `socfpga.dtb` automatically.

## Adding a New DTS/DTSI File

Drop any `.dts` or `.dtsi` file into this directory. The kernel Makefile glob-copies
all `*.dts` and `*.dtsi` files into the kernel source tree at build time — no Makefile
edits needed for DTSI includes. For a new board DTS, also add the DTB target name to
`arch/arm/boot/dts/Makefile` inside the kernel (the build script handles this for
`socfpga_cyclone5_de10_nano.dtb` automatically).

## Origin of Base Files

| File | Origin |
|------|--------|
| `socfpga.dtsi` | Extracted verbatim from `linux-socfpga` submodule (`arch/arm/boot/dts/`) |
| `socfpga_cyclone5.dtsi` | Extracted verbatim from `linux-socfpga` submodule |
| `socfpga_cyclone5_de10_nano.dts` | Authored for this project; based on upstream DE0-Nano-SoC DTS with DE10-Nano hardware differences, FPGA bridge enables, and calculator IP node |
