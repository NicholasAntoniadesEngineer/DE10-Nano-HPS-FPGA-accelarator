"""Board geometry and spatial indexing for the placement optimizer."""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

from cadquery_framework.kicad.component_library import Placement
from cadquery_framework.kicad.placement.config import EZ_OFFSET_X, EZ_OFFSET_Y

# ---------------------------------------------------------------------------
# Shapely availability — graceful fallback
# ---------------------------------------------------------------------------

try:
    from shapely.geometry import Point as _ShapelyPoint
    from shapely.geometry import Polygon as _ShapelyPolygon
    from shapely.geometry import box as _shapely_box
    from shapely.ops import unary_union as _unary_union

    _HAS_SHAPELY = True
except ImportError:
    _HAS_SHAPELY = False


def has_shapely() -> bool:
    """Return True if Shapely is available at runtime."""
    return _HAS_SHAPELY


def shapely_box(x0: float, y0: float, x1: float, y1: float):  # noqa: ANN201
    """Thin wrapper so other modules can build Shapely boxes without importing."""
    return _shapely_box(x0, y0, x1, y1)


def shapely_unary_union(geoms):  # noqa: ANN001, ANN201
    """Thin wrapper for ``shapely.ops.unary_union``."""
    return _unary_union(geoms)


# ===================================================================
# BoardGeometry
# ===================================================================

class BoardGeometry:
    """Computes usable PCB area as a polygon with holes."""

    def __init__(self, board_w: float, board_h: float, dims_path: Path) -> None:
        self.board_w = board_w
        self.board_h = board_h

        with open(dims_path) as fh:
            dims = json.load(fh)

        plate_size = dims["frame"]["plate_size"]
        half = plate_size / 2.0

        hs_w = dims["de10_nano"]["heatsink_width"] + 4.0
        hs_h = dims["de10_nano"]["heatsink_length"] + 4.0
        cx, cy = half, half
        self._hs_bounds = (cx - hs_w / 2, cy - hs_h / 2,
                           cx + hs_w / 2, cy + hs_h / 2)

        arm_angles: list[float] = dims["arms"]["arm_angles_deg"]
        motor_r = dims["arms"]["motor_to_motor_diagonal"] / 2.0
        prop_r = dims["propeller"]["diameter"] / 2.0 + dims["motor_riser"]["prop_clearance_margin"]

        self.motors: list[tuple[float, float, float]] = []
        for angle_deg in arm_angles:
            rad = math.radians(angle_deg)
            mx = motor_r * math.cos(rad) + half
            my = -motor_r * math.sin(rad) + half
            self.motors.append((mx, my, prop_r))

        inset = dims["de10_nano"]["mounting_hole_inset"]
        de10_w = dims["de10_nano"]["board_width"]
        de10_l = dims["de10_nano"]["board_length"]
        ox, oy = EZ_OFFSET_X, EZ_OFFSET_Y
        self.mounting_holes: list[tuple[float, float, float]] = [
            (ox + inset, oy + inset, 3.2),
            (ox + de10_w - inset, oy + inset, 3.2),
            (ox + inset, oy + de10_l - inset, 3.2),
            (ox + de10_w - inset, oy + de10_l - inset, 3.2),
        ]

        if _HAS_SHAPELY:
            self._build_shapely(board_w, board_h, cx, cy, hs_w, hs_h, prop_r)
        else:
            self._build_simple(board_w, board_h, cx, cy, hs_w, hs_h)

    def _build_shapely(
        self, bw: float, bh: float, cx: float, cy: float,
        hs_w: float, hs_h: float, prop_r: float,
    ) -> None:
        board_rect = _shapely_box(0, 0, bw, bh)
        heatsink = _shapely_box(cx - hs_w / 2, cy - hs_h / 2,
                                cx + hs_w / 2, cy + hs_h / 2)
        prop_cutouts = []
        for mx, my, pr in self.motors:
            circle = _ShapelyPoint(mx, my).buffer(pr, resolution=64)
            prop_cutouts.append(circle.intersection(board_rect))
        mounting_keepouts = [
            _ShapelyPoint(x, y).buffer(3.0) for x, y, _d in self.mounting_holes
        ]
        forbidden = _unary_union([heatsink] + prop_cutouts + mounting_keepouts)
        self.usable_area: _ShapelyPolygon = board_rect.difference(forbidden)
        self.forbidden = forbidden
        self._use_shapely = True

    def _build_simple(
        self, bw: float, bh: float, cx: float, cy: float,
        hs_w: float, hs_h: float,
    ) -> None:
        self._use_shapely = False
        self._board_bounds = (0.0, 0.0, bw, bh)

    def is_placeable(
        self, x: float, y: float, cw: float, ch: float, rotation: float = 0.0,
    ) -> bool:
        """Return True if the courtyard box fits entirely within usable area."""
        rad = math.radians(rotation)
        cos_a, sin_a = abs(math.cos(rad)), abs(math.sin(rad))
        rw = cw * cos_a + ch * sin_a
        rh = cw * sin_a + ch * cos_a
        x0, y0 = x - rw / 2, y - rh / 2
        x1, y1 = x + rw / 2, y + rh / 2

        if self._use_shapely:
            court_box = _shapely_box(x0, y0, x1, y1)
            return self.usable_area.contains(court_box)

        bb = self._board_bounds
        if x0 < bb[0] or y0 < bb[1] or x1 > bb[2] or y1 > bb[3]:
            return False
        hs = self._hs_bounds
        if not (x1 < hs[0] or x0 > hs[2] or y1 < hs[1] or y0 > hs[3]):
            return False
        return True

    def is_inside_board(self, x: float, y: float, cw: float, ch: float,
                        rotation: float = 0.0) -> bool:
        """Return True if courtyard is within the board rectangle (ignoring cutouts)."""
        rad = math.radians(rotation)
        cos_a, sin_a = abs(math.cos(rad)), abs(math.sin(rad))
        rw = cw * cos_a + ch * sin_a
        rh = cw * sin_a + ch * cos_a
        return (x - rw / 2 >= 0.5 and y - rh / 2 >= 0.5
                and x + rw / 2 <= self.board_w - 0.5
                and y + rh / 2 <= self.board_h - 0.5)

    def distance_to_forbidden(self, x: float, y: float) -> float:
        """Signed distance to forbidden boundary (negative = inside forbidden)."""
        if self._use_shapely:
            pt = _ShapelyPoint(x, y)
            d = pt.distance(self.forbidden.boundary)
            if self.forbidden.contains(pt):
                return -d
            return d
        hs = self._hs_bounds
        dx = max(hs[0] - x, 0, x - hs[2])
        dy = max(hs[1] - y, 0, y - hs[3])
        if dx == 0 and dy == 0:
            return -min(x - hs[0], hs[2] - x, y - hs[1], hs[3] - y)
        return math.hypot(dx, dy)

    def nearest_usable_point(self, x: float, y: float) -> tuple[float, float]:
        """Return the nearest point in usable area to (x, y)."""
        if self._use_shapely and not self.usable_area.contains(_ShapelyPoint(x, y)):
            pt = _ShapelyPoint(x, y)
            nearest = self.usable_area.exterior.interpolate(
                self.usable_area.exterior.project(pt)
            )
            return (nearest.x, nearest.y)
        return (x, y)

    def random_point_in_usable(self) -> tuple[float, float]:
        """Return a random (x, y) inside the usable area (rejection sampling)."""
        if self._use_shapely:
            minx, miny, maxx, maxy = self.usable_area.bounds
        else:
            minx, miny, maxx, maxy = 0.0, 0.0, self.board_w, self.board_h

        for _ in range(2000):
            px = random.uniform(minx, maxx)
            py = random.uniform(miny, maxy)
            if self._use_shapely:
                if self.usable_area.contains(_ShapelyPoint(px, py)):
                    return (px, py)
            else:
                if self.is_placeable(px, py, 0.1, 0.1):
                    return (px, py)
        return (self.board_w * 0.25, self.board_h * 0.25)

    def get_electronics_zone_offset(self) -> tuple[float, float]:
        return (EZ_OFFSET_X, EZ_OFFSET_Y)

    def courtyard_overlap_with_forbidden(
        self, x: float, y: float, cw: float, ch: float, rotation: float = 0.0,
    ) -> float:
        """Return overlap area between courtyard and forbidden zones."""
        if not self._use_shapely:
            return 0.0 if self.is_placeable(x, y, cw, ch, rotation) else cw * ch
        rad = math.radians(rotation)
        cos_a, sin_a = abs(math.cos(rad)), abs(math.sin(rad))
        rw = cw * cos_a + ch * sin_a
        rh = cw * sin_a + ch * cos_a
        court = _shapely_box(x - rw / 2, y - rh / 2, x + rw / 2, y + rh / 2)
        inter = court.intersection(self.forbidden)
        return inter.area


