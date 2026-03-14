#!/usr/bin/env python3
"""
KiCad PCB & Gerber Exporter for Drone FR4 Frame Parts

Generates .kicad_pcb files from the CadQuery 3D model geometry.
Each FR4 part (plates, arms, legs, boom, brackets) gets its own PCB file
with board outline, mounting holes, cutouts, and silkscreen labels.

The .kicad_pcb files can be:
  1. Opened in KiCad for review and modification
  2. Used directly to generate Gerber files via KiCad CLI or GUI
  3. Sent to JLCPCB/PCBWay as-is for mechanical PCB fabrication

Usage:
    source .venv/bin/activate
    python drone_design/modeling/export_gerber.py

Output:
    drone_design/cad/exports/gerber/*.kicad_pcb   (one per FR4 part)
    drone_design/cad/exports/gerber/README.txt     (fabrication notes)

Gerber generation (requires KiCad 7+ CLI):
    kicad-cli pcb export gerbers -o gerber_out/ bottom_plate.kicad_pcb
    kicad-cli pcb export drill -o gerber_out/ bottom_plate.kicad_pcb
"""

import sys
import json
import math
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Load connection dimensions from dimensions.json
_DIMS_PATH = Path(__file__).parent.parent / "cad" / "dimensions.json"
_D = json.loads(_DIMS_PATH.read_text())
_CONN = _D["connections"]
HEADER_PITCH = _CONN["header_pitch"]
HEADER_HOLE_D = _CONN["header_hole_diameter"]
HEADER_PAD_D = _CONN["header_pad_diameter"]
ARM_PINS_PER_SIDE = _CONN["arm_header_pins_per_side"]
ARM_HEADER_OFFSET = _CONN["arm_header_offset_from_slot"]
LEG_HEADER_PINS = _CONN["leg_header_pins"]
BOOM_HEADER_PINS = _CONN["boom_header_pins"]
BOOM_HEADER_INSET = _CONN["boom_header_inset"]

from components.assembly_constants import (
    PLATE_SIZE, PLATE_CORNER_R, BOTTOM_THICK, TOP_THICK,
    SLOT_W, SLOT_L, ARM_ANGLES,
    DE10_W, DE10_L, DE10_STANDOFF,
    ARM_LENGTH, ARM_WIDTH, ARM_THICK, ARM_TAB, ARM_WEB, ARM_FLANGE,
    MOTOR_SECTION, MOTOR_MOUNT_RECT,
    LEG_WIDTH, LEG_HEIGHT, LEG_THICK, FOOT_LENGTH, FOOT_THICK,
    LEG_HOLE_W, LEG_HOLE_H, LEG_HOLE_R, LEG_HOLE_N,
    BOOM_LENGTH, BOOM_WIDTH, BOOM_THICK, BOOM_FLANGE, BOOM_WEB,
    PUMP_BRACKET_W, PUMP_BRACKET_H, PUMP_BRACKET_T,
    KAGOME_CELL, KAGOME_HOLE_R, KAGOME_WEB_MIN,
)


def _uid():
    """Generate a KiCad-style UUID."""
    return str(uuid.uuid4())


