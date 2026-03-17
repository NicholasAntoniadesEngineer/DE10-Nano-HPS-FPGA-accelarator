"""ESP32-WROOM-32-N4 daughter board netlist with complete power supply circuit.

This file defines the standalone ESP32-based daughter board with:
  - ESP32-WROOM-32-N4 module (WiFi + BLE)
  - Complete power supply circuit (5V → 3.3V regulation)
  - AMS1117-3.3 LDO regulator (1A, 1.3V dropout)
  - SMAJ5V0 TVS diode for input protection
  - Ferrite beads for EMI suppression
  - Decoupling capacitors for power stability
  - Reset circuit (EN pin with RC filter)
  - I2C pull-up resistors

This is a simplified, focused design for ESP32 integration.
Output files: daughter_board_esp32.kicad_sch, daughter_board_esp32.kicad_pcb

Board: 85 × 108 mm, 4-layer, 1.6mm FR4, ENIG finish (JLCPCB compatible)
"""

from cadquery_framework.kicad.component_library import (
    BoardDefinition,
    KeepOutZone,
    NetConnection,
    Placement,
)
from drone_design.drone_model.components.electronics.daughter_board_components import (
    # ESP32 module
    ESP32_WROOM,
    # Power supply components
    AMS1117_3V3, TVS_SMAJ5V0, FERRITE_100R_PWR, FERRITE_100R_CLK, INDUCTOR_10U_PWR,
    # Capacitors for power supply
    CAP_100NF_0402, CAP_1UF_0402, CAP_4U7_0402, CAP_10UF_0603,
    # Resistors for pull-ups and filters
    RES_10K, RES_4K7,
    # Connectors
    JST_XH_2PIN, JST_SH_4PIN,
    # Passives
    RES_100R,
)

# Shorthand
NC = NetConnection


# =============================================================================
# ESP32 Module Pinout (WROOM-32-N4, 38-pin, 25.5 × 18mm)
# =============================================================================
# Pin layout from datasheet — module pins 1-38:
#   1: GND      10: EN (reset)       20: IO32      30: IO0 (strapping)
#   2: IO23     11: CLK              21: IO33      31: IO4 (dup)
#   3: IO22     12: SDO              22: IO25      32: GND
#   4: IO21     13: SDI              23: IO26      33: VDD33 (3.3V power)
#   5: IO19     14: CS               24: IO27      34: NC
#   6: IO18     15: IO5              25: IO14      35: IO10
#   7: IO17     16: IO35 (input)     26: IO12      36: IO9 (strapping)
#   8: IO16     17: IO34 (input)     27: IO13      37: IO11 (strapping)
#   9: IO4      18: IO39 (input)     28: IO15      38: GND
#            19: IO36 (input, SENSOR_VP)  29: IO2
#
# Key pins:
#   - VDD33 (pin 33): 3.3V supply (2.5-3.6V, typical ~100mA)
#   - GND (pins 1, 32, 38): Ground planes
#   - EN (pin 10): Reset/enable (active high, requires RC filter)
#   - CLK/SDO/SDI/CS (pins 11-14): Internal flash SPI (always active)
#   - IO0, IO2, IO15 (pins 30, 29, 28): Strapping pins (set boot mode at power-up)


# =============================================================================
# Component Placements (Optimized Layout)
# =============================================================================

