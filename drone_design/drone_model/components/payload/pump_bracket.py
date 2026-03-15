"""Friction-fit clip bracket for Takasago RP-Q1 pump — 1.6mm FR4.

Geometry: U-shaped channel that the pump body slides into. The channel
inner width matches the pump body width (11.9mm). Two zip-tie slots in
the walls allow securing the pump. Base plate extends beyond the channel
with M2.2 holes for bolting to the bottom frame plate.

Origin: base plate center at (0, 0, thickness/2).
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())
_B = _D["pump_bracket"]
_P = _D["pump"]

PUMP_W       = _P["body_width"]
CHANNEL_L    = _B["channel_length"]
WALL_H       = _B["wall_height"]
T            = _B["thickness"]
BASE_EXT     = _B["base_extension"]
ZIP_W        = _B["zip_slot_width"]
ZIP_H        = _B["zip_slot_height"]
FRAME_HOLE_D = _B["frame_hole_diameter"]
FRAME_INSET  = _B["frame_hole_inset"]
PCB_EDGE_CHAMFER = _D["assembly"]["pcb_edge_chamfer"]

CATALOG = {
    "pump_bracket": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm",
        "dims": "25 x 40 x 1.6mm",
        "mass_g": 3, "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "L-bracket to mount peristaltic pump",
        "interface": "Bolts to bottom plate; pump screws to bracket",
    },
}


def make_pump_bracket():
    """U-channel clip bracket with zip-tie slots and frame mounting holes."""
    base_chamfer = min(PCB_EDGE_CHAMFER, T * 0.45)
    wall_chamfer = min(PCB_EDGE_CHAMFER, T * 0.45)

    total_w = PUMP_W + 2 * T + 2 * BASE_EXT
    base_depth = CHANNEL_L

    # Base plate
    base = (
        cq.Workplane("XY")
        .rect(total_w, base_depth)
        .extrude(T)
        .edges("|Z")
        .chamfer(base_chamfer)
    )

    # Left wall
    left = (
        cq.Workplane("XY")
        .rect(T, base_depth)
        .extrude(WALL_H)
        .edges("|Z")
        .chamfer(wall_chamfer)
        .translate((-(PUMP_W / 2 + T / 2), 0, T))
    )

    # Right wall
    right = (
        cq.Workplane("XY")
        .rect(T, base_depth)
        .extrude(WALL_H)
        .edges("|Z")
        .chamfer(wall_chamfer)
        .translate(((PUMP_W / 2 + T / 2), 0, T))
    )

    bracket = base.union(left).union(right)

    # Zip-tie slots in both walls (rectangular cutouts near top)
    zip_z = T + WALL_H - ZIP_H - 1.0
    for sx in [-1, 1]:
        wx = sx * (PUMP_W / 2 + T / 2)
        slot = (
            cq.Workplane("XY")
            .rect(T + 1, ZIP_W)
            .extrude(ZIP_H)
            .translate((wx, 0, zip_z))
        )
        bracket = bracket.cut(slot)

    # Frame mounting holes in base plate extensions
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (total_w / 2 - FRAME_INSET)
            hy = sy * (base_depth / 2 - FRAME_INSET)
            hole = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(FRAME_HOLE_D / 2)
                .extrude(T)
            )
            bracket = bracket.cut(hole)

    anchors = {}
    if Anchor is not None:
        # Base plate bottom face (Z=0), normal down — outermost when underslung
        anchors["base_mount"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Base plate outermost surface when underslung",
        )
        # Top of walls — nearest face to plate when underslung
        anchors["top_mount"] = Anchor(
            point=(0, 0, T + WALL_H),
            normal=(0, 0, 1),
            label="Wall tops — nearest face to plate when underslung",
        )
        # Channel center at top of base plate — where pump body sits
        anchors["channel_center"] = Anchor(
            point=(0, 0, T),
            normal=(0, 0, 1),
            label="Channel center where pump rests",
        )

    return bracket, anchors


# =============================================================================
# KiCad PCB generator
# =============================================================================

try:
    from cadquery_framework.kicad.primitives import (
        rounded_rect_outline, outline_to_sexpr, through_hole_pad,
        text_sexpr, kicad_pcb_wrapper,
    )
except ImportError:
    pass  # KiCad export not available

PCB_OUTLINE_R = _D["assembly"].get("pcb_outline_corner_radius", 1.5)


def generate_pump_bracket_pcb():
    """Generate .kicad_pcb for the RP-Q1 pump clip bracket (unfolded U-channel).

    The 3D bracket is a U-channel (base + two walls). As a flat PCB for
    fabrication, it unfolds into: [left wall] - [FOLD] - [base] - [FOLD] - [right wall].
    """
    pump_w = PUMP_W
    channel_l = CHANNEL_L
    wall_h = WALL_H
    pb_t = T
    base_ext = BASE_EXT
    frame_hole_d = FRAME_HOLE_D
    frame_inset = FRAME_INSET
    zip_h = ZIP_H

    # Unfolded total width: wall + base (pump_w + 2*base_ext) + wall
    base_w = pump_w + 2 * pb_t + 2 * base_ext
    total_w = 2 * wall_h + base_w

    segs = []
    segs.extend(rounded_rect_outline(total_w, channel_l, min(PCB_OUTLINE_R, channel_l / 2 - 0.5)))
    content = outline_to_sexpr(segs)

    # Fold lines (silkscreen)
    fold_x1 = -base_w / 2
    fold_x2 = base_w / 2
    content += "\n" + text_sexpr("FOLD", fold_x1, 0, "F.SilkS", 1.0, 0.12)
    content += "\n" + text_sexpr("FOLD", fold_x2, 0, "F.SilkS", 1.0, 0.12)

    # Frame mounting holes (4 corners of base section)
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (base_w / 2 - frame_inset)
            hy = sy * (channel_l / 2 - frame_inset)
            content += "\n" + through_hole_pad(hx, hy, frame_hole_d, frame_hole_d + 1.0)

    # Zip-tie slots in wall sections (rectangular cutouts near top of each wall)
    zip_y = 0
    for sx in [-1, 1]:
        slot_cx = sx * (base_w / 2 + wall_h - zip_h - 1.0)
        content += "\n" + text_sexpr("ZIP", slot_cx, zip_y, "F.SilkS", 0.8, 0.1)

    content += "\n" + text_sexpr("PUMP CLIP", 0, 0, "F.SilkS", 1.5, 0.15)
    content += "\n" + text_sexpr(f"{total_w:.0f}x{channel_l:.0f}mm  FR4 {pb_t:.1f}mm", 0, 4, "F.SilkS", 1.0, 0.12)

    return kicad_pcb_wrapper("Drone Pump Clip Bracket", pb_t, content)