def _arc_points(cx, cy, r, start_deg, end_deg, n=16):
    """Generate arc points for rounded corners."""
    pts = []
    for i in range(n + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * i / n)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def _rounded_rect_outline(w, h, r, cx=0, cy=0):
    """Generate Edge.Cuts line segments for a rounded rectangle."""
    r = min(r, w / 2, h / 2)
    hw, hh = w / 2, h / 2
    lines = []

    corners = [
        (cx + hw - r, cy + hh - r, 0, 90),     # top-right
        (cx - hw + r, cy + hh - r, 90, 180),    # top-left
        (cx - hw + r, cy - hh + r, 180, 270),   # bottom-left
        (cx + hw - r, cy - hh + r, 270, 360),   # bottom-right
    ]

    # Straight edges between corners
    edges = [
        ((cx + hw - r, cy + hh), (cx - hw + r, cy + hh)),   # top
        ((cx - hw, cy + hh - r), (cx - hw, cy - hh + r)),   # left
        ((cx - hw + r, cy - hh), (cx + hw - r, cy - hh)),   # bottom
        ((cx + hw, cy - hh + r), (cx + hw, cy + hh - r)),   # right
    ]

    if r > 0.01:
        for acx, acy, sa, ea in corners:
            lines.append(("arc", acx, acy, r, sa, ea))
        for (x1, y1), (x2, y2) in edges:
            lines.append(("line", x1, y1, x2, y2))
    else:
        lines.append(("line", cx - hw, cy - hh, cx + hw, cy - hh))
        lines.append(("line", cx + hw, cy - hh, cx + hw, cy + hh))
        lines.append(("line", cx + hw, cy + hh, cx - hw, cy + hh))
        lines.append(("line", cx - hw, cy + hh, cx - hw, cy - hh))

    return lines


def _rect_outline(w, h, cx=0, cy=0):
    """Generate Edge.Cuts lines for a plain rectangle."""
    return _rounded_rect_outline(w, h, 0, cx, cy)


def _hexagon_outline(cx, cy, r):
    """Generate Edge.Cuts lines for a regular hexagon (flat-top)."""
    pts = []
    for i in range(6):
        angle = math.radians(60 * i + 30)  # flat-top orientation
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    lines = []
    for i in range(6):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 6]
        lines.append(("line", x1, y1, x2, y2))
    return lines


def _rotated_rect_outline(w, h, cx, cy, angle_deg):
    """Generate Edge.Cuts lines for a rotated rectangle."""
    hw, hh = w / 2, h / 2
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    rotated = [(cx + x * cos_a - y * sin_a, cy + x * sin_a + y * cos_a)
               for x, y in corners]
    lines = []
    for i in range(4):
        x1, y1 = rotated[i]
        x2, y2 = rotated[(i + 1) % 4]
        lines.append(("line", x1, y1, x2, y2))
    return lines


def _outline_to_sexpr(outline_segments, layer="Edge.Cuts", width=0.05):
    """Convert outline segments to KiCad S-expression strings."""
    lines = []
    for seg in outline_segments:
        if seg[0] == "line":
            _, x1, y1, x2, y2 = seg
            lines.append(
                f'  (gr_line (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) '
                f'(layer "{layer}") (width {width}) (uuid "{_uid()}"))'
            )
        elif seg[0] == "arc":
            _, acx, acy, r, sa, ea = seg
            # KiCad arcs: (gr_arc (start x y) (mid x y) (end x y) ...)
            sa_r, ea_r = math.radians(sa), math.radians(ea)
            ma_r = (sa_r + ea_r) / 2
            sx = acx + r * math.cos(sa_r)
            sy = acy + r * math.sin(sa_r)
            mx = acx + r * math.cos(ma_r)
            my = acy + r * math.sin(ma_r)
            ex = acx + r * math.cos(ea_r)
            ey = acy + r * math.sin(ea_r)
            lines.append(
                f'  (gr_arc (start {sx:.4f} {sy:.4f}) (mid {mx:.4f} {my:.4f}) '
                f'(end {ex:.4f} {ey:.4f}) '
                f'(layer "{layer}") (width {width}) (uuid "{_uid()}"))'
            )
    return "\n".join(lines)


def _circle_sexpr(cx, cy, r, layer="Edge.Cuts", width=0.05):
    """Generate a KiCad circle S-expression."""
    return (
        f'  (gr_circle (center {cx:.4f} {cy:.4f}) (end {cx + r:.4f} {cy:.4f}) '
        f'(layer "{layer}") (width {width}) (uuid "{_uid()}"))'
    )


