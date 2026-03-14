"""L-bracket pump cradle — 1.6mm FR4, bolts to bottom plate and holds pump.

Geometry: horizontal base plate with M3 frame mounting holes,
vertical back wall that the pump's mounting ears bolt to,
and triangular gussets for rigidity.
"""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())
_B = _D["pump_bracket"]

BASE_W       = _B["base_width"]
BASE_DEPTH   = _B["base_depth"]
BACK_H       = _B["back_height"]
T            = _B["thickness"]
GUSSET       = _B["gusset_size"]
FRAME_HOLE_D = _B["frame_hole_diameter"]
FRAME_INSET  = _B["frame_hole_inset"]
PUMP_HOLE_D  = _B["pump_hole_diameter"]
PUMP_HOLE_SX = _B["pump_hole_spacing_x"]


def make_pump_bracket():
    """L-bracket pump cradle with frame mounting holes and pump mounting holes."""

    # --- Horizontal base plate (bolts to underside of bottom frame plate) ---
    base = (
        cq.Workplane("XY")
        .rect(BASE_W, BASE_DEPTH)
        .extrude(T)
    )
    # 4x M3 frame mounting holes near corners
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (BASE_W / 2 - FRAME_INSET)
            hy = sy * (BASE_DEPTH / 2 - FRAME_INSET)
            hole = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(FRAME_HOLE_D / 2)
                .extrude(T)
            )
            base = base.cut(hole)

    # --- Vertical back wall (pump mounts against this) ---
    back = (
        cq.Workplane("XZ")
        .center(0, T + BACK_H / 2)
        .rect(BASE_W, BACK_H)
        .extrude(T)
        .translate((0, -BASE_DEPTH / 2, 0))
    )
    # 2x M3 pump mounting holes (match pump ear spacing)
    for sx in [-1, 1]:
        hx = sx * (PUMP_HOLE_SX / 2)
        hz = T + BACK_H / 2
        hole = (
            cq.Workplane("XZ")
            .center(hx, hz)
            .circle(PUMP_HOLE_D / 2)
            .extrude(T)
            .translate((0, -BASE_DEPTH / 2, 0))
        )
        back = back.cut(hole)

    bracket = base.union(back)

    # --- Triangular gussets (left and right) for rigidity ---
    for sx in [-1, 1]:
        gx = sx * (BASE_W / 2 - T / 2)
        gusset = (
            cq.Workplane("YZ")
            .moveTo(-BASE_DEPTH / 2, T)
            .lineTo(-BASE_DEPTH / 2, T + GUSSET)
            .lineTo(-BASE_DEPTH / 2 + GUSSET, T)
            .close()
            .extrude(T)
            .translate((gx - T / 2, 0, 0))
        )
        bracket = bracket.union(gusset)

    return bracket
