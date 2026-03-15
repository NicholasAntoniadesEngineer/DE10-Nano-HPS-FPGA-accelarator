"""Skeleton frame plate with Kagome-lattice cutouts and bolt-on arm mounting rails."""

import json
import math
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

PLATE_SIZE     = _D["frame"]["plate_size"]
PLATE_CORNER_R = _D["frame"]["plate_corner_radius"]
ARM_ANGLES     = _D["arms"]["arm_angles_deg"]
ARM_WIDTH      = _D["arms"]["arm_width"]
DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
KAGOME_CELL    = _D["assembly"]["kagome_cell_size"]
KAGOME_HOLE_R  = _D["assembly"]["kagome_hole_radius"]
KAGOME_WEB_MIN = _D["assembly"]["kagome_min_web"]
KAGOME_FILLET_R = _D["assembly"]["kagome_fillet_radius"]

# Pin header connection specs (retained for leg headers)
HEADER_PITCH       = _D["connections"]["header_pitch"]
HEADER_HOLE_D      = _D["connections"]["header_hole_diameter"]
HEADER_PAD_D       = _D["connections"]["header_pad_diameter"]
LEG_HEADER_PINS    = _D["connections"]["leg_header_pins"]
LEG_ANGLES         = _D["landing_gear"]["leg_angles_deg"]
LEG_WIDTH          = _D["landing_gear"]["leg_width"]
LEG_THICK          = _D["landing_gear"]["leg_thickness"]
TAB_DEPTH          = _D["landing_gear"]["mounting_tab_depth"]

BOTTOM_THICK   = _D["frame"]["bottom_plate_thickness"]
TOP_THICK      = _D["frame"]["top_plate_thickness"]
MOTOR_R        = _D["arms"]["motor_to_motor_diagonal"] / 2
MOUNT_FLANGE_LEN = _D["arms"]["mount_flange_length"]
# Arm slot at plate corner — arm inner tip sits here, flange overlaps plate
PLATE_DIAG_R   = PLATE_SIZE * math.sqrt(2) / 2
ARM_SLOT_R     = PLATE_DIAG_R - MOUNT_FLANGE_LEN
ARM_CLEARANCE_R = ARM_SLOT_R  # legacy alias

CATALOG = {
    "bottom_plate": {
        "material": "FR4 Glass Epoxy", "thickness": f"{BOTTOM_THICK}mm",
        "dims": f"{PLATE_SIZE} x {PLATE_SIZE} x {BOTTOM_THICK} mm",
        "mass_g": 42, "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Kagome lattice cutouts, 4x M2.5 standoff holes, 4x arm slots, 2x battery strap slots",
        "interface": "Arms press-fit into slots; standoffs bolt through M2.5 holes",
    },
    "top_plate": {
        "material": "FR4 Glass Epoxy", "thickness": f"{TOP_THICK}mm",
        "dims": f"{PLATE_SIZE} x {PLATE_SIZE} x {TOP_THICK} mm",
        "mass_g": 28, "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Kagome lattice cutouts, 72x110mm central opening for DE10-Nano access",
        "interface": "Arms press-fit into slots; landing legs bolt at edges",
    },
}

