# HPS-FPGA Communication

This guide explains how to set up and implement communication between the HPS (Hard Processor System) and FPGA on the DE10-Nano board.

## Overview

The DE10-Nano SoC combines an ARM-based HPS with an FPGA fabric. Communication between these two parts is essential for many applications. The communication is facilitated through:
- FPGA-to-HPS Bridge
- HPS-to-FPGA Bridge
- Lightweight HPS-to-FPGA Bridge
- FPGA-to-SDRAM Bridge

## Prerequisites

Before setting up HPS-FPGA communication, ensure you have:
1. A working Linux image on the HPS (see [Linux HPS Images](linux_hps_image.md))
2. Basic understanding of the development workflow (see [Development Workflow](development_workflow.md))
3. Intel Quartus Prime installed on your development machine
4. Required development tools (Intel SoC EDS, cross-compiler)

## Setup Process

### 1. FPGA Design Configuration

1. **Create or Modify FPGA Design**
   - Use Platform Designer (formerly QSys) to create your design
   - Add necessary Avalon-MM interfaces for HPS communication
   - Configure memory-mapped regions
   - Generate HDL code

2. **Synthesize and Generate FPGA Bitstream**
   - Compile the design in Quartus
   - Generate the `.sof` file
   - Convert to `.rbf` format for Linux loading

### 2. Device Tree Configuration

1. **Set Up Linux Source**
   ```bash
   # Clone Linux source code
   git clone https://github.com/altera-opensource/linux-socfpga.git
   cd linux-socfpga

   # Checkout recommended branch for DE10-Nano
   git checkout ACDS17.1_REL_GSRD_PR

   # Create branch for custom changes
   git checkout -b my_custom
   ```

2. **Enable FPGA Bridges**
   
   Create a custom device tree file:
   ```bash
   cd arch/arm/boot/dts
   cp socfpga_cyclone5_de0_nano_soc.dts my_custom.dts
   ```

   Add the following to `my_custom.dts`:
   ```dts
   &fpga_bridge0 {
     status = "okay";
     bridge-enable = <1>;
   };

   &fpga_bridge1 {
     status = "okay";
     bridge-enable = <1>;
   };

   &fpga_bridge2 {
     status = "okay";
     bridge-enable = <1>;
   };

   &fpga_bridge3 {
     status = "okay";
     bridge-enable = <1>;
   };
   ```

3. **Generate and Deploy Device Tree Binary**
   ```bash
   # Generate DTB
   cd ../../../  # Return to linux-socfpga root
   make ARCH=arm my_custom.dtb

   # Backup and replace the device tree
   mkdir -p fat
   mount /dev/mmcblk0p1 fat
   cp fat/socfpga_cyclone5_de0_nano_soc.dtb fat/socfpga_cyclone5_de0_nano_soc_orig.dtb
   cp arch/arm/boot/dts/my_custom.dtb fat/socfpga_cyclone5_de0_nano_soc.dtb
   umount fat
   reboot
   ```

4. **Verify Bridge Status**
   After reboot, verify bridges are enabled:
   ```bash
   cat /sys/class/fpga_bridge/*/state
   ```
   You should see all bridges showing as "enabled".

### 3. Linux Driver Development

1. **Create Kernel Module**
   - Implement platform driver
   - Set up memory-mapped I/O regions
   - Handle interrupts if required
   - Create user-space interface

2. **Build and Install Driver**
   - Cross-compile the driver
   - Load module on target system
   - Create device nodes if needed

## Communication Methods

### 1. Memory-Mapped I/O
- Direct register access through memory addresses
- Suitable for control signals and small data transfers
- Example:
  ```c
  // Write to FPGA register
  iowrite32(value, fpga_base + offset);
  
  // Read from FPGA register
  value = ioread32(fpga_base + offset);
  ```

### 2. DMA Transfers
- Efficient for large data transfers
- Reduces CPU overhead
- Requires DMA controller in FPGA design

### 3. Interrupts
- FPGA can signal HPS for events
- Requires interrupt controller configuration
- Useful for asynchronous communication

## Example: LED Control

Here's a simple example of controlling FPGA LEDs from the HPS:

1. **FPGA Component (Verilog)**
   ```verilog
   module custom_leds (
       input  logic        clk,
       input  logic        reset,
       input  logic        avs_s0_address,
       input  logic        avs_s0_write,
       input  logic [31:0] avs_s0_writedata,
       output logic [7:0]  leds
   );
   
   always_ff @ (posedge clk) begin
       if (reset)
           leds <= '0;
       else if (avs_s0_write)
           leds <= avs_s0_writedata[7:0];
   end
   endmodule
   ```

2. **Linux Driver**
   ```c
   static ssize_t led_write(struct file *file, const char __user *buf,
                           size_t count, loff_t *ppos)
   {
       u32 value;
       if (copy_from_user(&value, buf, sizeof(value)))
           return -EFAULT;
       iowrite32(value, led_base);
       return sizeof(value);
   }
   ```

## Troubleshooting

1. **Bridge Communication Issues**
   - Verify bridge status: `cat /sys/class/fpga_bridge/*/state`
   - Check device tree configuration
   - Validate memory mappings

2. **Driver Problems**
   - Check kernel logs: `dmesg`
   - Verify driver loading: `lsmod`
   - Test memory access permissions

3. **FPGA Design Issues**
   - Validate timing constraints
   - Check Avalon-MM interface connections
   - Verify address mappings

## Resources

- [Intel SoC FPGA Documentation](https://www.intel.com/content/www/us/en/docs/programmable/683689/current/introduction.html)
- [Linux Device Drivers Guide](https://www.kernel.org/doc/html/latest/driver-api/index.html)
- [Avalon Interface Specifications](https://www.intel.com/content/www/us/en/docs/programmable/683091/current/introduction-to-the-interface-specifications.html) 