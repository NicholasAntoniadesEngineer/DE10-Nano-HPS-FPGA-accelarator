"""Skeleton frame plate with Kagome-lattice cutouts and bolt-on arm mounting rails."""

import json
import math
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

PLATE_SIZE     = _D["frame"]["plate_size"]
PLATE_CORNER_R = _D["frame"]["plate_corner_radius"]
ARM_ANGLES     = _D["arms"]["arm_angles_deg"]
DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
KAGOME_CELL    = _D["assembly"]["kagome_cell_size"]
KAGOME_HOLE_R  = _D["assembly"]["kagome_hole_radius"]
KAGOME_WEB_MIN = _D["assembly"]["kagome_min_web"]
KAGOME_FILLET_R = _D["assembly"]["kagome_fillet_radius"]

# Pin header connection specs (retained for leg headers)
HEADER_PITCH       = _D["connections"]["header_pitch"]
HEADER_HOLE_D      = _D["connections"]["header_hole_diameter"]
LEG_HEADER_PINS    = _D["connections"]["leg_header_pins"]
LEG_ANGLES         = _D["landing_gear"]["leg_angles_deg"]
LEG_WIDTH          = _D["landing_gear"]["leg_width"]
LEG_THICK          = _D["landing_gear"]["leg_thickness"]
TAB_DEPTH          = _D["landing_gear"]["mounting_tab_depth"]

# Arm mounting rail constants
ARM_MOUNT_HOLE_D    = 2.2    # M2 clearance hole diameter
ARM_MOUNT_ROW_OFFSET = 5.0   # Perpendicular distance from arm centerline to each bolt row
ARM_MOUNT_PITCH     = 10.0   # Along-radial hole spacing
ARM_MOUNT_START     = 15.0   # Radial distance from center to first hole
ARM_MOUNT_EDGE_MARGIN = 5.0  # Margin from plate edge


def _kagome_cutouts(plate, thick, keepout_circles):
    """Apply Kagome-inspired triangular lattice cutouts to a plate."""
    half = PLATE_SIZE / 2 - 5

    row_h = KAGOME_CELL * math.sqrt(3) / 2
    centers = []
    row = 0
    y = -half + KAGOME_WEB_MIN
    while y < half - KAGOME_WEB_MIN:
        x_off = (KAGOME_CELL / 2) if (row % 2) else 0
        x = -half + KAGOME_WEB_MIN + x_off
        while x < half - KAGOME_WEB_MIN:
            clear = True
            for kcx, kcy, kr in keepout_circles:
                if math.hypot(x - kcx, y - kcy) < kr + KAGOME_HOLE_R + KAGOME_WEB_MIN:
                    clear = False
                    break
            if clear and math.hypot(x, y) > 12:
                centers.append((x, y))
            x += KAGOME_CELL
        y += row_h
        row += 1

    for cx, cy in centers:
        try:
            cutout = (
                cq.Workplane("XY")
                .center(cx, cy)
                .polygon(6, KAGOME_HOLE_R * 2)
                .extrude(thick)
            )
            plate = plate.cut(cutout)
        except Exception:
            pass

    try:
        plate = plate.edges("|Z").fillet(KAGOME_FILLET_R)
    except Exception:
        pass

    return plate


def _add_arm_mounting_rails(plate, thick):
    """Drill radial rows of M2 bolt holes along each arm angle for adjustable arm mounting.

    Two parallel rows of holes per arm, offset +/-ARM_MOUNT_ROW_OFFSET perpendicular
    to the arm centerline. Holes run from ARM_MOUNT_START out to the plate edge
    minus ARM_MOUNT_EDGE_MARGIN, spaced at ARM_MOUNT_PITCH.
    """
    hole_r = ARM_MOUNT_HOLE_D / 2
    # Maximum radial distance: from center to plate corner along a 45-degree arm
    # is PLATE_SIZE/2 * sqrt(2), but we conservatively use the inscribed circle
    # (distance to edge midpoint) for a square plate.
    # For a square plate, the max radial distance to the edge along angle theta is:
    # min(PLATE_SIZE/2 / |cos(theta)|, PLATE_SIZE/2 / |sin(theta)|)
    half = PLATE_SIZE / 2

    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        # Perpendicular direction
        perp_x, perp_y = -sin_a, cos_a

        # Compute max radial distance to plate edge along this angle
        abs_cos = abs(cos_a) if abs(cos_a) > 1e-9 else 1e-9
        abs_sin = abs(sin_a) if abs(sin_a) > 1e-9 else 1e-9
        max_radial = min(half / abs_cos, half / abs_sin) - ARM_MOUNT_EDGE_MARGIN

        # Generate hole positions along the radial line
        dist = ARM_MOUNT_START
        while dist <= max_radial:
            cx = dist * cos_a
            cy = dist * sin_a
            for side in [-1, 1]:
                hx = cx + side * ARM_MOUNT_ROW_OFFSET * perp_x
                hy = cy + side * ARM_MOUNT_ROW_OFFSET * perp_y
                hole = (
                    cq.Workplane("XY")
                    .center(hx, hy)
                    .circle(hole_r)
                    .extrude(thick)
                )
                plate = plate.cut(hole)
            dist += ARM_MOUNT_PITCH

    return plate


