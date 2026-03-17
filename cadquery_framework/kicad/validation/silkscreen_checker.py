"""Silkscreen DRC checker — validates component reference labels and board text.

Checks:
  1. Component reference text does not overlap pads (with clearance).
  2. Component reference text does not overlap mounting holes (with clearance).
  3. Component reference text stays within board edge clearance.
  4. Component reference text does not overlap other component reference text.
  5. Board-level title labels (gr_text) follow same rules.

This DRC is geometric only — actual KiCad DRC will catch trace/copper issues
after manual routing via the .kicad_dru file.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cadquery_framework.kicad.component_library import BoardDefinition
from cadquery_framework.kicad.jlcpcb_constraints import (
    JLCPCB_SILK_TO_PAD_MM,
    JLCPCB_COPPER_TO_EDGE_MM,
    SILK_MICRO_SIZE_MM,
    SILK_LARGE_SIZE_MM,
)


@dataclass
class SilkscreenResult:
    """Result of silkscreen validation."""

    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        """Return True if no errors."""
        return len(self.errors) == 0

    def report(self) -> str:
        """Return human-readable validation report."""
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


def _aabb_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """Return True if two AABBs overlap (axis-aligned bounding boxes).

    Each AABB is (xmin, ymin, xmax, ymax).
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax2 > bx1 and ax1 < bx2 and ay2 > by1 and ay1 < by2


def _aabb_circle_distance(
    aabb: tuple[float, float, float, float],
    circle_x: float,
    circle_y: float,
) -> float:
    """Return minimum distance from AABB to circle centre.

    Returns 0 if AABB contains circle centre.
    """
    xmin, ymin, xmax, ymax = aabb
    # Clamp circle centre to AABB
    closest_x = max(xmin, min(circle_x, xmax))
    closest_y = max(ymin, min(circle_y, ymax))
    # Distance from clamped point to circle centre
    return math.hypot(closest_x - circle_x, closest_y - circle_y)


def _compute_silk_text_aabb(
    x: float,
    y: float,
    rotation_deg: float,
    text_str: str,
    text_height_mm: float,
) -> tuple[float, float, float, float]:
    """Compute rotated AABB for a silkscreen text label.

    Text position (x, y) is the anchor point (centre of text).
    Rotation is in degrees (counter-clockwise).

    Returns (xmin, ymin, xmax, ymax).
    """
    # Character width is roughly 0.6 * height
    char_width = 0.6 * text_height_mm
    text_width = len(text_str) * char_width

    # Half-extents in local (unrotated) coordinates
    hw = text_width / 2
    hh = text_height_mm / 2

    # Rotate AABB half-extents
    rad = math.radians(rotation_deg)
    cos_a = abs(math.cos(rad))
    sin_a = abs(math.sin(rad))

    # Rotated AABB half-extents
    rot_hw = hw * cos_a + hh * sin_a
    rot_hh = hw * sin_a + hh * cos_a

    # Final AABB centred at (x, y)
    return (x - rot_hw, y - rot_hh, x + rot_hw, y + rot_hh)


