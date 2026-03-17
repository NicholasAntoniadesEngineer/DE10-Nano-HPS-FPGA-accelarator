"""Component definitions for the daughter board PCB.

Every ComponentDef carries real pin assignments from manufacturer datasheets
and LCSC part numbers for JLCPCB assembly.  Pin definitions are used for
netlist validation (ERC) and schematic generation.

Organised by subsystem, matching daughter_board_pcb_design.md sections 1-10.

IMPORTANT: Pin numbers and names MUST match the manufacturer datasheet
exactly.  When in doubt, cite the datasheet table number in a comment.
"""

from cadquery_framework.kicad.component_library import ComponentDef, Pin, PadGeometry
from cadquery_framework.kicad.footprint_generators import (
    pads_chip_0402,
    pads_chip_0603,
    pads_chip_1210,
    pads_chip_2512,
    pads_led_0603,
    pads_sot23_3,
    pads_sot23_5,
    pads_sot23_8,
    pads_sot353,
    pads_soic8,
    pads_hsop8_powerpad,
    pads_tssop24,
    pads_qfn24_3x3,
    pads_vqfn16,
    pads_lga10_2x2,
    pads_sod882,
    pads_sma,
    pads_smb,
    pads_jst_xh,
    pads_jst_sh,
    pads_fpc_zif_24,
    pads_header_2x20,
    pads_xt60pw,
    pads_barrel_jack,
    pads_xt30pw,
    pads_wilc3000_module,
    pads_inductor_1265,
)


# =============================================================================
# Section 1: Motor Driver — DShot buffers, TVS diodes, ESC connectors
# =============================================================================

# 74LVC1G17GW,125 — Single Schmitt-trigger buffer (SOT-353)
# Datasheet: NXP 74LVC1G17 Rev 8, Table 4
SCHMITT_74LVC1G17 = ComponentDef(
    ref_prefix="U", value="74LVC1G17", package="SOT-353",
    description="Single Schmitt-trigger buffer",
    mpn="74LVC1G17GW,125", lcsc="C7621",
    datasheet="https://www.nxp.com/docs/en/data-sheet/74LVC1G17.pdf",
    pins=(
        Pin("1", "A", "input"),
        Pin("2", "GND", "power_in"),
        Pin("3", "Y", "output"),
        Pin("4", "NC", "no_connect"),
        Pin("5", "VCC", "power_in"),
    ),
    pads=pads_sot353(),
    courtyard_w=2.80, courtyard_h=2.00,
)

# PESD5V0S1BL,315 — ESD/TVS protection diode (SOD-882)
# Datasheet: NXP PESD5V0S1BL Rev 5, Table 4
TVS_PESD5V0S1BL = ComponentDef(
    ref_prefix="D", value="PESD5V0S1BL", package="SOD-882",
    description="5V TVS ESD protection diode",
    mpn="PESD5V0S1BL,315", lcsc="C85387",
    datasheet="https://www.nxp.com/docs/en/data-sheet/PESD5V0S1BL.pdf",
    pins=(
        Pin("1", "A", "passive"),   # anode
        Pin("2", "K", "passive"),   # cathode
    ),
    pads=pads_sod882(),
    courtyard_w=1.60, courtyard_h=1.00,
)

# B3B-XH-A(LF)(SN) — JST-XH 3-pin through-hole header
# Datasheet: JST eXH.pdf
JST_XH_3PIN = ComponentDef(
    ref_prefix="J", value="JST-XH-3", package="JST-XH",
    description="JST-XH 3-pin 2.54mm TH header (ESC connector)",
    mpn="B3B-XH-A(LF)(SN)", lcsc="C144394",
    datasheet="https://www.jst.com/wp-content/uploads/2021/01/eXH.pdf",
    pins=(
        Pin("1", "SIG", "passive"),
        Pin("2", "VCC", "passive"),
        Pin("3", "GND", "passive"),
    ),
    pads=pads_jst_xh(3),
    courtyard_w=10.5, courtyard_h=5.00,
)


# =============================================================================
# Section 2: IMU — ICM-20948, SN74AVC4T245, TPS7A2018, BSS138
# =============================================================================

