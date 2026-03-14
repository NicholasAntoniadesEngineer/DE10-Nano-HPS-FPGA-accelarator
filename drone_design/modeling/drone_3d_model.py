#!/usr/bin/env python3
"""
Plant-Watering Drone — DE10-Nano — Parametric 3D Model (CadQuery)

ALL DIMENSIONS are loaded from cad/dimensions.json — the single source of truth.
Edit that file to change any dimension; the model and all exports reflect it automatically.

Usage:
    source .venv/bin/activate
    python drone_design/modeling/drone_3d_model.py

Output:
    drone_design/cad/exports/*.step  (individual parts + assembly)
"""

import json
import cadquery as cq
from pathlib import Path
import math

# =============================================================================
# Load dimensions from single source of truth
# =============================================================================

_DIMS_PATH = Path(__file__).resolve().parent.parent / "cad" / "dimensions.json"

def _load_dimensions():
    with open(_DIMS_PATH) as f:
        return json.load(f)

_D = _load_dimensions()

# --- Frame plates ---
PLATE_SIZE       = _D["frame"]["plate_size"]
PLATE_CORNER_R   = _D["frame"]["plate_corner_radius"]
BOTTOM_THICK     = _D["frame"]["bottom_plate_thickness"]
TOP_THICK        = _D["frame"]["top_plate_thickness"]
PLATE_SPACING    = _D["frame"]["plate_spacing"]
SLOT_W           = _D["frame"]["arm_slot_width"]
SLOT_L           = _D["frame"]["arm_slot_length"]

# --- Arms ---
MOTOR_TO_MOTOR_DIAG = _D["arms"]["motor_to_motor_diagonal"]
MOTOR_R          = MOTOR_TO_MOTOR_DIAG / 2
ARM_TAB          = _D["arms"]["arm_tab"]
ARM_LENGTH       = MOTOR_R + ARM_TAB / 2
ARM_WIDTH        = _D["arms"]["arm_width"]
ARM_THICK        = _D["arms"]["arm_thickness"]
ARM_FLANGE       = _D["arms"]["arm_flange_width"]
ARM_WEB          = _D["arms"]["arm_web_width"]
MOTOR_SECTION    = _D["arms"]["motor_mount_section_length"]
ARM_ANGLES       = _D["arms"]["arm_angles_deg"]

ADJ_MOTOR_DIST   = 2 * MOTOR_R * math.sin(math.radians(45))

# --- Landing gear ---
LEG_WIDTH        = _D["landing_gear"]["leg_width"]
LEG_HEIGHT       = _D["landing_gear"]["leg_height"]
LEG_THICK        = _D["landing_gear"]["leg_thickness"]
FOOT_LENGTH      = _D["landing_gear"]["foot_length"]
FOOT_THICK       = _D["landing_gear"]["foot_thickness"]
LEG_ANGLES       = _D["landing_gear"]["leg_angles_deg"]
LEG_HOLE_W       = _D["landing_gear"]["lightening_hole_width"]
LEG_HOLE_H       = _D["landing_gear"]["lightening_hole_height"]
LEG_HOLE_R       = _D["landing_gear"]["lightening_hole_end_radius"]
LEG_HOLE_N       = _D["landing_gear"]["lightening_hole_count"]

# --- Motor ---
MOTOR_BELL_OD    = _D["motor"]["bell_outer_diameter"]
MOTOR_BODY_H     = _D["motor"]["body_height"]
MOTOR_SHAFT_D    = _D["motor"]["shaft_diameter"]
MOTOR_SHAFT_H    = _D["motor"]["shaft_protrusion"]
MOTOR_TOTAL_H    = MOTOR_BODY_H + MOTOR_SHAFT_H
MOTOR_BASE_D     = _D["motor"]["base_plate_diameter"]
MOTOR_MOUNT_RECT = tuple(_D["motor"]["mount_bolt_pattern"])
MOTOR_STATOR_D   = _D["motor"]["stator_diameter"]
MOTOR_STATOR_H   = _D["motor"]["stator_height"]
MOTOR_BELL_T     = _D["motor"]["bell_wall_thickness"]
MOTOR_PROP_ADAPT_D = _D["motor"]["prop_adapter_diameter"]
MOTOR_PROP_ADAPT_H = _D["motor"]["prop_adapter_height"]

# --- Propeller ---
PROP_DIAMETER    = _D["propeller"]["diameter"]
PROP_HUB_D       = _D["propeller"]["hub_diameter"]
PROP_HUB_H       = _D["propeller"]["hub_height"]
PROP_BLADE_W     = _D["propeller"]["blade_width"]
PROP_BLADE_T     = _D["propeller"]["blade_thickness"]
PROP_TIP_CHORD   = _D["propeller"]["blade_tip_chord"]
PROP_ROOT_CHORD  = _D["propeller"]["blade_root_chord"]
PROP_MAX_CHORD   = _D["propeller"]["blade_max_chord"]
PROP_MAX_STATION = _D["propeller"]["blade_max_chord_station"]

