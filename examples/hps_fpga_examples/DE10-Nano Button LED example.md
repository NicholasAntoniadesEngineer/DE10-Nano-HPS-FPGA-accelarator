# DE10-Nano Button-LED Project

This document provides a step-by-step guide to create an FPGA design, a kernel module, and an application to detect a button press (KEY0) on the DE10-Nano board using the Hard Processor System (HPS) running Linux and drive an LED (LED0) via the FPGA. The instructions are crafted for Quartus Lite and start from scratch, ensuring the project is correctly configured for the Cyclone V SoC (5CSEBA6U23I7) and named "DE10_nano_button_led."

## FPGA Code

### Overview
The FPGA design uses Intel's Platform Designer to create a system with:
- A Hard Processor System (HPS) with the lightweight HPS-to-FPGA bridge enabled
- Two Parallel I/O (PIO) IPs: one for the button (input) and one for the LED (output)
- A clock source driven by the DE10-Nano's 50 MHz `CLOCK_50`

### Step 1: Create a New Quartus Project

1. **Launch Quartus Lite**:
   - Open the Quartus Lite software on your computer.

2. **Create a New Project**:
   - Go to File > New Project Wizard.
   - In the "New Project Wizard":
     - Project Name: Enter `DE10_nano_button_led`.
     - Directory: Choose a suitable directory (e.g., `C:\DE10_nano_button_led` or `/home/user/DE10_nano_button_led`).
     - Click Next.
   - Device Family: Select Cyclone V.
   - Device: In the list, find and select `5CSEBA6U23I7` (this is the Cyclone V SoC on the DE10-Nano board).
   - Click Next through the remaining screens (no files to add yet), then Finish.

   Note: At this stage, Quartus may prompt for a top-level design file. Since we're building from scratch, we'll create it later after Platform Designer work. Skip adding files for now.

### Step 2: Create the Platform Designer System

1. **Launch Platform Designer**:
   - In Quartus Lite, go to Tools > Platform Designer.
   - Select File > New System.
   - Save the system as `de10_nano_system.qsys` in your project directory.

2. **Add Components**:
   - **HPS (`hps_0`)**:
     - In the IP Catalog (right panel), search for "Cyclone V Hard Processor System".
     - Double-click to add it, name it `hps_0`.
     - In the settings window:
       - Go to the FPGA Interfaces tab.
       - Enable "Lightweight HPS-to-FPGA AXI Bridge".
       - Export the `h2f_reset` signal by double-clicking it and naming it `hps_0_h2f_reset`.
       - Click Finish.
   - **Clock Source (`clk_50`)**:
     - Search for "Clock Source" in the IP Catalog.
     - Add it, set the frequency to 50 MHz.
     - Export `clk` as `clk_clk` and `reset` as `reset_reset_n`.
   - **Button PIO (`pio_button`)**:
     - Search for "PIO (Parallel I/O)".
     - Add it, configure:
       - Width: 1 bit.
       - Direction: Input.
       - Export `external_connection` as `pio_button_external_connection` and `reset` as `pio_button_reset`.
   - **LED PIO (`pio_led`)**:
     - Search for "PIO (Parallel I/O)".
     - Add it, configure:
       - Width: 1 bit.
       - Direction: Output.
       - Export `external_connection` as `pio_led_external_connection` and `reset` as `pio_led_reset`.

3. **Make Connections**:
   - **Clock Connections**:
     - Connect `clk_50.clk` to `hps_0.h2f_lw_axi_clock`, `pio_button.clk`, and `pio_led.clk` (drag lines in the "Connections" column).
   - **Reset Connections**:
     - Connect `clk_50.reset` to `pio_button.reset` and `pio_led.reset`.
     - Optionally connect `clk_50.reset` to `hps_0.h2f_reset` or leave it unconnected (we'll tie it high later).
   - **AXI Connections**:
     - Connect `hps_0.h2f_lw_axi_master` to `pio_button.s1` and `pio_led.s1`.
     - Assign base addresses:
       - Right-click `pio_button.s1`, select Assign Base Address, set to `0x0000`.
       - Right-click `pio_led.s1`, set to `0x0010`.

4. **Generate HDL**:
   - Go to Generate > Generate HDL.
   - In the dialog:
     - Output Format: Select Verilog.
     - Output Directory: Use default (`output_files`) or specify a path.
     - Click Generate and wait for completion.

### Step 3: Create the Top-Level Verilog File

1. **Create a New Verilog File**:
   - In Quartus Lite, go to File > New > Verilog HDL File.
   - Save it as `DE10_Nano_SoC_GHRD.v` in your project directory.

2. **Add the Following Code**:

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
        // Other HPS ports omitted for simplicity
    );

    assign button_in = ~KEY[0];  // Invert KEY0 (active low) for logic 1 when pressed
    assign LED[0] = led_out;
    assign LED[3:1] = 3'b000;    // Keep other LEDs off

