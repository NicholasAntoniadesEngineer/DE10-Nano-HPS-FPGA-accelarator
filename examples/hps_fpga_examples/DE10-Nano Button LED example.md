# DE10-Nano Button-LED Project

This document provides a step-by-step guide to create an FPGA project from scratch for the DE10-Nano board. The project enables the Hard Processor System (HPS) running Linux to detect a button press (KEY0) and drive an LED (LED0) via the FPGA. It includes FPGA code, kernel module code, and application code, with detailed instructions for setting up, compiling, and running each component.

## Step 1: Create a Quartus Prime Project

### Overview
Begin by creating a Quartus Prime project targeting the Cyclone V SoC (5CSEBA6U23I7), the specific device for the DE10-Nano board. This ensures the project is configured with the correct device context from the start.

### Instructions
1. **Open Quartus Prime**:
   - Launch Quartus Prime on your computer.
2. **Create a New Project**:
   - Go to File > New > Quartus Prime Project.
   - Click "Next" on the introduction page.
3. **Project Settings**:
   - **Directory, Name, Top-Level Entity**:
     - Choose a directory for your project (e.g., ~/DE10_Nano_SoC_GHRD).
     - Set the project name to DE10_Nano_SoC_GHRD.
     - Set the top-level design entity to DE10_Nano_SoC_GHRD.
     - Click "Next".
   - **Add Files**:
     - Leave this blank for now (files will be added later).
     - Click "Next".
   - **Family, Device & Board Settings**:
     - Family: Select "Cyclone V".
     - Devices: Choose "Cyclone V SE" from the dropdown.
     - Specific Device: Search for and select 5CSEBA6U23I7.
     - Click "Next".
   - **EDA Tool Settings**:
     - Leave the default settings unless you need specific tool integration.
     - Click "Next".
   - **Summary**:
     - Review the summary and click "Finish" to create the project.

## Step 2: Create the Platform Designer System

### Overview
Next, use Platform Designer to create a system (.qsys file) that includes the HPS, Parallel I/O (PIO) IPs for the button and LED, and a clock source. This system defines the FPGA hardware interfaced by the HPS.

### Instructions
1. **Open Platform Designer**:
   - In Quartus Prime, go to Tools > Platform Designer.
2. **Create a New System**:
   - Go to File > New System.
   - Save the system as de10_nano_system.qsys.
3. **Add Components**:
   - **HPS (`hps_0`)**:
     - In the IP Catalog, search for "Cyclone V Hard Processor System".
     - Double-click to add it.
     - In the HPS configuration window, go to the FPGA Interfaces tab and enable "Lightweight HPS-to-FPGA AXI Bridge".
     - Export `h2f_reset` by checking the box and naming it `hps_0_h2f_reset`.
   - **Clock Source (`clk_50`)**:
     - In the IP Catalog, search for "Clock Source".
     - Add it and set the frequency to 50 MHz.
     - Export `clk_in` as `clk_clk` and `clk_in_reset` as `reset_reset_n`.
   - **Button PIO (`pio_button`)**:
     - In the IP Catalog, search for "PIO (Parallel I/O)".
     - Add it, set "Width" to 1 bit and "Direction" to "Input".
     - Export `pio` as `pio_button_external_connection` and `reset` as `pio_button_reset`.
   - **LED PIO (`pio_led`)**:
     - In the IP Catalog, search for "PIO".
     - Add it, set "Width" to 1 bit and "Direction" to "Output".
     - Export `pio` as `pio_led_external_connection` and `reset` as `pio_led_reset`.