def _through_hole_pad(cx, cy, drill_d, pad_d=None):
    """Generate a mounting hole footprint at (cx, cy)."""
    if pad_d is None:
        pad_d = drill_d + 0.5
    uid = _uid()
    return f"""  (footprint "MountingHole:MountingHole_{drill_d:.1f}mm" (layer "F.Cu")
    (uuid "{uid}")
    (at {cx:.4f} {cy:.4f})
    (pad "" thru_hole circle (at 0 0) (size {pad_d:.2f} {pad_d:.2f}) (drill {drill_d:.2f})
      (layers "*.Cu" "*.Mask")
      (uuid "{_uid()}")
    )
  )"""


def _header_pad_row(cx, cy, count, pitch, angle_deg=0, drill_d=None, pad_d=None):
    """Generate through-hole pads for a row of pin header holes."""
    if drill_d is None:
        drill_d = HEADER_HOLE_D
    if pad_d is None:
        pad_d = HEADER_PAD_D
    pads = []
    span = (count - 1) * pitch
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    for i in range(count):
        offset = -span / 2 + i * pitch
        px = cx + offset * cos_a
        py = cy + offset * sin_a
        pads.append(_through_hole_pad(px, py, drill_d, pad_d))
    return "\n".join(pads)


def _text_sexpr(text, cx, cy, layer="F.SilkS", size=1.5, thickness=0.15):
    """Generate a text label."""
    return (
        f'  (gr_text "{text}" (at {cx:.4f} {cy:.4f}) (layer "{layer}") '
        f'(uuid "{_uid()}")\n'
        f'    (effects (font (size {size} {size}) (thickness {thickness})))\n'
        f'  )'
    )


def _kicad_pcb_wrapper(title, thickness, inner_content):
    """Wrap content in a complete .kicad_pcb file."""
    return f"""(kicad_pcb (version 20221018) (generator "drone_gerber_export")
  (general
    (thickness {thickness:.2f})
    (legacy_teardrops no)
  )
  (paper "A4")
  (title_block
    (title "{title}")
    (date "{datetime.now().strftime('%Y-%m-%d')}")
    (comment 1 "Material: FR4")
    (comment 2 "Thickness: {thickness:.1f}mm")
    (comment 3 "Generated from drone_design/cad/dimensions.json")
  )
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user "B.Mask")
    (39 "F.Mask" user "F.Mask")
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (44 "Edge.Cuts" user)
  )
  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "core") (thickness {thickness - 0.07:.3f}) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
    )
    (pad_to_mask_clearance 0.05)
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
  (net 0 "")

{inner_content}
)
"""


# =============================================================================
# PCB Part Generators
# =============================================================================

def _kagome_cutout_centers(plate_size, keepout_circles):
    """Compute Kagome hexagonal cutout centers (mirrors drone_3d_model.py logic)."""
    half = plate_size / 2 - 5
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
    return centers


