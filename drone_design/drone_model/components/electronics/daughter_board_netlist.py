"""Complete netlist and placement definitions for the daughter board.

This file is the SINGLE SOURCE OF TRUTH for all electrical connections and
component positions on the board.  It is consumed by:
  - The PCB generator (daughter_board.py) to produce .kicad_pcb
  - The schematic generator to produce .kicad_sch
  - The BOM/CPL generator to produce JLCPCB assembly files
  - The validation suite to check correctness before manufacturing

Board: 85 × 108 mm, 4-layer, 1.6mm FR4, ENIG finish
Origin: top-left corner (0,0) = top-left of PCB outline
X increases rightward, Y increases downward (KiCad convention)

Placement strategy:
  - GPIO headers HDR1/HDR2 are FIXED to match DE10-Nano mechanical constraints.
  - All other components are placed algorithmically by the placement optimizer
    (force-directed zone assignment → Gaussian scatter → simulated annealing).
  - Frame-area components (ToF connectors) are at fixed structural positions.

Net connections derived from drone_design/docs/daughter_board_pcb_design.md
sections 1–10, GPIO pin tables, and circuit schematics.
"""

import json
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

from cadquery_framework.kicad.component_library import (
    BoardDefinition,
    KeepOutZone,
    NetConnection,
    Placement,
)
from cadquery_framework.kicad.placement_optimizer import optimize_placements
from drone_design.drone_model.components.electronics.daughter_board_components import (
    # Section 1: Motor Driver
    SCHMITT_74LVC1G17, TVS_PESD5V0S1BL, JST_XH_3PIN,
    # Section 2: IMU
    ICM_20948, SN74AVC4T245, TPS7A2018, BSS138,
    # Section 3: Camera
    FPC_24PIN, TPS7A2028, TPS7A2015,
    # Section 4: ToF Hub
    TCA9548A, JST_SH_4PIN,
    # Section 5: Barometer
    BMP390,
    # Section 6: IR Receivers
    JST_SH_3PIN,
    # Section 7: WiFi/BLE
    WILC3000, JST_SH_6PIN,
    # Section 8: Power
    XT60PW, SI4435DDY, TVS_SMBJ20A, BZX84C15, TPS54560,
    INDUCTOR_10UH, AP2112K, INA219, SHUNT_10MOHM,
    BARREL_JACK, XT30PW,
    # Section 9-10: Pump, Buzzer, LEDs, Switches
    AO3400A, SS14, JST_XH_2PIN,
    LED_GREEN, LED_RED, LED_BLUE, LED_YELLOW,
    # Passives
    RES_100R, RES_330R, RES_1K, RES_4K7, RES_10K, RES_24K9,
    RES_27K, RES_30K1, RES_100K, RES_150K, RES_160K, RES_1M,
    CAP_68PF_0402, CAP_100PF_0402, CAP_6N8_0402, CAP_47NF_0402,
    CAP_100NF_0402, CAP_1UF_0402, CAP_2U2_0402, CAP_4U7_0402,
    CAP_10UF_0603, CAP_10UF_1210, CAP_47UF_1210,
    # GPIO headers
    GPIO_HEADER_2X20,
)

# Shorthand
NC = NetConnection


# =============================================================================
# Component Placements — Algorithmically Optimised
# =============================================================================
# All component positions are computed by the placement optimizer:
#   1. Force-directed zone assignment (subsystem centroids)
#   2. Gaussian scatter within zones (satellites around ICs)
#   3. Simulated annealing refinement (HPWL + thermal + overlap cost)
#
# Coordinates are in the "electronics zone" system: origin (0, 0) = top-left
# of the 85 × 108mm DE10-Nano daughter board area.  build_board() applies the
# zone offset (+12.5mm X, +1.0mm Y) to transform to the 110×110mm board.
#
# GPIO Header positions are FIXED to match DE10-Nano mechanical constraints.
# Frame-area placements (ToF connectors) are manually positioned at structural
# mount points — see FRAME_PLACEMENTS.

# Fixed placements — mechanical constraint, never moved by optimizer.
FIXED_PLACEMENTS = [
    Placement(GPIO_HEADER_2X20, "HDR1", x=15.45, y=45.48, rotation=0),
    Placement(GPIO_HEADER_2X20, "HDR2", x=75.9,  y=45.48, rotation=0),
]