# ICM-20948 — 9-axis IMU (QFN-24 3×3mm)
# Datasheet: InvenSense DS-000189 Rev 1.3, Table 2 — Pin Descriptions
ICM_20948 = ComponentDef(
    ref_prefix="U", value="ICM-20948", package="QFN-24",
    description="9-axis IMU (gyro + accel + magnetometer)",
    mpn="ICM-20948", lcsc="C91752",
    datasheet="https://invensense.tdk.com/wp-content/uploads/2016/06/DS-000189-ICM-20948-v1.3.pdf",
    pins=(
        # Pin numbering from DS-000189 Table 2
        Pin("1",  "AUX_CL",  "bidirectional"),  # auxiliary I2C master clock
        Pin("2",  "SDO/AD0", "bidirectional"),   # SPI data out / I2C addr bit
        Pin("3",  "AUX_DA",  "bidirectional"),   # auxiliary I2C master data
        Pin("4",  "nCS",     "input"),           # SPI chip select (active low)
        Pin("5",  "AD1",     "input"),           # I2C address bit 1
        Pin("6",  "SCL/SCLK","input"),           # I2C/SPI clock
        Pin("7",  "SDA/SDI", "bidirectional"),   # I2C data / SPI data in
        Pin("8",  "INT1",    "output"),          # interrupt 1
        Pin("9",  "INT2",    "no_connect"),       # interrupt 2 (unused, leave NC)
        Pin("10", "REGOUT",  "power_out"),       # internal regulator out (requires 1uF cap)
        Pin("11", "FSYNC",   "input"),           # frame sync input
        Pin("12", "VDD",     "power_in"),        # digital power supply (1.71-1.95V)
        Pin("13", "GND_1",   "power_in"),        # ground
        Pin("14", "GND_2",   "power_in"),        # ground
        Pin("15", "GND_3",   "power_in"),        # ground
        Pin("16", "GND_4",   "power_in"),        # ground
        Pin("17", "GND_5",   "power_in"),        # ground
        Pin("18", "GND_6",   "power_in"),        # ground
        Pin("19", "RESV_19", "no_connect"),      # reserved
        Pin("20", "RESV_20", "no_connect"),      # reserved
        Pin("21", "RESV_21", "no_connect"),      # reserved
        Pin("22", "RESV_22", "no_connect"),      # reserved
        Pin("23", "RESV_23", "no_connect"),      # reserved
        Pin("24", "VDDIO",   "power_in"),        # I/O power supply (1.71-1.95V)
        Pin("25", "GND_PAD", "power_in"),        # exposed pad → GND
    ),
    pads=pads_qfn24_3x3(epad_w=1.70, epad_h=1.54),
    courtyard_w=4.00, courtyard_h=4.00,
)

# SN74AVC4T245RGYR — 4-bit dual-supply level translator (VQFN-16)
# Datasheet: TI SCES548T, Table 1 — Pin Functions
SN74AVC4T245 = ComponentDef(
    ref_prefix="U", value="SN74AVC4T245", package="VQFN-16",
    description="4-bit dual-supply bus transceiver / level translator",
    mpn="SN74AVC4T245RGYR", lcsc="C130106",
    datasheet="https://www.ti.com/lit/ds/symlink/sn74avc4t245.pdf",
    pins=(
        Pin("1",  "VCCA",   "power_in"),    # port A supply (1.8V)
        Pin("2",  "A1",     "bidirectional"),
        Pin("3",  "A2",     "bidirectional"),
        Pin("4",  "A3",     "bidirectional"),
        Pin("5",  "A4",     "bidirectional"),
        Pin("6",  "1OE_N",  "input"),       # output enable port A (active low)
        Pin("7",  "GND_1",  "power_in"),
        Pin("8",  "2OE_N",  "input"),       # output enable port B (active low)
        Pin("9",  "DIR",    "input"),       # direction control
        Pin("10", "B4",     "bidirectional"),
        Pin("11", "B3",     "bidirectional"),
        Pin("12", "B2",     "bidirectional"),
        Pin("13", "B1",     "bidirectional"),
        Pin("14", "VCCB",   "power_in"),    # port B supply (3.3V)
        Pin("15", "GND_2",  "power_in"),
        Pin("16", "NC",     "no_connect"),
        Pin("17", "GND_PAD","power_in"),    # exposed pad → GND
    ),
    pads=pads_vqfn16(epad=1.70),
    courtyard_w=4.50, courtyard_h=4.50,
)

# TPS7A2018DBVR — 1.8V LDO 300mA (SOT-23-5)
# Datasheet: TI SBVS252, Table 1
TPS7A2018 = ComponentDef(
    ref_prefix="U", value="TPS7A2018", package="SOT-23-5",
    description="1.8V 300mA ultra-low-noise LDO",
    mpn="TPS7A2018DBVR", lcsc="C181089",
    datasheet="https://www.ti.com/lit/ds/symlink/tps7a20.pdf",
    pins=(
        Pin("1", "OUT",  "power_out"),
        Pin("2", "GND",  "power_in"),
        Pin("3", "EN",   "input"),
        Pin("4", "NC",   "no_connect"),
        Pin("5", "IN",   "power_in"),
    ),
    pads=pads_sot23_5(),
    courtyard_w=3.40, courtyard_h=3.20,
)

