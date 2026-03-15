"""
Drone assembly manifest using constraint-based AssemblyBuilder.

Every part is positioned via physical mating constraints (mate/offset) using
anchor-to-anchor connections.  Only root plates use absolute placement.
Tubing segments use computed routing (absolute) as they are flexible.

Usage:
    from assembly.manifest import build_drone_manifest
    manifest = build_drone_manifest()
"""

import math
import sys
from pathlib import Path

_DRONE_MODEL = Path(__file__).resolve().parent.parent
_REPO_ROOT = _DRONE_MODEL.parent.parent
sys.path.insert(0, str(_DRONE_MODEL))
sys.path.insert(0, str(_REPO_ROOT))

from cadquery_framework.assembly.anchors import Anchor, AssemblyBuilder

# Component builders
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
from components.sensors.tof_bracket import (
    make_tof_bracket, TOF_BRACKET_T, TOF_BRACKET_TAB, TOF_BRACKET_DEPTH,
)
from components.sensors.camera import make_camera
from components.sensors.camera_bracket import (
    make_camera_bracket, CAM_BRACKET_TAB_H, CAM_BRACKET_T,
)
from components.payload.battery import make_battery
from components.payload.reservoir import make_reservoir
from components.payload.pump import make_pump
from components.payload.pump_bracket import make_pump_bracket
from components.payload.drip_nozzle import make_drip_nozzle
from components.payload.tubing import make_tubing_segment

# Assembly-level constants
from components.assembly_constants import (
    _D,
    BOTTOM_THICK, TOP_THICK, DE10_STANDOFF,
    PLATE_SIZE, PLATE_SPACING,
    MOTOR_R, ARM_LENGTH, ARM_WIDTH, ARM_THICK, ARM_ANGLES, ARM_CLEARANCE_R,
    MOTOR_TOTAL_H, ESC_H, ESC_RADIAL_FRAC,
    LEG_ANGLES, LEG_THICK,
    DE10_W, DE10_L, DE10_H,
    BATT_H, BATT_CG_OFFSET,
    RES_H, RES_OFFSET_X,
    BOOM_LENGTH, BOOM_THICK, BOOM_WIDTH,
    TOF_H, TOF_L,
    GROUND_Z, BOTTOM_Z, TOP_Z, DE10_Z, DB_Z, ARM_CENTER_Z,
    UNDERSLUNG_GAP, RES_OFFSET_Y, BRACKET_OFFSET_X, BRACKET_OFFSET_Y,
    BATT_ROTATION_DEG, CAMERA_BOOM_OFFSET,
    BRACKET_T, DB_ABOVE_DE10,
)


# ============================================================================
# Component catalog — metadata for each part type
# ============================================================================

