"""Tattu 4S 2200mAh 45C LiPo battery with XT60 connector."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

BATT_W        = _D["battery"]["width"]
BATT_L        = _D["battery"]["length"]
BATT_H        = _D["battery"]["height"]
BATT_XT60_W   = _D["battery"]["xt60_width"]
BATT_XT60_H   = _D["battery"]["xt60_height"]
BATT_XT60_D   = _D["battery"]["xt60_depth"]
BATT_CORNER_R = _D["battery"]["corner_radius"]


def make_battery():
    """Tattu 4S 2200mAh 45C LiPo with XT60 connector bump."""
    body = (
        cq.Workplane("XY")
        .rect(BATT_W, BATT_L)
        .extrude(BATT_H)
        .edges("|Z").fillet(BATT_CORNER_R)
        .edges(">Z").fillet(min(BATT_CORNER_R * 0.5, 1.5))
    )
    xt60_z = (BATT_H - BATT_XT60_H) / 2
    xt60 = (
        cq.Workplane("XY")
        .transformed(offset=(0, BATT_L / 2 + BATT_XT60_D / 2, xt60_z))
        .rect(BATT_XT60_W, BATT_XT60_D)
        .extrude(BATT_XT60_H)
    )
    return body.union(xt60)