# BSS138 — N-channel MOSFET for INT level shifting (SOT-23)
# Datasheet: ON Semi BSS138, Table — Pin Assignment
BSS138 = ComponentDef(
    ref_prefix="Q", value="BSS138", package="SOT-23",
    description="N-ch MOSFET 50V 220mA (INT level shift)",
    mpn="BSS138", lcsc="C112213",
    datasheet="https://www.onsemi.com/pdf/datasheet/bss138-d.pdf",
    pins=(
        Pin("1", "G", "input"),     # gate
        Pin("2", "S", "passive"),   # source
        Pin("3", "D", "passive"),   # drain
    ),
    pads=pads_sot23_3(),
    courtyard_w=3.40, courtyard_h=3.00,
)


# =============================================================================
# Section 3: Camera — FPC connector, 2.8V LDO, 1.5V LDO
# =============================================================================

# Molex 5051102491 — 24-pin 0.5mm FPC ZIF
FPC_24PIN = ComponentDef(
    ref_prefix="J", value="FPC-24", package="FPC-ZIF",
    description="24-pin 0.5mm FPC ZIF connector (OV5640 camera)",
    mpn="5051102491", lcsc="C2857003",
    datasheet="https://www.molex.com/en-us/products/part-detail/5051102491",
    pins=tuple(
        [Pin(str(i + 1), f"FPC_{i + 1}", "passive") for i in range(24)]
        + [Pin("MP1", "SHIELD1", "passive"), Pin("MP2", "SHIELD2", "passive")]
    ),
    pads=pads_fpc_zif_24(),
    courtyard_w=15.50, courtyard_h=4.00,
)

# TPS7A2028DBVR — 2.8V LDO (camera AVDD)
TPS7A2028 = ComponentDef(
    ref_prefix="U", value="TPS7A2028", package="SOT-23-5",
    description="2.8V 300mA ultra-low-noise LDO (camera AVDD)",
    mpn="TPS7A2028DBVR", lcsc="C181090",
    datasheet="https://www.ti.com/lit/ds/symlink/tps7a20.pdf",
    pins=(
        Pin("1", "OUT",  "power_out"),
        Pin("2", "GND",  "power_in"),
        Pin("3", "EN",   "input"),
        Pin("4", "NC",   "no_connect"),
        Pin("5", "IN",   "power_in"),
    ),
    pads=pads_sot23_5(),
    courtyard_w=3.40, courtyard_h=3.20,
)

# TPS7A2015DBVR — 1.5V LDO (camera DVDD)
TPS7A2015 = ComponentDef(
    ref_prefix="U", value="TPS7A2015", package="SOT-23-5",
    description="1.5V 300mA ultra-low-noise LDO (camera DVDD)",
    mpn="TPS7A2015DBVR", lcsc="C181088",
    datasheet="https://www.ti.com/lit/ds/symlink/tps7a20.pdf",
    pins=(
        Pin("1", "OUT",  "power_out"),
        Pin("2", "GND",  "power_in"),
        Pin("3", "EN",   "input"),
        Pin("4", "NC",   "no_connect"),
        Pin("5", "IN",   "power_in"),
    ),
    pads=pads_sot23_5(),
    courtyard_w=3.40, courtyard_h=3.20,
)


# =============================================================================
# Section 4: ToF Hub — TCA9548A, JST-SH 4-pin connectors
# =============================================================================