def _arm_rail_keepouts():
    """Generate keepout circles along the arm mounting rail paths."""
    keepouts = []
    half = PLATE_SIZE / 2

    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        abs_cos = abs(cos_a) if abs(cos_a) > 1e-9 else 1e-9
        abs_sin = abs(sin_a) if abs(sin_a) > 1e-9 else 1e-9
        max_radial = min(half / abs_cos, half / abs_sin) - ARM_MOUNT_EDGE_MARGIN

        dist = ARM_MOUNT_START
        while dist <= max_radial:
            cx = dist * cos_a
            cy = dist * sin_a
            # Keepout radius covers the two rows plus some margin
            keepouts.append((cx, cy, ARM_MOUNT_ROW_OFFSET + 4.0))
            dist += ARM_MOUNT_PITCH

    return keepouts


def _add_leg_header_holes(plate, thick):
    """Add pin header through-holes where landing leg mounting tabs overlap.

    Each leg has a horizontal tab extending inward under the plate by TAB_DEPTH.
    The tab center (radially) is at PLATE_SIZE/2 - LEG_THICK/2 - TAB_DEPTH/2.
    Holes are arranged tangentially (along the plate edge direction).
    """
    hole_r = HEADER_HOLE_D / 2
    span = (LEG_HEADER_PINS - 1) * HEADER_PITCH
    start = -span / 2
    # Radial distance to tab center: plate edge minus half the vertical
    # section thickness minus half the tab depth
    tab_center_dist = PLATE_SIZE / 2 - LEG_THICK / 2 - TAB_DEPTH / 2

    for angle in LEG_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        # Tangent direction (along plate edge)
        tang_x, tang_y = -sin_a, cos_a

        for i in range(LEG_HEADER_PINS):
            offset = start + i * HEADER_PITCH
            hx = tab_center_dist * cos_a + offset * tang_x
            hy = tab_center_dist * sin_a + offset * tang_y
            hole = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(hole_r)
                .extrude(thick)
            )
            plate = plate.cut(hole)

    return plate


def make_skeleton_plate(thick, is_bottom=True):
    """Create a plate with Kagome-lattice cutouts, arm mounting rails, and leg mount holes."""
    plate = (
        cq.Workplane("XY")
        .rect(PLATE_SIZE, PLATE_SIZE)
        .extrude(thick)
        .edges("|Z").fillet(PLATE_CORNER_R)
    )

    # Arm mounting rails (radial rows of M2 bolt holes)
    plate = _add_arm_mounting_rails(plate, thick)

    # Keepout zones for kagome cutouts: arm rail paths
    keepouts = _arm_rail_keepouts()

    if not is_bottom:
        central = (
            cq.Workplane("XY")
            .rect(72, 110)
            .extrude(thick)
            .edges("|Z").fillet(PLATE_CORNER_R)
        )
        plate = plate.cut(central)
        keepouts.append((0, 0, 58.0))
    else:
        # Battery strap slots
        for dy in [-20, 20]:
            strap = (
                cq.Workplane("XY")
                .center(0, dy)
                .rect(25, 3)
                .extrude(thick)
            )
            plate = plate.cut(strap)
            keepouts.append((0, dy, 15.0))

        # DE10-Nano standoff mounting holes (M2.5 clearance = 2.7mm)
        for dx in [-DE10_W/2 + 4, DE10_W/2 - 4]:
            for dy in [-DE10_L/2 + 4, DE10_L/2 - 4]:
                hole = (
                    cq.Workplane("XY")
                    .center(dx, dy)
                    .circle(1.35)
                    .extrude(thick)
                )
                plate = plate.cut(hole)
                keepouts.append((dx, dy, 5.0))

        # Landing leg header holes (bottom plate only — legs attach via mounting tab)
        plate = _add_leg_header_holes(plate, thick)
        tab_center_dist = PLATE_SIZE / 2 - LEG_THICK / 2 - TAB_DEPTH / 2
        for angle in LEG_ANGLES:
            rad = math.radians(angle)
            keepouts.append((
                tab_center_dist * math.cos(rad),
                tab_center_dist * math.sin(rad),
                10.0
            ))

    plate = _kagome_cutouts(plate, thick, keepouts)
    return plate