# --- ESC ---
ESC_L            = _D["esc"]["length"]
ESC_W            = _D["esc"]["width"]
ESC_H            = _D["esc"]["height"]
ESC_PAD_L        = _D["esc"]["solder_pad_length"]
ESC_PAD_W        = _D["esc"]["solder_pad_width"]
ESC_PAD_H        = _D["esc"]["solder_pad_height"]
ESC_PAD_N        = _D["esc"]["solder_pad_count"]

# --- DE10-Nano ---
DE10_W           = _D["de10_nano"]["board_width"]
DE10_L           = _D["de10_nano"]["board_length"]
DE10_H           = _D["de10_nano"]["pcb_thickness"]
DE10_COMPONENT_H = _D["de10_nano"]["tallest_component_height"]
DE10_STANDOFF    = _D["de10_nano"]["standoff_height"]
DE10_GPIO_L      = _D["de10_nano"]["gpio_header_length"]
DE10_GPIO_W      = _D["de10_nano"]["gpio_header_width"]
DE10_GPIO_H      = _D["de10_nano"]["gpio_header_height"]
HS_W             = _D["de10_nano"]["heatsink_width"]
HS_L             = _D["de10_nano"]["heatsink_length"]
HS_H             = _D["de10_nano"]["heatsink_height"]

# --- Daughter board ---
DB_W             = _D["daughter_board"]["width"]
DB_L             = _D["daughter_board"]["length"]
DB_H             = _D["daughter_board"]["pcb_thickness"]
DB_ABOVE_DE10    = _D["daughter_board"]["gap_above_de10"]

# --- Battery ---
BATT_L           = _D["battery"]["length"]
BATT_W           = _D["battery"]["width"]
BATT_H           = _D["battery"]["height"]
BATT_CG_OFFSET   = _D["battery"]["cg_offset_x"]
BATT_XT60_W      = _D["battery"]["xt60_width"]
BATT_XT60_H      = _D["battery"]["xt60_height"]
BATT_XT60_D      = _D["battery"]["xt60_depth"]
BATT_CORNER_R    = _D["battery"]["corner_radius"]

# --- Reservoir ---
RES_W            = _D["reservoir"]["width"]
RES_L            = _D["reservoir"]["length"]
RES_H            = _D["reservoir"]["height"]
RES_OFFSET_X     = _D["reservoir"]["offset_x"]

# --- Pump ---
PUMP_L           = _D["pump"]["total_length"]
PUMP_W           = _D["pump"]["width"]
PUMP_H           = _D["pump"]["height"]
PUMP_MOTOR_D     = _D["pump"]["motor_section_diameter"]
PUMP_HEAD_D      = _D["pump"]["pump_head_diameter"]
PUMP_BRACKET_W   = _D["pump"]["bracket_width"]
PUMP_BRACKET_H   = _D["pump"]["bracket_height"]
PUMP_BRACKET_T   = _D["pump"]["bracket_thickness"]
PUMP_TUBE_D      = _D["pump"]["tube_fitting_diameter"]
PUMP_TUBE_L      = _D["pump"]["tube_fitting_length"]

# --- ToF sensor ---
TOF_W            = _D["tof_sensor"]["board_width"]
TOF_L            = _D["tof_sensor"]["board_length"]
TOF_H            = _D["tof_sensor"]["board_height"]
TOF_SENSOR_H     = _D["tof_sensor"]["sensor_module_height"]
TOF_HOLE_D       = _D["tof_sensor"]["mounting_hole_diameter"]
TOF_HOLE_SX      = _D["tof_sensor"]["mounting_hole_spacing_x"]
TOF_HOLE_SY      = _D["tof_sensor"]["mounting_hole_spacing_y"]
TOF_PIN_W        = _D["tof_sensor"]["pin_header_width"]
TOF_PIN_L        = _D["tof_sensor"]["pin_header_length"]
TOF_PIN_H        = _D["tof_sensor"]["pin_header_height"]

# --- Camera ---
CAM_W            = _D["camera"]["adapter_pcb_width"]
CAM_L            = _D["camera"]["adapter_pcb_length"]
CAM_H            = _D["camera"]["adapter_pcb_thickness"]
CAM_LENS_D       = _D["camera"]["lens_barrel_diameter"]
CAM_LENS_H       = _D["camera"]["lens_barrel_height"]
CAM_FPC_W        = _D["camera"]["fpc_connector_width"]
CAM_FPC_H        = _D["camera"]["fpc_connector_height"]