ARM_MOUNT_HOLE_D      = 2.2
ARM_MOUNT_ROW_OFFSET  = _D["arms"]["mount_row_offset"]
ARM_MOUNT_PITCH       = 10.0
ARM_MOUNT_START       = 15.0
ARM_MOUNT_EDGE_MARGIN = 5.0


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
        # Large central cutout clears ALL DE10 connectors that protrude above
        # top plate Z. Then ADD BACK material tabs at the 4 M2.5 mounting holes
        # so the plate can bolt to the standoff stack through the daughter board.
        cutout_x = DE10_W + 4.0   # 72.58mm
        cutout_y = DE10_L + 4.0   # 111.95mm
        # Clamp to plate size minus minimum frame border (6mm each side)
        cutout_x = min(cutout_x, PLATE_SIZE - 12.0)
        cutout_y = min(cutout_y, PLATE_SIZE - 12.0)
        central = (
            cq.Workplane("XY")
            .rect(cutout_x, cutout_y)
            .extrude(thick)
        )
        plate = plate.cut(central)
        keepouts.append((0, 0, max(cutout_x, cutout_y) / 2 + 2.0))

        # Add material tabs back at each M2.5 mounting hole position.
        # Each tab is a 14mm square pad connected to the outer frame by a
        # 6mm wide bridge running radially outward to the plate border.
        de10_hole_inset = _D["de10_nano"]["mounting_hole_inset"]
        _m25_clearance_r = _D["daughter_board_mounting"]["mounting_hole_diameter"] / 2
        _tab_size = 14.0  # square pad size around hole
        _bridge_w = 6.0   # bridge width connecting tab to outer frame
        _half_plate = PLATE_SIZE / 2

        for dx in [-DE10_W / 2 + de10_hole_inset, DE10_W / 2 - de10_hole_inset]:
            for dy in [-DE10_L / 2 + de10_hole_inset, DE10_L / 2 - de10_hole_inset]:
                # Square material tab at mounting hole
                tab = (
                    cq.Workplane("XY")
                    .center(dx, dy)
                    .rect(_tab_size, _tab_size)
                    .extrude(thick)
                )
                plate = plate.union(tab)

                # Bridge from tab to outer frame border (along X direction)
                sx = 1 if dx > 0 else -1
                bridge_cx = (dx + sx * _half_plate) / 2
                bridge_len = abs(sx * _half_plate - dx) + _tab_size / 2
                bridge = (
                    cq.Workplane("XY")
                    .center(bridge_cx, dy)
                    .rect(bridge_len, _bridge_w)
                    .extrude(thick)
                )
                plate = plate.union(bridge)

                # Drill M2.5 clearance hole through tab
                hole = cq.Workplane("XY").center(dx, dy).circle(_m25_clearance_r).extrude(thick)
                plate = plate.cut(hole)
                keepouts.append((dx, dy, _tab_size / 2 + 2.0))

        # Relief notches for DE10 connectors that protrude above top plate Z.
        # Cut AFTER tab/bridge unions so these clearances aren't filled back in.
        # After mirror fix: barrel_jack cq_x = -19.18, ethernet cq_x = +17.54
        for nx, ny, nw, nl in [
            (-19.18, -51.19, 14.0, 16.0),  # barrel jack + 2mm margin
            (17.54, 39.10, 20.0, 18.0),    # ethernet + 2mm margin
        ]:
            notch = (
                cq.Workplane("XY")
                .center(nx, ny)
                .rect(nw, nl)
                .extrude(thick)
            )
            plate = plate.cut(notch)

        # ToF bracket mounting on top plate.
        # Front/back brackets at Y=±45 fall INSIDE the central cutout (±49),
        # so we add material tabs + bridges at those positions.
        # Left/right brackets at X=±45 are outside cutout (±36.3) — solid material.
        _tof_half = PLATE_SIZE / 2
        _tof_inset = 10.0  # bracket center inset from plate edge
        _tof_m2_r = 1.1    # M2 clearance hole radius
        _tof_hole_spacing = 5.0
        _tof_tab_w = 16.0   # tab width for front/back bracket pads
        _tof_tab_h = 12.0   # tab depth (along Y)
        _tof_bridge_w = 6.0

        # Front/back: add material tabs inside cutout, bridged to plate border
        for sy in [1, -1]:
            cy = sy * (_tof_half - _tof_inset)  # ±45
            # Material tab at bracket position
            tab = (
                cq.Workplane("XY")
                .center(0, cy)
                .rect(_tof_tab_w, _tof_tab_h)
                .extrude(thick)
            )
            plate = plate.union(tab)
            # Bridge from tab to outer frame border (along Y)
            border_y = sy * _half_plate
            bridge_cy = (cy + border_y) / 2
            bridge_len = abs(border_y - cy) + _tof_tab_h / 2
            bridge = (
                cq.Workplane("XY")
                .center(0, bridge_cy)
                .rect(_tof_bridge_w, bridge_len)
                .extrude(thick)
            )
            plate = plate.union(bridge)

        # Drill M2 mounting holes for all 4 bracket positions
        tof_bracket_positions = [
            (0, _tof_half - _tof_inset, "x"),     # front
            (0, -(_tof_half - _tof_inset), "x"),   # back
            (-(_tof_half - _tof_inset), 0, "y"),   # left
            (_tof_half - _tof_inset, 0, "y"),      # right
        ]
        for cx, cy, axis in tof_bracket_positions:
            for offset in [-_tof_hole_spacing, _tof_hole_spacing]:
                if axis == "x":
                    hx, hy = cx + offset, cy
                else:
                    hx, hy = cx, cy + offset
                hole = cq.Workplane("XY").center(hx, hy).circle(_tof_m2_r).extrude(thick)
                plate = plate.cut(hole)
                keepouts.append((hx, hy, 4.0))
    else:
        strap_spacing = min(20.0, PLATE_SIZE / 6.0)
        for dy in [-strap_spacing, strap_spacing]:
            strap = (
                cq.Workplane("XY")
                .center(0, dy)
                .rect(20, 3)
                .extrude(thick)
            )
            plate = plate.cut(strap)
            keepouts.append((0, dy, 12.0))

        de10_hole_inset = _D["de10_nano"]["mounting_hole_inset"]
        standoff_clearance_r = _D["daughter_board_mounting"]["mounting_hole_diameter"] / 2
        for dx in [-DE10_W/2 + de10_hole_inset, DE10_W/2 - de10_hole_inset]:
            for dy in [-DE10_L/2 + de10_hole_inset, DE10_L/2 - de10_hole_inset]:
                hole = (
                    cq.Workplane("XY")
                    .center(dx, dy)
                    .circle(standoff_clearance_r)
                    .extrude(thick)
                )
                plate = plate.cut(hole)
                keepouts.append((dx, dy, 5.0))

        # ToF-down direct board mount — 2x M2 holes at plate center for VL53L1X
        # Board mounting holes at diagonal corners, spacing 7.62 x 12.7mm
        _tof_hole_sx = _D["tof_sensor"]["mounting_hole_spacing_x"]
        _tof_hole_sy = _D["tof_sensor"]["mounting_hole_spacing_y"]
        for sx, sy in [(-1, -1), (1, 1)]:
            hx = sx * _tof_hole_sx / 2
            hy = sy * _tof_hole_sy / 2
            hole = cq.Workplane("XY").center(hx, hy).circle(1.1).extrude(thick)
            plate = plate.cut(hole)
            keepouts.append((hx, hy, 4.0))

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

    # --- Build anchors ---
    anchors = {}
    if Anchor is not None:
        anchors["top_surface"] = Anchor(
            point=(0, 0, thick), normal=(0, 0, 1), label="top surface"
        )
        anchors["bottom_surface"] = Anchor(
            point=(0, 0, 0), normal=(0, 0, -1), label="bottom surface"
        )

        # Arm slot anchors at plate corners along each arm angle.
        # The arm's frame_end (inner tip) sits here; the mount flange extends
        # inward over the plate corner for bolt-on mounting.
        _arm_slot_r = ARM_SLOT_R
        for i, angle in enumerate(ARM_ANGLES, start=1):
            rad = math.radians(angle)
            ax = _arm_slot_r * math.cos(rad)
            ay = _arm_slot_r * math.sin(rad)
            anchors[f"arm_slot_{i}"] = Anchor(
                point=(ax, ay, thick),
                normal=(0, 0, 1),
                label=f"arm slot {i} ({angle} deg)",
            )

        # Standoff hole anchors (DE10 mounting holes, bottom plate only)
        if is_bottom:
            de10_hole_inset = _D["de10_nano"]["mounting_hole_inset"]
            idx = 1
            for dx in [-DE10_W / 2 + de10_hole_inset, DE10_W / 2 - de10_hole_inset]:
                for dy in [-DE10_L / 2 + de10_hole_inset, DE10_L / 2 - de10_hole_inset]:
                    anchors[f"standoff_hole_{idx}"] = Anchor(
                        point=(dx, dy, thick),
                        normal=(0, 0, 1),
                        label=f"standoff hole {idx}",
                    )
                    idx += 1

            # Battery mounting point (underslung)
            anchors["battery_mount"] = Anchor(
                point=(_D["battery"]["cg_offset_x"], 0, 0),
                normal=(0, 0, -1),
                label="battery mount (underslung)",
            )
            # Pump bracket mounting point (underslung)
            anchors["pump_bracket_mount"] = Anchor(
                point=(_D["assembly"]["pump_bracket_offset_x"], _D["assembly"]["pump_bracket_offset_y"], 0),
                normal=(0, 0, -1),
                label="pump bracket mount (underslung)",
            )
            # Reservoir mounting point (underslung)
            anchors["reservoir_mount"] = Anchor(
                point=(_D["reservoir"]["offset_x"], _D["assembly"]["reservoir_offset_y"], 0),
                normal=(0, 0, -1),
                label="reservoir mount (underslung)",
            )
            # Nose boom root attachment (+X edge)
            boom_z_local = thick + _D["assembly"]["arm_z_above_bottom"] - _D["nose_boom"]["thickness"] / 2
            anchors["boom_root"] = Anchor(
                point=(PLATE_SIZE / 2, 0, boom_z_local),
                normal=(1, 0, 0),
                label="boom root (plate edge)",
            )
            # ToF-down direct board mount — board lies flat on underside, sensor faces down.
            # Board's mount_face (0,0,-1) opposes this anchor's (0,0,-1) → board flips
            # 180°, sensor aperture points downward.
            anchors["tof_mount_down"] = Anchor(
                point=(0, 0, 0),
                normal=(0, 0, -1),
                label="ToF down — board direct-mount on plate underside, sensor faces -Z",
            )

        # Leg slot anchors at LEG_ANGLES on plate edges
        leg_dist = PLATE_SIZE / 2 + _D["landing_gear"]["leg_thickness"] / 2
        for i, angle in enumerate(LEG_ANGLES, start=1):
            rad = math.radians(angle)
            lx = leg_dist * math.cos(rad)
            ly = leg_dist * math.sin(rad)
            anchors[f"leg_slot_{i}"] = Anchor(
                point=(lx, ly, 0),
                normal=(0, 0, -1),
                label=f"leg slot {i} ({angle} deg)",
            )

        # Upper standoff holes (top plate — bolts from below through standoff)
        if not is_bottom:
            de10_hole_inset = _D["de10_nano"]["mounting_hole_inset"]
            idx = 1
            for dx in [-DE10_W / 2 + de10_hole_inset, DE10_W / 2 - de10_hole_inset]:
                for dy in [-DE10_L / 2 + de10_hole_inset, DE10_L / 2 - de10_hole_inset]:
                    anchors[f"standoff_hole_{idx}"] = Anchor(
                        point=(dx, dy, 0),
                        normal=(0, 0, -1),
                        label=f"upper standoff hole {idx}",
                    )
                    idx += 1

        # ToF mounts (top plate)
        # UP/DOWN: ToF board mounted DIRECTLY on plate surface (no bracket).
        #   Board lies flat; sensor aperture faces away from plate.
        # SIDE (front/back/left/right): L-bracket base on plate top surface
        #   near the edge, tab hangs over the edge. Spin orients the tab
        #   toward the target direction. 2x M2 holes per bracket location.
        if not is_bottom:
            _half = PLATE_SIZE / 2
            _brk_inset = 10.0  # half bracket depth, tab overhangs edge

            # Note: ToF-up is mounted on daughter board, not top plate.

            # SIDE bracket mounts — bracket base on top surface near each edge
            anchors["tof_mount_front"] = Anchor(
                point=(0, _half - _brk_inset, thick),
                normal=(0, 0, 1),
                label="ToF bracket (front) — base on top, tab over +Y edge",
            )
            anchors["tof_mount_back"] = Anchor(
                point=(0, -(_half - _brk_inset), thick),
                normal=(0, 0, 1),
                label="ToF bracket (back) — base on top, tab over -Y edge",
            )
            anchors["tof_mount_left"] = Anchor(
                point=(-(_half - _brk_inset), 0, thick),
                normal=(0, 0, 1),
                label="ToF bracket (left) — base on top, tab over -X edge",
            )
            anchors["tof_mount_right"] = Anchor(
                point=(_half - _brk_inset, 0, thick),
                normal=(0, 0, 1),
                label="ToF bracket (right) — base on top, tab over +X edge",
            )

    return plate, anchors