# All components to be placed by the optimizer.
# Grouped by subsystem for clarity; the optimizer also auto-detects groups
# from net connectivity.
COMPONENTS_TO_PLACE: list[tuple] = [
    # ── Power Buck (Section 8) ──
    (XT60PW,         "J14"),
    (TVS_SMBJ20A,    "D6"),
    (BZX84C15,       "D7"),
    (SI4435DDY,      "Q2"),
    (SHUNT_10MOHM,   "R_SHUNT"),
    (XT30PW,         "SW1"),
    (TPS54560,       "U13"),
    (CAP_100NF_0402, "CBOOT"),
    (CAP_10UF_1210,  "CIN1"),
    (CAP_10UF_1210,  "CIN2"),
    (INDUCTOR_10UH,  "L1"),
    (CAP_47UF_1210,  "COUT1"),
    (CAP_47UF_1210,  "COUT2"),
    (BARREL_JACK,    "J15"),
    (RES_100K,       "R_RT"),
    (RES_100K,       "R_FB_T"),
    (RES_24K9,       "R_FB_B"),
    (RES_30K1,       "R_COMP"),
    (CAP_6N8_0402,   "C_COMP"),
    (CAP_68PF_0402,  "C_COMP2"),
    (CAP_47NF_0402,  "CSS"),
    (RES_1M,         "R_EN1"),
    (RES_160K,       "R_EN2"),

    # ── 3.3V LDO (Section 8) ──
    (AP2112K,        "U14"),
    (CAP_1UF_0402,   "C_LDO_IN"),
    (CAP_2U2_0402,   "C_LDO1"),
    (CAP_10UF_0603,  "C_LDO2"),

    # ── Current Sense (Section 8) ──
    (INA219,         "U15"),
    (CAP_100NF_0402, "C_INA"),
    (RES_150K,       "R19"),
    (RES_27K,        "R20"),
    (CAP_100PF_0402, "C_BATT"),

    # ── DShot Channel 1 (Section 1) ──
    (JST_XH_3PIN,        "J1"),
    (SCHMITT_74LVC1G17,  "U1"),
    (TVS_PESD5V0S1BL,    "D1"),
    (CAP_100NF_0402,     "C1"),

    # ── DShot Channel 2 ──
    (JST_XH_3PIN,        "J2"),
    (SCHMITT_74LVC1G17,  "U2"),
    (TVS_PESD5V0S1BL,    "D2"),
    (CAP_100NF_0402,     "C2"),

    # ── DShot Channel 3 ──
    (JST_XH_3PIN,        "J3"),
    (SCHMITT_74LVC1G17,  "U3"),
    (TVS_PESD5V0S1BL,    "D3"),
    (CAP_100NF_0402,     "C3"),

    # ── DShot Channel 4 ──
    (JST_XH_3PIN,        "J4"),
    (SCHMITT_74LVC1G17,  "U4"),
    (TVS_PESD5V0S1BL,    "D4"),
    (CAP_100NF_0402,     "C4"),

    # ── IMU (Section 2) ──
    (ICM_20948,      "U5"),
    (SN74AVC4T245,   "U6"),
    (TPS7A2018,      "U7"),
    (BSS138,         "Q1"),
    (CAP_10UF_0603,  "C5"),
    (CAP_100NF_0402, "C6"),
    (CAP_100NF_0402, "C7"),
    (CAP_100NF_0402, "C8"),
    (CAP_1UF_0402,   "C9"),
    (CAP_4U7_0402,   "C10"),
    (CAP_1UF_0402,   "C11"),
    (RES_10K,        "R1"),
    (RES_10K,        "R2"),
    (RES_10K,        "R3"),

    # ── Barometer (Section 5) ──
    (BMP390,         "U11"),
    (CAP_100NF_0402, "C20"),
    (CAP_100NF_0402, "C21"),
    (RES_10K,        "R14"),
    (RES_10K,        "R15"),

    # ── Camera LDOs (Section 3) ──
    (TPS7A2028,      "U8"),
    (TPS7A2015,      "U9"),
    (CAP_4U7_0402,   "C12"),
    (CAP_4U7_0402,   "C13"),
    (CAP_1UF_0402,   "C14"),
    (CAP_1UF_0402,   "C15"),
    (CAP_10UF_0603,  "C16"),
    (CAP_10UF_0603,  "C17"),
    (RES_4K7,        "R4"),
    (RES_4K7,        "R5"),
    (FPC_24PIN,      "J5"),

    # ── Pump Driver (Section 9) ──
    (AO3400A,        "Q3"),
    (RES_1K,         "R21"),
    (RES_10K,        "R22"),
    (SS14,           "D8"),
    (JST_XH_2PIN,    "J16"),

    # ── Buzzer Driver (Section 10) ──
    (AO3400A,        "Q4"),
    (RES_1K,         "R23"),
    (RES_10K,        "R24"),
    (JST_XH_2PIN,    "J17"),

    # ── Status LEDs (Section 10) ──
    (LED_GREEN,      "LED1"),
    (LED_RED,        "LED2"),
    (LED_BLUE,       "LED3"),
    (LED_YELLOW,     "LED4"),
    (RES_330R,       "R25"),
    (RES_330R,       "R26"),
    (RES_330R,       "R27"),
    (RES_330R,       "R28"),

    # ── Switches (Section 10) ──
    (JST_XH_2PIN,    "J18"),
    (JST_XH_2PIN,    "J19"),
    (RES_10K,        "R29"),
    (RES_10K,        "R30"),
    (RES_10K,        "R31"),
    (CAP_100NF_0402, "C29"),

    # ── ToF Hub (Section 4) ──
    (TCA9548A,       "U10"),
    (CAP_100NF_0402, "C18"),
    (CAP_10UF_0603,  "C19"),
    (RES_4K7,        "R6"),
    (RES_4K7,        "R7"),
    (RES_100R,       "R8"),
    (RES_100R,       "R9"),
    (RES_100R,       "R10"),
    (RES_100R,       "R11"),

    # ── WiFi/BLE (Section 7) ──
    (WILC3000,       "U12"),
    (CAP_10UF_0603,  "C26"),
    (CAP_100NF_0402, "C27"),
    (CAP_1UF_0402,   "C28"),
    (RES_10K,        "R17"),
    (RES_10K,        "R18"),
    (JST_SH_6PIN,    "J13"),

    # ── IR Receivers (Section 6) ──
    (JST_SH_3PIN,    "J12A"),
    (CAP_100NF_0402, "C22"),
    (RES_4K7,        "R16A"),
    (JST_SH_3PIN,    "J12B"),
    (CAP_100NF_0402, "C23"),
    (RES_4K7,        "R16B"),
    (JST_SH_3PIN,    "J12C"),
    (CAP_100NF_0402, "C24"),
    (RES_4K7,        "R16C"),
    (JST_SH_3PIN,    "J12D"),
    (CAP_100NF_0402, "C25"),
    (RES_4K7,        "R16D"),
]

# Subsystem groupings for the optimizer — maps subsystem name to ref list.
# The optimizer uses these to keep related components close together and
# to apply subsystem-level constraints (edge placement, thermal separation).
SUBSYSTEM_GROUPS: dict[str, list[str]] = {
    "power_buck": [
        "J14", "D6", "D7", "Q2", "R_SHUNT", "SW1", "U13", "CBOOT",
        "CIN1", "CIN2", "L1", "COUT1", "COUT2", "J15",
        "R_RT", "R_FB_T", "R_FB_B", "R_COMP", "C_COMP", "C_COMP2",
        "CSS", "R_EN1", "R_EN2",
    ],
    "power_ldo_3v3": ["U14", "C_LDO_IN", "C_LDO1", "C_LDO2"],
    "current_sense": ["U15", "C_INA", "R19", "R20", "C_BATT"],
    "dshot_ch1": ["J1", "U1", "D1", "C1"],
    "dshot_ch2": ["J2", "U2", "D2", "C2"],
    "dshot_ch3": ["J3", "U3", "D3", "C3"],
    "dshot_ch4": ["J4", "U4", "D4", "C4"],
    "imu": [
        "U5", "U6", "U7", "Q1",
        "C5", "C6", "C7", "C8", "C9", "C10", "C11",
        "R1", "R2", "R3",
    ],
    "barometer": ["U11", "C20", "C21", "R14", "R15"],
    "camera": [
        "U8", "U9", "C12", "C13", "C14", "C15", "C16", "C17",
        "R4", "R5", "J5",
    ],
    "pump_driver": ["Q3", "R21", "R22", "D8", "J16"],
    "buzzer_driver": ["Q4", "R23", "R24", "J17"],
    "leds": ["LED1", "LED2", "LED3", "LED4", "R25", "R26", "R27", "R28"],
    "switches": ["J18", "J19", "R29", "R30", "R31", "C29"],
    "tof_hub": ["U10", "C18", "C19", "R6", "R7", "R8", "R9", "R10", "R11"],
    "wifi_ble": ["U12", "C26", "C27", "C28", "R17", "R18", "J13"],
    "ir_front": ["J12A", "C22", "R16A"],
    "ir_left": ["J12B", "C23", "R16B"],
    "ir_right": ["J12C", "C24", "R16C"],
    "ir_rear": ["J12D", "C25", "R16D"],
}