# TCA9548APWR — 8-channel I2C multiplexer (TSSOP-24)
# Datasheet: TI SCPS206H, Table 1 — Pin Functions
TCA9548A = ComponentDef(
    ref_prefix="U", value="TCA9548A", package="TSSOP-24",
    description="8-channel I2C multiplexer",
    mpn="TCA9548APWR", lcsc="C131613",
    datasheet="https://www.ti.com/lit/ds/symlink/tca9548a.pdf",
    pins=(
        Pin("1",  "A0",    "input"),
        Pin("2",  "A1",    "input"),
        Pin("3",  "RESET_N","input"),
        Pin("4",  "SD0",   "bidirectional"),
        Pin("5",  "SC0",   "bidirectional"),
        Pin("6",  "SD1",   "bidirectional"),
        Pin("7",  "SC1",   "bidirectional"),
        Pin("8",  "SD2",   "bidirectional"),
        Pin("9",  "SC2",   "bidirectional"),
        Pin("10", "SD3",   "bidirectional"),
        Pin("11", "SC3",   "bidirectional"),
        Pin("12", "GND",   "power_in"),
        Pin("13", "SD4",   "bidirectional"),
        Pin("14", "SC4",   "bidirectional"),
        Pin("15", "SD5",   "bidirectional"),
        Pin("16", "SC5",   "bidirectional"),
        Pin("17", "SD6",   "bidirectional"),
        Pin("18", "SC6",   "bidirectional"),
        Pin("19", "SD7",   "bidirectional"),
        Pin("20", "SC7",   "bidirectional"),
        Pin("21", "A2",    "input"),
        Pin("22", "SCL",   "input"),
        Pin("23", "SDA",   "bidirectional"),
        Pin("24", "VCC",   "power_in"),
    ),
    pads=pads_tssop24(),
    courtyard_w=8.00, courtyard_h=9.50,
)

# SM04B-SRSS-TB(LF)(SN) — JST-SH 4-pin SMD (ToF sensor)
JST_SH_4PIN = ComponentDef(
    ref_prefix="J", value="JST-SH-4", package="JST-SH",
    description="JST-SH 4-pin 1.0mm SMD (ToF sensor)",
    mpn="SM04B-SRSS-TB(LF)(SN)", lcsc="C160404",
    datasheet="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf",
    pins=(
        Pin("1", "VCC", "passive"),
        Pin("2", "GND", "passive"),
        Pin("3", "SDA", "passive"),
        Pin("4", "SCL", "passive"),
        Pin("MP1", "SHIELD1", "passive"),
        Pin("MP2", "SHIELD2", "passive"),
    ),
    pads=pads_jst_sh(4),
    courtyard_w=7.80, courtyard_h=4.50,
)


# =============================================================================
# Section 5: Barometer — BMP390
# =============================================================================

# BMP390 — Barometric pressure sensor (LGA-10 2×2mm)
# Datasheet: Bosch BST-BMP390-DS002 Rev 1.1, Table 5 — Pin Description
BMP390 = ComponentDef(
    ref_prefix="U", value="BMP390", package="LGA-10",
    description="Barometric pressure sensor ±50Pa accuracy",
    mpn="BMP390", lcsc="C2688071",
    datasheet="https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp390-ds002.pdf",
    pins=(
        # Bottom row (pins 1-5)
        Pin("1",  "VDDIO", "power_in"),
        Pin("2",  "GND_1", "power_in"),
        Pin("3",  "SDI",   "bidirectional"),  # SPI MOSI / I2C SDA
        Pin("4",  "SCK",   "input"),          # SPI CLK / I2C SCL
        Pin("5",  "SDO",   "bidirectional"),  # SPI MISO / I2C addr select
        # Top row (pins 6-10)
        Pin("6",  "CSB",   "input"),          # chip select (high=I2C, low=SPI)
        Pin("7",  "INT",   "no_connect"),      # interrupt output (unused, leave NC)
        Pin("8",  "GND_2", "power_in"),
        Pin("9",  "VDD",   "power_in"),
        Pin("10", "GND_3", "power_in"),
    ),
    pads=pads_lga10_2x2(),
    courtyard_w=3.00, courtyard_h=3.00,
)


# =============================================================================
# Section 6: IR Beacon Receivers — TSOP38238 connectors
# =============================================================================

# SM03B-SRSS-TB(LF)(SN) — JST-SH 3-pin SMD (IR receiver)
JST_SH_3PIN = ComponentDef(
    ref_prefix="J", value="JST-SH-3", package="JST-SH",
    description="JST-SH 3-pin 1.0mm SMD (IR receiver)",
    mpn="SM03B-SRSS-TB(LF)(SN)", lcsc="C160403",
    datasheet="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf",
    pins=(
        Pin("1", "VCC", "passive"),
        Pin("2", "GND", "passive"),
        Pin("3", "OUT", "passive"),
        Pin("MP1", "SHIELD1", "passive"),
        Pin("MP2", "SHIELD2", "passive"),
    ),
    pads=pads_jst_sh(3),
    courtyard_w=6.80, courtyard_h=4.50,
)


# =============================================================================
# Section 7: WiFi/BLE — WILC3000, LTC bridge connector
# =============================================================================

