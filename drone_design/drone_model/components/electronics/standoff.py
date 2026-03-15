"""M2.5 hex standoff for board mounting."""

import cadquery as cq

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

import json
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())
DE10_STANDOFF = _D["de10_nano"]["standoff_height"]

CATALOG = {
    "standoff": {
        "material": "Brass, nickel plated",
        "dims": f"M2.5 x {DE10_STANDOFF}mm",
        "mass_g": 2, "qty": 4,
        "supplier": "Generic M2.5 hex standoff",
        "notes": "Female-female hex standoff, separates DE10-Nano from bottom plate",
        "interface": "M2.5 bolt through bottom plate into standoff",
    },
}


def make_standoff(h):
    """M2.5 hex standoff."""
    shape = cq.Workplane("XY").polygon(6, 5).extrude(h)

    anchors = {}
    if Anchor is not None:
        anchors["base"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Standoff base bolts to plate")
        anchors["top"] = Anchor(point=(0, 0, h), normal=(0, 0, 1), label="Standoff top supports board")

    return shape, anchors
