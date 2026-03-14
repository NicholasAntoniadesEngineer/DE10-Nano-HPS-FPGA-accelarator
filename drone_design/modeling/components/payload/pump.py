"""Kamoer NKP-DC-S06B peristaltic pump — 6V DC, silicone tube, 35ml/min.

Geometry: rectangular base with mounting ears, cylindrical motor section,
larger cylindrical pump head with visible rotor housing, two barbed tube
fittings on top (inlet/outlet), and a wire exit at the motor rear.
"""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())
_P = _D["pump"]

MOTOR_D          = _P["motor_diameter"]
MOTOR_L          = _P["motor_length"]
HEAD_D           = _P["pump_head_diameter"]
HEAD_L           = _P["pump_head_length"]
ROTOR_D          = _P["rotor_housing_diameter"]
ROTOR_DEPTH      = _P["rotor_housing_depth"]
BASE_W           = _P["base_width"]
BASE_DEPTH       = _P["base_depth"]
BASE_H           = _P["base_height"]
EAR_W            = _P["mounting_ear_width"]
EAR_EXT          = _P["mounting_ear_extension"]
MOUNT_HOLE_D     = _P["mounting_hole_diameter"]
FITTING_OD       = _P["tube_fitting_od"]
FITTING_ID       = _P["tube_fitting_id"]
FITTING_L        = _P["tube_fitting_length"]
BARB_OD          = _P["tube_fitting_barb_od"]
BARB_H           = _P["tube_fitting_barb_height"]
FITTING_SPACING  = _P["tube_fitting_spacing"]
WIRE_D           = _P["wire_exit_diameter"]

TOTAL_L = MOTOR_L + HEAD_L  # 54.5mm


def _make_barb_fitting(height):
    """Single barbed tube fitting — hollow cylinder with barb ring."""
    outer = cq.Workplane("XY").circle(FITTING_OD / 2).extrude(height)
    # Hollow bore
    bore = cq.Workplane("XY").circle(FITTING_ID / 2).extrude(height)
    fitting = outer.cut(bore)
    # Two barb rings for grip
    for z_off in [height * 0.3, height * 0.65]:
        barb = (
            cq.Workplane("XY")
            .workplane(offset=z_off)
            .circle(BARB_OD / 2)
            .extrude(BARB_H)
        )
        fitting = fitting.union(barb)
    return fitting


def make_pump():
    """Kamoer NKP-DC-S06B peristaltic pump with mounting ears and barb fittings."""

    # --- Flat rectangular base (mounting platform) ---
    base = (
        cq.Workplane("XY")
        .rect(BASE_W, BASE_DEPTH)
        .extrude(BASE_H)
    )

    # --- Mounting ears — extend from base sides with M3 through-holes ---
    ear_total_w = BASE_W + 2 * EAR_EXT
    ears = (
        cq.Workplane("XY")
        .rect(ear_total_w, EAR_W)
        .extrude(BASE_H)
    )
    # Punch mounting holes in ears
    for sx in [-1, 1]:
        hx = sx * (BASE_W / 2 + EAR_EXT / 2)
        hole = (
            cq.Workplane("XY")
            .center(hx, 0)
            .circle(MOUNT_HOLE_D / 2)
            .extrude(BASE_H)
        )
        ears = ears.cut(hole)
    base = base.union(ears)

    # --- Motor section — cylinder sitting on base, aligned along Y axis ---
    motor_cy = -BASE_DEPTH / 2 + MOTOR_L / 2
    motor = (
        cq.Workplane("XZ")
        .center(0, BASE_H + MOTOR_D / 2)
        .circle(MOTOR_D / 2)
        .extrude(MOTOR_L)
        .translate((0, -BASE_DEPTH / 2, 0))
    )
    base = base.union(motor)

    # --- Pump head — larger cylinder, forward of motor ---
    head = (
        cq.Workplane("XZ")
        .center(0, BASE_H + MOTOR_D / 2)
        .circle(HEAD_D / 2)
        .extrude(HEAD_L)
        .translate((0, -BASE_DEPTH / 2 + MOTOR_L, 0))
    )
    base = base.union(head)

    # --- Rotor housing ring — visible on front face of pump head ---
    rotor_face_y = -BASE_DEPTH / 2 + MOTOR_L + HEAD_L
    rotor_ring = (
        cq.Workplane("XZ")
        .center(0, BASE_H + MOTOR_D / 2)
        .circle(ROTOR_D / 2)
        .circle(ROTOR_D / 2 - 2)
        .extrude(ROTOR_DEPTH)
        .translate((0, rotor_face_y - ROTOR_DEPTH, 0))
    )
    base = base.union(rotor_ring)

    # --- Tube fittings — two barbed fittings on top of pump head ---
    head_top_z = BASE_H + MOTOR_D / 2 + HEAD_D / 2
    head_center_y = -BASE_DEPTH / 2 + MOTOR_L + HEAD_L / 2
    fitting = _make_barb_fitting(FITTING_L)

    for dx in [-FITTING_SPACING / 2, FITTING_SPACING / 2]:
        placed = fitting.translate((dx, head_center_y, head_top_z))
        base = base.union(placed)

    # --- Wire exit — small cylinder at motor rear ---
    wire_exit = (
        cq.Workplane("XZ")
        .center(0, BASE_H + MOTOR_D / 2)
        .circle(WIRE_D / 2)
        .extrude(3)
        .translate((0, -BASE_DEPTH / 2 - 3, 0))
    )
    base = base.union(wire_exit)

    return base
