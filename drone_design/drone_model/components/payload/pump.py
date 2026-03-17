"""Takasago RP-Q1 ring-drive peristaltic pump — 3V DC, 0.2-3.0 ml/min, 11g.

Geometry: rectangular body (31.5 x 11.9 x 13.9 mm) with slightly rounded
edges. Two silicone tubes (2.5mm OD) exit from the top face near the pump
head end (front), spaced 4.5mm apart. Motor wires exit from the rear face.
No mounting holes — uses external clip bracket.

Origin: body center at (0, 0, body_height/2). +Y = front (pump head end).
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())
_P = _D["pump"]

BODY_L   = _P["body_length"]
BODY_W   = _P["body_width"]
BODY_H   = _P["body_height"]
CORNER_R = _P["corner_radius"]
TUBE_OD  = _P["tube_od"]
TUBE_LEN = _P["tube_exit_length"]
TUBE_SP  = _P["tube_spacing"]
TUBE_INSET = _P["tube_exit_inset_from_front"]
WIRE_D   = _P["wire_diameter"]
WIRE_LEN = _P["wire_exit_length"]

CATALOG = {
    "pump": {
        "material": "POM housing + DC motor + silicone tubing",
        "dims": "64 x 38 x 30mm",
        "mass_g": 85, "qty": 1,
        "supplier": "Takasago RP-Q1",
        "notes": "3V DC peristaltic pump, 0.2-3.0 ml/min, 11g, ring-drive",
        "interface": "Tubing from reservoir; outlet to drip nozzle",
    },
}


def make_pump():
    """Takasago RP-Q1 — rectangular body with tube exits and wire stub."""

    # Main body — rounded rectangle
    body = (
        cq.Workplane("XY")
        .rect(BODY_W, BODY_L)
        .extrude(BODY_H)
        .edges("|Z")
        .fillet(CORNER_R)
    )

    # Two silicone tubes exiting from top face near front (pump head end)
    tube_y = BODY_L / 2 - TUBE_INSET
    for dx in [-TUBE_SP / 2, TUBE_SP / 2]:
        tube = (
            cq.Workplane("XY")
            .center(dx, tube_y)
            .circle(TUBE_OD / 2)
            .extrude(TUBE_LEN)
            .translate((0, 0, BODY_H))
        )
        body = body.union(tube)

    # Wire exit stubs from rear face (-Y)
    for dx in [-1.5, 1.5]:
        wire = (
            cq.Workplane("XZ")
            .center(dx, BODY_H / 2)
            .circle(WIRE_D / 2)
            .extrude(WIRE_LEN)
            .translate((0, -BODY_L / 2, 0))
        )
        body = body.union(wire)

    shape = body

    tube_y = BODY_L / 2 - TUBE_INSET
    anchors = {}
    if Anchor is not None:
        # Inlet tube tip (left tube, top face) — tube entry point
        anchors["inlet_tube"] = Anchor(
            point=(-TUBE_SP / 2, tube_y, BODY_H + TUBE_LEN),
            normal=(0, 0, 1),
            label="Inlet tube connection point",
        )
        # Outlet tube tip (right tube, top face) — tube exit point
        anchors["outlet_tube"] = Anchor(
            point=(TUBE_SP / 2, tube_y, BODY_H + TUBE_LEN),
            normal=(0, 0, 1),
            label="Outlet tube connection point",
        )
        # Base of pump body (Z=0) — bottom face
        anchors["base"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Pump base bottom face",
        )
        # Tube face (Z=BODY_H+TUBE_LEN) — top face including tube stubs
        # Used to mount pump so tubes point downward (away from plate)
        anchors["tube_face"] = Anchor(
            point=(0, 0, BODY_H + TUBE_LEN),
            normal=(0, 0, 1),
            label="Pump tube face — nearest to plate when underslung",
        )

    return shape, anchors