# =============================================================================
# KiCad PCB generators
# =============================================================================

try:
    from cadquery_framework.kicad.primitives import (
        rounded_rect_outline, rect_outline, hexagon_outline,
        outline_to_sexpr, through_hole_pad, header_pad_row,
        text_sexpr, kicad_pcb_wrapper,
    )
except ImportError:
    pass  # KiCad export not available


def _kagome_cutout_centers_pcb(plate_size, keepout_circles):
    """Compute Kagome hexagonal cutout centers for PCB outline generation."""
    half = plate_size / 2 - 5
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
    return centers


def generate_bottom_plate_pcb():
    """Generate .kicad_pcb for bottom frame plate."""
    segs = []

    # Board outline: rounded rectangle
    segs.extend(rounded_rect_outline(PLATE_SIZE, PLATE_SIZE, PLATE_CORNER_R))

    # Battery strap slots (2x)
    for dy in [-20, 20]:
        segs.extend(rect_outline(25, 3, 0, dy))

    # Keepout zones for Kagome computation (along arm rail paths)
    keepouts = []
    _MOUNT_PITCH = 10.0
    _MOUNT_START = 15.0
    _MOUNT_EDGE = 5.0
    _MOUNT_ROW_OFF = 5.0
    half = PLATE_SIZE / 2
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        abs_cos = abs(cos_a) if abs(cos_a) > 1e-9 else 1e-9
        abs_sin = abs(sin_a) if abs(sin_a) > 1e-9 else 1e-9
        max_r = min(half / abs_cos, half / abs_sin) - _MOUNT_EDGE
        dist = _MOUNT_START
        while dist <= max_r:
            keepouts.append((dist * cos_a, dist * sin_a, _MOUNT_ROW_OFF + 4.0))
            dist += _MOUNT_PITCH
    for dy in [-20, 20]:
        keepouts.append((0, dy, 15.0))

    # DE10-Nano standoff holes (4x M2.5)
    holes = []
    for dx in [-DE10_W / 2 + 4, DE10_W / 2 - 4]:
        for dy in [-DE10_L / 2 + 4, DE10_L / 2 - 4]:
            holes.append((dx, dy))
            keepouts.append((dx, dy, 5.0))

    # Kagome hexagonal cutouts
    hex_centers = _kagome_cutout_centers_pcb(PLATE_SIZE, keepouts)
    for cx, cy in hex_centers:
        segs.extend(hexagon_outline(cx, cy, KAGOME_HOLE_R))

    # Build content
    content = outline_to_sexpr(segs)
    for hx, hy in holes:
        content += "\n" + through_hole_pad(hx, hy, 2.7, 4.5)  # M2.5 hole

    # Arm mounting rail holes (radial rows of M2 bolt holes along each arm angle)
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        perp_x, perp_y = -sin_a, cos_a
        abs_cos = abs(cos_a) if abs(cos_a) > 1e-9 else 1e-9
        abs_sin = abs(sin_a) if abs(sin_a) > 1e-9 else 1e-9
        max_r = min(half / abs_cos, half / abs_sin) - _MOUNT_EDGE
        dist = _MOUNT_START
        while dist <= max_r:
            for side in [-1, 1]:
                hx = dist * cos_a + side * _MOUNT_ROW_OFF * perp_x
                hy = dist * sin_a + side * _MOUNT_ROW_OFF * perp_y
                content += "\n" + through_hole_pad(hx, hy, 2.2, 4.0)  # M2 clearance
            dist += _MOUNT_PITCH

    # Leg header holes (matching mounting tab overlap area)
    _LEG_ANGLES = [0, 90, 180, 270]
    _LEG_THICK = _D["landing_gear"]["leg_thickness"]
    _TAB_DEPTH = _D["landing_gear"]["mounting_tab_depth"]
    tab_center_dist = PLATE_SIZE / 2 - _LEG_THICK / 2 - _TAB_DEPTH / 2
    for angle in _LEG_ANGLES:
        rad = math.radians(angle)
        lx = tab_center_dist * math.cos(rad)
        ly = tab_center_dist * math.sin(rad)
        content += "\n" + header_pad_row(lx, ly, LEG_HEADER_PINS, HEADER_PITCH, angle_deg=angle + 90, drill_d=HEADER_HOLE_D, pad_d=HEADER_PAD_D)

    content += "\n" + text_sexpr("BOTTOM PLATE", 0, 0, "F.SilkS", 3, 0.3)
    content += "\n" + text_sexpr(f"{PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm  FR4 {BOTTOM_THICK:.1f}mm", 0, 5, "F.SilkS", 1.2, 0.15)

    return kicad_pcb_wrapper("Drone Bottom Frame Plate", BOTTOM_THICK, content)


