# AMP Drone Flight Controller — DE10-Nano

Asymmetric Multiprocessing architecture for an autonomous plant-watering drone. Linux on Core 0, bare-metal on Core 1, deterministic I/O in FPGA fabric. No RTOS. Single daughter board plugs into DE10-Nano GPIO headers.

---

## Controller Responsibilities

### Core 0 — Linux (ARM Cortex-A9, 800 MHz)

**Role: Non-real-time supervisor. Handles everything that needs an OS.**

| Responsibility | Detail |
|---------------|--------|
| Mission planning | Plant queue management, waypoint generation, dock return logic |
| Camera processing | OV5640 frame capture via FPGA DMA, AprilTag detection (tag36h11) |
| WiFi telemetry | WILC3000 via HPS SPI1 (wlan0), MAVLink-style protocol, web dashboard |
| Flight logging | SD card write (CSV or binary), ring buffer from Core 1 telemetry |
| Parameter management | PID gains, sensor calibration, mission config — stored in `/etc/drone/` |
| Core 1 lifecycle | Loads bare-metal firmware to DDR, writes entry point, releases Core 1 from reset |
| IR beacon homing | Processes IR receiver bearing data from Core 1 telemetry, generates dock-return waypoints |
| Battery monitoring | Reads ADC voltage via FPGA registers, triggers return-to-dock on low battery |
| Pump sequencing | Sends pump-on/off commands to Core 1 via OCRAM mailbox |
| OTA updates | WiFi (wlan0) firmware upload for both Linux rootfs and Core 1 binary |

**Does NOT do:** Anything with hard timing requirements. No direct motor control, no IMU reads, no PID math.

**Linux kernel:** Existing 5.x kernel with `maxcpus=1 mem=992M` bootargs. UIO driver retained for FPGA register access from userspace (camera frame buffer, telemetry readout).

---

### Core 1 — Bare-Metal (ARM Cortex-A9, 800 MHz)

**Role: Deterministic real-time flight controller. Sub-6 us jitter. No OS, no scheduler, no interrupts from Linux.**

| Responsibility | Detail |
|---------------|--------|
| Attitude estimation | Madgwick filter at 8 kHz using VFP/NEON (accel + gyro + mag fusion) |
| Rate PID loop | Roll, pitch, yaw rate controllers at 8 kHz (125 us period) |
| Position hold loop | Altitude (baro + ToF down) at 400 Hz, XY (IR beacon bearing + ToF) at 50 Hz |
| Motor mixing | Quadcopter X-frame mixer: PID outputs → 4 individual motor commands (0-2047 DShot) |
| Failsafe state machine | Arm/disarm, lost-link timeout, low-battery return-to-dock, motor kill |
| FPGA register I/O | Reads IMU data, ToF distances, baro from FPGA Avalon-MM registers via LW-H2F bridge (`0xFF200000`) |
| Motor command output | Writes 4x DShot values to FPGA registers → FPGA DShot engine generates protocol |
| Sensor health | Monitors IMU data rate, ToF validity bits, baro staleness — triggers failsafe on sensor loss |
| Pump execution | Sets pump PWM duty in FPGA register when commanded by Core 0 |
| Telemetry output | Writes IMU/attitude/PID/motor state to OCRAM mailbox every 1 ms (1 kHz) |

**Does NOT do:** File I/O, networking, camera processing, complex algorithms. Pure control loop.

**Timing budget per 125 us PID iteration:**

| Step | Time |
|------|------|
| Read 9x IMU registers from FPGA | ~0.5 us |
| Read 6x ToF + baro registers | ~0.3 us |
| Madgwick attitude filter | ~5-8 us |
| PID controllers (roll, pitch, yaw, alt) | ~2-4 us |
| Motor mixer + write 4x motor registers | ~0.2 us |
| Write telemetry to OCRAM | ~0.1 us |
| **Total** | **~8-13 us (6-10% of budget)** |

---

### FPGA Fabric — Deterministic I/O (50 MHz clock)

**Role: Clock-cycle-precise I/O. Parallel sensor acquisition. Hardware safety.**

