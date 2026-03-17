"""Custom daughter board — sensor hub, level shifters, power regulation.

Mounts above DE10-Nano via M2.5 standoffs at the same hole pattern.
Two 2x20 GPIO receptacle headers connect to DE10-Nano GPIO0 and GPIO1.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

try:
    import cadquery as cq
except ImportError:
    cq = None

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

from cadquery_framework.kicad.jlcpcb_constraints import (
    CU_OUTER_MM, CU_INNER_MM,
    PREPREG_THICKNESS_MM, PREPREG_MATERIAL, PREPREG_DK, PREPREG_LOSS_TANGENT,
    CORE_THICKNESS_MM, CORE_MATERIAL, CORE_DK, CORE_LOSS_TANGENT,
    SOLDER_MASK_THICKNESS_MM, SOLDER_MASK_EXPANSION_MM, SOLDER_MASK_MIN_WIDTH_MM,
    TH_GPIO_DRILL_MM, TH_GPIO_PAD_MM, TH_M25_DRILL_MM, TH_M25_PAD_MM,
    EDGE_CUTS_WIDTH_MM, COURTYARD_WIDTH_MM,
    SILK_LARGE_SIZE_MM, SILK_LARGE_THICK_MM,
    SILK_REF_SIZE_MM, SILK_REF_THICK_MM,
    SILK_SMALL_SIZE_MM, SILK_SMALL_THICK_MM,
    SILK_MICRO_SIZE_MM, SILK_MICRO_THICK_MM,
    SILK_FAB_SIZE_MM, SILK_FAB_THICK_MM,
    DRM_MIN_TRACE_MM, JLCPCB_MIN_DRILL_MM,
)

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

DB_W = _D["daughter_board"]["width"]
DB_L = _D["daughter_board"]["length"]
DB_H = _D["daughter_board"]["pcb_thickness"]

# Mounting holes — same pattern as DE10-Nano
DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
DB_MOUNT_HOLE_D = _D["daughter_board_mounting"]["mounting_hole_diameter"]
DB_MOUNT_INSET  = _D["daughter_board_mounting"]["mounting_hole_inset"]

# GPIO header receptacles
GPIO_PITCH  = _D["daughter_board_mounting"]["gpio_receptacle_pitch"]
GPIO_ROWS   = _D["daughter_board_mounting"]["gpio_receptacle_rows"]
GPIO_COLS   = _D["daughter_board_mounting"]["gpio_receptacle_cols"]
GPIO_LENGTH = (GPIO_COLS - 1) * GPIO_PITCH  # 48.26mm for 2x20
GPIO_WIDTH  = (GPIO_ROWS - 1) * GPIO_PITCH  # 2.54mm for 2-row
GPIO_HEADER_H = 8.5  # receptacle housing height (extends downward toward DE10)

_PLATE_SIZE = _D["frame"]["plate_size"]  # 110.0 — combined PCB is the full top plate

CATALOG = {
    "daughter_board": {
        "material": "FR4 PCB + components",
        "dims": f"{_PLATE_SIZE:.0f} x {_PLATE_SIZE:.0f} x {DB_H}mm",
        "mass_g": 45, "qty": 1,
        "supplier": "Custom PCB (JLCPCB)",
        "notes": "Combined top plate + daughter board: Kagome frame, sensor hub, power regulators",
        "interface": "Structural top plate + DE10-Nano daughter board in one PCB",
    },
}


def make_daughter_board():
    """Daughter board with M2.5 mounting holes, GPIO receptacles, and IC footprints."""
    pcb_chamfer = _D["assembly"]["pcb_edge_chamfer"]
    board_chamfer = min(pcb_chamfer, DB_H * 0.45)
    board = (
        cq.Workplane("XY")
        .rect(DB_W, DB_L)
        .extrude(DB_H)
        .edges("|Z")
        .chamfer(board_chamfer)
    )

    # M2.5 mounting holes (match DE10-Nano corner pattern)
    for dx in [-DE10_W/2 + DB_MOUNT_INSET, DE10_W/2 - DB_MOUNT_INSET]:
        for dy in [-DE10_L/2 + DB_MOUNT_INSET, DE10_L/2 - DB_MOUNT_INSET]:
            hole = (
                cq.Workplane("XY")
                .center(dx, dy)
                .circle(DB_MOUNT_HOLE_D / 2)
                .extrude(DB_H)
            )
            board = board.cut(hole)

    # GPIO receptacle headers (2x20, extending downward to mate with DE10-Nano)
    # Use Intel-to-CQ coordinate transform matching de10_nano.py
    gpio_connectors = _D["de10_nano"]["connectors"]
    for key in ("gpio0", "gpio1"):
        c = gpio_connectors[key]
        # Intel layout: x along 107mm length, y along 68.6mm width
        cq_x = DE10_W / 2 - c["intel_y"]
        cq_y = c["intel_x"] - DE10_L / 2
        # Header block extending downward (negative Z)
        header = (
            cq.Workplane("XY")
            .center(cq_x, cq_y + c["length"] / 2)
            .rect(GPIO_WIDTH + 2.0, c["length"] + 2.0)
            .extrude(-GPIO_HEADER_H)
            .edges("|Z")
            .chamfer(min(0.6, pcb_chamfer))
        )
        board = board.union(header)

    # Arduino header receptacles (extend downward to mate with DE10 Arduino headers)
    for key in ("arduino_digital_hi", "arduino_digital_lo", "arduino_analog", "arduino_power"):
        if key not in gpio_connectors:
            continue
        c = gpio_connectors[key]
        cq_x = DE10_W / 2 - c["intel_y"]
        cq_y = c["intel_x"] - DE10_L / 2
        ard_header = (
            cq.Workplane("XY")
            .center(cq_x, cq_y)
            .rect(c["width"] + 2.0, c["length"] + 2.0)
            .extrude(-GPIO_HEADER_H)
            .edges("|Z")
            .chamfer(min(0.6, pcb_chamfer))
        )
        board = board.union(ard_header)

    # NOTE: No heatsink cutout — the 8.5mm standoff gap between DE10-Nano and
    # daughter board provides clearance for the heatsink.  Components are placed
    # on the PCB surface above the heatsink zone.

    # IC / connector component blocks — rendered from the actual netlist placements
    # Coordinate transform: netlist uses top-left origin (0,0), CQ uses board centre
    from drone_design.drone_model.components.electronics.daughter_board_netlist import PLACEMENTS
    _hs_half_w = (_D["de10_nano"]["heatsink_width"] + 4) / 2
    _hs_half_l = (_D["de10_nano"]["heatsink_length"] + 4) / 2
    for p in PLACEMENTS:
        cw = p.component.courtyard_w
        ch = p.component.courtyard_h
        if cw < 1.5 and ch < 1.5:
            continue  # skip tiny passives (0402, 0603) for rendering speed
        cx = p.x - DB_W / 2
        cy = p.y - DB_L / 2
        # Skip components that overlap the heatsink cutout
        if (abs(cx) < _hs_half_w + cw / 2 and abs(cy) < _hs_half_l + ch / 2):
            continue
        ic_h = 2.0 if cw > 3.0 else 1.2  # taller block for larger ICs
        ic = (
            cq.Workplane("XY")
            .center(cx, cy)
            .rect(cw, ch)
            .extrude(DB_H + ic_h)
        )
        board = board.union(ic)

    # Anchor points
    anchors = {}
    if Anchor is not None:
        anchors["bottom_face"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Daughter board bottom mates with DE10 headers")
        # Top face at tallest IC block height — used for top plate clearance chain
        _ic_top = DB_H + 2.0  # PCB + tallest component height (large IC blocks)
        anchors["top_face"] = Anchor(point=(0, 0, _ic_top), normal=(0, 0, 1), label="Tallest point on daughter board")

        # Mounting holes matching DE10-Nano corner pattern (bottom — mates lower standoffs)
        idx = 1
        for dx in [-DE10_W/2 + DB_MOUNT_INSET, DE10_W/2 - DB_MOUNT_INSET]:
            for dy in [-DE10_L/2 + DB_MOUNT_INSET, DE10_L/2 - DB_MOUNT_INSET]:
                anchors[f"mounting_hole_{idx}"] = Anchor(
                    point=(dx, dy, 0), normal=(0, 0, -1),
                    label=f"M2.5 mounting hole {idx} (bottom)")
                # Upper standoff mount point — top of PCB at same XY
                anchors[f"standoff_top_{idx}"] = Anchor(
                    point=(dx, dy, DB_H), normal=(0, 0, 1),
                    label=f"upper standoff mount {idx} (top)")
                idx += 1

        # ToF-up mount on top surface corner — -X side to avoid ethernet (+X)
        anchors["tof_mount_up"] = Anchor(
            point=(-(DB_W / 2 - 8), DB_L / 2 - 8, _ic_top),
            normal=(0, 0, 1),
            label="ToF up — board direct-mount on daughter board top surface, sensor faces +Z",
        )

        # GPIO receptacles at same positions as DE10 headers, pointing down
        for key, anchor_name in (("gpio0", "gpio0_receptacle"), ("gpio1", "gpio1_receptacle")):
            c = gpio_connectors[key]
            cq_x = DE10_W / 2 - c["intel_y"]
            cq_y = c["intel_x"] - DE10_L / 2
            anchors[anchor_name] = Anchor(
                point=(cq_x, cq_y + c["length"] / 2, 0),
                normal=(0, 0, -1),
                label=f"{key.upper()} receptacle (PCB bottom, mates header top)")

    return board, anchors


# =============================================================================
# KiCad PCB generator — production-quality output from BoardDefinition
# =============================================================================

try:
    from cadquery_framework.kicad.primitives import (
        rounded_rect_outline, outline_to_sexpr,
        text_sexpr,
    )
    import uuid as _uuid
    _KI_AVAIL = True
except ImportError:
    _KI_AVAIL = False

from collections import defaultdict

from cadquery_framework.kicad.component_library import (
    BoardDefinition,
    Placement as CompPlacement,
    PadGeometry,
)


def _uid():
    return str(_uuid.uuid4())


def _net_sexpr(net_id, net_name):
    """KiCad net declaration."""
    return f'  (net {net_id} "{net_name}")'


# ---------------------------------------------------------------------------
# Pad S-expression generation from PadGeometry + net assignment
# ---------------------------------------------------------------------------

def _pad_sexpr(pad: PadGeometry, net_id: int, net_name: str,
               pin1: bool = False) -> str:
    """Generate KiCad pad S-expression from PadGeometry dataclass."""
    shape = pad.shape
    # Pin 1 of through-hole components uses square pad
    if pin1 and pad.pad_type == "thru_hole":
        shape = "rect"

    layers_str = " ".join(f'"{l}"' for l in pad.layers)

    parts = [
        f'    (pad "{pad.number}" {pad.pad_type} {shape}',
        f' (at {pad.x:.4f} {pad.y:.4f})',
        f' (size {pad.width:.3f} {pad.height:.3f})',
    ]

    if pad.drill > 0:
        parts.append(f' (drill {pad.drill:.2f})')

    if shape == "roundrect" and pad.roundrect_rratio > 0:
        parts.append(f' (roundrect_rratio {pad.roundrect_rratio:.3f})')

    parts.append(f' (layers {layers_str})')

    if net_name:
        parts.append(f' (net {net_id} "{net_name}")')

    parts.append(f' (uuid "{_uid()}"))')

    return "".join(parts)


# ---------------------------------------------------------------------------
# Footprint generation from Placement + net map
# ---------------------------------------------------------------------------

def _footprint_sexpr(placement: CompPlacement,
                     pin_net_map: dict[str, str],
                     net_ids: dict[str, int],
                     silk_offsets: dict[str, tuple[float, float]] | None = None) -> str:
    """Generate complete footprint S-expression for a placed component.

    Uses real pad geometry from ComponentDef, with net assignments from
    the pin_net_map.
    """
    comp = placement.component
    ref = placement.ref
    layer_prefix = placement.side  # "F" or "B"

    # Courtyard dimensions
    hw = comp.courtyard_w / 2
    hh = comp.courtyard_h / 2

    lines = []
    lines.append(
        f'  (footprint "custom:{comp.package}:{comp.mpn}" '
        f'(layer "{layer_prefix}.Cu") (uuid "{_uid()}")'
    )
    lines.append(f'  (at {placement.x:.4f} {placement.y:.4f} {placement.rotation:.1f})')
    lines.append(f'  (descr "{comp.description}")')

    # Reference designator on silkscreen (auto-repositioned if offsets provided)
    if silk_offsets and ref in silk_offsets:
        silk_dx, silk_dy = silk_offsets[ref]
    else:
        silk_dx, silk_dy = 0.0, -hh - 1.0
    lines.append(
        f'    (fp_text reference "{ref}" (at {silk_dx:.3f} {silk_dy:.3f}) '
        f'(layer "{layer_prefix}.SilkS") (uuid "{_uid()}")\n'
        f'      (effects (font (size {SILK_MICRO_SIZE_MM} {SILK_MICRO_SIZE_MM}) '
        f'(thickness {SILK_MICRO_THICK_MM})))\n'
        f'    )'
    )

    # Value on fab layer
    lines.append(
        f'    (fp_text value "{comp.value}" (at 0 {hh + 0.8:.3f}) '
        f'(layer "{layer_prefix}.Fab") (uuid "{_uid()}")\n'
        f'      (effects (font (size {SILK_FAB_SIZE_MM} {SILK_FAB_SIZE_MM}) '
        f'(thickness {SILK_FAB_THICK_MM})))\n'
        f'    )'
    )

    # Courtyard rectangle
    lines.append(
        f'    (fp_line (start {-hw:.3f} {-hh:.3f}) (end {hw:.3f} {-hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))'
    )
    lines.append(
        f'    (fp_line (start {hw:.3f} {-hh:.3f}) (end {hw:.3f} {hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))'
    )
    lines.append(
        f'    (fp_line (start {hw:.3f} {hh:.3f}) (end {-hw:.3f} {hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))'
    )
    lines.append(
        f'    (fp_line (start {-hw:.3f} {hh:.3f}) (end {-hw:.3f} {-hh:.3f}) '
        f'(layer "{layer_prefix}.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))'
    )

    # Pin-1 indicator (small triangle on silkscreen)
    if comp.pads:
        p1 = comp.pads[0]
        lines.append(
            f'    (fp_line (start {p1.x - 0.3:.3f} {p1.y - 0.5:.3f}) '
            f'(end {p1.x + 0.3:.3f} {p1.y - 0.5:.3f}) '
            f'(layer "{layer_prefix}.SilkS") (width {SILK_MICRO_THICK_MM}) (uuid "{_uid()}"))'
        )

    # All pads with net assignments
    for pad in comp.pads:
        net_name = pin_net_map.get(pad.number, "")
        net_id = net_ids.get(net_name, 0) if net_name else 0
        is_pin1 = (pad.number == comp.pads[0].number)
        lines.append(_pad_sexpr(pad, net_id, net_name, pin1=is_pin1))

    # 3D model reference (if component has one defined)
    if placement.component.model_3d:
        model_path = f"${{KIPRJMOD}}/models_3d/step/{placement.component.model_3d}.step"
        lines.append(
            f'  (model "{model_path}"\n'
            f'    (offset (xyz 0 0 0))\n'
            f'    (scale (xyz 1 1 1))\n'
            f'    (rotate (xyz 0 0 0))\n'
            f'  )'
        )

    lines.append('  )')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Copper zone pour S-expression
# ---------------------------------------------------------------------------

def _zone_pour(net_id: int, net_name: str, layer: str,
               points: list[tuple[float, float]],
               priority: int = 0) -> str:
    """Generate a filled copper zone pour."""
    pts = " ".join(f'(xy {x:.4f} {y:.4f})' for x, y in points)
    return (
        f'  (zone (net {net_id}) (net_name "{net_name}") (layer "{layer}") '
        f'(uuid "{_uid()}") (hatch edge 0.5)\n'
        f'    (priority {priority})\n'
        f'    (connect_pads (clearance 0.2))\n'
        f'    (fill yes (thermal_gap 0.25) (thermal_bridge_width 0.25))\n'
        f'    (polygon (pts {pts}))\n'
        f'  )'
    )


# ---------------------------------------------------------------------------
# Via stitching S-expression
# ---------------------------------------------------------------------------

def _via_sexpr(x: float, y: float, net_id: int, net_name: str,
               drill: float = 0.3, size: float = 0.6) -> str:
    """Generate a via S-expression."""
    return (
        f'  (via (at {x:.4f} {y:.4f}) (size {size:.2f}) (drill {drill:.2f}) '
        f'(layers "F.Cu" "B.Cu") (net {net_id}) (uuid "{_uid()}"))'
    )


# ---------------------------------------------------------------------------
# 4-layer PCB wrapper (unchanged stackup)
# ---------------------------------------------------------------------------

def _kicad_pcb_4layer(title, thickness, nets_block, content):
    """Full .kicad_pcb wrapper with a proper 4-layer stackup for an electrical PCB."""
    from datetime import datetime
    return f"""(kicad_pcb (version 20241228) (generator "pcbnew") (generator_version "9.0")
  (general
    (thickness {thickness:.2f})
    (legacy_teardrops no)
  )
  (paper "A4")
  (title_block
    (title "{title}")
    (date "{datetime.now().strftime('%Y-%m-%d')}")
    (rev "1.0")
    (company "Drone Project")
    (comment 1 "Material: FR4, Tg150")
    (comment 2 "Layers: 4  Thickness: {thickness:.1f}mm  Finish: ENIG")
    (comment 3 "Min trace: {DRM_MIN_TRACE_MM}mm  Min space: {DRM_MIN_TRACE_MM}mm  Min drill: {JLCPCB_MIN_DRILL_MM}mm via / {TH_GPIO_DRILL_MM}mm TH")
    (comment 4 "Stackup: F.Cu(sig) / In1.Cu(GND) / In2.Cu(PWR) / B.Cu(sig)")
  )
  (layers
    (0  "F.Cu"          signal    "Front copper - signal routing")
    (1  "In1.Cu"        power     "Inner layer 1 - GND plane")
    (2  "In2.Cu"        power     "Inner layer 2 - PWR plane (+3V3 / +5V / +1V8)")
    (31 "B.Cu"          signal    "Back copper - signal routing")
    (32 "B.Adhes"       user      "B.Adhesive")
    (33 "F.Adhes"       user      "F.Adhesive")
    (34 "B.Paste"       user)
    (35 "F.Paste"       user)
    (36 "B.SilkS"       user      "B.Silkscreen")
    (37 "F.SilkS"       user      "F.Silkscreen")
    (38 "B.Mask"        user      "B.Mask")
    (39 "F.Mask"        user      "F.Mask")
    (40 "Dwgs.User"     user      "User.Drawings")
    (41 "Cmts.User"     user      "User.Comments")
    (42 "Eco1.User"     user      "User.Eco1")
    (43 "Eco2.User"     user      "User.Eco2")
    (44 "Edge.Cuts"     user)
    (45 "Margin"        user)
    (46 "B.CrtYd"       user      "B.Courtyard")
    (47 "F.CrtYd"       user      "F.Courtyard")
    (48 "B.Fab"         user)
    (49 "F.Fab"         user)
  )
  (setup
    (stackup
      (layer "F.SilkS"      (type "Top Silk Screen"))
      (layer "F.Paste"       (type "Top Solder Paste"))
      (layer "F.Mask"        (type "Top Solder Mask")    (thickness {SOLDER_MASK_THICKNESS_MM}))
      (layer "F.Cu"          (type "copper")             (thickness {CU_OUTER_MM}))
      (layer "dielectric 1"  (type "prepreg")            (thickness {PREPREG_THICKNESS_MM}) (material "{PREPREG_MATERIAL}") (epsilon_r {PREPREG_DK}) (loss_tangent {PREPREG_LOSS_TANGENT}))
      (layer "In1.Cu"        (type "copper")             (thickness {CU_INNER_MM}))
      (layer "dielectric 2"  (type "core")               (thickness {CORE_THICKNESS_MM})  (material "{CORE_MATERIAL}") (epsilon_r {CORE_DK}) (loss_tangent {CORE_LOSS_TANGENT}))
      (layer "In2.Cu"        (type "copper")             (thickness {CU_INNER_MM}))
      (layer "dielectric 3"  (type "prepreg")            (thickness {PREPREG_THICKNESS_MM}) (material "{PREPREG_MATERIAL}") (epsilon_r {PREPREG_DK}) (loss_tangent {PREPREG_LOSS_TANGENT}))
      (layer "B.Cu"          (type "copper")             (thickness {CU_OUTER_MM}))
      (layer "B.Mask"        (type "Bottom Solder Mask") (thickness {SOLDER_MASK_THICKNESS_MM}))
      (layer "B.Paste"       (type "Bottom Solder Paste"))
      (layer "B.SilkS"       (type "Bottom Silk Screen"))
    )
    (pad_to_mask_clearance {SOLDER_MASK_EXPANSION_MM})
    (solder_mask_min_width {SOLDER_MASK_MIN_WIDTH_MM})
    (allow_soldermask_bridges_in_footprints no)
    (aux_axis_origin 0 0)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions yes)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (svgprecision 4)
      (excludeedgelayer yes)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (dxfpolygonmode yes)
      (dxfimperialunits yes)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotfptext no)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk yes)
      (outputformat 1)
      (mirror no)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "gerber/")
    )
  )