def validate_silkscreen(board: BoardDefinition) -> SilkscreenResult:
    """Run silkscreen validation checks."""
    errors: list[str] = []
    warnings: list[str] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Build list of all silkscreen AABBs (component refs + board text)
    # ─────────────────────────────────────────────────────────────────────────
    all_silk_aabbs: list[tuple[str, float, float, tuple[float, float, float, float]]] = []
    # Each entry: (ref/label, centre_x, centre_y, aabb)

    # Component reference text silkscreen
    for placement in board.placements:
        p = placement
        c = p.component

        # Reference text position:
        # - Positioned at distance d = courtyard_h/2 + 1.0 from component centre
        # - Along the direction perpendicular to rotation angle
        # - text_bx = p.x + d * sin(θ_rad)
        # - text_by = p.y - d * cos(θ_rad)
        courtyard_h = c.courtyard_h
        d = courtyard_h / 2 + 1.0
        theta_rad = math.radians(p.rotation)
        text_bx = p.x + d * math.sin(theta_rad)
        text_by = p.y - d * math.cos(theta_rad)

        # Compute reference text AABB
        ref_aabb = _compute_silk_text_aabb(
            text_bx,
            text_by,
            p.rotation,
            p.ref,
            SILK_MICRO_SIZE_MM,
        )
        all_silk_aabbs.append((p.ref, text_bx, text_by, ref_aabb))

    # Board-level gr_text labels
    board_labels = [
        ("BOARD_TITLE_1", 55.0, 50.5, SILK_LARGE_SIZE_MM),
        ("BOARD_TITLE_2", 55.0, 46.5, SILK_LARGE_SIZE_MM),
    ]
    for label_name, label_x, label_y, label_size in board_labels:
        label_aabb = _compute_silk_text_aabb(
            label_x,
            label_y,
            0.0,  # No rotation for board labels
            label_name,
            label_size,
        )
        all_silk_aabbs.append((label_name, label_x, label_y, label_aabb))

    # ─────────────────────────────────────────────────────────────────────────
    # Check 1: Silkscreen vs pads (with clearance)
    # ─────────────────────────────────────────────────────────────────────────
    for silk_ref, silk_x, silk_y, silk_aabb in all_silk_aabbs:
        for placement in board.placements:
            # Compute pads in board coordinates (handle rotation)
            for pad in placement.component.pads:
                # Transform pad from component-local to board coordinates
                theta_rad = math.radians(placement.rotation)
                cos_a = math.cos(theta_rad)
                sin_a = math.sin(theta_rad)

                # Pad centre in footprint-local coords, then rotate and translate
                pad_bx = placement.x + pad.x * cos_a - pad.y * sin_a
                pad_by = placement.y + pad.x * sin_a + pad.y * cos_a

                # Expanded pad AABB (with clearance)
                pad_hw = pad.width / 2 + JLCPCB_SILK_TO_PAD_MM
                pad_hh = pad.height / 2 + JLCPCB_SILK_TO_PAD_MM

                # For SMD pads, assume rotation matches component rotation
                # (actual implementation uses OBB, but for clearance AABB is conservative)
                pad_aabb = (
                    pad_bx - pad_hw,
                    pad_by - pad_hh,
                    pad_bx + pad_hw,
                    pad_by + pad_hh,
                )

                # Check overlap
                if _aabb_overlap(silk_aabb, pad_aabb):
                    errors.append(
                        f"Silk '{silk_ref}' at ({silk_x:.1f}, {silk_y:.1f}) "
                        f"overlaps pad {pad.number} of {placement.ref}"
                    )

    # ─────────────────────────────────────────────────────────────────────────
    # Check 2: Silkscreen vs mounting holes (with clearance)
    # ─────────────────────────────────────────────────────────────────────────
    for silk_ref, silk_x, silk_y, silk_aabb in all_silk_aabbs:
        for hole_x, hole_y, hole_d in board.mounting_holes:
            # AABB-to-circle distance with clearance
            clearance_r = hole_d / 2 + JLCPCB_SILK_TO_PAD_MM
            dist = _aabb_circle_distance(silk_aabb, hole_x, hole_y)

            if dist < clearance_r:
                errors.append(
                    f"Silk '{silk_ref}' at ({silk_x:.1f}, {silk_y:.1f}) "
                    f"overlaps mounting hole at ({hole_x:.1f}, {hole_y:.1f})"
                )

    # ─────────────────────────────────────────────────────────────────────────
    # Check 3: Silkscreen vs board edges (with clearance)
    # ─────────────────────────────────────────────────────────────────────────
    edge_margin = JLCPCB_COPPER_TO_EDGE_MM
    for silk_ref, silk_x, silk_y, silk_aabb in all_silk_aabbs:
        xmin, ymin, xmax, ymax = silk_aabb

        if xmin < edge_margin:
            errors.append(
                f"Silk '{silk_ref}' at ({silk_x:.1f}, {silk_y:.1f}) "
                f"is {xmin:.2f}mm from left edge (min {edge_margin}mm)"
            )
        if xmax > board.width - edge_margin:
            errors.append(
                f"Silk '{silk_ref}' at ({silk_x:.1f}, {silk_y:.1f}) "
                f"is {board.width - xmax:.2f}mm from right edge (min {edge_margin}mm)"
            )
        if ymin < edge_margin:
            errors.append(
                f"Silk '{silk_ref}' at ({silk_x:.1f}, {silk_y:.1f}) "
                f"is {ymin:.2f}mm from top edge (min {edge_margin}mm)"
            )
        if ymax > board.height - edge_margin:
            errors.append(
                f"Silk '{silk_ref}' at ({silk_x:.1f}, {silk_y:.1f}) "
                f"is {board.height - ymax:.2f}mm from bottom edge (min {edge_margin}mm)"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Check 4: Silkscreen vs silkscreen (no overlaps allowed)
    # ─────────────────────────────────────────────────────────────────────────
    for i in range(len(all_silk_aabbs)):
        for j in range(i + 1, len(all_silk_aabbs)):
            ref_a, _, _, aabb_a = all_silk_aabbs[i]
            ref_b, _, _, aabb_b = all_silk_aabbs[j]

            if _aabb_overlap(aabb_a, aabb_b):
                errors.append(f"Silk labels '{ref_a}' and '{ref_b}' overlap")

    # ─────────────────────────────────────────────────────────────────────────
    # Warning: No copper routing data
    # ─────────────────────────────────────────────────────────────────────────
    warnings.append(
        "No copper routing data — trace DRC must be run in KiCad after manual routing"
    )

    return SilkscreenResult(errors=errors, warnings=warnings)