| Responsibility | Detail |
|---------------|--------|
| SPI IMU master | Auto-reads ICM-20948 every 125 us (8 kHz). Stores accel[3]+gyro[3]+mag[3] in registers. Asserts IRQ to Core 1 on data ready. |
| DShot600 engine | 4 independent state machines. Reads motor registers, generates DShot frames autonomously. ~200 LEs total. |
| I2C ToF controller | Round-robin reads 6x VL53L1X through TCA9548A mux. Stores distances in registers. Full scan ~200 ms. |
| I2C barometer | Reads BMP390 pressure+temperature. Shared I2C bus with ToF. |
| IR beacon receiver | Reads 4x TSOP38238 (38 kHz IR receivers). Measures per-channel signal strength via pulse width. Computes bearing to base station beacon. |
| DVP camera capture | Captures OV5640 frames via 8-bit parallel bus. Writes to DDR frame buffer via H2F bridge DMA. |
| Camera preprocessing | Grayscale conversion + adaptive threshold in pipeline (~1500 ALMs). Feeds Core 0 for AprilTag. |
| Hardware watchdog | Core 1 must write to watchdog register every 50 ms. Timeout → immediate motor kill (all DShot = 0). |
| Pump PWM | Generates PWM signal for MOSFET gate. Duty cycle set by register write. |
| Buzzer control | PWM for piezo buzzer (arm tone, error beep, low battery alarm). |
| Safety cutoff | If watchdog fires OR e-stop asserted → all motors off in <100 ns. |
| ~~ESP32 UART bridge~~ | Removed — WILC3000 connects directly to HPS SPI1 via LTC connector (J10). No FPGA resources needed. |
| ADC interface | Reads LTC2308 (onboard DE10-Nano) for battery voltage monitoring. |

---

## IR Beacon Homing System

No GPS — this is an indoor drone. Navigation uses IR homing beacon for coarse dock return + camera AprilTag for precision landing.

### How It Works

1. **Base station** emits modulated 940nm IR pulses (38 kHz carrier, 1 kHz burst pattern) from a high-power LED array. Omnidirectional emission via dome lens. Visible range: 10-15m indoors.
2. **Drone** has 4× TSOP38238 IR receivers (38 kHz bandpass) mounted at 90° intervals (front, left, right, rear) on the daughter board edges.
3. **FPGA** measures each receiver's output pulse width — stronger signal = wider pulse (AGC response of TSOP38238). Computes bearing to beacon from differential signal strength.
4. **Core 1** uses bearing + ToF obstacle avoidance to navigate toward dock.
5. **At <1m range**, camera takes over — AprilTag on dock provides sub-centimeter precision for pogo pad alignment.

### Dock Return Sequence

```
[Low battery or mission complete]
    → Core 0 sends RETURN_TO_DOCK command via OCRAM
    → Core 1 reads IR_BEARING register from FPGA
    → Core 1 yaws toward beacon (bearing → 0°)
    → Core 1 flies forward using ToF for obstacle avoidance
    → IR signal strength increases as drone approaches
    → At IR_FRONT > threshold (approx <1m):
        → Core 0 switches to AprilTag precision mode
        → Core 0 detects dock AprilTag, computes exact XYZ offset
        → Core 0 sends precision setpoints to Core 1
        → Core 1 descends onto pogo pads
        → Dock detect pin goes high → disarm
```

### Base Station Design (separate small PCB)

| Component | Part | Purpose |
|-----------|------|---------|
| IR LED array | 4× TSAL6200 (940nm, 150mW each) | Omnidirectional beacon |
| LED driver | TLC5917 (constant current, 8-ch) | 20mA per LED, SPI controlled |
| Modulation | 555 timer or ATtiny85 | 38 kHz carrier + 1 kHz burst envelope |
| Power | 5V USB-C or 12V barrel jack | From wall adapter |
| Dome lens | 60° diffuser cap per LED | Wide coverage |
| AprilTag | Printed tag36h11, 100mm, on flat surface | Precision landing target |
| Pogo pins | 4× P75-E2 spring-loaded | V+, GND, sense×2 for charging |
| Charge controller | TP5100 (2S-4S LiPo charger) | CC/CV charging via pogo pins |
| Water reservoir | Gravity-fed tank + solenoid valve | Refills peristaltic pump tube when docked |

**Base station BOM: ~$25** (PCB + components, excluding water tank)

### Drone-Side IR Receivers

4× TSOP38238 mounted on daughter board edges, angled 45° outward:

| Receiver | Position | GPIO Pin | Orientation |
|----------|----------|----------|-------------|
| IR_FRONT | Front edge center | GPIO1[12] | 0° (forward) |
| IR_LEFT | Left edge center | GPIO1[13] | 270° (left) |
| IR_RIGHT | Right edge center | GPIO1[14] | 90° (right) |
| IR_REAR | Rear edge center | GPIO1[15] | 180° (rear) |

Each TSOP38238 needs only VCC (3.3V), GND, and OUT (digital, active-low pulse). No level shifting needed. The FPGA measures pulse timing to extract signal strength.