endmodule
```

### Step 4: Add Files to the Project

1. **Add Files**:
   - Go to Project > Add/Remove Files in Project.
   - Click the ... button, add:
     - `DE10_Nano_SoC_GHRD.v`
     - `de10_nano_system.qsys`
   - Click OK.

2. **Set Top-Level Entity**:
   - Go to Assignments > Settings > General.
   - Under "Top-level entity," select `DE10_Nano_SoC_GHRD`.
   - Click OK.

### Step 5: Add Pin Assignments

1. **Open Assignment Editor**:
   - Go to Assignments > Assignment Editor.

2. **Add Pin Assignments**:
   - Add the following (double-click to create new rows):
     - To: `CLOCK_50`, Location: `PIN_V11`
     - To: `KEY[0]`, Location: `PIN_AH17`
     - To: `KEY[1]`, Location: `PIN_AH16`
     - To: `LED[0]`, Location: `PIN_AG17`
     - To: `LED[1]`, Location: `PIN_AF17`
     - To: `LED[2]`, Location: `PIN_AE17`
     - To: `LED[3]`, Location: `PIN_AD17`

   Alternatively, edit `DE10_nano_button_led.qsf` directly:

```tcl
set_location_assignment PIN_V11  -to CLOCK_50
set_location_assignment PIN_AH17 -to KEY[0]
set_location_assignment PIN_AH16 -to KEY[1]
set_location_assignment PIN_AG17 -to LED[0]
set_location_assignment PIN_AF17 -to LED[1]
set_location_assignment PIN_AE17 -to LED[2]
set_location_assignment PIN_AD17 -to LED[3]
```

### Step 6: Compile the Project

1. **Start Compilation**:
   - Go to Processing > Start Compilation.
   - Wait for the process to complete. Check for errors in the "Messages" tab.

### Step 7: Program the FPGA

1. **Open Programmer**:
   - Go to Tools > Programmer.
   - Click Hardware Setup, select your USB-Blaster.
   - Click Add File, select `output_files/DE10_nano_button_led.sof`.
   - Click Start to program the FPGA.

## Kernel Code

### Overview
The kernel module maps the FPGA's memory-mapped registers into kernel space and exposes them via a character device (`/dev/button_led`). The addresses are based on the lightweight bridge base (0xFF200000) plus the offsets assigned in Platform Designer (0x0000 for button, 0x0010 for LED).

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
   - Log into the DE10-Nano's Linux system (via SSH or console).
   - Install kernel headers: `sudo apt-get install linux-headers-$(uname -r)` (Debian-based distros).

2. **Save Files**:
   - Save `button_led.c` and `Makefile` in a directory (e.g., `~/button_led_driver`).

3. **Compile**:
   - Run `make` to build `button_led.ko`.

4. **Load Module**:
   - Run `sudo insmod button_led.ko`.
   - Verify: `ls /dev/button_led`.
   - Check logs: `dmesg | grep button_led`.

5. **Unload (Optional)**:
   - Run `sudo rmmod button_led`.

## Application Code

### Overview
The user-space application polls the button state via `/dev/button_led` and toggles LED0 when KEY0 is pressed.

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
        usleep(100000);  // Poll every 100ms
    }

    close(fd);  // Unreachable due to infinite loop
    return 0;
}
```

### Application Instructions

1. **Compile**:
   - Save as `button_led_app.c`.
   - Run: `gcc button_led_app.c -o button_led_app`.

2. **Run**:
   - Run: `sudo ./button_led_app`.
   - Press KEY0 to see LED0 turn on; release to turn it off.

## Full Setup Workflow

1. **FPGA**:
   - Create the Quartus Lite project "DE10_nano_button_led" for the Cyclone V SoC (5CSEBA6U23I7).
   - Build the Platform Designer system, generate HDL, and create the top-level Verilog file.
   - Add files, assign pins, compile, and program the FPGA.

2. **Kernel**:
   - Compile and load the kernel module on the DE10-Nano's Linux system.

3. **Application**:
   - Compile and run the application to interact with the button and LED.

## Notes

- **Quartus Lite**: All IPs (HPS, PIO, Clock Source) are available in Quartus Lite.
- **Address Consistency**: The kernel module uses 0xFF200000 (button) and 0xFF200010 (LED), matching Platform Designer assignments offset from the lightweight bridge base.
- **Permissions**: Use sudo for the application due to `/dev/button_led` requiring root access.
- **Debugging**: Use `dmesg` for kernel logs and application printf outputs.
- **Reset**: Reset is tied high for simplicity. For robustness, connect KEY1 to `reset_reset_n`.

This setup ensures the HPS detects KEY0 presses and controls LED0 via the FPGA, starting from a fresh Quartus Lite project.
