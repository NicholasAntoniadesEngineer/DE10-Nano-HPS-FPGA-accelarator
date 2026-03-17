"""Pad-level overlap detection using Oriented Bounding Box (OBB) collision.

Goes beyond courtyard-level AABB checks by computing the actual board-space
position and rotation of every pad on every placed component, then testing
pairwise OBB overlap using the Separating Axis Theorem (SAT).

This catches real manufacturing defects that courtyard checks miss:
  - Rotated component pads intruding into a neighbour's footprint
  - Small-pitch IC pads overlapping adjacent passives
  - Connector pads overlapping nearby decoupling caps

Performance: O(n²) pairwise between components, but with spatial-hash
pre-filtering to skip distant pairs.  Typical daughter-board (~150
components) runs in <50ms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from cadquery_framework.kicad.component_library import (
    BoardDefinition,
    PadGeometry,
    Placement,
)


# ---------------------------------------------------------------------------
# OBB representation + SAT overlap test
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OBB2D:
    """Oriented Bounding Box in 2D — centre + half-extents + rotation."""

    cx: float       # centre X (board coords, mm)
    cy: float       # centre Y
    hw: float       # half-width  (along local X before rotation)
    hh: float       # half-height (along local Y before rotation)
    angle_rad: float  # rotation in radians (CCW from board X axis)

    @property
    def corners(self) -> list[tuple[float, float]]:
        """Return the four corners of this OBB in board coordinates."""
        cos_a = math.cos(self.angle_rad)
        sin_a = math.sin(self.angle_rad)
        dx = [(-self.hw, -self.hh), (self.hw, -self.hh),
              (self.hw, self.hh), (-self.hw, self.hh)]
        return [
            (self.cx + lx * cos_a - ly * sin_a,
             self.cy + lx * sin_a + ly * cos_a)
            for lx, ly in dx
        ]

    @property
    def axes(self) -> list[tuple[float, float]]:
        """Return the two separating axes (unit normals of the OBB edges)."""
        cos_a = math.cos(self.angle_rad)
        sin_a = math.sin(self.angle_rad)
        return [(cos_a, sin_a), (-sin_a, cos_a)]


def _project(corners: list[tuple[float, float]],
             axis: tuple[float, float]) -> tuple[float, float]:
    """Project corners onto axis, return (min, max) scalar projections."""
    dots = [c[0] * axis[0] + c[1] * axis[1] for c in corners]
    return min(dots), max(dots)


def obb_overlap(a: OBB2D, b: OBB2D) -> float:
    """Return overlap depth (mm) between two OBBs, or 0 if no overlap.

    Uses the Separating Axis Theorem: test all 4 potential separating
    axes (2 from each OBB).  If all axes show overlap, the boxes collide.
    The minimum overlap across all axes is the penetration depth.
    """
    a_corners = a.corners
    b_corners = b.corners
    min_overlap = float("inf")

    for axis in a.axes + b.axes:
        a_min, a_max = _project(a_corners, axis)
        b_min, b_max = _project(b_corners, axis)
        overlap = min(a_max, b_max) - max(a_min, b_min)
        if overlap <= 0:
            return 0.0  # separating axis found — no collision
        min_overlap = min(min_overlap, overlap)

    return min_overlap


# ---------------------------------------------------------------------------
# Pad → OBB conversion (respecting component rotation)
# ---------------------------------------------------------------------------

def pad_to_obb(pad: PadGeometry, placement: Placement) -> OBB2D:
    """Convert a pad definition + its component's placement to a board-space OBB.

    The pad's (x, y) is relative to the component centre.  The component
    is placed at (placement.x, placement.y) with rotation placement.rotation°.
    The resulting OBB accounts for both the component rotation and any
    inherent pad asymmetry.
    """
    comp_rad = math.radians(placement.rotation)
    cos_c = math.cos(comp_rad)
    sin_c = math.sin(comp_rad)

    # Rotate pad centre by component rotation, then translate to board coords
    board_x = placement.x + pad.x * cos_c - pad.y * sin_c
    board_y = placement.y + pad.x * sin_c + pad.y * cos_c

    # Pad orientation = component rotation (pads align with component)
    return OBB2D(
        cx=board_x,
        cy=board_y,
        hw=pad.width / 2,
        hh=pad.height / 2,
        angle_rad=comp_rad,
    )


# ---------------------------------------------------------------------------
# Spatial hash for broad-phase culling
# ---------------------------------------------------------------------------

def _cell_key(x: float, y: float, cell_size: float) -> tuple[int, int]:
    return (int(math.floor(x / cell_size)), int(math.floor(y / cell_size)))


def _obb_cells(obb: OBB2D, cell_size: float) -> set[tuple[int, int]]:
    """Return all grid cells that this OBB touches."""
    corners = obb.corners
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    cells = set()
    ix = int(math.floor(x_min / cell_size))
    while ix * cell_size <= x_max:
        iy = int(math.floor(y_min / cell_size))
        while iy * cell_size <= y_max:
            cells.add((ix, iy))
            iy += 1
        ix += 1
    return cells


# ---------------------------------------------------------------------------
# PadOverlapResult
# ---------------------------------------------------------------------------

@dataclass
class PadOverlap:
    """One detected pad-to-pad overlap."""
    ref_a: str
    pad_a: str
    ref_b: str
    pad_b: str
    overlap_mm: float

    def __str__(self) -> str:
        return (
            f"{self.ref_a}:pad{self.pad_a} ↔ {self.ref_b}:pad{self.pad_b} "
            f"overlap {self.overlap_mm:.3f}mm"
        )


@dataclass
class PadOverlapResult:
    overlaps: list[PadOverlap]
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def report(self) -> str:
        lines = []
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        for e in self.errors:
            lines.append(f"  ERROR:   {e}")
        if self.ok:
            lines.append(
                f"  PASS — {len(self.warnings)} warning(s), 0 pad overlaps"
            )
        else:
            lines.append(
                f"  FAIL — {len(self.overlaps)} pad overlap(s), "
                f"{len(self.errors)} error(s)"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------------------------

# Minimum overlap to report (ignores sub-manufacturing-tolerance touches)
_MIN_OVERLAP_MM = 0.02  # 20µm — below JLCPCB registration tolerance

# Pad clearance margin — pads should have at least this gap between them
_PAD_CLEARANCE_MM = 0.075  # 75µm — half of JLCPCB 0.1mm minimum clearance


def validate_pad_overlaps(
    board: BoardDefinition,
    clearance_mm: float = _PAD_CLEARANCE_MM,
    ignore_same_net: bool = True,
) -> PadOverlapResult:
    """Check every pad pair on the board for geometric overlap.

    Args:
        board: Complete board definition with placements.
        clearance_mm: Minimum required gap between pads of different nets.
            Pads closer than this trigger a warning; actual overlaps are errors.
        ignore_same_net: If True, pads connected to the same net are allowed
            to overlap (they'll be joined by copper pour anyway).

    Returns:
        PadOverlapResult with all detected overlaps.
    """
    errors: list[str] = []
    warnings: list[str] = []
    overlaps: list[PadOverlap] = []

    # Build net membership lookup: (ref, pad_number) → net_name
    pad_net: dict[tuple[str, str], str] = {}
    if ignore_same_net:
        for net_name, connections in board.nets.items():
            for conn in connections:
                pad_net[(conn.ref, conn.pin_number)] = net_name

    # Pre-compute all pad OBBs with spatial hashing
    CELL_SIZE = 5.0  # mm — coarse grid for broad-phase
    grid: dict[tuple[int, int], list[tuple[str, str, OBB2D]]] = {}

    for placement in board.placements:
        for pad in placement.component.pads:
            obb = pad_to_obb(pad, placement)
            # Expand OBB by clearance for the spatial hash
            expanded = OBB2D(
                obb.cx, obb.cy,
                obb.hw + clearance_mm, obb.hh + clearance_mm,
                obb.angle_rad,
            )
            cells = _obb_cells(expanded, CELL_SIZE)
            entry = (placement.ref, pad.number, obb)
            for cell in cells:
                grid.setdefault(cell, []).append(entry)

    # Narrow-phase: test pairs in the same grid cells
    tested: set[tuple[str, str, str, str]] = set()

    for cell_entries in grid.values():
        for i, (ref_a, pad_a, obb_a) in enumerate(cell_entries):
            for ref_b, pad_b, obb_b in cell_entries[i + 1:]:
                if ref_a == ref_b:
                    continue  # same component — pads are inherently close

                # Canonical pair key to avoid duplicate checks
                pair_key = (
                    (min(ref_a, ref_b), pad_a if ref_a < ref_b else pad_b,
                     max(ref_a, ref_b), pad_b if ref_a < ref_b else pad_a)
                )
                if pair_key in tested:
                    continue
                tested.add(pair_key)

                # Same-net pads can touch/overlap (copper pour merges them)
                if ignore_same_net:
                    net_a = pad_net.get((ref_a, pad_a), "")
                    net_b = pad_net.get((ref_b, pad_b), "")
                    if net_a and net_b and net_a == net_b:
                        continue

                # Test actual pad overlap
                depth = obb_overlap(obb_a, obb_b)
                if depth > _MIN_OVERLAP_MM:
                    overlap = PadOverlap(ref_a, pad_a, ref_b, pad_b, depth)
                    overlaps.append(overlap)
                    errors.append(str(overlap))
                else:
                    # Test clearance violation (expand pads by margin)
                    expanded_a = OBB2D(
                        obb_a.cx, obb_a.cy,
                        obb_a.hw + clearance_mm, obb_a.hh + clearance_mm,
                        obb_a.angle_rad,
                    )
                    expanded_b = OBB2D(
                        obb_b.cx, obb_b.cy,
                        obb_b.hw + clearance_mm, obb_b.hh + clearance_mm,
                        obb_b.angle_rad,
                    )
                    gap_depth = obb_overlap(expanded_a, expanded_b)
                    if gap_depth > _MIN_OVERLAP_MM:
                        warnings.append(
                            f"{ref_a}:pad{pad_a} ↔ {ref_b}:pad{pad_b} "
                            f"clearance < {clearance_mm}mm "
                            f"(gap violation: {gap_depth:.3f}mm)"
                        )

    return PadOverlapResult(overlaps=overlaps, errors=errors, warnings=warnings)