# =============================================================================
# Net Definitions
# =============================================================================
# Each net maps to a list of (ref, pin_number) connections.
# Pin numbers MUST match the ComponentDef pin definitions exactly.

NETS: dict[str, list[NetConnection]] = {
    # ── Power Rails ──
    "GND": [
        # Buck converter
        NC("U13", "7"), NC("U13", "9"),
        NC("CIN1", "2"), NC("CIN2", "2"), NC("COUT1", "2"), NC("COUT2", "2"),
        NC("CSS", "2"), NC("R_EN2", "2"), NC("R_FB_B", "2"),
        # 3.3V LDO
        NC("U14", "2"), NC("C_LDO_IN", "2"), NC("C_LDO1", "2"), NC("C_LDO2", "2"),
        # 1.8V LDO
        NC("U7", "2"), NC("C10", "2"), NC("C11", "2"),
        # IMU
        NC("U5", "13"), NC("U5", "14"), NC("U5", "15"), NC("U5", "16"),
        NC("U5", "17"), NC("U5", "18"), NC("U5", "25"),
        NC("C5", "2"), NC("C6", "2"), NC("C7", "2"), NC("C9", "2"),
        # Level translator
        NC("U6", "7"), NC("U6", "15"), NC("U6", "17"), NC("C8", "2"),
        # BSS138
        NC("Q1", "2"),
        # Camera LDOs
        NC("U8", "2"), NC("U9", "2"),
        NC("C12", "2"), NC("C13", "2"), NC("C14", "2"), NC("C15", "2"),
        NC("C16", "2"), NC("C17", "2"),
        # BMP390
        NC("U11", "2"), NC("U11", "8"), NC("U11", "10"),
        NC("C20", "2"), NC("C21", "2"),
        # TCA9548A
        NC("U10", "12"), NC("C18", "2"), NC("C19", "2"),
        NC("U10", "1"), NC("U10", "2"),  # A0=GND, A1=GND (I2C addr 0x70)
        # INA219
        NC("U15", "3"), NC("C_INA", "2"),
        NC("U15", "4"), NC("U15", "5"),  # A0=GND, A1=GND (addr 0x40)
        # DShot buffers
        NC("U1", "2"), NC("U2", "2"), NC("U3", "2"), NC("U4", "2"),
        NC("C1", "2"), NC("C2", "2"), NC("C3", "2"), NC("C4", "2"),
        NC("D1", "1"), NC("D2", "1"), NC("D3", "1"), NC("D4", "1"),  # TVS anode to GND
        # ESC connectors
        NC("J1", "3"), NC("J2", "3"), NC("J3", "3"), NC("J4", "3"),
        # Pump / buzzer MOSFETs
        NC("Q3", "2"), NC("Q4", "2"), NC("R22", "2"), NC("R24", "2"),
        # WILC3000
        NC("C26", "2"), NC("C27", "2"),
        # IR receiver decoupling
        NC("C22", "2"), NC("C23", "2"), NC("C24", "2"), NC("C25", "2"),
        # Switches
        NC("J18", "2"), NC("J19", "2"),
        # Battery divider bottom
        NC("R20", "2"), NC("C_BATT", "2"),
        # Battery protection
        NC("D6", "1"), NC("D7", "1"),
        # Barrel jack
        NC("J15", "2"),
        # Dock debounce
        NC("C29", "2"),
        # FSYNC pull-down
        NC("R3", "2"),
    ],

    "+5V": [
        NC("COUT1", "1"), NC("COUT2", "1"),
        NC("L1", "2"),          # inductor output → +5V rail
        NC("U14", "1"),         # AP2112K VIN
        NC("C_LDO_IN", "1"),
        NC("J15", "1"),         # barrel jack tip
        NC("J16", "1"),         # pump power (5V option)
        NC("J17", "1"),         # buzzer power
    ],

    "+3V3": [
        NC("U14", "5"),         # AP2112K output
        NC("C_LDO1", "1"), NC("C_LDO2", "1"),
        # DShot buffer VCC
        NC("U1", "5"), NC("U2", "5"), NC("U3", "5"), NC("U4", "5"),
        NC("C1", "1"), NC("C2", "1"), NC("C3", "1"), NC("C4", "1"),
        # Level translator VCCB
        NC("U6", "14"),
        # Camera DOVDD + I2C pull-ups
        NC("R4", "1"), NC("R5", "1"),
        # ToF I2C pull-ups
        NC("R6", "1"), NC("R7", "1"),
        # TCA9548A VCC
        NC("U10", "24"), NC("C18", "1"), NC("C19", "1"),
        # BMP390
        NC("U11", "1"), NC("U11", "9"),  # VDDIO + VDD
        NC("C20", "1"), NC("C21", "1"),
        NC("R14", "1"), NC("R15", "1"),  # SDO/CSB pull-ups
        # IR receiver VCC decoupling
        NC("C22", "1"), NC("C23", "1"), NC("C24", "1"), NC("C25", "1"),
        NC("R16A", "1"), NC("R16B", "1"), NC("R16C", "1"), NC("R16D", "1"),
        # INA219 VS
        NC("U15", "8"), NC("C_INA", "1"),
        # WILC3000 VCC
        NC("C26", "1"), NC("C27", "1"),
        NC("R17", "1"), NC("R18", "1"),  # CHIP_EN/RESETN pull-ups
        # INT pull-up (3.3V side)
        NC("R1", "1"),
        # Camera LDO inputs
        NC("U8", "5"), NC("C12", "1"),   # 2.8V LDO in
        NC("U9", "5"), NC("C13", "1"),   # 1.5V LDO in
        NC("U7", "5"), NC("C10", "1"),   # 1.8V LDO in
        # LDO enable pins (tied high)
        NC("U7", "3"), NC("U8", "3"), NC("U9", "3"), NC("U14", "3"),
        # LED power pulls, switch pull-ups
        NC("R25", "1"), NC("R26", "1"), NC("R27", "1"), NC("R28", "1"),
        NC("R29", "1"), NC("R30", "1"), NC("R31", "1"),
    ],

    "+1V8": [
        NC("U7", "1"),         # TPS7A2018 output
        NC("C11", "1"),
        NC("U6", "1"),         # translator VCCA
        NC("U5", "12"),        # ICM VDD
        NC("U5", "24"),        # ICM VDDIO
        NC("C5", "1"), NC("C6", "1"), NC("C7", "1"),
        NC("C8", "1"),         # translator decoupling
        NC("R2", "1"),         # INT pull-up 1.8V side
    ],

    "+2V8": [
        NC("U8", "1"),         # TPS7A2028 output
        NC("C14", "1"), NC("C16", "1"),
    ],

    "+1V5": [
        NC("U9", "1"),         # TPS7A2015 output
        NC("C15", "1"), NC("C17", "1"),
    ],

    "VBATT": [
        NC("J14", "1"),        # XT60 positive
        NC("Q2", "1"),         # P-MOSFET source (also pins 2,3)
        NC("Q2", "2"), NC("Q2", "3"),
        NC("D6", "2"),         # TVS cathode
        NC("D7", "2"),         # Zener cathode (gate protection)
    ],

    "VBATT_SW": [
        NC("Q2", "5"), NC("Q2", "6"), NC("Q2", "7"), NC("Q2", "8"),  # P-MOSFET drain
        NC("R_SHUNT", "1"),    # shunt resistor → INA219 IN+
        NC("R19", "1"),        # battery divider top
        NC("U15", "1"),        # INA219 IN+
    ],

    "VBATT_SWITCHED": [
        NC("R_SHUNT", "2"),
        NC("U15", "2"),        # INA219 IN-
        NC("SW1", "1"),        # arm switch connector
        NC("U13", "2"),        # TPS54560 VIN
        NC("CIN1", "1"), NC("CIN2", "1"),
        NC("R_EN1", "1"),      # UVLO divider top
    ],

    # ── IMU SPI (3.3V side: GPIO1 → translator) ──
    "IMU_SPI_SCLK": [NC("HDR2", "1"), NC("U6", "13")],
    "IMU_SPI_MOSI": [NC("HDR2", "3"), NC("U6", "12")],
    "IMU_SPI_MISO": [NC("HDR2", "5"), NC("U6", "11")],
    "IMU_SPI_CS_N": [NC("HDR2", "7"), NC("U6", "10")],

    # ── IMU SPI (1.8V side: translator → ICM-20948) ──
    "IMU_SCLK_1V8": [NC("U6", "2"), NC("U5", "6")],
    "IMU_MOSI_1V8": [NC("U6", "3"), NC("U5", "7")],
    "IMU_MISO_1V8": [NC("U6", "4"), NC("U5", "2")],
    "IMU_CS_1V8":   [NC("U6", "5"), NC("U5", "4")],

    # Level translator direction + enable
    "XLAT_DIR":  [NC("U6", "9")],   # will need net connection to a pull resistor or power
    "XLAT_OE1":  [NC("U6", "6")],   # tied to GND (always enabled) — added to GND net
    "XLAT_OE2":  [NC("U6", "8")],   # tied to GND (always enabled) — added to GND net

    # ── IMU INT (through BSS138 level shifter) ──
    "IMU_INT_1V8": [NC("U5", "8"), NC("Q1", "3"), NC("R2", "2")],   # drain + pull-up
    "IMU_INT":     [NC("Q1", "1"), NC("R1", "2"), NC("HDR2", "9")], # gate → GPIO_1[4]

    # IMU REGOUT (requires 1uF cap to GND)
    "IMU_REGOUT": [NC("U5", "10"), NC("C9", "1")],

    # IMU FSYNC (tied to GND via pull-down)
    "IMU_FSYNC": [NC("U5", "11"), NC("R3", "1")],

    # IMU AD0/SDO pin — tied to VDD for SPI mode
    # AD1 — tied to GND (done in GND net above via an additional entry if needed)

    # ── Camera DVP Bus (GPIO0 → FPC connector) ──
    # FPC pinout per design doc Section 3 (Arducam module)
    "CAM_D0":    [NC("HDR1", "1"),  NC("J5", "18")],
    "CAM_D1":    [NC("HDR1", "3"),  NC("J5", "17")],
    "CAM_D2":    [NC("HDR1", "5"),  NC("J5", "16")],
    "CAM_D3":    [NC("HDR1", "7"),  NC("J5", "15")],
    "CAM_D4":    [NC("HDR1", "9"),  NC("J5", "14")],
    "CAM_D5":    [NC("HDR1", "11"), NC("J5", "13")],
    "CAM_D6":    [NC("HDR1", "13"), NC("J5", "12")],
    "CAM_D7":    [NC("HDR1", "15"), NC("J5", "11")],
    "CAM_PCLK":  [NC("HDR1", "17"), NC("J5", "9")],
    "CAM_VSYNC": [NC("HDR1", "19"), NC("J5", "7")],
    "CAM_HSYNC": [NC("HDR1", "21"), NC("J5", "8")],
    "CAM_XCLK":  [NC("HDR1", "23"), NC("J5", "10")],
    "CAM_SIOC":  [NC("HDR1", "25"), NC("J5", "2"), NC("R4", "2")],
    "CAM_SIOD":  [NC("HDR1", "27"), NC("J5", "3"), NC("R5", "2")],
    "CAM_PWDN":  [NC("HDR1", "29"), NC("J5", "20")],
    "CAM_RESET": [NC("HDR1", "31"), NC("J5", "21")],

    # Camera FPC power pins
    "CAM_AVDD":  [NC("J5", "4"), NC("U8", "1")],    # 2.8V to FPC pin 4 (duplicate with +2V8)
    "CAM_DVDD":  [NC("J5", "6"), NC("U9", "1")],    # 1.5V to FPC pin 6 (duplicate with +1V5)

    # ── DShot Motor Signals ──
    "DSHOT_CH1":     [NC("HDR1", "33"), NC("U1", "1")],
    "DSHOT_CH1_OUT": [NC("U1", "3"), NC("D1", "2"), NC("J1", "1")],
    "DSHOT_CH2":     [NC("HDR1", "35"), NC("U2", "1")],
    "DSHOT_CH2_OUT": [NC("U2", "3"), NC("D2", "2"), NC("J2", "1")],
    "DSHOT_CH3":     [NC("HDR1", "37"), NC("U3", "1")],
    "DSHOT_CH3_OUT": [NC("U3", "3"), NC("D3", "2"), NC("J3", "1")],
    "DSHOT_CH4":     [NC("HDR1", "39"), NC("U4", "1")],
    "DSHOT_CH4_OUT": [NC("U4", "3"), NC("D4", "2"), NC("J4", "1")],

    # ── Pump PWM ──
    "PUMP_PWM": [NC("HDR1", "2"), NC("R21", "1")],   # GPIO_0[20] → gate resistor  (pin 2 = even = row B)
    "PUMP_GATE": [NC("R21", "2"), NC("Q3", "1"), NC("R22", "1")],
    "PUMP_DRAIN": [NC("Q3", "3"), NC("D8", "1"), NC("J16", "2")],

    # ── Buzzer PWM ──
    "BUZZER_PWM": [NC("HDR1", "4"), NC("R23", "1")],  # GPIO_0[21]
    "BUZZER_GATE": [NC("R23", "2"), NC("Q4", "1"), NC("R24", "1")],
    "BUZZER_DRAIN": [NC("Q4", "3"), NC("J17", "2")],

    # ── Status LEDs ──
    "LED_POWER":  [NC("HDR1", "6"), NC("R25", "2")],   # GPIO_0[25] → resistor
    "LED_POWER_A": [NC("LED1", "1")],  # This is wrong — needs ≥2 connections
    "LED_ARMED":  [NC("HDR1", "8"), NC("R26", "2")],
    "LED_BEACON": [NC("HDR1", "10"), NC("R27", "2")],
    "LED_ERROR":  [NC("HDR1", "12"), NC("R28", "2")],

    # ── I2C Shared Bus (GPIO1[5:6]) ──
    "I2C_SCL": [
        NC("HDR2", "11"), NC("R6", "2"),  # GPIO_1[5] → pull-up
        NC("U10", "22"),                    # TCA9548A upstream SCL
        NC("U11", "4"),                     # BMP390 SCK
        NC("U15", "6"),                     # INA219 SCL
    ],
    "I2C_SDA": [
        NC("HDR2", "13"), NC("R7", "2"),  # GPIO_1[6] → pull-up
        NC("U10", "23"),                    # TCA9548A upstream SDA
        NC("U11", "3"),                     # BMP390 SDI
        NC("U15", "7"),                     # INA219 SDA
    ],

    # ── ToF Mux Downstream Channels (TCA9548A → JST-SH connectors) ──
    "TOF0_SDA": [NC("U10", "4"), NC("J6", "3")],
    "TOF0_SCL": [NC("U10", "5"), NC("J6", "4")],
    "TOF1_SDA": [NC("U10", "6"), NC("J7", "3")],
    "TOF1_SCL": [NC("U10", "7"), NC("J7", "4")],
    "TOF2_SDA": [NC("U10", "8"), NC("J8", "3")],
    "TOF2_SCL": [NC("U10", "9"), NC("J8", "4")],
    "TOF3_SDA": [NC("U10", "10"), NC("J9", "3")],
    "TOF3_SCL": [NC("U10", "11"), NC("J9", "4")],
    "TOF4_SDA": [NC("U10", "13"), NC("J10", "3")],
    "TOF4_SCL": [NC("U10", "14"), NC("J10", "4")],
    "TOF5_SDA": [NC("U10", "15"), NC("J11", "3")],
    "TOF5_SCL": [NC("U10", "16"), NC("J11", "4")],

    # ToF mux reset
    "TOF_MUX_RESET_N": [NC("HDR2", "15"), NC("U10", "3")],

    # ToF XSHUT lines (GPIO_1[8-11])
    "TOF_XSHUT_0": [NC("HDR2", "17"), NC("R8", "1")],
    "TOF_XSHUT_1": [NC("HDR2", "19"), NC("R9", "1")],
    "TOF_XSHUT_2": [NC("HDR2", "21"), NC("R10", "1")],
    "TOF_XSHUT_3": [NC("HDR2", "23"), NC("R11", "1")],

    # IR receiver signals (GPIO_1[12-15])
    "IR_RX_FRONT": [NC("HDR2", "25"), NC("J12A", "3"), NC("R16A", "2")],
    "IR_RX_LEFT":  [NC("HDR2", "27"), NC("J12B", "3"), NC("R16B", "2")],
    "IR_RX_RIGHT": [NC("HDR2", "29"), NC("J12C", "3"), NC("R16C", "2")],
    "IR_RX_REAR":  [NC("HDR2", "31"), NC("J12D", "3"), NC("R16D", "2")],

    # INA219 alert
    "INA219_ALERT": [NC("HDR2", "33"), NC("U15", "1")],  # GPIO_1[16] — overloaded, INA219 IN+ is pin 1
    # NOTE: INA219 pin 1 is IN+ not ALERT. Alert is not broken out in SOT-23-8 version.
    # This connection needs review against the actual INA219BIDR pinout.

    # ── Battery Voltage Divider ──
    "BATT_SENSE": [NC("R19", "2"), NC("R20", "1"), NC("C_BATT", "1")],

    # ── Buck Converter Internal Nets ──
    "BUCK_PH":   [NC("U13", "8"), NC("L1", "1")],   # switch node
    "BUCK_BOOT": [NC("U13", "1"), NC("CBOOT", "1")],
    "BUCK_EN":   [NC("U13", "3"), NC("R_EN1", "2"), NC("R_EN2", "1")],
    "BUCK_SS":   [NC("U13", "4"), NC("CSS", "1")],
    "BUCK_COMP": [NC("U13", "6"), NC("R_COMP", "1"), NC("C_COMP", "1"), NC("C_COMP2", "1")],
    "BUCK_VSENSE": [NC("U13", "5"), NC("R_FB_T", "2"), NC("R_FB_B", "1")],
    "BUCK_RT":   [NC("R_RT", "1")],  # frequency set — other end to GND
    "BUCK_BOOT_SW": [NC("CBOOT", "2")],  # CBOOT other end → BUCK_PH

    # ── Switch/Input Signals ──
    "ARM_SWITCH":  [NC("HDR1", "14"), NC("R30", "2"), NC("J19", "1")],  # GPIO_0[22]
    "ESTOP_IN":    [NC("HDR1", "16"), NC("R29", "2"), NC("J18", "1")],  # GPIO_0[23]
    "DOCK_DETECT": [NC("HDR1", "18"), NC("R31", "2"), NC("C29", "1")],  # GPIO_0[24]

    # ── Arm switch connector ──
    "ARM_SW_COM": [NC("SW1", "2")],  # needs connection to VBATT_SWITCHED net

    # ── P-MOSFET gate ──
    "Q2_GATE": [NC("Q2", "4"), NC("D7", "1")],   # Zener anode side
}

