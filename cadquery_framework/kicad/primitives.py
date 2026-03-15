"""KiCad S-expression primitives for generating .kicad_pcb files.

These functions generate the building blocks for mechanical PCB files:
board outlines, mounting holes, cutouts, silkscreen labels, etc.
"""

import math
import uuid
from datetime import datetime


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


def outline_to_sexpr(outline_segments, layer="Edge.Cuts", width=0.05):
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


def circle_sexpr(cx, cy, r, layer="Edge.Cuts", width=0.05):
    """Generate a KiCad circle S-expression."""
    return (
        f'  (gr_circle (center {cx:.4f} {cy:.4f}) (end {cx + r:.4f} {cy:.4f}) '
        f'(layer "{layer}") (width {width}) (uuid "{uid()}"))'
    )


def through_hole_pad(cx, cy, drill_d, pad_d=None):
    """Generate a mounting hole footprint at (cx, cy)."""
    if pad_d is None:
        pad_d = drill_d + 0.5
    u = uid()
    return f"""  (footprint "MountingHole:MountingHole_{drill_d:.1f}mm" (layer "F.Cu")
    (uuid "{u}")
    (at {cx:.4f} {cy:.4f})
    (pad "" thru_hole circle (at 0 0) (size {pad_d:.2f} {pad_d:.2f}) (drill {drill_d:.2f})
      (layers "*.Cu" "*.Mask")
      (uuid "{uid()}")
    )
  )"""


def header_pad_row(cx, cy, count, pitch, angle_deg=0, drill_d=1.0, pad_d=1.7):
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


def text_sexpr(text, cx, cy, layer="F.SilkS", size=1.5, thickness=0.15):
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
