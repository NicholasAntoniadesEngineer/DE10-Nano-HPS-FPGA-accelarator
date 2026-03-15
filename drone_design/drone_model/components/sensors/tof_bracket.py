"""L-shaped ToF sensor mounting bracket — FR4 PCB, 1.6mm thick."""

import cadquery as cq

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

TOF_BRACKET_BASE   = 15    # mm, base face width (attaches to frame plate)
TOF_BRACKET_TAB    = 15    # mm, vertical tab width (holds ToF board)
TOF_BRACKET_DEPTH  = 20    # mm, depth of both faces
TOF_BRACKET_T      = 1.6   # mm, FR4 thickness
TOF_BRACKET_HOLE_D = 2.0   # mm, M2 hole diameter

CATALOG = {
    "tof_bracket": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm",
        "dims": "15 x 20 x 15mm L-shape",
        "mass_g": 1.0, "qty": 6,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "L-shaped bracket for VL53L1X ToF sensor",
        "interface": "2x M2 to frame plate; 2x M2 to ToF board",
    },
}


def make_tof_bracket():
    """L-shaped ToF sensor mounting bracket — FR4 PCB, 1.6mm thick.

    Two rectangular faces at 90 degrees:
      - Base face (XY plane): 15 x 20 mm, attaches to frame plate via 2x M2 holes
      - Vertical tab (XZ plane): 15 x 20 mm, holds ToF board via 2x M2 holes
    """
    # Base face — lies flat on the frame plate
    base = (
        cq.Workplane("XY")
        .rect(TOF_BRACKET_BASE, TOF_BRACKET_DEPTH)
        .extrude(TOF_BRACKET_T)
    )
    base = (
        base.faces(">Z").workplane()
        .pushPoints([(0, -5), (0, 5)])
        .hole(TOF_BRACKET_HOLE_D)
    )

    # Vertical tab — perpendicular to base, rises from one edge
    tab = (
        cq.Workplane("XZ")
        .center(0, TOF_BRACKET_T + TOF_BRACKET_TAB / 2)
        .rect(TOF_BRACKET_BASE, TOF_BRACKET_TAB)
        .extrude(TOF_BRACKET_T)
        .translate((0, TOF_BRACKET_DEPTH / 2 - TOF_BRACKET_T, 0))
    )
    tab = (
        tab.faces(">Y").workplane()
        .pushPoints([(0, -5), (0, 5)])
        .hole(TOF_BRACKET_HOLE_D)
    )

    shape = base.union(tab)

    anchors = {}
    if Anchor is not None:
        # Base bottom face (Z=0), normal down — bolts to frame plate
        anchors["plate_mount"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Base face for frame plate mounting",
        )
        # Vertical tab outer face (+Y side), normal +Y — ToF board attaches here
        anchors["sensor_mount"] = Anchor(
            point=(0, TOF_BRACKET_DEPTH / 2, TOF_BRACKET_T + TOF_BRACKET_TAB / 2),
            normal=(0, 1, 0),
            label="Tab face for ToF board attachment",
        )

    return shape, anchors