4. **Make Connections**:
   - **Clock Connections**:
     - Connect `clk_50.clk` to `hps_0.h2f_lw_axi_clock`, `pio_button.clk`, and `pio_led.clk`.
   - **Reset Connections**:
     - Connect `clk_50.clk_reset` to `pio_button.reset` and `pio_led.reset`.
     - Optionally connect `clk_50.clk_in_reset` to `hps_0.h2f_reset` or tie it high.
   - **AXI Connections**:
     - Connect `hps_0.h2f_lw_axi_master` to `pio_button.s1` and assign address 0x0000_0000.
     - Connect `hps_0.h2f_lw_axi_master` to `pio_led.s1` and assign address 0x0000_0010.
5. **Generate HDL**:
   - Go to Generate > Generate HDL.
   - Select "Verilog" as the HDL language.
   - Set the output directory to output_files.
   - Click "Generate" to create the HDL files.

## Step 3: Create the Top-Level Verilog File

### Overview
Create a top-level Verilog file to instantiate the Platform Designer system and connect it to the DE10-Nano's physical pins.

### Top-Level Verilog (`DE10_Nano_SoC_GHRD.v`)

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
        // Other HPS ports can be connected if needed
    );

    assign button_in = ~KEY[0];  // Invert KEY0 for logic 1 when pressed
    assign LED[0] = led_out;
    assign LED[3:1] = 3'b000;    // Turn off other LEDs

endmodule
```

### Instructions
1. **Create the Verilog File**:
   - In Quartus Prime, go to File > New > Verilog HDL File.
   - Copy and paste the Verilog code above.
   - Save it as DE10_Nano_SoC_GHRD.v.
2. **Add to Project**:
   - Go to Project > Add/Remove Files in Project.
   - Add DE10_Nano_SoC_GHRD.v and de10_nano_system.qsys to the project.

## Step 4: Add Pin Assignments

### Overview
Map the signals in the Verilog file to the physical pins on the DE10-Nano board using pin assignments in the .qsf file.

### Pin Assignments (`DE10_Nano_SoC_GHRD.qsf`)

Add these lines to your project's .qsf file:

```tcl
set_location_assignment PIN_V11  -to CLOCK_50
set_location_assignment PIN_AH17 -to KEY[0]
set_location_assignment PIN_AH16 -to KEY[1]
set_location_assignment PIN_AG17 -to LED[0]
set_location_assignment PIN_AF17 -to LED[1]
set_location_assignment PIN_AE17 -to LED[2]
set_location_assignment PIN_AD17 -to LED[3]
```

### Instructions
1. **Open the .qsf File**:
   - In Quartus Prime, go to Assignments > Assignment Editor or edit the .qsf file directly in a text editor.
2. **Add Assignments**:
   - In the Assignment Editor, add each pin assignment manually, or paste the lines above into the .qsf file.

## Step 5: Compile and Program the FPGA

### Instructions
1. **Set Top-Level Entity**:
   - Go to Assignments > Settings > General.
   - Ensure the top-level entity is DE10_Nano_SoC_GHRD.
2. **Compile the Project**:
   - Go to Processing > Start Compilation.
   - Wait for compilation to complete successfully.
3. **Program the FPGA**:
   - Connect the DE10-Nano board to your computer via USB-Blaster.
   - Go to Tools > Programmer.
   - Select the generated .sof file and program the FPGA.

## Step 6: Kernel Module Code

### Overview
The kernel module maps the FPGA's memory-mapped registers into kernel space and exposes them via a character device (`/dev/button_led`) for user-space interaction.

### Kernel Module (`button_led.c`)

```c
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/io.h>
#include <linux/uaccess.h>

#define BRIDGE_BASE   0xFF200000  // Lightweight bridge base address
#define BUTTON_OFFSET 0x0000      // Button PIO offset
#define LED_OFFSET    0x0010      // LED PIO offset

static void __iomem *button_addr;
static void __iomem *led_addr;
static int major;
static struct class *cls;

static ssize_t button_led_read(struct file *file, char __user *buf, size_t count, loff_t *ppos) {
    if (count < 1) return -EINVAL;
    u32 val = ioread32(button_addr);
    char state = (val & 1) ? '1' : '0';  // Button state: '1' pressed, '0' released
    if (copy_to_user(buf, &state, 1)) return -EFAULT;
    return 1;
}