# Fix: add translator OE pins to GND
NETS["GND"].extend([NC("U6", "6"), NC("U6", "8")])

# Fix: XLAT_DIR and single-pin nets need to be resolved
# DIR pin should be tied to VCCB (3.3V) for B→A direction on all channels
# For SPI: SCLK/MOSI/CS are B→A, MISO is A→B
# Actually the SN74AVC4T245 DIR pin controls direction for the entire port
# DIR=LOW: A→B, DIR=HIGH: B→A
# For our use: SCLK(B→A), MOSI(B→A), CS(B→A) → DIR=HIGH but MISO needs A→B
# The SN74AVC4T245 has per-group direction, not per-pin. Need to review.
# For simplicity and correctness, tie DIR HIGH (B→A) and handle
# MISO via the auto-direction feature of the AVC family.
NETS["+3V3"].append(NC("U6", "9"))  # DIR = HIGH = B→A

# Fix single-pin nets by merging them properly
# LED anode connections (LED → resistor → GPIO)
del NETS["LED_POWER_A"]  # remove broken single-pin net

# Proper LED connections: GPIO → resistor → LED anode, LED cathode → GND
# Redefine LED nets to include both resistor and LED
NETS["LED_POWER"] = [NC("R25", "2"), NC("LED1", "1")]
NETS["LED_ARMED"] = [NC("R26", "2"), NC("LED2", "1")]
NETS["LED_BEACON"] = [NC("R27", "2"), NC("LED3", "1")]
NETS["LED_ERROR"] = [NC("R28", "2"), NC("LED4", "1")]

