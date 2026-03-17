"""Package-specific footprint pad generators.

Every function returns a tuple of PadGeometry instances with dimensions
sourced from manufacturer datasheets or the IPC-7351B standard (Nominal
density, Level B).  Each function documents its dimensional source.

Manufacturing constraints (annular ring, solder mask expansion, etc.) are
imported from jlcpcb_constraints.py so all boards stay in sync.

IMPORTANT: Never invent pad dimensions.  If a datasheet is unavailable,
leave a TODO and skip the component until the datasheet is sourced.
"""

from __future__ import annotations

from cadquery_framework.kicad.component_library import PadGeometry, SMD_FRONT_LAYERS, TH_LAYERS, NPTH_LAYERS
from cadquery_framework.kicad.jlcpcb_constraints import (
    JLCPCB_MIN_ANNULAR_MM,
    SOLDER_MASK_EXPANSION_MM,
)


# =============================================================================
# Helper: symmetric 2-pad chip (resistor / capacitor / LED)
# =============================================================================

def _chip_pads(pad_w: float, pad_h: float, pitch: float) -> tuple[PadGeometry, ...]:
    """Two SMD pads centred at ±pitch/2 along X axis."""
    half = pitch / 2
    return (
        PadGeometry("1", x=-half, y=0.0, width=pad_w, height=pad_h, shape="rect"),
        PadGeometry("2", x=+half, y=0.0, width=pad_w, height=pad_h, shape="rect"),
    )


# ---------------------------------------------------------------------------
# Chip passives — IPC-7351B Nominal (Level B)
# ---------------------------------------------------------------------------

def pads_chip_0402() -> tuple[PadGeometry, ...]:
    """0402 (1005 metric) chip resistor / capacitor.

    Source: IPC-7351B Table 3-5, Nominal density (Level B).
    Body: 1.0 × 0.5 mm.  Pad: 0.56 × 0.62 mm, pitch 0.95 mm.
    """
    return _chip_pads(pad_w=0.56, pad_h=0.62, pitch=0.95)


def pads_chip_0603() -> tuple[PadGeometry, ...]:
    """0603 (1608 metric) chip resistor / capacitor / LED.

    Source: IPC-7351B Table 3-7, Nominal density (Level B).
    Body: 1.6 × 0.8 mm.  Pad: 0.90 × 0.95 mm, pitch 1.60 mm.
    """
    return _chip_pads(pad_w=0.90, pad_h=0.95, pitch=1.60)


def pads_chip_0805() -> tuple[PadGeometry, ...]:
    """0805 (2012 metric) chip resistor / capacitor.

    Source: IPC-7351B Table 3-9, Nominal density (Level B).
    Body: 2.0 × 1.25 mm.  Pad: 1.20 × 1.40 mm, pitch 1.80 mm.
    """
    return _chip_pads(pad_w=1.20, pad_h=1.40, pitch=1.80)


def pads_chip_1210() -> tuple[PadGeometry, ...]:
    """1210 (3225 metric) chip capacitor (large MLCC for buck converter).

    Source: IPC-7351B Table 3-11, Nominal density (Level B).
    Body: 3.2 × 2.5 mm.  Pad: 1.75 × 2.50 mm, pitch 2.90 mm.
    """
    return _chip_pads(pad_w=1.75, pad_h=2.50, pitch=2.90)


def pads_chip_2512() -> tuple[PadGeometry, ...]:
    """2512 (6432 metric) chip resistor (current sense shunt).

    Source: IPC-7351B Table 3-13, Nominal density (Level B).
    Body: 6.4 × 3.2 mm.  Pad: 1.50 × 2.80 mm, pitch 5.80 mm.
    """
    return _chip_pads(pad_w=1.50, pad_h=2.80, pitch=5.80)


# ---------------------------------------------------------------------------
# LED 0603
# ---------------------------------------------------------------------------

def pads_led_0603() -> tuple[PadGeometry, ...]:
    """0603 LED (Wurth 150060xx75000 series).

    Same footprint as 0603 chip passive — polarity indicated by silkscreen.
    Source: IPC-7351B Table 3-7 + Wurth 150060VS75000 datasheet.
    """
    return pads_chip_0603()


# ---------------------------------------------------------------------------
# SOT-23 family
# ---------------------------------------------------------------------------

