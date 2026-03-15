"""Modular two-section I-beam arm with adjustable motor distance.

All dimensions read from cad/dimensions.json (arms + motor sections).

The arm is split into two interlocking sections:

  Inner section  — bolt-on mounting flange at the frame end, I-beam body,
                   and a web-only overlap tail that slides inside the outer.

  Outer section  — motor mount plate at the tip, I-beam body, and a full
                   I-beam collar that receives the inner section's web.

Mount flange hole count adapts automatically to flange length.
Overlap hole count adapts automatically to overlap length.

Coordinate system: X = 0 is the arm mid-point.  Flange end at -ARM_LENGTH/2,
motor tip at +ARM_LENGTH/2.
"""

import math
import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

MOTOR_TO_MOTOR_DIAG = _D["arms"]["motor_to_motor_diagonal"]
MOTOR_R       = MOTOR_TO_MOTOR_DIAG / 2

MOUNT_FLANGE_LEN  = _D["arms"]["mount_flange_length"]
MOUNT_HOLE_D      = 2.2
MOUNT_ROW_OFFSET  = _D["arms"]["mount_row_offset"]
MOUNT_HOLE_PITCH  = 10.0

ARM_CLEARANCE_R = math.ceil((_D["arms"]["arm_width"] + 2) / math.sqrt(2))
ARM_LENGTH    = MOTOR_R - ARM_CLEARANCE_R
ARM_WIDTH     = _D["arms"]["arm_width"]
ARM_THICK     = _D["arms"]["arm_thickness"]
ARM_FLANGE    = _D["arms"]["arm_flange_width"]
ARM_WEB       = _D["arms"]["arm_web_width"]
MOTOR_SECTION = _D["arms"]["motor_mount_section_length"]
MOTOR_MOUNT_RECT = tuple(_D["motor"]["mount_bolt_pattern"])

# Motor mounting interface dimensions
MOTOR_BOLT_CIRCLE_D = _D["motor"]["mount_bolt_pattern"][0]  # 16 mm bolt circle
MOTOR_SHAFT_D       = _D["motor"]["shaft_diameter"]          # 3.17 mm
MOTOR_SHAFT_CLEAR   = 3.5                                    # shaft clearance hole
MOTOR_BASE_D        = _D["motor"]["base_plate_diameter"]     # 25 mm

M2_CLEAR_D          = 2.4   # M2 motor-bolt clearance hole
SLIDER_HOLE_D       = 2.2   # M2 clearance for slider/adjustment holes

CATALOG = {
    "arm": {
        "material": "FR4 Glass Epoxy", "thickness": f"{ARM_THICK}mm",
        "dims": f"{ARM_LENGTH:.0f} x {ARM_WIDTH} x {ARM_THICK} mm",
        "mass_g": 12, "qty": 4,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Modular two-section I-beam arm with adjustable overlap",
        "interface": "Tab press-fits into plate arm slots; motor bolts to tip",
    },
}

# ---------------------------------------------------------------------------
# Overlap / slider parameters
# ---------------------------------------------------------------------------
OVERLAP_LEN      = _D["arms"]["overlap_length"]
OVERLAP_HOLES    = max(2, int(OVERLAP_LEN / 10.0))
OVERLAP_HOLE_PITCH = OVERLAP_LEN / OVERLAP_HOLES

# The overlap zone is centred on the body mid-point (between tab end and
# motor section start) so that both sections are roughly equal in length.
_body_start = -ARM_LENGTH / 2 + MOUNT_FLANGE_LEN  # right edge of flange region
_body_end   =  ARM_LENGTH / 2 - MOTOR_SECTION   # left edge of motor section
_body_mid   = (_body_start + _body_end) / 2

OVERLAP_LEFT  = _body_mid - OVERLAP_LEN / 2   # X where overlap region starts
OVERLAP_RIGHT = _body_mid + OVERLAP_LEN / 2   # X where overlap region ends

# Adjustment hole positions — evenly spaced, inset from each edge by half pitch
_hole_inset  = OVERLAP_HOLE_PITCH / 2
_hole_span   = (OVERLAP_HOLES - 1) * OVERLAP_HOLE_PITCH
_hole_x0     = OVERLAP_LEFT + _hole_inset      # leftmost hole X

