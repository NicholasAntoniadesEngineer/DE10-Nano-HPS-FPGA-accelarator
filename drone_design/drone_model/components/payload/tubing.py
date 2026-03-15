"""Silicone tubing segment — dimensions from pump config (tube_od/id)."""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

TUBE_OD = _D["pump"]["tube_od"]
TUBE_ID = _D["pump"]["tube_id"]


def make_tubing_segment(length):
    """Silicone tubing segment with OD/ID from pump tube config."""
    shape = (
        cq.Workplane("XY")
        .circle(TUBE_OD / 2)
        .circle(TUBE_ID / 2)
        .extrude(length)
    )

    anchors = {}
    if Anchor is not None:
        anchors["start"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Tubing start connection endpoint",
        )
        anchors["end"] = Anchor(
            point=(0, 0, length),
            normal=(0, 0, 1),
            label="Tubing end connection endpoint",
        )

    return shape, anchors
