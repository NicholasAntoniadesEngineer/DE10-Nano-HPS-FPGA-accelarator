"""
Drone assembly manifest using constraint-based AssemblyBuilder.

Every part is positioned via physical mating constraints (mate/offset) using
anchor-to-anchor connections.  Only root plates use absolute placement.
Tubing segments use computed routing (absolute) as they are flexible.

Usage:
    from assembly.manifest import build_drone_manifest
    manifest, validation, tubing_allowed = build_drone_manifest()
"""

import json
import math
import sys
from pathlib import Path

_DRONE_MODEL = Path(__file__).resolve().parent.parent
_REPO_ROOT = _DRONE_MODEL.parent.parent
sys.path.insert(0, str(_DRONE_MODEL))
sys.path.insert(0, str(_REPO_ROOT))

import importlib.util
from cadquery_framework.assembly.anchors import Anchor, AssemblyBuilder
from cadquery_framework.viewer.overlay import load_overlay
from cadquery_framework.viewer.codegen.custom_part import generate_custom_part_module

# Component builders
from components.frame.skeleton_plate import make_skeleton_plate
from components.frame.arm import make_arm
from components.frame.motor_riser import make_motor_riser
from components.frame.nose_boom import make_nose_boom
from components.landing_gear.landing_leg import make_landing_leg
from components.propulsion.motor import make_motor
from components.propulsion.propeller import make_propeller, make_prop_clearance_disc
from components.propulsion.esc import make_esc
from components.electronics.de10_nano import make_de10_nano
from components.electronics.daughter_board import make_daughter_board
from components.electronics.standoff import make_standoff
from components.electronics.cooling_fan import make_cooling_fan
from components.sensors.tof_board import make_tof_board
from components.sensors.tof_bracket import (
    make_tof_bracket, TOF_BRACKET_T, TOF_BRACKET_TAB, TOF_BRACKET_DEPTH,
)
from components.sensors.camera import make_camera
from components.sensors.camera_bracket import make_camera_bracket
from components.payload.battery import make_battery
from components.payload.reservoir import make_reservoir
from components.payload.pump import make_pump
from components.payload.pump_bracket import make_pump_bracket
from components.payload.drip_nozzle import make_drip_nozzle
from components.payload.tubing import make_tube_segment, make_tube_joint, decompose_path

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
    RES_H, RES_OFFSET_X, RES_W, RES_L,
    BOOM_LENGTH, BOOM_THICK, BOOM_WIDTH,
    TOF_H, TOF_L,
    GROUND_Z, BOTTOM_Z, TOP_Z, DE10_Z, DB_Z, ARM_CENTER_Z,
    UNDERSLUNG_GAP, RES_OFFSET_Y, BRACKET_OFFSET_X, BRACKET_OFFSET_Y,
    BATT_ROTATION_DEG, CAMERA_BOOM_OFFSET,
    BRACKET_T, DB_ABOVE_DE10,
    RES_EXTRA_DROP, PUMP_Y_ROTATION,
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
    "motor_riser": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm x 7 layers",
        "dims": "Ø25mm x 11.2mm (7 stacked FR4 discs)",
        "mass_g": 14, "qty": 4,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Stacked FR4 disc riser, through-bolted on motor bolt circle, raises motor to clear top plate",
        "interface": "4x M2 through-bolts: arm tip → riser → motor base",
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
        "dims": "110 x 110 x 1.6mm",
        "mass_g": 45, "qty": 1,
        "supplier": "Custom PCB (JLCPCB)",
        "notes": "Combined top plate + daughter board: Kagome frame, sensor hub, power regulators",
        "interface": "Structural top plate + DE10-Nano daughter board in one PCB",
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
    "tubing": {
        "material": "Silicone (flexible)",
        "dims": "2.5mm OD, 1.5mm ID (per pump tube spec)",
        "mass_g": 0.5,
        "qty": 4,
        "supplier": "Generic silicone tubing",
        "notes": "Reservoir outlet to pump inlet; pump outlet to spout (nozzle). Pump can run in reverse to fill reservoir by sucking through the spout.",
        "interface": "Push-fit on reservoir barb, pump tube stubs, and nozzle barb.",
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


def _build_core_assembly():
    """Build the assembly with physical mating constraints for ALL rigid parts.

    Only bottom_plate uses absolute placement (assembly root).
    All other parts — including top_plate — are connected via mate()/offset()
    constraint chains.  Tubing is handled separately in _route_tubing() using
    resolved anchor positions from this assembly.
    """
    asm = AssemblyBuilder()

    # ========================================================================
    # ROOT — bottom plate is the single assembly root
    # ========================================================================

    asm.add("bottom_plate", make_skeleton_plate, args=(BOTTOM_THICK, True),
            color="#B87333", display="Bottom Plate (FR4 2.0mm)",
            meta=_catalog_meta("bottom_plate"))
    asm.place("bottom_plate", at=(0, 0, BOTTOM_Z))

    # ========================================================================
    # TOP PLATE (combined with daughter board) — single PCB
    # ========================================================================
    # Physical mounting chain:
    #   bottom_plate → 5mm standoffs → DE10 → (GPIO headers 8.5mm) →
    #   combined top plate (structural frame + daughter board electronics)
    # GPIO receptacle headers on the underside mate with DE10 GPIO pins.

    asm.add("top_plate", make_skeleton_plate, args=(TOP_THICK, False, True),
            color="#2FA84A", display="Top Plate + Daughter Board (FR4 1.6mm)",
            meta=_catalog_meta("top_plate"))
    asm.mate("top_plate.gpio0_receptacle", "de10_nano.gpio0")

    # ========================================================================
    # FRAME — CONSTRAINED: arms bolt to plate arm_slot anchors
    # ========================================================================

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

    for i, angle in enumerate(LEG_ANGLES):
        leg_name = f"leg_{i+1}"
        asm.add(leg_name, make_landing_leg, color="#2E8B3E",
                display=f"Landing Leg {i+1}",
                meta=_catalog_meta("landing_leg"))
        asm.mate(f"{leg_name}.mount_tab", f"bottom_plate.leg_slot_{i+1}",
                 spin=angle)

    asm.add("nose_boom", make_nose_boom, color="#2FA84A",
            display="Nose Boom (FR4 I-beam)",
            meta=_catalog_meta("nose_boom"))
    asm.mate("nose_boom.root", "bottom_plate.boom_root")

    # ========================================================================
    # PROPULSION — CONSTRAINED: motors bolt to arm tips
    # ========================================================================

    for i, angle in enumerate(ARM_ANGLES):
        riser_name = f"motor_riser_{i+1}"
        asm.add(riser_name, make_motor_riser, color="#B87333",
                display=f"Motor Riser {i+1} (stacked FR4)",
                meta=_catalog_meta("motor_riser"))
        asm.mate(f"{riser_name}.base_mount", f"arm_{i+1}.motor_tip")

        motor_name = f"motor_{i+1}"
        asm.add(motor_name, make_motor, color="#5A5A5A",
                display=f"Motor {i+1} (X2212)",
                meta=_catalog_meta("motor"))
        asm.mate(f"{motor_name}.base_mount", f"{riser_name}.motor_mount")

        prop_name = f"prop_{i+1}"
        asm.add(prop_name, make_propeller, color="#4A4A4A",
                display=f"Propeller {i+1} (1045)",
                meta=_catalog_meta("propeller"))
        asm.mate(f"{prop_name}.hub_base", f"motor_{i+1}.shaft_tip",
                 spin=angle + 30)

        esc_name = f"esc_{i+1}"
        asm.add(esc_name, make_esc, color="#3D3D3D",
                display=f"ESC {i+1} (30A)",
                meta=_catalog_meta("esc"))
        asm.mate(f"{esc_name}.top", f"arm_{i+1}.esc_mount", spin=angle)

    # ========================================================================
    # ELECTRONICS — CONSTRAINED: standoffs bolt to plate, DE10 on standoffs
    # ========================================================================

    for j in range(4):
        so_name = f"standoff_{j+1}"
        asm.add(so_name, make_standoff, args=(DE10_STANDOFF,),
                color="#BFBFC7", display=f"Standoff {j+1} (M2.5)",
                meta=_catalog_meta("standoff"))
        asm.mate(f"{so_name}.base", f"bottom_plate.standoff_hole_{j+1}")

    asm.add("de10_nano", make_de10_nano, color="#1A80CC",
            display="DE10-Nano FPGA Board",
            meta=_catalog_meta("de10_nano"))
    asm.mate("de10_nano.mounting_hole_1", "standoff_1.top")

    asm.add("cooling_fan", make_cooling_fan, color="#333333",
            display="Cooling Fan (30mm)",
            meta=_catalog_meta("cooling_fan"))
    asm.mate("cooling_fan.mount_face", "de10_nano.heatsink_top")

    # Daughter board is now combined into top_plate (combined_top=True)

    # ========================================================================
    # PAYLOAD — CONSTRAINED (underslung beneath bottom plate)
    # ========================================================================

    asm.add("battery", make_battery, color="#4A4A4A",
            display="Battery (4S 2200mAh)",
            meta=_catalog_meta("battery"))
    asm.offset("battery.top_face", "bottom_plate.battery_mount",
               gap=UNDERSLUNG_GAP, spin=BATT_ROTATION_DEG)

    asm.add("reservoir", make_reservoir, color="#4D99E6",
            display="Water Reservoir",
            meta=_catalog_meta("reservoir"))
    # bottom_face normal=(0,0,-1) opposes plate's downward normal → 180° flip
    # → reservoir body hangs below, fill port faces down (top of bag near plate)
    asm.offset("reservoir.bottom_face", "bottom_plate.reservoir_mount",
               gap=UNDERSLUNG_GAP)

    asm.add("pump_bracket", make_pump_bracket, color="#2FA84A",
            display="Pump Bracket (FR4)",
            meta=_catalog_meta("pump_bracket"))
    # base_mount normal=(0,0,-1) opposes plate's downward normal → 180° flip
    # → bracket inverts: flat base nearest plate, walls hang downward, channel opens down
    asm.offset("pump_bracket.base_mount", "bottom_plate.pump_bracket_mount",
               gap=UNDERSLUNG_GAP)

    asm.add("pump", make_pump, color="#E67300",
            display="Peristaltic Pump",
            meta=_catalog_meta("pump"))
    # pump.base normal=(0,0,-1) mates into inverted bracket's channel_center (now pointing down)
    # → pump hangs below bracket with tube stubs pointing further downward
    asm.mate("pump.base", "pump_bracket.channel_center",
             spin=PUMP_Y_ROTATION)

    # ========================================================================
    # SENSORS — CAMERA (constrained to boom)
    # ========================================================================

    asm.add("camera_bracket", make_camera_bracket, color="#2FA84A",
            display="Camera Bracket (FR4)",
            meta=_catalog_meta("camera"))
    asm.mate("camera_bracket.boom_mount", "nose_boom.camera_platform")

    asm.add("camera", make_camera, color="#3D3D3D",
            display="OV5640 Camera Module",
            meta=_catalog_meta("camera"))
    asm.mate("camera.mount_face", "camera_bracket.camera_mount")

    asm.add("drip_nozzle", make_drip_nozzle, color="#888888",
            display="Drip Nozzle",
            meta=_catalog_meta("drip_nozzle"))
    asm.mate("drip_nozzle.flange_mount", "nose_boom.nozzle_mount")

    # ========================================================================
    # SENSORS — ToF (ALL constrained: brackets to plates, sensors to brackets)
    # ========================================================================

    # --- UP/DOWN: ToF boards mounted DIRECTLY on plate surface (no bracket) ---
    # Board mount_face (0,0,-1) opposes plate normal → board lies flat,
    # sensor aperture faces away from plate.

    # Down: board on bottom plate underside, sensor faces down
    asm.add("tof_down", make_tof_board, color="#CC44CC",
            display="ToF Down", meta=_catalog_meta("tof_sensor"))
    asm.offset("tof_down.mount_face", "bottom_plate.tof_mount_down", gap=0)

    # Up: board on daughter board top surface, sensor faces up
    asm.add("tof_up", make_tof_board, color="#CC44CC",
            display="ToF Up", meta=_catalog_meta("tof_sensor"))
    asm.offset("tof_up.mount_face", "top_plate.tof_mount_up", gap=0)

    # --- SIDE: L-bracket on plate top surface, sensor on bracket tab ---
    # Bracket base flat on plate, tab hangs over edge toward target direction.
    # Spin orients the tab: 0°→+Y, 180°→-Y, 90°→-X, -90°→+X
    _brk_gap = TOF_BRACKET_T + 2

    # Drone orientation: +X = front (boom/camera), -X = back, +Y = right, -Y = left
    # Spin orients bracket tab: 0→+Y, 90→-X, -90→+X, 180→-Y
    tof_side_configs = [
        ("tof_front", "ToF Front",
         "tof_bracket_front", "ToF Bracket Front",
         "top_plate", "tof_mount_front", -90),    # tab over +X (boom side)
        ("tof_back", "ToF Back",
         "tof_bracket_back", "ToF Bracket Back",
         "top_plate", "tof_mount_back", 90),       # tab over -X
        ("tof_left", "ToF Left",
         "tof_bracket_left", "ToF Bracket Left",
         "top_plate", "tof_mount_left", 180),      # tab over -Y
        ("tof_right", "ToF Right",
         "tof_bracket_right", "ToF Bracket Right",
         "top_plate", "tof_mount_right", 0),       # tab over +Y
    ]
    for s_name, s_disp, b_name, b_disp, plate, mount_anchor, spin in tof_side_configs:
        asm.add(b_name, make_tof_bracket, color="#2FA84A",
                display=b_disp, meta=_catalog_meta("tof_bracket"))
        asm.offset(f"{b_name}.plate_mount", f"{plate}.{mount_anchor}",
                   gap=_brk_gap, spin=spin)

        asm.add(s_name, make_tof_board, color="#CC44CC",
                display=s_disp, meta=_catalog_meta("tof_sensor"))
        asm.mate(f"{s_name}.mount_face", f"{b_name}.sensor_mount")

    return asm


# ============================================================================
# Tubing — anchor-driven routing from resolved part positions
# ============================================================================

def _emit_tube_pieces(path_name, display_prefix, waypoints, color="#C0C0C0"):
    """Decompose a waypoint path into individual segment + joint manifest entries.

    Returns (entries, allowed_pairs):
      entries: list of manifest dicts (one per cylinder/sphere)
      allowed_pairs: set of frozenset pairs for adjacent segments
    """
    tube_meta = _catalog_meta("tubing")
    pieces = decompose_path(waypoints)
    entries = []
    allowed = set()
    seg_idx = 0
    joint_idx = 0
    prev_name = None

    for piece in pieces:
        if piece["type"] == "segment":
            name = f"{path_name}_s{seg_idx}"
            entries.append({
                "name": name,
                "display": f"{display_prefix} seg {seg_idx}",
                "color": color,
                "builder": make_tube_segment,
                "args": (piece["p1"], piece["p2"]),
                "pos": piece["p1"],
                "rot": (0.0, 0.0, 0.0),
                "meta": tube_meta,
                "anchors": {},
            })
            if prev_name:
                allowed.add(frozenset({prev_name, name}))
            prev_name = name
            seg_idx += 1
        else:
            name = f"{path_name}_j{joint_idx}"
            entries.append({
                "name": name,
                "display": f"{display_prefix} joint {joint_idx}",
                "color": color,
                "builder": make_tube_joint,
                "args": (),
                "pos": piece["center"],
                "rot": (0.0, 0.0, 0.0),
                "meta": tube_meta,
                "anchors": {},
            })
            if prev_name:
                allowed.add(frozenset({prev_name, name}))
            prev_name = name
            joint_idx += 1

    return entries, allowed


def _route_tubing(manifest_entries):
    """Create tubing: per-segment cylinders connecting world-space anchors.

    Reads tube route definitions from tube_routes.json (sibling of this
    package's parent directory).  Each route specifies:
      - start_anchor / end_anchor: resolved live from part positions
      - intermediate_waypoints: baked into the JSON, editable via viewer

    Returns (entries, allowed_pairs).
    Anchors are already in world coordinates after resolve().
    """
    parts = {e["name"]: e for e in manifest_entries}

    # Load route definitions
    routes_path = _DRONE_MODEL / "tube_routes.json"
    with open(routes_path) as fh:
        route_data = json.load(fh)

    # Live anchor lookup — endpoints always snap to current part positions
    anchor_map = {
        ("reservoir",   "outlet"):      parts["reservoir"]["anchors"]["outlet"].point,
        ("pump",        "outlet_tube"): parts["pump"]["anchors"]["outlet_tube"].point,
        ("pump",        "inlet_tube"):  parts["pump"]["anchors"]["inlet_tube"].point,
        ("drip_nozzle", "barb_inlet"):  parts["drip_nozzle"]["anchors"]["barb_inlet"].point,
    }

    # --- Routing debug ---
    print("\n  TUBING ROUTING DEBUG:")
    print(f"    Routes loaded from: {routes_path.name}")

    all_entries = []
    all_allowed = set()

    for route_name, route in route_data["routes"].items():
        sa = route["start_anchor"]
        ea = route["end_anchor"]
        start = anchor_map[(sa["part"], sa["anchor"])]
        end   = anchor_map[(ea["part"], ea["anchor"])]
        intermediates = [tuple(p) for p in route["intermediate_waypoints"]]
        waypoints = [start] + intermediates + [end]

        print(f"    {route['display']} ({len(waypoints)} waypoints):")

        def _fmt_wp(wp):
            return " \u2192 ".join(f"({p[0]:.1f},{p[1]:.1f},{p[2]:.1f})" for p in wp)
        print(f"      {_fmt_wp(waypoints)}")

        entries, adj_allowed = _emit_tube_pieces(
            route_name, route["display"], waypoints, route["color"]
        )
        all_entries.extend(entries)
        all_allowed.update(adj_allowed)

        # Resolve positional references in allowed_pairs
        seg_index = {
            "first":       0,
            "last":        -1,
            "second_last": -2,
            "third_last":  -3,
        }
        for pair in route.get("allowed_pairs", []):
            ts = pair["tube_segment"]
            idx = seg_index.get(ts)
            if idx is None:
                continue
            if ts in ("second_last", "third_last") and len(entries) < abs(idx):
                continue
            all_allowed.add(frozenset({entries[idx]["name"], pair["part"]}))

    return all_entries, all_allowed


# ============================================================================
# Public API
# ============================================================================

def build_drone_manifest(overlay_path=None):
    """Build the drone assembly manifest.

    Phase 1: Resolve all rigid parts via constraint solver (with optional
    viewer overlay: anchors and constraints applied before resolve,
    position overrides applied after).
    Phase 2: Route tubing between resolved world-space anchors.

    Args:
        overlay_path: Optional Path to output directory containing
            viewer_overlay.json. If present, viewer anchors and constraints
            are applied before resolve, and position/rotation overrides
            are applied to the manifest after resolve.

    Returns:
        tuple: (manifest_entries, validation). manifest_entries is a list of
        dicts compatible with pipeline.export_assembly(). validation is a dict
        with key "overlay_constraints_skipped" (list of skipped overlay constraints).
    """
    asm = _build_core_assembly()
    overlay = {}
    overlay_constraints_skipped = []
    if overlay_path is not None:
        overlay = load_overlay(Path(overlay_path))
    project_dir = Path(overlay_path).parent if overlay_path is not None else _DRONE_MODEL_DIR
    for new_part in overlay.get("new_parts", []):
        name = (new_part.get("name") or "").strip()
        display = (new_part.get("display") or name).strip()
        if not name:
            continue
        gen_path = generate_custom_part_module(project_dir, new_part, overwrite=False)
        if gen_path is None:
            continue
        spec = importlib.util.spec_from_file_location(
            f"components.custom.{gen_path.stem}", gen_path
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        builder = getattr(mod, f"make_{gen_path.stem}", None)
        if builder is None:
            continue
        asm.add(name, builder, color="#888888", display=display or name, meta={})
        geometry = new_part.get("geometry") or {}
        pos = geometry.get("pos", [0, 0, 0])
        rot = geometry.get("rot", [0, 0, 0])
        if len(pos) != 3:
            pos = [0, 0, 0]
        if len(rot) != 3:
            rot = [0, 0, 0]
        pos_zup = (float(pos[0]), float(-pos[2]), float(pos[1]))
        rot_deg = (float(rot[0]), float(rot[1]), float(rot[2]))
        asm.place(name, at=pos_zup, rot=rot_deg)
    if overlay:
        # Apply viewer-added anchors
        for part_name, anchor_list in overlay.get("anchors", {}).items():
            if part_name not in asm._parts:
                continue
            for a in anchor_list:
                name = a.get("name")
                point = a.get("point")
                normal = a.get("normal", [0, 0, 1])
                if name and point and len(point) == 3:
                    asm.add_anchor(
                        part_name, name,
                        (float(point[0]), float(point[1]), float(point[2])),
                        (float(normal[0]), float(normal[1]), float(normal[2])),
                    )
        # Apply viewer-added constraints; collect skipped for validation feedback
        overlay_constraints_skipped = []
        for c in overlay.get("constraints", []):
            child_part = c.get("child_part")
            child_anchor = c.get("child_anchor")
            parent_part = c.get("parent_part")
            parent_anchor = c.get("parent_anchor")
            kind = c.get("kind", "mate")
            gap = c.get("gap", 0.0)
            if not all([child_part, child_anchor, parent_part, parent_anchor]):
                overlay_constraints_skipped.append({
                    "reason": "missing_fields",
                    "constraint": dict(c),
                })
                continue
            try:
                if kind == "offset":
                    asm.offset(
                        f"{child_part}.{child_anchor}",
                        f"{parent_part}.{parent_anchor}",
                        gap=float(gap),
                    )
                else:
                    asm.mate(
                        f"{child_part}.{child_anchor}",
                        f"{parent_part}.{parent_anchor}",
                    )
            except ValueError as e:
                overlay_constraints_skipped.append({
                    "reason": "value_error",
                    "constraint": dict(c),
                    "detail": str(e),
                })
    # Print constraint tree before resolve for debugging
    asm.print_constraint_tree()

    core_manifest = asm.resolve()
    # NOTE: Overlay position/rotation overrides are intentionally NOT applied.
    # Anchor-based constraints are the single source of truth for part placement.
    # Overlays may add anchors and constraints (applied before resolve above),
    # but cannot override resolved positions — this ensures anchor authority.

    # Print resolved positions and key anchors
    asm.print_resolved_positions(core_manifest)
    asm.print_anchor_map(core_manifest, parts_filter=[
        "bottom_plate", "reservoir", "pump", "pump_bracket",
        "battery", "nose_boom", "drip_nozzle",
    ])

    # Phase 2 — route tubing using resolved world-space part positions
    tubing_entries, tubing_allowed = _route_tubing(core_manifest)
    validation = {"overlay_constraints_skipped": overlay_constraints_skipped}
    return core_manifest + tubing_entries, validation, tubing_allowed


def get_assembly_constraints():
    """Return constraint metadata for viewer visualization.

    Returns a list of dicts with keys: child_part, child_anchor,
    parent_part, parent_anchor, kind — suitable for passing to
    export_assembly(constraints=...).
    """
    asm = _build_core_assembly()
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