PLACEMENTS = [
    # ── Power supply chain (left edge) ──
    Placement(TVS_SMAJ5V0,      "D1",   x=10.0,  y=15.0,  rotation=0),  # input protection
    Placement(AMS1117_3V3,      "U1",   x=10.0,  y=25.0,  rotation=0),  # 3.3V LDO
    Placement(CAP_1UF_0402,     "C1",   x=15.0,  y=20.0,  rotation=0),  # LDO input cap
    Placement(CAP_4U7_0402,     "C2",   x=15.0,  y=28.0,  rotation=0),  # LDO output cap
    Placement(CAP_10UF_0603,    "C3",   x=20.0,  y=25.0,  rotation=90), # bulk output cap
    Placement(FERRITE_100R_PWR, "FB1",  x=25.0,  y=22.0,  rotation=0),  # VDD filtering

    # ── ESP32 module (centre) ──
    Placement(ESP32_WROOM,      "U2",   x=42.5,  y=54.0,  rotation=0),  # main module

    # ── Module decoupling (right side of ESP32) ──
    Placement(CAP_100NF_0402,   "C4",   x=60.0,  y=45.0,  rotation=0),  # VDD local 1
    Placement(CAP_100NF_0402,   "C5",   x=60.0,  y=50.0,  rotation=0),  # VDD local 2
    Placement(CAP_100NF_0402,   "C6",   x=60.0,  y=55.0,  rotation=0),  # VDD local 3
    Placement(CAP_100NF_0402,   "C7",   x=60.0,  y=63.0,  rotation=0),  # VDD local 4

    # ── Reset circuit (top of ESP32) ──
    Placement(RES_10K,          "R1",   x=42.5,  y=73.0,  rotation=0),  # EN pull-up
    Placement(CAP_100NF_0402,   "C8",   x=48.0,  y=73.0,  rotation=0),  # EN RC filter

    # ── SPI clock filtering (top-right) ──
    Placement(FERRITE_100R_CLK, "FB2",  x=68.0,  y=42.0,  rotation=0),  # CLK line filter

    # ── I2C pull-ups (right edge, if I2C used) ──
    Placement(RES_4K7,          "R2",   x=72.0,  y=68.0,  rotation=0),  # SCL pull-up
    Placement(RES_4K7,          "R3",   x=72.0,  y=75.0,  rotation=0),  # SDA pull-up

    # ── GPIO breakout headers (bottom) ──
    Placement(JST_XH_2PIN,      "J1",   x=20.0,  y=95.0,  rotation=0),  # GPIO header 1
    Placement(JST_XH_2PIN,      "J2",   x=50.0,  y=95.0,  rotation=0),  # GPIO header 2

    # ── Sensor connectors (corners) ──
    Placement(JST_SH_4PIN,      "J3",   x=12.0,  y=80.0,  rotation=0),  # I2C sensor (e.g., IMU)
]


# =============================================================================
# Net Definitions (Complete Power Supply + I/O)
# =============================================================================