def generate_bottom_plate():
    """Generate .kicad_pcb for bottom frame plate."""
    segs = []

    # Board outline: rounded rectangle
    segs.extend(_rounded_rect_outline(PLATE_SIZE, PLATE_SIZE, PLATE_CORNER_R))

    # Arm slots (4x, rotated rectangles)
    for angle in ARM_ANGLES:
        segs.extend(_rotated_rect_outline(SLOT_W, SLOT_L, 0, 0, angle))

    # Battery strap slots (2x)
    for dy in [-20, 20]:
        segs.extend(_rect_outline(25, 3, 0, dy))

    # Keepout zones for Kagome computation
    keepouts = []
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        for dist in range(0, int(SLOT_L / 2) + 5, 8):
            keepouts.append((dist * math.cos(rad), dist * math.sin(rad), 8.0))
    for dy in [-20, 20]:
        keepouts.append((0, dy, 15.0))

    # DE10-Nano standoff holes (4x M2.5)
    holes = []
    for dx in [-DE10_W / 2 + 4, DE10_W / 2 - 4]:
        for dy in [-DE10_L / 2 + 4, DE10_L / 2 - 4]:
            holes.append((dx, dy))
            keepouts.append((dx, dy, 5.0))

    # Kagome hexagonal cutouts
    hex_centers = _kagome_cutout_centers(PLATE_SIZE, keepouts)
    for cx, cy in hex_centers:
        segs.extend(_hexagon_outline(cx, cy, KAGOME_HOLE_R))

    # Build content
    content = _outline_to_sexpr(segs)
    for hx, hy in holes:
        content += "\n" + _through_hole_pad(hx, hy, 2.7, 4.5)  # M2.5 hole

    # Arm header holes (matching arm tab pin rows at each slot angle)
    slot_half = SLOT_L / 2
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        for side in [-1, 1]:
            # Offset perpendicular to slot axis
            perp_x = -sin_a * side * ARM_HEADER_OFFSET
            perp_y = cos_a * side * ARM_HEADER_OFFSET
            content += "\n" + _header_pad_row(
                perp_x, perp_y, ARM_PINS_PER_SIDE, HEADER_PITCH, angle_deg=angle)

    # Leg header holes (matching mounting tab overlap area)
    _LEG_ANGLES = [0, 90, 180, 270]
    _LEG_THICK = _D["landing_gear"]["leg_thickness"]
    _TAB_DEPTH = _D["landing_gear"]["mounting_tab_depth"]
    tab_center_dist = PLATE_SIZE / 2 - _LEG_THICK / 2 - _TAB_DEPTH / 2
    for angle in _LEG_ANGLES:
        rad = math.radians(angle)
        lx = tab_center_dist * math.cos(rad)
        ly = tab_center_dist * math.sin(rad)
        content += "\n" + _header_pad_row(lx, ly, LEG_HEADER_PINS, HEADER_PITCH, angle_deg=angle + 90)

    content += "\n" + _text_sexpr("BOTTOM PLATE", 0, 0, "F.SilkS", 3, 0.3)
    content += "\n" + _text_sexpr(f"{PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm  FR4 {BOTTOM_THICK:.1f}mm", 0, 5, "F.SilkS", 1.2, 0.15)

    return _kicad_pcb_wrapper("Drone Bottom Frame Plate", BOTTOM_THICK, content)


def generate_top_plate():
    """Generate .kicad_pcb for top frame plate."""
    segs = []

    # Board outline
    segs.extend(_rounded_rect_outline(PLATE_SIZE, PLATE_SIZE, PLATE_CORNER_R))

    # Arm slots
    for angle in ARM_ANGLES:
        segs.extend(_rotated_rect_outline(SLOT_W, SLOT_L, 0, 0, angle))

    # Central rectangular opening for DE10-Nano access
    segs.extend(_rounded_rect_outline(72, 110, PLATE_CORNER_R))

    # Keepouts
    keepouts = []
    for angle in ARM_ANGLES:
        rad = math.radians(angle)
        for dist in range(0, int(SLOT_L / 2) + 5, 8):
            keepouts.append((dist * math.cos(rad), dist * math.sin(rad), 8.0))
    keepouts.append((0, 0, 58.0))  # central opening keepout

    # Kagome cutouts
    hex_centers = _kagome_cutout_centers(PLATE_SIZE, keepouts)
    for cx, cy in hex_centers:
        segs.extend(_hexagon_outline(cx, cy, KAGOME_HOLE_R))

    content = _outline_to_sexpr(segs)
    content += "\n" + _text_sexpr("TOP PLATE", 0, -PLATE_SIZE / 2 + 8, "F.SilkS", 2.5, 0.25)
    content += "\n" + _text_sexpr(f"{PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm  FR4 {TOP_THICK:.1f}mm", 0, -PLATE_SIZE / 2 + 13, "F.SilkS", 1.0, 0.12)

    return _kicad_pcb_wrapper("Drone Top Frame Plate", TOP_THICK, content)


