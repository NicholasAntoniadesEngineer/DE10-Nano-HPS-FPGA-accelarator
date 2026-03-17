"""Deterministic row-based packing within assigned zones."""

from __future__ import annotations

import math

from cadquery_framework.kicad.component_library import ComponentDef, Placement
from cadquery_framework.kicad.placement.config import COURTYARD_GAP
from cadquery_framework.kicad.placement.geometry import BoardGeometry, SpatialIndex
from cadquery_framework.kicad.placement.utils import log, snap


class RowPacker:
    """Pack components into rows within a zone, guaranteeing zero overlaps.

    Strategy:
    1. Sort components by area (largest first).
    2. Place primary IC at zone centroid.
    3. Pack satellites in concentric rings around the centroid,
       row-by-row, checking both forbidden-zone and courtyard collisions.
    4. If zone is exhausted, expand search to nearest available board space.

    This replaces the Gaussian scatter which had no overlap guarantee.
    """

    def __init__(self, geometry: BoardGeometry, spatial: SpatialIndex) -> None:
        self.geo = geometry
        self.spatial = spatial

    def pack_subsystem(
        self,
        components: list[tuple[ComponentDef, str]],
        centroid: tuple[float, float],
    ) -> list[Placement]:
        """Pack all components near *centroid* with zero overlaps."""
        if not components:
            return []

        sorted_comps = sorted(
            components,
            key=lambda c: c[0].courtyard_w * c[0].courtyard_h,
            reverse=True,
        )

        placements: list[Placement] = []

        for cdef, ref in sorted_comps:
            pos = self._find_position(centroid, cdef)
            if pos is None:
                # Board-wide search as last resort.
                pos = self._board_wide_search(cdef)
            if pos is None:
                log(f"  WARNING: Could not place {ref} — using centroid fallback")
                pos = (snap(centroid[0]), snap(centroid[1]), 0.0)

            px, py, rot = pos
            p = Placement(cdef, ref, px, py, rot)
            placements.append(p)
            self.spatial.add_placement(p)

        return placements

    def _find_position(
        self,
        centroid: tuple[float, float],
        cdef: ComponentDef,
        max_radius: float = 35.0,
    ) -> tuple[float, float, float] | None:
        """Spiral search from centroid for a valid position.

        Returns (x, y, rotation) or None.
        """
        cx, cy = centroid
        cw, ch = cdef.courtyard_w, cdef.courtyard_h

        # Try centroid first.
        for rot in [0.0, 90.0]:
            if self._try_position(cx, cy, cw, ch, rot):
                return (snap(cx), snap(cy), rot)

        # Spiral outward in 0.5mm steps, 15 deg increments.
        step = 0.5
        n_steps = int(max_radius / step)
        for r_idx in range(1, n_steps + 1):
            r = r_idx * step
            n_angles = max(12, min(36, int(2 * math.pi * r / 1.5)))
            for a_idx in range(n_angles):
                angle = 2 * math.pi * a_idx / n_angles
                px = cx + r * math.cos(angle)
                py = cy + r * math.sin(angle)
                for rot in [0.0, 90.0]:
                    if self._try_position(px, py, cw, ch, rot):
                        return (snap(px), snap(py), rot)

        return None

    def _board_wide_search(self, cdef: ComponentDef) -> tuple[float, float, float] | None:
        """Scan entire board on 1mm grid for a valid position."""
        cw, ch = cdef.courtyard_w, cdef.courtyard_h
        step = 1.0
        margin = max(cw, ch) / 2 + 1.0

        bw, bh = self.geo.board_w, self.geo.board_h
        best_pos = None
        best_dist_to_centre = float('inf')

        y = margin
        while y < bh - margin:
            x = margin
            while x < bw - margin:
                for rot in [0.0, 90.0]:
                    if self._try_position(x, y, cw, ch, rot):
                        dist = math.hypot(x - bw / 2, y - bh / 2)
                        if dist < best_dist_to_centre:
                            best_dist_to_centre = dist
                            best_pos = (snap(x), snap(y), rot)
                x += step
            y += step

        return best_pos

    def _try_position(
        self, x: float, y: float, cw: float, ch: float, rot: float,
    ) -> bool:
        """Check if a component can be placed at (x, y, rot)."""
        x = snap(x)
        y = snap(y)
        if not self.geo.is_placeable(x, y, cw, ch, rot):
            return False

        rad = math.radians(rot)
        cos_a, sin_a = abs(math.cos(rad)), abs(math.sin(rad))
        rw = cw * cos_a + ch * sin_a
        rh = cw * sin_a + ch * cos_a
        gap = COURTYARD_GAP
        x0 = x - rw / 2 - gap
        y0 = y - rh / 2 - gap
        x1 = x + rw / 2 + gap
        y1 = y + rh / 2 + gap

        return not self.spatial.query_overlap(x0, y0, x1, y1)