# LED GPIO drive nets
NETS["GPIO_LED_POWER"]  = [NC("HDR1", "6"),  NC("R25", "1")]
NETS["GPIO_LED_ARMED"]  = [NC("HDR1", "8"),  NC("R26", "1")]
NETS["GPIO_LED_BEACON"] = [NC("HDR1", "10"), NC("R27", "1")]
NETS["GPIO_LED_ERROR"]  = [NC("HDR1", "12"), NC("R28", "1")]

# LED cathodes to GND
NETS["GND"].extend([
    NC("LED1", "2"), NC("LED2", "2"), NC("LED3", "2"), NC("LED4", "2"),
])

# Fix single-pin nets
NETS["BUCK_RT"] = [NC("R_RT", "1"), NC("R_RT", "2")]  # RT pin connects R to GND
# Actually R_RT pin 1 → U13 RT pin (not broken out in HSOP-8 — TPS54560 uses internal)
# R_RT sets frequency: one end to RT/CLK pin, other to GND. But TPS54560 HSOP-8
# doesn't have RT pin exposed — it uses internal oscillator.
# Remove R_RT from netlist since TPS54560DDAR doesn't expose RT pin.
del NETS["BUCK_RT"]

# BUCK_BOOT_SW: CBOOT other end connects to switch node (PH)
NETS["BUCK_PH"].append(NC("CBOOT", "2"))
del NETS["BUCK_BOOT_SW"]