COMPONENT_CATALOG = {
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
    "arm": {
        "material": "FR4 Glass Epoxy", "thickness": f"{ARM_THICK}mm",
        "dims": f"{ARM_LENGTH:.0f} x {ARM_WIDTH} x {ARM_THICK} mm",
        "mass_g": 12, "qty": 4,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Modular two-section I-beam arm with adjustable overlap",
        "interface": "Tab press-fits into plate arm slots; motor bolts to tip",
    },
    "motor": {
        "material": "Aluminum + copper windings",
        "dims": "\u00d827.5 x 26mm body + 13mm shaft",
        "mass_g": 56, "qty": 4,
        "supplier": "SunnySky X2212 980KV",
        "notes": "Outrunner BLDC, 980KV, max thrust ~800g/motor at 4S",
        "interface": "4x M3 bolts to arm tip; 3-phase wires to ESC",
    },
    "propeller": {
        "material": "Glass-filled nylon",
        "dims": "\u00d8254mm (10 inch), 4.5 inch pitch",
        "mass_g": 14, "qty": 4,
        "supplier": "GemFan 1045",
        "notes": "2-blade, CW/CCW pairs. ~800g thrust at full throttle",
        "interface": "Press-fit/collet on 3.17mm motor shaft",
    },
    "esc": {
        "material": "FR4 PCB + MOSFETs",
        "dims": "35 x 17 x 5.5 mm",
        "mass_g": 8, "qty": 4,
        "supplier": "FVT LittleBee 30A BLHeli_32",
        "notes": "30A continuous, DShot600 input, BLHeli_32 firmware",
        "interface": "3-phase output to motor; signal wire to FPGA GPIO",
    },
    "landing_leg": {
        "material": "FR4 Glass Epoxy", "thickness": "2.0mm",
        "dims": "L-shape: 20x80mm vertical + 40mm foot",
        "mass_g": 8, "qty": 4,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "L-shaped with 3x capsule lightening holes",
        "interface": "Bolts to bottom plate edge",
    },
    "de10_nano": {
        "material": "FR4 PCB + components",
        "dims": f"{DE10_W:.1f} x {DE10_L:.1f} x 1.6mm PCB (17mm tallest)",
        "mass_g": 65, "qty": 1,
        "supplier": "Terasic DE10-Nano",
        "notes": "Cyclone V SoC: dual ARM Cortex-A9 800MHz + 41K ALM FPGA",
        "interface": "4x M2.5 standoffs to bottom plate; GPIO for sensors+motors",
    },
    "standoff": {
        "material": "Brass, nickel plated",
        "dims": f"M2.5 x {DE10_STANDOFF}mm",
        "mass_g": 2, "qty": 4,
        "supplier": "Generic M2.5 hex standoff",
        "notes": "Female-female hex standoff, separates DE10-Nano from bottom plate",
        "interface": "M2.5 bolt through bottom plate into standoff",
    },
    "daughter_board": {
        "material": "FR4 PCB + components",
        "dims": "85 x 100 x 1.6mm",
        "mass_g": 35, "qty": 1,
        "supplier": "Custom PCB (JLCPCB)",
        "notes": "Sensor hub: level shifter, I2C mux, barometer, power regulators",
        "interface": "Stacks above DE10-Nano on standoffs",
    },
    "battery": {
        "material": "Lithium polymer cells",
        "dims": "106 x 35 x 30mm",
        "mass_g": 192, "qty": 1,
        "supplier": "Tattu 2200mAh 4S 45C",
        "notes": "14.8V nominal, 45C discharge, ~8-12 min flight time",
        "interface": "XT60 connector to power distribution",
    },
    "reservoir": {
        "material": "TPU (thermoplastic polyurethane)",
        "dims": "50 x 80 x 40mm (300ml capacity)",
        "mass_g": 25, "qty": 1,
        "supplier": "Custom bladder",
        "notes": "Collapsible water reservoir, gravity-fed to pump",
        "interface": "Silicone tubing to pump inlet",
    },
    "pump_bracket": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm",
        "dims": "25 x 40 x 1.6mm",
        "mass_g": 3, "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "L-bracket to mount peristaltic pump",
        "interface": "Bolts to bottom plate; pump screws to bracket",
    },
    "pump": {
        "material": "POM housing + DC motor + silicone tubing",
        "dims": "64 x 38 x 30mm",
        "mass_g": 85, "qty": 1,
        "supplier": "Takasago RP-Q1",
        "notes": "3V DC peristaltic pump, 0.2-3.0 ml/min, 11g, ring-drive",
        "interface": "Tubing from reservoir; outlet to drip nozzle",
    },
    "nose_boom": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm",
        "dims": f"{BOOM_LENGTH} x {BOOM_WIDTH} x 1.6mm",
        "mass_g": 18, "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Modular two-section I-beam boom with adjustable overlap",
        "interface": "Root bolts to frame; nozzle at tip",
    },
    "camera": {
        "material": "FR4 PCB + CMOS sensor + lens",
        "dims": "25 x 30 x 1.6mm PCB + lens barrel",
        "mass_g": 8, "qty": 1,
        "supplier": "Custom adapter PCB + OV5640 module",
        "notes": "OV5640 5MP camera, 1080p@30fps, DVP parallel mode",
        "interface": "16-pin ribbon to GPIO0; 5V from header",
    },
    "drip_nozzle": {
        "material": "Brass + stainless steel",
        "dims": "\u00d86 x 15mm",
        "mass_g": 5, "qty": 1,
        "supplier": "Generic drip irrigation nozzle",
        "notes": "Adjustable drip nozzle, 0-60ml/min",
        "interface": "Barb press-fit into silicone tubing",
    },
    "tof_sensor": {
        "material": "FR4 PCB + VL53L1X VCSEL module",
        "dims": "13 x 18 x 2mm board + 2.5mm sensor",
        "mass_g": 1.5, "qty": 6,
        "supplier": "Pololu #3415 (VL53L1X carrier)",
        "notes": "Time-of-Flight laser ranging, 4m max, 50Hz, I2C",
        "interface": "I2C via TCA9548A mux on daughter board",
    },
    "tof_bracket": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm",
        "dims": "15 x 20 x 15mm L-shape",
        "mass_g": 1.0, "qty": 6,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "L-shaped bracket for VL53L1X ToF sensor",
        "interface": "2x M2 to frame plate; 2x M2 to ToF board",
    },
}