# --- Nose boom ---
BOOM_LENGTH      = _D["nose_boom"]["length"]
BOOM_WIDTH       = _D["nose_boom"]["width"]
BOOM_THICK       = _D["nose_boom"]["thickness"]
BOOM_FLANGE      = _D["nose_boom"]["flange_width"]
BOOM_WEB         = _D["nose_boom"]["web_width"]

# --- Assembly parameters ---
ESC_RADIAL_FRAC  = _D["assembly"]["esc_radial_fraction"]
KAGOME_CELL      = _D["assembly"]["kagome_cell_size"]
KAGOME_HOLE_R    = _D["assembly"]["kagome_hole_radius"]
KAGOME_WEB_MIN   = _D["assembly"]["kagome_min_web"]
KAGOME_FILLET_R  = _D["assembly"]["kagome_fillet_radius"]

# =============================================================================
# Z-height references (ground = 0)
# =============================================================================

GROUND_Z     = 0.0
LEG_TOP_Z    = GROUND_Z + FOOT_THICK + LEG_HEIGHT
BOTTOM_Z     = LEG_TOP_Z
TOP_Z        = BOTTOM_Z + BOTTOM_THICK + PLATE_SPACING
DE10_Z       = BOTTOM_Z + BOTTOM_THICK + DE10_STANDOFF
DB_Z         = DE10_Z + DE10_H + DB_ABOVE_DE10
ARM_CENTER_Z = BOTTOM_Z + BOTTOM_THICK + PLATE_SPACING / 2


# =============================================================================
# Component builders
# =============================================================================

def _kagome_cutouts(plate, thick, keepout_circles):
    """Apply Kagome-inspired triangular lattice cutouts to a plate."""
    half = PLATE_SIZE / 2 - 5

    row_h = KAGOME_CELL * math.sqrt(3) / 2
    centers = []
    row = 0
    y = -half + KAGOME_WEB_MIN
    while y < half - KAGOME_WEB_MIN:
        x_off = (KAGOME_CELL / 2) if (row % 2) else 0
        x = -half + KAGOME_WEB_MIN + x_off
        while x < half - KAGOME_WEB_MIN:
            clear = True
            for kcx, kcy, kr in keepout_circles:
                if math.hypot(x - kcx, y - kcy) < kr + KAGOME_HOLE_R + KAGOME_WEB_MIN:
                    clear = False
                    break
            if clear and math.hypot(x, y) > 12:
                centers.append((x, y))
            x += KAGOME_CELL
        y += row_h
        row += 1

    for cx, cy in centers:
        try:
            cutout = (
                cq.Workplane("XY")
                .center(cx, cy)
                .polygon(6, KAGOME_HOLE_R * 2)
                .extrude(thick)
            )
            plate = plate.cut(cutout)
        except Exception:
            pass

    try:
        plate = plate.edges("|Z").fillet(KAGOME_FILLET_R)
    except Exception:
        pass

    return plate


def make_skeleton_plate(thick, is_bottom=True):
    """Create a plate with Kagome-lattice cutouts for optimal stiffness/weight."""
    plate = (
        cq.Workplane("XY")
        .rect(PLATE_SIZE, PLATE_SIZE)
        .extrude(thick)
        .edges("|Z").fillet(PLATE_CORNER_R)
    )

    for angle in ARM_ANGLES:
        slot = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, angle))
            .rect(SLOT_W, SLOT_L)
            .extrude(thick)
        )
        plate = plate.cut(slot)

    keepouts = []
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        for dist in range(0, int(SLOT_L / 2) + 5, 8):
            keepouts.append((dist * math.cos(rad), dist * math.sin(rad), 8.0))

    if not is_bottom:
        central = (
            cq.Workplane("XY")
            .rect(72, 110)
            .extrude(thick)
            .edges("|Z").fillet(PLATE_CORNER_R)
        )
        plate = plate.cut(central)
        keepouts.append((0, 0, 58.0))
    else:
        for dy in [-20, 20]:
            strap = (
                cq.Workplane("XY")
                .center(0, dy)
                .rect(25, 3)
                .extrude(thick)
            )
            plate = plate.cut(strap)
            keepouts.append((0, dy, 15.0))

        for dx in [-DE10_W/2 + 4, DE10_W/2 - 4]:
            for dy in [-DE10_L/2 + 4, DE10_L/2 - 4]:
                hole = (
                    cq.Workplane("XY")
                    .center(dx, dy)
                    .circle(1.25)
                    .extrude(thick)
                )
                plate = plate.cut(hole)
                keepouts.append((dx, dy, 5.0))

    plate = _kagome_cutouts(plate, thick, keepouts)
    return plate


