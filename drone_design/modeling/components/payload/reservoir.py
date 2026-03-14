"""TPU collapsible 300ml water reservoir."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

RES_W = _D["reservoir"]["width"]
RES_L = _D["reservoir"]["length"]
RES_H = _D["reservoir"]["height"]


def make_reservoir():
    """TPU collapsible 300ml water reservoir."""
    return (
        cq.Workplane("XY")
        .rect(RES_W, RES_L)
        .extrude(RES_H)
        .edges().fillet(5)
    )
