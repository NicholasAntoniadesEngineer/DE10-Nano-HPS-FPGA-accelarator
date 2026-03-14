"""I-beam skeleton arm with motor mount holes at the tip."""

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


def make_arm():
    """Create an I-beam skeleton arm with motor mount holes at the tip."""
    arm = (
        cq.Workplane("XY")
        .rect(ARM_LENGTH, ARM_WIDTH)
        .extrude(ARM_THICK)
    )

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

    mx_center = ARM_LENGTH / 2 - MOTOR_SECTION / 2
    for dx in [-MOTOR_MOUNT_RECT[0]/2, MOTOR_MOUNT_RECT[0]/2]:
        for dy in [-MOTOR_MOUNT_RECT[1]/2, MOTOR_MOUNT_RECT[1]/2]:
            hole = (
                cq.Workplane("XY")
                .center(mx_center + dx, dy)
                .circle(1.6)
                .extrude(ARM_THICK)
            )
            arm = arm.cut(hole)

    return arm
