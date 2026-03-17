"""Stacked FR4 PCB motor riser — raises motor above arm to clear top plate.

Construction: N layers of circular FR4 PCB plates stacked with through-bolts.
Each layer is a circular disc matching the motor base diameter with:
- Central shaft clearance hole
- 4x M2 through-bolt holes on the motor bolt circle (16mm)

The number of layers is computed from the desired height / FR4 thickness.
Through-bolts pass from arm tip, through all riser layers, into motor base.

Origin: center of base disc at (0, 0, 0). +Z = up toward motor.
"""

import json
import math
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())
_R = _D["motor_riser"]
_M = _D["motor"]

RISER_H        = _R["height"]
LAYER_THICK    = _R["layer_thickness"]
DISC_DIAMETER  = _M["base_plate_diameter"]       # match motor base
BOLT_CIRCLE_D  = _M["mount_bolt_pattern"][0]     # 16mm bolt circle
SHAFT_CLEAR_D  = 3.5                             # shaft clearance hole
M2_CLEAR_D     = 2.4                             # M2 bolt clearance

N_LAYERS       = max(1, round(RISER_H / LAYER_THICK))
ACTUAL_H       = N_LAYERS * LAYER_THICK

CATALOG = {
    "motor_riser": {
        "material": "FR4 Glass Epoxy",
        "thickness": f"{LAYER_THICK}mm x {N_LAYERS} layers",
        "dims": f"Ø{DISC_DIAMETER}mm x {ACTUAL_H:.1f}mm ({N_LAYERS} layers)",
        "mass_g": round(2.0 * N_LAYERS),
        "qty": 4,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": f"Stacked FR4 disc riser, {N_LAYERS} layers, through-bolted",
        "interface": "4x M2 through-bolts: arm tip (bottom) → riser → motor base (top)",
    },
}


def make_motor_riser():
    """Stacked FR4 disc riser — circular plates with bolt holes."""
    disc_r = DISC_DIAMETER / 2
    bolt_r = BOLT_CIRCLE_D / 2
    shaft_r = SHAFT_CLEAR_D / 2
    m2_r = M2_CLEAR_D / 2

    # Build full stack as a single extrusion (visually solid block)
    body = (
        cq.Workplane("XY")
        .circle(disc_r)
        .extrude(ACTUAL_H)
    )

    # Score lines between layers (shallow grooves to show stacking)
    groove_depth = 0.3
    for i in range(1, N_LAYERS):
        z = i * LAYER_THICK
        groove = (
            cq.Workplane("XY")
            .workplane(offset=z - groove_depth / 2)
            .circle(disc_r + 0.1)
            .circle(disc_r - 1.5)
            .extrude(groove_depth)
        )
        body = body.cut(groove)

    # Central shaft clearance hole
    shaft_hole = (
        cq.Workplane("XY")
        .circle(shaft_r)
        .extrude(ACTUAL_H)
    )
    body = body.cut(shaft_hole)

    # 4x M2 through-bolt holes on motor bolt circle (0, 90, 180, 270 deg)
    for angle_deg in [0, 90, 180, 270]:
        angle_rad = math.radians(angle_deg)
        hx = bolt_r * math.cos(angle_rad)
        hy = bolt_r * math.sin(angle_rad)
        hole = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(m2_r)
            .extrude(ACTUAL_H)
        )
        body = body.cut(hole)

    anchors = {}
    if Anchor is not None:
        anchors["base_mount"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Riser base — mates to arm motor_tip",
        )
        anchors["motor_mount"] = Anchor(
            point=(0, 0, ACTUAL_H),
            normal=(0, 0, 1),
            label="Riser top — motor base_mount mates here",
        )

    return body, anchors