---

## FPGA Register Map

Single Avalon-MM slave on LW-H2F bridge. Replaces calculator IP entirely.

**Base address: `0xFF200000`** (offset 0x000 in QSys, 512 bytes, 128 registers)

| Offset | Register | R/W | Accessed By | Description |
|--------|----------|-----|-------------|-------------|
| **Control** | | | | |
| 0x000 | CONTROL | R/W | Core 1 | [0]=arm, [1]=kill, [7:4]=flight_mode |
| 0x004 | STATUS | R | Both | [0]=armed, [1]=flying, [2]=failsafe, [3]=docked, [4]=core1_alive |
| 0x008 | ERROR_FLAGS | R | Both | [0]=imu_timeout, [1]=watchdog, [2]=estop, [3]=low_batt |
| 0x00C | WATCHDOG | W | Core 1 | Write any value to pet. 50 ms timeout → motor kill. |
| **IMU (FPGA → Core 1)** | | | | |
| 0x010 | ACCEL_X | R | Core 1 | 16-bit signed, raw |
| 0x014 | ACCEL_Y | R | Core 1 | |
| 0x018 | ACCEL_Z | R | Core 1 | |
| 0x01C | GYRO_X | R | Core 1 | 16-bit signed, raw |
| 0x020 | GYRO_Y | R | Core 1 | |
| 0x024 | GYRO_Z | R | Core 1 | |
| 0x028 | MAG_X | R | Core 1 | 16-bit signed, raw |
| 0x02C | MAG_Y | R | Core 1 | |
| 0x030 | MAG_Z | R | Core 1 | |
| 0x034 | IMU_STATUS | R | Core 1 | [0]=data_ready (clears on read), [15:8]=sample_count |
| **Motors (Core 1 → FPGA)** | | | | |
| 0x040 | MOTOR_FL | R/W | Core 1 | DShot value 0-2047 (front-left) |
| 0x044 | MOTOR_FR | R/W | Core 1 | front-right |
| 0x048 | MOTOR_RL | R/W | Core 1 | rear-left |
| 0x04C | MOTOR_RR | R/W | Core 1 | rear-right |
| 0x050 | MOTOR_STATUS | R | Core 1 | [3:0]=telemetry valid per motor |
| **ToF (FPGA → Core 1)** | | | | |
| 0x060 | TOF_DOWN | R | Core 1 | Distance mm, 16-bit (altitude) |
| 0x064 | TOF_UP | R | Core 1 | Distance mm (ceiling) |
| 0x068 | TOF_FRONT | R | Core 1 | |
| 0x06C | TOF_BACK | R | Core 1 | |
| 0x070 | TOF_LEFT | R | Core 1 | |
| 0x074 | TOF_RIGHT | R | Core 1 | |
| 0x078 | TOF_STATUS | R | Core 1 | [5:0]=valid bits per sensor |
| **Barometer (FPGA → Core 1)** | | | | |
| 0x080 | BARO_PRESS | R | Core 1 | 24-bit raw pressure |
| 0x084 | BARO_TEMP | R | Core 1 | 24-bit raw temperature |
| 0x088 | BARO_STATUS | R | Core 1 | [0]=data_ready |
| **IR Beacon (FPGA → Core 1)** | | | | |
| 0x090 | IR_FRONT | R | Core 1 | Front receiver signal strength (16-bit, 0=no signal) |
| 0x094 | IR_LEFT | R | Core 1 | Left receiver signal strength |
| 0x098 | IR_RIGHT | R | Core 1 | Right receiver signal strength |
| 0x09C | IR_REAR | R | Core 1 | Rear receiver signal strength |
| 0x0A0 | IR_BEARING | R | Core 1 | Computed bearing to beacon (signed degrees × 100, FPGA calculated) |
| 0x0A4 | IR_STATUS | R | Core 1 | [0]=beacon_detected, [3:1]=strongest_channel, [7:4]=signal_quality |
| **Camera (FPGA → Core 0)** | | | | |
| 0x0B0 | CAM_FRAME_ADDR | R/W | Core 0 | DDR frame buffer address for DMA |
| 0x0B4 | CAM_CONTROL | R/W | Core 0 | [0]=capture_enable, [1]=frame_done (clears on read) |
| 0x0B8 | CAM_CONFIG | R/W | Core 0 | [15:0]=width, [31:16]=height |
| **Pump / Buzzer** | | | | |
| 0x0C0 | PUMP_CONTROL | R/W | Core 1 | [0]=enable, [15:8]=PWM duty (0-255) |
| 0x0C4 | BUZZER_CONTROL | R/W | Core 1 | [0]=enable, [15:8]=frequency divider |
| **Battery (FPGA → Both)** | | | | |
| 0x0D0 | BATT_VOLTAGE | R | Both | ADC reading, 12-bit (from LTC2308 CH0) |
| 0x0D4 | BATT_CURRENT | R | Both | INA219 current reading (via I2C, shared bus) |
| ~~**ESP32 WiFi UART bridge**~~ | | | | *(Removed — WILC3000 uses HPS SPI1 directly, no FPGA registers)* |
| **Misc** | | | | |
| 0x0F0 | GPIO_OUT | R/W | Both | [3:0]=status LEDs, [4]=arm_switch_read, [5]=estop_read, [6]=dock_detect |
| 0x0F4 | GPIO_IN | R | Both | Raw input pin states |
| 0x0FC | VERSION | R | Both | 0x00020001 |