def make_arm():
    """Create an I-beam skeleton arm with motor mount holes at the tip."""
    arm = (
        cq.Workplane("XY")
        .rect(ARM_LENGTH, ARM_WIDTH)
        .extrude(ARM_THICK)
    )

    body_inner = -ARM_LENGTH / 2 + ARM_TAB
    body_outer = ARM_LENGTH / 2 - MOTOR_SECTION
    cutout_length = (body_outer - body_inner) - 10
    cutout_cx = (body_inner + body_outer) / 2
    cutout_width = (ARM_WIDTH - ARM_WEB) / 2 - ARM_FLANGE
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (ARM_WEB / 2 + ARM_FLANGE + cutout_width / 2)
            icut = (
                cq.Workplane("XY")
                .center(cutout_cx, cy)
                .rect(cutout_length, cutout_width)
                .extrude(ARM_THICK)
            )
            arm = arm.cut(icut)

    mx_center = ARM_LENGTH / 2 - MOTOR_SECTION / 2
    for dx in [-MOTOR_MOUNT_RECT[0]/2, MOTOR_MOUNT_RECT[0]/2]:
        for dy in [-MOTOR_MOUNT_RECT[1]/2, MOTOR_MOUNT_RECT[1]/2]:
            hole = (
                cq.Workplane("XY")
                .center(mx_center + dx, dy)
                .circle(1.6)
                .extrude(ARM_THICK)
            )
            arm = arm.cut(hole)

    return arm


def _capsule_2d(width, height, end_radius):
    """Create a 2D capsule (stadium) shape for lightening holes."""
    straight = height - 2 * end_radius
    if straight < 0:
        straight = 0
        end_radius = height / 2
    return (
        cq.Workplane("XZ")
        .moveTo(-width / 2, -straight / 2)
        .lineTo(-width / 2, straight / 2)
        .threePointArc((0, straight / 2 + end_radius), (width / 2, straight / 2))
        .lineTo(width / 2, -straight / 2)
        .threePointArc((0, -straight / 2 - end_radius), (-width / 2, -straight / 2))
        .close()
    )


def make_landing_leg():
    """Create an L-shaped landing gear leg with capsule lightening holes."""
    vertical = (
        cq.Workplane("XZ")
        .rect(LEG_WIDTH, LEG_HEIGHT)
        .extrude(LEG_THICK)
        .translate((0, 0, FOOT_THICK + LEG_HEIGHT / 2))
    )

    foot = (
        cq.Workplane("XY")
        .rect(LEG_WIDTH, FOOT_LENGTH)
        .extrude(FOOT_THICK)
        .translate((0, FOOT_LENGTH / 2 - LEG_THICK / 2, FOOT_THICK / 2))
    )

    leg = vertical.union(foot)

    usable_h = LEG_HEIGHT - 15
    spacing = usable_h / (LEG_HOLE_N + 1)
    for i in range(LEG_HOLE_N):
        zh = FOOT_THICK + 10 + spacing * (i + 1)
        try:
            capsule = _capsule_2d(LEG_HOLE_W, LEG_HOLE_H, LEG_HOLE_R)
            hole = capsule.center(0, zh).extrude(LEG_THICK)
            leg = leg.cut(hole)
        except Exception:
            hole = (
                cq.Workplane("XZ")
                .center(0, zh)
                .rect(LEG_HOLE_W, LEG_HOLE_H)
                .extrude(LEG_THICK)
            )
            leg = leg.cut(hole)

    return leg


