"""Custom daughter board — sensor hub, level shifters, power regulation.

Mounts above DE10-Nano via M2.5 standoffs at the same hole pattern.
Two 2x20 GPIO receptacle headers connect to DE10-Nano GPIO0 and GPIO1.
"""

import json
from pathlib import Path

try:
    import cadquery as cq
except ImportError:
    cq = None

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

from cadquery_framework.kicad.jlcpcb_constraints import (
    CU_OUTER_MM, CU_INNER_MM,
    PREPREG_THICKNESS_MM, PREPREG_MATERIAL, PREPREG_DK, PREPREG_LOSS_TANGENT,
    CORE_THICKNESS_MM, CORE_MATERIAL, CORE_DK, CORE_LOSS_TANGENT,
    SOLDER_MASK_THICKNESS_MM, SOLDER_MASK_EXPANSION_MM, SOLDER_MASK_MIN_WIDTH_MM,
    TH_GPIO_DRILL_MM, TH_GPIO_PAD_MM, TH_M25_DRILL_MM, TH_M25_PAD_MM,
    EDGE_CUTS_WIDTH_MM, COURTYARD_WIDTH_MM,
    SILK_LARGE_SIZE_MM, SILK_LARGE_THICK_MM,
    SILK_REF_SIZE_MM, SILK_REF_THICK_MM,
    SILK_SMALL_SIZE_MM, SILK_SMALL_THICK_MM,
    SILK_MICRO_SIZE_MM, SILK_MICRO_THICK_MM,
    SILK_FAB_SIZE_MM, SILK_FAB_THICK_MM,
    DRM_MIN_TRACE_MM, JLCPCB_MIN_DRILL_MM,
)

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

DB_W = _D["daughter_board"]["width"]
DB_L = _D["daughter_board"]["length"]
DB_H = _D["daughter_board"]["pcb_thickness"]

# Mounting holes — same pattern as DE10-Nano
DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
DB_MOUNT_HOLE_D = _D["daughter_board_mounting"]["mounting_hole_diameter"]
DB_MOUNT_INSET  = _D["daughter_board_mounting"]["mounting_hole_inset"]

# GPIO header receptacles
GPIO_PITCH  = _D["daughter_board_mounting"]["gpio_receptacle_pitch"]
GPIO_ROWS   = _D["daughter_board_mounting"]["gpio_receptacle_rows"]
GPIO_COLS   = _D["daughter_board_mounting"]["gpio_receptacle_cols"]
GPIO_LENGTH = (GPIO_COLS - 1) * GPIO_PITCH  # 48.26mm for 2x20
GPIO_WIDTH  = (GPIO_ROWS - 1) * GPIO_PITCH  # 2.54mm for 2-row
GPIO_HEADER_H = 8.5  # receptacle housing height (extends downward toward DE10)

CATALOG = {
    "daughter_board": {
        "material": "FR4 PCB + components",
        "dims": "85 x 100 x 1.6mm",
        "mass_g": 35, "qty": 1,
        "supplier": "Custom PCB (JLCPCB)",
        "notes": "Sensor hub: level shifter, I2C mux, barometer, power regulators",
        "interface": "Stacks above DE10-Nano on standoffs",
    },
}