---

## Memory Architecture

### DDR3 Partitioning (1 GB)

| Region | Address Range | Size | Owner |
|--------|--------------|------|-------|
| Linux kernel + userspace | `0x00000000` - `0x3DFFFFFF` | 992 MB | Core 0 |
| Shared IPC | `0x3E000000` - `0x3E0FFFFF` | 1 MB | Both (non-cacheable) |
| Core 1 firmware + heap + stack | `0x3E100000` - `0x3FFFFFFF` | 31 MB | Core 1 |

### OCRAM IPC Layout (64 KB at `0xFFFF0000`)

Single-cycle access. Linux does not touch OCRAM. All regions non-cacheable in both cores' MMUs.

| Address | Size | Direction | Content |
|---------|------|-----------|---------|
| `0xFFFF0000` | 256 B | Core 0 → Core 1 | **Command mailbox**: setpoint (roll/pitch/yaw/thrust), flight mode, pump cmd |
| `0xFFFF0100` | 256 B | Core 1 → Core 0 | **Telemetry mailbox**: attitude quaternion, PID outputs, motor values, sensor health |
| `0xFFFF0200` | 512 B | Core 1 → Core 0 | **Sensor snapshot**: latest raw IMU, ToF, baro values |
| `0xFFFF0400` | 4 KB | Core 1 → Core 0 | **Flight log ring buffer**: timestamped entries, Core 0 drains to SD |
| `0xFFFF1400` | 4 KB | Core 0 → Core 1 | **Mission waypoints**: plant positions, dock location |
| `0xFFFF2400` | ~55 KB | — | Reserved |

**Signaling:** SGI #1 (Core 0 → Core 1: new command), SGI #2 (Core 1 → Core 0: telemetry ready).

Lock-free single-producer/single-consumer ring buffers. No mutexes needed.

### DDR Shared Region (`0x3E000000`, 1 MB)

| Offset | Size | Purpose |
|--------|------|---------|
| 0x000000 | 512 KB | Camera frame buffer (720p grayscale = 921,600 bytes, double-buffered = 2 frames) |
| 0x080000 | 256 KB | AprilTag detection results |
| 0x0C0000 | 256 KB | Extended flight log (bulk, Core 0 writes to SD) |

---

## AMP Boot Sequence

### 1. Power On → U-Boot (unchanged from existing system)
- Preloader (SPL) initializes DDR3, clocks
- U-Boot loads FPGA bitstream (`fpga load`), enables bridges (`bridge enable`)
- U-Boot loads Linux kernel with bootargs:
  ```
  mem=992M maxcpus=1 uio_pdrv_genirq.of_id=generic-uio earlyprintk
  ```

### 2. Linux Boot on Core 0
- Kernel starts on Core 0 only (Core 1 held in reset by hardware)
- UIO driver binds to flight controller FPGA IP
- Systemd starts `core1-loader.service`

### 3. Core 1 Loader (`core1_loader` application)
```c
// Executed on Core 0 as a Linux userspace application
// 1. Load bare-metal binary from SD card to reserved DDR
memcpy((void*)0x3E100000, firmware_binary, firmware_size);

// 2. Write entry point to cpu1startaddr register
*(volatile uint32_t*)0xFFD080C4 = 0x3E100000;

// 3. Release Core 1 from reset (clear bit 1 of mpumodrst)
uint32_t val = *(volatile uint32_t*)0xFFD05010;
val &= ~(1 << 1);
*(volatile uint32_t*)0xFFD05010 = val;

// Core 1 is now running bare-metal firmware
```

