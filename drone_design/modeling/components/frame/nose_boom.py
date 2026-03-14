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

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

BOOM_LENGTH  = _D["nose_boom"]["length"]       # 380 mm — full assembled length
BOOM_WIDTH   = _D["nose_boom"]["width"]         # 20 mm
BOOM_THICK   = _D["nose_boom"]["thickness"]     # 1.6 mm
BOOM_FLANGE  = _D["nose_boom"]["flange_width"]  # 4 mm
BOOM_WEB     = _D["nose_boom"]["web_width"]     # 3 mm

# Pin header connection specs (root-end attachment to frame)
HEADER_PITCH      = _D["connections"]["header_pitch"]          # 2.54 mm
HEADER_HOLE_D     = _D["connections"]["header_hole_diameter"]  # 1.0 mm
BOOM_HEADER_PINS  = _D["connections"]["boom_header_pins"]      # 6
BOOM_HEADER_INSET = _D["connections"]["boom_header_inset"]     # 3.0 mm

# Modular overlap / adjustment zone
OVERLAP_LENGTH = 40.0   # mm — how far the root slides into the tip
HOLE_PITCH     = 10.0   # mm — spacing between M2 adjustment holes
M2_CLEARANCE   = 2.2    # mm — hole diameter for M2 bolt clearance

# Derived lengths
ROOT_USABLE  = 150.0                          # mm — frame to start of overlap
ROOT_TOTAL   = ROOT_USABLE + OVERLAP_LENGTH   # 190 mm — physical root piece
TIP_TOTAL    = BOOM_LENGTH - ROOT_USABLE      # 230 mm — physical tip piece
                                              # (collar is 40 mm of that)

# Number of M2 holes in the overlap zone
_N_HOLES = int(OVERLAP_LENGTH / HOLE_PITCH)  # 4


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

    for side in (-1, 1):
        cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_w / 2)
        pocket = (
            cq.Workplane("XY")
            .box(cutout_len, cutout_w, BOOM_THICK, centered=(True, True, False))
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
        # Shift so that X=0 is the left (root) face:
        .translate((ROOT_TOTAL / 2, 0.0, 0.0))
    )

    # --- I-beam pockets along the USABLE section only ---
    # We preserve 30 mm at the root face (header hole area) + leave the overlap
    # tail solid (we will strip its flanges separately).
    cutout_len = ROOT_USABLE - 30.0   # pocket from x=30 to x=ROOT_USABLE
    cutout_w   = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_len > 1.0 and cutout_w > 1.0:
        pocket_cx = 30.0 + cutout_len / 2   # centre of pocket in root-local X
        for side in (-1, 1):
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_w / 2)
            pocket = (
                cq.Workplane("XY")
                .box(cutout_len, cutout_w, BOOM_THICK, centered=(True, True, False))
                .translate((pocket_cx, cy, 0.0))
            )
            root = root.cut(pocket)

    # --- Strip flanges from the overlap tail ---
    # The tail spans x = ROOT_USABLE … ROOT_TOTAL.
    # We remove the flange strips (BOOM_FLANGE wide, each side of the web)
    # so only the web (3 mm wide) remains — it slides into the tip collar.
    flange_cutout_w = (BOOM_WIDTH - BOOM_WEB) / 2   # = 8.5 mm each side
    for side in (-1, 1):
        cy = side * (BOOM_WEB / 2 + flange_cutout_w / 2)
        flange_strip = (
            cq.Workplane("XY")
            .box(OVERLAP_LENGTH, flange_cutout_w, BOOM_THICK,
                 centered=(True, True, False))
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

    return root


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
        .translate((TIP_TOTAL / 2, 0.0, 0.0))
    )

    # --- I-beam pockets along the body (past the collar) ---
    # Leave 30 mm solid at the nozzle end for nozzle attachment.
    body_len    = TIP_TOTAL - OVERLAP_LENGTH   # = 190 mm
    cutout_len  = body_len - 30.0
    cutout_w    = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_len > 1.0 and cutout_w > 1.0:
        pocket_cx = OVERLAP_LENGTH + cutout_len / 2
        for side in (-1, 1):
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_w / 2)
            pocket = (
                cq.Workplane("XY")
                .box(cutout_len, cutout_w, BOOM_THICK, centered=(True, True, False))
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

    return tip


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
    root = make_boom_root()
    tip  = make_boom_tip()

    # Root: translate so its tip face (X = ROOT_TOTAL in root-local) sits at
    # X = 0 in assembly space.  Root occupies [-ROOT_TOTAL, 0].
    root = root.translate((-ROOT_TOTAL, 0.0, 0.0))

    # Tip: translate so its collar face (X = 0 in tip-local) sits at
    # X = -(overlap_mm) in assembly space (the root web sticks out by overlap_mm).
    # At default (overlap_mm = OVERLAP_LENGTH = 40), collar face at X = -40.
    tip = tip.translate((-overlap_mm, 0.0, 0.0))

    # Combine — this is a visual assembly union; in reality the two pieces are
    # separate PCBs that overlap and are bolted together.
    return root.union(tip)
