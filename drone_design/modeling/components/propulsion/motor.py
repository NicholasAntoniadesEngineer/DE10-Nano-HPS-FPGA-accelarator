"""SunnySky X2212 980KV brushless motor."""

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


def make_motor():
    """SunnySky X2212 980KV brushless motor."""
    base = cq.Workplane("XY").circle(MOTOR_BASE_D / 2).extrude(3)
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
    return motor.union(shaft)