### 4. Core 1 Bare-Metal Startup
```asm
.global _start
_start:
    CPSID   if                          @ Disable interrupts
    LDR     sp, =0x3FFFFFF0             @ Stack at top of Core 1 DDR region

    /* Leave SCU coherency — Core 1 manages its own caches */
    MRC     p15, 0, r0, c1, c0, 1      @ Read ACTLR
    BIC     r0, r0, #(1 << 6)          @ Clear SMP bit
    MCR     p15, 0, r0, c1, c0, 1

    /* Enable VFP/NEON for floating-point PID math */
    MRC     p15, 0, r0, c1, c0, 2
    ORR     r0, r0, #(0xF << 20)       @ Enable CP10 + CP11
    MCR     p15, 0, r0, c1, c0, 2
    ISB
    VMRS    r0, FPEXC
    ORR     r0, r0, #(1 << 30)         @ Set EN bit
    VMSR    FPEXC, r0

    /* Set up MMU page tables:
       0x00000000-0x3DFFFFFF  → Not mapped (Linux territory)
       0x3E000000-0x3E0FFFFF  → Normal, Non-cacheable (shared IPC DDR)
       0x3E100000-0x3FFFFFFF  → Normal, Cacheable (Core 1 firmware)
       0xFF200000-0xFF3FFFFF  → Device (FPGA LW bridge)
       0xFFD00000-0xFFDFFFFF  → Device (System/Reset manager)
       0xFFFEC000-0xFFFEFFFF  → Device (SCU, GIC, L2 cache)
       0xFFFF0000-0xFFFFFFFF  → Normal, Non-cacheable (OCRAM IPC) */
    BL      mmu_init

    /* Configure GIC for Core 1 */
    BL      gic_init
    /* Route FPGA IRQ 0 (IMU data ready, GIC SPI 72) to Core 1 */
    /* Route private timer (PPI 29) for 8 kHz tick */

    CPSIE   if                          @ Enable interrupts
    BL      core1_main                  @ Jump to C flight controller
    B       .                           @ Should never return
```

### 5. Core 1 Main Loop
```c
void core1_main(void) {
    pid_init(&pid_roll);
    pid_init(&pid_pitch);
    pid_init(&pid_yaw);
    pid_init(&pid_alt);
    madgwick_init(&ahrs);

    // Configure private timer for 8 kHz (125 us)
    private_timer_init(TIMER_FREQ_HZ / 8000);

    while (1) {
        // Wait for IMU data ready IRQ from FPGA (SPI 72)
        // or private timer tick — whichever comes first
        wfi();

        // 1. Read sensors from FPGA registers
        imu_read(&imu);           // 9 registers at 0xFF200010
        tof_read(&tof);           // 6 registers at 0xFF200060
        baro_read(&baro);         // 2 registers at 0xFF200080

        // 2. Attitude estimation
        madgwick_update(&ahrs, &imu, dt);

        // 3. Read setpoints from OCRAM command mailbox
        cmd_read(&setpoint);      // 0xFFFF0000

        // 4. PID controllers
        float motor_fl, motor_fr, motor_rl, motor_rr;
        pid_update(&pid_roll,  ahrs.roll_rate,  setpoint.roll_rate);
        pid_update(&pid_pitch, ahrs.pitch_rate, setpoint.pitch_rate);
        pid_update(&pid_yaw,   ahrs.yaw_rate,   setpoint.yaw_rate);
        pid_update(&pid_alt,   baro.altitude,    setpoint.altitude);
        motor_mix(pid_roll.out, pid_pitch.out, pid_yaw.out, pid_alt.out,
                  &motor_fl, &motor_fr, &motor_rl, &motor_rr);

        // 5. Write motor commands to FPGA
        FPGA_WRITE(MOTOR_FL, (uint32_t)motor_fl);
        FPGA_WRITE(MOTOR_FR, (uint32_t)motor_fr);
        FPGA_WRITE(MOTOR_RL, (uint32_t)motor_rl);
        FPGA_WRITE(MOTOR_RR, (uint32_t)motor_rr);

        // 6. Pet watchdog
        FPGA_WRITE(WATCHDOG, 1);

        // 7. Write telemetry to OCRAM (every 8th iteration = 1 kHz)
        if (++telem_div >= 8) {
            telem_write(&ahrs, &pid_roll, &pid_pitch, &pid_yaw, &imu);
            sgi_send(2, CPU0);  // Signal Core 0
            telem_div = 0;
        }
    }
}
```

---

## GIC Interrupt Routing