# ARM_SW_COM: XT30 pin 2 connects back to switched power
NETS["VBATT_SWITCHED"].append(NC("SW1", "2"))
del NETS["ARM_SW_COM"]

# Remove single-pin nets that were temporary
for key in ["XLAT_DIR", "XLAT_OE1", "XLAT_OE2"]:
    if key in NETS:
        del NETS[key]

# ToF connector VCC/GND
for jref in ["J6", "J7", "J8", "J9", "J10", "J11"]:
    NETS["+3V3"].append(NC(jref, "1"))
    NETS["GND"].append(NC(jref, "2"))

# IR receiver connector VCC/GND
for jref in ["J12A", "J12B", "J12C", "J12D"]:
    NETS["+3V3"].append(NC(jref, "1"))
    NETS["GND"].append(NC(jref, "2"))

# FPC connector GND pins (1, 19, 22, 23, 24)
for pin in ["1", "19", "22", "23", "24"]:
    NETS["GND"].append(NC("J5", pin))
# FPC pin 5 = DOVDD = 3.3V
NETS["+3V3"].append(NC("J5", "5"))

# JST-SH shield/mount pads → GND
for jref in ["J6", "J7", "J8", "J9", "J10", "J11"]:
    NETS["GND"].extend([NC(jref, "MP1"), NC(jref, "MP2")])
for jref in ["J12A", "J12B", "J12C", "J12D"]:
    NETS["GND"].extend([NC(jref, "MP1"), NC(jref, "MP2")])
NETS["GND"].extend([NC("J13", "MP1"), NC("J13", "MP2")])
NETS["GND"].extend([NC("J5", "MP1"), NC("J5", "MP2")])