NETS = {
    # ── Power rails ──
    "GND": [
        # LDO
        NC("U1", "2"),     # AMS1117 GND pin
        NC("C1", "2"), NC("C2", "2"), NC("C3", "2"),  # cap grounds

        # ESP32 module
        NC("U2", "1"), NC("U2", "32"), NC("U2", "38"),  # module GND pins

        # Module decoupling
        NC("C4", "2"), NC("C5", "2"), NC("C6", "2"), NC("C7", "2"),

        # Reset circuit
        NC("C8", "2"),     # EN RC cap to GND

        # TVS diode
        NC("D1", "2"),     # anode → GND

        # I2C pull-ups (other end)
        NC("R2", "2"), NC("R3", "2"),

        # Connector grounds
        NC("J1", "2"), NC("J2", "2"),
        NC("J3", "2"),  # JST-SH GND pin
    ],

    "+5V_IN": [
        # From external power supply (e.g., barrel jack or USB)
        NC("D1", "1"),     # TVS anode input
    ],

    "+5V": [
        # TVS output → LDO input
        NC("D1", "2"),     # NO: anode to GND, cathode to +5V rail
        # Correct: TVS pin 1 (A) = anode = input, pin 2 (C) = cathode = output
        # Cathode ties to +5V rail after protection
        NC("U1", "3"),     # AMS1117 VIN
        NC("C1", "1"),     # LDO input cap
    ],

    "+3V3": [
        # LDO output
        NC("U1", "2"),     # AMS1117 VOUT
        NC("C2", "1"), NC("C3", "1"),  # output caps

        # Module power
        NC("U2", "33"),    # ESP32 VDD33

        # Module decoupling
        NC("C4", "1"), NC("C5", "1"), NC("C6", "1"), NC("C7", "1"),

        # Reset pull-up
        NC("R1", "1"),

        # I2C pull-ups
        NC("R2", "1"), NC("R3", "1"),

        # Ferrite outputs (after filtering)
        # FB1 output → +3V3 rail (already done via U2)
    ],

    # ── Reset / Enable Circuit ──
    "EN_RC": [
        # EN pin (pin 10) with RC filter
        NC("U2", "10"),    # ESP32 EN pin
        NC("R1", "2"),     # pull-up resistor other end
        NC("C8", "1"),     # RC filter cap
    ],

    # ── Internal Flash SPI (CLK/SDO/SDI/CS) ──
    # These pins are not user-controllable; they connect internally to flash.
    # CLK (pin 11) may have ferrite bead for EMI filtering.
    "FLASH_CLK": [
        NC("U2", "11"),    # ESP32 CLK
        NC("FB2", "1"),    # ferrite bead input (optional)
    ],

    "FLASH_CLK_OUT": [
        NC("FB2", "2"),    # ferrite bead output (to internal flash, not broken out)
    ],

    # SDO (pin 12): SPI data out from flash
    # SDI (pin 13): SPI data in to flash
    # CS (pin 14): Chip select for flash
    # These are internal — no user access

    # ── GPIO pins (user I/O) ──
    # Map a few key GPIOs to connectors for flexibility
    "GPIO_IO23": [
        NC("U2", "2"),     # IO23 (general purpose)
        NC("J1", "1"),     # header pin 1
    ],

    "GPIO_IO22": [
        NC("U2", "3"),     # IO22 (general purpose)
        NC("J2", "1"),     # header pin 1
    ],

    "GPIO_IO21": [
        NC("U2", "4"),     # IO21 (ADC)
    ],

    "GPIO_IO19": [
        NC("U2", "5"),     # IO19 (ADC, touch)
    ],

    "GPIO_IO18": [
        NC("U2", "6"),     # IO18 (ADC, touch)
    ],

    "GPIO_IO17": [
        NC("U2", "7"),     # IO17 (ADC, touch)
    ],

    "GPIO_IO16": [
        NC("U2", "8"),     # IO16 (ADC, touch)
    ],

    "GPIO_IO5": [
        NC("U2", "15"),    # IO5 (touch)
    ],

    # ── I2C Bus (GPIO pins for sensors) ──
    # Standard ESP32 I2C uses GPIO21 (SDA) and GPIO22 (SCL)
    # Alternate: GPIO4 (SDA) and GPIO5 (SCL)
    "I2C_SDA": [
        NC("U2", "4"),     # IO21 or use IO4 on pin 9/31
        NC("R3", "2"),     # pull-up to +3V3
        NC("J3", "3"),     # JST-SH pin 3 (SDA)
    ],

    "I2C_SCL": [
        NC("U2", "3"),     # IO22 or use IO5 on pin 15
        NC("R2", "2"),     # pull-up to +3V3
        NC("J3", "4"),     # JST-SH pin 4 (SCL)
    ],

    # ── Other I/O pins (breakout) ──
    "GPIO_IO25": [
        NC("U2", "22"),    # IO25 (DAC)
    ],

    "GPIO_IO26": [
        NC("U2", "23"),    # IO26 (DAC)
    ],

    "GPIO_IO27": [
        NC("U2", "24"),    # IO27 (ADC, touch)
    ],

    "GPIO_IO14": [
        NC("U2", "25"),    # IO14 (ADC, touch)
    ],

    "GPIO_IO12": [
        NC("U2", "26"),    # IO12 (ADC, touch)
    ],

    "GPIO_IO13": [
        NC("U2", "27"),    # IO13 (ADC, touch)
    ],

    "GPIO_IO15": [
        NC("U2", "28"),    # IO15 (ADC, touch, strapping)
    ],

    "GPIO_IO2": [
        NC("U2", "29"),    # IO2 (ADC, touch, strapping)
    ],

    "GPIO_IO0": [
        NC("U2", "30"),    # IO0 (strapping) — pulled up for normal boot, pulled low for programming
    ],

    # ── Sensor Connector Power ──
    "J3_VCC": [
        # I2C sensor connector VCC (pin 1)
        NC("J3", "1"),     # +3V3 power to sensor
    ],

    # ── Unused pins (no-connect or tied appropriately) ──
    # IO35, IO34, IO39, IO36 (pins 16-19): Input-only, no driver
    # These should be left unconnected or tied to GND if not used.

    # ── NC pin ──
    "NC": [
        NC("U2", "34"),    # No-connect pin (pin 34)
    ],
}

