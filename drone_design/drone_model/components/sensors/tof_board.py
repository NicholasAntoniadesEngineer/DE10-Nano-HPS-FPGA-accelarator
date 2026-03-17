"""VL53L1X Pololu carrier #3415 — Time-of-Flight rangefinder board."""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

TOF_W        = _D["tof_sensor"]["board_width"]
TOF_L        = _D["tof_sensor"]["board_length"]
TOF_H        = _D["tof_sensor"]["board_height"]
TOF_SENSOR_H = _D["tof_sensor"]["sensor_module_height"]
TOF_HOLE_D   = _D["tof_sensor"]["mounting_hole_diameter"]
TOF_HOLE_SX  = _D["tof_sensor"]["mounting_hole_spacing_x"]
TOF_HOLE_SY  = _D["tof_sensor"]["mounting_hole_spacing_y"]
TOF_PIN_W    = _D["tof_sensor"]["pin_header_width"]
TOF_PIN_L    = _D["tof_sensor"]["pin_header_length"]
TOF_PIN_H    = _D["tof_sensor"]["pin_header_height"]
PCB_EDGE_CHAMFER = _D["assembly"]["pcb_edge_chamfer"]

CATALOG = {
    "tof_sensor": {
        "material": "FR4 PCB + VL53L1X VCSEL module",
        "dims": "13 x 18 x 2mm board + 2.5mm sensor",
        "mass_g": 1.5, "qty": 6,
        "supplier": "Pololu #3415 (VL53L1X carrier)",
        "notes": "Time-of-Flight laser ranging, 4m max, 50Hz, I2C",
        "interface": "I2C via TCA9548A mux on daughter board",
    },
}


def make_tof_board():
    """VL53L1X Pololu carrier #3415 — PCB with mounting holes, sensor, and pin header."""
    board_chamfer = min(PCB_EDGE_CHAMFER, TOF_H * 0.45)
    board = (
        cq.Workplane("XY")
        .rect(TOF_W, TOF_L)
        .extrude(TOF_H)
        .edges("|Z")
        .chamfer(board_chamfer)
    )

    # Mounting holes — two at opposite corners (Pololu #3415 layout)
    for sx, sy in [(-1, -1), (1, 1)]:
        hole = (
            cq.Workplane("XY")
            .center(sx * TOF_HOLE_SX / 2, sy * TOF_HOLE_SY / 2)
            .circle(TOF_HOLE_D / 2)
            .extrude(TOF_H)
        )
        board = board.cut(hole)

    component_chamfer = min(0.6, PCB_EDGE_CHAMFER)
    # VL53L1X sensor module (4.4 x 2.4 mm optical aperture), offset toward +Y end
    sensor = (
        cq.Workplane("XY")
        .center(0, TOF_L / 2 - 4.0)
        .rect(4.4, 2.4)
        .extrude(TOF_H + TOF_SENSOR_H)
        .edges("|Z")
        .chamfer(component_chamfer)
    )

    # Pin header strip on bottom (-Z), along -Y edge of board
    pin_header = (
        cq.Workplane("XY")
        .center(0, -(TOF_L / 2 - TOF_PIN_L / 2))
        .rect(TOF_PIN_W, TOF_PIN_L)
        .extrude(-TOF_PIN_H)
        .edges("|Z")
        .chamfer(component_chamfer)
    )

    shape = board.union(sensor).union(pin_header)

    anchors = {}
    if Anchor is not None:
        # Bottom of PCB (Z=0), normal pointing down — for bracket attachment
        anchors["mount_face"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Bottom PCB face for bracket mounting",
        )
        # Top of sensor module, normal pointing up — sensing direction
        anchors["sensor_face"] = Anchor(
            point=(0, TOF_L / 2 - 4.0, TOF_H + TOF_SENSOR_H),
            normal=(0, 0, 1),
            label="Sensor aperture face (VL53L1X optical axis)",
        )

    return shape, anchors