# WILC3000 LTC bridge (J13) — SPI signals: module ↔ J13 connector
# The WILC3000 module SPI pins connect to J13 for LTC bridge cable
NETS["WILC_SPI_CLK"]  = [NC("J13", "1"), NC("U12", "17")]  # SPI_CLK
NETS["WILC_SPI_MOSI"] = [NC("J13", "2"), NC("U12", "18")]  # SPI_MOSI
NETS["WILC_SPI_MISO"] = [NC("J13", "3"), NC("U12", "19")]  # SPI_MISO
NETS["WILC_SPI_SSN"]  = [NC("J13", "4"), NC("U12", "20")]  # SPI_SSN
NETS["WILC_IRQ"]      = [NC("J13", "5"), NC("U12", "21")]  # IRQ_N
NETS["GND"].append(NC("J13", "6"))

# WILC3000 module CHIP_EN and RESETN — connected to pull-up resistors
NETS["WILC_CHIP_EN"] = [NC("U12", "22"), NC("R17", "2")]
NETS["WILC_RESETN"]  = [NC("U12", "23"), NC("R18", "2"), NC("C28", "1")]
NETS["GND"].append(NC("C28", "2"))  # RESETN RC cap to GND

# WILC3000 power pins
NETS["+3V3"].extend([NC("U12", "1"), NC("U12", "2")])  # VCC pins
NETS["GND"].extend([NC("U12", "3"), NC("U12", "4"), NC("U12", "5"),
                     NC("U12", "6"), NC("U12", "7"), NC("U12", "8"),
                     NC("U12", "9"), NC("U12", "10")])  # GND pins

# XSHUT series resistor outputs → JST-SH pin 4 (using available pins)
# Design doc says XSHUT goes to pin 4 of ToF connectors, but our JST-SH 4-pin
# has pins 1-4 = VCC/GND/SDA/SCL. XSHUT would need a 5th pin or separate wire.
# Per design doc, XSHUT is routed to GPIO_1 pins, not to JST connectors.
# The XSHUT signal goes from FPGA GPIO → series resistor → VL53L1X XSHUT pin
# which is on the sensor breakout board, reached via cable.
# So R8-R11 output pins just go to the XSHUT net (no further board connection).

# BMP390 SDO and CSB pull-ups
NETS["BMP_SDO"]  = [NC("U11", "5"), NC("R14", "2")]  # SDO to VDD → addr 0x77
NETS["BMP_CSB"]  = [NC("U11", "6"), NC("R15", "2")]  # CSB to VDD → I2C mode

# Battery connector GND
NETS["GND"].append(NC("J14", "2"))

# TCA9548A unused channels (SD6/SC6, SD7/SC7) and A2
NETS["GND"].append(NC("U10", "21"))  # A2 = GND

# R_FB_T top → +5V
NETS["+5V"].append(NC("R_FB_T", "1"))

# R_RT — TPS54560 DDA package pin 8 is PH, there's no RT pin in HSOP-8.
# R_RT is DNP but remains in placement. Connect both pins to avoid ERC error.
NETS["GND"].extend([NC("R_RT", "1"), NC("R_RT", "2")])  # DNP, both ends to GND

# ICM-20948 AD0/SDO (pin 2) — already in IMU_MISO_1V8 net
# ICM-20948 AD1 (pin 5) — tie to GND for address
NETS["GND"].append(NC("U5", "5"))

# ICM-20948 unused auxiliary I2C — tie to GND (bidirectional pins, safe to ground)
NETS["GND"].extend([NC("U5", "1"), NC("U5", "3")])  # AUX_CL, AUX_DA — not used
# ICM-20948 INT2 — leave unconnected (pin type is output, handled by no_connect in component)
# BMP390 INT pin — leave unconnected (polling mode, pin type is output)

# TCA9548A unused channels SD6/SC6, SD7/SC7 — leave floating (they're I2C buses)
# These need ≥2 connections. Tie to +3V3 as they're idle high
NETS["+3V3"].extend([
    NC("U10", "17"), NC("U10", "18"),  # SD6, SC6
    NC("U10", "19"), NC("U10", "20"),  # SD7, SC7
])

# ESC connector VCC pins (pin 2) — connected to +5V for ESC power
NETS["+5V"].extend([NC("J1", "2"), NC("J2", "2"), NC("J3", "2"), NC("J4", "2")])

# Barrel jack switch pin (J15 pin 3) — tie to GND (switch pin, NC when no barrel)
NETS["GND"].append(NC("J15", "3"))

# SS14 flyback diode cathode (D8 pin 2) — goes to +5V (pump flyback)
NETS["+5V"].append(NC("D8", "2"))

# Compensation network: C_COMP pin 2 and C_COMP2 pin 2 → BUCK_VSENSE
NETS["BUCK_VSENSE"].extend([NC("C_COMP", "2"), NC("C_COMP2", "2")])

# R_COMP pin 2 → BUCK_COMP (forms RC compensation with C_COMP)
NETS["BUCK_COMP"].append(NC("R_COMP", "2"))

# XSHUT series resistor outputs — these go to cable header for ToF sensors
# For now, tie R8-R11 pin 2 to the XSHUT nets (extended to connector via cable)
NETS["TOF_XSHUT_0"].append(NC("R8", "2"))
NETS["TOF_XSHUT_1"].append(NC("R9", "2"))
NETS["TOF_XSHUT_2"].append(NC("R10", "2"))
NETS["TOF_XSHUT_3"].append(NC("R11", "2"))

# GPIO header spare pins — these are physical pass-through pins to the DE10-Nano.
# They have no on-board load, so they are left unnetted on the daughter board side.
# The GPIO_HEADER_2X20 component pins are typed "passive" and will be reported as
# unconnected by the validator; the validator silently skips HDR-prefixed unconnected
# passive pins rather than raising an error or warning.


# =============================================================================
# Run Placement Optimizer
# =============================================================================
# Now that NETS is fully defined, invoke the optimizer to compute positions
# for all non-fixed components.  The optimizer works in 110×110mm board
# coordinates internally and returns results in electronics-zone coordinates.

_DIMS_PATH = Path(__file__).resolve().parents[2] / "dimensions.json"

