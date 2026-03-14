"""VL53L1X Pololu carrier #3415 — Time-of-Flight rangefinder board."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

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


def make_tof_board():
    """VL53L1X Pololu carrier #3415 — PCB with mounting holes, sensor, and pin header."""
    board = cq.Workplane("XY").rect(TOF_W, TOF_L).extrude(TOF_H)

    # Mounting holes — two at opposite corners (Pololu #3415 layout)
    for sx, sy in [(-1, -1), (1, 1)]:
        hole = (
            cq.Workplane("XY")
            .center(sx * TOF_HOLE_SX / 2, sy * TOF_HOLE_SY / 2)
            .circle(TOF_HOLE_D / 2)
            .extrude(TOF_H)
        )
        board = board.cut(hole)

    # VL53L1X sensor module (4.4 x 2.4 mm optical aperture), offset toward +Y end
    sensor = (
        cq.Workplane("XY")
        .center(0, TOF_L / 2 - 4.0)
        .rect(4.4, 2.4)
        .extrude(TOF_H + TOF_SENSOR_H)
    )

    # Pin header strip on bottom (-Z), along -Y edge of board
    pin_header = (
        cq.Workplane("XY")
        .center(0, -(TOF_L / 2 - TOF_PIN_L / 2))
        .rect(TOF_PIN_W, TOF_PIN_L)
        .extrude(-TOF_PIN_H)
    )

    return board.union(sensor).union(pin_header)
