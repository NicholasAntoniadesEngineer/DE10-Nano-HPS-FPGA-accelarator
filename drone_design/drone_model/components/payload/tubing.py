"""Silicone tubing segments for water path: reservoir → pump → frame edge → boom → drip nozzle.

Dimensions (OD/ID) come from pump config in dimensions.json so tubing matches pump
tube stubs and nozzle barb. Each segment is a hollow cylinder along local +Z;
assembly places segments between anchor points (reservoir outlet, pump inlet/outlet,
nozzle barb) with computed rotation so segments connect end-to-end.
"""

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
    """Silicone tubing segment: hollow cylinder along +Z from 0 to length.

    OD/ID from pump tube config. Start at (0,0,0), end at (0,0,length); assembly
    positions and orients each segment so start/end align with part anchors.
    """
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
            label="Start (connects to reservoir barb, pump stub, or previous segment)",
        )
        anchors["end"] = Anchor(
            point=(0, 0, length),
            normal=(0, 0, 1),
            label="End (connects to pump stub, waypoint, or nozzle barb)",
        )

    return shape, anchors