# ATWILC3000-MR110UB — WiFi/BLE SPI module (castellated)
def _wilc3000_pin(i: int) -> Pin:
    """Return Pin for WILC3000 module position i (0-based).

    Pins 11-16 and 24-34 (1-based) are reserved/unused module pads —
    mark them no_connect so the ERC does not warn about unconnected
    unspecified pins.
    """
    pin_num = i + 1
    _NO_CONNECT_PINS = frozenset(range(11, 17)) | frozenset(range(24, 35))
    pin_type = "no_connect" if pin_num in _NO_CONNECT_PINS else "unspecified"
    return Pin(str(pin_num), f"MOD_{pin_num}", pin_type)


WILC3000 = ComponentDef(
    ref_prefix="U", value="ATWILC3000", package="Module",
    description="WiFi 802.11 b/g/n + BLE 4.2 SPI module",
    mpn="ATWILC3000-MR110UB", lcsc="",  # customer-supplied (not standard JLCPCB stock)
    datasheet="https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/70005327B.pdf",
    pins=tuple(_wilc3000_pin(i) for i in range(34)),
    pads=pads_wilc3000_module(),
    courtyard_w=21.00, courtyard_h=15.50,
)

# SM06B-SRSS-TB(LF)(SN) — JST-SH 6-pin SMD (LTC bridge cable)
JST_SH_6PIN = ComponentDef(
    ref_prefix="J", value="JST-SH-6", package="JST-SH",
    description="JST-SH 6-pin 1.0mm SMD (LTC bridge cable)",
    mpn="SM06B-SRSS-TB(LF)(SN)", lcsc="C160406",
    datasheet="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf",
    pins=(
        Pin("1", "SPI_CLK",  "passive"),
        Pin("2", "SPI_MOSI", "passive"),
        Pin("3", "SPI_MISO", "passive"),
        Pin("4", "SPI_SSN",  "passive"),
        Pin("5", "IRQ",      "passive"),
        Pin("6", "GND",      "passive"),
        Pin("MP1", "SHIELD1", "passive"),
        Pin("MP2", "SHIELD2", "passive"),
    ),
    pads=pads_jst_sh(6),
    courtyard_w=10.80, courtyard_h=4.50,
)


# =============================================================================
# Section 8: Power Management
# =============================================================================

# XT60PW-M — Battery connector (through-hole)
XT60PW = ComponentDef(
    ref_prefix="J", value="XT60PW-M", package="XT60",
    description="XT60 PCB-mount battery connector 30A",
    mpn="XT60PW-M", lcsc="",  # customer-supplied
    datasheet="https://www.amass.com.cn/en/product/detail/XT60PW.html",
    pins=(
        Pin("1", "VBATT_POS", "passive"),
        Pin("2", "VBATT_NEG", "passive"),
    ),
    pads=pads_xt60pw(),
    courtyard_w=12.00, courtyard_h=8.00,
)

# SI4435DDY — P-channel MOSFET (SO-8) for reverse polarity protection
# Datasheet: Vishay SI4435DDY, Pin Configuration
SI4435DDY = ComponentDef(
    ref_prefix="Q", value="SI4435DDY", package="SO-8",
    description="P-ch MOSFET -30V -8.8A (reverse polarity protection)",
    mpn="SI4435DDY-T1-GE3", lcsc="C18759",
    datasheet="https://www.vishay.com/docs/68771/si4435ddy.pdf",
    pins=(
        Pin("1", "S", "passive"),    # source
        Pin("2", "S", "passive"),    # source (paralleled)
        Pin("3", "S", "passive"),    # source (paralleled)
        Pin("4", "G", "input"),      # gate
        Pin("5", "D", "passive"),    # drain
        Pin("6", "D", "passive"),    # drain (paralleled)
        Pin("7", "D", "passive"),    # drain (paralleled)
        Pin("8", "D", "passive"),    # drain (paralleled)
    ),
    pads=pads_soic8(),
    courtyard_w=6.50, courtyard_h=5.50,
)

# SMBJ20A — TVS diode 20V (SMB package)
TVS_SMBJ20A = ComponentDef(
    ref_prefix="D", value="SMBJ20A", package="SMB",
    description="TVS diode 20V 600W (battery protection)",
    mpn="SMBJ20A", lcsc="C123804",
    datasheet="https://www.littelfuse.com/media?resourcetype=datasheets&itemid=d1c73af4-2796-4319-9420-63a3d7ef0985",
    pins=(
        Pin("1", "A", "passive"),  # anode
        Pin("2", "K", "passive"),  # cathode
    ),
    pads=pads_smb(),
    courtyard_w=6.50, courtyard_h=4.50,
)

