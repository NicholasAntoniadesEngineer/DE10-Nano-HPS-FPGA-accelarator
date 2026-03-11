# DE10-Nano Button-LED Project

This document provides the FPGA code, kernel module code, and application code to detect a button press (KEY0) on the DE10-Nano board using the Hard Processor System (HPS) running Linux and drive an LED (LED0) via the FPGA. Instructions are included for setting up, compiling, and running each component.

## FPGA Code

### Overview
The FPGA design uses Intel's Platform Designer to create a system with:
- A Hard Processor System (HPS) with the lightweight HPS-to-FPGA bridge enabled
- Two Parallel I/O (PIO) IPs: one for the button (input) and one for the LED (output)
- A clock source driven by the DE10-Nano's 50 MHz `CLOCK_50`

### Platform Designer System (`de10_nano_system.qsys`)

1. **Create the System**:
   - Open Quartus Prime, Tools, Platform Designer
   - Create a new system: File, New System, save as `de10_nano_system.qsys`

2. **Add Components**:
   - **HPS (`hps_0`)**:
     - IP Catalog: "Cyclone V Hard Processor System"
     - Enable "Lightweight HPS-to-FPGA AXI Bridge" (FPGA Interfaces tab)
     - Export `h2f_reset` as `hps_0_h2f_reset`
   - **Clock Source (`clk_50`)**:
     - IP Catalog: "Clock Source", set to 50 MHz
     - Export `clk_in` as `clk_clk`, `clk_in_reset` as `reset_reset_n`
   - **Button PIO (`pio_button`)**:
     - IP Catalog: "PIO (Parallel I/O)"
     - Width: 1 bit, Direction: Input
     - Export `pio` as `pio_button_external_connection`, `reset` as `pio_button_reset`
   - **LED PIO (`pio_led`)**:
     - IP Catalog: "PIO"
     - Width: 1 bit, Direction: Output
     - Export `pio` as `pio_led_external_connection`, `reset` as `pio_led_reset`

3. **Connections**:
   - **Clock**:
     - `clk_50.clk` to `hps_0.h2f_lw_axi_clock`, `pio_button.clk`, `pio_led.clk`
   - **Reset**:
     - `clk_50.clk_reset` to `pio_button.reset`, `pio_led.reset`
     - `clk_50.clk_in_reset` to `hps_0.h2f_reset` (optional, or tie high)
   - **AXI**:
     - `hps_0.h2f_lw_axi_master` to `pio_button.s1` (address `0xFF200000`), `pio_led.s1` (address `0xFF200010`)

4. **Generate HDL**:
   - `Generate > Generate HDL`, select Verilog, output to `output_files`

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
        // Other HPS ports omitted
    );

    assign button_in = ~KEY[0];  // Invert KEY0 for logic 1 when pressed
    assign LED[0] = led_out;
    assign LED[3:1] = 3'b000;

endmodule
```

### Pin Assignments (`DE10_Nano_SoC_GHRD.qsf`)

Add to your Quartus .qsf:

```tcl
set_location_assignment PIN_V11  -to CLOCK_50
set_location_assignment PIN_AH17 -to KEY[0]
set_location_assignment PIN_AH16 -to KEY[1]
set_location_assignment PIN_AG17 -to LED[0]
set_location_assignment PIN_AF17 -to LED[1]
set_location_assignment PIN_AE17 -to LED[2]
set_location_assignment PIN_AD17 -to LED[3]
```

### FPGA Instructions

1. **Create Project**:
   - Open Quartus Prime, create a new project for the DE10-Nano (Cyclone V SoC: 5CSEBA6U23I7)
   - Set the top-level entity to DE10_Nano_SoC_GHRD

2. **Add Files**:
   - Add `DE10_Nano_SoC_GHRD.v` and `de10_nano_system.qsys` to the project

3. **Compile**:
   - Processing > Start Compilation

4. **Program FPGA**:
   - Use Quartus Programmer with the generated .sof file to program the FPGA via USB-Blaster

## Kernel Code

### Overview
The kernel module maps the FPGA's memory-mapped registers (0xFF200000 for button, 0xFF200010 for LED) into kernel space and exposes them via a character device (`/dev/button_led`) for user-space interaction.

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

### Kernel Module Instructions

1. **Setup Environment**:
   - Ensure you're on the DE10-Nano's Linux system (e.g., via SSH or console)
   - Install kernel headers: `sudo apt-get install linux-headers-$(uname -r)` (if using a Debian-based distro)

2. **Save Files**:
   - Save `button_led.c` and `Makefile` in a directory (e.g., `~/button_led_driver`)

3. **Compile**:
   - Run `make` in the directory to build `button_led.ko`

4. **Load Module**:
   - Run `sudo insmod button_led.ko`
   - Check `/dev/button_led` exists: `ls /dev/button_led`
   - View logs: `dmesg | grep button_led`

5. **Unload (Optional)**:
   - Run `sudo rmmod button_led` to remove the module

## Application Code

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

## Full Setup Workflow

1. **FPGA**:
   - Configure and generate the Platform Designer system
   - Compile and program the FPGA using Quartus

2. **Kernel**:
   - Compile and load the kernel module on the DE10-Nano's Linux system

3. **Application**:
   - Compile and run the application to interact with the button and LED

## Notes

- **Address Consistency**: Verify that 0xFF200000 and 0xFF200010 match the addresses assigned in Platform Designer
- **Permissions**: Use sudo for the app because `/dev/button_led` requires root access by default
- **Debugging**: Use `dmesg` for kernel logs and printf outputs in the app for troubleshooting
- **Reset**: The reset is tied high in this example; for a more robust design, connect KEY1 to `reset_reset_n`

This setup enables the HPS to detect KEY0 presses and control LED0 via the FPGA.
