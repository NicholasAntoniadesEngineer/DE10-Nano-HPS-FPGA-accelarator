"""Modular two-section I-beam arm with adjustable motor distance.

The arm is split into two interlocking sections:

  Inner section  — contains a bolt-on mounting flange (30 mm) at the frame end
                   and the main I-beam body.  The flange has two rows of M2
                   clearance holes for bolting to the frame plate's radial rail.
                   In the overlap region the flanges are omitted so the inner
                   web can slide *between* the outer section's flanges.

  Outer section  — contains the circular motor mounting plate at the tip and
                   a full I-beam body.  The overlap region keeps its full
                   I-beam profile; the inner web nests inside these flanges.

Overlap mechanics
-----------------
* Overlap length : OVERLAP_LEN = 40 mm
* M2 clearance holes (2.2 mm dia) every 10 mm along the web of both sections
  in the overlap zone — bolt through whichever pair aligns at the desired arm
  length.
* Effective arm length range: ARM_LENGTH (default/maximum) down to
  ARM_LENGTH - OVERLAP_LEN + 10 mm (one-hole minimum engagement).

Mounting flange
---------------
* 30 mm long, full arm width (25 mm), full thickness — no I-beam cutouts.
* 2 rows of M2 clearance holes (2.2 mm dia) at +/-5 mm from arm centerline.
* 3 holes per row at 10 mm pitch, starting 5 mm from the frame end (6 total).
* User bolts 2-4 holes through matching holes on the frame plate's radial rail.

Coordinate system
-----------------
Both functions return geometry centred on the **full-length arm origin**
(X = 0 is the arm mid-point) so they can be positioned identically in an
assembly.  The flange/inner end is at X = -ARM_LENGTH/2; the motor tip is at
X = +ARM_LENGTH/2.
"""

import math
import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

MOTOR_TO_MOTOR_DIAG = _D["arms"]["motor_to_motor_diagonal"]
MOTOR_R       = MOTOR_TO_MOTOR_DIAG / 2

# Mounting flange parameters (replaces old press-fit tab)
MOUNT_FLANGE_LEN  = 30.0   # mm — length of the bolt-on mounting flange
MOUNT_HOLE_D      = 2.2    # mm — M2 clearance hole diameter
MOUNT_ROW_OFFSET  = 5.0    # mm — perpendicular offset from arm centerline
MOUNT_HOLE_PITCH  = 10.0   # mm — along-arm spacing between mounting holes

ARM_LENGTH    = MOTOR_R + MOUNT_FLANGE_LEN / 2
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

# ---------------------------------------------------------------------------
# Overlap / slider parameters
# ---------------------------------------------------------------------------
OVERLAP_LEN      = 40.0   # mm — length of the sliding overlap region
OVERLAP_HOLES    = 4      # number of M2 adjustment holes in the overlap zone
OVERLAP_HOLE_PITCH = 10.0 # mm — spacing between adjustment holes

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
    flange_pocket_w = (ARM_WIDTH - ARM_WEB) / 2   # = (25 - 3) / 2 = 11 mm

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

    # Mounting flange bolt holes — 2 rows of 3 holes (6 total)
    # Rows at +/-MOUNT_ROW_OFFSET from centerline, holes spaced at
    # MOUNT_HOLE_PITCH along arm length starting 5 mm from frame end.
    hole_r = MOUNT_HOLE_D / 2
    holes_per_row = 3
    first_hole_offset = 5.0  # mm from the frame end

    for side in [-1, 1]:
        hy = side * MOUNT_ROW_OFFSET
        for i in range(holes_per_row):
            hx = inner_left + first_hole_offset + i * MOUNT_HOLE_PITCH
            h = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(hole_r)
                .extrude(ARM_THICK)
            )
            body = body.cut(h)

    return body


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

    return body


def make_arm():
    """Return the complete arm as a single unioned solid (backward-compatible).

    Combines inner and outer sections at the default (maximum) arm length.
    The two sections are returned as a union so the result is identical in
    shape to the original single-piece arm (minus the small web-only overlap
    gap, which is filled by the outer section's flanges).
    """
    return make_arm_inner().union(make_arm_outer())
