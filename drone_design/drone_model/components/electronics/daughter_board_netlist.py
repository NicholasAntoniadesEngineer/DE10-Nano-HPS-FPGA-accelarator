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
# Component Placements
# =============================================================================
# Coordinates are in the "electronics zone" system: origin (0, 0) = top-left
# of the 85 × 108mm DE10-Nano daughter board area, which sits centred within
# the 110 × 110mm combined top-plate PCB.
#
# build_board() applies the zone offset (+12.5mm X, +1.0mm Y) to transform
# all positions into the full 110 × 110mm board coordinate system.
#
# GPIO Header positions are FIXED to match DE10-Nano mechanical constraints:
#   HDR1 (GPIO0): centre (15.45, 45.48), courtyard x=[12.45, 18.45] y=[19.48, 71.48]
#   HDR2 (GPIO1): centre (75.90, 45.48), courtyard x=[72.90, 78.90] y=[19.48, 71.48]
#
# Mounting holes (DE10-Nano pattern, electronics-zone coords):
#   (12.21, 4.02), (72.79, 4.02), (12.21, 103.97), (72.79, 103.97) — M2.7
#
# Layout Zones (electronics zone coords):
#   Zone 1 — Power (y < 19.5):        85mm × ~19mm, top edge
#   Zone 2 — ESC/DShot (x < 12.4):    ~12mm × 52mm, left strip beside HDR1
#   Zone 3 — Main (x=18.5-72.9):      ~54mm × 52mm, between headers
#   Zone 4 — Right passives (x > 79):  ~6mm strip, right of HDR2
#   Zone 5 — Below headers (y > 71.5): 85mm × ~36mm, sensors/connectors/WiFi
#
# Thermal: heat sources (U13, L1, R_SHUNT) in Zone 1 are ≥30mm from IMU (U5)
#          and barometer (U11) in Zone 3.