OVERLAP_HOLE_XS = [_hole_x0 + i * OVERLAP_HOLE_PITCH for i in range(OVERLAP_HOLES)]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cut_ibeam_flanges(body, x_left, x_right):
    """Remove the flanges (keeping only the web) over the X range [x_left, x_right].

    Used to make the inner section's overlap region web-only so it can slide
    inside the outer section's flanges.
    """
    cutout_len = x_right - x_left
    cutout_cx  = (x_left + x_right) / 2
    # Width of one flange pocket (from outer edge of web to outer edge of arm)
    flange_pocket_w = (ARM_WIDTH - ARM_WEB) / 2

    for side in [-1, 1]:
        cy = side * (ARM_WEB / 2 + flange_pocket_w / 2)
        flange_cut = (
            cq.Workplane("XY")
            .center(cutout_cx, cy)
            .rect(cutout_len, flange_pocket_w)
            .extrude(ARM_THICK)
        )
        body = body.cut(flange_cut)
    return body


def _cut_weight_relief(body, x_left, x_right):
    """Cut I-beam lightening pockets (between web and flanges) over the given X range."""
    cutout_len   = (x_right - x_left) - 10.0
    cutout_cx    = (x_left + x_right) / 2
    cutout_width = (ARM_WIDTH - ARM_WEB) / 2 - ARM_FLANGE   # = 5 mm

    if cutout_width > 1.0 and cutout_len > 1.0:
        for side in [-1, 1]:
            cy = side * (ARM_WEB / 2 + ARM_FLANGE + cutout_width / 2)
            pocket = (
                cq.Workplane("XY")
                .center(cutout_cx, cy)
                .rect(cutout_len, cutout_width)
                .extrude(ARM_THICK)
            )
            body = body.cut(pocket)
    return body


def _punch_slider_holes(body, hole_xs):
    """Punch M2 adjustment holes through the web at the given X positions."""
    for hx in hole_xs:
        hole = (
            cq.Workplane("XY")
            .center(hx, 0)
            .circle(SLIDER_HOLE_D / 2)
            .extrude(ARM_THICK)
        )
        body = body.cut(hole)
    return body


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def make_arm_inner():
    """Return the inner (flange) section of the modular arm.

    Spans from X = -ARM_LENGTH/2 (frame end) to X = OVERLAP_RIGHT.

    The first 30 mm (MOUNT_FLANGE_LEN) is a solid mounting flange — full arm
    width, full thickness, no I-beam cutouts.  Two rows of M2 clearance holes
    (2.2 mm dia) are drilled through the flange for bolting to the frame
    plate's radial rail.

    In the overlap zone (OVERLAP_LEFT to OVERLAP_RIGHT) the flanges are
    removed, leaving a bare web strip that slides between the outer section's
    flanges.  M2 adjustment holes are punched through the web in this zone.
    """
    inner_left  = -ARM_LENGTH / 2
    inner_right =  OVERLAP_RIGHT

    inner_len = inner_right - inner_left
    inner_cx  = (inner_left + inner_right) / 2

    # Base rectangular body for the inner section
    body = (
        cq.Workplane("XY")
        .center(inner_cx, 0)
        .rect(inner_len, ARM_WIDTH)
        .extrude(ARM_THICK)
    )

    # Weight-relief pockets in the non-overlap body region
    # (from right edge of mounting flange to left edge of overlap zone)
    relief_left  = inner_left + MOUNT_FLANGE_LEN
    relief_right = OVERLAP_LEFT
    body = _cut_weight_relief(body, relief_left, relief_right)

    # Overlap region: remove flanges, keep web only
    body = _cut_ibeam_flanges(body, OVERLAP_LEFT, OVERLAP_RIGHT)

    # M2 adjustment holes in the overlap web
    body = _punch_slider_holes(body, OVERLAP_HOLE_XS)

    hole_r = MOUNT_HOLE_D / 2
    first_hole_inset = 3.0
    available_span = MOUNT_FLANGE_LEN - 2 * first_hole_inset
    flange_hole_pitch = min(MOUNT_HOLE_PITCH, max(5.0, available_span))
    holes_per_row = max(1, int(available_span / flange_hole_pitch) + 1)
    actual_pitch = available_span / max(1, holes_per_row - 1) if holes_per_row > 1 else 0.0

    for side in [-1, 1]:
        hy = side * MOUNT_ROW_OFFSET
        for i in range(holes_per_row):
            hx = inner_left + first_hole_inset + i * actual_pitch
            h = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(hole_r)
                .extrude(ARM_THICK)
            )
            body = body.cut(h)

    anchors = {}
    if Anchor is not None:
        inner_left = -ARM_LENGTH / 2
        anchors["frame_end"] = Anchor(
            point=(inner_left, 0, 0),
            normal=(0, 0, -1),
            label="frame end (inner)",
        )
        anchors["overlap_end"] = Anchor(
            point=(OVERLAP_RIGHT, 0, ARM_THICK / 2),
            normal=(1, 0, 0),
            label="overlap end (inner)",
        )
        anchors["top_face"] = Anchor(
            point=(0, 0, ARM_THICK), normal=(0, 0, 1), label="top face (inner)"
        )
        anchors["bottom_face"] = Anchor(
            point=(0, 0, 0), normal=(0, 0, -1), label="bottom face (inner)"
        )

    return body, anchors


