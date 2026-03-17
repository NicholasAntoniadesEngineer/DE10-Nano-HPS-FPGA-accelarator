"""Physical courtyard and keep-out zone validation.

Checks:
  1. No component courtyard overlaps (2D AABB with margin).
  2. All components within board outline (with edge clearance).
  3. Through-hole components respect hole-to-edge clearance.
  4. Keep-out zone violations (e.g. antenna area).
  5. Mounting hole clearance zones.
  6. Heatsink/fan cutout zone — physical hole, no PCB material.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from cadquery_framework.kicad.component_library import BoardDefinition, KeepOutZone, Placement
from cadquery_framework.kicad.jlcpcb_constraints import (
    DRM_COURTYARD_CLEARANCE_MM,
    JLCPCB_COPPER_TO_EDGE_MM,
    JLCPCB_HOLE_TO_EDGE_MM,
    DRM_STANDOFF_CLEARANCE_MM,
)


@dataclass
class PhysicalResult:
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
            lines.append(f"  PASS — {len(self.warnings)} warning(s), 0 errors")
        else:
            lines.append(f"  FAIL — {len(self.warnings)} warning(s), {len(self.errors)} error(s)")
        return "\n".join(lines)


def _aabb_overlap(a: tuple[float, float, float, float],
                   b: tuple[float, float, float, float],
                   margin: float = 0.0) -> float:
    """Return overlap distance between two AABBs, or 0 if no overlap.

    Each AABB is (xmin, ymin, xmax, ymax).
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    # Expand A by margin
    ax1 -= margin
    ay1 -= margin
    ax2 += margin
    ay2 += margin
    # Compute overlap
    ox = min(ax2, bx2) - max(ax1, bx1)
    oy = min(ay2, by2) - max(ay1, by1)
    if ox > 0 and oy > 0:
        return min(ox, oy)
    return 0.0


def _point_in_rect(x: float, y: float,
                    rx: float, ry: float, rw: float, rh: float) -> bool:
    """Check if point (x,y) is inside rectangle (rx, ry, rw, rh) where
    (rx, ry) is top-left and (rw, rh) are width/height."""
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def validate_physical(board: BoardDefinition) -> PhysicalResult:
    """Run all physical validation checks."""
    errors: list[str] = []
    warnings: list[str] = []

    # Board outline as AABB (origin at top-left, so 0,0 to w,h)
    board_xmin = 0.0
    board_ymin = 0.0
    board_xmax = board.width
    board_ymax = board.height

    # ------------------------------------------------------------------
    # Check 1: Courtyard overlaps
    # ------------------------------------------------------------------
    placements = board.placements
    for i in range(len(placements)):
        a = placements[i]
        a_bounds = a.courtyard_bounds
        for j in range(i + 1, len(placements)):
            b = placements[j]
            b_bounds = b.courtyard_bounds
            overlap = _aabb_overlap(a_bounds, b_bounds, DRM_COURTYARD_CLEARANCE_MM)
            if overlap > 0:
                errors.append(
                    f"Courtyard overlap: {a.ref} and {b.ref} "
                    f"overlap by {overlap:.2f}mm "
                    f"(min clearance: {DRM_COURTYARD_CLEARANCE_MM}mm)"
                )

    # ------------------------------------------------------------------
    # Check 2: Components within board outline
    # ------------------------------------------------------------------
    for p in placements:
        bounds = p.courtyard_bounds
        # SMD: copper-to-edge clearance
        min_edge = JLCPCB_HOLE_TO_EDGE_MM if p.component.has_thru_holes else JLCPCB_COPPER_TO_EDGE_MM
        if bounds[0] < board_xmin + min_edge:
            errors.append(f"{p.ref}: left edge at {bounds[0]:.2f}mm, need ≥{min_edge}mm from board edge")
        if bounds[1] < board_ymin + min_edge:
            errors.append(f"{p.ref}: top edge at {bounds[1]:.2f}mm, need ≥{min_edge}mm from board edge")
        if bounds[2] > board_xmax - min_edge:
            errors.append(f"{p.ref}: right edge at {bounds[2]:.2f}mm, board width {board.width}mm")
        if bounds[3] > board_ymax - min_edge:
            errors.append(f"{p.ref}: bottom edge at {bounds[3]:.2f}mm, board height {board.height}mm")

    # ------------------------------------------------------------------
    # Check 3: Keep-out zone violations
    # ------------------------------------------------------------------
    for zone in board.keep_outs:
        zone_bounds = (zone.xmin, zone.ymin, zone.xmax, zone.ymax)
        for p in placements:
            if p.ref == zone.owner_ref:
                continue
            overlap = _aabb_overlap(p.courtyard_bounds, zone_bounds)
            if overlap > 0:
                errors.append(
                    f"{p.ref} violates keep-out zone '{zone.name}' "
                    f"(overlap: {overlap:.2f}mm)"
                )

    # ------------------------------------------------------------------
    # Check 4: Mounting hole clearance
    # ------------------------------------------------------------------
    # Components exempt from mounting-hole clearance (e.g. on opposite side).
    MOUNTING_HOLE_EXEMPT: set[str] = set()

    for mx, my, drill_d in board.mounting_holes:
        # Clearance zone around mounting hole
        clearance = DRM_STANDOFF_CLEARANCE_MM + drill_d / 2
        hole_bounds = (mx - clearance, my - clearance, mx + clearance, my + clearance)
        for p in placements:
            if p.ref in MOUNTING_HOLE_EXEMPT:
                continue
            overlap = _aabb_overlap(p.courtyard_bounds, hole_bounds)
            if overlap > 0:
                warnings.append(
                    f"{p.ref} is within {DRM_STANDOFF_CLEARANCE_MM}mm of "
                    f"mounting hole at ({mx:.1f}, {my:.1f})"
                )

    # ------------------------------------------------------------------
    # Check 5: Heatsink/fan cutout zone (physical hole in PCB)
    # ------------------------------------------------------------------
    # The DE10-Nano heatsink + fan assembly protrudes through the daughter
    # board.  A 44×44mm cutout (40mm heatsink + 4mm clearance) is centred
    # on the 110×110mm plate.  There is NO PCB material in this zone —
    # any component placed here will fall into empty space.
    cutout = _heatsink_cutout_zone(board.width, board.height)
    if cutout:
        cx_min, cy_min, cx_max, cy_max = cutout
        for p in placements:
            bounds = p.courtyard_bounds
            # Check if courtyard overlaps the cutout
            if (bounds[2] > cx_min and bounds[0] < cx_max and
                    bounds[3] > cy_min and bounds[1] < cy_max):
                errors.append(
                    f"{p.ref} at ({p.x:.1f}, {p.y:.1f}) is inside the "
                    f"heatsink/fan cutout zone "
                    f"[{cx_min:.0f},{cy_min:.0f}]-[{cx_max:.0f},{cy_max:.0f}] "
                    f"— no PCB material here"
                )

    # ------------------------------------------------------------------
    # Check 6: Propeller clearance cutout zones (no PCB material)
    # ------------------------------------------------------------------
    # At each motor position, the propeller disc clips the board corner.
    # Use AABB-circle intersection: clamp motor centre to the nearest
    # point on the component's courtyard bounding box, then check if
    # that clamped point is within prop_r of the motor.  This catches
    # components whose courtyard extends into the cutout even if the
    # component centre is outside.
    prop_motors = _propeller_motor_positions(board.width, board.height)
    for motor_bx, motor_by, prop_r, label in prop_motors:
        for p in placements:
            bounds = p.courtyard_bounds  # (xmin, ymin, xmax, ymax)
            closest_x = max(bounds[0], min(motor_bx, bounds[2]))
            closest_y = max(bounds[1], min(motor_by, bounds[3]))
            dist = math.sqrt((closest_x - motor_bx) ** 2 + (closest_y - motor_by) ** 2)
            if dist < prop_r:
                errors.append(
                    f"{p.ref} at ({p.x:.1f}, {p.y:.1f}) is inside the "
                    f"propeller cutout zone '{label}' "
                    f"(courtyard-to-motor: {dist:.1f}mm < prop radius {prop_r:.1f}mm) "
                    f"— no PCB material here"
                )

    return PhysicalResult(errors=errors, warnings=warnings)


