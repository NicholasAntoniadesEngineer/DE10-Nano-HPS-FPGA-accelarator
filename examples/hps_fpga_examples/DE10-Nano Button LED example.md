# DE10-Nano Button-LED Project

This document provides a complete guide to create an FPGA design, kernel module, and application for the DE10-Nano board using Quartus Lite. The Hard Processor System (HPS) runs Linux, detects a button press (KEY0), and drives an LED (LED0) via the FPGA. The project, named DE10_nano_button_led, includes proper SDRAM initialization for the HPS to boot Linux, ensuring successful HDL generation and compilation.

## FPGA Code

### Overview
The FPGA design uses Intel's Platform Designer to create a system with:
- A Hard Processor System (HPS) with the lightweight HPS-to-FPGA bridge enabled and SDRAM configured for Linux.
- Two Parallel I/O (PIO) IPs: one for the button (input) and one for the LED (output).
- A clock source driven by the DE10-Nano's 50 MHz `CLOCK_50`.

### Step 1: Create a New Quartus Project

1. **Launch Quartus Lite**:
   - Open Quartus Lite (e.g., version 20.1.0).

2. **Create a New Project**:
   - Go to File > New Project Wizard.
   - Project Name: DE10_nano_button_led.
   - Directory: Choose a location (e.g., ~/DE10_nano_button_led).
   - Click Next.
   - Device Family: Select Cyclone V.
   - Device: Choose 5CSEBA6U23I7 (DE10-Nano's Cyclone V SoC).
   - Click Next through remaining screens (no files yet), then Finish.

### Step 2: Create the Platform Designer System

1. **Launch Platform Designer**:
   - In Quartus Lite, go to Tools > Platform Designer.
   - Select File > New System, save as `de10_nano_system.qsys` in your project directory.

2. **Add Components**:
   - **HPS (`hps_0`)**:
     - IP Catalog: "Cyclone V Hard Processor System".
     - Add it, name it `hps_0`.
     - Configure:
       - FPGA Interfaces:
         - Enable "Lightweight HPS-to-FPGA AXI Bridge".
       - Peripheral Pins:
         - Enable "SDRAM" (required for Linux).
       - Configure SDRAM (match DE10-Nano's DDR3):
         - Memory Type: DDR3.
         - Width: 32 bits.
         - Total Size: 1024 MB (1 GB).
         - Frequency: 400 MHz.
         - Use default timing parameters (e.g., CAS latency, refresh settings).
       - Export `h2f_reset` as `hps_0_h2f_reset`.
     - Click Finish.
   - **Clock Source (`clk_50`)**:
     - IP Catalog: "Clock Source", set to 50 MHz.
     - Export `clk` as `clk_clk`, `reset` as `reset_reset_n`.
   - **Button PIO (`pio_button`)**:
     - IP Catalog: "PIO (Parallel I/O)".
     - Width: 1 bit, Direction: Input.
     - Export `external_connection` as `pio_button_external_connection`, `reset` as `pio_button_reset`.
   - **LED PIO (`pio_led`)**:
     - IP Catalog: "PIO (Parallel I/O)".
     - Width: 1 bit, Direction: Output.
     - Export `external_connection` as `pio_led_external_connection`, `reset` as `pio_led_reset`.

3. **Make Connections**:
   - **Clock**:
     - `clk_50.clk` to `hps_0.h2f_lw_axi_clock`, `pio_button.clk`, `pio_led.clk`.
   - **Reset**:
     - `clk_50.reset` to `pio_button.reset`, `pio_led.reset`.
     - `clk_50.reset` to `hps_0.h2f_reset` (optional; can tie high in Verilog).
   - **AXI**:
     - `hps_0.h2f_lw_axi_master` to `pio_button.s1` (address `0x0000`), `pio_led.s1` (address `0x0010`).
   - **SDRAM**: Leave `hps_0.hps_sdram` unconnected to FPGA fabric (used by HPS only).

4. **Generate HDL**:
   - Go to Generate > Generate HDL.
   - Select Verilog, output to `output_files`.
   - Click Generate. This should succeed with SDRAM configured.

### Step 3: Create the Top-Level Verilog File

1. **Create Verilog File**:
   - File > New > Verilog HDL File.
   - Save as `DE10_Nano_SoC_GHRD.v`.

2. **Add Code**:

```verilog
module DE10_Nano_SoC_GHRD (
    input CLOCK_50,          // PIN_V11
    input [1:0] KEY,         // KEY0: PIN_AH17, KEY1: PIN_AH16 (active low)
    output [3:0] LED         // LED0: PIN_AG17, LED1-3: PIN_AF17, AE17, AD17
);

    wire button_in;
    wire led_out;
    wire hps_reset;
    wire pio_button_rst;
    wire pio_led_rst;

    de10_nano_system u0 (
        .clk_clk(CLOCK_50),
        .reset_reset_n(1'b1),                   // Tie high for simplicity
        .pio_button_external_connection_export(button_in),
        .pio_led_external_connection_export(led_out),
        .hps_0_h2f_reset(hps_reset),
        .pio_button_reset(pio_button_rst),
        .pio_led_reset(pio_led_rst)
        // SDRAM and other HPS ports auto-connected
    );

    assign button_in = ~KEY[0];  // Invert KEY0 for logic 1 when pressed
    assign LED[0] = led_out;
    assign LED[3:1] = 3'b000;

endmodule
```

### Step 4: Add Files and Set Top-Level

1. **Add Files**:
   - Project > Add/Remove Files in Project.
   - Add `DE10_Nano_SoC_GHRD.v` and `de10_nano_system.qsys`.

2. **Set Top-Level**:
   - Assignments > Settings > General.
   - Top-level entity: `DE10_Nano_SoC_GHRD`.

### Step 5: Add Pin Assignments

1. **Edit .qsf**:
   - Open `DE10_nano_button_led.qsf` in a text editor or use Assignments > Assignment Editor.
   - Add:

```tcl
set_location_assignment PIN_V11  -to CLOCK_50
set_location_assignment PIN_AH17 -to KEY[0]
set_location_assignment PIN_AH16 -to KEY[1]
set_location_assignment PIN_AG17 -to LED[0]
set_location_assignment PIN_AF17 -to LED[1]
set_location_assignment PIN_AE17 -to LED[2]
set_location_assignment PIN_AD17 -to LED[3]
```

2. **SDRAM Pin Assignments**:
   - After HDL generation, find `hps_sdram_p0_pin_assignments.tcl` in `output_files/de10_nano_system/synthesis/submodules/`.
   - Run it post-synthesis (Tools > Tcl Scripts) to assign SDRAM pins (matches DE10-Nano's DDR3).

### Step 6: Compile the Project

1. **Clean Project**:
   - Project > Clean All.

2. **Compile**:
   - Processing > Start Compilation.
   - Post-synthesis, run `hps_sdram_p0_pin_assignments.tcl` if prompted, then recompile.

3. **Output**:
   - Check for `DE10_nano_button_led.sof` in `output_files`.

### Step 7: Program the FPGA

- Tools > Programmer.
- Select USB-Blaster, add `DE10_nano_button_led.sof`, and click Start.

## HPS Boot Configuration

### Overview
The HPS requires a preloader to initialize SDRAM for Linux to boot.

1. **Generate Preloader**:
   - Use Intel's Embedded Design Suite (EDS):
     - Tools > Embedded Command Shell.
     - Run: `bsp-editor`.
   - Load your `.qsys` file, configure HPS settings (SDRAM enabled), and generate preloader files.
   - Output: `software/spl_bsp/`.

2. **Build Preloader**:
   - In EDS shell: `make -C software/spl_bsp/`.
   - Copy `preloader-mkpimage.bin` to your SD card's boot partition.

3. **SD Card Setup**:
   - Use a Terasic-provided Linux SD card image.
   - Update the preloader in the boot partition with your generated file.

## Kernel Code

### Overview
The kernel module maps FPGA registers (0xFF200000 base) to a character device (`/dev/button_led`).

### Kernel Module (`button_led.c`)

```c
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/io.h>
#include <linux/uaccess.h>

#define BRIDGE_BASE   0xFF200000  // Lightweight bridge base
#define BUTTON_OFFSET 0x0000
#define LED_OFFSET    0x0010

static void __iomem *button_addr;
static void __iomem *led_addr;
static int major;
static struct class *cls;

static ssize_t button_led_read(struct file *file, char __user *buf, size_t count, loff_t *ppos) {
    if (count < 1) return -EINVAL;
    u32 val = ioread32(button_addr);
    char state = (val & 1) ? '1' : '0';
    if (copy_to_user(buf, &state, 1)) return -EFAULT;
    return 1;
}

static ssize_t button_led_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos) {
    if (count < 1) return -EINVAL;
    char state;
    if (copy_from_user(&state, buf, 1)) return -EFAULT;
    u32 val = (state == '1') ? 1 : 0;
    iowrite32(val, led_addr);
    return 1;
}

static const struct file_operations fops = {
    .read  = button_led_read,
    .write = button_led_write,
};

static int __init button_led_init(void) {
    button_addr = ioremap(BRIDGE_BASE + BUTTON_OFFSET, 4);
    led_addr = ioremap(BRIDGE_BASE + LED_OFFSET, 4);
    if (!button_addr || !led_addr) {
        pr_err("ioremap failed\n");
        return -ENOMEM;
    }
    major = register_chrdev(0, "button_led", &fops);
    if (major < 0) {
        pr_err("register_chrdev failed\n");
        return major;
    }
    cls = class_create(THIS_MODULE, "button_led");
    if (IS_ERR(cls)) {
        unregister_chrdev(major, "button_led");
        return PTR_ERR(cls);
    }
    if (IS_ERR(device_create(cls, NULL, MKDEV(major, 0), NULL, "button_led"))) {
        class_destroy(cls);
        unregister_chrdev(major, "button_led");
        return -EIO;
    }
    pr_info("button_led module loaded\n");
    return 0;
}

static void __exit button_led_exit(void) {
    device_destroy(cls, MKDEV(major, 0));
    class_destroy(cls);
    unregister_chrdev(major, "button_led");
    iounmap(button_addr);
    iounmap(led_addr);
    pr_info("button_led module unloaded\n");
}

module_init(button_led_init);
module_exit(button_led_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("DE10-Nano Button-LED Driver");
```

### Makefile

```makefile
obj-m += button_led.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
```

### Instructions

1. **Setup**:
   - SSH into DE10-Nano's Linux.
   - Install headers: `sudo apt-get install linux-headers-$(uname -r)`.

2. **Compile**:
   - Save files in `~/button_led_driver`.
   - Run `make`.

3. **Load**:
   - `sudo insmod button_led.ko`.
   - Verify: `ls /dev/button_led`.

## Application Code

### Application (`button_led_app.c`)

```c
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

int main() {
    int fd = open("/dev/button_led", O_RDWR);
    if (fd < 0) {
        perror("Failed to open /dev/button_led");
        return 1;
    }
    char state;
    printf("Press KEY0 to toggle LED0 (Ctrl+C to exit)\n");
    while (1) {
        if (read(fd, &state, 1) != 1) {
            perror("read failed");
            return 1;
        }
        if (state == '1') {
            printf("Button pressed\n");
            if (write(fd, "1", 1) != 1) {
                perror("write failed");
                return 1;
            }
        } else {
            if (write(fd, "0", 1) != 1) {
                perror("write failed");
                return 1;
            }
        }
        usleep(100000);
    }
    close(fd);
    return 0;
}
```

### Instructions

1. **Compile**:
   - `gcc button_led_app.c -o button_led_app`.

2. **Run**:
   - `sudo ./button_led_app`.

## Full Workflow

1. **FPGA**:
   - Create project, configure Platform Designer with SDRAM, compile, and program.

2. **HPS**:
   - Generate and install preloader for SDRAM initialization.

3. **Kernel**:
   - Compile and load the kernel module.

4. **Application**:
   - Run the app to control LED0 with KEY0.

## Notes

- **SDRAM**: Configured for HPS/Linux; FPGA uses lightweight bridge only.
- **Addresses**: 0xFF200000 base aligns with Platform Designer's lightweight bridge offset.
- **Preloader**: Matches HPS settings to boot Linux correctly.
- **Debugging**: Use `dmesg` and app output for troubleshooting.

This setup ensures Linux runs on the HPS with SDRAM, and the FPGA controls the button and LED seamlessly.
