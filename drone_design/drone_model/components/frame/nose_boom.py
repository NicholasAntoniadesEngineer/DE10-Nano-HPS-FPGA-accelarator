"""Two-section modular nose boom (watering spout arm) with I-beam profile.

Sections
--------
Root section  (~150 mm usable + 40 mm overlap tail, 190 mm total)
    Attaches to the airframe.  The last 40 mm of the root has its flanges
    removed so that the plain web slides *inside* the tip section's full
    I-beam channel.  M2 bolt holes (2.2 mm clearance) are drilled every
    10 mm along the overlap zone so that the two sections can be bolted at
    any of 4-5 positions, giving adjustable total boom length.

Tip section   (230 mm usable body + 40 mm full-I-beam collar, 270 mm total)
    Carries the drip nozzle at the far end.  The inner 40 mm collar is the
    full I-beam profile and receives the root web that slides inside it.
    Matching M2 holes are drilled through *both* flanges + web in the collar
    so a bolt through the collar pinches the root web at the chosen position.

Default (fully-inserted) assembly total length = 150 + 230 = 380 mm, matching
the original nose_boom.length dimension.

Coordinate convention (local per section)
------------------------------------------
The long axis is X.  X = 0 is the frame-side (root) end of each section.
Positive X points toward the nozzle.
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

BOOM_LENGTH  = _D["nose_boom"]["length"]       # 380 mm — full assembled length
BOOM_WIDTH   = _D["nose_boom"]["width"]         # 20 mm
BOOM_THICK   = _D["nose_boom"]["thickness"]     # 1.6 mm
BOOM_FLANGE  = _D["nose_boom"]["flange_width"]  # 4 mm
BOOM_WEB     = _D["nose_boom"]["web_width"]     # 3 mm

# Pin header connection specs (root-end attachment to frame)
HEADER_PITCH      = _D["connections"]["header_pitch"]          # 2.54 mm
HEADER_HOLE_D     = _D["connections"]["header_hole_diameter"]  # 1.0 mm
HEADER_PAD_D      = _D["connections"]["header_pad_diameter"]   # 1.7 mm
BOOM_HEADER_PINS  = _D["connections"]["boom_header_pins"]      # 6
BOOM_HEADER_INSET = _D["connections"]["boom_header_inset"]     # 3.0 mm
PCB_EDGE_CHAMFER = _D["assembly"]["pcb_edge_chamfer"]

OVERLAP_LENGTH = _D["nose_boom"]["overlap_length"]
HOLE_PITCH     = 10.0
M2_CLEARANCE   = 2.2

ROOT_USABLE  = _D["nose_boom"]["root_usable_length"]
ROOT_TOTAL   = ROOT_USABLE + OVERLAP_LENGTH
TIP_TOTAL    = BOOM_LENGTH - ROOT_USABLE

_N_HOLES = max(1, int(OVERLAP_LENGTH / HOLE_PITCH))

CATALOG = {
    "nose_boom": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm",
        "dims": f"{BOOM_LENGTH} x {BOOM_WIDTH} x 1.6mm",
        "mass_g": 18, "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Modular two-section I-beam boom with adjustable overlap",
        "interface": "Root bolts to frame; nozzle at tip",
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ibeam_rect(length: float, width: float, thick: float) -> cq.Workplane:
    """Solid rectangular slab — basis for I-beam cutouts."""
    return (
        cq.Workplane("XY")
        .box(length, width, thick, centered=(True, True, False))
    )


def _cut_ibeam_pockets(solid: cq.Workplane,
                       length: float,
                       leave_flanges_mm: float = 30.0) -> cq.Workplane:
    """Remove material between the flanges and web, leaving an I-beam profile.

    Parameters
    ----------
    solid:
        The rectangular slab to carve.
    length:
        Overall length of the slab.
    leave_flanges_mm:
        Length of solid material to preserve at each *end* of the slab
        (i.e. no pocketing in the first/last N mm).
    """
    cutout_len = length - 2 * leave_flanges_mm
    cutout_w   = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_w <= 1.0 or cutout_len <= 1.0:
        return solid

    pocket_fillet = min(PCB_EDGE_CHAMFER * 2, cutout_w / 2 - 0.3, cutout_len / 2 - 0.3)
    for side in (-1, 1):
        cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_w / 2)
        pocket = (
            cq.Workplane("XY")
            .box(cutout_len, cutout_w, BOOM_THICK, centered=(True, True, False))
            .edges("|Z")
            .fillet(pocket_fillet)
            .translate((0.0, cy, 0.0))
        )
        solid = solid.cut(pocket)
    return solid


def _drill_m2_row(solid: cq.Workplane,
                  x_positions,
                  y_center: float = 0.0) -> cq.Workplane:
    """Drill M2 clearance holes through the full thickness at given X positions."""
    r = M2_CLEARANCE / 2
    for x in x_positions:
        cyl = (
            cq.Workplane("XY")
            .cylinder(BOOM_THICK, r)
            .translate((x, y_center, BOOM_THICK / 2))
        )
        solid = solid.cut(cyl)
    return solid


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def make_boom_root() -> cq.Workplane:
    """Build the root section of the modular nose boom.

    Total length: ROOT_TOTAL = 190 mm.
      0 … ROOT_USABLE (150 mm)  — full I-beam, root header holes, attaches to
                                   airframe.
      ROOT_USABLE … ROOT_TOTAL  — web-only (flanges stripped) overlap tail that
                                   slides inside the tip collar.  M2 adjustment
                                   holes every HOLE_PITCH mm.

    Local X = 0 is the frame-side (root) end.
    """
    # --- Main slab ---
    root = (
        cq.Workplane("XY")
        .box(ROOT_TOTAL, BOOM_WIDTH, BOOM_THICK, centered=(True, True, False))
        .edges("|Z")
        .chamfer(min(PCB_EDGE_CHAMFER, BOOM_THICK * 0.45))
        # Shift so that X=0 is the left (root) face:
        .translate((ROOT_TOTAL / 2, 0.0, 0.0))
    )

    # --- I-beam pockets along the USABLE section only ---
    # We preserve 30 mm at the root face (header hole area) + leave the overlap
    # tail solid (we will strip its flanges separately).
    cutout_len = ROOT_USABLE - 30.0   # pocket from x=30 to x=ROOT_USABLE
    cutout_w   = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_len > 1.0 and cutout_w > 1.0:
        pocket_fillet = min(PCB_EDGE_CHAMFER * 2, cutout_w / 2 - 0.3, cutout_len / 2 - 0.3)
        pocket_cx = 30.0 + cutout_len / 2   # centre of pocket in root-local X
        for side in (-1, 1):
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_w / 2)
            pocket = (
                cq.Workplane("XY")
                .box(cutout_len, cutout_w, BOOM_THICK, centered=(True, True, False))
                .edges("|Z")
                .fillet(pocket_fillet)
                .translate((pocket_cx, cy, 0.0))
            )
            root = root.cut(pocket)

    # --- Strip flanges from the overlap tail ---
    # The tail spans x = ROOT_USABLE … ROOT_TOTAL.
    # We remove the flange strips (BOOM_FLANGE wide, each side of the web)
    # so only the web (3 mm wide) remains — it slides into the tip collar.
    flange_cutout_w = (BOOM_WIDTH - BOOM_WEB) / 2   # = 8.5 mm each side
    flange_fillet = min(PCB_EDGE_CHAMFER * 2, flange_cutout_w / 2 - 0.3, OVERLAP_LENGTH / 2 - 0.3)
    for side in (-1, 1):
        cy = side * (BOOM_WEB / 2 + flange_cutout_w / 2)
        flange_strip = (
            cq.Workplane("XY")
            .box(OVERLAP_LENGTH, flange_cutout_w, BOOM_THICK,
                 centered=(True, True, False))
            .edges("|Z")
            .fillet(flange_fillet)
            .translate((ROOT_USABLE + OVERLAP_LENGTH / 2, cy, 0.0))
        )
        root = root.cut(flange_strip)

    # --- Root-end header holes (two rows, for frame pin-header connection) ---
    hole_r = HEADER_HOLE_D / 2
    span   = (BOOM_HEADER_PINS - 1) * HEADER_PITCH
    # Place header rows 10 mm in from the root face (x = 0)
    hx_centre = BOOM_HEADER_INSET + 10.0

    for row_offset in (-4.0, 4.0):
        for i in range(BOOM_HEADER_PINS):
            hy = -span / 2 + i * HEADER_PITCH
            hole = (
                cq.Workplane("XY")
                .cylinder(BOOM_THICK, hole_r)
                .translate((hx_centre + row_offset, hy, BOOM_THICK / 2))
            )
            root = root.cut(hole)

    # --- M2 adjustment holes through the overlap web tail ---
    # Spaced HOLE_PITCH apart starting at ROOT_USABLE + HOLE_PITCH/2
    # so the first hole is 5 mm inside the tail.
    overlap_hole_xs = [
        ROOT_USABLE + (k + 0.5) * HOLE_PITCH
        for k in range(_N_HOLES)
    ]
    root = _drill_m2_row(root, overlap_hole_xs)

    anchors = {}
    if Anchor is not None:
        anchors["root"] = Anchor(
            point=(0, 0, BOOM_THICK / 2),
            normal=(-1, 0, 0),
            label="root (frame attachment)",
        )
        anchors["tip"] = Anchor(
            point=(ROOT_TOTAL, 0, BOOM_THICK / 2),
            normal=(1, 0, 0),
            label="tip (overlap end)",
        )
        anchors["top_face"] = Anchor(
            point=(ROOT_TOTAL / 2, 0, BOOM_THICK),
            normal=(0, 0, 1),
            label="top face (root)",
        )

    return root, anchors


def make_boom_tip() -> cq.Workplane:
    """Build the tip section of the modular nose boom.

    Total length: TIP_TOTAL = 230 mm.
      0 … OVERLAP_LENGTH (40 mm)  — full I-beam collar that receives the root's
                                     web tail.  Matching M2 holes let a bolt
                                     clamp the two sections at the desired
                                     extension.
      OVERLAP_LENGTH … TIP_TOTAL  — full I-beam body carrying the drip nozzle.

    Local X = 0 is the collar end (the end that faces the airframe / overlaps
    the root).  Positive X points toward the nozzle.
    """
    # --- Main slab ---
    tip = (
        cq.Workplane("XY")
        .box(TIP_TOTAL, BOOM_WIDTH, BOOM_THICK, centered=(True, True, False))
        .edges("|Z")
        .chamfer(min(PCB_EDGE_CHAMFER, BOOM_THICK * 0.45))
        .translate((TIP_TOTAL / 2, 0.0, 0.0))
    )

    # --- I-beam pockets along the body (past the collar) ---
    # Leave 30 mm solid at the nozzle end for nozzle attachment.
    body_len    = TIP_TOTAL - OVERLAP_LENGTH   # = 190 mm
    cutout_len  = body_len - 30.0
    cutout_w    = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_len > 1.0 and cutout_w > 1.0:
        pocket_fillet = min(PCB_EDGE_CHAMFER * 2, cutout_w / 2 - 0.3, cutout_len / 2 - 0.3)
        pocket_cx = OVERLAP_LENGTH + cutout_len / 2
        for side in (-1, 1):
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_w / 2)
            pocket = (
                cq.Workplane("XY")
                .box(cutout_len, cutout_w, BOOM_THICK, centered=(True, True, False))
                .edges("|Z")
                .fillet(pocket_fillet)
                .translate((pocket_cx, cy, 0.0))
            )
            tip = tip.cut(pocket)

    # --- M2 adjustment holes through the collar (full flange + web) ---
    # These match the spacing in make_boom_root so any hole aligns with any
    # other hole when the root tail is inserted.
    # Place them at HOLE_PITCH/2, 3*HOLE_PITCH/2, … from the collar face.
    collar_hole_xs = [
        (k + 0.5) * HOLE_PITCH
        for k in range(_N_HOLES)
    ]
    tip = _drill_m2_row(tip, collar_hole_xs)

    anchors = {}
    if Anchor is not None:
        anchors["collar"] = Anchor(
            point=(0, 0, BOOM_THICK / 2),
            normal=(-1, 0, 0),
            label="collar (receives root web)",
        )
        anchors["nozzle_tip"] = Anchor(
            point=(TIP_TOTAL, 0, BOOM_THICK / 2),
            normal=(1, 0, 0),
            label="nozzle tip",
        )
        anchors["camera_mount"] = Anchor(
            point=(TIP_TOTAL * 0.4, 0, 0),
            normal=(0, 0, -1),
            label="camera mount (underside)",
        )
        anchors["nozzle_mount"] = Anchor(
            point=(TIP_TOTAL, 0, 0),
            normal=(0, 0, -1),
            label="nozzle mount (boom underside at tip)",
        )

    return tip, anchors


# ---------------------------------------------------------------------------
# Combined assembly (backward-compatible)
# ---------------------------------------------------------------------------

def make_nose_boom(overlap_mm: float = OVERLAP_LENGTH) -> cq.Workplane:
    """Return both sections assembled at the given overlap, as a single solid.

    Parameters
    ----------
    overlap_mm:
        How far the root's web tail is inserted into the tip collar.
        Default = OVERLAP_LENGTH (40 mm) → total length = 380 mm.
        Range: HOLE_PITCH … OVERLAP_LENGTH.

    The root section sits at X < 0 (frame side) and the tip at X >= 0.
    Assembly origin is the root/tip interface plane.
    """
    root_result = make_boom_root()
    tip_result  = make_boom_tip()
    root_shape = root_result[0] if isinstance(root_result, tuple) else root_result
    tip_shape  = tip_result[0] if isinstance(tip_result, tuple) else tip_result

    # Root: translate so its tip face (X = ROOT_TOTAL in root-local) sits at
    # X = 0 in assembly space.  Root occupies [-ROOT_TOTAL, 0].
    root_shape = root_shape.translate((-ROOT_TOTAL, 0.0, 0.0))

    # Tip: translate so its collar face (X = 0 in tip-local) sits at
    # X = -(overlap_mm) in assembly space (the root web sticks out by overlap_mm).
    # At default (overlap_mm = OVERLAP_LENGTH = 40), collar face at X = -40.
    tip_shape = tip_shape.translate((-overlap_mm, 0.0, 0.0))

    # Combine
    shape = root_shape.union(tip_shape)

    # Assembly-space total: root face at -ROOT_TOTAL, tip end at TIP_TOTAL - overlap_mm
    anchors = {}
    if Anchor is not None:
        anchors["root"] = Anchor(
            point=(-ROOT_TOTAL, 0, BOOM_THICK / 2),
            normal=(-1, 0, 0),
            label="root (frame attachment)",
        )
        tip_end_x = TIP_TOTAL - overlap_mm
        anchors["tip"] = Anchor(
            point=(tip_end_x, 0, BOOM_THICK / 2),
            normal=(1, 0, 0),
            label="nozzle tip",
        )
        camera_x = -overlap_mm + TIP_TOTAL * 0.4
        anchors["camera_platform"] = Anchor(
            point=(camera_x, 0, BOOM_THICK),
            normal=(0, 0, 1),
            label="camera platform (top of boom, forward-facing mount)",
        )
        anchors["nozzle_mount"] = Anchor(
            point=(tip_end_x, 0, 0),
            normal=(0, 0, -1),
            label="nozzle mount (boom underside at tip)",
        )

    return shape, anchors


# =============================================================================
# KiCad PCB generator
# =============================================================================

try:
    from cadquery_framework.kicad.primitives import (
        rounded_rect_outline, outline_to_sexpr, header_pad_row,
        text_sexpr, kicad_pcb_wrapper,
    )
except ImportError:
    pass  # KiCad export not available

PCB_OUTLINE_R = _D["assembly"].get("pcb_outline_corner_radius", 1.5)


def generate_nose_boom_pcb():
    """Generate .kicad_pcb for the nose boom (I-beam profile). Rounded corners in outline and cutouts."""
    segs = []

    # Outer rectangle — rounded corners in cutout design
    segs.extend(rounded_rect_outline(BOOM_LENGTH, BOOM_WIDTH, min(PCB_OUTLINE_R, BOOM_WIDTH / 2 - 0.5), 0, 0))

    # I-beam side cutouts — rounded corners
    cutout_length = BOOM_LENGTH - 40  # leave 20mm solid at each end
    cutout_width = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    cutout_r = min(PCB_OUTLINE_R, cutout_width / 2 - 0.2) if cutout_width > 1 else 0
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_width / 2)
            segs.extend(rounded_rect_outline(cutout_length, cutout_width, cutout_r, 0, cy))

    content = outline_to_sexpr(segs)

    # Root end header holes (two rows for plate connection)
    root_x = -BOOM_LENGTH / 2 + BOOM_HEADER_INSET + 10
    for row_offset in [-4.0, 4.0]:
        content += "\n" + header_pad_row(root_x + row_offset, 0, BOOM_HEADER_PINS, HEADER_PITCH, angle_deg=90, drill_d=HEADER_HOLE_D, pad_d=HEADER_PAD_D)

    content += "\n" + text_sexpr("BOOM", 0, 0, "F.SilkS", 2, 0.2)
    content += "\n" + text_sexpr(f"{BOOM_LENGTH:.0f}x{BOOM_WIDTH:.0f}mm  FR4 {BOOM_THICK:.1f}mm", 0, 4, "F.SilkS", 1.0, 0.12)

    return kicad_pcb_wrapper("Drone Nose Boom (I-Beam)", BOOM_THICK, content)
