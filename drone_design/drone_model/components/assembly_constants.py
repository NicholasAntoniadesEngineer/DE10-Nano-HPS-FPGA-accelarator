"""
Assembly-level dimensions derived from dimensions.json.

This module is the single source of truth for constants that depend on
multiple component groups (e.g. Z-heights that combine leg, plate, and
standoff dimensions).  Individual component modules load their *own*
dimensions directly from dimensions.json — this file only holds the
cross-cutting assembly-placement constants.

Importers: drone_3d_model.py, export_stl.py, export_gerber.py
"""

import json
import math
from pathlib import Path

_DIMS_PATH = Path(__file__).resolve().parent.parent / "dimensions.json"

def _load_dimensions():
    with open(_DIMS_PATH) as f:
        return json.load(f)

_D = _load_dimensions()

# ─── Frame ────────────────────────────────────────────────────────────────────
PLATE_SIZE     = _D["frame"]["plate_size"]
PLATE_CORNER_R = _D["frame"]["plate_corner_radius"]
BOTTOM_THICK   = _D["frame"]["bottom_plate_thickness"]
TOP_THICK      = _D["frame"]["top_plate_thickness"]
PLATE_SPACING  = _D["frame"]["plate_spacing"]

# ─── Arms ─────────────────────────────────────────────────────────────────────
MOTOR_TO_MOTOR_DIAG = _D["arms"]["motor_to_motor_diagonal"]
MOTOR_R      = MOTOR_TO_MOTOR_DIAG / 2
MOUNT_FLANGE_LEN = _D["arms"]["mount_flange_length"]
# Arm slot at plate corner: arm extends FROM the plate edge OUTWARD to motor.
# At 45°, plate corner distance = PLATE_SIZE * √2 / 2.  The arm's mount
# flange overlaps the plate by MOUNT_FLANGE_LEN, so the inner tip of the arm
# sits that distance inboard from the corner.
PLATE_DIAG_R = PLATE_SIZE * math.sqrt(2) / 2          # ~77.8 mm for 110mm plate
ARM_SLOT_R   = PLATE_DIAG_R - MOUNT_FLANGE_LEN        # ~62.8 mm — arm inner tip
# Keep legacy name for imports that reference it
ARM_CLEARANCE_R = ARM_SLOT_R
# Arm extends from ARM_SLOT_R outward so motor mount CENTER sits at MOTOR_R.
MOTOR_SECTION_VAL = _D["arms"]["motor_mount_section_length"]
ARM_LENGTH   = MOTOR_R - ARM_SLOT_R + MOTOR_SECTION_VAL / 2
ARM_WIDTH    = _D["arms"]["arm_width"]
ARM_THICK    = _D["arms"]["arm_thickness"]
ARM_FLANGE   = _D["arms"]["arm_flange_width"]
ARM_WEB      = _D["arms"]["arm_web_width"]
MOTOR_SECTION = _D["arms"]["motor_mount_section_length"]
ARM_ANGLES   = _D["arms"]["arm_angles_deg"]
ADJ_MOTOR_DIST = 2 * MOTOR_R * math.sin(math.radians(45))
MOTOR_MOUNT_RECT = _D["motor"]["mount_bolt_pattern"]

# ─── Landing gear ─────────────────────────────────────────────────────────────
LEG_WIDTH    = _D["landing_gear"]["leg_width"]
LEG_HEIGHT   = _D["landing_gear"]["leg_height"]
LEG_THICK    = _D["landing_gear"]["leg_thickness"]
FOOT_LENGTH  = _D["landing_gear"]["foot_length"]
FOOT_THICK   = _D["landing_gear"]["foot_thickness"]
LEG_ANGLES   = _D["landing_gear"]["leg_angles_deg"]
LEG_HOLE_W   = _D["landing_gear"]["lightening_hole_width"]
LEG_HOLE_H   = _D["landing_gear"]["lightening_hole_height"]
LEG_HOLE_R   = _D["landing_gear"]["lightening_hole_end_radius"]
LEG_HOLE_N   = _D["landing_gear"]["lightening_hole_count"]

# ─── Motor / propulsion ──────────────────────────────────────────────────────
MOTOR_TOTAL_H = _D["motor"]["body_height"] + _D["motor"]["shaft_protrusion"]
ESC_H        = _D["esc"]["height"]
ESC_RADIAL_FRAC = _D["assembly"]["esc_radial_fraction"]

