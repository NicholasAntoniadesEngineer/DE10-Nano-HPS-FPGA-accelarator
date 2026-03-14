#!/usr/bin/env python3
"""
Plant-Watering Drone — DE10-Nano — Parametric 3D Model (CadQuery)

Assembly orchestrator — imports self-contained component builders from
components/<category>/<part>.py and positions them into the full drone.

Each component file loads its own dimensions from cad/dimensions.json.
Assembly-level constants (cross-cutting placement dimensions) live in
components/assembly_constants.py and are re-exported here for backward
compatibility with export_stl.py and export_gerber.py.

Component layout:
    components/assembly_constants.py  ← shared placement constants
    components/frame/           skeleton_plate, arm, nose_boom
    components/landing_gear/    landing_leg
    components/propulsion/      motor, propeller, esc
    components/electronics/     de10_nano, daughter_board, standoff
    components/sensors/         tof_board, tof_bracket, camera
    components/payload/         battery, reservoir, pump, pump_bracket,
                                drip_nozzle, tubing

Usage:
    source .venv/bin/activate
    python drone_design/modeling/drone_3d_model.py

Output:
    drone_design/cad/exports/*.step  (individual parts + assembly)
"""

import sys
import math
import cadquery as cq
from pathlib import Path

# Add modeling/ to sys.path so components.* namespace packages resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ── Component builders (one file per part) ──────────────────────────────────
from components.frame.skeleton_plate import make_skeleton_plate
from components.frame.arm import make_arm
from components.frame.nose_boom import make_nose_boom
from components.landing_gear.landing_leg import make_landing_leg
from components.propulsion.motor import make_motor
from components.propulsion.propeller import make_propeller
from components.propulsion.esc import make_esc
from components.electronics.de10_nano import make_de10_nano
from components.electronics.daughter_board import make_daughter_board
from components.electronics.standoff import make_standoff
from components.sensors.tof_board import make_tof_board
from components.sensors.tof_bracket import make_tof_bracket, TOF_BRACKET_T, TOF_BRACKET_TAB, TOF_BRACKET_DEPTH
from components.sensors.camera import make_camera
from components.payload.battery import make_battery
from components.payload.reservoir import make_reservoir
from components.payload.pump import make_pump
from components.payload.pump_bracket import make_pump_bracket
from components.payload.drip_nozzle import make_drip_nozzle
from components.payload.tubing import make_tubing_segment

# ── Assembly-level constants ────────────────────────────────────────────────
# All cross-cutting placement dimensions live in assembly_constants.py.
# Re-exported here so existing importers (export_stl, export_gerber) still work.
from components.assembly_constants import *  # noqa: F401,F403
from components.assembly_constants import _D, _DIMS_PATH


# =============================================================================
# Assembly — position each part in the drone
# =============================================================================