| Interrupt | GIC ID | Target | Purpose |
|-----------|--------|--------|---------|
| FPGA IRQ 0 (IMU data ready) | SPI 72 | **Core 1** | Triggers PID iteration |
| FPGA IRQ 1 (camera frame done) | SPI 73 | **Core 0** | AprilTag processing |
| FPGA IRQ 2 (watchdog timeout) | SPI 74 | **Core 1** | Emergency motor kill |
| Core 1 private timer | PPI 29 | **Core 1** | 8 kHz backup tick |
| SGI #1 | SGI 1 | **Core 1** | New command from Linux |
| SGI #2 | SGI 2 | **Core 0** | Telemetry ready |
| Ethernet | SPI 152 | **Core 0** | Linux networking |
| UART0 | SPI 194 | **Core 0** | Serial console |
| USB | SPI 189 | **Core 0** | (spare — WiFi via WILC3000 on HPS SPI1) |

Route via `GICD_ITARGETSRn` at `0xFFFED800`: write `0x01` for Core 0, `0x02` for Core 1.

---

## Device Tree Changes

```dts
/* socfpga_cyclone5_de10_nano.dts — modified for AMP */

/ {
    chosen {
        bootargs = "earlyprintk uio_pdrv_genirq.of_id=generic-uio mem=992M maxcpus=1";
    };

    memory {
        device_type = "memory";
        reg = <0x00000000 0x3E000000>;  /* 992 MB for Linux */
    };

    reserved-memory {
        #address-cells = <1>;
        #size-cells = <1>;
        ranges;

        amp_shared: shared@3e000000 {
            compatible = "shared-dma-pool";
            reg = <0x3E000000 0x00100000>;
            no-map;
        };

        amp_core1: core1@3e100000 {
            reg = <0x3E100000 0x01F00000>;
            no-map;
        };
    };
};

/* FPGA bridges — unchanged, already enabled */
&fpga_bridge0 { status = "okay"; bridge-enable = <1>; };
&fpga_bridge1 { status = "okay"; bridge-enable = <1>; };

/* Flight controller FPGA IP replaces calculator */
&soc {
    flight_ctrl0: flight-controller@ff200000 {
        compatible = "generic-uio";
        reg = <0xff200000 0x200>;       /* 512 bytes */
        interrupts = <0 73 4>;          /* Camera frame IRQ → Core 0 only */
        interrupt-parent = <&intc>;
        linux,uio-name = "fpga-flight-controller";
        status = "okay";
    };
};
```

---

## Boot Script Changes (`create_sd_image.sh`)

```bash
# In boot.scr generation, modify bootargs:
setenv bootargs "console=ttyS0,115200 root=/dev/mmcblk0p2 rw rootwait \
    mem=992M maxcpus=1 uio_pdrv_genirq.of_id=generic-uio earlyprintk"
```

---

## Codebase Modifications

The existing calculator IP and its infrastructure are replaced entirely. No backwards compatibility.

| Current File | Action | New File |
|-------------|--------|----------|
| `FPGA/ip/custom/calculator/*` | **Delete** | `FPGA/ip/custom/flight_controller/*` |
| `calculator_registers.v` | Replace | `fc_registers.v` (128 registers, 512 bytes) |
| `calculator_core.v` | Replace | `dshot_engine.v`, `spi_imu_master.v`, `i2c_tof_ctrl.v`, `dvp_capture.v`, `hw_watchdog.v`, `ir_beacon_rx.v`, `buzzer_pwm.v`, `pump_pwm.v`, `adc_reader.v` |
| `calculator_avalon_mm.v` | Replace | `fc_avalon_mm.v` (wider address, same pattern) |
| `calculator_hw.tcl` | Replace | `flight_controller_hw.tcl` |
| `HPS/drivers/calculator/*` | **Delete** | `HPS/drivers/flight_controller/*` (UIO driver for Core 0) |
| `HPS/applications/calculator_demo/` | **Delete** | `HPS/applications/core1_loader/` |
| `HPS/applications/calculator_test/` | **Delete** | `HPS/applications/flight_telemetry/` |
| `HPS/applications/boot_led/` | **Delete** | — (LEDs controlled by FPGA GPIO_OUT register) |
| `FPGA/quartus/qsys/soc_system.qsys` | Modify | Replace calculator_0 with flight_controller_0 |
| `FPGA/hdl/DE10_NANO_SoC_GHRD.v` | Modify | Add GPIO0/GPIO1 port connections to flight controller conduits |
| `HPS/linux_image/kernel/dts/*.dts` | Modify | Add reserved-memory, change bootargs, replace UIO node |
| `HPS/linux_image/build/create_sd_image.sh` | Modify | Add `maxcpus=1 mem=992M` to boot.scr |
| — | **New** | `HPS/bare_metal/` — Core 1 firmware (startup.S, main.c, pid.c, madgwick.c, hal.c, ipc.c) |
| — | **New** | `HPS/bare_metal/Makefile` — ARM bare-metal cross-compile (arm-none-eabi-gcc) |
| — | **New** | `HPS/bare_metal/linker.ld` — Link at 0x3E100000 |