def generate_arm():
    """Generate .kicad_pcb for one motor arm (I-beam profile)."""
    segs = []

    # Outer rectangle
    segs.extend(_rect_outline(ARM_LENGTH, ARM_WIDTH))

    # I-beam cutouts (two side channels)
    body_inner = -ARM_LENGTH / 2 + ARM_TAB
    body_outer = ARM_LENGTH / 2 - MOTOR_SECTION
    cutout_length = (body_outer - body_inner) - 10
    cutout_cx = (body_inner + body_outer) / 2
    cutout_width = (ARM_WIDTH - ARM_WEB) / 2 - ARM_FLANGE
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (ARM_WEB / 2 + ARM_FLANGE + cutout_width / 2)
            segs.extend(_rect_outline(cutout_length, cutout_width, cutout_cx, cy))

    # Motor mount holes (4x M3)
    holes = []
    mx_center = ARM_LENGTH / 2 - MOTOR_SECTION / 2
    for dx in [-MOTOR_MOUNT_RECT[0] / 2, MOTOR_MOUNT_RECT[0] / 2]:
        for dy in [-MOTOR_MOUNT_RECT[1] / 2, MOTOR_MOUNT_RECT[1] / 2]:
            holes.append((mx_center + dx, dy))

    content = _outline_to_sexpr(segs)
    for hx, hy in holes:
        content += "\n" + _through_hole_pad(hx, hy, 3.2, 5.0)  # M3 clearance

    # Pin header holes along tab (two rows for plate connection)
    tab_cx = -ARM_LENGTH / 2 + ARM_TAB / 2
    for side in [-1, 1]:
        hy = side * ARM_HEADER_OFFSET
        content += "\n" + _header_pad_row(tab_cx, hy, ARM_PINS_PER_SIDE, HEADER_PITCH)

    content += "\n" + _text_sexpr("ARM", 0, 0, "F.SilkS", 2, 0.2)
    content += "\n" + _text_sexpr(f"{ARM_LENGTH:.0f}x{ARM_WIDTH:.0f}mm  FR4 {ARM_THICK:.1f}mm", 0, 4, "F.SilkS", 1.0, 0.12)

    return _kicad_pcb_wrapper("Drone Motor Arm (I-Beam)", ARM_THICK, content)


def generate_landing_leg():
    """Generate .kicad_pcb for one L-shaped landing leg with mounting tab.

    PCB layout (unfolded flat, as manufactured):
      - Vertical section: LEG_WIDTH x LEG_HEIGHT, centered at (0, LEG_HEIGHT/2)
      - Foot: FOOT_LENGTH x FOOT_THICK, extending to +X at bottom
      - Mounting tab: LEG_WIDTH x TAB_DEPTH, extending to -X at top (fold line at top edge)
      - Lightening holes in vertical section
      - Pin header holes in the mounting tab (for plate connection)

    When assembled, the tab folds 90 degrees to sit flat under the bottom plate.
    """
    _LG = _D["landing_gear"]
    tab_depth = _LG["mounting_tab_depth"]

    segs = []

    # Vertical section
    segs.extend(_rect_outline(LEG_WIDTH, LEG_HEIGHT, 0, LEG_HEIGHT / 2))

    # Foot (horizontal extension at bottom, extends to +X)
    foot_cx = FOOT_LENGTH / 2 - LEG_WIDTH / 2
    segs.extend(_rect_outline(FOOT_LENGTH, FOOT_THICK, foot_cx, 0))

    # Mounting tab at top (extends to -X, representing inward fold under plate)
    tab_cx = -(LEG_WIDTH / 2 + tab_depth / 2)
    tab_cy = LEG_HEIGHT - LEG_THICK / 2  # at top edge
    segs.extend(_rect_outline(tab_depth, LEG_WIDTH, tab_cx, tab_cy))

    # Lightening holes in vertical section (capsule-shaped, simplified as ovals)
    hole_spacing = (LEG_HEIGHT - 20) / LEG_HOLE_N
    for i in range(LEG_HOLE_N):
        hy = 15 + hole_spacing * (i + 0.5)
        segs.extend(_rounded_rect_outline(LEG_HOLE_W, LEG_HOLE_H, LEG_HOLE_R, 0, hy))

    content = _outline_to_sexpr(segs)

    # Pin header holes in mounting tab (vertical through-holes when assembled)
    tab_hole_cx = tab_cx  # center of tab
    span = (LEG_HEADER_PINS - 1) * HEADER_PITCH
    for i in range(LEG_HEADER_PINS):
        hx = -span / 2 + i * HEADER_PITCH
        content += "\n" + _through_hole_pad(hx, tab_cy, HEADER_HOLE_D, HEADER_PAD_D)

    # Fold line indicator on silkscreen
    fold_y = LEG_HEIGHT
    content += "\n" + _text_sexpr("FOLD", -(LEG_WIDTH / 2 + tab_depth / 2), fold_y + 3, "F.SilkS", 1.0, 0.12)
    content += "\n" + _text_sexpr("LEG", 0, LEG_HEIGHT / 2, "F.SilkS", 2, 0.2)

    return _kicad_pcb_wrapper("Drone Landing Leg (L-shape + Tab)", LEG_THICK, content)