# ===================================================================
# Spatial index for fast overlap checking
# ===================================================================

class SpatialIndex:
    """Simple grid-based spatial index for AABB overlap queries.

    Divides the board into cells and maps placements to cells for O(1)
    average-case overlap checking instead of O(n).
    """

    def __init__(self, board_w: float, board_h: float, cell_size: float = 10.0):
        self.cell_size = cell_size
        self.cols = max(1, int(math.ceil(board_w / cell_size)))
        self.rows = max(1, int(math.ceil(board_h / cell_size)))
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.bounds: list[tuple[float, float, float, float]] = []
        self.refs: list[str] = []

    def add(self, idx: int, ref: str, x0: float, y0: float, x1: float, y1: float) -> None:
        while idx >= len(self.bounds):
            self.bounds.append((0, 0, 0, 0))
            self.refs.append("")
        self.bounds[idx] = (x0, y0, x1, y1)
        self.refs[idx] = ref
        for ci in range(max(0, int(x0 / self.cell_size)),
                        min(self.cols, int(x1 / self.cell_size) + 1)):
            for cj in range(max(0, int(y0 / self.cell_size)),
                            min(self.rows, int(y1 / self.cell_size) + 1)):
                self.cells[(ci, cj)].append(idx)

    def add_placement(self, p: Placement) -> int:
        idx = len(self.bounds)
        b = p.courtyard_bounds
        self.add(idx, p.ref, b[0], b[1], b[2], b[3])
        return idx

    def query_overlap(self, x0: float, y0: float, x1: float, y1: float,
                      exclude_idx: int = -1) -> bool:
        """Return True if any existing AABB overlaps the query box."""
        for ci in range(max(0, int(x0 / self.cell_size)),
                        min(self.cols, int(x1 / self.cell_size) + 1)):
            for cj in range(max(0, int(y0 / self.cell_size)),
                            min(self.rows, int(y1 / self.cell_size) + 1)):
                for idx in self.cells.get((ci, cj), []):
                    if idx == exclude_idx:
                        continue
                    b = self.bounds[idx]
                    if x0 < b[2] and x1 > b[0] and y0 < b[3] and y1 > b[1]:
                        return True
        return False

    def rebuild(self, placements: list[Placement]) -> None:
        """Rebuild index from scratch."""
        self.cells.clear()
        self.bounds.clear()
        self.refs.clear()
        for p in placements:
            self.add_placement(p)
