# DE10-Nano Plant-Watering Drone Flight Controller -- Daughter Board PCB Design

## Overview

This document specifies a single combined daughter board that plugs into both GPIO0 (JP1) and GPIO1 (JP7) headers of the DE10-Nano development board. The board implements an autonomous plant-watering drone flight controller with 11 subsystems.

**Target frame**: 450mm quadcopter
**Board form factor**: Single PCB, approximately 85mm x 100mm
**Layer count**: 4-layer (see Section 11)
**Estimated weight**: 35-42g (bare PCB + components, excluding connectors/cables)

---

## DE10-Nano GPIO Pin Reference

The DE10-Nano Cyclone V SoC board has two 2x20 GPIO headers, all at 3.3V LVTTL:

### GPIO0 (JP1) -- 36 I/O pins + VCC(3.3V)/VCC(5V)/GND

| Header Pin | FPGA Pin | Signal Name    | This Design Assignment          |
|-----------|----------|----------------|----------------------------------|
| 1         | PIN_V12  | GPIO_0[0]      | CAM_D0 (OV5640 DVP data bit 0)  |
| 2         | PIN_E8   | GPIO_0[1]      | CAM_D1                           |
| 3         | PIN_W12  | GPIO_0[2]      | CAM_D2                           |
| 4         | PIN_D11  | GPIO_0[3]      | CAM_D3                           |
| 5         | PIN_D8   | GPIO_0[4]      | CAM_D4                           |
| 6         | PIN_AH13 | GPIO_0[5]      | CAM_D5                           |
| 7         | PIN_AF7  | GPIO_0[6]      | CAM_D6                           |
| 8         | PIN_AH14 | GPIO_0[7]      | CAM_D7                           |
| 9         | PIN_AF4  | GPIO_0[8]      | CAM_PCLK (pixel clock)           |
| 10        | PIN_AH3  | GPIO_0[9]      | CAM_VSYNC                        |
| 11        | PIN_AD5  | GPIO_0[10]     | CAM_HSYNC (HREF)                 |
| 12        | PIN_AG14 | GPIO_0[11]     | CAM_XCLK (24MHz from FPGA PLL)  |
| 13        | PIN_AE11 | GPIO_0[12]     | CAM_SIOC (SCCB/I2C clock)       |
| 14        | PIN_AG11 | GPIO_0[13]     | CAM_SIOD (SCCB/I2C data)        |
| 15        | PIN_AH9  | GPIO_0[14]     | CAM_PWDN (power down)            |
| 16        | PIN_AG16 | GPIO_0[15]     | CAM_RESET                        |
| 17        | PIN_AD7  | GPIO_0[16]     | DSHOT_CH1 (Motor 1)              |
| 18        | PIN_AE7  | GPIO_0[17]     | DSHOT_CH2 (Motor 2)              |
| 19        | PIN_AC7  | GPIO_0[18]     | DSHOT_CH3 (Motor 3)              |
| 20        | PIN_AD5  | GPIO_0[19]     | DSHOT_CH4 (Motor 4)              |
| 21        | PIN_AE4  | GPIO_0[20]     | PUMP_PWM (water pump)            |
| 22        | PIN_AE3  | GPIO_0[21]     | BUZZER_PWM                       |
| 23        | PIN_AD2  | GPIO_0[22]     | ARM_SWITCH_IN                    |
| 24        | PIN_AC1  | GPIO_0[23]     | ESTOP_IN (emergency stop)        |
| 25        | PIN_AB3  | GPIO_0[24]     | DOCK_DETECT_IN                   |
| 26        | PIN_AC3  | GPIO_0[25]     | STATUS_LED_POWER                 |
| 27        | PIN_AD1  | GPIO_0[26]     | STATUS_LED_ARMED                 |
| 28        | PIN_AC2  | GPIO_0[27]     | STATUS_LED_BEACON                |
| 29-30     |          | VCC5/VCC3P3    | Power pins                        |
| 31-36     |          | GPIO_0[28-33]  | STATUS_LED_ERROR, CHARGE_SENSE1/2, spare |

### GPIO1 (JP7) -- 36 I/O pins + VCC(3.3V)/VCC(5V)/GND

| Header Pin | FPGA Pin | Signal Name    | This Design Assignment          |
|-----------|----------|----------------|----------------------------------|
| 1         | PIN_Y15  | GPIO_1[0]      | IMU_SPI_SCLK                     |
| 2         | PIN_AC24 | GPIO_1[1]      | IMU_SPI_MOSI                     |
| 3         | PIN_AA15 | GPIO_1[2]      | IMU_SPI_MISO                     |
| 4         | PIN_AD26 | GPIO_1[3]      | IMU_SPI_CS_N                     |
| 5         | PIN_AG28 | GPIO_1[4]      | IMU_INT                           |
| 6         | PIN_AF28 | GPIO_1[5]      | TOF_I2C_SCL (to TCA9548A)       |
| 7         | PIN_AE25 | GPIO_1[6]      | TOF_I2C_SDA (to TCA9548A)       |
| 8         | PIN_AC22 | GPIO_1[7]      | TOF_MUX_RESET_N                  |
| 9         | PIN_AE22 | GPIO_1[8]      | TOF_XSHUT_0                      |
| 10        | PIN_AF21 | GPIO_1[9]      | TOF_XSHUT_1                      |
| 11        | PIN_AG20 | GPIO_1[10]     | TOF_XSHUT_2                      |
| 12        | PIN_AH20 | GPIO_1[11]     | TOF_XSHUT_3                      |
| 13        | PIN_AH18 | GPIO_1[12]     | IR_RX_FRONT (TSOP38238 front)   |
| 14        | PIN_AH19 | GPIO_1[13]     | IR_RX_LEFT (TSOP38238 left)     |
| 15        | PIN_AG18 | GPIO_1[14]     | IR_RX_RIGHT (TSOP38238 right)    |
| 16        | PIN_AH17 | GPIO_1[15]     | IR_RX_REAR (TSOP38238 rear)      |
| 17        | PIN_AG15 | GPIO_1[16]     | INA219_ALERT                     |
| 18-36     |          | GPIO_1[17-35]  | Spare / future expansion         |

### Arduino Header ADC (directly on DE10-Nano)

The DE10-Nano has an LTC2308 12-bit ADC accessible via SPI from the FPGA. ADC_CH0-CH7 are on the Arduino analog header. We use ADC_CH0 for battery voltage monitoring via a resistor divider routed to the Arduino header's A0 pin.

---

## 1. Motor Driver Section (4x BLDC via External ESC)

### Architecture Decision

External ESCs are used (standard for drones). The daughter board provides DShot600 signal conditioning, connectors, and protection. ESCs connect via 3-pin cables (signal, VCC, GND).

### DShot600 Protocol Requirements

DShot600 runs at 600 kbit/s. Each bit period is 1.67 us. A "1" bit is a pulse high for 1.25 us, a "0" bit is high for 0.625 us. The FPGA generates these timing-critical signals natively -- no CPU involvement.

### Circuit Design

```
FPGA GPIO_0[16..19] (3.3V) --> 74LVC1G17 Schmitt trigger buffer (per channel) --> ESC signal pin
                                     |
                                PESD5V0S1BL (TVS diode, per channel)
                                     |
                                    GND
```

**Level shifting**: Not required. DShot600 ESCs accept 3.3V logic directly. The 74LVC1G17 single Schmitt-trigger buffer provides clean edge shaping for the timing-critical DShot waveforms, driving up to 32mA at 3.3V.

**ESC connectors**: 4x JST-XH 3-pin (2.54mm pitch) -- Signal, VCC(unused), GND.

### Component List

| Ref   | Part Number          | Description                    | Package    | Qty | Unit Price | Supplier  |
|-------|---------------------|--------------------------------|------------|-----|-----------|-----------|
| U1-U4 | 74LVC1G17GW,125     | Single Schmitt buffer          | SOT-353    | 4   | $0.22     | Mouser    |
| D1-D4 | PESD5V0S1BL,315     | 5V TVS diode                   | SOD-882    | 4   | $0.12     | Mouser    |
| C1-C4 | GRM155R71C104KA01D  | 100nF 0402 MLCC (buffer Vcc)   | 0402       | 4   | $0.02     | DigiKey   |
| J1-J4 | B3B-XH-A(LF)(SN)   | JST-XH 3-pin header            | Through-hole| 4   | $0.18     | DigiKey   |

### PCB Layout

- Route DShot signal traces as 50-ohm controlled impedance (not strictly necessary at 600kHz, but good practice).
- Place TVS diodes within 3mm of connector pads.
- Place buffer decoupling capacitor within 2mm of buffer VCC pin.
- Keep motor signal traces away from IMU/barometer analog sections -- minimum 10mm separation.
- ESC connectors along one board edge for clean cable routing.

**Subsystem cost**: ~$2.20

---

## 2. IMU -- ICM-20948 (9-axis: 3-axis gyro + 3-axis accel + 3-axis magnetometer)

### Critical Design Challenge

The ICM-20948 VDDIO operates at **1.71V-1.95V** (nominal 1.8V), while DE10-Nano GPIO is 3.3V LVTTL. A bidirectional level shifter is required for the SPI bus.

### Circuit Design