def build_assembly():
    """Build the full drone assembly. All dimensions from cad/dimensions.json."""
    assy = cq.Assembly()

    # ── Bottom Plate ──
    assy.add(
        make_skeleton_plate(BOTTOM_THICK, is_bottom=True),
        loc=cq.Location((0, 0, BOTTOM_Z)),
        name="bottom_plate",
        color=cq.Color(0.72, 0.45, 0.2, 1.0)
    )

    # ── Top Plate ──
    assy.add(
        make_skeleton_plate(TOP_THICK, is_bottom=False),
        loc=cq.Location((0, 0, TOP_Z)),
        name="top_plate",
        color=cq.Color(0.1, 0.45, 0.15, 1.0)
    )

    # ── Arms (4x, X-config) ──
    arm = make_arm()
    arm_offset = ARM_LENGTH / 2 - ARM_TAB / 2

    for i, angle in enumerate(ARM_ANGLES):
        rad = math.radians(angle)
        cx = arm_offset * math.cos(rad)
        cy = arm_offset * math.sin(rad)
        assy.add(
            arm,
            loc=cq.Location(
                (cx, cy, ARM_CENTER_Z - ARM_THICK / 2),
                (0, 0, angle)
            ),
            name=f"arm_{i+1}",
            color=cq.Color(0.72, 0.45, 0.2, 1.0)
        )

    # ── Motors + Propellers + ESCs ──
    motor = make_motor()
    prop = make_propeller()
    esc = make_esc()

    for i, angle in enumerate(ARM_ANGLES):
        rad = math.radians(angle)
        mx = MOTOR_R * math.cos(rad)
        my = MOTOR_R * math.sin(rad)
        motor_z = ARM_CENTER_Z + ARM_THICK / 2

        assy.add(motor, loc=cq.Location((mx, my, motor_z)),
                 name=f"motor_{i+1}", color=cq.Color(0.2, 0.2, 0.2, 1.0))

        assy.add(prop, loc=cq.Location((mx, my, motor_z + MOTOR_TOTAL_H), (0, 0, angle + 30)),
                 name=f"prop_{i+1}", color=cq.Color(0.15, 0.15, 0.15, 0.5))

        esc_r = MOTOR_R * ESC_RADIAL_FRAC
        ex = esc_r * math.cos(rad)
        ey = esc_r * math.sin(rad)
        assy.add(esc, loc=cq.Location((ex, ey, ARM_CENTER_Z - ARM_THICK / 2 - ESC_H), (0, 0, angle)),
                 name=f"esc_{i+1}", color=cq.Color(0.1, 0.1, 0.1, 1.0))

    # ── Landing Gear ──
    # Leg vertical section center sits at radial distance = PLATE_SIZE/2 + LEG_THICK/2
    # so the inner face aligns with plate edge and the mounting tab extends inward
    leg = make_landing_leg()
    leg_radial_dist = PLATE_SIZE / 2 + LEG_THICK / 2
    for i, angle in enumerate(LEG_ANGLES):
        rad = math.radians(angle)
        lx = leg_radial_dist * math.cos(rad)
        ly = leg_radial_dist * math.sin(rad)
        assy.add(leg, loc=cq.Location((lx, ly, GROUND_Z), (0, 0, angle)),
                 name=f"leg_{i+1}", color=cq.Color(0.08, 0.35, 0.12, 1.0))

    # ── DE10-Nano ──
    assy.add(make_de10_nano(), loc=cq.Location((0, 0, DE10_Z)),
             name="de10_nano", color=cq.Color(0.0, 0.3, 0.6, 1.0))

    # ── Standoffs ──
    standoff = make_standoff(DE10_STANDOFF)
    for j, (dx, dy) in enumerate([
        (-DE10_W / 2 + 4, -DE10_L / 2 + 4),
        (-DE10_W / 2 + 4,  DE10_L / 2 - 4),
        ( DE10_W / 2 - 4, -DE10_L / 2 + 4),
        ( DE10_W / 2 - 4,  DE10_L / 2 - 4),
    ]):
        assy.add(standoff, loc=cq.Location((dx, dy, BOTTOM_Z + BOTTOM_THICK)),
                 name=f"standoff_{j+1}", color=cq.Color(0.75, 0.75, 0.78, 1.0))

    # ── Daughter Board ──
    assy.add(make_daughter_board(), loc=cq.Location((0, 0, DB_Z)),
             name="daughter_board", color=cq.Color(0.5, 0.1, 0.1, 1.0))

    # ── Battery (shifted rearward for CG balance) ──
    assy.add(make_battery(), loc=cq.Location((BATT_CG_OFFSET, 0, BOTTOM_Z - BATT_H - 3)),
             name="battery", color=cq.Color(0.15, 0.15, 0.15, 1.0))

    # ── Water delivery system ──
    # Layout: reservoir behind center (x=-15), pump bracket near boom root (x=45),
    # tubing connects reservoir→pump, then pump→boom→nozzle.

    # Reservoir — offset to +Y side to clear bottom ToF sensor at origin
    RES_L = _D["reservoir"]["length"]
    res_x = RES_OFFSET_X      # -15 (behind center)
    res_y = 25                 # offset to one side, clear of ToF down at (0,0)
    res_z = BOTTOM_Z - RES_H - 5
    assy.add(make_reservoir(), loc=cq.Location((res_x, res_y, res_z)),
             name="reservoir", color=cq.Color(0.3, 0.6, 0.9, 0.6))

    # Pump bracket — near boom root, other side of frame
    bracket_x = PLATE_SIZE / 2 - 15  # 45mm, near front edge
    bracket_y = -20                   # offset to opposite side from reservoir
    assy.add(make_pump_bracket(),
             loc=cq.Location((bracket_x, bracket_y, BOTTOM_Z), (180, 0, 0)),
             name="pump_bracket", color=cq.Color(0.1, 0.45, 0.15, 1.0))

    # Pump — mounted on bracket back wall
    pump_x = bracket_x
    pump_y = bracket_y + BRACKET_BASE_D / 2 + PUMP_BASE_H
    pump_z = BOTTOM_Z - BRACKET_T - BRACKET_BACK_H / 2
    assy.add(make_pump(),
             loc=cq.Location((pump_x, pump_y, pump_z), (90, 0, 0)),
             name="pump", color=cq.Color(0.3, 0.3, 0.3, 1.0))

    # ── Nose Boom ──
    boom_center_x = PLATE_SIZE / 2 + BOOM_LENGTH / 2
    boom_z = ARM_CENTER_Z - BOOM_THICK / 2
    assy.add(make_nose_boom(),
             loc=cq.Location((boom_center_x, 0, boom_z)),
             name="nose_boom", color=cq.Color(0.1, 0.45, 0.15, 1.0))

    # ── Camera (under boom, lens facing down) ──
    cam_x = PLATE_SIZE / 2 + 30
    assy.add(make_camera(), loc=cq.Location((cam_x, 0, boom_z - 2)),
             name="camera", color=cq.Color(0.1, 0.1, 0.1, 1.0))

    # ── Tubing: reservoir outlet → pump inlet ──
    # Reservoir outlet barb is on +Y face at mid-height
    res_outlet_x = res_x
    res_outlet_y = res_y + RES_L / 2  # +Y face of reservoir
    res_outlet_z = res_z + RES_H / 2
    dx = pump_x - res_outlet_x
    dy = pump_y - res_outlet_y
    dz = pump_z - res_outlet_z
    tube_res_pump_len = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(-dz, math.sqrt(dx ** 2 + dy ** 2)))
    assy.add(make_tubing_segment(tube_res_pump_len),
             loc=cq.Location((res_outlet_x, res_outlet_y, res_outlet_z),
                             (pitch, 0, yaw)),
             name="tubing_res_to_pump", color=cq.Color(0.8, 0.8, 0.85, 0.7))

    # ── Tubing: pump outlet → along boom to nozzle ──
    boom_tube_start_x = PLATE_SIZE / 2
    boom_tube_len = BOOM_LENGTH - 20
    assy.add(make_tubing_segment(boom_tube_len),
             loc=cq.Location((boom_tube_start_x, 0, boom_z - 4), (0, 90, 0)),
             name="tubing_boom", color=cq.Color(0.8, 0.8, 0.85, 0.7))

    # ── Drip nozzle (flange bolted to boom tip, body/cone pointing down) ──
    nozzle_x = PLATE_SIZE / 2 + BOOM_LENGTH
    assy.add(make_drip_nozzle(),
             loc=cq.Location((nozzle_x, 0, boom_z - BOOM_THICK / 2)),
             name="drip_nozzle", color=cq.Color(0.4, 0.4, 0.4, 1.0))

    # ── ToF Sensors (6 directions) ──
    tof = make_tof_board()
    assy.add(tof, loc=cq.Location((0, 0, BOTTOM_Z - TOF_H - 2), (180, 0, 0)),
             name="tof_down", color=cq.Color(0.6, 0.1, 0.6, 1.0))
    assy.add(tof, loc=cq.Location((0, 0, TOP_Z + TOP_THICK + 2)),
             name="tof_up", color=cq.Color(0.6, 0.1, 0.6, 1.0))
    assy.add(tof, loc=cq.Location((0, PLATE_SIZE / 2, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (90, 0, 0)),
             name="tof_front", color=cq.Color(0.6, 0.1, 0.6, 1.0))
    assy.add(tof, loc=cq.Location((0, -PLATE_SIZE / 2 + 5, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (-90, 0, 0)),
             name="tof_back", color=cq.Color(0.6, 0.1, 0.6, 1.0))
    assy.add(tof, loc=cq.Location((-PLATE_SIZE / 2, 0, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (0, -90, 0)),
             name="tof_left", color=cq.Color(0.6, 0.1, 0.6, 1.0))
    assy.add(tof, loc=cq.Location((PLATE_SIZE / 2, 0, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (0, 90, 0)),
             name="tof_right", color=cq.Color(0.6, 0.1, 0.6, 1.0))

    return assy


# =============================================================================
# Export (when run directly)
# =============================================================================

def main():
    out_dir = Path(__file__).resolve().parent.parent / "cad" / "exports" / "step"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"DIMENSIONS SOURCE: {_DIMS_PATH}")
    print("=" * 60)
    print(f"  Motor-to-motor diagonal:     {MOTOR_TO_MOTOR_DIAG:.1f} mm")
    print(f"  Motor distance from center:  {MOTOR_R:.1f} mm")
    print(f"  Adjacent motor distance:     {ADJ_MOTOR_DIST:.1f} mm")
    print(f"  Prop diameter (10\"):          {PROP_DIAMETER:.1f} mm")
    print(f"  Adjacent prop clearance:     {ADJ_MOTOR_DIST - PROP_DIAMETER:.1f} mm")
    arm_offset = ARM_LENGTH / 2 - ARM_TAB / 2
    arm_tip = arm_offset + ARM_LENGTH / 2
    print(f"  Arm tip from center:         {arm_tip:.2f} mm (should = {MOTOR_R})")
    print(f"  Arm total length:            {ARM_LENGTH:.2f} mm")
    print("=" * 60)

    print("\nBuilding drone assembly...")
    assy = build_assembly()

    assy_path = out_dir / "drone_assembly.step"
    print(f"Exporting assembly -> {assy_path}")
    assy.save(str(assy_path))

    pieces = {
        "bottom_plate": (make_skeleton_plate, (BOTTOM_THICK, True)),
        "top_plate": (make_skeleton_plate, (TOP_THICK, False)),
        "arm": (make_arm, ()),
        "landing_leg": (make_landing_leg, ()),
        "tof_board": (make_tof_board, ()),
        "pump_bracket": (make_pump_bracket, ()),
    }

    for name, (func, args) in pieces.items():
        path = out_dir / f"{name}.step"
        print(f"Exporting {name} -> {path}")
        part = func(*args)
        cq.exporters.export(part, str(path))

    print(f"\nDone! Files in: {out_dir}/")


if __name__ == "__main__":
    main()