def pads_sot23_3() -> tuple[PadGeometry, ...]:
    """SOT-23 3-pin (e.g. BSS138 N-ch MOSFET, BZX84C15 Zener).

    Source: JEDEC TO-236AB / IPC-7351B Table 4-3 Nominal.
    Body: 2.9 × 1.3 mm.  Pad: 1.00 (X) × 0.60 (Y) mm.
    KiCad convention: width=X extent (outward from body), height=Y extent (lead width).
    Pin 1,2 at y=+1.0mm (left col), pin 3 at y=-1.0mm (right col).
    """
    return (
        PadGeometry("1", x=-0.95, y=+1.0, width=1.00, height=0.60, shape="rect"),
        PadGeometry("2", x=-0.95, y=-1.0, width=1.00, height=0.60, shape="rect"),
        PadGeometry("3", x=+0.95, y=0.0,  width=1.00, height=0.60, shape="rect"),
    )


def pads_sot23_5() -> tuple[PadGeometry, ...]:
    """SOT-23-5 (e.g. TPS7A20xx LDO, AP2112K LDO).

    Source: JEDEC MO-178 / IPC-7351B Table 4-3 Nominal.
    Body: 2.9 × 1.6 mm.  Pitch: 0.95 mm.  Pad: 1.10 (X) × 0.60 (Y) mm.
    Pins 1-3 on left column (y = -0.95, 0, +0.95), pins 4-5 on right.
    """
    pads = []
    # Left column: pins 1, 2, 3 (bottom to top)
    for i, pin_num in enumerate(["1", "2", "3"]):
        y = (i - 1) * 0.95
        pads.append(PadGeometry(pin_num, x=-1.10, y=y, width=1.10, height=0.60, shape="rect"))
    # Right column: pins 5, 4 (bottom to top — note pin numbering)
    for i, pin_num in enumerate(["5", "4"]):
        y = (i - 0.5) * 0.95
        pads.append(PadGeometry(pin_num, x=+1.10, y=y, width=1.10, height=0.60, shape="rect"))
    return tuple(pads)


def pads_sot23_6() -> tuple[PadGeometry, ...]:
    """SOT-23-6 (e.g. some regulators, logic ICs).

    Source: JEDEC MO-178 / IPC-7351B Nominal.
    Body: 2.9 × 1.6 mm.  Pitch: 0.95 mm.  Pad: 1.10 (X) × 0.60 (Y) mm.
    Pins 1-3 left, pins 4-6 right.
    """
    pads = []
    for i, pin_num in enumerate(["1", "2", "3"]):
        y = (i - 1) * 0.95
        pads.append(PadGeometry(pin_num, x=-1.10, y=y, width=1.10, height=0.60, shape="rect"))
    for i, pin_num in enumerate(["6", "5", "4"]):
        y = (i - 1) * 0.95
        pads.append(PadGeometry(pin_num, x=+1.10, y=y, width=1.10, height=0.60, shape="rect"))
    return tuple(pads)