def make_arm_outer():
    """Return the outer (motor) section of the modular arm.

    Spans from X = OVERLAP_LEFT to X = +ARM_LENGTH/2 (motor tip).

    The overlap zone (OVERLAP_LEFT to OVERLAP_RIGHT) retains the full I-beam
    profile — the inner section's bare web slides between these flanges.
    M2 adjustment holes are punched through the web in the overlap zone to
    match the inner section's holes.

    The motor tip is a circular plate (motor base diameter) with a shaft
    clearance hole and four M2 bolt holes on the 16 mm bolt circle.
    """
    outer_left  = OVERLAP_LEFT
    outer_right =  ARM_LENGTH / 2

    outer_len = outer_right - outer_left
    outer_cx  = (outer_left + outer_right) / 2

    # Motor mount plate (circular, centred on motor section mid-point)
    mount_cx   = outer_right - MOTOR_SECTION / 2
    mount_plate = (
        cq.Workplane("XY")
        .center(mount_cx, 0)
        .circle(MOTOR_BASE_D / 2)
        .extrude(ARM_THICK)
    )

    # Base rectangular body for the outer section
    body = (
        cq.Workplane("XY")
        .center(outer_cx, 0)
        .rect(outer_len, ARM_WIDTH)
        .extrude(ARM_THICK)
    )

    # Union the circular motor plate
    body = body.union(mount_plate)

    # Weight-relief pockets in the non-overlap body region
    # (from right edge of overlap zone to left edge of motor section)
    relief_left  = OVERLAP_RIGHT
    relief_right = outer_right - MOTOR_SECTION
    body = _cut_weight_relief(body, relief_left, relief_right)

    # M2 adjustment holes in the overlap web (match inner section)
    body = _punch_slider_holes(body, OVERLAP_HOLE_XS)

    # Motor shaft clearance hole
    shaft_hole = (
        cq.Workplane("XY")
        .center(mount_cx, 0)
        .circle(MOTOR_SHAFT_CLEAR / 2)
        .extrude(ARM_THICK)
    )
    body = body.cut(shaft_hole)

    # 4x M2 mounting holes on 16 mm bolt circle (0, 90, 180, 270 deg)
    bolt_r = MOTOR_BOLT_CIRCLE_D / 2
    for angle_deg in [0, 90, 180, 270]:
        angle_rad = math.radians(angle_deg)
        hx = mount_cx + bolt_r * math.cos(angle_rad)
        hy = bolt_r * math.sin(angle_rad)
        hole = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(M2_CLEAR_D / 2)
            .extrude(ARM_THICK)
        )
        body = body.cut(hole)

    anchors = {}
    if Anchor is not None:
        outer_right = ARM_LENGTH / 2
        anchors["overlap_end"] = Anchor(
            point=(OVERLAP_LEFT, 0, ARM_THICK / 2),
            normal=(-1, 0, 0),
            label="overlap end (outer)",
        )
        anchors["motor_tip"] = Anchor(
            point=(outer_right, 0, ARM_THICK),
            normal=(0, 0, 1),
            label="motor tip (outer)",
        )
        anchors["top_face"] = Anchor(
            point=(0, 0, ARM_THICK), normal=(0, 0, 1), label="top face (outer)"
        )
        anchors["bottom_face"] = Anchor(
            point=(0, 0, 0), normal=(0, 0, -1), label="bottom face (outer)"
        )

    return body, anchors