def _propeller_motor_positions(
    board_w: float, board_h: float,
) -> list[tuple[float, float, float, str]]:
    """Return motor positions and prop radii for propeller cutout checks.

    Returns list of (motor_board_x, motor_board_y, prop_radius, label)
    in board coordinates (top-left origin).
    """
    try:
        dims_path = (
            Path(__file__).resolve().parents[3]
            / "drone_design" / "drone_model" / "dimensions.json"
        )
        dims = json.loads(dims_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    plate_size = dims.get("frame", {}).get("plate_size", 0)
    if abs(board_w - plate_size) > 0.5 or abs(board_h - plate_size) > 0.5:
        return []  # not the combined plate

    motor_r = dims["arms"]["motor_to_motor_diagonal"] / 2
    prop_r = dims["propeller"]["diameter"] / 2 + dims.get("motor_riser", {}).get("prop_clearance_margin", 3.0)
    arm_angles = dims["arms"]["arm_angles_deg"]
    half = plate_size / 2

    motors = []
    for angle_deg in arm_angles:
        rad = math.radians(angle_deg)
        # Motor centre in centre-origin, convert to top-left board coords
        # Note: CadQuery Y is up, board Y is down → negate Y
        mx_board = motor_r * math.cos(rad) + half
        my_board = -motor_r * math.sin(rad) + half
        motors.append((mx_board, my_board, prop_r, f"prop_{angle_deg}deg"))

    return motors


def _heatsink_cutout_zone(
    board_w: float, board_h: float,
) -> tuple[float, float, float, float] | None:
    """Return the heatsink cutout AABB in board coordinates, or None.

    Only applies to the combined 110×110mm top plate + daughter board.
    The cutout is 44×44mm centred on the board (40mm heatsink + 4mm margin).
    """
    try:
        dims_path = (
            Path(__file__).resolve().parents[3]
            / "drone_design" / "drone_model" / "dimensions.json"
        )
        dims = json.loads(dims_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    plate_size = dims.get("frame", {}).get("plate_size", 0)
    if abs(board_w - plate_size) > 0.5 or abs(board_h - plate_size) > 0.5:
        return None  # not the combined plate — skip

    hs_w = dims["de10_nano"]["heatsink_width"]   # 40mm
    hs_l = dims["de10_nano"]["heatsink_length"]   # 40mm
    margin = 2.0  # mm clearance per side for fan mounting

    cx, cy = board_w / 2, board_h / 2
    half_w = (hs_w + 2 * margin) / 2  # 22mm
    half_h = (hs_l + 2 * margin) / 2
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)
