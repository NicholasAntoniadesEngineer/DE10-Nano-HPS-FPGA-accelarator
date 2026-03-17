"""Automatic silk label repositioner — finds collision-free positions for all reference labels.

Algorithm:
  1. Compute default silk positions (courtyard_h/2 + 1.0mm above component centre).
  2. Build obstacle list: all pad AABBs, mounting holes, board edges.
  3. For each label, check if default position is free. If not, try candidate
     positions in a spiral pattern (8 directions × increasing distances) until
     a collision-free spot is found.
  4. Return a dict mapping ref → (local_dx, local_dy) offsets relative to
     the footprint centre (in footprint-local coordinates, pre-rotation).

The returned offsets replace the default (0, -hh - 1.0) in the footprint serializer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

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
    """Generate candidate (local_dx, local_dy) offsets for silk label placement.

    Returns offsets in footprint-local coordinates (pre-rotation).
    The first candidate is the default position (above).
    """
    candidates = []
    hw = courtyard_w / 2
    hh = courtyard_h / 2
    for dist in _DISTANCES:
        for dx_dir, dy_dir in _DIRECTIONS:
            # Offset from component centre in local coords
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
    edge_margin = JLCPCB_COPPER_TO_EDGE_MM
    bw = board.width
    bh = board.height

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