static ssize_t button_led_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos) {
    if (count < 1) return -EINVAL;
    char state;
    if (copy_from_user(&state, buf, 1)) return -EFAULT;
    u32 val = (state == '1') ? 1 : 0;    // LED: '1' on, '0' off
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
        iounmap(button_addr);
        iounmap(led_addr);
        return major;
    }

    cls = class_create(THIS_MODULE, "button_led");
    if (IS_ERR(cls)) {
        unregister_chrdev(major, "button_led");
        iounmap(button_addr);
        iounmap(led_addr);
        return PTR_ERR(cls);
    }
    if (IS_ERR(device_create(cls, NULL, MKDEV(major, 0), NULL, "button_led"))) {
        class_destroy(cls);
        unregister_chrdev(major, "button_led");
        iounmap(button_addr);
        iounmap(led_addr);
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
1. **Setup Environment**:
   - Access the DE10-Nano's Linux system (e.g., via SSH or console).
   - Install kernel headers: `sudo apt-get install linux-headers-$(uname -r)` (for Debian-based distros).
2. **Save Files**:
   - Save `button_led.c` and `Makefile` in a directory (e.g., `~/button_led_driver`).
3. **Compile**:
   - Run `make` to build `button_led.ko`.
4. **Load Module**:
   - Run `sudo insmod button_led.ko`.
   - Verify `/dev/button_led` exists: `ls /dev/button_led`.
   - Check logs: `dmesg | grep button_led`.
5. **Unload (Optional)**:
   - Run `sudo rmmod button_led` to remove the module.

## Step 7: Application Code

### Overview
The user-space application polls the button state via `/dev/button_led` and toggles LED0 based on whether KEY0 is pressed.

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
            close(fd);
            return 1;
        }
        if (state == '1') {
            printf("Button pressed\n");
            if (write(fd, "1", 1) != 1) {
                perror("write failed");
                close(fd);
                return 1;
            }
        } else {
            if (write(fd, "0", 1) != 1) {
                perror("write failed");
                close(fd);
                return 1;
            }
        }
        usleep(100000);  // Poll every 100ms to avoid overwhelming the system
    }

    close(fd);  // Unreachable due to infinite loop, but good practice
    return 0;
}
```

### Instructions
1. **Compile the Application**:
   - Save the code as `button_led_app.c`.
   - Compile: `gcc -o button_led_app button_led_app.c`.
2. **Run the Application**:
   - Run with `sudo ./button_led_app`.
   - Press KEY0 to toggle LED0.

## Full Setup Workflow

1. **Create Quartus Project**:
   - Set up a new project for the Cyclone V SoC (5CSEBA6U23I7).
2. **Create Platform Designer System**:
   - Add HPS, clock, and PIOs; generate HDL.
3. **Create Top-Level Verilog File**:
   - Instantiate the system and connect to pins.
4. **Add Pin Assignments**:
   - Map signals to physical pins.
5. **Compile and Program FPGA**:
   - Compile and program via USB-Blaster.
6. **Compile and Load Kernel Module**:
   - Build and insert the kernel module.
7. **Compile and Run Application**:
   - Build and run the application.

## Notes

- **Address Consistency**: The kernel module uses 0xFF200000 (button) and 0xFF200010 (LED), which align with Platform Designer's Lightweight HPS-to-FPGA bridge base (0xFF200000) plus offsets (0x0000 and 0x0010).
- **Permissions**: Use sudo for the application due to root access requirements for `/dev/button_led`.
- **Debugging**: Check kernel logs with `dmesg` and use printf in the application.
- **Reset**: Reset is tied high here; for robustness, connect KEY1 to `reset_reset_n`.

This setup enables the HPS to detect KEY0 presses and control LED0 via the FPGA.
