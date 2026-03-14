"""
Assembly-level dimensions derived from cad/dimensions.json.

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

_DIMS_PATH = Path(__file__).resolve().parent.parent.parent / "cad" / "dimensions.json"

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
MOUNT_FLANGE_LEN = 30.0  # mm — bolt-on mounting flange length
ARM_LENGTH   = MOTOR_R + MOUNT_FLANGE_LEN / 2
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
RES_H        = _D["reservoir"]["height"]
RES_OFFSET_X = _D["reservoir"]["offset_x"]

# Pump system
PUMP_BASE_W       = _D["pump"]["base_width"]
PUMP_BASE_D       = _D["pump"]["base_depth"]
PUMP_BASE_H       = _D["pump"]["base_height"]
PUMP_MOTOR_D      = _D["pump"]["motor_diameter"]
BRACKET_BASE_W    = _D["pump_bracket"]["base_width"]
BRACKET_BASE_D    = _D["pump_bracket"]["base_depth"]
BRACKET_BACK_H    = _D["pump_bracket"]["back_height"]
BRACKET_T         = _D["pump_bracket"]["thickness"]
# Aliases used by exporters
PUMP_W         = PUMP_BASE_W
PUMP_BRACKET_W = BRACKET_BASE_W
PUMP_BRACKET_H = BRACKET_BACK_H
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

# ─── Z-height references (ground = 0) ────────────────────────────────────────
GROUND_Z     = 0.0
LEG_TOP_Z    = GROUND_Z + FOOT_THICK + LEG_HEIGHT
BOTTOM_Z     = LEG_TOP_Z
TOP_Z        = BOTTOM_Z + BOTTOM_THICK + PLATE_SPACING
DE10_Z       = BOTTOM_Z + BOTTOM_THICK + DE10_STANDOFF
DB_Z         = DE10_Z + DE10_H + DB_ABOVE_DE10
ARM_CENTER_Z = BOTTOM_Z + BOTTOM_THICK + PLATE_SPACING / 2