# BZX84C15 — 15V Zener diode (SOT-23)
BZX84C15 = ComponentDef(
    ref_prefix="D", value="BZX84C15", package="SOT-23",
    description="15V Zener diode (MOSFET gate protection)",
    mpn="BZX84C15", lcsc="C8056",
    datasheet="https://www.nxp.com/docs/en/data-sheet/BZX84_SER.pdf",
    pins=(
        Pin("1", "A", "passive"),
        Pin("2", "K", "passive"),
        Pin("3", "NC", "no_connect"),
    ),
    pads=pads_sot23_3(),
    courtyard_w=3.40, courtyard_h=3.00,
)

# TPS54560DDAR — 5V/5A buck converter (HSOP-8 with PowerPAD)
# Datasheet: TI SLVSCS3, Table 1 — Pin Functions
TPS54560 = ComponentDef(
    ref_prefix="U", value="TPS54560", package="HSOP-8",
    description="60V input 5A step-down converter",
    mpn="TPS54560DDAR", lcsc="C15062",
    datasheet="https://www.ti.com/lit/ds/symlink/tps54560.pdf",
    pins=(
        Pin("1", "BOOT",  "passive"),
        Pin("2", "VIN",   "power_in"),
        Pin("3", "EN",    "input"),
        Pin("4", "SS",    "passive"),        # soft-start
        Pin("5", "VSENSE","input"),          # feedback
        Pin("6", "COMP",  "passive"),        # compensation
        Pin("7", "GND",   "power_in"),
        Pin("8", "PH",    "output"),         # switch node
        Pin("9", "PAD",   "power_in"),       # exposed pad → GND
    ),
    pads=pads_hsop8_powerpad(),
    courtyard_w=8.00, courtyard_h=7.00,
)

# SRP1265A-100M — 10uH power inductor (12.5×12.5mm)
INDUCTOR_10UH = ComponentDef(
    ref_prefix="L", value="10uH", package="1265",
    description="10uH 6A shielded power inductor",
    mpn="SRP1265A-100M", lcsc="C261937",
    datasheet="https://www.bourns.com/docs/product-datasheets/SRP1265A.pdf",
    pins=(
        Pin("1", "1", "passive"),
        Pin("2", "2", "passive"),
    ),
    pads=pads_inductor_1265(),
    courtyard_w=14.50, courtyard_h=14.50,
)

# AP2112K-3.3TRG1 — 3.3V/600mA LDO (SOT-23-5)
# Datasheet: Diodes Inc. AP2112K
AP2112K = ComponentDef(
    ref_prefix="U", value="AP2112K-3.3", package="SOT-23-5",
    description="3.3V 600mA LDO regulator",
    mpn="AP2112K-3.3TRG1", lcsc="C51118",
    datasheet="https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    pins=(
        Pin("1", "VIN",   "power_in"),
        Pin("2", "GND",   "power_in"),
        Pin("3", "EN",    "input"),
        Pin("4", "NC",    "no_connect"),
        Pin("5", "VOUT",  "power_out"),
    ),
    pads=pads_sot23_5(),
    courtyard_w=3.40, courtyard_h=3.20,
)

# INA219BIDR — Current/power monitor (SOT-23-8)
# Datasheet: TI SBOS448G, Table 1 — Pin Functions
INA219 = ComponentDef(
    ref_prefix="U", value="INA219", package="SOT-23-8",
    description="26V bidirectional I2C current/power monitor",
    mpn="INA219BIDR", lcsc="C82106",
    datasheet="https://www.ti.com/lit/ds/symlink/ina219.pdf",
    pins=(
        Pin("1", "IN+",   "input"),       # shunt positive input
        Pin("2", "IN-",   "input"),       # shunt negative input
        Pin("3", "GND",   "power_in"),
        Pin("4", "A1",    "input"),       # address bit 1
        Pin("5", "A0",    "input"),       # address bit 0
        Pin("6", "SCL",   "input"),       # I2C clock
        Pin("7", "SDA",   "bidirectional"),# I2C data
        Pin("8", "VS",    "power_in"),    # supply voltage
    ),
    pads=pads_sot23_8(),
    courtyard_w=3.40, courtyard_h=3.20,
)

# CSS2H-2512R-L010F — 10mΩ 2W current sense shunt (2512)
SHUNT_10MOHM = ComponentDef(
    ref_prefix="R", value="10mR", package="2512",
    description="10mOhm 2W 1% current sense resistor",
    mpn="CSS2H-2512R-L010F", lcsc="C211204",
    datasheet="https://www.bourns.com/docs/product-datasheets/CSS2H-2512.pdf",
    pins=(
        Pin("1", "1", "passive"),
        Pin("2", "2", "passive"),
    ),
    pads=pads_chip_2512(),
    courtyard_w=7.80, courtyard_h=4.20,
)

