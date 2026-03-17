"""KiCad S-expression primitives for generating .kicad_pcb files.

These functions generate the building blocks for mechanical PCB files:
board outlines, mounting holes, cutouts, silkscreen labels, etc.

Manufacturing tolerances are centralised in:
  cadquery_framework/kicad/jlcpcb_constraints.py
"""

import math
import uuid
from datetime import datetime

from cadquery_framework.kicad.jlcpcb_constraints import (
    CU_OUTER_MM,
    FR4_2L_DK,
    FR4_2L_LOSS_TANGENT,
    SOLDER_MASK_THICKNESS_MM,
    SOLDER_MASK_EXPANSION_MM,
    EDGE_CUTS_WIDTH_MM,
    TH_GPIO_DRILL_MM,
    TH_GPIO_PAD_MM,
    TH_DEFAULT_ANNULAR_MM,
    SILK_LARGE_SIZE_MM,
    SILK_LARGE_THICK_MM,
)


def uid():
    """Generate a KiCad-style UUID."""
    return str(uuid.uuid4())


def arc_points(cx, cy, r, start_deg, end_deg, n=16):
    """Generate arc points for rounded corners."""
    pts = []
    for i in range(n + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * i / n)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def rounded_rect_outline(w, h, r, cx=0, cy=0):
    """Generate Edge.Cuts line segments for a rounded rectangle."""
    r = min(r, w / 2, h / 2)
    hw, hh = w / 2, h / 2
    lines = []

    corners = [
        (cx + hw - r, cy + hh - r, 0, 90),
        (cx - hw + r, cy + hh - r, 90, 180),
        (cx - hw + r, cy - hh + r, 180, 270),
        (cx + hw - r, cy - hh + r, 270, 360),
    ]

    edges = [
        ((cx + hw - r, cy + hh), (cx - hw + r, cy + hh)),
        ((cx - hw, cy + hh - r), (cx - hw, cy - hh + r)),
        ((cx - hw + r, cy - hh), (cx + hw - r, cy - hh)),
        ((cx + hw, cy - hh + r), (cx + hw, cy + hh - r)),
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


def rect_outline(w, h, cx=0, cy=0):
    """Generate Edge.Cuts lines for a plain rectangle."""
    return rounded_rect_outline(w, h, 0, cx, cy)


def hexagon_outline(cx, cy, r):
    """Generate Edge.Cuts lines for a regular hexagon (flat-top)."""
    pts = []
    for i in range(6):
        angle = math.radians(60 * i + 30)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    lines = []
    for i in range(6):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 6]
        lines.append(("line", x1, y1, x2, y2))
    return lines


def rounded_hexagon_outline(cx, cy, r, corner_r):
    """Generate Edge.Cuts for a regular hexagon (flat-top) with rounded corners.

    corner_r is the radius at each vertex; clamped so insets do not cross.
    """
    corner_r = min(corner_r, r * 0.4)
    if corner_r < 0.01:
        return hexagon_outline(cx, cy, r)
    pts = []
    for i in range(6):
        angle = math.radians(60 * i + 30)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    a_pts = []
    b_pts = []
    for i in range(6):
        vx, vy = pts[i]
        px, py = pts[(i - 1) % 6]
        nx, nxy = pts[(i + 1) % 6]
        dx_prev = vx - px
        dy_prev = vy - py
        len_prev = math.hypot(dx_prev, dy_prev) or 1e-9
        dx_next = nx - vx
        dy_next = nxy - vy
        len_next = math.hypot(dx_next, dy_next) or 1e-9
        a_pts.append((vx - corner_r * (dx_prev / len_prev), vy - corner_r * (dy_prev / len_prev)))
        b_pts.append((vx - corner_r * (dx_next / len_next), vy - corner_r * (dy_next / len_next)))
    segs = []
    for i in range(6):
        bx_prev, by_prev = b_pts[(i - 1) % 6]
        ax, ay = a_pts[i]
        segs.append(("line", bx_prev, by_prev, ax, ay))
        vx, vy = pts[i]
        sa = math.degrees(math.atan2(ay - vy, ax - vx))
        ea = math.degrees(math.atan2(b_pts[i][1] - vy, b_pts[i][0] - vx))
        if ea <= sa:
            ea += 360
        segs.append(("arc", vx, vy, corner_r, sa, ea))
    return segs