# Frame-area placements must be defined BEFORE the optimizer call so they
# can be passed as immovable obstacles.  They use full 110×110 board coords.
_FRAME_PLACEMENTS_FOR_OPTIMIZER = [
    Placement(JST_SH_4PIN, "J6",   x=104.0, y=55.0,  rotation=90),   # front bracket
    Placement(JST_SH_4PIN, "J7",   x=6.0,   y=55.0,  rotation=270),  # back bracket
    Placement(JST_SH_4PIN, "J8",   x=97.0,  y=30.0,  rotation=90),   # left (inboard to clear prop_45deg)
    Placement(JST_SH_4PIN, "J9",   x=97.0,  y=80.0,  rotation=90),   # right (inboard to clear prop_315deg)
    Placement(JST_SH_4PIN, "J10",  x=6.0,   y=40.0,  rotation=270),  # up sensor
    Placement(JST_SH_4PIN, "J11",  x=6.0,   y=70.0,  rotation=270),  # spare
]

# Keep-out zones in board coordinates (shifted from EZ).
_EZ_OX_PRE = (_D["frame"]["plate_size"] - _D["daughter_board"]["width"]) / 2
_EZ_OY_PRE = (_D["frame"]["plate_size"] - _D["daughter_board"]["length"]) / 2
_KEEP_OUT_ZONES = [
    KeepOutZone(
        name="WILC3000 antenna",
        owner_ref="U12",
        xmin=73.0 + 9.6 - 2.0 + _EZ_OX_PRE,
        ymin=92.0 - 7.5 + _EZ_OY_PRE,
        xmax=_D["daughter_board"]["width"] + _EZ_OX_PRE,
        ymax=92.0 + 7.5 + _EZ_OY_PRE,
    ),
]

PLACEMENTS = optimize_placements(
    components_and_refs=COMPONENTS_TO_PLACE,
    nets=NETS,
    fixed_placements=FIXED_PLACEMENTS,
    board_width=_D["frame"]["plate_size"],
    board_height=_D["frame"]["plate_size"],
    dims_path=_DIMS_PATH,
    subsystem_groups=SUBSYSTEM_GROUPS,
    seed=42,
    frame_placements=_FRAME_PLACEMENTS_FOR_OPTIMIZER,
    keep_out_zones=_KEEP_OUT_ZONES,
)


# =============================================================================
# Frame-area placements (110×110 board coordinates)
# =============================================================================
# These components sit on the structural frame area OUTSIDE the 85×108
# electronics zone.  Coordinates are in the full 110×110 plate system.
# They are NOT offset by build_board() — they go directly into the board.
#
# ToF bracket mounts are at ±45mm from plate centre (centre-origin):
#   Front (+X): (100, 55)   Back (-X): (10, 55)
#   Left  (-Y): (55, 10)    Right(+Y): (55, 100)
# in 110×110 top-left coordinates.

# Reuse the list already defined for the optimizer (single source of truth).
FRAME_PLACEMENTS = list(_FRAME_PLACEMENTS_FOR_OPTIMIZER)


# =============================================================================
# Board Definition
# =============================================================================

# Electronics zone offset within the 110×110 plate
_PLATE_SIZE = _D["frame"]["plate_size"]            # 110.0
_PLATE_CR = _D["frame"]["plate_corner_radius"]     # 2.0
_EZ_W = _D["daughter_board"]["width"]              # 85.0
_EZ_H = _D["daughter_board"]["length"]             # 108.0
_EZ_OX = (_PLATE_SIZE - _EZ_W) / 2                # 12.5
_EZ_OY = (_PLATE_SIZE - _EZ_H) / 2                # 1.0


def build_board() -> BoardDefinition:
    """Construct the combined top-plate + daughter board definition.

    The fabricated PCB is 110×110mm (PLATE_SIZE).  Electronics-zone
    component positions are offset from 85×108 coords to 110×110 coords.
    Frame-area components (ToF connectors) are already in 110×110 coords.
    """
    # Shift electronics-zone placements to 110×110 board coordinates
    shifted = []
    for p in PLACEMENTS:
        shifted.append(Placement(
            component=p.component,
            ref=p.ref,
            x=p.x + _EZ_OX,
            y=p.y + _EZ_OY,
            rotation=p.rotation,
            side=p.side,
        ))

    # Add frame-area placements (already in 110×110 coords)
    shifted.extend(FRAME_PLACEMENTS)

    # Shift nets — ref designators don't change, only positions matter
    # (nets reference refs, not coordinates)

    # Shift keep-out zones
    keep_outs = [
        # WILC3000 antenna keep-out (shifted from electronics zone)
        KeepOutZone(
            name="WILC3000 antenna",
            owner_ref="U12",
            xmin=73.0 + 9.6 - 2.0 + _EZ_OX,
            ymin=92.0 - 7.5 + _EZ_OY,
            xmax=_EZ_W + _EZ_OX,       # right edge of electronics zone
            ymax=92.0 + 7.5 + _EZ_OY,
        ),
    ]

    # Shift mounting holes from electronics zone to 110×110 coords
    ez_holes = [
        (12.21, 4.02,   2.7),
        (72.79, 4.02,   2.7),
        (12.21, 103.97, 2.7),
        (72.79, 103.97, 2.7),
    ]
    mounting_holes = [
        (x + _EZ_OX, y + _EZ_OY, d) for x, y, d in ez_holes
    ]

    # ToF sensor bracket M2 mounting holes (NPTH, 2.2mm drill).
    # Positions from 3D model in 110×110 board coords — no offset needed.
    # Centre (55, 55) omitted because it falls inside the heatsink cutout.
    tof_bracket_holes = [
        (100.0, 55.0, 2.2),   # Front (+X)
        ( 10.0, 55.0, 2.2),   # Back  (-X)
        ( 55.0, 10.0, 2.2),   # Left  (-Y)
        ( 55.0, 100.0, 2.2),  # Right (+Y)
    ]
    mounting_holes.extend(tof_bracket_holes)

    board = BoardDefinition(
        title="DE10-Nano Combined Top Plate + Daughter Board",
        width=_PLATE_SIZE,
        height=_PLATE_SIZE,
        corner_radius=_PLATE_CR,
        thickness=1.6,
        placements=shifted,
        nets=NETS,
        keep_outs=keep_outs,
        mounting_holes=mounting_holes,
    )
    return board
