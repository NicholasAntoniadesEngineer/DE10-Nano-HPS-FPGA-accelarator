"""Automatic silk label repositioner — finds collision-free positions for all reference labels.

Algorithm:
  1. Compute default silk positions (courtyard_h/2 + 1.0mm above component centre).
  2. Build obstacle list: all pad AABBs, mounting holes, board edges, propeller cutouts.
  3. For each label, check if default position is free. If not, try candidate
     positions in a spiral pattern (8 directions × increasing distances) until
     a collision-free spot is found.
  4. Return a dict mapping ref → (local_dx, local_dy) offsets relative to
     the footprint centre (in footprint-local coordinates, pre-rotation).

The returned offsets replace the default (0, -hh - 1.0) in the footprint serializer.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from cadquery_framework.kicad.component_library import BoardDefinition, Placement
from cadquery_framework.kicad.jlcpcb_constraints import (
    JLCPCB_SILK_TO_PAD_MM,
    JLCPCB_COPPER_TO_EDGE_MM,
    SILK_MICRO_SIZE_MM,
)


# ── Geometry helpers ────────────────────────────────────────────────────────

def _aabb_overlap(a: tuple[float, float, float, float],
                  b: tuple[float, float, float, float]) -> bool:
    return a[2] > b[0] and a[0] < b[2] and a[3] > b[1] and a[1] < b[3]


def _aabb_circle_overlap(aabb: tuple[float, float, float, float],
                         cx: float, cy: float, r: float) -> bool:
    closest_x = max(aabb[0], min(cx, aabb[2]))
    closest_y = max(aabb[1], min(cy, aabb[3]))
    return math.hypot(closest_x - cx, closest_y - cy) < r


def _point_in_cutout(x: float, y: float, half: float,
                     cutouts: list[tuple[float, float, float]]) -> bool:
    """Check if a point (board coords, top-left origin) is in a propeller cutout zone.

    A point is in the cutout if:
      1. It is outside the board rectangle (beyond any edge), OR
      2. It is inside a propeller disc AND beyond a board corner
         (i.e., the propeller arc has cut away the PCB material there).
    """
    # Convert to centre-origin for propeller geometry
    cx = x - half
    cy = y - half
    for mx, my, pr in cutouts:
        dist = math.hypot(cx - mx, cy - my)
        if dist < pr:
            # Inside propeller disc — check if the board corner is cut away here.
            # The cutout removes material OUTSIDE the arc (toward the corner).
            # Point is in cutout if it's closer to the corner than the arc.
            # Simple check: point is beyond both adjacent edges toward this corner.
            corner_x = half if mx > 0 else -half
            corner_y = half if my > 0 else -half
            # Is the point on the corner side of the motor?
            if ((cx - mx) * (corner_x - mx) > 0 or abs(cx - mx) < 1.0) and \
               ((cy - my) * (corner_y - my) > 0 or abs(cy - my) < 1.0):
                return True
    return False


def _aabb_in_cutout(aabb: tuple[float, float, float, float], half: float,
                    cutouts: list[tuple[float, float, float]]) -> bool:
    """Check if ANY corner of the AABB is in a propeller cutout zone."""
    x1, y1, x2, y2 = aabb
    for x, y in [(x1, y1), (x2, y1), (x1, y2), (x2, y2),
                 ((x1 + x2) / 2, (y1 + y2) / 2)]:
        if _point_in_cutout(x, y, half, cutouts):
            return True
    return False


def _text_aabb(bx: float, by: float, text: str, height: float,
               rot_deg: float = 0.0) -> tuple[float, float, float, float]:
    """Compute AABB for text centred at (bx, by) in board coordinates."""
    char_w = 0.6 * height
    hw = len(text) * char_w / 2
    hh = height / 2
    rad = math.radians(rot_deg)
    cos_a = abs(math.cos(rad))
    sin_a = abs(math.sin(rad))
    rot_hw = hw * cos_a + hh * sin_a
    rot_hh = hw * sin_a + hh * cos_a
    return (bx - rot_hw, by - rot_hh, bx + rot_hw, by + rot_hh)


def _local_to_board(lx: float, ly: float, px: float, py: float,
                    rot_deg: float) -> tuple[float, float]:
    """Transform footprint-local (lx, ly) to board coordinates given placement."""
    rad = math.radians(rot_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    bx = px + lx * cos_a - ly * sin_a
    by = py + lx * sin_a + ly * cos_a
    return bx, by


# ── Obstacle building ──────────────────────────────────────────────────────

@dataclass
class _Obstacle:
    """An axis-aligned bounding box that silk text must not overlap."""
    aabb: tuple[float, float, float, float]


def _build_pad_obstacles(board: BoardDefinition) -> list[_Obstacle]:
    """Build AABB obstacles from all pads on the board (with clearance)."""
    obstacles = []
    clearance = JLCPCB_SILK_TO_PAD_MM
    for p in board.placements:
        rad = math.radians(p.rotation)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        for pad in p.component.pads:
            pad_bx = p.x + pad.x * cos_a - pad.y * sin_a
            pad_by = p.y + pad.x * sin_a + pad.y * cos_a
            hw = pad.width / 2 + clearance
            hh = pad.height / 2 + clearance
            obstacles.append(_Obstacle((pad_bx - hw, pad_by - hh,
                                        pad_bx + hw, pad_by + hh)))
    return obstacles


def _build_hole_obstacles(board: BoardDefinition) -> list[tuple[float, float, float]]:
    """Return (cx, cy, radius_with_clearance) for each mounting hole."""
    return [(hx, hy, hd / 2 + JLCPCB_SILK_TO_PAD_MM)
            for hx, hy, hd in board.mounting_holes]


def _build_propeller_cutouts(board_size: float) -> list[tuple[float, float, float]]:
    """Build propeller cutout circles in centre-origin coordinates.

    Returns list of (mx, my, prop_radius) for each motor.
    """
    dims_path = Path(__file__).resolve().parents[3] / "drone_design" / "drone_model" / "dimensions.json"
    if not dims_path.exists():
        return []
    dims = json.loads(dims_path.read_text())
    motor_r = dims["arms"]["motor_to_motor_diagonal"] / 2
    prop_r = (dims["propeller"]["diameter"] / 2
              + dims.get("motor_riser", {}).get("prop_clearance_margin", 3.0))
    arm_angles = dims["arms"]["arm_angles_deg"]

    cutouts = []
    for angle_deg in arm_angles:
        rad = math.radians(angle_deg)
        mx = motor_r * math.cos(rad)
        my = motor_r * math.sin(rad)
        cutouts.append((mx, my, prop_r))
    return cutouts


# ── Candidate generation ───────────────────────────────────────────────────

# 8 directions: above, below, left, right, and 4 diagonals
_DIRECTIONS = [
    (0, -1),   # above (default)
    (0, 1),    # below
    (-1, 0),   # left
    (1, 0),    # right
    (-1, -1),  # top-left
    (1, -1),   # top-right
    (-1, 1),   # bottom-left
    (1, 1),    # bottom-right
]

# Distances to try (mm from courtyard edge)
_DISTANCES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]


def _candidate_offsets(courtyard_w: float, courtyard_h: float,
                       ) -> list[tuple[float, float]]:
    """Generate candidate (local_dx, local_dy) offsets for silk label placement."""
    candidates = []
    hw = courtyard_w / 2
    hh = courtyard_h / 2
    for dist in _DISTANCES:
        for dx_dir, dy_dir in _DIRECTIONS:
            lx = dx_dir * (hw + dist) if dx_dir != 0 else 0.0
            ly = dy_dir * (hh + dist) if dy_dir != 0 else 0.0
            candidates.append((lx, ly))
    return candidates


# ── Main repositioner ──────────────────────────────────────────────────────

def reposition_silk_labels(board: BoardDefinition) -> dict[str, tuple[float, float]]:
    """Find collision-free silk label positions for all components.

    Returns dict mapping ref → (local_dx, local_dy) in footprint-local coordinates.
    These replace the default (0, -courtyard_h/2 - 1.0) offset in the footprint
    serializer's fp_text reference line.
    """
    pad_obstacles = _build_pad_obstacles(board)
    hole_obstacles = _build_hole_obstacles(board)
    prop_cutouts = _build_propeller_cutouts(board.width)
    edge_margin = JLCPCB_COPPER_TO_EDGE_MM
    bw = board.width
    bh = board.height
    half = bw / 2  # for centre-origin conversion

    # Board-level text obstacles (title labels at fixed positions)
    board_label_aabbs = [
        _text_aabb(55.0, 50.5, "BOARD_TITLE_1", 1.5),
        _text_aabb(55.0, 46.5, "BOARD_TITLE_2", 1.5),
    ]

    # Already-placed silk label AABBs (greedy: earlier placements are fixed)
    placed_silk: list[tuple[str, tuple[float, float, float, float]]] = []
    for aabb in board_label_aabbs:
        placed_silk.append(("_board_label_", aabb))

    offsets: dict[str, tuple[float, float]] = {}

    for placement in board.placements:
        comp = placement.component
        candidates = _candidate_offsets(comp.courtyard_w, comp.courtyard_h)
        ref = placement.ref
        best_offset = None

        for lx, ly in candidates:
            # Transform to board coordinates
            bx, by = _local_to_board(lx, ly, placement.x, placement.y,
                                     placement.rotation)
            # Compute text AABB in board coords
            silk_aabb = _text_aabb(bx, by, ref, SILK_MICRO_SIZE_MM,
                                  placement.rotation)

            # Check board edges
            if (silk_aabb[0] < edge_margin or
                silk_aabb[2] > bw - edge_margin or
                silk_aabb[1] < edge_margin or
                silk_aabb[3] > bh - edge_margin):
                continue

            # Check propeller cutout zones (no PCB material there)
            if prop_cutouts and _aabb_in_cutout(silk_aabb, half, prop_cutouts):
                continue

            # Check pad obstacles
            pad_hit = False
            for obs in pad_obstacles:
                if _aabb_overlap(silk_aabb, obs.aabb):
                    pad_hit = True
                    break
            if pad_hit:
                continue

            # Check hole obstacles
            hole_hit = False
            for hx, hy, hr in hole_obstacles:
                if _aabb_circle_overlap(silk_aabb, hx, hy, hr):
                    hole_hit = True
                    break
            if hole_hit:
                continue

            # Check already-placed silk labels
            silk_hit = False
            for _, other_aabb in placed_silk:
                if _aabb_overlap(silk_aabb, other_aabb):
                    silk_hit = True
                    break
            if silk_hit:
                continue

            # Found a valid position
            best_offset = (lx, ly)
            placed_silk.append((ref, silk_aabb))
            break

        if best_offset is None:
            # Fallback: use default position (above, distance 1.0mm from courtyard)
            default_ly = -(comp.courtyard_h / 2 + 1.0)
            best_offset = (0.0, default_ly)
            bx, by = _local_to_board(0.0, default_ly, placement.x,
                                     placement.y, placement.rotation)
            silk_aabb = _text_aabb(bx, by, ref, SILK_MICRO_SIZE_MM,
                                  placement.rotation)
            placed_silk.append((ref, silk_aabb))

        offsets[ref] = best_offset

    return offsets