---

## FPGA Resource Budget

| Module | ALMs | DSP | BRAM (M10K) | Notes |
|--------|------|-----|-------------|-------|
| DShot600 engine (4 ch) | ~200 | 0 | 0 | 4 independent state machines |
| SPI IMU master + FIFO | ~500 | 0 | 2 | 7 MHz SPI, 8 kHz auto-trigger |
| I2C ToF controller | ~400 | 0 | 1 | Soft I2C master + mux sequencer |
| I2C barometer | ~200 | 0 | 1 | Shared bus, interleaved with ToF |
| IR beacon receiver | ~200 | 0 | 1 | 4-ch 38 kHz demod, signal strength + bearing |
| DVP camera capture | ~1,000 | 0 | 20 | 8-bit parallel, line buffers |
| Grayscale + threshold | ~500 | 0 | 10 | Pipeline preprocessing |
| H2F DMA controller | ~800 | 0 | 4 | Frame buffer write to DDR |
| Hardware watchdog | ~50 | 0 | 0 | 50 ms timeout counter |
| Pump PWM | ~30 | 0 | 0 | |
| Buzzer PWM | ~30 | 0 | 0 | |
| ADC reader (LTC2308) | ~200 | 0 | 0 | SPI master for onboard ADC |
| ~~ESP32 UART bridge~~ | ~~150~~ | ~~0~~ | ~~2~~ | Removed — WILC3000 on HPS SPI1 |
| Avalon-MM registers | ~300 | 0 | 2 | 128 registers, arbitration |
| GPIO / LED control | ~50 | 0 | 0 | |
| **Total** | **~4,410** | **0** | **41** | |
| **Available (5CSEBA6)** | **41,910** | **112** | **553** | |
| **Utilization** | **~10.5%** | **0%** | **~7.4%** | |

---

## Daughter Board PCB

See [daughter_board_pcb_design.md](daughter_board_pcb_design.md) for full schematic-level detail. See [drone_frame_and_propulsion.md](drone_frame_and_propulsion.md) for PCB frame, motors, ESCs, battery, and BMS. Summary:

### Board Specifications
- **Size**: 85 × 100 mm, 4-layer PCB
- **Weight**: ~42g (PCB + components, excluding cables)
- **Connects via**: 2x 2×20 female headers (GPIO0 + GPIO1)
- **Cost**: ~$48.50 per board (PCB fab + components at JLCPCB)

### Subsystem Summary

| Section | Key Components | Connection |
|---------|---------------|------------|
| **Motor drivers** | 4× 74LVC1G17 Schmitt buffer + PESD5V0S1BL TVS, 4× JST-XH 3-pin ESC connectors | GPIO0[16-19] |
| **IMU** | ICM-20948 (QFN-24) + SN74AVC4T245 level shifter (3.3V↔1.8V) + TPS7A2018 1.8V LDO | GPIO1[0-4] SPI |
| **Camera** | 24-pin 0.5mm FPC connector + TPS7A2028 2.8V + TPS7A2015 1.5V LDOs | GPIO0[0-15] DVP |
| **ToF hub** | TCA9548A mux + 6× JST-SH 4-pin + 6× XSHUT GPIO lines | GPIO1[5-15] I2C |
| **Barometer** | BMP390 (LGA-10), shared I2C bus, 1mm pressure vent hole | GPIO1[5-6] shared |
| **IR beacon RX** | 4× TSOP38238 (38 kHz IR receivers) at 90° spacing + signal conditioning | GPIO1[12-15] digital |
| **WiFi/BLE** | ATWILC3000-MR110UB via HPS SPI1 + LTC bridge cable | LTC connector (J10) |
| **Power** | XT60 in → SI4435DDY reverse-polarity MOSFET → SMBJ20A TVS → TPS54560 buck (5V/5A) → AP2112K 3.3V LDO, INA219 current monitor | Battery → barrel jack |
| **Pump** | AO3400A N-MOSFET + SS14 Schottky + JST-XH 2-pin | GPIO0[20] PWM |
| **Safety** | Arm switch, e-stop (NC fail-safe), dock detect with RC debounce | GPIO0[22-24] |
| **Status** | 4× LEDs (power/armed/beacon/error) + piezo buzzer driver | GPIO0[25-28] + GPIO0[21] |
| **Charging** | 4× pogo pads on bottom (V+, GND, sense×2) | GPIO0[30-31] |