def make_motor():
    """SunnySky X2212 980KV brushless outrunner motor.

    Geometry (bottom to top):
      1. Base mounting plate with 4x M3 bolt holes
      2. Stator cylinder (windings) centered on the base
      3. Outrunner bell — hollow cylinder with solid cap
      4. Shaft through center
      5. Prop adapter nub on top of bell cap
    """
    base_thick = 3.0

    # 1. Base mounting plate
    base = cq.Workplane("XY").circle(MOTOR_BASE_D / 2).extrude(base_thick)
    # 4x M3 bolt holes at mount_bolt_pattern rectangle positions
    for dx in [-MOTOR_MOUNT_RECT[0] / 2, MOTOR_MOUNT_RECT[0] / 2]:
        for dy in [-MOTOR_MOUNT_RECT[1] / 2, MOTOR_MOUNT_RECT[1] / 2]:
            hole = (
                cq.Workplane("XY")
                .center(dx, dy)
                .circle(1.5)
                .extrude(base_thick)
            )
            base = base.cut(hole)

    # 2. Stator cylinder (windings), sitting on top of the base plate
    stator = (
        cq.Workplane("XY")
        .workplane(offset=base_thick)
        .circle(MOTOR_STATOR_D / 2)
        .extrude(MOTOR_STATOR_H)
    )

    # 3. Outrunner bell — hollow cylinder for the full body height
    bell_inner_r = MOTOR_BELL_OD / 2 - MOTOR_BELL_T
    bell = (
        cq.Workplane("XY")
        .circle(MOTOR_BELL_OD / 2)
        .circle(bell_inner_r)
        .extrude(MOTOR_BODY_H)
    )
    # Solid cap at the top of the bell
    cap_thick = MOTOR_BELL_T
    cap = (
        cq.Workplane("XY")
        .workplane(offset=MOTOR_BODY_H - cap_thick)
        .circle(MOTOR_BELL_OD / 2)
        .extrude(cap_thick)
    )
    bell = bell.union(cap)

    # Assemble base + stator + bell
    motor = base.union(stator).union(bell)

    # Chamfer the top edge of the bell
    try:
        motor = motor.faces(">Z").chamfer(1.0)
    except Exception:
        pass

    # 4. Shaft through center (full body height + protrusion)
    shaft = cq.Workplane("XY").circle(MOTOR_SHAFT_D / 2).extrude(MOTOR_TOTAL_H)
    motor = motor.union(shaft)

    # 5. Prop adapter nub on top of the bell cap
    prop_adapter = (
        cq.Workplane("XY")
        .workplane(offset=MOTOR_BODY_H)
        .circle(MOTOR_PROP_ADAPT_D / 2)
        .extrude(MOTOR_PROP_ADAPT_H)
    )
    motor = motor.union(prop_adapter)

    return motor


def make_prop_hub():
    """GemFan 1045 propeller hub only."""
    return cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)


def _blade_chord_at(t):
    """Return chord width at normalised span station *t* (0=root, 1=tip).

    Linearly interpolates between three control points:
      root (t=0) -> max-chord (t=PROP_MAX_STATION) -> tip (t=1).
    """
    if t <= PROP_MAX_STATION:
        frac = t / PROP_MAX_STATION
        return PROP_ROOT_CHORD + frac * (PROP_MAX_CHORD - PROP_ROOT_CHORD)
    else:
        frac = (t - PROP_MAX_STATION) / (1.0 - PROP_MAX_STATION)
        return PROP_MAX_CHORD + frac * (PROP_TIP_CHORD - PROP_MAX_CHORD)


def _make_tapered_blade(flip=False):
    """Build one tapered-chord propeller blade along the +X axis.

    The blade is constructed from five extruded segments unioned together,
    each with the interpolated chord width at that radial station.
    If *flip* is True the blade is mirrored to the -X axis.
    """
    blade_length = (PROP_DIAMETER - PROP_HUB_D) / 2
    hub_r = PROP_HUB_D / 2
    n_segments = 5
    sign = -1.0 if flip else 1.0

    result = None
    for i in range(n_segments):
        t0 = i / n_segments
        t1 = (i + 1) / n_segments
        t_mid = (t0 + t1) / 2.0

        r_inner = hub_r + t0 * blade_length
        r_outer = hub_r + t1 * blade_length
        seg_len = r_outer - r_inner
        chord = _blade_chord_at(t_mid)

        cx = sign * (r_inner + seg_len / 2.0)
        seg = (
            cq.Workplane("XY")
            .center(cx, 0)
            .ellipse(seg_len / 2.0, chord / 2.0)
            .extrude(PROP_BLADE_T)
        )
        result = seg if result is None else result.union(seg)

    return result


def make_propeller():
    """GemFan 1045 — 2-blade prop with tapered-chord blades."""
    hub = cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)
    blade1 = _make_tapered_blade(flip=False)
    blade2 = _make_tapered_blade(flip=True)
    return hub.union(blade1).union(blade2)


def make_esc():
    """FVT LittleBee 30A BLHeli_32 — PCB body with solder pads."""
    # Main PCB body with filleted vertical edges
    body = (
        cq.Workplane("XY")
        .rect(ESC_L, ESC_W)
        .extrude(ESC_H)
        .edges("|Z").fillet(1)
    )

    # Solder pads: half on the +Y end (motor wires), half on the -Y end (power/signal)
    pads_per_end = ESC_PAD_N // 2
    # Evenly space pads across the width (X axis)
    spacing = ESC_W / (pads_per_end + 1)

    for end_sign in (+1, -1):
        # Y centre of each pad row: flush against the ESC edge
        pad_cy = end_sign * (ESC_L / 2 - ESC_PAD_L / 2)
        for i in range(pads_per_end):
            pad_cx = -ESC_W / 2 + spacing * (i + 1)
            pad = (
                cq.Workplane("XY")
                .center(pad_cx, pad_cy)
                .rect(ESC_PAD_W, ESC_PAD_L)
                .extrude(ESC_H + ESC_PAD_H)
            )
            body = body.union(pad)

    return body


