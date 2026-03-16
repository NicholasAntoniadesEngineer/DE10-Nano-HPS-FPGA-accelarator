"""L-shaped landing gear leg with horizontal mounting tab, lightening holes, and header holes.

The leg has three sections:
  1. Foot — horizontal at bottom, extends outward (+Y) for ground contact
  2. Vertical — upright section with capsule lightening holes for weight reduction
  3. Mounting tab — horizontal at top, extends inward (-Y) to overlap under the
     bottom plate. Pin header holes pass vertically (Z-axis) through both the tab
     and the plate for a soldered structural/electrical connection.
"""

import json
try:
    import cadquery as cq
except ImportError:
    cq = None
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

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
HEADER_PAD_D    = _D["connections"]["header_pad_diameter"]
LEG_HEADER_PINS = _D["connections"]["leg_header_pins"]
PCB_EDGE_CHAMFER = _D["assembly"]["pcb_edge_chamfer"]
PCB_OUTLINE_R = _D["assembly"].get("pcb_outline_corner_radius", 1.5)

CATALOG = {
    "landing_leg": {
        "material": "FR4 Glass Epoxy", "thickness": "2.0mm",
        "dims": "L-shape: 20x80mm vertical + 40mm foot",
        "mass_g": 8, "qty": 4,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "L-shaped with 3x capsule lightening holes",
        "interface": "Bolts to bottom plate edge",
    },
}


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
    leg_chamfer = min(PCB_EDGE_CHAMFER, LEG_THICK * 0.45)
    # Vertical section — stands at plate edge
    vertical = (
        cq.Workplane("XZ")
        .rect(LEG_WIDTH, LEG_HEIGHT)
        .extrude(LEG_THICK)
        .edges("|Y")
        .chamfer(leg_chamfer)
        .translate((0, 0, FOOT_THICK + LEG_HEIGHT / 2))
    )

    # Foot — extends outward (+Y) at ground level
    foot = (
        cq.Workplane("XY")
        .rect(LEG_WIDTH, FOOT_LENGTH)
        .extrude(FOOT_THICK)
        .edges("|Z")
        .chamfer(min(PCB_EDGE_CHAMFER, FOOT_THICK * 0.45))
        .translate((0, FOOT_LENGTH / 2 - LEG_THICK / 2, FOOT_THICK / 2))
    )

    # Mounting tab — extends inward (-Y) at the top of the vertical section
    # Tab top surface aligns with bottom plate bottom surface
    tab_top_z = FOOT_THICK + LEG_HEIGHT
    tab = (
        cq.Workplane("XY")
        .rect(LEG_WIDTH, TAB_DEPTH)
        .extrude(TAB_THICK)
        .edges("|Z")
        .chamfer(min(PCB_EDGE_CHAMFER, TAB_THICK * 0.45))
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

    anchors = {}
    if Anchor is not None:
        # Foot base: ground contact at bottom of foot, center of foot
        anchors["foot_base"] = Anchor(
            point=(0, FOOT_LENGTH / 2 - LEG_THICK / 2, 0),
            normal=(0, 0, -1),
            label="foot base (ground contact)",
        )
        # Mount tab: top of mounting tab, at tab center (inward from vertical section)
        # The tab extends in -Y from the vertical section; its center is at:
        tab_center_y = -(LEG_THICK / 2 + TAB_DEPTH / 2)
        tab_top_z = FOOT_THICK + LEG_HEIGHT
        anchors["mount_tab"] = Anchor(
            point=(0, tab_center_y, tab_top_z),
            normal=(0, 0, 1),
            label="mount tab center (solders to plate underside)",
        )

    return leg, anchors


# =============================================================================
# KiCad PCB generator
# =============================================================================

try:
    from cadquery_framework.kicad.primitives import (
        rounded_rect_outline,
        outline_to_sexpr, through_hole_pad,
        text_sexpr, kicad_pcb_wrapper,
    )
except ImportError:
    pass  # KiCad export not available


def generate_landing_leg_pcb():
    """Generate .kicad_pcb for one L-shaped landing leg with mounting tab.

    PCB layout (unfolded flat, as manufactured):
      - Vertical section: LEG_WIDTH x LEG_HEIGHT, centered at (0, LEG_HEIGHT/2)
      - Foot: FOOT_LENGTH x FOOT_THICK, extending to +X at bottom
      - Mounting tab: LEG_WIDTH x TAB_DEPTH, extending to -X at top (fold line at top edge)
      - Lightening holes in vertical section
      - Pin header holes in the mounting tab (for plate connection)

    When assembled, the tab folds 90 degrees to sit flat under the bottom plate.
    """
    tab_depth = TAB_DEPTH

    segs = []

    # Vertical section — rounded corners in cutout design
    segs.extend(rounded_rect_outline(LEG_WIDTH, LEG_HEIGHT, min(PCB_OUTLINE_R, LEG_WIDTH / 2 - 0.5), 0, LEG_HEIGHT / 2))

    # Foot (horizontal extension at bottom, extends to +X) — rounded corners
    foot_cx = FOOT_LENGTH / 2 - LEG_WIDTH / 2
    segs.extend(rounded_rect_outline(FOOT_LENGTH, FOOT_THICK, min(PCB_OUTLINE_R, FOOT_THICK / 2 - 0.2), foot_cx, 0))

    # Mounting tab at top (extends to -X, representing inward fold under plate) — rounded corners
    tab_cx = -(LEG_WIDTH / 2 + tab_depth / 2)
    tab_cy = LEG_HEIGHT - LEG_THICK / 2  # at top edge
    segs.extend(rounded_rect_outline(tab_depth, LEG_WIDTH, min(PCB_OUTLINE_R, LEG_WIDTH / 2 - 0.5), tab_cx, tab_cy))

    # Lightening holes in vertical section (capsule-shaped, simplified as ovals)
    hole_spacing = (LEG_HEIGHT - 20) / LEG_HOLE_N
    for i in range(LEG_HOLE_N):
        hy = 15 + hole_spacing * (i + 0.5)
        segs.extend(rounded_rect_outline(LEG_HOLE_W, LEG_HOLE_H, LEG_HOLE_R, 0, hy))

    content = outline_to_sexpr(segs)

    # Pin header holes in mounting tab (vertical through-holes when assembled)
    span = (LEG_HEADER_PINS - 1) * HEADER_PITCH
    for i in range(LEG_HEADER_PINS):
        hx = -span / 2 + i * HEADER_PITCH
        content += "\n" + through_hole_pad(hx, tab_cy, HEADER_HOLE_D, HEADER_PAD_D)

    # Fold line indicator on silkscreen
    fold_y = LEG_HEIGHT
    content += "\n" + text_sexpr("FOLD", -(LEG_WIDTH / 2 + tab_depth / 2), fold_y + 3, "F.SilkS", 1.0, 0.12)
    content += "\n" + text_sexpr("LEG", 0, LEG_HEIGHT / 2, "F.SilkS", 2, 0.2)

    return kicad_pcb_wrapper("Drone Landing Leg (L-shape + Tab)", LEG_THICK, content)