```
                    +-------------------+
    3.3V ---|>|--- | TXS0104E          |
    (from header)  |  OE ---> 3.3V     |        +------------------+
                   |  VCCA = 1.8V      |        |  ICM-20948       |
    GPIO_1[0] <--->|  A1 <---> B1      |<------>|  SPI_CLK         |
    GPIO_1[1] <--->|  A2 <---> B2      |<------>|  SPI_MOSI (SDI)  |
    GPIO_1[2] <--->|  A3 <---> B3      |<------>|  SPI_MISO (SDO)  |
    GPIO_1[3] <--->|  A4 <---> B4      |<------>|  SPI_CS_N (nCS)  |
                   |  VCCB = 3.3V      |        |                  |
                   +-------------------+        |  INT1 --> GPIO_1[4] (open drain, 10k pull-up to 3.3V)
                                                |  VDD  = 1.8V     |
                                                |  VDDIO = 1.8V    |
                                                |  GND             |
                                                +------------------+
```

**Why TXS0104E instead of TXB0104**: The TXB0104 uses auto-direction sensing and can be confused by SPI's fast edges and the MISO line's tristate behavior. The TXS0104E is a **push-pull** level translator better suited for SPI where direction is known. However, for SPI the best approach is actually a **unidirectional** solution:

**Revised approach -- discrete level shifting for SPI**:

- SCLK, MOSI, CS_N: FPGA drives (3.3V to 1.8V) -- use **3x 74LVC1G07** (open-drain buffer) with 2.2k pull-up to 1.8V on each line. Or more simply, use resistor dividers (4.7k + 6.8k gives 1.8V from 3.3V, but too slow for SPI at 7MHz).

**Final choice: SN74AVC4T245** -- a 4-bit dual-supply bus transceiver. Port A = 1.8V, Port B = 3.3V. Supports up to 380 Mbps, auto-direction per pin or direction-controlled. Perfect for SPI.

```
              3.3V (VCCB)          1.8V (VCCA)
                |                     |
        +-------+---------------------+-------+
        |       SN74AVC4T245                   |
        |  DIR = tied per channel              |
        |  1OE_N = GND (always enabled)        |
        |  2OE_N = GND (always enabled)        |
        |                                      |
        |  B1 <--- GPIO_1[0] SCLK  --> A1 ----|---> ICM SCLK
        |  B2 <--- GPIO_1[1] MOSI  --> A2 ----|---> ICM SDI
        |  B3 ---> GPIO_1[2] MISO  <-- A3 ----|<--- ICM SDO
        |  B4 <--- GPIO_1[3] CS_N  --> A4 ----|---> ICM nCS
        +--------------------------------------+
```

Direction control: SCLK/MOSI/CS are B-to-A (3.3V to 1.8V). MISO is A-to-B (1.8V to 3.3V). The SN74AVC4T245 has a DIR pin per 2-bit group, which works for SPI.

### 1.8V LDO for IMU

**Part: TPS7A2018DBVR** (TPS7A20 family, fixed 1.8V output)
- Input: 3.3V
- Output: 1.8V, 300mA max (ICM-20948 draws < 5mA typ)
- Dropout: 110mV typ at 300mA
- Package: SOT-23-5
- Quiescent current: 6.5uA

```
3.3V ---[TPS7A2018]--- 1.8V
         |    |    |
        4.7uF  |  1uF
        (in)  GND (out)
```

### ICM-20948 Decoupling

- VDD (pin 13): 100nF + 10uF MLCC to GND
- VDDIO (pin 14): 100nF to GND
- REGOUT (pin 11): 1uF to GND (internal regulator output, required)
- FSYNC (pin 1): tied to GND via 10k (unused)
- AD0/SDO: tied to VDD for SPI mode (AD0=1 selects SPI, SDO becomes SPI data out)

### INT1 Pin

ICM-20948 INT1 is open-drain capable at 1.8V. Use a 10k pull-up to 3.3V on the FPGA side (the pin is 3.3V tolerant when configured as open-drain by the ICM-20948). Alternatively, route through a 5th channel of the level shifter -- but since we only have 4 channels on SN74AVC4T245, use a simple N-channel MOSFET level shifter (BSS138 + 10k pull-ups on each side) for the interrupt line.

### Vibration Isolation

Mount the ICM-20948 on a small isolated island of the PCB connected via 2-3 thin traces (thermal relief style). Alternatively, use:
- **Molex gel pads** or **3M VHB foam tape** between the PCB and the drone frame
- Place IMU at the board center (minimize moment arm from vibrations)
- Add four 2.5mm slot routes around the IMU footprint (stress relief slots)

### Component List

| Ref   | Part Number              | Description                      | Package     | Qty | Unit Price | Supplier |
|-------|-------------------------|----------------------------------|-------------|-----|-----------|----------|
| U5    | ICM-20948               | 9-axis IMU                       | QFN-24 3x3mm| 1   | $8.50     | DigiKey  |
| U6    | SN74AVC4T245RGYR        | 4-bit level translator           | VQFN-16     | 1   | $0.85     | Mouser   |
| U7    | TPS7A2018DBVR           | 1.8V LDO 300mA                   | SOT-23-5    | 1   | $0.55     | DigiKey  |
| Q1    | BSS138                  | N-ch MOSFET (INT level shift)    | SOT-23      | 1   | $0.15     | DigiKey  |
| C5    | 10uF 0402 MLCC          | VDD decoupling                   | 0402        | 1   | $0.05     |          |
| C6-C8 | 100nF 0402 MLCC         | VDD, VDDIO, translator decoupling| 0402       | 3   | $0.02     |          |
| C9    | 1uF 0402 MLCC           | REGOUT decoupling                | 0402        | 1   | $0.03     |          |
| C10   | 4.7uF 0402 MLCC         | LDO input                        | 0402        | 1   | $0.04     |          |
| C11   | 1uF 0402 MLCC           | LDO output                       | 0402        | 1   | $0.03     |          |
| R1-R3 | 10k 0402                | INT pull-ups, FSYNC tie          | 0402        | 3   | $0.01     |          |

### PCB Layout

- Place ICM-20948 at board center, away from motor traces and power converter switching nodes.
- 4 stress-relief routing slots (1mm wide, 5mm long) around the ICM QFN.
- Ground pour under IMU, no switching node traces beneath.
- Level translator within 5mm of IMU for short 1.8V trace runs.
- SPI traces: matched length is not critical at 7MHz, but keep < 25mm.

**Subsystem cost**: ~$11.50

---

## 3. Camera Interface -- OV5640 DVP (8-bit parallel)

### Architecture

The OV5640 module comes on its own small PCB with FPC ribbon cable. The daughter board provides an FPC connector, power LDOs, and routes the 8-bit DVP bus + control signals to GPIO0.

### OV5640 Power Requirements

| Rail   | Voltage | Current | Purpose          |
|--------|---------|---------|------------------|
| AVDD   | 2.8V    | 80mA    | Analog supply     |
| DVDD   | 1.5V    | 60mA    | Digital core      |
| DOVDD  | 1.8-3.3V| 20mA    | Digital I/O       |

For this design, DOVDD = 3.3V (matches FPGA GPIO directly -- no level shifting needed).

### FPC Connector

**Part: Molex 5051102491** (or equivalent) -- 24-pin, 0.5mm pitch, bottom-contact, ZIF FPC connector. This matches standard OV5640 camera modules (e.g., Arducam OV5640 module with 24-pin FPC).

### Standard OV5640 24-pin FPC Pinout

| FPC Pin | Signal  | Connects To          |
|---------|---------|----------------------|
| 1       | GND     | Ground               |
| 2       | SIO_C   | GPIO_0[12] (I2C CLK) |
| 3       | SIO_D   | GPIO_0[13] (I2C DATA)|
| 4       | AVDD    | 2.8V LDO output      |
| 5       | DOVDD   | 3.3V                 |
| 6       | DVDD    | 1.5V LDO output      |
| 7       | VSYNC   | GPIO_0[9]            |
| 8       | HREF    | GPIO_0[10]           |
| 9       | PCLK    | GPIO_0[8]            |
| 10      | XCLK    | GPIO_0[11]           |
| 11      | D9(D7)  | GPIO_0[7]            |
| 12      | D8(D6)  | GPIO_0[6]            |
| 13      | D7(D5)  | GPIO_0[5]            |
| 14      | D6(D4)  | GPIO_0[4]            |
| 15      | D5(D3)  | GPIO_0[3]            |
| 16      | D4(D2)  | GPIO_0[2]            |
| 17      | D3(D1)  | GPIO_0[1]            |
| 18      | D2(D0)  | GPIO_0[0]            |
| 19      | GND     | Ground               |
| 20      | PWDN    | GPIO_0[14]           |
| 21      | RESET   | GPIO_0[15]           |
| 22-24   | GND     | Ground               |

Note: OV5640 FPC pinouts vary by module manufacturer. Verify against your specific module datasheet. The above follows the common Arducam/generic Chinese module pinout.

### XCLK Source

Route from FPGA PLL output via GPIO_0[11]. The FPGA generates a clean 24MHz clock from its PLL (50MHz input / 25 * 12 = 24MHz). This avoids adding a discrete oscillator.

### Power LDOs

**2.8V AVDD LDO: TPS7A2028DBVR** (TPS7A20 family, fixed 2.8V)
- Input: 3.3V
- Output: 2.8V, 300mA max
- Dropout: 110mV typ (margin: 3.3V - 2.8V = 500mV, well above dropout)
- Package: SOT-23-5

**1.5V DVDD LDO: TPS7A2015DBVR** (TPS7A20 family, fixed 1.5V)
- Input: 3.3V
- Output: 1.5V, 300mA max
- Package: SOT-23-5