def capsule_outline(length, width, cx=0, cy=0):
    """Generate Edge.Cuts for a capsule (rectangle with semicircular ends).

    length: total length along the long axis (x).
    width: diameter of the semicircular ends (and height of the straight sides).
    No sharp corners — ends are full semicircles.
    """
    if width >= length:
        return rounded_rect_outline(length, width, width / 2 - 0.01, cx, cy)
    r = width / 2
    half_rect = (length - width) / 2
    segs = []
    segs.append(("arc", cx - half_rect, cy, r, 90, 270))
    segs.append(("line", cx - half_rect, cy - r, cx + half_rect, cy - r))
    segs.append(("arc", cx + half_rect, cy, r, 270, 90))
    segs.append(("line", cx + half_rect, cy + r, cx - half_rect, cy + r))
    return segs


def rotated_rect_outline(w, h, cx, cy, angle_deg):
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


def outline_to_sexpr(outline_segments, layer="Edge.Cuts", width=EDGE_CUTS_WIDTH_MM):
    """Convert outline segments to KiCad S-expression strings."""
    lines = []
    for seg in outline_segments:
        if seg[0] == "line":
            _, x1, y1, x2, y2 = seg
            lines.append(
                f'  (gr_line (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) '
                f'(layer "{layer}") (width {width}) (uuid "{uid()}"))'
            )
        elif seg[0] == "arc":
            _, acx, acy, r, sa, ea = seg
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
                f'(layer "{layer}") (width {width}) (uuid "{uid()}"))'
            )
    return "\n".join(lines)


def circle_sexpr(cx, cy, r, layer="Edge.Cuts", width=EDGE_CUTS_WIDTH_MM):
    """Generate a KiCad circle S-expression."""
    return (
        f'  (gr_circle (center {cx:.4f} {cy:.4f}) (end {cx + r:.4f} {cy:.4f}) '
        f'(layer "{layer}") (width {width}) (uuid "{uid()}"))'
    )


def through_hole_pad(cx, cy, drill_d, pad_d=None):
    """Generate a mounting hole footprint at (cx, cy)."""
    if pad_d is None:
        pad_d = drill_d + 2 * TH_DEFAULT_ANNULAR_MM
    u = uid()
    return f"""  (footprint "MountingHole:MountingHole_{drill_d:.1f}mm" (layer "F.Cu")
    (uuid "{u}")
    (at {cx:.4f} {cy:.4f})
    (pad "" thru_hole circle (at 0 0) (size {pad_d:.2f} {pad_d:.2f}) (drill {drill_d:.2f})
      (layers "*.Cu" "*.Mask")
      (uuid "{uid()}")
    )
  )"""


def header_pad_row(cx, cy, count, pitch, angle_deg=0, drill_d=TH_GPIO_DRILL_MM, pad_d=TH_GPIO_PAD_MM):
    """Generate through-hole pads for a row of pin header holes.

    Args:
        cx, cy: center of the row
        count: number of pins
        pitch: pin spacing (mm)
        angle_deg: rotation of the row
        drill_d: drill hole diameter (mm)
        pad_d: pad diameter (mm)
    """
    pads = []
    span = (count - 1) * pitch
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    for i in range(count):
        offset = -span / 2 + i * pitch
        px = cx + offset * cos_a
        py = cy + offset * sin_a
        pads.append(through_hole_pad(px, py, drill_d, pad_d))
    return "\n".join(pads)


def text_sexpr(text, cx, cy, layer="F.SilkS", size=SILK_LARGE_SIZE_MM, thickness=SILK_LARGE_THICK_MM):
    """Generate a text label."""
    return (
        f'  (gr_text "{text}" (at {cx:.4f} {cy:.4f}) (layer "{layer}") '
        f'(uuid "{uid()}")\n'
        f'    (effects (font (size {size} {size}) (thickness {thickness})))\n'
        f'  )'
    )


def kicad_pcb_wrapper(title, thickness, inner_content, generator_name="cadquery_framework"):
    """Wrap content in a complete .kicad_pcb file.

    Args:
        title: board title for title block
        thickness: PCB thickness in mm
        inner_content: KiCad S-expression content (outlines, holes, etc.)
        generator_name: name to put in the generator field
    """
    return f"""(kicad_pcb (version 20221018) (generator "{generator_name}")
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
      (layer "F.Mask" (type "Top Solder Mask") (thickness {SOLDER_MASK_THICKNESS_MM}))
      (layer "F.Cu" (type "copper") (thickness {CU_OUTER_MM}))
      (layer "dielectric 1" (type "core") (thickness {"{:.3f}".format(thickness - 2 * CU_OUTER_MM)}) (material "FR4") (epsilon_r {FR4_2L_DK}) (loss_tangent {FR4_2L_LOSS_TANGENT}))
      (layer "B.Cu" (type "copper") (thickness {CU_OUTER_MM}))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness {SOLDER_MASK_THICKNESS_MM}))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
    )
    (pad_to_mask_clearance {SOLDER_MASK_EXPANSION_MM})
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
