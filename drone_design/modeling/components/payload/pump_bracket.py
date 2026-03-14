"""Pump mounting bracket — FR4."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

PUMP_BRACKET_W = _D["pump"]["bracket_width"]
PUMP_BRACKET_H = _D["pump"]["bracket_height"]
PUMP_BRACKET_T = _D["pump"]["bracket_thickness"]


def make_pump_bracket():
    """Pump mounting bracket — FR4."""
    return (
        cq.Workplane("XY")
        .rect(PUMP_BRACKET_W, PUMP_BRACKET_T)
        .extrude(PUMP_BRACKET_H)
    )
