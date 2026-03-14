"""SunnySky X2212 980KV brushless motor with mounting bolt holes."""

import math
import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

MOTOR_BELL_OD  = _D["motor"]["bell_outer_diameter"]
MOTOR_BODY_H   = _D["motor"]["body_height"]
MOTOR_SHAFT_D  = _D["motor"]["shaft_diameter"]
MOTOR_SHAFT_H  = _D["motor"]["shaft_protrusion"]
MOTOR_TOTAL_H  = MOTOR_BODY_H + MOTOR_SHAFT_H
MOTOR_BASE_D   = _D["motor"]["base_plate_diameter"]
MOTOR_BOLT_CIRCLE_D = _D["motor"]["mount_bolt_pattern"][0]  # 16mm inner bolt circle

# Base plate height (the flat mounting portion below the bell)
BASE_H = 3.0
# M2 bolt hole diameter (matching arm M2 clearance holes)
M2_THREAD_D = 2.0


def make_motor():
    """SunnySky X2212 980KV brushless motor with base plate bolt holes.

    The base plate has 4x M2 threaded holes on the 16mm bolt circle at
    0, 90, 180, 270 degrees, matching the arm mounting plate pattern.
    """
    base = cq.Workplane("XY").circle(MOTOR_BASE_D / 2).extrude(BASE_H)
    bell = (
        cq.Workplane("XY")
        .circle(MOTOR_BELL_OD / 2)
        .circle(MOTOR_BELL_OD / 2 - 1.5)
        .extrude(MOTOR_BODY_H)
    )
    cap = (
        cq.Workplane("XY")
        .workplane(offset=MOTOR_BODY_H - 3)
        .circle(MOTOR_BELL_OD / 2)
        .extrude(3)
    )
    bell = bell.union(cap)
    motor = base.union(bell)
    motor = motor.faces(">Z").chamfer(1.5)
    shaft = cq.Workplane("XY").circle(MOTOR_SHAFT_D / 2).extrude(MOTOR_TOTAL_H)
    motor = motor.union(shaft)

    # 4x M2 mounting bolt holes through the base plate (16mm bolt circle)
    bolt_r = MOTOR_BOLT_CIRCLE_D / 2
    for angle_deg in [0, 90, 180, 270]:
        angle_rad = math.radians(angle_deg)
        hx = bolt_r * math.cos(angle_rad)
        hy = bolt_r * math.sin(angle_rad)
        hole = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(M2_THREAD_D / 2)
            .extrude(BASE_H)
        )
        motor = motor.cut(hole)

    return motor