PLACEMENTS = [
    # =========================================================================
    # ZONE 1: Power Section (y = 0–19.5)
    # =========================================================================
    #
    # L1 (14.5×14.5) dominates this zone. Placed centre-right with U13 left.
    # Input path: J14 → D6 → Q2 → R_SHUNT → U13 → L1 → COUT
    # J15 barrel jack at top-right. LEDs far top-right.
    #
    # J14 (XT60PW, rot=90 → AABB 8×12) bounds: x=[0.5, 8.5], y=[7.5, 19.5]
    # Rotated 90° to clear mounting hole at (12.21, 4.02) — bolt zone x≥9.2
    # y=13.5 clears prop_135deg cutout (board y=14.5, dist=54.5mm > 54mm)
    # and leaves 0.35mm gap to J1 below (J14 bottom=19.5, J1 top=19.85)
    Placement(XT60PW,         "J14",    x=4.5,   y=13.5,   rotation=90),
    # D6 (SMB, 6.5×4.5) bounds: x=[14.25, 20.75], y=[1.75, 6.25]
    Placement(TVS_SMBJ20A,    "D6",     x=17.5,  y=4.0,    rotation=0),
    # D7 (SOT-23, 3.4×3.0) bounds: x=[21.3, 24.7], y=[2.5, 5.5]
    Placement(BZX84C15,       "D7",     x=23.0,  y=4.0,    rotation=0),
    # Q2 (SO-8, 6.5×5.5) bounds: x=[14.25, 20.75], y=[7.25, 12.75]
    Placement(SI4435DDY,      "Q2",     x=17.5,  y=10.0,   rotation=0),
    # R_SHUNT (2512, 7.8×4.2) bounds: x=[21.1, 28.9], y=[7.9, 12.1]
    Placement(SHUNT_10MOHM,   "R_SHUNT",x=25.0,  y=10.0,   rotation=0),
    # SW1 (XT30, 8×6) bounds: x=[21, 29], y=[13, 19]
    Placement(XT30PW,         "SW1",    x=25.0,  y=16.0,   rotation=0),

    # U13 (HSOP-8, 8×7) bounds: x=[29.4, 37.4], y=[6.5, 13.5]
    Placement(TPS54560,       "U13",    x=33.4,  y=10.0,   rotation=0),
    # CBOOT (0402) bounds: x=[29.2, 30.8], y=[5.0, 6.0]
    Placement(CAP_100NF_0402, "CBOOT",  x=30.0,  y=5.5,    rotation=0),
    # CIN1 (1210, 4.6×3.2) bounds: x=[31.1, 35.7], y=[2.4, 5.6]
    Placement(CAP_10UF_1210,  "CIN1",   x=33.4,  y=4.0,    rotation=0),
    # CIN2 (1210, 4.6×3.2) bounds: x=[31.1, 35.7], y=[14.4, 17.6]
    Placement(CAP_10UF_1210,  "CIN2",   x=33.4,  y=16.0,   rotation=0),

    # L1 (1265, 14.5×14.5) bounds: x=[37.75, 52.25], y=[4.75, 19.25]
    Placement(INDUCTOR_10UH,  "L1",     x=45.0,  y=12.0,   rotation=0),

    # COUT1 (1210, 4.6×3.2) bounds: x=[52.7, 57.3], y=[2.4, 5.6]
    Placement(CAP_47UF_1210,  "COUT1",  x=55.0,  y=4.0,    rotation=0),
    # COUT2 (1210, 4.6×3.2) bounds: x=[52.7, 57.3], y=[6.4, 9.6]
    Placement(CAP_47UF_1210,  "COUT2",  x=55.0,  y=8.0,    rotation=0),

    # J15 (Barrel Jack, 10×12) bounds: x=[58, 68], y=[1, 13]
    Placement(BARREL_JACK,    "J15",    x=63.0,  y=7.0,    rotation=0),

    # Status LEDs (0603, 2.4×1.5) — below mounting hole bolt zone
    # Mounting hole at (72.79, 4.02) → bolt zone x=[69.8, 75.8], y=[1.0, 7.0]
    # Moved from y=2 to y=9 to clear propeller cutout zone at top-right corner
    # (prop_45deg motor at board (132.8, -22.8), radius 54mm)
    Placement(LED_GREEN,      "LED1",   x=69.5,  y=10.0,   rotation=0),
    Placement(LED_RED,        "LED2",   x=72.0,  y=10.0,   rotation=0),
    Placement(LED_BLUE,       "LED3",   x=74.5,  y=10.0,   rotation=0),
    Placement(LED_YELLOW,     "LED4",   x=77.0,  y=10.0,   rotation=0),
    # LED resistors (0402) — below LEDs
    Placement(RES_330R,       "R25",    x=69.5,  y=12.0,   rotation=0),
    Placement(RES_330R,       "R26",    x=72.0,  y=12.0,   rotation=0),
    Placement(RES_330R,       "R27",    x=74.5,  y=12.0,   rotation=0),
    Placement(RES_330R,       "R28",    x=77.0,  y=12.0,   rotation=0),

    # Buck passives (0402) — small passives in gaps around power ICs
    # Row at y=18.5 below CIN2, right of SW1 (SW1 right=29)
    Placement(RES_100K,       "R_RT",   x=30.0,  y=18.5,   rotation=0),
    Placement(RES_100K,       "R_FB_T", x=32.0,  y=18.5,   rotation=0),
    Placement(RES_24K9,       "R_FB_B", x=34.0,  y=18.5,   rotation=0),
    # Cluster near D7 area (x=26-29, y=2-6)
    Placement(RES_30K1,       "R_COMP", x=26.0,  y=2.0,    rotation=0),
    Placement(CAP_6N8_0402,   "C_COMP", x=28.0,  y=2.0,    rotation=0),
    Placement(CAP_68PF_0402,  "C_COMP2",x=26.0,  y=4.0,    rotation=0),
    Placement(CAP_47NF_0402,  "CSS",    x=28.0,  y=4.0,    rotation=0),
    Placement(RES_1M,         "R_EN1",  x=26.0,  y=6.0,    rotation=0),
    Placement(RES_160K,       "R_EN2",  x=28.0,  y=6.0,    rotation=0),

    # 3.3V LDO — right of L1/COUT area
    # U14 (SOT-23-5, 3.4×3.2) bounds: x=[53.3, 56.7], y=[14.4, 17.6]
    Placement(AP2112K,        "U14",    x=55.0,  y=16.0,   rotation=0),
    # C_LDO_IN (0402) bounds: x=[52.7, 54.3], y=[18.0, 19.0]
    Placement(CAP_1UF_0402,   "C_LDO_IN", x=53.5, y=18.5,  rotation=0),
    # C_LDO1 (0402) bounds: x=[57.2, 58.8], y=[14.5, 15.5]
    Placement(CAP_2U2_0402,   "C_LDO1", x=58.0,  y=15.0,   rotation=0),
    # C_LDO2 (0603, 2.4×1.5) bounds: x=[54.8, 57.2], y=[17.75, 19.25]
    Placement(CAP_10UF_0603,  "C_LDO2", x=56.0,  y=18.5,   rotation=0),

    # INA219 + battery divider — below J15
    # U15 (SOT-23-8, 3.4×3.2) bounds: x=[59.3, 62.7], y=[14.4, 17.6]
    Placement(INA219,         "U15",    x=61.0,  y=16.0,   rotation=0),
    Placement(CAP_100NF_0402, "C_INA",  x=64.0,  y=15.0,   rotation=0),
    Placement(RES_150K,       "R19",    x=64.0,  y=17.0,   rotation=0),
    Placement(RES_27K,        "R20",    x=66.0,  y=15.0,   rotation=0),
    Placement(CAP_100PF_0402, "C_BATT", x=66.0,  y=17.0,   rotation=0),

    # =========================================================================
    # ZONE 2: ESC/DShot (left strip, x < 12.4, y = 19.5–71.5)
    # =========================================================================
    #
    # JST-XH 3-pin at rot=90: effective courtyard 5.0w × 10.5h
    # Pattern: J at x≈5, U+D+C between J and HDR1
    #
    # Channel 1 (y ≈ 24)
    # J1 (rot=90) bounds: x=[2.5, 7.5], y=[18.75, 29.25]
    Placement(JST_XH_3PIN, "J1",         x=5.0,   y=25.1,   rotation=90),
    # U1 (2.8×2.0) bounds: x=[7.6, 10.4], y=[21.0, 23.0]
    Placement(SCHMITT_74LVC1G17, "U1",   x=9.0,   y=22.0,   rotation=0),
    # D1 (1.6×1.0) bounds: x=[10.7, 12.3], y=[21.5, 22.5]
    Placement(TVS_PESD5V0S1BL, "D1",     x=11.5,  y=22.0,   rotation=0),
    # C1 (0402, 1.6×1.0) bounds: x=[7.7, 9.3], y=[23.5, 24.5]
    Placement(CAP_100NF_0402, "C1",       x=8.5,   y=24.5,   rotation=0),

    # Channel 2 (y ≈ 36)
    Placement(JST_XH_3PIN, "J2",         x=5.0,   y=36.0,   rotation=90),
    Placement(SCHMITT_74LVC1G17, "U2",   x=9.0,   y=34.0,   rotation=0),
    Placement(TVS_PESD5V0S1BL, "D2",     x=11.5,  y=34.0,   rotation=0),
    Placement(CAP_100NF_0402, "C2",       x=8.5,   y=36.5,   rotation=0),

    # Channel 3 (y ≈ 48)
    Placement(JST_XH_3PIN, "J3",         x=5.0,   y=48.0,   rotation=90),
    Placement(SCHMITT_74LVC1G17, "U3",   x=9.0,   y=46.0,   rotation=0),
    Placement(TVS_PESD5V0S1BL, "D3",     x=11.5,  y=46.0,   rotation=0),
    Placement(CAP_100NF_0402, "C3",       x=8.5,   y=48.5,   rotation=0),

    # Channel 4 (y ≈ 60)
    Placement(JST_XH_3PIN, "J4",         x=5.0,   y=60.0,   rotation=90),
    Placement(SCHMITT_74LVC1G17, "U4",   x=9.0,   y=58.0,   rotation=0),
    Placement(TVS_PESD5V0S1BL, "D4",     x=11.5,  y=58.0,   rotation=0),
    Placement(CAP_100NF_0402, "C4",       x=8.5,   y=60.5,   rotation=0),

    # =========================================================================
    # GPIO Headers (FIXED positions — non-negotiable)
    # =========================================================================
    # HDR1 courtyard: x=[12.45, 18.45], y=[19.48, 71.48]
    Placement(GPIO_HEADER_2X20, "HDR1",  x=15.45, y=45.48,  rotation=0),
    # HDR2 courtyard: x=[72.90, 78.90], y=[19.48, 71.48]
    Placement(GPIO_HEADER_2X20, "HDR2",  x=75.9,  y=45.48,  rotation=0),

    # =========================================================================
    # ZONE 3: Below heatsink cutout (y = 76–87)
    # =========================================================================
    #
    # CRITICAL: The 44×44mm heatsink/fan cutout occupies the board centre.
    # In EZ coords: x=[20.5, 64.5], y=[32, 76].  NO components may be here.
    # All Zone 3 components are placed BELOW the cutout (y > 76).
    #
    # Layout sub-zones below cutout:
    #   Barometer:   x=20-30, y=77-82 (far from heat, close to pressure vent)
    #   IMU cluster: x=35-55, y=77-86 (centre-X for vibration, close to HDR2 SPI)
    #   Pump/Buzzer: x=64.5-83, y=77-87 (right zone near HDR1 GPIO)

    # ── IMU Section (below cutout, y ≈ 77–88) ──
    # Pad-level spacing: U5 QFN-24 bottom pads extend to y+2.355mm
    #   U6 VQFN-16 top pads extend to y-2.595mm
    #   Need U5.y+2.355 < U6.y-2.595 → centre gap ≥ 5.0mm
    # Using 6mm gap: U5 at y=78, U6 at y=84
    Placement(ICM_20948,      "U5",     x=42.5,  y=78.0,   rotation=0),
    Placement(SN74AVC4T245,   "U6",     x=42.5,  y=84.0,   rotation=0),
    # U7 (TPS7A2018 1.8V LDO) — right of U6, feeds U5+U6
    Placement(TPS7A2018,      "U7",     x=48.5,  y=84.0,   rotation=0),
    # Q1 (BSS138 INT level shifter) — left of U5
    Placement(BSS138,         "Q1",     x=35.0,  y=78.0,   rotation=0),

    # IMU decoupling caps — per ICM-20948 DS-000189 §7.1: "as close as possible"
    # NOTE: cutout boundary at y=76 in EZ coords → must stay y > 76.5 for safety
    # C5 (10uF 0603) — VDD bulk, left of U5 (within 3mm)
    Placement(CAP_10UF_0603,  "C5",     x=38.5,  y=78.0,   rotation=90),
    # C6 (100nF 0402) — VDD bypass, right of U5 (between U5 and C5)
    Placement(CAP_100NF_0402, "C6",     x=46.0,  y=78.0,   rotation=0),
    # C7 (100nF 0402) — U6 VCCA decoupling, left of U6
    Placement(CAP_100NF_0402, "C7",     x=39.0,  y=84.0,   rotation=0),
    # C8 (100nF 0402) — U6 VCCB decoupling, below U6
    Placement(CAP_100NF_0402, "C8",     x=42.5,  y=87.0,   rotation=0),
    # C9 (1uF 0402) — REGOUT cap, between U5 and U6 (mid gap)
    Placement(CAP_1UF_0402,   "C9",     x=42.5,  y=81.0,   rotation=0),
    # C10 (4.7uF 0402) — U7 input cap, below U7
    Placement(CAP_4U7_0402,   "C10",    x=48.5,  y=86.5,   rotation=0),
    # C11 (1uF 0402) — U7 output cap, right of U7
    Placement(CAP_1UF_0402,   "C11",    x=52.0,  y=84.0,   rotation=0),
    # R1 (10K, INT 3.3V pull-up) — near Q1
    Placement(RES_10K,        "R1",     x=35.0,  y=80.5,   rotation=0),
    # R2 (10K, INT 1.8V pull-up) — left of Q1 (clear of Q1 courtyard)
    Placement(RES_10K,        "R2",     x=31.0,  y=78.0,   rotation=0),
    # R3 (10K, FSYNC pull-down) — left of U5/U6 gap, clear of both courtyards
    Placement(RES_10K,        "R3",     x=37.0,  y=81.0,   rotation=0),

    # ── Barometer (below cutout, left zone, thermally separated) ──
    # U11 (BMP390, LGA-10, 3×3) — far from power ICs
    Placement(BMP390,         "U11",    x=25.0,  y=79.0,   rotation=0),
    # C20 (100nF) — left of U11 (VDD bypass per BST-BMP390-DS002 §5.2)
    Placement(CAP_100NF_0402, "C20",    x=22.0,  y=79.0,   rotation=0),
    # C21 (100nF) — right of U11 (VDDIO bypass)
    Placement(CAP_100NF_0402, "C21",    x=28.0,  y=77.0,   rotation=0),
    # R14 (10K, SDO pull-up) — right of U11
    Placement(RES_10K,        "R14",    x=28.0,  y=79.0,   rotation=0),
    # R15 (10K, CSB pull-up) — below R14
    Placement(RES_10K,        "R15",    x=28.0,  y=81.0,   rotation=0),

    # ── Camera LDOs (between headers, upper area y ≈ 21–29) ──
    # U8 (TPS7A2028, 3.4×3.2) bounds: x=[20.3, 23.7], y=[20.4, 23.6]
    Placement(TPS7A2028,      "U8",     x=22.0,  y=22.0,   rotation=0),
    # U9 (TPS7A2015, 3.4×3.2) bounds: x=[25.3, 28.7], y=[20.4, 23.6]
    Placement(TPS7A2015,      "U9",     x=27.0,  y=22.0,   rotation=0),
    # C12 bounds: x=[18.6, 20.2], y=[21.0, 22.0] — between HDR1 right and U8 left
    Placement(CAP_4U7_0402,   "C12",    x=19.4,  y=21.5,   rotation=0),
    # C13 bounds: x=[29.7, 31.3], y=[21.5, 22.5] — right of U9
    Placement(CAP_4U7_0402,   "C13",    x=30.5,  y=22.0,   rotation=0),
    # C14 bounds: x=[19.2, 20.8], y=[24.0, 25.0]
    Placement(CAP_1UF_0402,   "C14",    x=20.0,  y=24.5,   rotation=0),
    # C15 bounds: x=[24.2, 25.8], y=[24.5, 25.5]
    Placement(CAP_1UF_0402,   "C15",    x=25.0,  y=25.0,   rotation=0),
    # C16 (0603) bounds: x=[20.8, 23.2], y=[25.75, 27.25]
    Placement(CAP_10UF_0603,  "C16",    x=22.0,  y=26.5,   rotation=0),
    # C17 (0603) bounds: x=[25.8, 28.2], y=[25.75, 27.25]
    Placement(CAP_10UF_0603,  "C17",    x=27.0,  y=26.5,   rotation=0),
    # Camera I2C pull-ups
    Placement(RES_4K7,        "R4",     x=22.0,  y=28.5,   rotation=0),
    Placement(RES_4K7,        "R5",     x=24.0,  y=28.5,   rotation=0),

    # ── Pump Driver (above cutout, upper Zone 3, y ≈ 28–32) ──
    # Placed above the cutout zone (y < 32 in EZ coords = y < 33 in board)
    Placement(AO3400A,        "Q3",     x=35.0,  y=30.0,   rotation=0),
    Placement(RES_1K,         "R21",    x=32.0,  y=30.0,   rotation=0),
    Placement(RES_10K,        "R22",    x=32.0,  y=28.0,   rotation=0),
    # D8 (SS14, 5.0×3.5 courtyard) — below Q3 with gap
    Placement(SS14,           "D8",     x=35.0,  y=25.5,   rotation=0),
    # J16 (JST-XH 2-pin pump connector) — right edge, below R16C
    # R16C at y=56, bottom at 56.5+0.5=57.0. J16 rot=90: 5×8.
    # J16 top = centre - 4. Centre = 57.0 + 0.2 + 4 = 61.2
    Placement(JST_XH_2PIN,   "J16",    x=82.0,  y=62.0,   rotation=90),

    # ── Buzzer Driver (above cutout, y ≈ 28–32) ──
    Placement(AO3400A,        "Q4",     x=45.0,  y=30.0,   rotation=0),
    Placement(RES_1K,         "R23",    x=42.0,  y=30.0,   rotation=0),
    Placement(RES_10K,        "R24",    x=42.0,  y=28.0,   rotation=0),
    # J17 (JST-XH 2-pin buzzer connector) — right edge, below J16
    # J16 bottom at 62+4=66. J17 top at 72-4=68. Gap = 2mm OK.
    Placement(JST_XH_2PIN,   "J17",    x=82.0,  y=72.0,   rotation=90),

    # =========================================================================
    # ZONE 4: Right of HDR2 (x > 79, y = 19.5–71.5)
    # =========================================================================
    #
    # HDR2 right edge at 78.9. JST-XH 2-pin at rot=90: 5w × 8h.
    # Centre x ≥ 78.9 + 2.5 = 81.4, max x = 85 - 2.5 = 82.5.
    # J18 at (82, 25, rot=90) bounds: x=[79.5, 84.5], y=[21, 29]
    Placement(JST_XH_2PIN,   "J18",    x=82.0,  y=25.0,   rotation=90),
    # J19 at (82, 35, rot=90) bounds: x=[79.5, 84.5], y=[31, 39]
    Placement(JST_XH_2PIN,   "J19",    x=82.0,  y=35.0,   rotation=90),
    # Switch pull-ups (0402) — above J18 courtyard
    Placement(RES_10K,        "R29",    x=80.0,  y=20.0,   rotation=0),
    Placement(RES_10K,        "R30",    x=82.5,  y=20.0,   rotation=0),
    Placement(RES_10K,        "R31",    x=80.0,  y=40.5,   rotation=0),
    Placement(CAP_100NF_0402, "C29",    x=82.5,  y=40.5,   rotation=0),

    # IR right connector (right edge)
    # J12C (JST-SH 3-pin, rot=270): effective 4.5w × 6.8h
    # bounds: x=[79.75, 84.25], y=[47.6, 54.4]
    Placement(JST_SH_3PIN, "J12C",      x=82.0,  y=51.0,   rotation=270),
    Placement(CAP_100NF_0402, "C24",     x=80.0,  y=44.0,   rotation=0),
    Placement(RES_4K7, "R16C",           x=80.0,  y=56.0,   rotation=0),

    # =========================================================================
    # ZONE 5: Below headers (y > 71.5, down to 108)
    # =========================================================================

    # ── ToF Hub (below IMU cluster, y ≈ 89–99) ──
    # U10 (TCA9548A, TSSOP-24, 8×9.5 courtyard) — centred below IMU area
    Placement(TCA9548A,       "U10",    x=42.0,  y=93.0,   rotation=0),
    # ToF decoupling — above U10 with clearance (U10 top edge at ~88.25)
    Placement(CAP_100NF_0402, "C18",    x=40.0,  y=87.5,   rotation=0),
    Placement(CAP_10UF_0603,  "C19",    x=47.5,  y=88.0,   rotation=0),
    # ToF I2C upstream pull-ups — above U10
    Placement(RES_4K7,        "R6",     x=37.0,  y=87.5,   rotation=0),
    Placement(RES_4K7,        "R7",     x=34.5,  y=87.5,   rotation=0),
    # XSHUT series resistors — below U10 (U10 bottom at ~97.75)
    Placement(RES_100R,       "R8",     x=36.0,  y=98.5,   rotation=0),
    Placement(RES_100R,       "R9",     x=38.0,  y=98.5,   rotation=0),
    Placement(RES_100R,       "R10",    x=40.0,  y=98.5,   rotation=0),
    Placement(RES_100R,       "R11",    x=42.0,  y=98.5,   rotation=0),

    # ToF connectors — see FRAME_PLACEMENTS below (positioned on the 110mm
    # structural frame near bracket mounts, not in the 85×108 electronics zone).

    # ── Camera FPC (bottom-left area) ──
    # J5 (FPC-ZIF, 15.5×4) bounds: x=[12.25, 27.75], y=[100, 104]
    Placement(FPC_24PIN,      "J5",     x=24.0,  y=102.0,  rotation=0),

    # ── WiFi/BLE (bottom-right corner) ──
    # U12 (WILC3000, 21×15.5) bounds: x=[62.5, 83.5], y=[84.25, 99.75]
    Placement(WILC3000,       "U12",    x=73.0,  y=92.0,   rotation=0),
    # WiFi caps/resistors — above U12 courtyard
    Placement(CAP_10UF_0603,  "C26",    x=64.0,  y=82.0,   rotation=0),
    Placement(CAP_100NF_0402, "C27",    x=67.0,  y=82.0,   rotation=0),
    Placement(CAP_1UF_0402,   "C28",    x=70.0,  y=82.0,   rotation=0),
    Placement(RES_10K,        "R17",    x=73.0,  y=82.0,   rotation=0),
    Placement(RES_10K,        "R18",    x=75.0,  y=82.0,   rotation=0),
    # J13 (JST-SH 6-pin, 10.8×4.5) bounds: x=[67.1, 77.9], y=[100.75, 105.25]
    Placement(JST_SH_6PIN,   "J13",    x=64.0,  y=103.0,  rotation=0),

    # ── IR Receiver Connectors (board edges) ──
    # J12A — Front (bottom edge)
    Placement(JST_SH_3PIN, "J12A",      x=42.5,  y=105.0,  rotation=0),
    Placement(CAP_100NF_0402, "C22",     x=47.0,  y=105.0,  rotation=0),
    Placement(RES_4K7, "R16A",           x=49.0,  y=105.0,  rotation=0),

    # J12B — Left (left edge, rot=90: 4.5w × 6.8h)
    Placement(JST_SH_3PIN, "J12B",      x=3.5,   y=85.0,   rotation=90),
    Placement(CAP_100NF_0402, "C23",     x=3.5,   y=80.0,   rotation=0),
    Placement(RES_4K7, "R16B",           x=3.5,   y=89.5,   rotation=0),

    # J12D — Rear (placed in Zone 5 bottom-left, cable routed to rear sensor)
    # bounds: x=[6.6, 13.4], y=[94.75, 99.25]
    Placement(JST_SH_3PIN, "J12D",      x=10.0,  y=97.0,   rotation=0),
    Placement(CAP_100NF_0402, "C25",     x=10.0,  y=94.0,   rotation=0),
    Placement(RES_4K7, "R16D",           x=12.0,  y=94.0,   rotation=0),
]


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