def make_arm():
    """Return the complete arm as a single unioned solid (backward-compatible).

    Combines inner and outer sections at the default (maximum) arm length.
    The two sections are returned as a union so the result is identical in
    shape to the original single-piece arm (minus the small web-only overlap
    gap, which is filled by the outer section's flanges).
    """
    inner_result = make_arm_inner()
    outer_result = make_arm_outer()
    inner_shape = inner_result[0] if isinstance(inner_result, tuple) else inner_result
    outer_shape = outer_result[0] if isinstance(outer_result, tuple) else outer_result
    shape = inner_shape.union(outer_shape)

    anchors = {}
    if Anchor is not None:
        # frame_end: inner tip of arm, sits on plate top surface.
        # At drone radius ARM_CLEARANCE_R; motor_tip at MOTOR_R.
        anchors["frame_end"] = Anchor(
            point=(-ARM_LENGTH / 2, 0, 0),
            normal=(0, 0, -1),
            label="frame end (inner tip)",
        )
        anchors["motor_tip"] = Anchor(
            point=(ARM_LENGTH / 2, 0, ARM_THICK),
            normal=(0, 0, 1),
            label="motor tip",
        )
        # ESC mount: underside of arm at ESC_RADIAL_FRAC of motor radius.
        # Arm local x=0 is arm center. frame_end at -ARM_LENGTH/2 sits at
        # drone radius ARM_CLEARANCE_R. So local_x = drone_r - ARM_CLEARANCE_R - ARM_LENGTH/2.
        esc_radial_frac = _D["assembly"]["esc_radial_fraction"]
        esc_drone_r = MOTOR_R * esc_radial_frac
        esc_local_x = esc_drone_r - ARM_CLEARANCE_R - ARM_LENGTH / 2
        anchors["esc_mount"] = Anchor(
            point=(esc_local_x, 0, 0),
            normal=(0, 0, -1),
            label="ESC mount (underside)",
        )
        anchors["top_face"] = Anchor(
            point=(0, 0, ARM_THICK), normal=(0, 0, 1), label="top face"
        )
        anchors["bottom_face"] = Anchor(
            point=(0, 0, 0), normal=(0, 0, -1), label="bottom face"
        )

    return shape, anchors


# =============================================================================
# KiCad PCB generator
# =============================================================================

try:
    from cadquery_framework.kicad.primitives import (
        rect_outline, outline_to_sexpr, through_hole_pad,
        text_sexpr, kicad_pcb_wrapper,
    )
except ImportError:
    pass  # KiCad export not available


def generate_arm_pcb():
    """Generate .kicad_pcb for one motor arm (I-beam profile)."""
    segs = []

    # Outer rectangle
    segs.extend(rect_outline(ARM_LENGTH, ARM_WIDTH))

    # I-beam cutouts (two side channels)
    body_inner = -ARM_LENGTH / 2 + MOUNT_FLANGE_LEN
    body_outer = ARM_LENGTH / 2 - MOTOR_SECTION
    cutout_length = (body_outer - body_inner) - 10
    cutout_cx = (body_inner + body_outer) / 2
    cutout_width = (ARM_WIDTH - ARM_WEB) / 2 - ARM_FLANGE
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (ARM_WEB / 2 + ARM_FLANGE + cutout_width / 2)
            segs.extend(rect_outline(cutout_length, cutout_width, cutout_cx, cy))

    # Motor mount holes (4x M3)
    holes = []
    mx_center = ARM_LENGTH / 2 - MOTOR_SECTION / 2
    for dx in [-MOTOR_MOUNT_RECT[0] / 2, MOTOR_MOUNT_RECT[0] / 2]:
        for dy in [-MOTOR_MOUNT_RECT[1] / 2, MOTOR_MOUNT_RECT[1] / 2]:
            holes.append((mx_center + dx, dy))

    content = outline_to_sexpr(segs)
    for hx, hy in holes:
        content += "\n" + through_hole_pad(hx, hy, 3.2, 5.0)  # M3 clearance

    # Mounting flange bolt holes (2 rows of 3 M2 holes)
    flange_start_x = -ARM_LENGTH / 2 + 5.0  # 5mm from frame end
    for side in [-1, 1]:
        hy = side * 5.0  # +/-5mm from centerline
        for i in range(3):
            hx = flange_start_x + i * 10.0
            content += "\n" + through_hole_pad(hx, hy, 2.2, 4.0)  # M2 clearance

    content += "\n" + text_sexpr("ARM", 0, 0, "F.SilkS", 2, 0.2)
    content += "\n" + text_sexpr(f"{ARM_LENGTH:.0f}x{ARM_WIDTH:.0f}mm  FR4 {ARM_THICK:.1f}mm", 0, 4, "F.SilkS", 1.0, 0.12)

    return kicad_pcb_wrapper("Drone Motor Arm (I-Beam)", ARM_THICK, content)
