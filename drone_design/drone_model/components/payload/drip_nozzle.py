"""Adjustable drip irrigation emitter with boom-tip mounting flange.

Geometry: mounting flange with M2 bolt holes (attaches to boom end),
barbed inlet fitting on top for tubing, cylindrical body transitioning
to a conical emitter tip pointing downward.
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())
_N = _D["drip_nozzle"]

BODY_D       = _N["body_diameter"]
BODY_H       = _N["body_height"]
CONE_TOP_D   = _N["cone_top_diameter"]
CONE_TIP_D   = _N["cone_tip_diameter"]
CONE_H       = _N["cone_height"]
BARB_OD      = _N["barb_od"]
BARB_ID      = _N["barb_id"]
BARB_L       = _N["barb_length"]
FLANGE_W     = _N["flange_width"]
FLANGE_DEPTH = _N["flange_depth"]
FLANGE_T     = _N["flange_thickness"]
FLANGE_HOLE_D = _N["flange_hole_diameter"]
FLANGE_HOLE_S = _N["flange_hole_spacing"]

CATALOG = {
    "drip_nozzle": {
        "material": "Brass + stainless steel",
        "dims": "\u00d86 x 15mm",
        "mass_g": 5, "qty": 1,
        "supplier": "Generic drip irrigation nozzle",
        "notes": "Adjustable drip nozzle, 0-60ml/min",
        "interface": "Barb press-fit into silicone tubing",
    },
}


def make_drip_nozzle():
    """Drip emitter with mounting flange and barbed inlet.

    Oriented with flange at Z=0 (mounts to boom underside),
    barb inlet extending upward (+Z), body and cone extending downward (-Z).
    """

    # --- Mounting flange (attaches to boom tip) ---
    flange = (
        cq.Workplane("XY")
        .rect(FLANGE_W, FLANGE_DEPTH)
        .extrude(FLANGE_T)
    )
    # 2x M2 mounting holes
    for sx in [-1, 1]:
        hole = (
            cq.Workplane("XY")
            .center(sx * FLANGE_HOLE_S / 2, 0)
            .circle(FLANGE_HOLE_D / 2)
            .extrude(FLANGE_T)
        )
        flange = flange.cut(hole)

    # --- Cylindrical body (below flange, extending in -Z) ---
    body = (
        cq.Workplane("XY")
        .circle(BODY_D / 2)
        .extrude(-BODY_H)
    )
    nozzle = flange.union(body)

    # --- Conical emitter tip (-Z, below body) ---
    try:
        cone = (
            cq.Workplane("XY")
            .workplane(offset=-BODY_H)
            .circle(CONE_TOP_D / 2)
            .workplane(offset=-CONE_H)
            .circle(CONE_TIP_D / 2)
            .loft()
        )
        nozzle = nozzle.union(cone)
    except Exception:
        # Fallback: simple cylinder if loft fails
        cone = (
            cq.Workplane("XY")
            .circle(CONE_TOP_D / 2)
            .extrude(-BODY_H - CONE_H)
        )
        nozzle = nozzle.union(cone)

    # --- Barbed inlet fitting (above flange, +Z) ---
    inlet = (
        cq.Workplane("XY")
        .workplane(offset=FLANGE_T)
        .circle(BARB_OD / 2)
        .extrude(BARB_L)
    )
    # Hollow bore through entire nozzle
    bore = (
        cq.Workplane("XY")
        .circle(BARB_ID / 2)
        .extrude(FLANGE_T + BARB_L)
    )
    bore_down = (
        cq.Workplane("XY")
        .circle(BARB_ID / 2)
        .extrude(-BODY_H - CONE_H)
    )
    # Barb ring for tubing grip
    barb_ring = (
        cq.Workplane("XY")
        .workplane(offset=FLANGE_T + BARB_L * 0.5)
        .circle((BARB_OD + 1.5) / 2)
        .extrude(2)
    )

    nozzle = nozzle.union(inlet).union(barb_ring)
    nozzle = nozzle.cut(bore).cut(bore_down)

    anchors = {}
    if Anchor is not None:
        # Barb inlet tip (+Z above flange) — tubing connection
        anchors["barb_inlet"] = Anchor(
            point=(0, 0, FLANGE_T + BARB_L),
            normal=(0, 0, 1),
            label="Barbed inlet for tubing connection",
        )
        # Flange top face (Z=FLANGE_T) — bolts to boom tip underside
        anchors["flange_mount"] = Anchor(
            point=(0, 0, FLANGE_T),
            normal=(0, 0, 1),
            label="Flange face for boom tip mounting",
        )

    return nozzle, anchors
