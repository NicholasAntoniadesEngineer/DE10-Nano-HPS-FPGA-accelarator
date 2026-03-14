"""L-shaped landing gear leg with capsule lightening holes."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

LEG_WIDTH    = _D["landing_gear"]["leg_width"]
LEG_HEIGHT   = _D["landing_gear"]["leg_height"]
LEG_THICK    = _D["landing_gear"]["leg_thickness"]
FOOT_LENGTH  = _D["landing_gear"]["foot_length"]
FOOT_THICK   = _D["landing_gear"]["foot_thickness"]
LEG_HOLE_W   = _D["landing_gear"]["lightening_hole_width"]
LEG_HOLE_H   = _D["landing_gear"]["lightening_hole_height"]
LEG_HOLE_R   = _D["landing_gear"]["lightening_hole_end_radius"]
LEG_HOLE_N   = _D["landing_gear"]["lightening_hole_count"]


def _capsule_2d(width, height, end_radius):
    """Create a 2D capsule (stadium) shape for lightening holes."""
    straight = height - 2 * end_radius
    if straight < 0:
        straight = 0
        end_radius = height / 2
    return (
        cq.Workplane("XZ")
        .moveTo(-width / 2, -straight / 2)
        .lineTo(-width / 2, straight / 2)
        .threePointArc((0, straight / 2 + end_radius), (width / 2, straight / 2))
        .lineTo(width / 2, -straight / 2)
        .threePointArc((0, -straight / 2 - end_radius), (-width / 2, -straight / 2))
        .close()
    )


def make_landing_leg():
    """Create an L-shaped landing gear leg with capsule lightening holes."""
    vertical = (
        cq.Workplane("XZ")
        .rect(LEG_WIDTH, LEG_HEIGHT)
        .extrude(LEG_THICK)
        .translate((0, 0, FOOT_THICK + LEG_HEIGHT / 2))
    )

    foot = (
        cq.Workplane("XY")
        .rect(LEG_WIDTH, FOOT_LENGTH)
        .extrude(FOOT_THICK)
        .translate((0, FOOT_LENGTH / 2 - LEG_THICK / 2, FOOT_THICK / 2))
    )

    leg = vertical.union(foot)

    usable_h = LEG_HEIGHT - 15
    spacing = usable_h / (LEG_HOLE_N + 1)
    for i in range(LEG_HOLE_N):
        zh = FOOT_THICK + 10 + spacing * (i + 1)
        try:
            capsule = _capsule_2d(LEG_HOLE_W, LEG_HOLE_H, LEG_HOLE_R)
            hole = capsule.center(0, zh).extrude(LEG_THICK)
            leg = leg.cut(hole)
        except Exception:
            hole = (
                cq.Workplane("XZ")
                .center(0, zh)
                .rect(LEG_HOLE_W, LEG_HOLE_H)
                .extrude(LEG_THICK)
            )
            leg = leg.cut(hole)

    return leg
