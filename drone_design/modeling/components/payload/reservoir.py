"""TPU collapsible 300ml water reservoir with outlet barb fitting."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())
_R = _D["reservoir"]

RES_W      = _R["width"]
RES_L      = _R["length"]
RES_H      = _R["height"]
FILLET_R   = _R["fillet_radius"]
BARB_OD    = _R["outlet_barb_od"]
BARB_L     = _R["outlet_barb_length"]


def make_reservoir():
    """TPU collapsible 300ml water reservoir with outlet barb on +Y face."""
    body = (
        cq.Workplane("XY")
        .rect(RES_W, RES_L)
        .extrude(RES_H)
        .edges().fillet(FILLET_R)
    )

    # Outlet barb fitting — protruding from +Y face at mid-height
    barb = (
        cq.Workplane("XY")
        .center(0, RES_L / 2 + BARB_L / 2)
        .circle(BARB_OD / 2)
        .extrude(RES_H / 2 + BARB_OD)
    )
    # Position barb at mid-height on +Y face
    barb = (
        cq.Workplane("YZ")
        .center(RES_L / 2 + BARB_L / 2, RES_H / 2)
        .circle(BARB_OD / 2)
        .extrude(BARB_L)
        .translate((0, 0, 0))
    )
    # Simpler approach: horizontal barb on +Y face
    barb = (
        cq.Workplane("XZ")
        .center(0, RES_H / 2)
        .circle(BARB_OD / 2)
        .extrude(BARB_L)
        .translate((0, RES_L / 2, 0))
    )

    return body.union(barb)