```
3.3V ---[TPS7A2028]--- 2.8V (AVDD)    3.3V ---[TPS7A2015]--- 1.5V (DVDD)
         |    |    |                            |    |    |
        4.7uF  | 1uF+10uF                     4.7uF  | 1uF+10uF
        (in)  GND (out)                        (in)  GND (out)
```

SCCB (I2C) pull-ups: 4.7k to 3.3V on SIO_C and SIO_D lines (OV5640 SCCB is I2C-compatible).

### Component List

| Ref    | Part Number          | Description                    | Package     | Qty | Unit Price | Supplier |
|--------|---------------------|--------------------------------|-------------|-----|-----------|----------|
| J5     | 5051102491 (Molex)  | 24-pin 0.5mm FPC ZIF           | SMD         | 1   | $0.65     | DigiKey  |
| U8     | TPS7A2028DBVR       | 2.8V LDO 300mA (AVDD)         | SOT-23-5    | 1   | $0.55     | DigiKey  |
| U9     | TPS7A2015DBVR       | 1.5V LDO 300mA (DVDD)         | SOT-23-5    | 1   | $0.55     | DigiKey  |
| C12-C13| 4.7uF 0402 MLCC     | LDO input caps                  | 0402        | 2   | $0.04     |          |
| C14-C15| 1uF 0402 MLCC       | LDO output caps                 | 0402        | 2   | $0.03     |          |
| C16-C17| 10uF 0603 MLCC      | LDO output bulk caps            | 0603        | 2   | $0.08     |          |
| R4-R5  | 4.7k 0402           | I2C pull-ups                    | 0402        | 2   | $0.01     |          |

### PCB Layout

- FPC connector along board edge for ribbon cable clearance.
- LDOs within 10mm of FPC connector to minimize power trace length.
- PCLK trace may run up to 96MHz (OV5640 max pixel clock) -- treat as high-speed, keep short and direct.
- GND plane under DVP data bus traces.
- Separate AVDD and DVDD pours if possible, star-ground back to main GND.

**Subsystem cost**: ~$2.50

---

## 4. ToF Sensor Hub -- 6x VL53L1X

### Architecture

Six VL53L1X time-of-flight sensors provide obstacle detection in all directions (front, back, left, right, up, down). All VL53L1X modules have the same fixed I2C address (0x52 / 0x29 7-bit), so a **TCA9548A I2C multiplexer** routes the FPGA's I2C master to one sensor at a time. Each sensor connects via a 4-pin JST-SH cable.

Additionally, XSHUT (active-low shutdown) lines allow individual sensor power-cycling and address reassignment at boot (alternative to mux, but mux is more robust).

### Circuit Design

```
                      3.3V
                       |
                      4.7k  4.7k
                       |     |
GPIO_1[5] SCL --------+-----|--------+
GPIO_1[6] SDA --------+-----|--------+
                       |     |        |
                 +-----+-----+--------+-----+
                 |     TCA9548A              |
                 |  A0=GND A1=GND A2=GND    |  (I2C addr: 0x70)
                 |  RESET_N <-- GPIO_1[7]   |
                 |                          |
                 |  SD0/SC0 ----> JST-SH J6  (ToF 0: Down)
                 |  SD1/SC1 ----> JST-SH J7  (ToF 1: Front)
                 |  SD2/SC2 ----> JST-SH J8  (ToF 2: Back)
                 |  SD3/SC3 ----> JST-SH J9  (ToF 3: Left)
                 |  SD4/SC4 ----> JST-SH J10 (ToF 4: Right)
                 |  SD5/SC5 ----> JST-SH J11 (ToF 5: Up)
                 |  SD6,SD7 ---  unused      |
                 +---------------------------+
```