# ============================================================================
# Assembly manifest builder — constraint-based
# ============================================================================

def _catalog_meta(meta_key):
    """Retrieve catalog metadata for a part type."""
    return COMPONENT_CATALOG.get(meta_key, {})


# Gap between plate top surface and arm bottom (rail hardware clearance)
_ARM_Z_GAP = ARM_CENTER_Z - ARM_THICK / 2 - (BOTTOM_Z + BOTTOM_THICK)


def _build_assembly_builder():
    """Build the assembly with physical mating constraints for ALL parts.

    Only root plates (bottom_plate, top_plate) use absolute placement.
    All other parts are connected via mate()/offset() constraint chains.
    Tubing segments use computed routing (absolute) as flexible components.
    """
    asm = AssemblyBuilder()
    GAP = 1.0  # minimum clearance (mm)

    # ========================================================================
    # ROOT — absolute placement
    # ========================================================================

    asm.add("bottom_plate", make_skeleton_plate, args=(BOTTOM_THICK, True),
            color="#B87333", display="Bottom Plate (FR4 2.0mm)",
            meta=_catalog_meta("bottom_plate"))
    asm.place("bottom_plate", at=(0, 0, BOTTOM_Z))

    asm.add("top_plate", make_skeleton_plate, args=(TOP_THICK, False),
            color="#2FA84A", display="Top Plate (FR4 1.6mm)",
            meta=_catalog_meta("top_plate"))
    asm.place("top_plate", at=(0, 0, TOP_Z))

    # ========================================================================
    # FRAME — CONSTRAINED: arms bolt to plate arm_slot anchors
    # ========================================================================

    # Arms (4x) — arm frame_end (bottom face) mates plate arm_slot (top surface)
    # with Z gap for rail hardware and spin for angular orientation.
    for i, angle in enumerate(ARM_ANGLES):
        name = f"arm_{i+1}"
        asm.add(name, make_arm, color="#B87333",
                display=f"Arm {i+1} (FR4 I-beam)",
                meta=_catalog_meta("arm"))
        asm.offset(f"{name}.frame_end", f"bottom_plate.arm_slot_{i+1}",
                   gap=_ARM_Z_GAP, spin=angle)

    # ========================================================================
    # FRAME — CONSTRAINED: legs bolt to plate edges, boom pins into plate
    # ========================================================================

    # Landing legs (4x) — mount_tab (top, normal up) mates plate leg_slot (bottom, normal down)
    for i, angle in enumerate(LEG_ANGLES):
        leg_name = f"leg_{i+1}"
        asm.add(leg_name, make_landing_leg, color="#2E8B3E",
                display=f"Landing Leg {i+1}",
                meta=_catalog_meta("landing_leg"))
        asm.mate(f"{leg_name}.mount_tab", f"bottom_plate.leg_slot_{i+1}",
                 spin=angle)

    # Nose boom — root (normal -X) mates plate boom_root (normal +X)
    asm.add("nose_boom", make_nose_boom, color="#2FA84A",
            display="Nose Boom (FR4 I-beam)",
            meta=_catalog_meta("nose_boom"))
    asm.mate("nose_boom.root", "bottom_plate.boom_root")

    # ========================================================================
    # PROPULSION — CONSTRAINED: motors bolt to arm tips
    # ========================================================================

    for i, angle in enumerate(ARM_ANGLES):
        rad = math.radians(angle)

        # Motor — base_mount (bottom, normal down) mates arm motor_tip (top, normal up)
        motor_name = f"motor_{i+1}"
        asm.add(motor_name, make_motor, color="#5A5A5A",
                display=f"Motor {i+1} (X2212)",
                meta=_catalog_meta("motor"))
        asm.mate(f"{motor_name}.base_mount", f"arm_{i+1}.motor_tip")

        # Propeller — hub_base mates motor shaft_tip
        prop_name = f"prop_{i+1}"
        asm.add(prop_name, make_propeller, color="#4A4A4A",
                display=f"Propeller {i+1} (1045)",
                meta=_catalog_meta("propeller"))
        asm.mate(f"{prop_name}.hub_base", f"motor_{i+1}.shaft_tip",
                 spin=angle + 30)

        # ESC — top surface (normal up) mates arm esc_mount (normal down)
        esc_name = f"esc_{i+1}"
        asm.add(esc_name, make_esc, color="#3D3D3D",
                display=f"ESC {i+1} (30A)",
                meta=_catalog_meta("esc"))
        asm.mate(f"{esc_name}.top", f"arm_{i+1}.esc_mount", spin=angle)

    # ========================================================================
    # ELECTRONICS — CONSTRAINED: standoffs bolt to plate, DE10 on standoffs
    # ========================================================================

    # Standoffs (4x) — base mates plate standoff_hole (M2.5 bolt through)
    for j in range(4):
        so_name = f"standoff_{j+1}"
        asm.add(so_name, make_standoff, args=(DE10_STANDOFF,),
                color="#BFBFC7", display=f"Standoff {j+1} (M2.5)",
                meta=_catalog_meta("standoff"))
        asm.mate(f"{so_name}.base", f"bottom_plate.standoff_hole_{j+1}")

    # DE10-Nano — mounting_hole_1 mates standoff_1 top (M3 bolt)
    asm.add("de10_nano", make_de10_nano, color="#1A80CC",
            display="DE10-Nano FPGA Board",
            meta=_catalog_meta("de10_nano"))
    asm.mate("de10_nano.mounting_hole_1", "standoff_1.top")

    # Daughter board — gpio0_receptacle (normal down) mates DE10 gpio0 (normal up)
    asm.add("daughter_board", make_daughter_board, color="#CC3333",
            display="Daughter Board",
            meta=_catalog_meta("daughter_board"))
    asm.mate("daughter_board.gpio0_receptacle", "de10_nano.gpio0")

    # ========================================================================
    # PAYLOAD — CONSTRAINED (underslung beneath bottom plate)
    # ========================================================================

    # Battery — top_face (normal up) mates plate battery_mount (normal down)
    # offset = UNDERSLUNG_GAP + BATT_H (battery hangs below by its full height + gap)
    asm.add("battery", make_battery, color="#4A4A4A",
            display="Battery (4S 2200mAh)",
            meta=_catalog_meta("battery"))
    asm.offset("battery.top_face", "bottom_plate.battery_mount",
               gap=UNDERSLUNG_GAP, spin=BATT_ROTATION_DEG)

    # Reservoir — bottom_face (normal down) mates plate reservoir_mount (normal down)
    # After mate: reservoir flips (180°) so its body extends downward from anchor.
    # offset gap = UNDERSLUNG_GAP pushes anchor point down from plate bottom.
    # Result: reservoir top at plate_bottom - gap, bottom at top - RES_H.
    asm.add("reservoir", make_reservoir, color="#4D99E6",
            display="Water Reservoir",
            meta=_catalog_meta("reservoir"))
    asm.offset("reservoir.bottom_face", "bottom_plate.reservoir_mount",
               gap=UNDERSLUNG_GAP)

    # Pump bracket — base_mount (normal down) mates plate pump_bracket_mount (normal down)
    # Bracket flips so base faces up against plate underside
    asm.add("pump_bracket", make_pump_bracket, color="#2FA84A",
            display="Pump Bracket (FR4)",
            meta=_catalog_meta("pump_bracket"))
    asm.offset("pump_bracket.base_mount", "bottom_plate.pump_bracket_mount",
               gap=UNDERSLUNG_GAP)

    # Pump — base (normal down) mates pump_bracket channel_center (normal up)
    asm.add("pump", make_pump, color="#E67300",
            display="Peristaltic Pump",
            meta=_catalog_meta("pump"))
    asm.mate("pump.base", "pump_bracket.channel_center")

    # ========================================================================
    # SENSORS — CAMERA (constrained to boom)
    # ========================================================================

    # Camera bracket — boom_mount (normal -Y) mates boom camera_mount (normal -Z)
    # Produces 90° rotation so bracket tab hangs downward
    asm.add("camera_bracket", make_camera_bracket, color="#2FA84A",
            display="Camera Bracket (FR4)",
            meta=_catalog_meta("camera"))
    asm.mate("camera_bracket.boom_mount", "nose_boom.camera_mount", spin=-90)

    # Camera — mount_face (normal +Z) mates camera_bracket camera_mount (normal -Y)
    asm.add("camera", make_camera, color="#3D3D3D",
            display="OV5640 Camera Module",
            meta=_catalog_meta("camera"))
    asm.mate("camera.mount_face", "camera_bracket.camera_mount")

    # Drip nozzle — flange_mount (normal +Z) mates boom nozzle_mount (normal -Z)
    asm.add("drip_nozzle", make_drip_nozzle, color="#888888",
            display="Drip Nozzle",
            meta=_catalog_meta("drip_nozzle"))
    asm.mate("drip_nozzle.flange_mount", "nose_boom.nozzle_mount")

    # ========================================================================
    # SENSORS — ToF (ALL constrained: brackets to plates, sensors to brackets)
    # ========================================================================

    _brk_gap = TOF_BRACKET_T + 2  # clearance gap between plate and bracket base

    # (sensor_name, display, bracket_name, display, plate_part, mount_anchor, spin)
    tof_configs = [
        ("tof_down", "ToF Down",
         "tof_bracket_down", "ToF Bracket Down",
         "bottom_plate", "tof_mount_down", 0),
        ("tof_up", "ToF Up",
         "tof_bracket_up", "ToF Bracket Up",
         "top_plate", "tof_mount_up", 0),
        ("tof_front", "ToF Front",
         "tof_bracket_front", "ToF Bracket Front",
         "top_plate", "tof_mount_front", 0),
        ("tof_back", "ToF Back",
         "tof_bracket_back", "ToF Bracket Back",
         "top_plate", "tof_mount_back", 0),
        ("tof_left", "ToF Left",
         "tof_bracket_left", "ToF Bracket Left",
         "top_plate", "tof_mount_left", 0),
        ("tof_right", "ToF Right",
         "tof_bracket_right", "ToF Bracket Right",
         "top_plate", "tof_mount_right", 0),
    ]
    for s_name, s_disp, b_name, b_disp, plate, mount_anchor, spin in tof_configs:
        # Bracket — plate_mount (normal down) mates plate tof_mount_* (directional normal)
        asm.add(b_name, make_tof_bracket, color="#2FA84A",
                display=b_disp, meta=_catalog_meta("tof_bracket"))
        asm.offset(f"{b_name}.plate_mount", f"{plate}.{mount_anchor}",
                   gap=_brk_gap, spin=spin)

        # Sensor — mount_face mates bracket sensor_mount
        asm.add(s_name, make_tof_board, color="#CC44CC",
                display=s_disp, meta=_catalog_meta("tof_sensor"))
        asm.mate(f"{s_name}.mount_face", f"{b_name}.sensor_mount")

    # ========================================================================
    # TUBING — computed routing (absolute placement)
    # ========================================================================

    _pc = _D["pump"]
    _tube_y_local = _pc["body_length"] / 2 - _pc.get("tube_exit_inset_from_front", 5)
    _tube_z_local = _pc["body_height"] + _pc.get("tube_exit_length", 8)
    _tube_sp = _pc.get("tube_spacing", 10)

    pump_x = BRACKET_OFFSET_X
    pump_y = BRACKET_OFFSET_Y
    pump_z_ref = BOTTOM_Z - 14

    pump_fit_inlet = (pump_x + _tube_sp / 2, pump_y - 2,
                      pump_z_ref - _tube_z_local - 3)
    pump_fit_outlet = (pump_x - _tube_sp / 2, pump_y - 2,
                       pump_z_ref - _tube_z_local - 3)

    res_length = _D["reservoir"]["length"]
    _res_z = BOTTOM_Z - RES_H - UNDERSLUNG_GAP  # computed for tubing routing
    res_outlet = (RES_OFFSET_X + _D["reservoir"]["width"] / 2 + 3,
                  RES_OFFSET_Y - res_length / 2 - 3,
                  _res_z - 3)

    nozzle_tube_x = PLATE_SIZE / 2 + BOOM_LENGTH + 13

    def _add_tube(name, display, start, end):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        mid = ((start[0] + end[0]) / 2,
               (start[1] + end[1]) / 2,
               (start[2] + end[2]) / 2)
        horiz = math.sqrt(dx * dx + dy * dy)
        pitch = math.degrees(math.atan2(horiz, dz)) if length > 0 else 0
        yaw = math.degrees(math.atan2(dy, dx)) if horiz > 0 else 0

        asm.add(name, make_tubing_segment, args=(length,),
                color="#C0C0C0", display=display)
        asm.place(name, at=mid, rot=(pitch, 0, yaw))

    _add_tube("tubing_res_to_pump", "Tubing: Reservoir \u2192 Pump",
              res_outlet, pump_fit_inlet)

    outside_x = PLATE_SIZE / 2 + 55
    waypoint_low = (outside_x, pump_fit_outlet[1], pump_fit_outlet[2])
    _add_tube("tubing_pump_to_edge", "Tubing: Pump \u2192 Frame Edge",
              pump_fit_outlet, waypoint_low)

    boom_z_ref = ARM_CENTER_Z + ARM_THICK / 2 + GAP
    waypoint_high = (outside_x, 0, boom_z_ref - 3)
    _add_tube("tubing_edge_vertical", "Tubing: Vertical Rise",
              waypoint_low, waypoint_high)

    boom_start = (PLATE_SIZE / 2 + 3, 0, boom_z_ref - 3)
    boom_end = (nozzle_tube_x - 3, 0, boom_z_ref - 3)
    _add_tube("tubing_edge_to_boom", "Tubing: Along Boom",
              boom_start, boom_end)

    return asm


def build_drone_manifest():
    """Build the drone assembly manifest.

    Returns:
        list[dict]: Manifest entries compatible with pipeline.export_assembly().
    """
    return _build_assembly_builder().resolve()


def get_assembly_constraints():
    """Return constraint metadata for viewer visualization.

    Returns a list of dicts with keys: child_part, child_anchor,
    parent_part, parent_anchor, kind — suitable for passing to
    export_assembly(constraints=...).
    """
    asm = _build_assembly_builder()
    constraints = []
    for c in asm._constraints:
        constraints.append({
            "child_part": c.child_part,
            "child_anchor": c.child_anchor,
            "parent_part": c.parent_part,
            "parent_anchor": c.parent_anchor,
            "kind": c.kind,
        })
    return constraints
