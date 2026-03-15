"""SunnySky X2212 980KV brushless motor with mounting bolt holes."""

import math
import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

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

CATALOG = {
    "motor": {
        "material": "Aluminum + copper windings",
        "dims": "\u00d827.5 x 26mm body + 13mm shaft",
        "mass_g": 56, "qty": 4,
        "supplier": "SunnySky X2212 980KV",
        "notes": "Outrunner BLDC, 980KV, max thrust ~800g/motor at 4S",
        "interface": "4x M3 bolts to arm tip; 3-phase wires to ESC",
    },
}


def _make_anchors():
    """Build anchor dict (shared across all detail levels)."""
    bolt_r = MOTOR_BOLT_CIRCLE_D / 2
    anchors = {}
    if Anchor is not None:
        anchors["base_mount"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Motor base mounting surface")
        anchors["shaft_tip"] = Anchor(point=(0, 0, MOTOR_TOTAL_H), normal=(0, 0, 1), label="Shaft tip for propeller attachment")
        for i, angle_deg in enumerate([0, 90, 180, 270], start=1):
            angle_rad = math.radians(angle_deg)
            bx = bolt_r * math.cos(angle_rad)
            by = bolt_r * math.sin(angle_rad)
            anchors[f"bolt_hole_{i}"] = Anchor(point=(bx, by, 0), normal=(0, 0, -1), label=f"M2 bolt hole {i} at {angle_deg} deg")
    return anchors


def _make_envelope():
    """Simple bounding cylinder for the motor."""
    motor = cq.Workplane("XY").circle(MOTOR_BELL_OD / 2).extrude(MOTOR_TOTAL_H)
    return motor


def _make_assembly():
    """Assembly-level motor (original geometry)."""
    bolt_r = MOTOR_BOLT_CIRCLE_D / 2

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


def _make_detailed():
    """Detailed motor with stator teeth, vent slots, bearing bore, wire terminals, prop adapter."""
    det = _D["motor"]["detailed"]
    bolt_r = MOTOR_BOLT_CIRCLE_D / 2
    bell_r = MOTOR_BELL_OD / 2
    wall_t = _D["motor"]["bell_wall_thickness"]
    stator_d = _D["motor"]["stator_diameter"]
    stator_h = _D["motor"]["stator_height"]

    # --- Base plate with edge chamfer ---
    base = cq.Workplane("XY").circle(MOTOR_BASE_D / 2).extrude(BASE_H)
    base = base.edges("|Z").chamfer(0.5)

    # --- Bell (hollow cylinder) ---
    bell = (
        cq.Workplane("XY")
        .circle(bell_r)
        .circle(bell_r - wall_t)
        .extrude(MOTOR_BODY_H)
    )
    # Solid cap on top
    cap = (
        cq.Workplane("XY")
        .workplane(offset=MOTOR_BODY_H - 3)
        .circle(bell_r)
        .extrude(3)
    )
    bell = bell.union(cap)

    # --- Vent slots cut into bell wall ---
    vent_count = det["vent_slot_count"]
    vent_w = det["vent_slot_width"]
    vent_h = det["vent_slot_height"]
    vent_z_center = MOTOR_BODY_H / 2
    for i in range(vent_count):
        angle = math.radians(i * 360.0 / vent_count)
        cx = (bell_r) * math.cos(angle)
        cy = (bell_r) * math.sin(angle)
        slot = (
            cq.Workplane("XY")
            .workplane(offset=vent_z_center - vent_h / 2)
            .center(cx, cy)
            .rect(vent_w, wall_t * 3)
            .extrude(vent_h)
        )
        # Rotate the slot to be radially oriented
        slot = slot.rotateAboutCenter((0, 0, 1), math.degrees(angle))
        bell = bell.cut(slot)

    motor = base.union(bell)
    motor = motor.faces(">Z").chamfer(1.5)

    # --- Shaft ---
    shaft = cq.Workplane("XY").circle(MOTOR_SHAFT_D / 2).extrude(MOTOR_TOTAL_H)
    motor = motor.union(shaft)

    # --- Prop adapter on top of shaft ---
    adapter_d = det["prop_adapter_diameter"]
    adapter_h = det["prop_adapter_height"]
    adapter = (
        cq.Workplane("XY")
        .workplane(offset=MOTOR_BODY_H)
        .circle(adapter_d / 2)
        .extrude(adapter_h)
    )
    motor = motor.union(adapter)

    # --- Stator with radial teeth (inside the bell) ---
    stator_r = stator_d / 2
    tooth_count = det["stator_tooth_count"]
    tooth_w = det["stator_tooth_width"]
    tooth_depth = det["stator_tooth_depth"]
    # Stator core ring
    stator_core_ir = MOTOR_SHAFT_D / 2 + 1.0
    stator_core = (
        cq.Workplane("XY")
        .workplane(offset=BASE_H)
        .circle(stator_core_ir + 2.0)
        .circle(stator_core_ir)
        .extrude(stator_h)
    )
    motor = motor.union(stator_core)
    # Radial teeth extending from core to near bell inner wall
    for i in range(tooth_count):
        angle = math.radians(i * 360.0 / tooth_count)
        # Tooth center radial position
        tooth_r_center = stator_core_ir + 2.0 + tooth_depth / 2
        tx = tooth_r_center * math.cos(angle)
        ty = tooth_r_center * math.sin(angle)
        tooth = (
            cq.Workplane("XY")
            .workplane(offset=BASE_H)
            .center(tx, ty)
            .rect(tooth_depth, tooth_w)
            .extrude(stator_h)
        )
        tooth = tooth.rotateAboutCenter((0, 0, 1), math.degrees(angle))
        motor = motor.union(tooth)

    # --- Bearing bore recess on base plate bottom ---
    bore_d = det["bearing_bore_diameter"]
    bore_depth = det["bearing_bore_depth"]
    bore_cut = (
        cq.Workplane("XY")
        .workplane(offset=-bore_depth)
        .circle(bore_d / 2)
        .extrude(bore_depth)
    )
    motor = motor.cut(bore_cut)

    # --- Wire terminal stubs on base plate edge ---
    wire_count = det["wire_terminal_count"]
    wire_d = det["wire_diameter"]
    for i in range(wire_count):
        angle = math.radians(i * 360.0 / wire_count + 30)  # offset 30deg from bolt holes
        wx = (MOTOR_BASE_D / 2) * math.cos(angle)
        wy = (MOTOR_BASE_D / 2) * math.sin(angle)
        wire = (
            cq.Workplane("XY")
            .center(wx, wy)
            .circle(wire_d / 2)
            .extrude(-3.0)
        )
        motor = motor.union(wire)

    # --- 4x M2 bolt holes ---
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


def make_motor(detail="assembly"):
    """SunnySky X2212 980KV brushless motor with base plate bolt holes.

    Parameters
    ----------
    detail : str
        Level of geometric detail: ``"envelope"``, ``"assembly"`` (default),
        or ``"detailed"``.
    """
    if detail == "envelope":
        motor = _make_envelope()
    elif detail == "detailed":
        motor = _make_detailed()
    else:
        motor = _make_assembly()

    return motor, _make_anchors()
