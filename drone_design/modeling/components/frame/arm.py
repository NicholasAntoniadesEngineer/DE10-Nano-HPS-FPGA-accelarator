"""I-beam skeleton arm with motor mounting plate, bolt holes, and plate header holes on tab."""

import math
import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

MOTOR_TO_MOTOR_DIAG = _D["arms"]["motor_to_motor_diagonal"]
MOTOR_R       = MOTOR_TO_MOTOR_DIAG / 2
ARM_TAB       = _D["arms"]["arm_tab"]
ARM_LENGTH    = MOTOR_R + ARM_TAB / 2
ARM_WIDTH     = _D["arms"]["arm_width"]
ARM_THICK     = _D["arms"]["arm_thickness"]
ARM_FLANGE    = _D["arms"]["arm_flange_width"]
ARM_WEB       = _D["arms"]["arm_web_width"]
MOTOR_SECTION = _D["arms"]["motor_mount_section_length"]
MOTOR_MOUNT_RECT = tuple(_D["motor"]["mount_bolt_pattern"])

# Motor mounting interface dimensions
MOTOR_BOLT_CIRCLE_D = _D["motor"]["mount_bolt_pattern"][0]  # 16mm inner bolt circle
MOTOR_SHAFT_D       = _D["motor"]["shaft_diameter"]          # 3.17mm
MOTOR_SHAFT_CLEAR   = 3.5                                    # clearance hole for shaft
MOTOR_BASE_D        = _D["motor"]["base_plate_diameter"]     # 25mm
M2_CLEAR_D          = 2.4                                    # M2 clearance hole diameter

# Pin header connection specs
HEADER_PITCH      = _D["connections"]["header_pitch"]
HEADER_HOLE_D     = _D["connections"]["header_hole_diameter"]
ARM_PINS_PER_SIDE = _D["connections"]["arm_header_pins_per_side"]
ARM_HEADER_OFFSET = _D["connections"]["arm_header_offset_from_slot"]


def make_arm():
    """Create an I-beam skeleton arm with motor mounting plate and header holes.

    The motor mount section (tip, positive-X end) is a solid flat plate wide
    enough to mount the motor, with a center shaft hole and 4x M2 bolt holes
    on the 16mm bolt circle.

    The tab region (inner end) has two rows of through-holes that align with
    matching holes on the frame plates for pin-header joints.
    """
    # --- Motor mounting plate at the tip ---
    # The mount plate is a circle (motor base diameter) centered on the motor
    # section, unioned with the main arm rectangle so the tip flares out
    # to accommodate the round motor base.
    mount_cx = ARM_LENGTH / 2 - MOTOR_SECTION / 2
    mount_plate = (
        cq.Workplane("XY")
        .center(mount_cx, 0)
        .circle(MOTOR_BASE_D / 2)
        .extrude(ARM_THICK)
    )

    # Main arm body (rectangular)
    arm = (
        cq.Workplane("XY")
        .rect(ARM_LENGTH, ARM_WIDTH)
        .extrude(ARM_THICK)
    )

    # Union the circular mount plate with the rectangular arm
    arm = arm.union(mount_plate)

    # I-beam cutouts (weight reduction in body section, between tab and mount)
    body_inner = -ARM_LENGTH / 2 + ARM_TAB
    body_outer = ARM_LENGTH / 2 - MOTOR_SECTION
    cutout_length = (body_outer - body_inner) - 10
    cutout_cx = (body_inner + body_outer) / 2
    cutout_width = (ARM_WIDTH - ARM_WEB) / 2 - ARM_FLANGE
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (ARM_WEB / 2 + ARM_FLANGE + cutout_width / 2)
            icut = (
                cq.Workplane("XY")
                .center(cutout_cx, cy)
                .rect(cutout_length, cutout_width)
                .extrude(ARM_THICK)
            )
            arm = arm.cut(icut)

    # --- Motor shaft center hole (3.5mm clearance) ---
    shaft_hole = (
        cq.Workplane("XY")
        .center(mount_cx, 0)
        .circle(MOTOR_SHAFT_CLEAR / 2)
        .extrude(ARM_THICK)
    )
    arm = arm.cut(shaft_hole)

    # --- 4x M2 mounting holes on 16mm bolt circle (0, 90, 180, 270 deg) ---
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
        arm = arm.cut(hole)

    # --- Pin header holes along tab (two rows, matching plate holes) ---
    hole_r = HEADER_HOLE_D / 2
    span = (ARM_PINS_PER_SIDE - 1) * HEADER_PITCH
    tab_cx = -ARM_LENGTH / 2 + ARM_TAB / 2

    for side in [-1, 1]:
        hy = side * ARM_HEADER_OFFSET
        for i in range(ARM_PINS_PER_SIDE):
            hx = tab_cx + (-span / 2 + i * HEADER_PITCH)
            hole = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(hole_r)
                .extrude(ARM_THICK)
            )
            arm = arm.cut(hole)

    return arm