### Connector List

| Connector | Type | Qty | Purpose |
|-----------|------|-----|---------|
| XT60 male | PCB mount | 1 | Battery input (14.8V) |
| JST-XH 3-pin | Through-hole | 4 | ESC signal + power sense |
| JST-SH 4-pin | SMD | 6 | VL53L1X ToF sensor cables |
| JST-SH 3-pin | SMD | 4 | TSOP38238 IR receivers (VCC, GND, OUT) |
| JST-XH 2-pin | Through-hole | 1 | Water pump |
| FPC 24-pin 0.5mm | SMD | 1 | OV5640 camera module |
| 2×20 female 2.54mm | Through-hole | 2 | DE10-Nano GPIO0 + GPIO1 |
| Barrel jack pigtail | Wire | 1 | 5V to DE10-Nano |
| 2-pin header | Through-hole | 1 | Arm switch |
| 2-pin header | Through-hole | 1 | Emergency stop |
| JST-SH 6-pin | SMD | 1 | WILC3000 LTC bridge cable |
| Pogo pads | SMD copper | 4 | Charging dock interface |

---

## Total BOM Cost

| Category | Cost |
|----------|------|
| DE10-Nano dev board | ~$130 |
| Daughter board PCB + components | ~$49 |
| 4× BLHeli_32 ESC (30A) | ~$60 |
| 4× BLDC motor (2212 920KV) | ~$40 |
| OV5640 camera module | ~$12 |
| 6× VL53L1X breakout (Pololu) | ~$72 |
| 4× TSOP38238 IR receivers | ~$4 |
| IR beacon base station (IR LEDs + driver PCB) | ~$10 |
| Peristaltic pump + tubing | ~$15 |
| 4S LiPo 1300mAh | ~$25 |
| 450mm drone frame | ~$30 |
| Propellers (5045, 2 sets) | ~$8 |
| Wiring, connectors, standoffs | ~$15 |
| **Total** | **~$470** |

---

## Implementation Order

1. **Daughter board PCB**: Design in KiCad, fab at JLCPCB (2 weeks turnaround)
2. **FPGA IP**: `generate-ip-framework.sh flight_controller` → implement all modules
3. **Device tree + boot script**: Add reserved-memory, maxcpus=1, replace calculator UIO node
4. **Core 1 firmware**: Bare-metal startup assembly → PID loop in C → OCRAM IPC
5. **Core 1 loader**: Linux app that loads firmware and releases Core 1
6. **Core 0 applications**: Telemetry logger, camera/AprilTag processor, mission planner
7. **Bench test**: Single motor + IMU on daughter board, verify 8 kHz loop on oscilloscope
8. **Integration**: Mount on frame, all sensors, first hover test
9. **Mission logic**: Plant watering autonomy, dock landing, charge management

---

## Verification

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Core 1 boots bare-metal | Serial debug output via OCRAM → Core 0 → UART | "Core 1 alive" message |
| 8 kHz PID loop | Toggle GPIO pin at loop start/end, measure on scope | 125 us ± 6 us period |
| IMU data valid | Read ACCEL_Z while board is flat | ~16384 (1g at ±2g range) |
| DShot output | Scope on ESC signal line | 600 kbit/s, correct frame format |
| Motor spin test | Arm + send DShot 100 | Motor spins slowly, all 4 matched |
| ToF sensors | Hold hand at known distance | Reads within ±20mm |
| Watchdog kill | Stop petting watchdog | Motors cut within 50 ms |
| E-stop | Press e-stop button | Immediate motor kill, all DShot = 0 |
| IPC latency | Timestamp command in Core 0, measure arrival in Core 1 | <1 us (OCRAM) |
| IR beacon homing | Point beacon at drone, read IR_BEARING register | Bearing tracks beacon ±10° |
| IR beacon range | Move beacon 1m → 5m → 10m | Signal strength decreases monotonically |
| Camera frame | Capture single frame, dump to SD | Valid 720p grayscale image |
| WiFi link | Connect to WILC3000 AP (wlan0), request telemetry | JSON telemetry at 10 Hz |
| Dock landing | Fly to beacon, switch to AprilTag at <1m | Lands on pogo pads within ±2cm |