{nets_block}

{content}
)
"""


def _outer_boundary_with_prop_arcs(bw, bh, cr, dims, arm_angles, plate_size):
    """Build the outer board boundary with propeller arc cutouts replacing corners.

    Instead of a full rounded rectangle + appended arcs (which creates
    overlapping Edge.Cuts segments), this builds a single closed boundary
    where each corner is replaced by the propeller clearance arc.

    Boundary goes clockwise: right edge → 45° arc → top edge → 135° arc →
    left edge → 225° arc → bottom edge → 315° arc.
    """
    half = plate_size / 2  # 55mm
    motor_r = dims["arms"]["motor_to_motor_diagonal"] / 2  # 110mm
    prop_r = (dims["propeller"]["diameter"] / 2
              + dims.get("motor_riser", {}).get("prop_clearance_margin", 3.0))  # 54mm

    def _intersect_edge(mx, my, edge_axis, edge_val, half_plate):
        """Find where propeller circle intersects a board edge.

        edge_axis='x' means vertical edge at x=edge_val.
        edge_axis='y' means horizontal edge at y=edge_val.
        Returns list of (x, y) points on the board edge.
        """
        pts = []
        if edge_axis == "x":
            dx = edge_val - mx
            if abs(dx) < prop_r:
                dy = math.sqrt(prop_r ** 2 - dx ** 2)
                for sign in [1, -1]:
                    iy = my + sign * dy
                    if -half_plate <= iy <= half_plate:
                        pts.append((edge_val, iy))
        else:  # y
            dy = edge_val - my
            if abs(dy) < prop_r:
                ddx = math.sqrt(prop_r ** 2 - dy ** 2)
                for sign in [1, -1]:
                    ix = mx + sign * ddx
                    if -half_plate <= ix <= half_plate:
                        pts.append((ix, edge_val))
        return pts

    # For each corner motor, find the intersection on each adjacent edge.
    # Map: corner_angle → {edge1_pt, edge2_pt, motor_centre, arc_angles}
    # 45° motor  → intersects right edge (x=+half) and top edge (y=+half)
    # 135° motor → intersects top edge (y=+half) and left edge (x=-half)
    # 225° motor → intersects left edge (x=-half) and bottom edge (y=-half)
    # 315° motor → intersects bottom edge (y=-half) and right edge (x=+half)

    corner_data = {}  # angle → dict with edge intersection points + arc params

    for angle_deg in arm_angles:
        rad = math.radians(angle_deg)
        mx = motor_r * math.cos(rad)
        my = motor_r * math.sin(rad)

        # Determine the two adjacent edges for this corner
        if angle_deg == 45:
            edges = [("x", half), ("y", half)]  # right, top
        elif angle_deg == 135:
            edges = [("y", half), ("x", -half)]  # top, left
        elif angle_deg == 225:
            edges = [("x", -half), ("y", -half)]  # left, bottom
        elif angle_deg == 315:
            edges = [("y", -half), ("x", half)]  # bottom, right
        else:
            continue

        pts_per_edge = {}
        for axis, val in edges:
            hits = _intersect_edge(mx, my, axis, val, half)
            if hits:
                # Take the point closest to the corner
                corner_x = half if mx > 0 else -half
                corner_y = half if my > 0 else -half
                hits.sort(key=lambda p: math.hypot(p[0] - corner_x, p[1] - corner_y))
                pts_per_edge[(axis, val)] = hits[0]

        if len(pts_per_edge) == 2:
            edge_keys = list(pts_per_edge.keys())
            p1 = pts_per_edge[edge_keys[0]]
            p2 = pts_per_edge[edge_keys[1]]

            # Arc angles from motor centre
            a1 = math.degrees(math.atan2(p1[1] - my, p1[0] - mx))
            a2 = math.degrees(math.atan2(p2[1] - my, p2[0] - mx))

            # Determine correct arc direction (the one containing the board corner)
            corner_x = half if mx > 0 else -half
            corner_y = half if my > 0 else -half
            ca = math.degrees(math.atan2(corner_y - my, corner_x - mx))

            def _in_ccw_arc(s, e, t):
                s, e, t = s % 360, e % 360, t % 360
                return (s <= t <= e) if s <= e else (t >= s or t <= e)

            if _in_ccw_arc(a1, a2, ca):
                sa, ea = a1, a2
            else:
                sa, ea = a2, a1

            # Store edge→point mapping (stable, not affected by arc direction)
            corner_data[angle_deg] = {
                "mx": mx, "my": my, "r": prop_r,
                "sa": sa, "ea": ea,
                "edge_pts": dict(pts_per_edge),  # {edge_key: (x, y)}
            }

    # Now build the boundary. Each edge is trimmed between two corner arcs.
    # Right edge (x=+half): from 315°.right_pt up to 45°.right_pt
    # Top edge (y=+half): from 45°.top_pt left to 135°.top_pt
    # Left edge (x=-half): from 135°.left_pt down to 225°.left_pt
    # Bottom edge (y=-half): from 225°.bottom_pt right to 315°.bottom_pt

    def _get_edge_pt(angle, edge_key):
        """Get the intersection point for a specific corner and edge."""
        d = corner_data.get(angle)
        if not d:
            return None
        return d["edge_pts"].get(edge_key)

    # ── Fillet computation ──────────────────────────────────────────────
    # At each junction between a straight edge and a propeller arc, insert
    # a fillet arc of radius 6mm to round off the hard angle.
    #
    # Fillet center: offset `fr` inward from edge, and `prop_r + fr` from
    # the motor centre (external tangency).
    fr = 6.0  # aggressive fillet radius (6mm)

    def _fillet_at_vertical_edge(edge_x, y_int, mx, my, prop_r, inward_sign):
        """Compute fillet between vertical edge (x=edge_x) and propeller arc.

        inward_sign: -1 if edge is right (x=+half), +1 if left (x=-half).
        Returns (fillet_center, edge_tangent_pt, arc_tangent_pt, fillet_sa, fillet_ea).
        """
        x_fc = edge_x + inward_sign * fr
        disc = (prop_r + fr) ** 2 - (x_fc - mx) ** 2
        if disc < 0:
            return None
        y_fc_candidates = [my + math.sqrt(disc), my - math.sqrt(disc)]
        y_fc = min(y_fc_candidates, key=lambda y: abs(y - y_int))

        # Tangent point on edge: directly perpendicular from fillet centre
        edge_tp = (edge_x, y_fc)

        # Tangent point on propeller arc: on line from motor to fillet centre
        dx = x_fc - mx
        dy = y_fc - my
        dist = math.hypot(dx, dy)
        arc_tp = (mx + prop_r * dx / dist, my + prop_r * dy / dist)

        # Fillet arc angles from fillet centre
        sa_f = math.degrees(math.atan2(edge_tp[1] - y_fc, edge_tp[0] - x_fc))
        ea_f = math.degrees(math.atan2(arc_tp[1] - y_fc, arc_tp[0] - x_fc))

        return (x_fc, y_fc), edge_tp, arc_tp, sa_f, ea_f

    def _fillet_at_horizontal_edge(edge_y, x_int, mx, my, prop_r, inward_sign):
        """Compute fillet between horizontal edge (y=edge_y) and propeller arc.

        inward_sign: -1 if edge is top (y=+half), +1 if bottom (y=-half).
        """
        y_fc = edge_y + inward_sign * fr
        disc = (prop_r + fr) ** 2 - (y_fc - my) ** 2
        if disc < 0:
            return None
        x_fc_candidates = [mx + math.sqrt(disc), mx - math.sqrt(disc)]
        x_fc = min(x_fc_candidates, key=lambda x: abs(x - x_int))

        edge_tp = (x_fc, edge_y)

        dx = x_fc - mx
        dy = y_fc - my
        dist = math.hypot(dx, dy)
        arc_tp = (mx + prop_r * dx / dist, my + prop_r * dy / dist)

        sa_f = math.degrees(math.atan2(edge_tp[1] - y_fc, edge_tp[0] - x_fc))
        ea_f = math.degrees(math.atan2(arc_tp[1] - y_fc, arc_tp[0] - x_fc))

        return (x_fc, y_fc), edge_tp, arc_tp, sa_f, ea_f

    def _prop_angle(mx, my, pt):
        """Angle of point on propeller arc from motor centre."""
        return math.degrees(math.atan2(pt[1] - my, pt[0] - mx))

    # Precompute fillets for all 8 junction points
    fillets = {}
    # Format: fillets[(corner_angle, edge_key)] = fillet_data or None

    for angle_deg, d in corner_data.items():
        mx, my = d["mx"], d["my"]
        pr = d["r"]
        for edge_key, int_pt in d["edge_pts"].items():
            axis, val = edge_key
            if axis == "x":
                inward = -1 if val > 0 else 1
                f = _fillet_at_vertical_edge(val, int_pt[1], mx, my, pr, inward)
            else:
                inward = -1 if val > 0 else 1
                f = _fillet_at_horizontal_edge(val, int_pt[0], mx, my, pr, inward)
            if f:
                fillets[(angle_deg, edge_key)] = f

    # ── Build boundary segments ─────────────────────────────────────────
    def _emit_edge_and_fillets(edge_start, edge_end, corner_before, edge_key_before,
                                corner_after, edge_key_after, is_vertical):
        """Emit a trimmed edge with fillet arcs on each end."""
        out = []
        # Fillet at start of edge (coming from previous arc)
        f_start = fillets.get((corner_before, edge_key_before))
        # Fillet at end of edge (going into next arc)
        f_end = fillets.get((corner_after, edge_key_after))

        if is_vertical:
            y1 = f_start[1][1] if f_start else edge_start[1]
            y2 = f_end[1][1] if f_end else edge_end[1]
            out.append(("line", edge_start[0], y1, edge_end[0], y2))
        else:
            x1 = f_start[1][0] if f_start else edge_start[0]
            x2 = f_end[1][0] if f_end else edge_end[0]
            out.append(("line", x1, edge_start[1], x2, edge_end[1]))
        return out

    def _emit_prop_arc_with_fillets(angle_deg, d):
        """Emit a propeller arc trimmed by fillets, plus the fillet arcs."""
        out = []
        mx, my, pr = d["mx"], d["my"], d["r"]
        sa, ea = d["sa"], d["ea"]

        # Get the two edge keys for this corner
        edge_keys = list(d["edge_pts"].keys())

        # Determine which edge is "first" (start of prop arc) and "second" (end)
        # by checking which intersection is at angle sa vs ea
        pts = {}
        for ek in edge_keys:
            pt = d["edge_pts"][ek]
            a = _prop_angle(mx, my, pt)
            pts[ek] = (pt, a)

        # Sort by proximity to sa and ea
        ek_start = min(edge_keys, key=lambda ek: abs(((pts[ek][1] - sa + 180) % 360) - 180))
        ek_end = [ek for ek in edge_keys if ek != ek_start][0]

        f_start = fillets.get((angle_deg, ek_start))
        f_end = fillets.get((angle_deg, ek_end))

        # Emit fillet at arc start (junction with previous edge)
        if f_start:
            fc, edge_tp, arc_tp, sa_f, ea_f = f_start
            # Fillet arc: from edge tangent point to arc tangent point
            # Direction: the short arc that rounds the corner inward
            out.append(("arc", fc[0], fc[1], fr, sa_f, ea_f))
            # Trim propeller arc start
            sa = _prop_angle(mx, my, arc_tp)

        # Emit fillet at arc end
        if f_end:
            fc, edge_tp, arc_tp, sa_f, ea_f = f_end
            ea = _prop_angle(mx, my, arc_tp)

        # Emit the (trimmed) propeller arc
        out.append(("arc", mx, my, pr, sa, ea))

        # Emit fillet at arc end
        if f_end:
            fc, edge_tp, arc_tp, sa_f, ea_f = f_end
            out.append(("arc", fc[0], fc[1], fr, ea_f, sa_f))

        return out

    segs = []

    # Right edge (x = +half): trimmed
    r_bot_pt = _get_edge_pt(315, ("x", half)) or (half, -half + cr)
    r_top_pt = _get_edge_pt(45, ("x", half)) or (half, half - cr)
    f_bot = fillets.get((315, ("x", half)))
    f_top = fillets.get((45, ("x", half)))
    ry_bot = f_bot[1][1] if f_bot else r_bot_pt[1]
    ry_top = f_top[1][1] if f_top else r_top_pt[1]
    segs.append(("line", half, ry_bot, half, ry_top))

    # 45° propeller arc with fillets
    if 45 in corner_data:
        segs.extend(_emit_prop_arc_with_fillets(45, corner_data[45]))

    # Top edge (y = +half): trimmed
    t_right_pt = _get_edge_pt(45, ("y", half)) or (half - cr, half)
    t_left_pt = _get_edge_pt(135, ("y", half)) or (-half + cr, half)
    f_right = fillets.get((45, ("y", half)))
    f_left = fillets.get((135, ("y", half)))
    tx_right = f_right[1][0] if f_right else t_right_pt[0]
    tx_left = f_left[1][0] if f_left else t_left_pt[0]
    segs.append(("line", tx_right, half, tx_left, half))

    # 135° propeller arc with fillets
    if 135 in corner_data:
        segs.extend(_emit_prop_arc_with_fillets(135, corner_data[135]))

    # Left edge (x = -half): trimmed
    l_top_pt = _get_edge_pt(135, ("x", -half)) or (-half, half - cr)
    l_bot_pt = _get_edge_pt(225, ("x", -half)) or (-half, -half + cr)
    f_top_l = fillets.get((135, ("x", -half)))
    f_bot_l = fillets.get((225, ("x", -half)))
    ly_top = f_top_l[1][1] if f_top_l else l_top_pt[1]
    ly_bot = f_bot_l[1][1] if f_bot_l else l_bot_pt[1]
    segs.append(("line", -half, ly_top, -half, ly_bot))

    # 225° propeller arc with fillets
    if 225 in corner_data:
        segs.extend(_emit_prop_arc_with_fillets(225, corner_data[225]))

    # Bottom edge (y = -half): trimmed
    b_left_pt = _get_edge_pt(225, ("y", -half)) or (-half + cr, -half)
    b_right_pt = _get_edge_pt(315, ("y", -half)) or (half - cr, -half)
    f_left_b = fillets.get((225, ("y", -half)))
    f_right_b = fillets.get((315, ("y", -half)))
    bx_left = f_left_b[1][0] if f_left_b else b_left_pt[0]
    bx_right = f_right_b[1][0] if f_right_b else b_right_pt[0]
    segs.append(("line", bx_left, -half, bx_right, -half))

    # 315° propeller arc with fillets
    if 315 in corner_data:
        segs.extend(_emit_prop_arc_with_fillets(315, corner_data[315]))

    return segs


def generate_daughter_board_pcb():
    """Generate production-quality .kicad_pcb for the combined top plate + daughter board.

    The fabricated PCB is 110×110mm (PLATE_SIZE) — the full structural top frame
    plate with integrated electronics.  Features:
      - Outer frame with Kagome lattice lightening cutouts
      - Central heatsink/fan pass-through cutout
      - Connector relief cutouts (Ethernet, barrel jack)
      - All electronic component footprints (from daughter_board_netlist)
      - 4-layer stackup, copper zone pours, GND via stitching

    Content:
      Edge.Cuts      — 110×110 outline + Kagome hex cutouts + heatsink + connector reliefs
      F.Cu / B.Cu    — all real SMD + TH pads with net assignments
      In1.Cu         — GND copper zone pour (continuous plane)
      In2.Cu         — +3V3 copper zone pour
      F.Courtyard    — courtyard outlines for every component
      F.SilkS        — ref designators, pin-1 markers, board title
      F.Fab          — component values
      GND vias       — perimeter via stitching (2mm spacing)
    """
    if not _KI_AVAIL:
        raise RuntimeError("cadquery_framework.kicad.primitives not available")

    from cadquery_framework.kicad.primitives import rounded_hexagon_outline
    from drone_design.drone_model.components.frame.skeleton_plate import (
        _kagome_cutout_centers_pcb, KAGOME_HOLE_R, ARM_ANGLES, PLATE_CORNER_R,
    )
    from drone_design.drone_model.components.assembly_constants import PLATE_SIZE
    import math

    # Import netlist and build board definition
    from drone_design.drone_model.components.electronics.daughter_board_netlist import build_board
    board = build_board()

    # Auto-reposition silk labels to avoid collisions
    from cadquery_framework.kicad.validation.silk_repositioner import reposition_silk_labels
    silk_offsets = reposition_silk_labels(board)

    # Validate silkscreen DRC with repositioned labels
    from cadquery_framework.kicad.validation.silkscreen_checker import validate_silkscreen
    result = validate_silkscreen(board, silk_offsets=silk_offsets)
    if result.errors:
        print(f"[silkscreen] {len(result.errors)} label issues remain after auto-reposition")
        print(result.report())
    else:
        print(f"[silkscreen] All labels repositioned — 0 errors")

    bw = board.width      # 110.0 mm (PLATE_SIZE)
    bh = board.height     # 110.0 mm
    bt = board.thickness  # 1.6 mm
    cr = board.corner_radius  # PLATE_CORNER_R = 2.0

    # ── Build global net table ───────────────────────────────────────────────
    net_ids: dict[str, int] = {"": 0}
    for net_name in sorted(board.nets.keys()):
        if net_name and net_name not in net_ids:
            net_ids[net_name] = len(net_ids)

    # ── Build per-placement pin→net maps ─────────────────────────────────────
    ref_pin_nets: dict[str, dict[str, str]] = defaultdict(dict)
    for net_name, connections in board.nets.items():
        for conn in connections:
            ref_pin_nets[conn.ref][conn.pin_number] = net_name

    # ── Board outline (Edge.Cuts) — centre-origin ─────────────────────────
    ox = bw / 2   # offset: top-left (0,0) → centre
    oy = bh / 2

    segs = _outer_boundary_with_prop_arcs(bw, bh, cr, _D, ARM_ANGLES, PLATE_SIZE)

    # ── Heatsink/fan pass-through cutout (centre of board) ─────────────────
    _hs_w = _D["de10_nano"]["heatsink_width"]
    _hs_l = _D["de10_nano"]["heatsink_length"]
    _hs_clear = 4.0
    _hs_cw = _hs_w + _hs_clear
    _hs_cl = _hs_l + _hs_clear
    _hs_r = min(cr, 3.0)
    segs.extend(rounded_rect_outline(_hs_cw, _hs_cl, _hs_r))

    # ── Connector relief cutouts (Ethernet, barrel jack from DE10-Nano) ────
    _de10_conn = _D["de10_nano"]["connectors"]
    for key, margin in [("ethernet", 6.0), ("barrel_jack", 4.0)]:
        if key not in _de10_conn:
            continue
        c = _de10_conn[key]
        cx = DE10_W / 2 - c["intel_y"]
        cy = c["intel_x"] - DE10_L / 2
        w, h = c["width"] + margin * 2, c["length"] + margin * 2
        r = min(2.0, (min(w, h) / 2) - 0.5)
        segs.extend(rounded_rect_outline(w, h, r, cx, cy))

    # ── Kagome lattice lightening cutouts (frame area only) ────────────────
    # Keepouts: arm rail paths + central daughter board area (solid PCB)
    keepouts = []
    half = PLATE_SIZE / 2
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        abs_cos = abs(cos_a) if abs(cos_a) > 1e-9 else 1e-9
        abs_sin = abs(sin_a) if abs(sin_a) > 1e-9 else 1e-9
        max_r = min(half / abs_cos, half / abs_sin) - 5.0
        dist = 15.0
        while dist <= max_r:
            keepouts.append((dist * cos_a, dist * sin_a, 9.0))
            dist += 10.0
    keepouts.append((0, 0, 58.0))  # central electronics area keepout

    _hex_r = min(cr, KAGOME_HOLE_R * 0.35)
    hex_centers = _kagome_cutout_centers_pcb(PLATE_SIZE, keepouts)
    for hcx, hcy in hex_centers:
        segs.extend(rounded_hexagon_outline(hcx, hcy, KAGOME_HOLE_R, _hex_r))

    content = outline_to_sexpr(segs)

    # ── Mounting holes (NPTH) ────────────────────────────────────────────────
    gnd_net_id = net_ids.get("GND", 0)
    for mx, my, drill_d in board.mounting_holes:
        hx = mx - ox
        hy = my - oy
        pad_d = drill_d + 0.6
        content += f"""
  (footprint "MountingHole:MountingHole_{drill_d:.1f}mm" (layer "F.Cu") (uuid "{_uid()}")
  (at {hx:.4f} {hy:.4f})
  (descr "M2.5 mounting hole, GND-tied")
    (fp_text reference "MH" (at 0 -2.5) (layer "F.SilkS") (uuid "{_uid()}")
      (effects (font (size {SILK_MICRO_SIZE_MM} {SILK_MICRO_SIZE_MM}) (thickness {SILK_MICRO_THICK_MM})))
    )
    (fp_text value "M2.5" (at 0 2.5) (layer "F.Fab") (uuid "{_uid()}")
      (effects (font (size {SILK_FAB_SIZE_MM} {SILK_FAB_SIZE_MM}) (thickness {SILK_FAB_THICK_MM})))
    )
    (fp_circle (center 0 0) (end {pad_d / 2 + 0.5:.3f} 0) (layer "F.CrtYd") (width {COURTYARD_WIDTH_MM}) (uuid "{_uid()}"))
    (pad "" thru_hole circle (at 0 0) (size {pad_d:.2f} {pad_d:.2f}) (drill {drill_d:.2f})
      (layers "*.Cu" "*.Mask")
      (net {gnd_net_id} "GND")
      (uuid "{_uid()}")
    )
  )"""

    # ── All component footprints with real pads and net assignments ──────────
    for placement in board.placements:
        pin_nets = ref_pin_nets.get(placement.ref, {})
        shifted = CompPlacement(
            component=placement.component,
            ref=placement.ref,
            x=placement.x - ox,
            y=placement.y - oy,
            rotation=placement.rotation,
            side=placement.side,
        )
        content += "\n" + _footprint_sexpr(shifted, pin_nets, net_ids,
                                          silk_offsets=silk_offsets)

    # ── Copper zone pours on inner layers ────────────────────────────────────
    margin = 0.5
    zone_pts = [
        (-bw / 2 + margin, -bh / 2 + margin),
        ( bw / 2 - margin, -bh / 2 + margin),
        ( bw / 2 - margin,  bh / 2 - margin),
        (-bw / 2 + margin,  bh / 2 - margin),
    ]

    content += "\n" + _zone_pour(gnd_net_id, "GND", "In1.Cu", zone_pts, priority=0)
    v33_net_id = net_ids.get("+3V3", 0)
    if v33_net_id:
        content += "\n" + _zone_pour(v33_net_id, "+3V3", "In2.Cu", zone_pts, priority=0)
    content += "\n" + _zone_pour(gnd_net_id, "GND", "F.Cu", zone_pts, priority=0)
    content += "\n" + _zone_pour(gnd_net_id, "GND", "B.Cu", zone_pts, priority=0)

    # ── GND via stitching around perimeter ──────────────────────────────────
    via_spacing = 2.0
    via_inset = 1.5

    x = -bw / 2 + via_inset
    while x <= bw / 2 - via_inset:
        content += "\n" + _via_sexpr(x, -bh / 2 + via_inset, gnd_net_id, "GND")
        content += "\n" + _via_sexpr(x,  bh / 2 - via_inset, gnd_net_id, "GND")
        x += via_spacing

    y = -bh / 2 + via_inset + via_spacing
    while y <= bh / 2 - via_inset - via_spacing:
        content += "\n" + _via_sexpr(-bw / 2 + via_inset, y, gnd_net_id, "GND")
        content += "\n" + _via_sexpr( bw / 2 - via_inset, y, gnd_net_id, "GND")
        y += via_spacing

    # ── Board identification silkscreen ───────────────────────────────────────
    content += "\n" + text_sexpr(
        "DE10-NANO COMBINED TOP PLATE + DAUGHTER BOARD",
        0, bh / 2 - 4.5,
        "F.SilkS", SILK_REF_SIZE_MM, SILK_REF_THICK_MM,
    )
    content += "\n" + text_sexpr(
        f"{bw:.0f}x{bh:.0f}mm  FR4  1.6mm  4L  ENIG  Kagome frame",
        0, bh / 2 - 8.5,
        "F.SilkS", SILK_SMALL_SIZE_MM, SILK_SMALL_THICK_MM,
    )
    content += "\n" + text_sexpr(
        "Stackup: F.Cu(sig) / In1(GND) / In2(PWR) / B.Cu(sig)",
        0, bh / 2 - 12.0,
        "Cmts.User", SILK_MICRO_SIZE_MM, SILK_MICRO_THICK_MM,
    )

    # ── Build net table ──────────────────────────────────────────────────────
    nets_block = "\n".join(
        _net_sexpr(nid, nname)
        for nname, nid in sorted(net_ids.items(), key=lambda x: x[1])
    )

    return _kicad_pcb_4layer(
        f"DE10-Nano Daughter Board v2.0 ({len(board.placements)} components, "
        f"{board.net_count()} nets)",
        bt, nets_block, content,
    )