# PJ-102AH — 5.5×2.1mm barrel jack
BARREL_JACK = ComponentDef(
    ref_prefix="J", value="PJ-102AH", package="Barrel-Jack",
    description="5.5x2.1mm DC barrel jack",
    mpn="PJ-102AH", lcsc="",  # customer-supplied
    datasheet="https://www.sameskydevices.com/product/resource/pj-102a.pdf",
    pins=(
        Pin("1", "TIP",    "passive"),
        Pin("2", "SLEEVE", "passive"),
        Pin("3", "SWITCH", "passive"),
    ),
    pads=pads_barrel_jack(),
    courtyard_w=10.00, courtyard_h=12.00,
)

# XT30PW-F — Arm switch connector
XT30PW = ComponentDef(
    ref_prefix="J", value="XT30PW-F", package="XT30",
    description="XT30 PCB-mount arm switch connector",
    mpn="XT30PW-F", lcsc="",  # customer-supplied
    datasheet="https://www.amass.com.cn/en/product/detail/XT30PW.html",
    pins=(
        Pin("1", "SW1", "passive"),
        Pin("2", "SW2", "passive"),
    ),
    pads=pads_xt30pw(),
    courtyard_w=8.00, courtyard_h=6.00,
)


# =============================================================================
# Section 9 & 10: Pump, Buzzer, LEDs, Switches — MOSFETs, connectors, passives
# =============================================================================

# AO3400A — N-channel MOSFET (SOT-23) for pump/buzzer driver
AO3400A = ComponentDef(
    ref_prefix="Q", value="AO3400A", package="SOT-23",
    description="N-ch MOSFET 30V 5.8A (pump/buzzer driver)",
    mpn="AO3400A", lcsc="C20917",
    datasheet="https://www.aosmd.com/res/data_sheets/AO3400A.pdf",
    pins=(
        Pin("1", "G", "input"),
        Pin("2", "S", "passive"),
        Pin("3", "D", "passive"),
    ),
    pads=pads_sot23_3(),
    courtyard_w=3.40, courtyard_h=3.00,
)

# SS14 — 1A 40V Schottky diode (SMA)
SS14 = ComponentDef(
    ref_prefix="D", value="SS14", package="SMA",
    description="1A 40V Schottky diode (pump flyback)",
    mpn="SS14", lcsc="C2480",
    datasheet="https://www.vishay.com/docs/88746/ss12.pdf",
    pins=(
        Pin("1", "A", "passive"),
        Pin("2", "K", "passive"),
    ),
    pads=pads_sma(),
    courtyard_w=5.00, courtyard_h=3.50,
)

# B2B-XH-A(LF)(SN) — JST-XH 2-pin (pump, buzzer, ESTOP, ARM)
JST_XH_2PIN = ComponentDef(
    ref_prefix="J", value="JST-XH-2", package="JST-XH",
    description="JST-XH 2-pin 2.54mm TH header",
    mpn="B2B-XH-A(LF)(SN)", lcsc="C144393",
    datasheet="https://www.jst.com/wp-content/uploads/2021/01/eXH.pdf",
    pins=(
        Pin("1", "P1", "passive"),
        Pin("2", "P2", "passive"),
    ),
    pads=pads_jst_xh(2),
    courtyard_w=8.00, courtyard_h=5.00,
)


# =============================================================================
# Generic passives — shared across all subsystems
# =============================================================================

def _resistor(value: str, lcsc: str) -> ComponentDef:
    """Create a 0402 resistor definition."""
    return ComponentDef(
        ref_prefix="R", value=value, package="0402",
        description=f"{value} 0402 1% thin-film resistor",
        mpn=f"RC0402FR-07{value}L", lcsc=lcsc,
        datasheet="",
        pins=(Pin("1", "1", "passive"), Pin("2", "2", "passive")),
        pads=pads_chip_0402(),
        courtyard_w=1.60, courtyard_h=1.00,
    )


def _capacitor(value: str, package: str, lcsc: str) -> ComponentDef:
    """Create a capacitor definition."""
    pads_fn = {"0402": pads_chip_0402, "0603": pads_chip_0603, "1210": pads_chip_1210}
    cw = {"0402": 1.60, "0603": 2.40, "1210": 4.60}
    ch = {"0402": 1.00, "0603": 1.50, "1210": 3.20}
    return ComponentDef(
        ref_prefix="C", value=value, package=package,
        description=f"{value} {package} MLCC X7R/X5R",
        mpn=f"GRM-{package}-{value}", lcsc=lcsc,
        datasheet="",
        pins=(Pin("1", "1", "passive"), Pin("2", "2", "passive")),
        pads=pads_fn[package](),
        courtyard_w=cw[package], courtyard_h=ch[package],
    )


