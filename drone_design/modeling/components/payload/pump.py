"""Kamoer NKP-DC-S06B peristaltic pump with inlet/outlet tube fittings."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

PUMP_L       = _D["pump"]["total_length"]
PUMP_MOTOR_D = _D["pump"]["motor_section_diameter"]
PUMP_HEAD_D  = _D["pump"]["pump_head_diameter"]
PUMP_TUBE_D  = _D["pump"]["tube_fitting_diameter"]
PUMP_TUBE_L  = _D["pump"]["tube_fitting_length"]


def make_pump():
    """Kamoer NKP-DC-S06B peristaltic pump with inlet/outlet tube fittings."""
    motor_len = PUMP_L * 0.6
    head_len = PUMP_L * 0.4

    motor_section = (
        cq.Workplane("YZ")
        .circle(PUMP_MOTOR_D / 2)
        .extrude(motor_len)
        .translate((-PUMP_L / 2, 0, 0))
    )

    head = (
        cq.Workplane("YZ")
        .circle(PUMP_HEAD_D / 2)
        .extrude(head_len)
        .translate((-PUMP_L / 2 + motor_len, 0, 0))
    )

    pump = motor_section.union(head)

    head_center_x = -PUMP_L / 2 + motor_len + head_len / 2
    fitting_spacing = PUMP_HEAD_D * 0.35
    head_top_z = PUMP_HEAD_D / 2

    for dx in [-fitting_spacing, fitting_spacing]:
        fitting = (
            cq.Workplane("XY")
            .center(head_center_x + dx, 0)
            .circle(PUMP_TUBE_D / 2)
            .extrude(head_top_z + PUMP_TUBE_L)
        )
        pump = pump.union(fitting)

    return pump