# ─── Electronics ──────────────────────────────────────────────────────────────
DE10_W       = _D["de10_nano"]["board_width"]
DE10_L       = _D["de10_nano"]["board_length"]
DE10_H       = _D["de10_nano"]["pcb_thickness"]
DE10_STANDOFF = _D["de10_nano"]["standoff_height"]
DB_ABOVE_DE10 = _D["daughter_board"]["gap_above_de10"]

# ─── Payload ──────────────────────────────────────────────────────────────────
BATT_H       = _D["battery"]["height"]
BATT_CG_OFFSET = _D["battery"]["cg_offset_x"]
RES_W        = _D["reservoir"]["width"]
RES_L        = _D["reservoir"]["length"]
RES_H        = _D["reservoir"]["height"]
RES_OFFSET_X = _D["reservoir"]["offset_x"]

# Pump system (Takasago RP-Q1)
PUMP_BODY_L       = _D["pump"]["body_length"]
PUMP_BODY_W       = _D["pump"]["body_width"]
PUMP_BODY_H       = _D["pump"]["body_height"]
PUMP_TUBE_OD      = _D["pump"]["tube_od"]
PUMP_TUBE_LEN     = _D["pump"]["tube_exit_length"]
PUMP_TUBE_SP      = _D["pump"]["tube_spacing"]
PUMP_TUBE_INSET   = _D["pump"]["tube_exit_inset_from_front"]
BRACKET_CHANNEL_L = _D["pump_bracket"]["channel_length"]
BRACKET_WALL_H    = _D["pump_bracket"]["wall_height"]
BRACKET_T         = _D["pump_bracket"]["thickness"]
BRACKET_BASE_EXT  = _D["pump_bracket"]["base_extension"]
# Derived bracket width
PUMP_BRACKET_W = PUMP_BODY_W + 2 * BRACKET_T + 2 * BRACKET_BASE_EXT
PUMP_BRACKET_T = BRACKET_T

# ─── Boom ─────────────────────────────────────────────────────────────────────
BOOM_LENGTH  = _D["nose_boom"]["length"]
BOOM_WIDTH   = _D["nose_boom"]["width"]
BOOM_THICK   = _D["nose_boom"]["thickness"]
BOOM_FLANGE  = _D["nose_boom"]["flange_width"]
BOOM_WEB     = _D["nose_boom"]["web_width"]

# ─── Sensors ──────────────────────────────────────────────────────────────────
TOF_H        = _D["tof_sensor"]["board_height"]
TOF_L        = _D["tof_sensor"]["board_length"]

# ─── Assembly ─────────────────────────────────────────────────────────────────
KAGOME_CELL    = _D["assembly"]["kagome_cell_size"]
KAGOME_HOLE_R  = _D["assembly"]["kagome_hole_radius"]
KAGOME_WEB_MIN = _D["assembly"]["kagome_min_web"]

# Propeller (for clearance report)
PROP_DIAMETER = _D["propeller"]["diameter"]

# Placement offsets
UNDERSLUNG_GAP      = _D["assembly"]["underslung_gap"]
RES_OFFSET_Y        = _D["assembly"]["reservoir_offset_y"]
BRACKET_OFFSET_X    = _D["assembly"]["pump_bracket_offset_x"]
BRACKET_OFFSET_Y    = _D["assembly"]["pump_bracket_offset_y"]
CAMERA_BOOM_OFFSET  = _D["assembly"]["camera_boom_offset"]
BATT_ROTATION_DEG   = _D["assembly"]["battery_rotation_deg"]
ARM_Z_ABOVE_BOTTOM  = _D["assembly"]["arm_z_above_bottom"]

# ─── Z-height references (ground = 0) ────────────────────────────────────────
GROUND_Z     = 0.0
LEG_TOP_Z    = GROUND_Z + FOOT_THICK + LEG_HEIGHT
BOTTOM_Z     = LEG_TOP_Z
TOP_Z        = BOTTOM_Z + BOTTOM_THICK + PLATE_SPACING
DE10_Z       = BOTTOM_Z + BOTTOM_THICK + DE10_STANDOFF
DB_Z         = DE10_Z + DE10_H + DB_ABOVE_DE10
ARM_CENTER_Z = BOTTOM_Z + BOTTOM_THICK + ARM_Z_ABOVE_BOTTOM