Each downstream I2C channel has **no pull-ups** on the daughter board -- the VL53L1X breakout modules (e.g., Pololu #3415 or Adafruit #3967) include their own 10k pull-ups. If using bare VL53L1X sensors, add 4.7k pull-ups on each downstream channel.

### XSHUT Lines

6 individual XSHUT lines allow selective power-on sequencing (useful for runtime address reassignment without the mux, or for resetting a misbehaving sensor):

```
GPIO_1[8]  --> XSHUT_0 (pin 4 on J6)
GPIO_1[9]  --> XSHUT_1 (pin 4 on J7)
GPIO_1[10] --> XSHUT_2 (pin 4 on J8)
GPIO_1[11] --> XSHUT_3 (pin 4 on J9)
GPIO_1[14] --> XSHUT_4 (pin 4 on J10)
GPIO_1[15] --> XSHUT_5 (pin 4 on J11)
```

XSHUT has internal pull-down on VL53L1X, so sensor stays off until FPGA drives high. Each XSHUT line has a 100-ohm series resistor for ESD protection.

### JST-SH Connector Pinout (4-pin, 1.0mm pitch)

| Pin | Signal | Notes                    |
|-----|--------|--------------------------|
| 1   | VCC    | 3.3V (from daughter board)|
| 2   | GND    | Ground                    |
| 3   | SDA    | I2C data (from TCA9548A channel) |
| 4   | SCL    | I2C clock (from TCA9548A channel)|

### Component List

| Ref     | Part Number           | Description                    | Package    | Qty | Unit Price | Supplier |
|---------|-----------------------|--------------------------------|------------|-----|-----------|----------|
| U10     | TCA9548APWR           | 8-ch I2C mux                   | TSSOP-24   | 1   | $1.80     | DigiKey  |
| J6-J11  | SM04B-SRSS-TB(LF)(SN)| JST-SH 4-pin header             | SMD        | 6   | $0.35     | DigiKey  |
| R6-R7   | 4.7k 0402             | Upstream I2C pull-ups           | 0402       | 2   | $0.01     |          |
| R8-R13  | 100R 0402             | XSHUT series resistors          | 0402       | 6   | $0.01     |          |
| C18     | 100nF 0402 MLCC       | TCA9548A decoupling             | 0402       | 1   | $0.02     |          |
| C19     | 10uF 0603 MLCC        | TCA9548A bulk decoupling        | 0603       | 1   | $0.08     |          |

### PCB Layout

- JST-SH connectors along board edges (sensors mount on drone arms via cables).
- Keep upstream I2C traces short (< 20mm from GPIO header to TCA9548A).
- Downstream I2C traces go to edge connectors -- cable length up to 200mm is fine at 400kHz I2C.
- TCA9548A decoupling within 2mm of VCC pin.

**Subsystem cost**: ~$5.00

---

## 5. Barometer -- BMP390

### Architecture

The BMP390 shares the **upstream** I2C bus with the TCA9548A (before the mux). The BMP390 I2C address is **0x77** (SDO pin tied to VDD) or **0x76** (SDO to GND). The TCA9548A is at 0x70, and VL53L1X is at 0x29 -- no conflicts.

We connect BMP390 directly to GPIO_1[5] (SCL) and GPIO_1[6] (SDA), same bus as TCA9548A upstream.

### Circuit Design

```
                    3.3V
                     |
               +-----+-----+
               |   BMP390   |
               |  VDD=3.3V  |
               |  VDDIO=3.3V|
               |  SDO=VDD   | (addr 0x77)
               |  CSB=VDD   | (I2C mode select)
               |  SCL <-----|--- GPIO_1[5] (shared with TCA9548A)
               |  SDA <-----|--- GPIO_1[6] (shared with TCA9548A)
               |  INT (NC)  |
               +-----+------+
                     |
                   100nF + 100nF (VDD + VDDIO decoupling)
                     |
                    GND
```

### Pressure Port

For accurate barometric readings in a drone environment:
- Place a **1mm diameter hole** in the PCB directly above the BMP390 sensor port.
- Shield from propeller wash with a small piece of open-cell foam over the hole.
- Do NOT place a solder mask dam over the sensor opening.

### Component List

| Ref  | Part Number        | Description               | Package     | Qty | Unit Price | Supplier |
|------|--------------------|---------------------------|-------------|-----|-----------|----------|
| U11  | BMP390             | Barometric pressure sensor | LGA-10 2x2mm| 1  | $3.20     | Mouser   |
| C20-C21| 100nF 0402 MLCC  | VDD + VDDIO decoupling    | 0402        | 2   | $0.02     |          |
| R14  | 10k 0402           | SDO pull-up (addr select)  | 0402        | 1   | $0.01     |          |
| R15  | 10k 0402           | CSB pull-up (I2C mode)     | 0402        | 1   | $0.01     |          |

### PCB Layout

- Place BMP390 **away from heat sources** (LDOs, buck converter). Temperature changes affect pressure reading.
- Minimum 5mm from power converter.
- 1mm vent hole in PCB above sensor, no copper pour within 2mm of hole.
- Place near board center alongside IMU for best vibration isolation.

**Subsystem cost**: ~$3.30

---

## 6. IR Beacon Receivers -- TSOP38238

### Architecture Decision

For indoor autonomous navigation, GPS is unnecessary and unreliable. Instead, the drone uses an **IR homing beacon** on the base station for coarse return-to-dock navigation (effective range 10-15m), combined with **camera AprilTag detection** for precision landing at <1m.

Four **TSOP38238** IR receivers are mounted at the board edges (front, left, right, rear) pointing outward. The base station emits modulated 940nm IR from an LED array at 38 kHz. The FPGA measures received pulse width from each sensor to determine signal strength and computes a bearing estimate for homing.

### Interface

Each TSOP38238 has a single digital output (active-low pulse when IR detected):
- GPIO_1[12]: IR_RX_FRONT (FPGA input, active-low)
- GPIO_1[13]: IR_RX_LEFT (FPGA input, active-low)
- GPIO_1[14]: IR_RX_RIGHT (FPGA input, active-low)
- GPIO_1[15]: IR_RX_REAR (FPGA input, active-low)

All outputs are 3.3V compatible (TSOP38238 operates at 2.5-5.5V). No level shifting needed.

### TSOP38238 Key Specs

- Carrier frequency: 38 kHz
- Supply voltage: 2.5-5.5V (powered from 3.3V rail)
- Supply current: 0.35mA typ
- Reception distance: 45m (with matched emitter)
- Output: active-low, open-collector with internal pull-up
- Package: Through-hole (Vishay Minicast, 3-pin)
- Built-in AGC, bandpass filter, and demodulator

### Circuit Design (per receiver)

```
3.3V ---+--- VCC (pin 2)
        |
       100nF (decoupling, close to VCC pin)
        |
       GND

TSOP38238:
  Pin 1 (OUT) ---+--- GPIO_1[12..15] (FPGA input)
                  |
                [4.7k pull-up to 3.3V] (optional, internal pull-up exists)
  Pin 2 (VCC) --- 3.3V
  Pin 3 (GND) --- GND
```

The internal demodulator outputs a clean active-low pulse when a 38 kHz burst is received. The FPGA timestamps rising and falling edges to measure pulse width, which correlates with signal strength (closer = stronger = wider pulses).

### Connector (JST-SH 3-pin, 1.0mm pitch, per sensor)

Each IR receiver mounts at a board edge via a short cable:

| Pin | Signal | Connection |
|-----|--------|-----------|
| 1   | VCC    | 3.3V |
| 2   | GND    | Ground |
| 3   | OUT    | GPIO_1[12-15] (one per sensor) |

Connectors J12A-J12D at four board edges. Alternatively, the TSOP38238 modules can be soldered directly to the daughter board edges on small breakout tabs.

### Component List

| Ref     | Part Number        | Description                     | Package      | Qty | Unit Price | Supplier |
|---------|--------------------|---------------------------------|-------------|-----|-----------|----------|
| IR1-IR4 | TSOP38238          | 38 kHz IR receiver              | Through-hole | 4   | $0.80     | DigiKey  |
| J12A-D  | SM03B-SRSS-TB(LF)(SN) | JST-SH 3-pin (IR sensor)  | SMD          | 4   | $0.30     | DigiKey  |
| C22-C25 | 100nF 0402 MLCC    | IR receiver VCC decoupling      | 0402         | 4   | $0.02     |          |
| R16A-D  | 4.7k 0402          | IR output pull-ups (optional)   | 0402         | 4   | $0.01     |          |

### PCB Layout

- Place JST-SH connectors at **all four board edges** (front, left, right, rear) for maximum angular coverage.
- Each TSOP38238 should face outward with no PCB copper or components blocking its reception window.
- Minimum 20mm between IR receiver connectors and WILC3000 WiFi antenna.
- Decoupling caps within 3mm of each connector VCC pin.
- Keep IR receiver signal traces short (< 50mm) and away from switching power traces.

### ToF XSHUT Tradeoff

GPIO_1[14-15] were previously allocated to TOF_XSHUT_4 and TOF_XSHUT_5. With these pins reassigned to IR receivers, those two ToF sensors (channels 4 and 5 on the TCA9548A) lose individual XSHUT control. They can still be managed via TCA9548A mux channel isolation -- the mux enables/disables each downstream I2C bus independently, providing equivalent functionality for sensor initialization sequencing.

**Subsystem cost**: ~$5.00 (4 receivers + connectors + passives; IR receivers purchased separately at ~$0.80 each)

---

## 7. WiFi/BLE -- Microchip WILC3000 (ATWILC3000-MR110UB)

### Architecture Decision

The WILC3000 provides WiFi 802.11 b/g/n + Bluetooth 4.2/BLE via **HPS SPI1**, connecting directly to the Linux networking stack. This eliminates the need for custom firmware, FPGA soft UART, and FPGA GPIO pins. WiFi appears as `wlan0` (via `wpa_supplicant` or `hostapd`), BLE appears as `hci0` (via BlueZ). The mainline Linux kernel driver (`wilc_spi`) has been upstream since Linux 5.5.

**Connection to HPS**: The DE10-Nano's LTC connector (J10) exposes HPS SPI1 (CLK, MOSI, MISO, SS) and one HPS GPIO. The WILC3000 SPI signals route from the daughter board to J10 via a short 6-wire cable. No FPGA resources are used.

**Advantages over ESP32-C3 UART approach**:
- **20x throughput**: SPI at 48 MHz vs UART at ~1 Mbps
- **Zero FPGA resources**: No soft UART IP, no Avalon-MM bridge registers
- **Standard Linux networking**: SSH, web dashboard, camera debug streams, OTA updates
- **No custom firmware**: Mainline kernel driver handles everything
- **Frees 4 FPGA GPIO pins**: GPIO_1[17-20] become spare

### WILC3000 Key Specs

- Supply: 3.3V (internal 1.8V LDO for core)
- SPI: Host interface, up to 48 MHz
- WiFi: 802.11 b/g/n, 2.4 GHz, up to 72 Mbps (HT40)
- BLE: Bluetooth 4.2, dual-mode
- Antenna: Built-in PCB antenna (ATWILC3000-MR110UB) or u.FL (MR110CA)
- Dimensions: 19.2 x 13.7 x 2.5mm (module)
- Linux driver: `wilc_spi` (mainline since 5.5)

### Circuit Design

```
     Daughter Board                          DE10-Nano
     ┌──────────────────────────┐            ┌──────────────┐
     │                          │   6-wire   │              │
     │  3.3V (from AP2112K)     │   cable    │  LTC Conn    │
     │     |                    │            │  (J10)       │
     │  10uF + 100nF            │            │              │
     │     |                    │            │              │
     │  +--+--------------------+--+         │              │
     │  |     WILC3000 Module      |         │              │
     │  |                          |         │              │
     │  | SPI_CLK  ────────────────┼─────────┤ HPS_SPIM_CLK │
     │  | SPI_MOSI ────────────────┼─────────┤ HPS_SPIM_MOSI│
     │  | SPI_MISO ────────────────┼─────────┤ HPS_SPIM_MISO│
     │  | SPI_SSN  ────────────────┼─────────┤ HPS_SPIM_SS  │
     │  | IRQ      ────────────────┼─────────┤ HPS_LTC_GPIO │
     │  |                          |         │              │
     │  | CHIP_EN  ◄── 10k to 3.3V|         │              │
     │  | RESETN   ◄── 10k + 1uF  |         │              │
     │  |                    (RC)  |         │              │
     │  | GND ─────────────────────┼─────────┤ GND          │
     │  +--------------------------+         └──────────────┘
     │     |          |
     │  [Antenna   [Decoupling]
     │   keep-out]
     └──────────────────────────┘
```

### LTC Bridge Cable Header (J13, 6-pin)

Routes SPI + IRQ signals from daughter board to DE10-Nano LTC connector (J10):

| Pin | Signal       | LTC Connector Pin |
|-----|-------------|-------------------|
| 1   | SPI_CLK     | HPS_SPIM_CLK      |
| 2   | SPI_MOSI    | HPS_SPIM_MOSI     |
| 3   | SPI_MISO    | HPS_SPIM_MISO     |
| 4   | SPI_SSN     | HPS_SPIM_SS       |
| 5   | IRQ         | HPS_LTC_GPIO      |
| 6   | GND         | GND                |

Cable length: 50-80mm (short as possible for SPI signal integrity at 48 MHz).

### Antenna Keep-out

The ATWILC3000-MR110UB has a built-in PCB antenna. Requirements:
- **No copper pour** (ground or signal) within 10mm of antenna edge on the daughter board.
- No components within 15mm in the antenna radiation direction.
- Place the module at a **board corner** with the antenna extending toward the board edge.
- No ground plane under the antenna section (cut-out in all layers).

### Linux Integration

```bash
# Device tree overlay for WILC3000 on HPS SPI1
&spi1 {
    status = "okay";
    wilc_spi@0 {
        compatible = "microchip,wilc3000";
        reg = <0>;
        spi-max-frequency = <48000000>;
        interrupt-parent = <&portc>;  /* HPS GPIO bank */
        interrupts = <9 2>;           /* HPS_LTC_GPIO, falling edge */
    };
};

# After boot:
# modprobe wilc_spi         (if built as module)
# wpa_supplicant -i wlan0   (WiFi client)
# hostapd /etc/hostapd.conf (WiFi AP for telemetry)
# hciconfig hci0 up         (BLE)
```

### Component List

| Ref  | Part Number              | Description                  | Package     | Qty | Unit Price | Supplier |
|------|-------------------------|------------------------------|-------------|-----|-----------|----------|
| U12  | ATWILC3000-MR110UB      | WiFi/BLE SPI module          | Module      | 1   | $7.00     | DigiKey  |
| C26  | 10uF 0603 MLCC          | VCC bulk decoupling          | 0603        | 1   | $0.08     |          |
| C27  | 100nF 0402 MLCC         | VCC decoupling               | 0402        | 1   | $0.02     |          |
| C28  | 1uF 0402 MLCC           | RESETN RC delay cap          | 0402        | 1   | $0.03     |          |
| R17  | 10k 0402                | CHIP_EN pull-up              | 0402        | 1   | $0.01     |          |
| R18  | 10k 0402                | RESETN pull-up               | 0402        | 1   | $0.01     |          |
| J13  | SM06B-SRSS-TB(LF)(SN)   | JST-SH 6-pin (LTC bridge)   | SMD         | 1   | $0.35     |          |

### PCB Layout

- Place WILC3000 at board corner with antenna protruding toward board edge.
- Ground plane cut-out under antenna area (all 4 layers).
- Keep all high-speed digital traces > 20mm from antenna.
- 3.3V decoupling within 3mm of WILC3000 VCC pins.
- SPI traces: matched length, 50-ohm impedance, max 50mm to J13 header.

**Subsystem cost**: ~$7.50

---

## 8. Power Management

### Power Architecture

```
4S LiPo (14.8-16.8V)
    |
    +--[XT60 connector]
    |
    +--[P-MOSFET reverse polarity protection]
    |
    +--[SMBJ20A TVS diode to GND]
    |
    +--[Physical arm/kill switch]
    |
    +--- VBATT rail (14.8-16.8V) ---> Battery voltage sense (divider to ADC)
    |                               |
    |                               +---> INA219 current sensor
    |
    +--[TPS54560 Buck]---> 5V / 5A rail
         |                     |
         |                     +---> DE10-Nano barrel jack (5V, ~2A)
         |                     +---> ESC BEC backup (if needed)
         |                     +---> Barrel jack connector (5.5x2.1mm)
         |
         +--[AP2112K-3.3]---> 3.3V / 600mA rail
              |                    |
              |                    +---> Sensors (BMP390, TCA9548A, IR receivers, WILC3000)
              |                    +---> Level shifters, buffers, pull-ups
              |                    +---> Camera DOVDD
              |
              +--[TPS7A2018]---> 1.8V / 300mA (IMU VDDIO)
              +--[TPS7A2028]---> 2.8V / 300mA (Camera AVDD)
              +--[TPS7A2015]---> 1.5V / 300mA (Camera DVDD)
```

### Reverse Polarity Protection

**P-Channel MOSFET**: SI4435DDY (P-ch, -30V, -8.8A, RDS(on)=20mΩ)

```
VBATT_IN ---+---[10k]---+
            |            |
            +--||--Gate  |
            | Source     |
            +---- Drain--+--- VBATT_PROTECTED
            SI4435DDY
```

When connected correctly, Gate is pulled below Source by the 10k resistor through the body diode initial conduction, turning the P-FET fully on. Reverse polarity: Gate goes positive relative to Source, FET stays off.

Add a 15V zener (BZX84C15) gate-to-source for ESD protection.

### TVS Protection

**SMBJ20A** -- 20V standoff, 600W peak pulse, SMB package. Clamps transients from battery connection/disconnection.

### 5V Buck Converter -- TPS54560

Design parameters:
- VIN: 14.8-16.8V (4S LiPo)
- VOUT: 5.0V
- IOUT: 5A max (DE10-Nano draws ~2A, peripherals ~0.5A, margin for camera)
- fSW: 480kHz (good balance of efficiency vs size)

**Component values (from TI WEBENCH for TPS54560, 16.8V to 5V at 5A, 480kHz)**:

| Component | Value           | Part Number           | Notes                    |
|-----------|----------------|-----------------------|--------------------------|
| L1        | 10uH, 6A       | SRP1265A-100M (Bourns)| Shielded, 12.5x12.5mm   |
| CIN       | 2x 10uF/25V    | GRM32ER71E106KA12L    | X7R 1210 MLCC           |
| COUT      | 2x 47uF/10V    | GRM32ER71A476ME15L    | X7R 1210 MLCC           |
| CBOOT     | 100nF/16V      | Standard 0402         | Bootstrap                |
| R_RT      | 100k            | 0402                  | Sets fSW = 480kHz       |
| R_FB_TOP  | 100k            | 0402 1%               | Feedback divider top     |
| R_FB_BOT  | 24.9k           | 0402 1%               | VOUT = 0.8V * (1 + 100k/24.9k) = 4.97V |
| R_COMP    | 30.1k           | 0402                  | Type II compensation     |
| C_COMP    | 6.8nF           | 0402                  | Compensation capacitor   |
| C_COMP2   | 68pF            | 0402                  | HF comp pole             |
| R_EN1     | 1M              | 0402                  | EN divider top (UVLO)    |
| R_EN2     | 160k            | 0402                  | EN divider bottom (enable at ~13V) |
| D_BOOT    | CUS10S30 (Toshiba)| SOD-323             | Bootstrap diode (optional, internal exists) |
| CSS       | 47nF            | 0402                  | Soft-start (5ms)         |

**UVLO**: The EN divider (1M/160k) sets turn-on at ~13V (protects against under-voltage LiPo damage) and hysteresis of ~1V via internal current source.

### 3.3V LDO -- AP2112K-3.3TRG1

- Input: 5V
- Output: 3.3V, 600mA
- Dropout: 250mV at 600mA
- Quiescent: 55uA
- Package: SOT-23-5
- Built-in enable, overcurrent, thermal protection

```
5V ---[AP2112K-3.3]--- 3.3V_SENSOR
       |    |    |
      1uF   |  2.2uF + 10uF
      (in) GND (out)
```

### Battery Voltage Monitoring

Resistor divider scales 16.8V max to < 3.3V for the DE10-Nano's LTC2308 ADC:

```
VBATT ---[100k]---+---[27k]--- GND
                   |
                   +--- ADC_CH0 (Arduino header A0)
                   |
                  100pF (anti-alias filter)
```

Divider ratio: 27k / (100k + 27k) = 0.2126
At 16.8V: ADC sees 3.57V -- slightly above 3.3V.

**Revised**: Use 100k + 33k:
Ratio: 33k / (100k + 33k) = 0.2481
At 16.8V: ADC sees 4.17V -- too high.

**Revised**: Use 150k + 27k:
Ratio: 27k / (150k + 27k) = 0.1525
At 16.8V: ADC sees 2.56V. At 14.0V (empty): 2.14V. Good range for 12-bit ADC.

### Current Sensing -- INA219

The INA219 measures battery current for power monitoring and flight time estimation.

```
VBATT_PROTECTED ---[R_SHUNT 10mΩ]---+--- VBATT_SWITCHED
                                      |
                    +--------+        |
                    | INA219 |        |
                    | IN+    |--------+  (load side)
                    | IN-    |--------+  (battery side)
                    | VS     |--- 3.3V
                    | SCL    |--- GPIO_1[5] (shared I2C)
                    | SDA    |--- GPIO_1[6] (shared I2C)
                    | A0=GND |   (addr 0x40)
                    | A1=GND |
                    | ALERT  |--- GPIO_1[16] (optional overcurrent interrupt)
                    +--------+
```

- Shunt: 10mΩ, 1%, 2W (Bourns CSS2H-2512R-L010F)
- At 10A max: V_shunt = 100mV (within INA219 +/-320mV range at PGA=8)
- INA219 I2C address 0x40 (A0=A1=GND) -- no conflict with TCA9548A (0x70) or BMP390 (0x77)

### Physical Safety Switch

An XT30 loop connector or a high-current toggle switch in the VBATT line:

```
VBATT_PROTECTED ---[XT30 female]---[XT30 male loop-back plug]--- VBATT_SWITCHED
```

The "arm plug" is a common drone safety feature. Remove the plug to cut all power to ESCs/motors. The 5V rail to the DE10-Nano can be wired before or after this switch (before = board stays powered when disarmed; recommended).

### Component List

| Ref     | Part Number              | Description                        | Package     | Qty | Unit Price | Supplier |
|---------|-------------------------|-----------------------------------|-------------|-----|-----------|----------|
| J14     | XT60PW-M (Amass)        | XT60 male PCB mount               | Through-hole| 1   | $1.50     | Amazon   |
| J15     | PJ-102AH                | 5.5x2.1mm barrel jack             | Through-hole| 1   | $0.60     | DigiKey  |
| Q2      | SI4435DDY               | P-ch MOSFET reverse protection    | SO-8        | 1   | $0.85     | DigiKey  |
| D6      | SMBJ20A                 | TVS 20V 600W                      | SMB         | 1   | $0.35     | DigiKey  |
| D7      | BZX84C15                | 15V Zener (gate protect)          | SOT-23      | 1   | $0.08     |          |
| U13     | TPS54560DDAR            | 5V/5A Buck converter              | HSOP-8      | 1   | $3.20     | DigiKey  |
| L1      | SRP1265A-100M           | 10uH 6A shielded inductor         | 12.5x12.5mm | 1   | $1.50     | DigiKey  |
| U14     | AP2112K-3.3TRG1         | 3.3V/600mA LDO                    | SOT-23-5    | 1   | $0.38     | DigiKey  |
| U15     | INA219BIDR              | Current/power monitor              | SOT-23-8    | 1   | $1.20     | DigiKey  |
| R_SHUNT | CSS2H-2512R-L010F       | 10mΩ 2W current sense             | 2512        | 1   | $0.65     | DigiKey  |
| CIN1-2  | GRM32ER71E106KA12L      | 10uF/25V X7R (buck input)         | 1210        | 2   | $0.35     |          |
| COUT1-2 | GRM32ER71A476ME15L      | 47uF/10V X7R (buck output)        | 1210        | 2   | $0.55     |          |
| R_FB_T  | 100k 1% 0402           | Buck feedback top                  | 0402        | 1   | $0.02     |          |
| R_FB_B  | 24.9k 1% 0402          | Buck feedback bottom               | 0402        | 1   | $0.02     |          |
| R_RT    | 100k 0402              | Buck frequency set                 | 0402        | 1   | $0.01     |          |
| R19-R20 | 150k + 27k 1% 0402     | Battery voltage divider            | 0402        | 2   | $0.02     |          |
| C_BATT  | 100pF 0402             | ADC anti-alias                     | 0402        | 1   | $0.02     |          |
| Various | Comp/bootstrap/SS caps  | See buck design table              | 0402        | 5   | $0.02     |          |
| SW1     | XT30PW-F (Amass)       | Arm switch connector (loop plug)   | Through-hole| 1   | $0.80     |          |

### PCB Layout

- **Buck converter**: Tight layout critical. Hot loop (CIN -> VIN -> SW -> L1 -> COUT -> GND -> CIN) must be minimal area. Place input caps within 5mm of TPS54560.
- Inductor directly adjacent to SW pin. Output caps at inductor output pad.
- Ground plane under entire buck area, thermal vias under TPS54560 exposed pad.
- **Separation**: Buck converter in one corner, analog sensors (IMU, baro) in opposite corner. Minimum 25mm between switching node and IMU.
- Battery input connector and protection circuit along one board edge.
- Current sense resistor in the high-current path, Kelvin connection to INA219 sense pins.

**Subsystem cost**: ~$14.50

---

## 9. Water Pump Driver

### Circuit Design

```
GPIO_0[20] ---[1k]---+--- Gate
                      |
                     [10k] (pull-down to GND)
                      |
                     GND

                 Drain ---+---[SS14]---+--- PUMP_VCC (5V or VBATT)
                           |     ^      |
                       [PUMP-]   |   [PUMP+]   (JST-XH 2-pin connector J16)
                           |   (cathode|
                          GND  to drain)
                           |
                        Source
                           |
                          GND
```

**MOSFET choice**: AO3400A (N-ch, 30V, 5.8A, RDS(on)=40mΩ, SOT-23)
- More appropriate than IRLZ44N (through-hole, overkill) for a small pump drawing < 2A.
- Logic-level gate: VGS(th) = 1.0V typ, fully enhanced at 2.5V. 3.3V gate drive is sufficient.

**Flyback diode**: SS14 (1A, 40V Schottky, SMA package). Protects against pump motor back-EMF.

**Gate pull-down**: 10k to GND ensures pump stays off during FPGA boot/reset.

**Pump power**: Selectable via a solder jumper -- 5V rail or VBATT_SWITCHED. Most small peristaltic pumps used for plant watering run at 3-12V DC.

### Component List

| Ref  | Part Number     | Description                    | Package     | Qty | Unit Price | Supplier |
|------|----------------|--------------------------------|-------------|-----|-----------|----------|
| Q3   | AO3400A        | N-ch MOSFET 30V 5.8A           | SOT-23      | 1   | $0.25     | DigiKey  |
| D8   | SS14           | 1A 40V Schottky                 | SMA         | 1   | $0.12     | DigiKey  |
| R21  | 1k 0402        | Gate series resistor            | 0402        | 1   | $0.01     |          |
| R22  | 10k 0402       | Gate pull-down                  | 0402        | 1   | $0.01     |          |
| J16  | B2B-XH-A(LF)(SN)| JST-XH 2-pin (pump connector) | Through-hole| 1   | $0.14     | DigiKey  |
| SJ1  | Solder jumper   | Power select: 5V or VBATT      | 0603 pad    | 1   | --        |          |

### PCB Layout

- MOSFET and Schottky close together, short drain trace.
- Pump connector at board edge.
- Keep gate trace away from high-current drain path.

**Subsystem cost**: ~$0.60

---

## 10. Miscellaneous

### 10a. Buzzer Driver

Same topology as pump driver, smaller MOSFET:

```
GPIO_0[21] ---[1k]---+--- Gate (AO3400A)
                      |
                     [10k] pull-down
                      |
                     GND

                 Drain --- [Buzzer-] (JST-XH 2-pin J17)
                 Source --- GND
                 [Buzzer+] --- 5V
```

Uses a passive piezo buzzer driven by PWM (2.7kHz typical). Active buzzers also work but are less flexible for multi-tone alerts.

| Ref  | Part Number     | Description              | Package     | Qty | Unit Price |
|------|----------------|--------------------------|-------------|-----|-----------|
| Q4   | AO3400A        | N-ch MOSFET              | SOT-23      | 1   | $0.25     |
| R23  | 1k 0402        | Gate resistor            | 0402        | 1   | $0.01     |
| R24  | 10k 0402       | Gate pull-down           | 0402        | 1   | $0.01     |
| J17  | B2B-XH-A(LF)(SN)| JST-XH 2-pin           | Through-hole| 1   | $0.14     |

### 10b. Status LEDs

Four indicator LEDs with current-limiting resistors, directly driven from FPGA GPIOs:

| LED    | Color  | GPIO         | Purpose              |
|--------|--------|-------------|----------------------|
| LED1   | Green  | GPIO_0[25]  | Power OK              |
| LED2   | Red    | GPIO_0[26]  | Armed                 |
| LED3   | Blue   | GPIO_0[27]  | Beacon Lock           |
| LED4   | Yellow | GPIO_0[28]  | Error / Warning       |

Each LED: 0603 SMD LED + 330-ohm 0402 series resistor (3.3V, ~5mA per LED).

| Ref    | Part Number          | Description           | Package | Qty | Unit Price |
|--------|---------------------|-----------------------|---------|-----|-----------|
| LED1   | 150060VS75000       | Green 0603 LED        | 0603    | 1   | $0.08     |
| LED2   | 150060RS75000       | Red 0603 LED          | 0603    | 1   | $0.08     |
| LED3   | 150060BS75000       | Blue 0603 LED         | 0603    | 1   | $0.10     |
| LED4   | 150060YS75000       | Yellow 0603 LED       | 0603    | 1   | $0.08     |
| R25-R28| 330R 0402           | LED current limiters  | 0402    | 4   | $0.01     |

### 10c. Emergency Stop Button Connector

2-pin JST-XH connector (J18) for a normally-closed momentary push button mounted on the drone frame:

```
3.3V ---[10k pull-up]---+--- GPIO_0[23] (ESTOP_IN)
                         |
                        [J18: ESTOP button, normally closed]
                         |
                        GND
```

When the button is pressed (NC opens), GPIO goes HIGH = emergency stop triggered.
When cable disconnects, GPIO goes HIGH = failsafe (same as e-stop).

### 10d. Arm Switch Input

2-pin JST-XH connector (J19) for an external arm/disarm toggle switch:

```
3.3V ---[10k pull-up]---+--- GPIO_0[22] (ARM_SWITCH_IN)
                         |
                        [J19: Toggle switch to GND]
                         |
                        GND
```

### 10e. Dock Detection

Simple contact sense for autonomous charging dock detection:

```
3.3V ---[10k pull-up]---+--- GPIO_0[24] (DOCK_DETECT_IN)
                         |
                        [100nF debounce cap]
                         |
                        [Pogo pin contact to dock GND]
                         |
                        GND
```

### 10f. Pogo Pin Charge Pads

Four pogo-pin landing pads on the bottom side of the PCB for autonomous charging dock:

| Pad | Signal  | Diameter | Notes                                    |
|-----|---------|----------|------------------------------------------|
| P1  | V+      | 3mm      | Battery charge input (16.8V max)          |
| P2  | GND     | 3mm      | Ground return                             |
| P3  | SENSE1  | 2mm      | Dock detection / handshake (to DOCK_DETECT)|
| P4  | SENSE2  | 2mm      | Charge status feedback                    |

Pads are exposed copper circles with ENIG finish, no solder mask. Route V+/GND through 2oz copper traces to handle charge current (1-2A).

### Miscellaneous Component List (additional)

| Ref    | Part Number         | Description                    | Package      | Qty | Unit Price |
|--------|--------------------|---------------------------------|-------------|-----|-----------|
| J18    | B2B-XH-A(LF)(SN)  | ESTOP connector                 | Through-hole | 1   | $0.14     |
| J19    | B2B-XH-A(LF)(SN)  | ARM switch connector            | Through-hole | 1   | $0.14     |
| R29-R31| 10k 0402           | Pull-ups (ESTOP, ARM, DOCK)     | 0402         | 3   | $0.01     |
| C28    | 100nF 0402         | Dock debounce cap               | 0402         | 1   | $0.02     |

**Subsystem cost**: ~$1.80

---

## 11. Mechanical Design

### Board Dimensions

- **Size**: 85mm x 100mm (fits within 450mm frame center section)
- **Shape**: Rectangular with rounded corners (2mm radius) and notch cut-outs for GPIO header clearance
- **Thickness**: 1.6mm (standard)

### Layer Stackup (4-layer)

| Layer | Purpose                              | Copper Weight |
|-------|--------------------------------------|---------------|
| L1    | Signal (top) + power components       | 1oz (35um)    |
| L2    | Ground plane (continuous)             | 1oz           |
| L3    | Power plane (5V, 3.3V, 1.8V splits)  | 1oz           |
| L4    | Signal (bottom) + pogo pads           | 1oz           |

**Why 4-layer**: The buck converter switching node (up to 480kHz with fast edges) needs a solid ground plane directly beneath it to contain EMI. A 2-layer board would require extensive ground stitching and would compromise signal integrity on the DVP camera bus and SPI bus. The cost difference at prototype quantities (JLCPCB) is ~$5 vs ~$2 for 5 boards.

### Mounting Holes

- 4x M3 mounting holes at corners (3.2mm drill, 6mm annular ring)
- Hole pattern: 75mm x 90mm (centered), compatible with standard drone mounting plates
- Additional 2x M2.5 holes matching DE10-Nano standoff pattern offset

### GPIO Header Sockets

- 2x **SSQ-120-03-G-D** (Samtec) or equivalent 2x20 female headers, 2.54mm pitch, 8.5mm insulation height
- These are through-hole and plug into DE10-Nano's GPIO0 (JP1) and GPIO1 (JP7) male headers
- The daughter board sits above the DE10-Nano with ~12mm standoff clearance

### Weight Estimate

| Item                      | Weight    |
|---------------------------|-----------|
| 4-layer PCB (85x100mm)    | 22g       |
| SMD components (all)       | 5g        |
| Through-hole connectors    | 8g        |
| GPIO female headers (2x)   | 4g        |
| XT60 connector             | 3g        |
| **Total bare board**       | **~42g**  |

### Connector Placement Map (top view)

```
+------------------------------------------------------------------+
|  [XT60]  [SMBJ]  [ARM_SW]  [BARREL]                             |
|  Battery Input & Power                          [LED1-4]         |
|                                                                   |
|  [TPS54560 Buck Area]    [INA219]                                |
|  L1, CIN, COUT                                                   |
|                                                                   |
|  [AP2112K]                                                        |
|  3.3V LDO          [BMP390]  [ICM-20948]                         |
|                              [SN74AVC4T245]                       |
|                              [TPS7A2018 1.8V]                     |
|                                                                   |
|  GPIO0 Socket                            GPIO1 Socket            |
|  [2x20 female]                           [2x20 female]           |
|                                                                   |
|  [TCA9548A]    [FPC Camera]                                      |
|  [J6-J11 ToF]  [TPS7A2028]  [TPS7A2015]                         |
|                                                                   |
|  [J12A IR]   [J16 PUMP]  [J17 BUZZER]  [WILC3000 Module]  >>>ANT |
|  [J18 ESTOP] [J19 ARM]   [J13 LTC]     [Antenna keep-out]  >>>  |
+------------------------------------------------------------------+
                                                        ^
                                                   Board edge
                                                   (antenna area)
```

### PCB Design Rules

- Minimum trace width: 6mil (0.15mm) for signals
- Minimum trace spacing: 6mil
- Power traces (VBATT): 40mil (1mm) minimum, 2oz copper preferred or use polygon pour
- Via size: 0.3mm drill / 0.6mm annular ring
- Thermal vias under TPS54560 and all QFN/exposed-pad ICs: 0.3mm drill, tented, 4-6 vias per pad

---

## Complete Bill of Materials (BOM) Summary

### Active Components

| Ref    | Part Number              | Description                          | Package      | Qty | Unit $ | Ext $  |
|--------|-------------------------|--------------------------------------|-------------|-----|--------|--------|
| U1-U4  | 74LVC1G17GW,125         | Schmitt buffer (DShot)               | SOT-353      | 4   | 0.22   | 0.88   |
| U5     | ICM-20948               | 9-axis IMU                           | QFN-24       | 1   | 8.50   | 8.50   |
| U6     | SN74AVC4T245RGYR        | 4-bit level translator               | VQFN-16      | 1   | 0.85   | 0.85   |
| U7     | TPS7A2018DBVR           | 1.8V LDO                            | SOT-23-5     | 1   | 0.55   | 0.55   |
| U8     | TPS7A2028DBVR           | 2.8V LDO (camera AVDD)              | SOT-23-5     | 1   | 0.55   | 0.55   |
| U9     | TPS7A2015DBVR           | 1.5V LDO (camera DVDD)              | SOT-23-5     | 1   | 0.55   | 0.55   |
| U10    | TCA9548APWR             | 8-ch I2C multiplexer                 | TSSOP-24     | 1   | 1.80   | 1.80   |
| U11    | BMP390                  | Barometric pressure sensor           | LGA-10       | 1   | 3.20   | 3.20   |
| U12    | ATWILC3000-MR110UB      | WiFi/BLE SPI module                  | Module       | 1   | 7.00   | 7.00   |
| U13    | TPS54560DDAR            | 5V/5A buck converter                 | HSOP-8       | 1   | 3.20   | 3.20   |
| U14    | AP2112K-3.3TRG1         | 3.3V/600mA LDO                      | SOT-23-5     | 1   | 0.38   | 0.38   |
| U15    | INA219BIDR              | Current/power monitor                | SOT-23-8     | 1   | 1.20   | 1.20   |

### Discrete Semiconductors

| Ref    | Part Number              | Description                          | Package      | Qty | Unit $ | Ext $  |
|--------|-------------------------|--------------------------------------|-------------|-----|--------|--------|
| Q1     | BSS138                  | N-ch MOSFET (IMU INT level shift)    | SOT-23       | 1   | 0.15   | 0.15   |
| Q2     | SI4435DDY               | P-ch MOSFET (reverse polarity)       | SO-8         | 1   | 0.85   | 0.85   |
| Q3     | AO3400A                 | N-ch MOSFET (pump driver)            | SOT-23       | 1   | 0.25   | 0.25   |
| Q4     | AO3400A                 | N-ch MOSFET (buzzer driver)          | SOT-23       | 1   | 0.25   | 0.25   |
| D1-D4  | PESD5V0S1BL,315         | TVS diode (DShot ESD)                | SOD-882      | 4   | 0.12   | 0.48   |
| D6     | SMBJ20A                 | TVS 20V (battery)                    | SMB          | 1   | 0.35   | 0.35   |
| D7     | BZX84C15                | 15V Zener (MOSFET gate)              | SOT-23       | 1   | 0.08   | 0.08   |
| D8     | SS14                    | 1A Schottky (pump flyback)           | SMA          | 1   | 0.12   | 0.12   |
| LED1   | 150060VS75000 (Wurth)   | Green 0603                           | 0603         | 1   | 0.08   | 0.08   |
| LED2   | 150060RS75000           | Red 0603                             | 0603         | 1   | 0.08   | 0.08   |
| LED3   | 150060BS75000           | Blue 0603                            | 0603         | 1   | 0.10   | 0.10   |
| LED4   | 150060YS75000           | Yellow 0603                          | 0603         | 1   | 0.08   | 0.08   |

### Passive Components

| Ref         | Value / Part             | Description                        | Package | Qty | Unit $ | Ext $  |
|-------------|-------------------------|------------------------------------|---------|-----|--------|--------|
| R1-R3       | 10k                     | IMU INT pull-ups, FSYNC            | 0402    | 3   | 0.01   | 0.03   |
| R4-R5       | 4.7k                    | Camera I2C pull-ups                | 0402    | 2   | 0.01   | 0.02   |
| R6-R7       | 4.7k                    | ToF upstream I2C pull-ups          | 0402    | 2   | 0.01   | 0.02   |
| R8-R11      | 100R                    | XSHUT series resistors (4 of 6 ToF)| 0402   | 4   | 0.01   | 0.04   |
| R14-R15     | 10k                     | BMP390 SDO/CSB pull-ups            | 0402    | 2   | 0.01   | 0.02   |
| R16A-D      | 4.7k                    | IR receiver pull-ups               | 0402    | 4   | 0.01   | 0.04   |
| R17-R18     | 10k                     | WILC3000 CHIP_EN/RESETN pull-ups   | 0402    | 2   | 0.01   | 0.02   |
| R19         | 150k 1%                 | Battery divider top                | 0402    | 1   | 0.02   | 0.02   |
| R20         | 27k 1%                  | Battery divider bottom             | 0402    | 1   | 0.02   | 0.02   |
| R21,R23     | 1k                      | MOSFET gate series (pump, buzzer)  | 0402    | 2   | 0.01   | 0.02   |
| R22,R24     | 10k                     | MOSFET gate pull-downs             | 0402    | 2   | 0.01   | 0.02   |
| R25-R28     | 330R                    | LED current limiters               | 0402    | 4   | 0.01   | 0.04   |
| R29-R31     | 10k                     | ESTOP/ARM/DOCK pull-ups            | 0402    | 3   | 0.01   | 0.03   |
| R_FB_T      | 100k 1%                 | Buck feedback top                  | 0402    | 1   | 0.02   | 0.02   |
| R_FB_B      | 24.9k 1%               | Buck feedback bottom               | 0402    | 1   | 0.02   | 0.02   |
| R_RT        | 100k                    | Buck freq set                      | 0402    | 1   | 0.01   | 0.01   |
| R_COMP      | 30.1k                   | Buck compensation                  | 0402    | 1   | 0.01   | 0.01   |
| R_EN1       | 1M                      | Buck UVLO top                      | 0402    | 1   | 0.01   | 0.01   |
| R_EN2       | 160k                    | Buck UVLO bottom                   | 0402    | 1   | 0.01   | 0.01   |
| R_SHUNT     | CSS2H-2512R-L010F       | 10mΩ 2W shunt                     | 2512    | 1   | 0.65   | 0.65   |
| L1          | SRP1265A-100M           | 10uH 6A inductor                   | 12.5mm  | 1   | 1.50   | 1.50   |
| CIN1-2      | 10uF/25V X7R            | Buck input                         | 1210    | 2   | 0.35   | 0.70   |
| COUT1-2     | 47uF/10V X7R            | Buck output                        | 1210    | 2   | 0.55   | 1.10   |
| C1-C4       | 100nF                   | Buffer decoupling                  | 0402    | 4   | 0.02   | 0.08   |
| C5          | 10uF                    | IMU VDD bulk                       | 0402    | 1   | 0.05   | 0.05   |
| C6-C8       | 100nF                   | IMU/translator decoupling          | 0402    | 3   | 0.02   | 0.06   |
| C9          | 1uF                     | IMU REGOUT                         | 0402    | 1   | 0.03   | 0.03   |
| C10         | 4.7uF                   | 1.8V LDO input                     | 0402    | 1   | 0.04   | 0.04   |
| C11         | 1uF                     | 1.8V LDO output                    | 0402    | 1   | 0.03   | 0.03   |
| C12-C13     | 4.7uF                   | Camera LDO inputs                  | 0402    | 2   | 0.04   | 0.08   |
| C14-C15     | 1uF                     | Camera LDO outputs                 | 0402    | 2   | 0.03   | 0.06   |
| C16-C17     | 10uF                    | Camera LDO bulk outputs            | 0603    | 2   | 0.08   | 0.16   |
| C18         | 100nF                   | TCA9548A decoupling                | 0402    | 1   | 0.02   | 0.02   |
| C19         | 10uF                    | TCA9548A bulk                      | 0603    | 1   | 0.08   | 0.08   |
| C20-C21     | 100nF                   | BMP390 decoupling                  | 0402    | 2   | 0.02   | 0.04   |
| C22-C25     | 100nF                   | IR receiver decoupling (4x)        | 0402    | 4   | 0.02   | 0.08   |
| C26         | 10uF                    | WILC3000 bulk decoupling           | 0603    | 1   | 0.08   | 0.08   |
| C27         | 100nF                   | WILC3000 decoupling                | 0402    | 1   | 0.02   | 0.02   |
| C28         | 1uF                     | WILC3000 RESETN RC                 | 0402    | 1   | 0.03   | 0.03   |
| C29         | 100nF                   | Dock debounce                      | 0402    | 1   | 0.02   | 0.02   |
| CBOOT       | 100nF/16V               | Buck bootstrap                     | 0402    | 1   | 0.02   | 0.02   |
| C_COMP      | 6.8nF                   | Buck compensation                  | 0402    | 1   | 0.02   | 0.02   |
| C_COMP2     | 68pF                    | Buck HF pole                       | 0402    | 1   | 0.02   | 0.02   |
| CSS         | 47nF                    | Buck soft-start                    | 0402    | 1   | 0.02   | 0.02   |
| C_LDO_IN    | 1uF                     | 3.3V LDO input                     | 0402    | 1   | 0.03   | 0.03   |
| C_LDO_OUT1  | 2.2uF                   | 3.3V LDO output                    | 0402    | 1   | 0.04   | 0.04   |
| C_LDO_OUT2  | 10uF                    | 3.3V LDO bulk output               | 0603    | 1   | 0.08   | 0.08   |

### Connectors

| Ref    | Part Number              | Description                          | Type         | Qty | Unit $ | Ext $  |
|--------|-------------------------|--------------------------------------|-------------|-----|--------|--------|
| J1-J4  | B3B-XH-A(LF)(SN)       | JST-XH 3-pin (ESC)                  | TH           | 4   | 0.18   | 0.72   |
| J5     | 5051102491 (Molex)      | 24-pin 0.5mm FPC ZIF (camera)       | SMD          | 1   | 0.65   | 0.65   |
| J6-J11 | SM04B-SRSS-TB(LF)(SN)  | JST-SH 4-pin (ToF sensors)          | SMD          | 6   | 0.35   | 2.10   |
| J12A-D | SM03B-SRSS-TB(LF)(SN)  | JST-SH 3-pin (IR receivers, 4x)     | SMD          | 4   | 0.30   | 1.20   |
| J13    | SM06B-SRSS-TB(LF)(SN)  | JST-SH 6-pin (LTC bridge cable)      | SMD          | 1   | 0.35   | 0.35   |
| J14    | XT60PW-M (Amass)        | XT60 battery input                   | TH           | 1   | 1.50   | 1.50   |
| J15    | PJ-102AH               | Barrel jack 5.5x2.1mm               | TH           | 1   | 0.60   | 0.60   |
| J16    | B2B-XH-A(LF)(SN)       | JST-XH 2-pin (pump)                 | TH           | 1   | 0.14   | 0.14   |
| J17    | B2B-XH-A(LF)(SN)       | JST-XH 2-pin (buzzer)               | TH           | 1   | 0.14   | 0.14   |
| J18    | B2B-XH-A(LF)(SN)       | JST-XH 2-pin (ESTOP)                | TH           | 1   | 0.14   | 0.14   |
| J19    | B2B-XH-A(LF)(SN)       | JST-XH 2-pin (ARM switch)           | TH           | 1   | 0.14   | 0.14   |
| SW1    | XT30PW-F (Amass)        | XT30 arm switch connector            | TH           | 1   | 0.80   | 0.80   |
| HDR1-2 | SSQ-120-03-G-D (Samtec) | 2x20 female header 2.54mm           | TH           | 2   | 1.80   | 3.60   |

---

## Cost Summary

| Category              | Extended Cost |
|-----------------------|---------------|
| Active ICs (12)       | $28.71        |
| Discrete semis (16)   | $2.91         |
| Passive components    | $7.55         |
| Connectors (19)       | $11.13        |
| **Component total**   | **$50.50**    |
| PCB fabrication (JLCPCB, 4-layer, 5pcs) | ~$12.00 ($2.40/board) |
| **Per-board total**   | **~$53.00**   |

### External Modules (purchased separately, not on daughter board BOM)

| Item                  | Approx. Cost  |
|-----------------------|---------------|
| 6x VL53L1X breakout   | $60.00        |
| 1x OV5640 camera module| $12.00       |
| 4x TSOP38238 IR receiver | $3.20      |
| 4x ESC (30A BLHeli32) | $60.00        |
| 4x BLDC motors        | $40.00        |
| 1x Peristaltic pump   | $8.00         |
| 1x Piezo buzzer       | $1.00         |
| Cables/wiring         | $10.00        |
| **External total**    | **~$194.20**  |

---

## I2C Address Map (shared bus on GPIO_1[5:6])

| Device      | Address (7-bit) | Notes                    |
|-------------|----------------|--------------------------|
| TCA9548A    | 0x70           | A0=A1=A2=GND             |
| BMP390      | 0x77           | SDO=VDD                  |
| INA219      | 0x40           | A0=A1=GND                |
| VL53L1X (x6)| 0x29          | Behind TCA9548A mux channels 0-5 |

No address conflicts.

---

## Signal Summary -- FPGA GPIO Utilization

### GPIO0 (JP1): 29 of 36 pins used

| Function          | Pins Used | GPIO Numbers     |
|-------------------|-----------|------------------|
| Camera DVP data   | 8         | GPIO_0[0-7]      |
| Camera control    | 8         | GPIO_0[8-15]     |
| DShot motor       | 4         | GPIO_0[16-19]    |
| Pump PWM          | 1         | GPIO_0[20]       |
| Buzzer PWM        | 1         | GPIO_0[21]       |
| Switches/inputs   | 3         | GPIO_0[22-24]    |
| Status LEDs       | 4         | GPIO_0[25-28]    |
| Spare             | 7         | GPIO_0[29-35]    |

### GPIO1 (JP7): 17 of 36 pins used

| Function          | Pins Used | GPIO Numbers     |
|-------------------|-----------|------------------|
| IMU SPI + INT     | 5         | GPIO_1[0-4]      |
| I2C bus (shared)  | 2         | GPIO_1[5-6]      |
| ToF mux reset     | 1         | GPIO_1[7]        |
| ToF XSHUT         | 4         | GPIO_1[8-11]     |
| IR beacon receivers| 4        | GPIO_1[12-15]    |
| INA219 alert      | 1         | GPIO_1[16]       |
| Spare             | 19        | GPIO_1[17-35]    |

---

## Design Review Checklist

- [x] All sensor I2C addresses verified non-conflicting
- [x] 1.8V level shifting for ICM-20948 SPI (SN74AVC4T245)
- [x] OV5640 DOVDD at 3.3V -- no level shifting needed for DVP bus
- [x] DShot600 at 3.3V -- compatible with standard ESCs
- [x] WILC3000 connects via HPS SPI1 on LTC connector (J10) -- no FPGA resources needed
- [x] IR receivers (TSOP38238) at 3.3V -- direct digital output, no level shifting
- [x] Battery UVLO set at ~13V (protects 4S LiPo from deep discharge)
- [x] Reverse polarity protection via P-MOSFET
- [x] TVS protection on battery and motor signal lines
- [x] All MOSFET gates have pull-downs for safe boot state
- [x] Emergency stop is fail-safe (open = stop)
- [x] Buck converter separated from analog sensors by >25mm
- [x] IMU has vibration isolation provisions (stress-relief slots)
- [x] Barometer has pressure vent hole
- [x] WILC3000 antenna keep-out zone defined
- [x] IR receivers at 4 board edges for 360-degree beacon coverage
- [x] ToF XSHUT_4/5 tradeoff documented (using mux isolation instead)
- [x] 19 spare GPIO1 + 7 spare GPIO0 pins available for future expansion
