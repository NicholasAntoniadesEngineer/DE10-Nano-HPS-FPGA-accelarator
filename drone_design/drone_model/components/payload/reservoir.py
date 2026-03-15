"""TPU collapsible water reservoir with outlet barb fitting.

Capacity determined by width x length x height from dimensions.json.
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())
_R = _D["reservoir"]

RES_W      = _R["width"]
RES_L      = _R["length"]
RES_H      = _R["height"]
FILLET_R   = _R["fillet_radius"]
BARB_OD    = _R["outlet_barb_od"]
BARB_L     = _R["outlet_barb_length"]

CATALOG = {
    "reservoir": {
        "material": "TPU (thermoplastic polyurethane)",
        "dims": "50 x 80 x 40mm (300ml capacity)",
        "mass_g": 25, "qty": 1,
        "supplier": "Custom bladder",
        "notes": "Collapsible water reservoir, gravity-fed to pump",
        "interface": "Silicone tubing to pump inlet",
    },
}


def make_reservoir():
    """TPU collapsible water reservoir with outlet barb on +Y face at mid-height."""
    body = (
        cq.Workplane("XY")
        .rect(RES_W, RES_L)
        .extrude(RES_H)
        .edges().fillet(FILLET_R)
    )

    barb = (
        cq.Workplane("XZ")
        .center(0, RES_H / 2)
        .circle(BARB_OD / 2)
        .extrude(BARB_L)
        .translate((0, RES_L / 2, 0))
    )

    shape = body.union(barb)

    anchors = {}
    if Anchor is not None:
        # Outlet barb tip on +Y face at mid-height
        anchors["outlet"] = Anchor(
            point=(0, RES_L / 2 + BARB_L, RES_H / 2),
            normal=(0, 1, 0),
            label="Barb fitting outlet for tubing connection",
        )
        # Bottom face rests on frame
        anchors["bottom_face"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Bottom face resting on frame",
        )

    return shape, anchors
