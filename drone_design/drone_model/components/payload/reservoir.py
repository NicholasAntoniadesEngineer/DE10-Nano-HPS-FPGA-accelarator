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
        "material": "TPU (thermoplastic polyurethane), 0.3mm wall",
        "dims": f"{RES_W} x {RES_L} x {RES_H}mm ({int(RES_W*RES_L*RES_H/1000)}ml nominal)",
        "mass_g": 15, "qty": 1,
        "supplier": "Custom TPU bladder (3D printed or heat-welded)",
        "notes": "Collapsible water reservoir with screw-cap fill port and strap retention grooves. "
                 "Gravity-fed to pump via 6mm OD barb fitting on +Y face.",
        "interface": "6mm barb → silicone tubing → pump inlet; velcro straps through bottom plate slots",
    },
}


def make_reservoir():
    """TPU collapsible water reservoir with outlet barb, fill port, and strap channels.

    Features:
    - Main body with filleted edges (soft TPU bag shape)
    - Outlet barb on +Y face at mid-height (connects to pump via silicone tubing)
    - Fill port on top face (-X side) — screw-cap opening for refilling
    - Two strap channels molded into the body (for velcro/rubber strap retention)
    """
    body = (
        cq.Workplane("XY")
        .rect(RES_W, RES_L)
        .extrude(RES_H)
        .edges().fillet(FILLET_R)
    )

    # Outlet barb on +Y face at mid-height
    # XZ workplane normal is -Y, so extrude goes -Y. We translate so the barb
    # protrudes OUTSIDE the body (+Y face at Y=RES_L/2).
    barb = (
        cq.Workplane("XZ")
        .center(0, RES_H / 2)
        .circle(BARB_OD / 2)
        .extrude(BARB_L)
        .translate((0, RES_L / 2 + BARB_L, 0))
    )

    # Fill port on top face (8mm diameter cap, 5mm tall, offset to -X side)
    fill_port_d = 8.0
    fill_port_h = 5.0
    fill_port = (
        cq.Workplane("XY")
        .center(-(RES_W / 2 - 8), 0)
        .circle(fill_port_d / 2)
        .extrude(fill_port_h)
        .translate((0, 0, RES_H))
    )

    # Strap retention channels — two shallow grooves around body for straps
    # Each channel is a 3mm wide, 1.5mm deep groove cut around X-Z cross-section
    strap_w = 3.0
    strap_depth = 1.5
    strap_positions = [-RES_L / 4, RES_L / 4]
    shape = body.union(barb).union(fill_port)
    for sy in strap_positions:
        channel = (
            cq.Workplane("XY")
            .center(0, sy)
            .rect(RES_W + 2, strap_w)
            .extrude(RES_H + 2)
        )
        inner = (
            cq.Workplane("XY")
            .center(0, sy)
            .rect(RES_W + 2 - 2 * strap_depth, strap_w)
            .extrude(RES_H + 2 - 2 * strap_depth)
            .translate((0, 0, strap_depth))
        )
        groove = channel.cut(inner)
        shape = shape.cut(groove)

    anchors = {}
    if Anchor is not None:
        # Outlet barb tip on +Y face at mid-height
        anchors["outlet"] = Anchor(
            point=(0, RES_L / 2 + BARB_L, RES_H / 2),
            normal=(0, 1, 0),
            label="Barb fitting outlet — silicone tubing to pump inlet",
        )
        # Bottom face — sits on frame or strap cradle
        anchors["bottom_face"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Bottom face — outermost surface when underslung",
        )
        # Top face — fill port access
        anchors["top_face"] = Anchor(
            point=(0, 0, RES_H),
            normal=(0, 0, 1),
            label="Top face — fill port access",
        )
        # Strap groove positions (for routing retention straps through bottom plate)
        for i, sy in enumerate(strap_positions, 1):
            anchors[f"strap_groove_{i}"] = Anchor(
                point=(0, sy, 0),
                normal=(0, 0, -1),
                label=f"Strap groove {i} at Y={sy:.0f}mm — velcro/rubber strap",
            )

    return shape, anchors