def _intel_to_cq(intel_x, intel_y):
    """Convert Intel mechanical layout coords to CadQuery board-centered coords.

    Intel layout: x along 107mm length, y along 68.6mm width.
    CadQuery:     DE10_W (68.58) on x-axis, DE10_L (107.95) on y-axis.
    """
    cq_x = intel_y - DE10_W / 2
    cq_y = intel_x - DE10_L / 2
    return cq_x, cq_y


def make_de10_nano():
    """DE10-Nano FPGA board with mounting holes, GPIO headers, heatsink, and connectors."""
    connectors = _D["de10_nano"]["connectors"]
    hole_d = _D["de10_nano"]["mounting_hole_diameter"]
    hole_inset = _D["de10_nano"]["mounting_hole_inset"]

    # --- Main PCB ---
    board = (
        cq.Workplane("XY")
        .rect(DE10_W, DE10_L)
        .extrude(DE10_H)
        .edges("|Z").fillet(1)
    )

    # --- 4x M3 mounting holes (through-hole cutouts near corners) ---
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (DE10_W / 2 - hole_inset)
            hy = sy * (DE10_L / 2 - hole_inset)
            hole = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(hole_d / 2)
                .extrude(DE10_H)
            )
            board = board.cut(hole)

    # --- FPGA heatsink (centered on board) ---
    heatsink = (
        cq.Workplane("XY")
        .rect(HS_W, HS_L)
        .extrude(DE10_H + HS_H)
    )
    board = board.union(heatsink)

    # --- GPIO headers (2x20 pin) ---
    for key in ("gpio0", "gpio1"):
        c = connectors[key]
        cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
        # Header center: offset by half the header length along CQ y-axis
        header = (
            cq.Workplane("XY")
            .center(cx, cy + c["length"] / 2)
            .rect(c["width"], c["length"])
            .extrude(DE10_H + c["height"])
        )
        board = board.union(header)

    # --- Connectors as simple raised blocks ---
    for key in ("hdmi", "usb_otg", "ethernet", "barrel_jack"):
        c = connectors[key]
        cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
        block = (
            cq.Workplane("XY")
            .center(cx, cy)
            .rect(c["width"], c["length"])
            .extrude(DE10_H + c["height"])
        )
        board = board.union(block)

    return board


def make_daughter_board():
    """Daughter board — sensor hub, level shifters, power regulation."""
    board = (
        cq.Workplane("XY")
        .rect(DB_W, DB_L)
        .extrude(DB_H)
        .edges("|Z").fillet(1)
    )
    for pos in [(0, 20), (-15, -15), (15, -15), (0, -30)]:
        ic = (
            cq.Workplane("XY")
            .center(pos[0], pos[1])
            .rect(8, 8)
            .extrude(DB_H + 2)
        )
        board = board.union(ic)
    return board


def make_battery():
    """Tattu 4S 2200mAh 45C LiPo with XT60 connector bump."""
    # Main body with rounded vertical edges and smaller top-edge fillet
    body = (
        cq.Workplane("XY")
        .rect(BATT_W, BATT_L)
        .extrude(BATT_H)
        .edges("|Z").fillet(BATT_CORNER_R)
        .edges(">Z").fillet(min(BATT_CORNER_R * 0.5, 1.5))
    )
    # XT60 connector bump centred on the +Y face, at mid-height
    xt60_z = (BATT_H - BATT_XT60_H) / 2
    xt60 = (
        cq.Workplane("XY")
        .transformed(offset=(0, BATT_L / 2 + BATT_XT60_D / 2, xt60_z))
        .rect(BATT_XT60_W, BATT_XT60_D)
        .extrude(BATT_XT60_H)
    )
    return body.union(xt60)


def make_reservoir():
    """TPU collapsible 300ml water reservoir."""
    return (
        cq.Workplane("XY")
        .rect(RES_W, RES_L)
        .extrude(RES_H)
        .edges().fillet(5)
    )


def make_pump_bracket():
    """Pump mounting bracket — FR4."""
    return (
        cq.Workplane("XY")
        .rect(PUMP_BRACKET_W, PUMP_BRACKET_T)
        .extrude(PUMP_BRACKET_H)
    )