def generate_nose_boom():
    """Generate .kicad_pcb for the nose boom (I-beam profile)."""
    segs = []

    # Outer rectangle
    segs.extend(_rect_outline(BOOM_LENGTH, BOOM_WIDTH))

    # I-beam side cutouts
    cutout_length = BOOM_LENGTH - 40  # leave 20mm solid at each end
    cutout_width = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_width / 2)
            segs.extend(_rect_outline(cutout_length, cutout_width, 0, cy))

    content = _outline_to_sexpr(segs)

    # Root end header holes (two rows for plate connection)
    root_x = -BOOM_LENGTH / 2 + BOOM_HEADER_INSET + 10
    for row_offset in [-4.0, 4.0]:
        content += "\n" + _header_pad_row(root_x + row_offset, 0, BOOM_HEADER_PINS, HEADER_PITCH, angle_deg=90)

    content += "\n" + _text_sexpr("BOOM", 0, 0, "F.SilkS", 2, 0.2)
    content += "\n" + _text_sexpr(f"{BOOM_LENGTH:.0f}x{BOOM_WIDTH:.0f}mm  FR4 {BOOM_THICK:.1f}mm", 0, 4, "F.SilkS", 1.0, 0.12)

    return _kicad_pcb_wrapper("Drone Nose Boom (I-Beam)", BOOM_THICK, content)


def generate_pump_bracket():
    """Generate .kicad_pcb for the pump mounting bracket."""
    _PB = _D["pump_bracket"]
    pb_w = _PB["base_width"]
    pb_d = _PB["base_depth"]
    pb_t = _PB["thickness"]
    frame_hole_d = _PB["frame_hole_diameter"]
    frame_inset = _PB["frame_hole_inset"]
    pump_hole_d = _PB["pump_hole_diameter"]
    pump_hole_sx = _PB["pump_hole_spacing_x"]

    segs = []
    segs.extend(_rect_outline(pb_w, pb_d))

    content = _outline_to_sexpr(segs)

    # Frame mounting holes (4 corners)
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (pb_w / 2 - frame_inset)
            hy = sy * (pb_d / 2 - frame_inset)
            content += "\n" + _through_hole_pad(hx, hy, frame_hole_d, frame_hole_d + 1.0)

    # Pump mounting holes (2x, centered vertically)
    for sx in [-1, 1]:
        hx = sx * (pump_hole_sx / 2)
        content += "\n" + _through_hole_pad(hx, 0, pump_hole_d, pump_hole_d + 1.0)

    content += "\n" + _text_sexpr("PUMP BRACKET", 0, 0, "F.SilkS", 1.5, 0.15)
    content += "\n" + _text_sexpr(f"{pb_w:.0f}x{pb_d:.0f}mm  FR4 {pb_t:.1f}mm", 0, 4, "F.SilkS", 1.0, 0.12)

    return _kicad_pcb_wrapper("Drone Pump Bracket", pb_t, content)


