"""Skeleton frame plate with Kagome-lattice cutouts for optimal stiffness/weight."""

import json
import math
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

PLATE_SIZE     = _D["frame"]["plate_size"]
PLATE_CORNER_R = _D["frame"]["plate_corner_radius"]
SLOT_W         = _D["frame"]["arm_slot_width"]
SLOT_L         = _D["frame"]["arm_slot_length"]
ARM_ANGLES     = _D["arms"]["arm_angles_deg"]
DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
KAGOME_CELL    = _D["assembly"]["kagome_cell_size"]
KAGOME_HOLE_R  = _D["assembly"]["kagome_hole_radius"]
KAGOME_WEB_MIN = _D["assembly"]["kagome_min_web"]
KAGOME_FILLET_R = _D["assembly"]["kagome_fillet_radius"]


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