# Standard resistors
RES_100R = _resistor("100R", "C25076")
RES_330R = _resistor("330R", "C25104")
RES_1K   = _resistor("1k",   "C11702")
RES_4K7  = _resistor("4.7k", "C25900")
RES_10K  = _resistor("10k",  "C25744")
RES_24K9 = _resistor("24.9k","C25942")
RES_27K  = _resistor("27k",  "C25960")
RES_30K1 = _resistor("30.1k","C25978")
RES_100K = _resistor("100k", "C25741")
RES_150K = _resistor("150k", "C25764")
RES_160K = _resistor("160k", "C25766")
RES_1M   = _resistor("1M",   "C25585")

# Standard capacitors
CAP_68PF_0402  = _capacitor("68pF",  "0402", "C1560")
CAP_100PF_0402 = _capacitor("100pF", "0402", "C1525")
CAP_6N8_0402   = _capacitor("6.8nF", "0402", "C1580")
CAP_47NF_0402  = _capacitor("47nF",  "0402", "C1590")
CAP_100NF_0402 = _capacitor("100nF", "0402", "C1525")
CAP_1UF_0402   = _capacitor("1uF",   "0402", "C52923")
CAP_2U2_0402   = _capacitor("2.2uF", "0402", "C12960")
CAP_4U7_0402   = _capacitor("4.7uF", "0402", "C23733")
CAP_10UF_0603  = _capacitor("10uF",  "0603", "C19702")
CAP_10UF_1210  = _capacitor("10uF/25V","1210","C32133")  # buck input (25V rated)
CAP_47UF_1210  = _capacitor("47uF/10V","1210","C76882")  # buck output

# LED 0603
LED_GREEN = ComponentDef(
    ref_prefix="LED", value="Green", package="0603",
    description="Green 0603 LED (power indicator)",
    mpn="150060VS75000", lcsc="C72043",
    datasheet="https://www.we-online.com/components/products/datasheet/150060VS75000.pdf",
    pins=(Pin("1", "A", "passive"), Pin("2", "K", "passive")),
    pads=pads_led_0603(),
    courtyard_w=2.40, courtyard_h=1.50,
)

LED_RED = ComponentDef(
    ref_prefix="LED", value="Red", package="0603",
    description="Red 0603 LED (armed indicator)",
    mpn="150060RS75000", lcsc="C72044",
    datasheet="https://www.we-online.com/components/products/datasheet/150060RS75000.pdf",
    pins=(Pin("1", "A", "passive"), Pin("2", "K", "passive")),
    pads=pads_led_0603(),
    courtyard_w=2.40, courtyard_h=1.50,
)

LED_BLUE = ComponentDef(
    ref_prefix="LED", value="Blue", package="0603",
    description="Blue 0603 LED (beacon lock indicator)",
    mpn="150060BS75000", lcsc="C72041",
    datasheet="https://www.we-online.com/components/products/datasheet/150060BS75000.pdf",
    pins=(Pin("1", "A", "passive"), Pin("2", "K", "passive")),
    pads=pads_led_0603(),
    courtyard_w=2.40, courtyard_h=1.50,
)

LED_YELLOW = ComponentDef(
    ref_prefix="LED", value="Yellow", package="0603",
    description="Yellow 0603 LED (error indicator)",
    mpn="150060YS75000", lcsc="C72038",
    datasheet="https://www.we-online.com/components/products/datasheet/150060YS75000.pdf",
    pins=(Pin("1", "A", "passive"), Pin("2", "K", "passive")),
    pads=pads_led_0603(),
    courtyard_w=2.40, courtyard_h=1.50,
)

# GPIO headers (2×20 female)
GPIO_HEADER_2X20 = ComponentDef(
    ref_prefix="J", value="2x20-F", package="2x20-2.54mm",
    description="2x20 female header 2.54mm (GPIO socket)",
    mpn="SSQ-120-03-G-D", lcsc="",  # customer-supplied (Samtec)
    datasheet="https://www.samtec.com/products/ssq-120-03-g-d",
    pins=tuple(Pin(str(i + 1), f"P{i + 1}", "passive") for i in range(40)),
    pads=pads_header_2x20(),
    courtyard_w=6.00, courtyard_h=52.00,
)