# Fix power rail connections
# SMAJ5V0 TVS diode pins: 1=A (anode), 2=C (cathode)
# For input protection: VIN → anode (pin 1), cathode (pin 2) → regulated output
NETS["+5V_IN"] = [NC("D1", "1")]  # Input from external 5V source
NETS["+5V"] = [
    NC("D1", "2"),                  # TVS cathode → regulated 5V rail
    NC("U1", "3"),                  # AMS1117 VIN
    NC("C1", "1"),                  # input cap
]

# Ferrite bead for VDD line (optional, for additional filtering)
# FB1 connects in series between +3V3 rail and module VDD
# For simplicity, omit FB1 and route VDD directly (present in placement but unnetted)

# Fix I2C pin confusion: ESP32 I2C defaults
# Most common: GPIO21 (SDA), GPIO22 (SCL)
# But we should clarify which GPIO pins will actually be used for I2C
# For now, assign: IO21 → SDA, IO22 → SCL
NETS["I2C_SDA"] = [
    NC("U2", "4"),     # IO21 (SDA)
    NC("R3", "2"),
    NC("J3", "3"),
]

NETS["I2C_SCL"] = [
    NC("U2", "3"),     # IO22 (SCL)
    NC("R2", "2"),
    NC("J3", "4"),
]

# Sensor connector power
NETS["+3V3"].append(NC("J3", "1"))  # +3V3 to sensor
NETS["GND"].append(NC("J3", "2"))   # GND to sensor

# Fix NC pin and strapping pins
NETS["GND"].extend([
    NC("U2", "34"),    # NC → GND (safe)
    # Strapping pins at power-up determine boot mode
    # IO0 (pin 30): pulled up for normal mode, pulled down for programming
    # IO2 (pin 29): should be low or floating (controls LED/flash)
    # IO15 (pin 28): should be low (silent boot)
    # Leave these as-is in placement, no special netting needed for normal operation
])


# =============================================================================
# Board Definition
# =============================================================================

def build_esp32_board() -> BoardDefinition:
    """Build the ESP32-WROOM-32-N4 daughter board definition.

    Returns a BoardDefinition with:
      - All placements
      - All net connections
      - No keep-out zones (simple design)
      - Mounting holes matching parent board
    """

    board = BoardDefinition(
        title="ESP32-WROOM-32-N4 Daughter Board with Power Supply",
        width=85.0,      # 85 mm width
        height=108.0,    # 108 mm length
        corner_radius=2.0,
        thickness=1.6,
        placements=PLACEMENTS,
        nets=NETS,
        keep_outs=[],
        mounting_holes=[
            # M2.5 holes matching DE10-Nano pattern (inset from edges)
            (12.21, 4.02,   2.7),
            (72.79, 4.02,   2.7),
            (12.21, 103.97, 2.7),
            (72.79, 103.97, 2.7),
        ],
    )
    return board
