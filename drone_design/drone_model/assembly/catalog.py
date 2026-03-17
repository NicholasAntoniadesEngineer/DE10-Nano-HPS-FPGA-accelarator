"""Component catalog — aggregates CATALOG metadata from all component files."""

from components.assembly_constants import (
    BOTTOM_THICK, TOP_THICK, DE10_STANDOFF,
)

# Component builders (needed for INDIVIDUAL_PARTS)
from components.frame.skeleton_plate import CATALOG as _plate_cat, make_skeleton_plate
from components.frame.arm import CATALOG as _arm_cat, make_arm, make_arm_inner, make_arm_outer
from components.frame.nose_boom import CATALOG as _boom_cat, make_nose_boom, make_boom_root, make_boom_tip
from components.landing_gear.landing_leg import CATALOG as _leg_cat, make_landing_leg
from components.propulsion.motor import CATALOG as _motor_cat, make_motor
from components.propulsion.propeller import CATALOG as _prop_cat, make_propeller
from components.propulsion.esc import CATALOG as _esc_cat, make_esc
from components.electronics.de10_nano import CATALOG as _de10_cat, make_de10_nano
from components.electronics.daughter_board import CATALOG as _db_cat, make_daughter_board
from components.electronics.standoff import CATALOG as _standoff_cat, make_standoff
from components.sensors.tof_board import CATALOG as _tof_cat, make_tof_board
from components.sensors.tof_bracket import CATALOG as _tof_bracket_cat, make_tof_bracket
from components.sensors.camera import CATALOG as _camera_cat, make_camera
from components.sensors.camera_bracket import CATALOG as _camera_bracket_cat, make_camera_bracket
from components.payload.battery import CATALOG as _battery_cat, make_battery
from components.payload.reservoir import CATALOG as _reservoir_cat, make_reservoir
from components.payload.pump import CATALOG as _pump_cat, make_pump
from components.payload.pump_bracket import CATALOG as _pump_bracket_cat, make_pump_bracket
from components.payload.drip_nozzle import CATALOG as _nozzle_cat, make_drip_nozzle
from components.electronics.cooling_fan import CATALOG as _fan_cat, make_cooling_fan


# =============================================================================
# Component catalog — aggregated from individual component modules
# =============================================================================

COMPONENT_CATALOG = {}
COMPONENT_CATALOG.update(_plate_cat)
COMPONENT_CATALOG.update(_arm_cat)
COMPONENT_CATALOG.update(_boom_cat)
COMPONENT_CATALOG.update(_leg_cat)
COMPONENT_CATALOG.update(_motor_cat)
COMPONENT_CATALOG.update(_prop_cat)
COMPONENT_CATALOG.update(_esc_cat)
COMPONENT_CATALOG.update(_de10_cat)
COMPONENT_CATALOG.update(_db_cat)
COMPONENT_CATALOG.update(_standoff_cat)
COMPONENT_CATALOG.update(_tof_cat)
COMPONENT_CATALOG.update(_tof_bracket_cat)
COMPONENT_CATALOG.update(_camera_cat)
COMPONENT_CATALOG.update(_camera_bracket_cat)
COMPONENT_CATALOG.update(_battery_cat)
COMPONENT_CATALOG.update(_reservoir_cat)
COMPONENT_CATALOG.update(_pump_cat)
COMPONENT_CATALOG.update(_pump_bracket_cat)
COMPONENT_CATALOG.update(_nozzle_cat)
COMPONENT_CATALOG.update(_fan_cat)


# =============================================================================
# Individual parts (exported at origin for manufacturing)
# =============================================================================

INDIVIDUAL_PARTS = {
    "bottom_plate": (make_skeleton_plate, (BOTTOM_THICK, True)),
    "top_plate": (make_skeleton_plate, (TOP_THICK, False)),
    "arm": (make_arm, ()),
    "arm_inner": (make_arm_inner, ()),
    "arm_outer": (make_arm_outer, ()),
    "landing_leg": (make_landing_leg, ()),
    "tof_board": (make_tof_board, ()),
    "tof_bracket": (make_tof_bracket, ()),
    "pump_bracket": (make_pump_bracket, ()),
    "motor": (make_motor, ()),
    "propeller": (make_propeller, ()),
    "esc": (make_esc, ()),
    "de10_nano": (make_de10_nano, ()),
    "daughter_board": (make_daughter_board, ()),
    "battery": (make_battery, ()),
    "reservoir": (make_reservoir, ()),
    "pump": (make_pump, ()),
    "standoff": (make_standoff, (DE10_STANDOFF,)),
    "cooling_fan": (make_cooling_fan, ()),
    "drip_nozzle": (make_drip_nozzle, ()),
    "camera": (make_camera, ()),
    "camera_bracket": (make_camera_bracket, ()),
    "nose_boom": (make_nose_boom, ()),
    "boom_root": (make_boom_root, ()),
    "boom_tip": (make_boom_tip, ()),
}