def generate_top_plate_pcb():
    """Generate .kicad_pcb for top frame plate."""
    segs = []

    # Board outline
    segs.extend(rounded_rect_outline(PLATE_SIZE, PLATE_SIZE, PLATE_CORNER_R))

    # Central rectangular opening — sized to stay inside standoff hole pattern
    _tp_hole_inset = _D["de10_nano"]["mounting_hole_inset"]
    _tp_cutout_x = 2 * (DE10_W / 2 - _tp_hole_inset - 6.0)
    _tp_cutout_y = 2 * (DE10_L / 2 - _tp_hole_inset - 6.0)
    segs.extend(rounded_rect_outline(_tp_cutout_x, _tp_cutout_y, PLATE_CORNER_R))

    # Keepouts (along arm rail paths + central opening)
    keepouts = []
    half = PLATE_SIZE / 2
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        abs_cos = abs(cos_a) if abs(cos_a) > 1e-9 else 1e-9
        abs_sin = abs(sin_a) if abs(sin_a) > 1e-9 else 1e-9
        max_r = min(half / abs_cos, half / abs_sin) - 5.0
        dist = 15.0
        while dist <= max_r:
            keepouts.append((dist * cos_a, dist * sin_a, 9.0))
            dist += 10.0
    keepouts.append((0, 0, 58.0))  # central opening keepout

    # Kagome cutouts
    hex_centers = _kagome_cutout_centers_pcb(PLATE_SIZE, keepouts)
    for cx, cy in hex_centers:
        segs.extend(hexagon_outline(cx, cy, KAGOME_HOLE_R))

    content = outline_to_sexpr(segs)
    content += "\n" + text_sexpr("TOP PLATE", 0, -PLATE_SIZE / 2 + 8, "F.SilkS", 2.5, 0.25)
    content += "\n" + text_sexpr(f"{PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm  FR4 {TOP_THICK:.1f}mm", 0, -PLATE_SIZE / 2 + 13, "F.SilkS", 1.0, 0.12)

    return kicad_pcb_wrapper("Drone Top Frame Plate", TOP_THICK, content)