def make_pump():
    """Kamoer NKP-DC-S06B peristaltic pump with inlet/outlet tube fittings."""
    motor_len = PUMP_L * 0.6
    head_len = PUMP_L * 0.4

    # Motor section cylinder (rear)
    motor_section = (
        cq.Workplane("YZ")
        .circle(PUMP_MOTOR_D / 2)
        .extrude(motor_len)
        .translate((-PUMP_L / 2, 0, 0))
    )

    # Pump head cylinder (front, joined to motor section)
    head = (
        cq.Workplane("YZ")
        .circle(PUMP_HEAD_D / 2)
        .extrude(head_len)
        .translate((-PUMP_L / 2 + motor_len, 0, 0))
    )

    pump = motor_section.union(head)

    # Tube fittings — two barbs protruding upward from the pump head top
    head_center_x = -PUMP_L / 2 + motor_len + head_len / 2
    fitting_spacing = PUMP_HEAD_D * 0.35
    head_top_z = PUMP_HEAD_D / 2

    for dx in [-fitting_spacing, fitting_spacing]:
        fitting = (
            cq.Workplane("XY")
            .center(head_center_x + dx, 0)
            .circle(PUMP_TUBE_D / 2)
            .extrude(head_top_z + PUMP_TUBE_L)
        )
        pump = pump.union(fitting)

    return pump


def make_tof_board():
    """VL53L1X Pololu carrier #3415 — PCB with mounting holes, sensor, and pin header."""
    # PCB substrate
    board = cq.Workplane("XY").rect(TOF_W, TOF_L).extrude(TOF_H)

    # Mounting holes — two at opposite corners (Pololu #3415 layout)
    for sx, sy in [(-1, -1), (1, 1)]:
        hole = (
            cq.Workplane("XY")
            .center(sx * TOF_HOLE_SX / 2, sy * TOF_HOLE_SY / 2)
            .circle(TOF_HOLE_D / 2)
            .extrude(TOF_H)
        )
        board = board.cut(hole)

    # VL53L1X sensor module (4.4 x 2.4 mm optical aperture), offset toward +Y end
    sensor = (
        cq.Workplane("XY")
        .center(0, TOF_L / 2 - 4.0)
        .rect(4.4, 2.4)
        .extrude(TOF_H + TOF_SENSOR_H)
    )

    # Pin header strip on bottom (-Z), along -Y edge of board
    pin_header = (
        cq.Workplane("XY")
        .center(0, -(TOF_L / 2 - TOF_PIN_L / 2))
        .rect(TOF_PIN_W, TOF_PIN_L)
        .extrude(-TOF_PIN_H)
    )

    return board.union(sensor).union(pin_header)


# --- ToF bracket constants ---
TOF_BRACKET_BASE   = 15    # mm, base face width (attaches to frame plate)
TOF_BRACKET_TAB    = 15    # mm, vertical tab width (holds ToF board)
TOF_BRACKET_DEPTH  = 20    # mm, depth of both faces
TOF_BRACKET_T      = 1.6   # mm, FR4 thickness
TOF_BRACKET_HOLE_D = 2.0   # mm, M2 hole diameter


def make_tof_bracket():
    """L-shaped ToF sensor mounting bracket — FR4 PCB, 1.6mm thick.

    Two rectangular faces at 90 degrees:
      - Base face (XY plane): 15 x 20 mm, attaches to frame plate via 2x M2 holes
      - Vertical tab (XZ plane): 15 x 20 mm, holds ToF board via 2x M2 holes
    """
    # Base face — lies flat on the frame plate
    base = (
        cq.Workplane("XY")
        .rect(TOF_BRACKET_BASE, TOF_BRACKET_DEPTH)
        .extrude(TOF_BRACKET_T)
    )
    # 2x M2 mounting holes in base
    base = (
        base.faces(">Z").workplane()
        .pushPoints([(0, -5), (0, 5)])
        .hole(TOF_BRACKET_HOLE_D)
    )

    # Vertical tab — perpendicular to base, rises from one edge
    tab = (
        cq.Workplane("XZ")
        .center(0, TOF_BRACKET_T + TOF_BRACKET_TAB / 2)
        .rect(TOF_BRACKET_BASE, TOF_BRACKET_TAB)
        .extrude(TOF_BRACKET_T)
        .translate((0, TOF_BRACKET_DEPTH / 2 - TOF_BRACKET_T, 0))
    )
    # 2x M2 mounting holes in tab
    tab = (
        tab.faces(">Y").workplane()
        .pushPoints([(0, -5), (0, 5)])
        .hole(TOF_BRACKET_HOLE_D)
    )

    return base.union(tab)


def make_standoff(h):
    """M2.5 hex standoff."""
    return cq.Workplane("XY").polygon(6, 5).extrude(h)


def make_drip_nozzle():
    """Adjustable drip emitter — cone shape."""
    base = cq.Workplane("XY").circle(5).extrude(5)
    tip = (
        cq.Workplane("XY")
        .workplane(offset=5)
        .circle(4)
        .workplane(offset=12)
        .circle(1.5)
        .loft()
    )
    try:
        return base.union(tip)
    except Exception:
        return cq.Workplane("XY").circle(4).extrude(15)