def pads_sot23_8() -> tuple[PadGeometry, ...]:
    """SOT-23-8 (e.g. INA219BIDR current monitor).

    Source: TI DBV package (JEDEC MO-178) / IPC-7351B Nominal.
    Body: 2.9 × 1.6 mm.  Pitch: 0.65 mm.  Pad: 1.10 (X) × 0.40 (Y) mm.
    Pins 1-4 left column, pins 5-8 right column.
    """
    pads = []
    for i in range(4):
        y = (i - 1.5) * 0.65
        pads.append(PadGeometry(str(i + 1), x=-1.10, y=y, width=1.10, height=0.40, shape="rect"))
    for i in range(4):
        y = (1.5 - i) * 0.65
        pads.append(PadGeometry(str(i + 5), x=+1.10, y=y, width=1.10, height=0.40, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# SOT-353 / SC-70-5
# ---------------------------------------------------------------------------

def pads_sot353() -> tuple[PadGeometry, ...]:
    """SOT-353 / SC-70-5 (e.g. 74LVC1G17 Schmitt buffer).

    Source: JEDEC MO-203 / NXP SOT353 package outline.
    Body: 2.0 × 1.25 mm.  Pitch: 0.65 mm.  Pad: 0.80 (X) × 0.40 (Y) mm.
    Pins 1-3 left column, pins 4-5 right column.
    """
    pads = []
    for i, pin_num in enumerate(["1", "2", "3"]):
        y = (i - 1) * 0.65
        pads.append(PadGeometry(pin_num, x=-0.85, y=y, width=0.80, height=0.40, shape="rect"))
    for i, pin_num in enumerate(["5", "4"]):
        y = (i - 0.5) * 0.65
        pads.append(PadGeometry(pin_num, x=+0.85, y=y, width=0.80, height=0.40, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# SO-8 / SOIC-8
# ---------------------------------------------------------------------------

def pads_soic8() -> tuple[PadGeometry, ...]:
    """SO-8 / SOIC-8 (e.g. SI4435DDY P-ch MOSFET).

    Source: JEDEC MS-012 / IPC-7351B Table 4-7 Nominal.
    Body: 4.9 × 3.9 mm.  Pitch: 1.27 mm.  Pad: 1.55 (X) × 0.60 (Y) mm.
    Pad centre at ±2.475mm (KiCad std: SOIC-8_3.9x4.9mm_P1.27mm).
    Outer edge: 2.475 + 0.775 = 3.25mm.  Inner edge: 2.475 - 0.775 = 1.70mm.
    Pins 1-4 left, pins 5-8 right.
    """
    pads = []
    for i in range(4):
        y = (i - 1.5) * 1.27
        pads.append(PadGeometry(str(i + 1), x=-2.475, y=y, width=1.55, height=0.60, shape="rect"))
    for i in range(4):
        y = (1.5 - i) * 1.27
        pads.append(PadGeometry(str(i + 5), x=+2.475, y=y, width=1.55, height=0.60, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# HSOP-8 with PowerPAD (TPS54560)
# ---------------------------------------------------------------------------

def pads_hsop8_powerpad() -> tuple[PadGeometry, ...]:
    """HSOP-8 / HSOIC-8 with exposed thermal pad (TPS54560DDAR).

    Source: TI DDA package mechanical drawing (MPDS081B).
    Body: 6.2 × 5.0 mm.  Pitch: 1.27 mm.  Pad: 2.00 (X) × 0.60 (Y) mm.
    Pad centre at ±2.90mm.  Outer edge: 3.90mm.  Inner edge: 0.90mm.
    Exposed pad (pin 9): 3.40 (X) × 4.00 (Y) mm (fits between pin columns).
    Pins 1-4 left column, pins 5-8 right column, pin 9 = epad centre.
    """
    pads = []
    for i in range(4):
        y = (i - 1.5) * 1.27
        pads.append(PadGeometry(str(i + 1), x=-2.90, y=y, width=2.00, height=0.60, shape="rect"))
    for i in range(4):
        y = (1.5 - i) * 1.27
        pads.append(PadGeometry(str(i + 5), x=+2.90, y=y, width=2.00, height=0.60, shape="rect"))
    # Exposed thermal pad
    pads.append(PadGeometry("9", x=0.0, y=0.0, width=3.40, height=4.00, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# TSSOP-24
# ---------------------------------------------------------------------------

def pads_tssop24() -> tuple[PadGeometry, ...]:
    """TSSOP-24 (e.g. TCA9548APWR I2C mux).

    Source: TI PW package (JEDEC MO-153) / IPC-7351B Table 4-9 Nominal.
    Body: 4.4 × 7.8 mm.  Pitch: 0.65 mm.  Pad: 1.45 (X) × 0.35 (Y) mm.
    Pad centre at ±2.875mm (KiCad std: TSSOP-24_4.4x7.8mm_P0.65mm).
    Outer edge: 2.875 + 0.725 = 3.60mm.  Inner edge: 2.875 - 0.725 = 2.15mm.
    Pins 1-12 left column, pins 13-24 right column.
    """
    pads = []
    for i in range(12):
        y = (i - 5.5) * 0.65
        pads.append(PadGeometry(str(i + 1), x=-2.875, y=y, width=1.45, height=0.35, shape="rect"))
    for i in range(12):
        y = (5.5 - i) * 0.65
        pads.append(PadGeometry(str(i + 13), x=+2.875, y=y, width=1.45, height=0.35, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# QFN-24 3×3mm (ICM-20948)
# ---------------------------------------------------------------------------

def pads_qfn24_3x3(epad_w: float = 1.70, epad_h: float = 1.54) -> tuple[PadGeometry, ...]:
    """QFN-24 3.0 × 3.0 mm (e.g. ICM-20948 9-axis IMU).

    Source: InvenSense DS-000189 Rev 1.3, Table 9 — Mechanical Specifications.
    Body: 3.0 × 3.0 × 1.04 mm.  Pitch: 0.50 mm.
    Pad: 0.25 × 0.85 mm (land pattern from recommended footprint).
    Exposed pad: epad_w × epad_h (1.70 × 1.54 mm nominal).
    Pin 1 is at top-left corner (standard QFN convention).

    24 perimeter pads: 6 per side.
    """
    pads = []
    pad_w = 0.25
    pad_h = 0.85
    pitch = 0.50
    # Distance from centre to pad centre (along the major axis)
    edge = 1.50 + pad_h / 2  # body half-width + pad extends outward

    # Bottom side: pins 1-6 (left to right)
    for i in range(6):
        x = (i - 2.5) * pitch
        pads.append(PadGeometry(str(i + 1), x=x, y=edge, width=pad_w, height=pad_h, shape="rect"))
    # Right side: pins 7-12 (bottom to top)
    for i in range(6):
        y = (2.5 - i) * pitch
        pads.append(PadGeometry(str(i + 7), x=edge, y=y, width=pad_h, height=pad_w, shape="rect"))
    # Top side: pins 13-18 (right to left)
    for i in range(6):
        x = (2.5 - i) * pitch
        pads.append(PadGeometry(str(i + 13), x=x, y=-edge, width=pad_w, height=pad_h, shape="rect"))
    # Left side: pins 19-24 (top to bottom)
    for i in range(6):
        y = (i - 2.5) * pitch
        pads.append(PadGeometry(str(i + 19), x=-edge, y=y, width=pad_h, height=pad_w, shape="rect"))
    # Exposed pad
    pads.append(PadGeometry("25", x=0.0, y=0.0, width=epad_w, height=epad_h, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# VQFN-16 (SN74AVC4T245)
# ---------------------------------------------------------------------------

def pads_vqfn16(epad: float = 1.70) -> tuple[PadGeometry, ...]:
    """VQFN-16 3.5 × 3.5 mm (e.g. SN74AVC4T245RGYR level translator).

    Source: TI RGY package drawing (SLVSE80 / MPQF003B).
    Body: 3.5 × 3.5 mm.  Pitch: 0.50 mm.
    Pad: 0.30 × 0.85 mm.  Exposed pad: epad × epad.
    4 pads per side, 16 total + exposed pad (pin 17).
    """
    pads = []
    pad_w = 0.30
    pad_h = 0.85
    pitch = 0.50
    edge = 1.75 + pad_h / 2

    # Bottom: pins 1-4
    for i in range(4):
        x = (i - 1.5) * pitch
        pads.append(PadGeometry(str(i + 1), x=x, y=edge, width=pad_w, height=pad_h, shape="rect"))
    # Right: pins 5-8
    for i in range(4):
        y = (1.5 - i) * pitch
        pads.append(PadGeometry(str(i + 5), x=edge, y=y, width=pad_h, height=pad_w, shape="rect"))
    # Top: pins 9-12
    for i in range(4):
        x = (1.5 - i) * pitch
        pads.append(PadGeometry(str(i + 9), x=x, y=-edge, width=pad_w, height=pad_h, shape="rect"))
    # Left: pins 13-16
    for i in range(4):
        y = (i - 1.5) * pitch
        pads.append(PadGeometry(str(i + 13), x=-edge, y=y, width=pad_h, height=pad_w, shape="rect"))
    # Exposed pad
    pads.append(PadGeometry("17", x=0.0, y=0.0, width=epad, height=epad, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# LGA-10 2×2mm (BMP390)
# ---------------------------------------------------------------------------

def pads_lga10_2x2() -> tuple[PadGeometry, ...]:
    """LGA-10 2.0 × 2.0 mm (BMP390 barometric pressure sensor).

    Source: Bosch BST-BMP390-DS002 Rev 1.1, Figure 5 — Package Drawing.
    Body: 2.0 × 2.0 × 0.8 mm.  10 pads arranged:
      - Bottom row (pins 1-5): 5 pads at y=+0.55mm, pitch 0.40mm
      - Top row (pins 6-10): 5 pads at y=-0.55mm, pitch 0.40mm
    Pad: 0.35 × 0.30 mm.
    """
    pads = []
    pad_w = 0.35
    pad_h = 0.30
    pitch = 0.40
    # Bottom row: pins 1-5 (left to right)
    for i in range(5):
        x = (i - 2) * pitch
        pads.append(PadGeometry(str(i + 1), x=x, y=0.55, width=pad_w, height=pad_h, shape="rect"))
    # Top row: pins 6-10 (right to left)
    for i in range(5):
        x = (2 - i) * pitch
        pads.append(PadGeometry(str(i + 6), x=x, y=-0.55, width=pad_w, height=pad_h, shape="rect"))
    return tuple(pads)


# ---------------------------------------------------------------------------
# Diode packages
# ---------------------------------------------------------------------------

def pads_sod882() -> tuple[PadGeometry, ...]:
    """SOD-882 ultra-small diode (e.g. PESD5V0S1BL TVS diode).

    Source: NXP SOD882 package outline drawing.
    Body: 1.0 × 0.6 × 0.48 mm.  Pad: 0.30 × 0.40 mm, pitch 0.65 mm.
    """
    return _chip_pads(pad_w=0.30, pad_h=0.40, pitch=0.65)


def pads_sod323() -> tuple[PadGeometry, ...]:
    """SOD-323 small diode.

    Source: JEDEC SOD-323 / Diodes Inc. package drawing.
    Body: 1.7 × 1.25 mm.  Pad: 0.50 × 0.60 mm, pitch 1.90 mm.
    """
    return _chip_pads(pad_w=0.50, pad_h=0.60, pitch=1.90)


def pads_sma() -> tuple[PadGeometry, ...]:
    """SMA / DO-214AC diode (e.g. SS14 Schottky).

    Source: IPC-7351B Table 5-3 Nominal / DO-214AC JEDEC.
    Body: 3.6 × 2.6 mm.  Pad: 1.60 × 2.20 mm, pitch 3.90 mm.
    """
    return _chip_pads(pad_w=1.60, pad_h=2.20, pitch=3.90)


def pads_smb() -> tuple[PadGeometry, ...]:
    """SMB / DO-214AA diode (e.g. SMBJ20A TVS).

    Source: IPC-7351B Table 5-5 Nominal / DO-214AA JEDEC.
    Body: 5.3 × 3.6 mm.  Pad: 2.00 × 2.50 mm, pitch 4.60 mm.
    """
    return _chip_pads(pad_w=2.00, pad_h=2.50, pitch=4.60)


# ---------------------------------------------------------------------------
# Connectors — JST-XH through-hole
# ---------------------------------------------------------------------------

def pads_jst_xh(n_pins: int) -> tuple[PadGeometry, ...]:
    """JST-XH through-hole header (2.54mm pitch).

    Source: JST eXH.pdf — B2B-XH-A / B3B-XH-A series.
    Drill: 1.0mm.  Pad: 1.70mm diameter (annular ring = 0.35mm/side).
    Pitch: 2.54mm.
    """
    pads = []
    span = (n_pins - 1) * 2.54
    for i in range(n_pins):
        x = -span / 2 + i * 2.54
        pads.append(PadGeometry(
            str(i + 1), x=x, y=0.0, width=1.70, height=1.70,
            shape="circle", pad_type="thru_hole", layers=TH_LAYERS, drill=1.0,
        ))
    return tuple(pads)


# ---------------------------------------------------------------------------
# Connectors — JST-SH SMD
# ---------------------------------------------------------------------------

def pads_jst_sh(n_pins: int) -> tuple[PadGeometry, ...]:
    """JST-SH SMD header (1.0mm pitch).

    Source: JST eSH.pdf — SM0xB-SRSS-TB series.
    KiCad std ref: JST_SH_SM0xB-SRSS-TB_1x0N-1MP_P1.00mm_Horizontal.
    Signal pad: 0.60 (X) × 1.55 (Y) mm at y=0.  Pitch: 1.0mm.
    Mounting tabs: 1.00 (X) × 1.80 (Y) mm at y=-1.40 (behind signal pads).
    """
    pads = []
    span = (n_pins - 1) * 1.0
    for i in range(n_pins):
        x = -span / 2 + i * 1.0
        pads.append(PadGeometry(
            str(i + 1), x=x, y=0.0, width=0.60, height=1.55, shape="rect",
        ))
    # Mounting tabs (MP1, MP2) — structural only, offset behind signal pads
    tab_x = span / 2 + 1.85
    pads.append(PadGeometry(
        "MP1", x=-tab_x, y=-1.40, width=1.00, height=1.80, shape="rect",
    ))
    pads.append(PadGeometry(
        "MP2", x=+tab_x, y=-1.40, width=1.00, height=1.80, shape="rect",
    ))
    return tuple(pads)


# ---------------------------------------------------------------------------
# Connector — 24-pin 0.5mm FPC ZIF (Molex 5051102491)
# ---------------------------------------------------------------------------

def pads_fpc_zif_24() -> tuple[PadGeometry, ...]:
    """24-pin 0.5mm pitch FPC ZIF connector (Molex 5051102491).

    Source: Molex product page 5051102491 / drawing 505110-2491.
    Signal pad: 0.30 (X) × 1.30 (Y) mm at y=0.  Pitch: 0.50mm.
    Mounting tabs: 1.20 (X) × 2.10 (Y) mm at y=-1.10 (behind signal pads).
    """
    pads = []
    span = 23 * 0.50
    for i in range(24):
        x = -span / 2 + i * 0.50
        pads.append(PadGeometry(
            str(i + 1), x=x, y=0.0, width=0.30, height=1.30, shape="rect",
        ))
    # Mounting tabs — offset behind signal pads (toward connector body)
    tab_x = span / 2 + 1.50
    pads.append(PadGeometry(
        "MP1", x=-tab_x, y=-1.10, width=1.20, height=2.10, shape="rect",
    ))
    pads.append(PadGeometry(
        "MP2", x=+tab_x, y=-1.10, width=1.20, height=2.10, shape="rect",
    ))
    return tuple(pads)


# ---------------------------------------------------------------------------
# Connector — 2×20 pin header (GPIO)
# ---------------------------------------------------------------------------

def pads_header_2x20() -> tuple[PadGeometry, ...]:
    """2×20 through-hole pin header (2.54mm pitch, e.g. SSQ-120-03-G-D).

    Source: Standard 0.1" header per JEDEC.
    Drill: 1.0mm.  Pad: 1.70mm diameter.  Row spacing: 2.54mm.
    40 pins total: odd pins in row A, even in row B.

    Pin numbering follows DE10-Nano GPIO convention:
    Pin 1 = top-left, pin 2 = top-right, etc. (zigzag).
    """
    pads = []
    pitch = 2.54
    for i in range(40):
        row = i % 2          # 0 = left column, 1 = right column
        col = i // 2         # position along column
        x = (row - 0.5) * pitch   # ±1.27mm from centre
        y = (col - 9.5) * pitch   # 20 positions, centred
        pads.append(PadGeometry(
            str(i + 1), x=x, y=y, width=1.70, height=1.70,
            shape="circle", pad_type="thru_hole", layers=TH_LAYERS, drill=1.0,
        ))
    return tuple(pads)


# ---------------------------------------------------------------------------
# Connector — XT60PW PCB mount
# ---------------------------------------------------------------------------

def pads_xt60pw() -> tuple[PadGeometry, ...]:
    """XT60PW-M PCB-mount battery connector (Amass).

    Source: Amass XT60PW mechanical drawing / SnapEDA footprint.
    2 power pins (7.5mm pitch) + 2 locating tabs.
    Drill: 2.0mm for power pins.  Pad: 3.50mm diameter.
    """
    return (
        PadGeometry("1", x=-3.75, y=0.0, width=3.50, height=3.50,
                     shape="circle", pad_type="thru_hole", layers=TH_LAYERS, drill=2.0),
        PadGeometry("2", x=+3.75, y=0.0, width=3.50, height=3.50,
                     shape="circle", pad_type="thru_hole", layers=TH_LAYERS, drill=2.0),
    )


# ---------------------------------------------------------------------------
# Connector — PJ-102AH barrel jack
# ---------------------------------------------------------------------------

def pads_barrel_jack() -> tuple[PadGeometry, ...]:
    """PJ-102AH 5.5×2.1mm barrel jack (Same Sky / CUI Devices).

    Source: Same Sky PJ-102A datasheet.
    3 pins: centre (tip), barrel (sleeve), switch (N/C for this design).
    Through-hole with various drill sizes.
    """
    return (
        PadGeometry("1", x=0.0, y=0.0, width=2.50, height=2.50,
                     shape="circle", pad_type="thru_hole", layers=TH_LAYERS, drill=1.50),
        PadGeometry("2", x=-3.00, y=4.70, width=3.50, height=3.50,
                     shape="oval", pad_type="thru_hole", layers=TH_LAYERS, drill=2.00),
        PadGeometry("3", x=3.00, y=4.70, width=3.50, height=3.50,
                     shape="oval", pad_type="thru_hole", layers=TH_LAYERS, drill=2.00),
    )


# ---------------------------------------------------------------------------
# Connector — XT30PW (arm switch)
# ---------------------------------------------------------------------------

def pads_xt30pw() -> tuple[PadGeometry, ...]:
    """XT30PW-F PCB-mount arm switch connector (Amass).

    Source: Amass XT30PW mechanical drawing.
    2 power pins, 4.0mm pitch.  Drill: 1.5mm.  Pad: 2.50mm.
    """
    return (
        PadGeometry("1", x=-2.0, y=0.0, width=2.50, height=2.50,
                     shape="circle", pad_type="thru_hole", layers=TH_LAYERS, drill=1.50),
        PadGeometry("2", x=+2.0, y=0.0, width=2.50, height=2.50,
                     shape="circle", pad_type="thru_hole", layers=TH_LAYERS, drill=1.50),
    )


# ---------------------------------------------------------------------------
# WILC3000 module (castellated pads)
# ---------------------------------------------------------------------------

def pads_wilc3000_module() -> tuple[PadGeometry, ...]:
    """ATWILC3000-MR110UB WiFi/BLE module (Microchip).

    Source: Microchip DS70005327B — Recommended Footprint.
    Module: 19.2 × 13.7 mm.  Castellated pads along three edges.

    Simplified pad layout — 34 castellated pads total.
    Key pads: VCC (multiple), GND (multiple), SPI (CLK/MOSI/MISO/SSN),
    IRQ, CHIP_EN, RESETN.
    """
    pads = []
    # Bottom edge: 16 pads, pitch 1.0mm
    for i in range(16):
        x = (i - 7.5) * 1.0
        pads.append(PadGeometry(
            str(i + 1), x=x, y=6.85, width=0.60, height=1.00, shape="rect",
        ))
    # Right edge: 7 pads, pitch 1.2mm
    for i in range(7):
        y = (3.0 - i) * 1.2
        pads.append(PadGeometry(
            str(i + 17), x=9.60, y=y, width=1.00, height=0.60, shape="rect",
        ))
    # Top edge: 8 pads, pitch 1.0mm
    for i in range(8):
        x = (3.5 - i) * 1.0
        pads.append(PadGeometry(
            str(i + 24), x=x, y=-6.85, width=0.60, height=1.00, shape="rect",
        ))
    # Left edge: 3 pads
    for i in range(3):
        y = (i - 1) * 1.2
        pads.append(PadGeometry(
            str(i + 32), x=-9.60, y=y, width=1.00, height=0.60, shape="rect",
        ))
    return tuple(pads)


# ---------------------------------------------------------------------------
# Inductor — SRP1265A
# ---------------------------------------------------------------------------

def pads_inductor_1265() -> tuple[PadGeometry, ...]:
    """SRP1265A shielded power inductor (Bourns).

    Source: Bourns SRP1265A series datasheet.
    Body: 12.5 × 12.5 × 6.5 mm.  Pad: 3.80 × 4.50 mm, pitch 8.80 mm.
    """
    return (
        PadGeometry("1", x=-4.40, y=0.0, width=3.80, height=4.50, shape="rect"),
        PadGeometry("2", x=+4.40, y=0.0, width=3.80, height=4.50, shape="rect"),
    )


# ---------------------------------------------------------------------------
# Mounting hole (non-plated through-hole)
# ---------------------------------------------------------------------------

def pads_mounting_hole(drill_d: float, pad_d: float = 0.0) -> tuple[PadGeometry, ...]:
    """Non-plated through-hole mounting hole.

    If pad_d == 0, uses drill_d + 2 × JLCPCB_MIN_ANNULAR_MM.
    For GND-tied mounting holes, use a plated through-hole instead.
    """
    if pad_d <= 0:
        pad_d = drill_d + 2 * JLCPCB_MIN_ANNULAR_MM
    return (
        PadGeometry(
            "1", x=0.0, y=0.0, width=pad_d, height=pad_d,
            shape="circle", pad_type="np_thru_hole", layers=NPTH_LAYERS, drill=drill_d,
        ),
    )