# =============================================================================
# Main
# =============================================================================

def main():
    out_dir = Path(__file__).resolve().parent.parent / "cad" / "exports" / "gerber"
    out_dir.mkdir(parents=True, exist_ok=True)

    parts = [
        ("bottom_plate", generate_bottom_plate),
        ("top_plate", generate_top_plate),
        ("arm", generate_arm),
        ("landing_leg", generate_landing_leg),
        ("nose_boom", generate_nose_boom),
        ("pump_bracket", generate_pump_bracket),
    ]

    print("Generating KiCad PCB files for FR4 frame parts...")
    for name, generator in parts:
        path = out_dir / f"{name}.kicad_pcb"
        content = generator()
        path.write_text(content, encoding="utf-8")
        size_kb = path.stat().st_size / 1024
        print(f"  {name}.kicad_pcb ({size_kb:.1f} KB)")

    # Write fabrication notes
    readme = out_dir / "README.txt"
    readme.write_text(f"""Drone FR4 Frame Parts — KiCad PCB Files
========================================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

These are MECHANICAL PCBs — no copper traces, no electrical components.
Order as standard FR4 PCB from any fabricator (JLCPCB, PCBWay, OSH Park).

Files:
  bottom_plate.kicad_pcb  — {PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm, {BOTTOM_THICK:.1f}mm FR4, Kagome cutouts + arm/leg header holes
  top_plate.kicad_pcb     — {PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm, {TOP_THICK:.1f}mm FR4, central opening + cutouts
  arm.kicad_pcb           — {ARM_LENGTH:.0f}x{ARM_WIDTH:.0f}mm, {ARM_THICK:.1f}mm FR4, I-beam, M3 motor holes + 2x{ARM_PINS_PER_SIDE} header pads
  landing_leg.kicad_pcb   — L-shape, {LEG_THICK:.1f}mm FR4, lightening holes + {LEG_HEADER_PINS} header pads
  nose_boom.kicad_pcb     — {BOOM_LENGTH:.0f}x{BOOM_WIDTH:.0f}mm, {BOOM_THICK:.1f}mm FR4, I-beam + 2x{BOOM_HEADER_PINS} root header pads
  pump_bracket.kicad_pcb  — {_D['pump_bracket']['base_width']:.0f}x{_D['pump_bracket']['base_depth']:.0f}mm, {_D['pump_bracket']['thickness']:.1f}mm FR4, frame + pump mounting holes

Fabrication specs:
  Material:     FR4 (standard glass-epoxy)
  Finish:       HASL or bare copper (cosmetic only)
  Solder mask:  Optional (green default)
  Silkscreen:   White (part labels)
  Min hole:     {HEADER_HOLE_D}mm (pin header) / 2.5mm (M2.5 standoff) / 3.2mm (M3 motor mount)
  Copper:       Not required — these are structural, not electrical

To generate Gerber files (requires KiCad 7+):
  kicad-cli pcb export gerbers -o gerber_out/ bottom_plate.kicad_pcb
  kicad-cli pcb export drill -o gerber_out/ bottom_plate.kicad_pcb

Or open in KiCad GUI: File → Fabrication Outputs → Gerbers

Quantities per drone:
  bottom_plate × 1
  top_plate    × 1
  arm          × 4
  landing_leg  × 4
  nose_boom    × 1
  pump_bracket × 1
  Total: 12 PCBs per drone
""", encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"Generated {len(parts)} KiCad PCB files in: {out_dir}/")
    print(f"See {readme.name} for fabrication instructions.")
    print(f"{'=' * 60}")
    print("\nTo generate Gerbers:")
    print("  kicad-cli pcb export gerbers -o gerber_out/ <file>.kicad_pcb")
    print("  kicad-cli pcb export drill -o gerber_out/ <file>.kicad_pcb")
    print("\nOr open in KiCad GUI for review + manual Gerber export.")


if __name__ == "__main__":
    main()