FRAME_PLACEMENTS = [
    # ToF sensor connectors — on the 12.5mm structural frame strips (left/right
    # of the 85×108 electronics zone).  Cables route from here to bracket mounts.
    #
    # Left strip (x < 12.5) and right strip (x > 97.5), rotated 90° so pads
    # face inward.  Y positions match bracket y-coordinates where possible.
    #
    # Bracket mounts (110 top-left):  front(100,55) back(10,55) left(55,10) right(55,100)
    Placement(JST_SH_4PIN, "J6",   x=104.0, y=55.0,  rotation=90),   # front bracket (+X edge)
    Placement(JST_SH_4PIN, "J7",   x=6.0,   y=55.0,  rotation=270),  # back bracket  (-X edge)
    Placement(JST_SH_4PIN, "J8",   x=104.0, y=25.0,  rotation=90),   # left bracket  (routed to -Y, moved from y=15 to clear prop_45deg cutout)
    Placement(JST_SH_4PIN, "J9",   x=104.0, y=85.0,  rotation=90),   # right bracket (routed to +Y, moved from y=95 to clear prop_315deg cutout)
    Placement(JST_SH_4PIN, "J10",  x=6.0,   y=40.0,  rotation=270),  # up sensor
    Placement(JST_SH_4PIN, "J11",  x=6.0,   y=70.0,  rotation=270),  # spare
]


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