def make_daughter_board():
    """Daughter board with M2.5 mounting holes, GPIO receptacles, and IC footprints."""
    pcb_chamfer = _D["assembly"]["pcb_edge_chamfer"]
    board_chamfer = min(pcb_chamfer, DB_H * 0.45)
    board = (
        cq.Workplane("XY")
        .rect(DB_W, DB_L)
        .extrude(DB_H)
        .edges("|Z")
        .chamfer(board_chamfer)
    )

    # M2.5 mounting holes (match DE10-Nano corner pattern)
    for dx in [-DE10_W/2 + DB_MOUNT_INSET, DE10_W/2 - DB_MOUNT_INSET]:
        for dy in [-DE10_L/2 + DB_MOUNT_INSET, DE10_L/2 - DB_MOUNT_INSET]:
            hole = (
                cq.Workplane("XY")
                .center(dx, dy)
                .circle(DB_MOUNT_HOLE_D / 2)
                .extrude(DB_H)
            )
            board = board.cut(hole)

    # GPIO receptacle headers (2x20, extending downward to mate with DE10-Nano)
    # Use Intel-to-CQ coordinate transform matching de10_nano.py
    gpio_connectors = _D["de10_nano"]["connectors"]
    for key in ("gpio0", "gpio1"):
        c = gpio_connectors[key]
        # Intel layout: x along 107mm length, y along 68.6mm width
        cq_x = DE10_W / 2 - c["intel_y"]
        cq_y = c["intel_x"] - DE10_L / 2
        # Header block extending downward (negative Z)
        header = (
            cq.Workplane("XY")
            .center(cq_x, cq_y + c["length"] / 2)
            .rect(GPIO_WIDTH + 2.0, c["length"] + 2.0)
            .extrude(-GPIO_HEADER_H)
            .edges("|Z")
            .chamfer(min(0.6, pcb_chamfer))
        )
        board = board.union(header)

    # Arduino header receptacles (extend downward to mate with DE10 Arduino headers)
    for key in ("arduino_digital_hi", "arduino_digital_lo", "arduino_analog", "arduino_power"):
        if key not in gpio_connectors:
            continue
        c = gpio_connectors[key]
        cq_x = DE10_W / 2 - c["intel_y"]
        cq_y = c["intel_x"] - DE10_L / 2
        ard_header = (
            cq.Workplane("XY")
            .center(cq_x, cq_y)
            .rect(c["width"] + 2.0, c["length"] + 2.0)
            .extrude(-GPIO_HEADER_H)
            .edges("|Z")
            .chamfer(min(0.6, pcb_chamfer))
        )
        board = board.union(ard_header)

    # Central heatsink/fan cutout — the DE10 heatsink (40x40mm) and cooling fan
    # protrude through this opening. 2mm clearance on each side.
    _hs_w = _D["de10_nano"]["heatsink_width"]
    _hs_l = _D["de10_nano"]["heatsink_length"]
    hs_cutout = (
        cq.Workplane("XY")
        .rect(_hs_w + 4, _hs_l + 4)
        .extrude(DB_H)
        .edges("|Z")
        .chamfer(board_chamfer)
    )
    board = board.cut(hs_cutout)

    # IC component blocks (level shifters, mux, power regulators)
    # Positioned around the heatsink cutout, not overlapping it
    for pos in [(25, 20), (-25, -15), (25, -15), (0, -30)]:
        ic = (
            cq.Workplane("XY")
            .center(pos[0], pos[1])
            .rect(8, 8)
            .extrude(DB_H + 2)
            .edges("|Z")
            .chamfer(min(0.6, pcb_chamfer))
        )
        board = board.union(ic)

    # Anchor points
    anchors = {}
    if Anchor is not None:
        anchors["bottom_face"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Daughter board bottom mates with DE10 headers")
        # Top face at tallest IC block height — used for top plate clearance chain
        _ic_top = DB_H + 2  # PCB + IC component height
        anchors["top_face"] = Anchor(point=(0, 0, _ic_top), normal=(0, 0, 1), label="Tallest point on daughter board")

        # Mounting holes matching DE10-Nano corner pattern (bottom — mates lower standoffs)
        idx = 1
        for dx in [-DE10_W/2 + DB_MOUNT_INSET, DE10_W/2 - DB_MOUNT_INSET]:
            for dy in [-DE10_L/2 + DB_MOUNT_INSET, DE10_L/2 - DB_MOUNT_INSET]:
                anchors[f"mounting_hole_{idx}"] = Anchor(
                    point=(dx, dy, 0), normal=(0, 0, -1),
                    label=f"M2.5 mounting hole {idx} (bottom)")
                # Upper standoff mount point — top of PCB at same XY
                anchors[f"standoff_top_{idx}"] = Anchor(
                    point=(dx, dy, DB_H), normal=(0, 0, 1),
                    label=f"upper standoff mount {idx} (top)")
                idx += 1

        # ToF-up mount on top surface corner — -X side to avoid ethernet (+X)
        anchors["tof_mount_up"] = Anchor(
            point=(-(DB_W / 2 - 8), DB_L / 2 - 8, _ic_top),
            normal=(0, 0, 1),
            label="ToF up — board direct-mount on daughter board top surface, sensor faces +Z",
        )

        # GPIO receptacles at same positions as DE10 headers, pointing down
        for key, anchor_name in (("gpio0", "gpio0_receptacle"), ("gpio1", "gpio1_receptacle")):
            c = gpio_connectors[key]
            cq_x = DE10_W / 2 - c["intel_y"]
            cq_y = c["intel_x"] - DE10_L / 2
            anchors[anchor_name] = Anchor(
                point=(cq_x, cq_y + c["length"] / 2, 0),
                normal=(0, 0, -1),
                label=f"{key.upper()} receptacle (PCB bottom, mates header top)")

    return board, anchors


# =============================================================================
# KiCad PCB generator
# =============================================================================

try:
    from cadquery_framework.kicad.primitives import (
        rounded_rect_outline, outline_to_sexpr, through_hole_pad,
        text_sexpr, kicad_pcb_wrapper,
    )
    import uuid as _uuid
    _KI_AVAIL = True
except ImportError:
    _KI_AVAIL = False

# ── Coordinate transform ──────────────────────────────────────────────────────
# Intel PCB coords:   origin = board bottom-left corner
#                     X along 107.95mm (length) axis
#                     Y along 68.58mm  (width)  axis
# CadQuery / KiCad:   origin = board center
#                     CQ_X = DE10_W/2 - intel_y
#                     CQ_Y = intel_x  - DE10_L/2
# ─────────────────────────────────────────────────────────────────────────────

# Full GPIO0 (JP1) pin→net mapping.
# DE10-Nano 2x20 header pin numbering: odd pins on row A, even pins on row B.
# Row A = column closer to board centre (lower intel_y).
# Pins increment along +Y (increasing intel_x).
# Net names follow the design doc signal assignments.
_GPIO0_NETS = {
    # pin: net_name
     1: "CAM_D0",        2: "CAM_D1",
     3: "CAM_D2",        4: "CAM_D3",
     5: "CAM_D4",        6: "CAM_D5",
     7: "CAM_D6",        8: "CAM_D7",
     9: "CAM_PCLK",     10: "CAM_VSYNC",
    11: "CAM_HSYNC",    12: "CAM_XCLK",
    13: "CAM_SIOC",     14: "CAM_SIOD",
    15: "CAM_PWDN",     16: "CAM_RESET",
    17: "DSHOT_CH1",    18: "DSHOT_CH2",
    19: "DSHOT_CH3",    20: "DSHOT_CH4",
    21: "PUMP_PWM",     22: "BUZZER_PWM",
    23: "ARM_SW_IN",    24: "ESTOP_IN",
    25: "DOCK_DET",     26: "LED_POWER",
    27: "LED_ARMED",    28: "LED_BEACON",
    29: "+5V",          30: "+3V3",
    31: "LED_ERROR",    32: "CHARGE_SENSE1",
    33: "CHARGE_SENSE2",34: "GPIO0_SPARE34",
    35: "GND",          36: "GND",
    37: "GPIO0_SPARE37",38: "GPIO0_SPARE38",
    39: "GPIO0_SPARE39",40: "GPIO0_SPARE40",
}

# Full GPIO1 (JP2) pin→net mapping.
_GPIO1_NETS = {
     1: "IMU_SCLK",      2: "IMU_MOSI",
     3: "IMU_MISO",      4: "IMU_CS_N",
     5: "IMU_INT",       6: "TOF_I2C_SCL",
     7: "TOF_I2C_SDA",   8: "TOF_MUX_RST_N",
     9: "TOF_XSHUT0",   10: "TOF_XSHUT1",
    11: "TOF_XSHUT2",   12: "TOF_XSHUT3",
    13: "IR_RX_FRONT",  14: "IR_RX_LEFT",
    15: "IR_RX_RIGHT",  16: "IR_RX_REAR",
    17: "INA219_ALERT", 18: "GPIO1_SPARE18",
    19: "GPIO1_SPARE19",20: "GPIO1_SPARE20",
    21: "GPIO1_SPARE21",22: "GPIO1_SPARE22",
    23: "GPIO1_SPARE23",24: "GPIO1_SPARE24",
    25: "GPIO1_SPARE25",26: "GPIO1_SPARE26",
    27: "GPIO1_SPARE27",28: "GPIO1_SPARE28",
    29: "+5V",          30: "+3V3",
    31: "GPIO1_SPARE31",32: "GPIO1_SPARE32",
    33: "GPIO1_SPARE33",34: "GPIO1_SPARE34",
    35: "GND",          36: "GND",
    37: "GPIO1_SPARE37",38: "GPIO1_SPARE38",
    39: "GPIO1_SPARE39",40: "GPIO1_SPARE40",
}

# Power / ground net names used across the board
_PWR_NETS = {"+5V", "+3V3", "+1V8", "GND"}

# Component placements: (ref, value, cx, cy, width_mm, height_mm, layer, description)
# All coordinates in board-centre frame (mm).  Layer "F" = front, "B" = back.
# Positions are chosen to avoid the heatsink cutout (±22mm), mounting holes,
# and GPIO connector areas.  Left half (X<0) = GPIO0 subsystems.
# Right half (X>0) = GPIO1 subsystems.  Top strip (Y>30) = power/misc.
_COMPONENTS = [
    # ── GPIO0 subsystems (left side) ─────────────────────────────────────────
    # U1-U4: DShot buffers (74LVC1G17, SOT-353, ~1.6x1.6mm)
    ("U1",  "74LVC1G17", -30.0,  25.0,  3.0,  3.0, "F", "DSHOT_CH1 Schmitt buf"),
    ("U2",  "74LVC1G17", -30.0,  20.0,  3.0,  3.0, "F", "DSHOT_CH2 Schmitt buf"),
    ("U3",  "74LVC1G17", -30.0,  15.0,  3.0,  3.0, "F", "DSHOT_CH3 Schmitt buf"),
    ("U4",  "74LVC1G17", -30.0,  10.0,  3.0,  3.0, "F", "DSHOT_CH4 Schmitt buf"),
    # D1-D4: TVS diodes on ESC signal lines (SOD-882, ~1.6x0.9mm)
    ("D1",  "PESD5V0S1BL", -26.0, 25.0, 2.0, 1.5, "F", "DSHOT_CH1 TVS"),
    ("D2",  "PESD5V0S1BL", -26.0, 20.0, 2.0, 1.5, "F", "DSHOT_CH2 TVS"),
    ("D3",  "PESD5V0S1BL", -26.0, 15.0, 2.0, 1.5, "F", "DSHOT_CH3 TVS"),
    ("D4",  "PESD5V0S1BL", -26.0, 10.0, 2.0, 1.5, "F", "DSHOT_CH4 TVS"),
    # J1-J4: JST-XH 3-pin ESC connectors (left board edge, evenly spaced)
    ("J1",  "JST-XH-3",  -34.0,  25.0,  7.5,  5.0, "F", "ESC1 connector"),
    ("J2",  "JST-XH-3",  -34.0,  18.0,  7.5,  5.0, "F", "ESC2 connector"),
    ("J3",  "JST-XH-3",  -34.0,  11.0,  7.5,  5.0, "F", "ESC3 connector"),
    ("J4",  "JST-XH-3",  -34.0,   4.0,  7.5,  5.0, "F", "ESC4 connector"),
    # J5: Pump/buzzer JST-XH 2-pin
    ("J5",  "JST-XH-2",  -34.0,  -4.0,  5.5,  5.0, "F", "Pump/buzzer out"),
    # ── GPIO1 subsystems (right side) ────────────────────────────────────────
    # U5: IMU level translator SN74AVC4T245 (TSSOP-16, ~5x4.4mm)
    ("U5",  "SN74AVC4T245",  28.0,  20.0,  6.0,  5.5, "F", "IMU SPI level xlat"),
    # U6: 1.8V LDO for IMU (SOT-23-5, ~3x2mm)
    ("U6",  "TPS7A2018",     28.0,  12.0,  3.5,  2.5, "F", "1.8V LDO for IMU"),
    # U7: ICM-20948 IMU (3x3mm LGA)
    ("U7",  "ICM-20948",     28.0,   5.0,  4.0,  4.0, "F", "9-axis IMU"),
    # U8: TCA9548A I2C mux for 6x ToF sensors (SOIC-24, ~8.6x7.5mm)
    ("U8",  "TCA9548A",      28.0,  -8.0,  9.5,  8.5, "F", "I2C mux for ToF"),
    # J6-J11: Molex Picoblade 4-pin for 6x ToF sensors (right side)
    ("J6",  "PICOBLADE-4",   34.0,  28.0,  5.0,  4.0, "F", "ToF sensor 0"),
    ("J7",  "PICOBLADE-4",   34.0,  22.0,  5.0,  4.0, "F", "ToF sensor 1"),
    ("J8",  "PICOBLADE-4",   34.0,  16.0,  5.0,  4.0, "F", "ToF sensor 2"),
    ("J9",  "PICOBLADE-4",   34.0,  10.0,  5.0,  4.0, "F", "ToF sensor 3"),
    ("J10", "PICOBLADE-4",   34.0,   4.0,  5.0,  4.0, "F", "ToF sensor 4 (up)"),
    ("J11", "PICOBLADE-4",   34.0,  -2.0,  5.0,  4.0, "F", "ToF sensor 5 (down)"),
    # J12-J15: IR receiver connectors (right edge, lower)
    ("J12", "JST-SH-3",      34.0, -10.0,  4.5,  3.5, "F", "IR front"),
    ("J13", "JST-SH-3",      34.0, -15.0,  4.5,  3.5, "F", "IR left"),
    ("J14", "JST-SH-3",      34.0, -20.0,  4.5,  3.5, "F", "IR right"),
    ("J15", "JST-SH-3",      34.0, -25.0,  4.5,  3.5, "F", "IR rear"),
    # ── Power section (top strip, above heatsink area) ────────────────────────
    # U9: INA219 current/voltage monitor (SOIC-8, ~5x4mm)
    ("U9",  "INA219",         0.0,  33.0,  5.5,  4.5, "F", "Battery V/I monitor"),
    # J16: Battery sense JST-XH 2-pin
    ("J16", "JST-XH-2",       8.0,  36.0,  5.5,  5.0, "F", "Batt sense input"),
    # J17: Status LED JST-SH 6-pin
    ("J17", "JST-SH-6",      -8.0,  36.0,  7.5,  3.5, "F", "Status LEDs"),
    # J18: Arm/estop switch JST-SH 3-pin
    ("J18", "JST-SH-3",     -16.0,  36.0,  4.5,  3.5, "F", "Arm/EStop switch"),
    # U10: Barometer (BMP390, LGA-8 2x2mm) — near board centre, shielded
    ("U10", "BMP390",        -3.0,  28.0,  3.0,  3.0, "F", "Barometric altimeter"),
    # C1-C10: Bulk decoupling (0402, scattered — courtyard only)
    ("C1",  "100nF",         24.0,  28.0,  1.5,  1.0, "F", "IMU VDD decoup"),
    ("C2",  "10uF",          25.5,  28.0,  2.0,  1.5, "F", "IMU VDD bulk"),
    ("C3",  "100nF",         24.0,  26.0,  1.5,  1.0, "F", "IMU VDDIO decoup"),
    ("C4",  "1uF",           25.5,  26.0,  2.0,  1.5, "F", "IMU REGOUT"),
    ("C5",  "4.7uF",         24.0,  10.0,  2.0,  1.5, "F", "1V8 LDO input"),
    ("C6",  "1uF",           25.5,  10.0,  2.0,  1.5, "F", "1V8 LDO output"),
    ("C7",  "100nF",         -3.0,  25.5,  1.5,  1.0, "F", "Baro decoup"),
    ("C8",  "100nF",          0.0,  30.5,  1.5,  1.0, "F", "INA219 decoup"),
    ("C9",  "100nF",         24.0, -12.0,  1.5,  1.0, "F", "TCA9548A decoup"),
    ("C10", "10uF",          25.5, -12.0,  2.0,  1.5, "F", "TCA9548A bulk"),
    # R1-R4: Pull-up resistors for IMU INT, TOF MUX RST (0402)
    ("R1",  "10k",           26.0,   2.0,  1.5,  1.0, "F", "IMU INT pull-up"),
    ("R2",  "10k",           26.0,   0.0,  1.5,  1.0, "F", "TOF MUX RST pull-up"),
    ("R3",  "4k7",           -5.0,  28.0,  1.5,  1.0, "F", "INA219 current shunt hi"),
    ("R4",  "4k7",           -5.0,  26.0,  1.5,  1.0, "F", "INA219 current shunt lo"),
]

# ── GPIO header connector layout ─────────────────────────────────────────────
# 2x20 male header, 2.54mm pitch, pins run along Y axis.
# In KiCad footprint convention: pin 1 at lowest-Y, odd pins on row A (lower X),
# even pins on row B (higher X).
_GPIO_LAYOUT = {
    "gpio0": {
        "ref":      "JP1",
        "value":    "2x20_GPIO0",
        "cx":       DE10_W / 2 - _D["de10_nano"]["connectors"]["gpio0"]["intel_y"],
        "y_pin1":   _D["de10_nano"]["connectors"]["gpio0"]["intel_x"] - DE10_L / 2,
        "nets":     _GPIO0_NETS,
        "label":    "JP1 GPIO0",
    },
    "gpio1": {
        "ref":      "JP2",
        "value":    "2x20_GPIO1",
        "cx":       DE10_W / 2 - _D["de10_nano"]["connectors"]["gpio1"]["intel_y"],
        "y_pin1":   _D["de10_nano"]["connectors"]["gpio1"]["intel_x"] - DE10_L / 2,
        "nets":     _GPIO1_NETS,
        "label":    "JP2 GPIO1",
    },
}


def _uid():
    return str(_uuid.uuid4())


def _net_sexpr(net_id, net_name):
    """KiCad net declaration."""
    return f'  (net {net_id} "{net_name}")'


def _th_pad_with_net(cx, cy, pad_no, drill_d, pad_d, net_id, net_name, square=False):
    """Through-hole pad inside a footprint, with net assignment."""
    shape = "rect" if square else "circle"
    return (
        f'    (pad "{pad_no}" thru_hole {shape} (at {cx:.4f} {cy:.4f}) '
        f'(size {pad_d:.2f} {pad_d:.2f}) (drill {drill_d:.2f}) '
        f'(layers "*.Cu" "*.Mask") '
        f'(net {net_id} "{net_name}") '
        f'(uuid "{_uid()}"))'
    )


def _gpio_footprint(layout, global_nets, pitch=2.54, drill_d=1.0, pad_d=1.7):
    """Generate a complete 2x20 through-hole GPIO receptacle footprint.

    Pin numbering follows DE10-Nano JP1/JP2 conventions:
      - Odd pins (1,3,5,...) are on row A: x = cx - pitch/2
      - Even pins (2,4,6,...) are on row B: x = cx + pitch/2
      - Pin 1 at y_pin1 (lowest Y), pin 39 at y_pin1 + 19*pitch

    global_nets: dict {net_name: net_id} — the file-wide net table (net 0 = "").
        Any NC pins not in global_nets are added to it automatically.
    Returns footprint_str.
    """
    cx    = layout["cx"]
    y_p1  = layout["y_pin1"]
    ref   = layout["ref"]
    value = layout["value"]
    nets  = layout["nets"]
    label = layout["label"]

    def _lookup(name):
        if name not in global_nets:
            global_nets[name] = len(global_nets)
        return global_nets[name]

    # Build pad list
    pads = []
    for pos in range(1, 21):      # 20 positions (rows of pins)
        pin_a = 2 * pos - 1       # odd pin number (row A, lower X)
        pin_b = 2 * pos           # even pin number (row B, higher X)
        y_pos = y_p1 + (pos - 1) * pitch   # Y increases with pin position
        xa    = cx - pitch / 2    # row A
        xb    = cx + pitch / 2    # row B

        net_a = nets.get(pin_a, f"NC_{ref}_{pin_a}")
        net_b = nets.get(pin_b, f"NC_{ref}_{pin_b}")

        pads.append(_th_pad_with_net(
            xa - cx, y_pos - (y_p1 + 19 * pitch / 2),   # relative to footprint origin
            pin_a, drill_d, pad_d,
            _lookup(net_a), net_a,
            square=(pin_a == 1),   # square pad on pin 1
        ))
        pads.append(_th_pad_with_net(
            xb - cx, y_pos - (y_p1 + 19 * pitch / 2),
            pin_b, drill_d, pad_d,
            _lookup(net_b), net_b,
        ))

    # Courtyard (F.Courtyard)
    cy_center = y_p1 + 19 * pitch / 2
    cyd_w = 2 * pitch + 2.0
    cyd_l = 19 * pitch + 2.0
    hw, hl = cyd_w / 2, cyd_l / 2
    courtyard = (
        f'    (fp_line (start {-hw:.3f} {-hl:.3f}) (end {hw:.3f} {-hl:.3f}) '
        f'(layer "F.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))\n'
        f'    (fp_line (start {hw:.3f} {-hl:.3f}) (end {hw:.3f} {hl:.3f}) '
        f'(layer "F.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))\n'
        f'    (fp_line (start {hw:.3f} {hl:.3f}) (end {-hw:.3f} {hl:.3f}) '
        f'(layer "F.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))\n'
        f'    (fp_line (start {-hw:.3f} {hl:.3f}) (end {-hw:.3f} {-hl:.3f}) '
        f'(layer "F.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))'
    )
    # Silkscreen pin-1 indicator and reference label
    silk_pin1 = (
        f'    (fp_text "1" (at {-(pitch / 2 + 2.0):.3f} {-hl + 0.5:.3f}) (layer "F.SilkS") '
        f'(uuid "{_uid()}")\n'
        f'      (effects (font (size {SILK_MICRO_SIZE_MM} {SILK_MICRO_SIZE_MM}) (thickness {SILK_MICRO_THICK_MM})))\n'
        f'    )'
    )
    silk_ref = (
        f'    (fp_text reference "{ref}" (at 0 {-hl - 2.5:.3f}) (layer "F.SilkS") '
        f'(uuid "{_uid()}")\n'
        f'      (effects (font (size {SILK_REF_SIZE_MM} {SILK_REF_SIZE_MM}) (thickness {SILK_REF_THICK_MM})))\n'
        f'    )'
    )
    silk_val = (
        f'    (fp_text value "{label}" (at 0 {hl + 2.0:.3f}) (layer "F.Fab") '
        f'(uuid "{_uid()}")\n'
        f'      (effects (font (size {SILK_SMALL_SIZE_MM} {SILK_SMALL_SIZE_MM}) (thickness {SILK_SMALL_THICK_MM})))\n'
        f'    )'
    )

    fp = (
        f'  (footprint "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical" '
        f'(layer "F.Cu") (uuid "{_uid()}")\n'
        f'  (at {cx:.4f} {cy_center:.4f})\n'
        f'  (descr "DE10-Nano {label} 2x20 receptacle")\n'
        f'{silk_ref}\n'
        f'{silk_val}\n'
        f'{courtyard}\n'
        + "\n".join(pads) + "\n"
        f'  )'
    )
    return fp


def _component_footprint(ref, value, cx, cy, w, h, layer, description):
    """Minimal courtyard + silkscreen footprint for a placed component."""
    hw, hh = w / 2, h / 2
    layer_prefix = "F" if layer == "F" else "B"
    lines = (
        f'  (footprint "custom:{ref}" (layer "{layer_prefix}.Cu") (uuid "{_uid()}")\n'
        f'  (at {cx:.4f} {cy:.4f})\n'
        f'  (descr "{description}")\n'
        f'    (fp_text reference "{ref}" (at 0 {-hh - 1.0:.3f}) (layer "{layer_prefix}.SilkS") '
        f'(uuid "{_uid()}")\n'
        f'      (effects (font (size {SILK_MICRO_SIZE_MM} {SILK_MICRO_SIZE_MM}) (thickness {SILK_MICRO_THICK_MM})))\n'
        f'    )\n'
        f'    (fp_text value "{value}" (at 0 {hh + 0.8:.3f}) (layer "{layer_prefix}.Fab") '
        f'(uuid "{_uid()}")\n'
        f'      (effects (font (size {SILK_FAB_SIZE_MM} {SILK_FAB_SIZE_MM}) (thickness {SILK_FAB_THICK_MM})))\n'
        f'    )\n'
        f'    (fp_line (start {-hw:.3f} {-hh:.3f}) (end {hw:.3f} {-hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))\n'
        f'    (fp_line (start {hw:.3f} {-hh:.3f}) (end {hw:.3f} {hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))\n'
        f'    (fp_line (start {hw:.3f} {hh:.3f}) (end {-hw:.3f} {hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))\n'
        f'    (fp_line (start {-hw:.3f} {hh:.3f}) (end {-hw:.3f} {-hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))\n'
        f'  )'
    )
    return lines


def _kicad_pcb_4layer(title, thickness, nets_block, content):
    """Full .kicad_pcb wrapper with a proper 4-layer stackup for an electrical PCB."""
    from datetime import datetime
    return f"""(kicad_pcb (version 20221018) (generator "cadquery_framework")
  (general
    (thickness {thickness:.2f})
    (legacy_teardrops no)
  )
  (paper "A4")
  (title_block
    (title "{title}")
    (date "{datetime.now().strftime('%Y-%m-%d')}")
    (rev "1.0")
    (company "Drone Project")
    (comment 1 "Material: FR4, Tg150")
    (comment 2 "Layers: 4  Thickness: {thickness:.1f}mm  Finish: ENIG")
    (comment 3 "Min trace: {DRM_MIN_TRACE_MM}mm  Min space: {DRM_MIN_TRACE_MM}mm  Min drill: {JLCPCB_MIN_DRILL_MM}mm via / {TH_GPIO_DRILL_MM}mm TH")
    (comment 4 "Stackup: F.Cu(sig) / In1.Cu(GND) / In2.Cu(PWR) / B.Cu(sig)")
  )
  (layers
    (0  "F.Cu"          signal    "Front copper - signal routing")
    (1  "In1.Cu"        power     "Inner layer 1 - GND plane")
    (2  "In2.Cu"        power     "Inner layer 2 - PWR plane (+3V3 / +5V / +1V8)")
    (31 "B.Cu"          signal    "Back copper - signal routing")
    (32 "B.Adhes"       user      "B.Adhesive")
    (33 "F.Adhes"       user      "F.Adhesive")
    (34 "B.Paste"       user)
    (35 "F.Paste"       user)
    (36 "B.SilkS"       user      "B.Silkscreen")
    (37 "F.SilkS"       user      "F.Silkscreen")
    (38 "B.Mask"        user      "B.Mask")
    (39 "F.Mask"        user      "F.Mask")
    (40 "Dwgs.User"     user      "User.Drawings")
    (41 "Cmts.User"     user      "User.Comments")
    (42 "Eco1.User"     user      "User.Eco1")
    (43 "Eco2.User"     user      "User.Eco2")
    (44 "Edge.Cuts"     user)
    (45 "Margin"        user)
    (46 "B.CrtYd"       user      "B.Courtyard")
    (47 "F.CrtYd"       user      "F.Courtyard")
    (48 "B.Fab"         user)
    (49 "F.Fab"         user)
  )
  (setup
    (stackup
      (layer "F.SilkS"      (type "Top Silk Screen"))
      (layer "F.Paste"       (type "Top Solder Paste"))
      (layer "F.Mask"        (type "Top Solder Mask")    (thickness {SOLDER_MASK_THICKNESS_MM}))
      (layer "F.Cu"          (type "copper")             (thickness {CU_OUTER_MM}))
      (layer "dielectric 1"  (type "prepreg")            (thickness {PREPREG_THICKNESS_MM}) (material "{PREPREG_MATERIAL}") (epsilon_r {PREPREG_DK}) (loss_tangent {PREPREG_LOSS_TANGENT}))
      (layer "In1.Cu"        (type "copper")             (thickness {CU_INNER_MM}))
      (layer "dielectric 2"  (type "core")               (thickness {CORE_THICKNESS_MM})  (material "{CORE_MATERIAL}") (epsilon_r {CORE_DK}) (loss_tangent {CORE_LOSS_TANGENT}))
      (layer "In2.Cu"        (type "copper")             (thickness {CU_INNER_MM}))
      (layer "dielectric 3"  (type "prepreg")            (thickness {PREPREG_THICKNESS_MM}) (material "{PREPREG_MATERIAL}") (epsilon_r {PREPREG_DK}) (loss_tangent {PREPREG_LOSS_TANGENT}))
      (layer "B.Cu"          (type "copper")             (thickness {CU_OUTER_MM}))
      (layer "B.Mask"        (type "Bottom Solder Mask") (thickness {SOLDER_MASK_THICKNESS_MM}))
      (layer "B.Paste"       (type "Bottom Solder Paste"))
      (layer "B.SilkS"       (type "Bottom Silk Screen"))
    )
    (pad_to_mask_clearance {SOLDER_MASK_EXPANSION_MM})
    (solder_mask_min_width {SOLDER_MASK_MIN_WIDTH_MM})
    (allow_soldermask_bridges_in_footprints no)
    (aux_axis_origin 0 0)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions yes)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (svgprecision 4)
      (excludeedgelayer yes)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (dxfpolygonmode yes)
      (dxfimperialunits yes)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotfptext no)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk yes)
      (outputformat 1)
      (mirror no)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "gerber/")
    )
  )

{nets_block}

{content}
)
"""


def generate_daughter_board_pcb():
    """Generate production-quality .kicad_pcb for the daughter board.

    Coordinate origin: board centre.
    X-axis: parallel to DE10-Nano 68.58mm (width) axis.
    Y-axis: parallel to DE10-Nano 107.95mm (length) axis.

    Board: 72×80mm, 1.6mm FR4, 4-layer (sig/GND/PWR/sig).

    Content:
      Edge.Cuts     — board outline (3mm corner radius) + heatsink/fan cutout
      F.Cu / B.Cu   — all through-hole pads with net assignments
      F.Courtyard   — courtyard outlines for every component
      F.SilkS       — connector labels, pin-1 markers, ref designators, board ID
      F.Fab         — component values
      Dwgs.User     — DE10-Nano board shadow at 1:1 scale (routing reference)
      Net list       — all 72 GPIO signals + power/GND nets declared
    """
    if not _KI_AVAIL:
        raise RuntimeError("cadquery_framework.kicad.primitives not available")

    db_w  = DB_W           # 72.0 mm
    db_l  = DB_L           # 80.0 mm
    db_t  = DB_H           # 1.6 mm
    de10_w = DE10_W        # 68.58 mm
    de10_l = DE10_L        # 107.95 mm
    hole_d = DB_MOUNT_HOLE_D   # 2.7 mm
    inset  = DB_MOUNT_INSET    # 4.0 mm
    hs_w   = _D["de10_nano"]["heatsink_width"]    # 40.0 mm
    hs_l   = _D["de10_nano"]["heatsink_length"]   # 40.0 mm

    # ── Collect all net names to build global net table ───────────────────────
    all_nets = {"": 0}   # net 0 = no-connect / unconnected
    for nets_dict in (_GPIO0_NETS, _GPIO1_NETS):
        for net_name in nets_dict.values():
            if net_name not in all_nets:
                all_nets[net_name] = len(all_nets)
    # Power nets guaranteed present
    for pnet in ("+5V", "+3V3", "+1V8", "GND"):
        if pnet not in all_nets:
            all_nets[pnet] = len(all_nets)

    # Assign GPIO connector net IDs using the global table
    def _gp_net_id(name):
        return all_nets.get(name, 0)

    # ── Board outline (Edge.Cuts) ─────────────────────────────────────────────
    segs = rounded_rect_outline(db_w, db_l, 3.0)
    content = outline_to_sexpr(segs)

    # ── Heatsink / cooling-fan cutout (Edge.Cuts) ─────────────────────────────
    cutout_w = hs_w + 4.0   # 44mm
    cutout_l = hs_l + 4.0   # 44mm
    hs_segs = rounded_rect_outline(cutout_w, cutout_l, 1.5)
    content += "\n" + outline_to_sexpr(hs_segs)

    # ── M2.5 mounting holes — four board corners, inset 4mm ───────────────────
    mh_net = _gp_net_id("GND")
    for hx in [-db_w / 2 + inset, db_w / 2 - inset]:
        for hy in [-db_l / 2 + inset, db_l / 2 - inset]:
            # Use a proper footprint so the hole has a reference
            ref_label = f"MH{1 + int(hx > 0) + 2 * int(hy > 0)}"
            content += f"""
  (footprint "MountingHole:MountingHole_2.7mm_M2.5" (layer "F.Cu") (uuid "{_uid()}")
  (at {hx:.4f} {hy:.4f})
  (descr "M2.5 standoff, GND-tied")
    (fp_text reference "{ref_label}" (at 0 -2.5) (layer "F.SilkS") (uuid "{_uid()}")
      (effects (font (size {SILK_MICRO_SIZE_MM} {SILK_MICRO_SIZE_MM}) (thickness {SILK_MICRO_THICK_MM})))
    )
    (fp_text value "M2.5" (at 0 2.5) (layer "F.Fab") (uuid "{_uid()}")
      (effects (font (size {SILK_FAB_SIZE_MM} {SILK_FAB_SIZE_MM}) (thickness {SILK_FAB_THICK_MM})))
    )
    (fp_circle (center 0 0) (end 2.0 0) (layer "F.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))
    (pad "" thru_hole circle (at 0 0) (size {TH_M25_PAD_MM} {TH_M25_PAD_MM}) (drill {TH_M25_DRILL_MM})
      (layers "*.Cu" "*.Mask")
      (net {mh_net} "GND")
      (uuid "{_uid()}")
    )
  )"""

    # ── GPIO0 (JP1) footprint ─────────────────────────────────────────────────
    jp1_fp = _gpio_footprint(
        _GPIO_LAYOUT["gpio0"],
        global_nets=all_nets,
        pitch=GPIO_PITCH,
        drill_d=TH_GPIO_DRILL_MM, pad_d=TH_GPIO_PAD_MM,
    )
    content += "\n" + jp1_fp

    # ── GPIO1 (JP2) footprint ─────────────────────────────────────────────────
    jp2_fp = _gpio_footprint(
        _GPIO_LAYOUT["gpio1"],
        global_nets=all_nets,
        pitch=GPIO_PITCH,
        drill_d=TH_GPIO_DRILL_MM, pad_d=TH_GPIO_PAD_MM,
    )
    content += "\n" + jp2_fp

    # ── All subsystem components (courtyard + silkscreen + fab) ──────────────
    for comp in _COMPONENTS:
        ref, value, cx, cy, w, h, layer, desc = comp
        content += "\n" + _component_footprint(ref, value, cx, cy, w, h, layer, desc)

    # ── DE10-Nano board shadow (Dwgs.User — routing reference, not fabricated) ─
    de10_segs = rounded_rect_outline(de10_w, de10_l, 1.0)
    content += "\n" + outline_to_sexpr(de10_segs, layer="Dwgs.User", width=0.08)
    content += "\n" + text_sexpr(
        "DE10-Nano PCB shadow (routing reference only — not Edge.Cuts)",
        0, -de10_l / 2 - 5.0,
        "Dwgs.User", SILK_MICRO_SIZE_MM, SILK_MICRO_THICK_MM,
    )

    # ── Board identification silkscreen ───────────────────────────────────────
    content += "\n" + text_sexpr(
        "DE10-NANO FLIGHT CTRL DAUGHTER BOARD",
        0, db_l / 2 - 4.5,
        "F.SilkS", SILK_REF_SIZE_MM, SILK_REF_THICK_MM,
    )
    content += "\n" + text_sexpr(
        f"{db_w:.0f}x{db_l:.0f}mm  FR4  1.6mm  4L  ENIG",
        0, db_l / 2 - 8.5,
        "F.SilkS", SILK_SMALL_SIZE_MM, SILK_SMALL_THICK_MM,
    )
    content += "\n" + text_sexpr(
        "HEATSINK/FAN OPENING",
        0, 0,
        "F.SilkS", SILK_MICRO_SIZE_MM, SILK_MICRO_THICK_MM,
    )
    content += "\n" + text_sexpr(
        "Stackup: F.Cu(sig) / In1(GND) / In2(PWR) / B.Cu(sig)",
        0, db_l / 2 - 12.0,
        "Cmts.User", SILK_MICRO_SIZE_MM, SILK_MICRO_THICK_MM,
    )

    # ── Build net table AFTER all footprints (NC pins may have been added) ─────
    nets_block = "\n".join(
        _net_sexpr(nid, nname) for nname, nid in sorted(all_nets.items(), key=lambda x: x[1])
    )

    return _kicad_pcb_4layer("DE10-Nano Daughter Board v1.0", db_t, nets_block, content)