def make_camera():
    """OV5640 camera on adapter PCB — lens facing DOWN (-Z), FPC connector on top."""
    # Adapter PCB with small corner fillets
    pcb = (
        cq.Workplane("XY")
        .rect(CAM_W, CAM_L)
        .extrude(CAM_H)
        .edges("|Z")
        .fillet(0.5)
    )
    # Lens barrel on bottom face, centered, extending in -Z
    lens = (
        cq.Workplane("XY")
        .circle(CAM_LENS_D / 2)
        .extrude(-CAM_LENS_H)
    )
    # FPC connector block on top face (+Z), at -Y edge of PCB
    fpc_depth = 5.0
    fpc = (
        cq.Workplane("XY")
        .workplane(offset=CAM_H)
        .center(0, -CAM_L / 2 + fpc_depth / 2)
        .rect(CAM_FPC_W, fpc_depth)
        .extrude(CAM_FPC_H)
    )
    return pcb.union(lens).union(fpc)


def make_nose_boom():
    """Forward-extending PCB boom arm with I-beam skeleton profile."""
    boom = (
        cq.Workplane("XY")
        .rect(BOOM_LENGTH, BOOM_WIDTH)
        .extrude(BOOM_THICK)
    )
    cutout_length = BOOM_LENGTH - 60
    cutout_width = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_width / 2)
            icut = (
                cq.Workplane("XY")
                .center(0, cy)
                .rect(cutout_length, cutout_width)
                .extrude(BOOM_THICK)
            )
            boom = boom.cut(icut)
    return boom


def make_tubing_segment(length):
    """Silicone tubing segment (3mm ID x 5mm OD)."""
    return (
        cq.Workplane("XY")
        .circle(2.5)
        .circle(1.5)
        .extrude(length)
    )


# =============================================================================
# Assembly
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
    leg = make_landing_leg()
    for i, angle in enumerate(LEG_ANGLES):
        rad = math.radians(angle)
        lx = (PLATE_SIZE / 2 + 2) * math.cos(rad)
        ly = (PLATE_SIZE / 2 + 2) * math.sin(rad)
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

    # ── Reservoir (forward of center, near pump/boom) ──
    assy.add(make_reservoir(), loc=cq.Location((RES_OFFSET_X, 0, BOTTOM_Z - RES_H - 3)),
             name="reservoir", color=cq.Color(0.3, 0.6, 0.9, 0.6))

    # ── Pump ──
    assy.add(make_pump_bracket(),
             loc=cq.Location((PLATE_SIZE / 2 - 5, 0, BOTTOM_Z - PUMP_BRACKET_H)),
             name="pump_bracket", color=cq.Color(0.1, 0.45, 0.15, 1.0))

    assy.add(make_pump(),
             loc=cq.Location((PLATE_SIZE / 2 - 5, -(PUMP_BRACKET_T + PUMP_W / 2),
                              BOTTOM_Z - PUMP_BRACKET_H / 2)),
             name="pump", color=cq.Color(0.3, 0.3, 0.3, 1.0))

    # ── Nose Boom ──
    boom_center_x = PLATE_SIZE / 2 + BOOM_LENGTH / 2
    assy.add(make_nose_boom(),
             loc=cq.Location((boom_center_x, 0, ARM_CENTER_Z - BOOM_THICK / 2), (0, 0, 0)),
             name="nose_boom", color=cq.Color(0.1, 0.45, 0.15, 1.0))

    # ── Camera (under boom, lens facing down) ──
    cam_x = PLATE_SIZE / 2 + 30
    cam_z = ARM_CENTER_Z - BOOM_THICK / 2 - 2
    assy.add(make_camera(), loc=cq.Location((cam_x, 0, cam_z)),
             name="camera", color=cq.Color(0.1, 0.1, 0.1, 1.0))

    # ── Tubing along boom ──
    assy.add(make_tubing_segment(BOOM_LENGTH - 30),
             loc=cq.Location((boom_center_x, 0, ARM_CENTER_Z - BOOM_THICK / 2 - 4), (0, 90, 0)),
             name="tubing", color=cq.Color(0.8, 0.8, 0.85, 0.7))

    # ── Drip nozzle at boom tip ──
    nozzle_x = PLATE_SIZE / 2 + BOOM_LENGTH
    assy.add(make_drip_nozzle(),
             loc=cq.Location((nozzle_x, 0, ARM_CENTER_Z - BOOM_THICK / 2 - 5), (180, 0, 0)),
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
    out_dir = Path(__file__).resolve().parent.parent / "cad" / "exports"
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
