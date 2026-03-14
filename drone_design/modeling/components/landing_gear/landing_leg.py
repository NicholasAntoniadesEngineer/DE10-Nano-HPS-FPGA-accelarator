"""L-shaped landing gear leg with horizontal mounting tab, lightening holes, and header holes.

The leg has three sections:
  1. Foot — horizontal at bottom, extends outward (+Y) for ground contact
  2. Vertical — upright section with capsule lightening holes for weight reduction
  3. Mounting tab — horizontal at top, extends inward (-Y) to overlap under the
     bottom plate. Pin header holes pass vertically (Z-axis) through both the tab
     and the plate for a soldered structural/electrical connection.
"""

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
TAB_DEPTH    = _D["landing_gear"]["mounting_tab_depth"]
TAB_THICK    = _D["landing_gear"]["mounting_tab_thickness"]

# Pin header connection specs
HEADER_PITCH    = _D["connections"]["header_pitch"]
HEADER_HOLE_D   = _D["connections"]["header_hole_diameter"]
LEG_HEADER_PINS = _D["connections"]["leg_header_pins"]


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
    """Create an L-shaped landing gear leg with mounting tab and lightening holes.

    Coordinate system (leg local frame):
      X = tangential (along plate edge)
      Y = radial (+Y outward from frame, -Y inward toward center)
      Z = vertical (0 = ground)

    The mounting tab at the top extends in -Y (inward), sitting flush under
    the bottom plate. Pin headers pass vertically through the tab and plate.
    """
    # Vertical section — stands at plate edge
    vertical = (
        cq.Workplane("XZ")
        .rect(LEG_WIDTH, LEG_HEIGHT)
        .extrude(LEG_THICK)
        .translate((0, 0, FOOT_THICK + LEG_HEIGHT / 2))
    )

    # Foot — extends outward (+Y) at ground level
    foot = (
        cq.Workplane("XY")
        .rect(LEG_WIDTH, FOOT_LENGTH)
        .extrude(FOOT_THICK)
        .translate((0, FOOT_LENGTH / 2 - LEG_THICK / 2, FOOT_THICK / 2))
    )

    # Mounting tab — extends inward (-Y) at the top of the vertical section
    # Tab top surface aligns with bottom plate bottom surface
    tab_top_z = FOOT_THICK + LEG_HEIGHT
    tab = (
        cq.Workplane("XY")
        .rect(LEG_WIDTH, TAB_DEPTH)
        .extrude(TAB_THICK)
        .translate((0, -(LEG_THICK / 2 + TAB_DEPTH / 2), tab_top_z - TAB_THICK / 2))
    )

    leg = vertical.union(foot).union(tab)

    # Capsule lightening holes in vertical section
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

    # Pin header holes through the mounting tab (vertical, Z-axis)
    # These align with matching holes in the bottom plate for soldered connection
    hole_r = HEADER_HOLE_D / 2
    span = (LEG_HEADER_PINS - 1) * HEADER_PITCH
    tab_center_y = -(LEG_THICK / 2 + TAB_DEPTH / 2)

    for i in range(LEG_HEADER_PINS):
        hx = -span / 2 + i * HEADER_PITCH
        hole = (
            cq.Workplane("XY")
            .center(hx, tab_center_y)
            .circle(hole_r)
            .extrude(TAB_THICK)
            .translate((0, 0, tab_top_z - TAB_THICK))
        )
        leg = leg.cut(hole)

    return leg
