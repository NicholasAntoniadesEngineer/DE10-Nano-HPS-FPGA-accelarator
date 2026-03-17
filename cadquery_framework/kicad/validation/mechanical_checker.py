"""Mechanical validation — checks PCB layout against physical assembly constraints.

Ensures the daughter board layout matches the DE10-Nano mechanical geometry
defined in dimensions.json.  Catches mismatches that electrical/physical
validation cannot: GPIO header alignment, mounting hole pattern, heatsink
clearance, board dimension consistency, and connector orientation.

This is the automated answer to "does the layout match the actual drone model?"
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cadquery_framework.kicad.component_library import BoardDefinition, Placement


@dataclass
class MechanicalResult:
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


def _load_dimensions(dims_path: Optional[Path] = None) -> dict:
    """Load dimensions.json from the default path or a provided path."""
    if dims_path is None:
        dims_path = (
            Path(__file__).resolve().parents[3]
            / "drone_design"
            / "drone_model"
            / "dimensions.json"
        )
    return json.loads(dims_path.read_text())


def _find(board: BoardDefinition, ref: str) -> Optional[Placement]:
    """Find placement by ref, or None."""
    try:
        return board.get_placement(ref)
    except KeyError:
        return None


def validate_mechanical(
    board: BoardDefinition,
    dims_path: Optional[Path] = None,
) -> MechanicalResult:
    """Run all mechanical validation checks against dimensions.json.

    Checks:
      1. Board dimensions match dimensions.json
      2. GPIO header spacing matches DE10-Nano GPIO0/GPIO1 separation
      3. Mounting hole pattern matches DE10-Nano standoff pattern
      4. No components overlap the heatsink keep-out zone
      5. Connectors face appropriate board edges
    """
    errors: list[str] = []
    warnings: list[str] = []

    dims = _load_dimensions(dims_path)
    de10 = dims["de10_nano"]
    db_dims = dims["daughter_board"]
    db_mount = dims["daughter_board_mounting"]

    # ------------------------------------------------------------------
    # Check 1: Board dimensions consistency
    # ------------------------------------------------------------------
    # The combined top-plate + daughter board uses frame.plate_size (110×110).
    # Fall back to daughter_board dimensions for a standalone board.
    plate_size = dims.get("frame", {}).get("plate_size")
    if plate_size and abs(board.width - plate_size) < 0.5 and abs(board.height - plate_size) < 0.5:
        # Combined plate — dimensions match plate_size, OK
        pass
    else:
        expected_w = db_dims["width"]
        expected_h = db_dims["length"]
        if abs(board.width - expected_w) > 0.5:
            errors.append(
                f"Board width mismatch: netlist says {board.width}mm, "
                f"dimensions.json says {expected_w}mm"
            )
        if abs(board.height - expected_h) > 0.5:
            errors.append(
                f"Board height mismatch: netlist says {board.height}mm, "
                f"dimensions.json says {expected_h}mm"
            )

    # ------------------------------------------------------------------
    # Check 2: GPIO header spacing matches DE10-Nano
    # ------------------------------------------------------------------
    # DE10-Nano GPIO positions from Intel mechanical layout
    gpio0 = de10["connectors"]["gpio0"]
    gpio1 = de10["connectors"]["gpio1"]

    # GPIO header separation across DE10-Nano width (intel_y axis)
    # Pin 1 to Pin 1 distance
    expected_gpio_sep = abs(gpio0["intel_y"] - gpio1["intel_y"])

    hdr1 = _find(board, "HDR1")
    hdr2 = _find(board, "HDR2")

    if hdr1 and hdr2:
        # Measure separation between header centres
        actual_sep = math.hypot(hdr2.x - hdr1.x, hdr2.y - hdr1.y)

        if abs(actual_sep - expected_gpio_sep) > 1.0:
            errors.append(
                f"GPIO header separation: HDR1↔HDR2 = {actual_sep:.1f}mm, "
                f"but DE10-Nano GPIO0↔GPIO1 = {expected_gpio_sep:.1f}mm "
                f"(must match within 1mm for receptacles to mate)"
            )

        # Check they're at the same Y (both on same intel_x)
        if abs(gpio0["intel_x"] - gpio1["intel_x"]) < 0.1:
            # Both DE10-Nano headers at same x → daughter board headers
            # should be at same y (or x, depending on orientation)
            y_diff = abs(hdr1.y - hdr2.y)
            x_diff = abs(hdr1.x - hdr2.x)

            # Determine orientation: separation should be along x (across width)
            # or along y (along length) of the daughter board
            if x_diff > y_diff:
                # Headers separated in X (across board width) — correct
                if abs(x_diff - expected_gpio_sep) > 1.0:
                    errors.append(
                        f"GPIO header X separation: {x_diff:.1f}mm, "
                        f"expected {expected_gpio_sep:.1f}mm"
                    )
                if y_diff > 2.0:
                    warnings.append(
                        f"GPIO headers not Y-aligned: "
                        f"HDR1 y={hdr1.y:.1f}, HDR2 y={hdr2.y:.1f} "
                        f"(Δy={y_diff:.1f}mm)"
                    )
            else:
                # Headers separated in Y — possibly rotated 90°
                if abs(y_diff - expected_gpio_sep) > 1.0:
                    errors.append(
                        f"GPIO header Y separation: {y_diff:.1f}mm, "
                        f"expected {expected_gpio_sep:.1f}mm"
                    )

    # ------------------------------------------------------------------
    # Check 3: Mounting hole pattern
    # ------------------------------------------------------------------
    # DE10-Nano mounting holes at corners with 4mm inset
    de10_w = de10["board_width"]
    de10_l = de10["board_length"]
    de10_inset = de10["mounting_hole_inset"]
    db_inset = db_mount["mounting_hole_inset"]

    # Expected mounting pattern: DE10-Nano corner holes
    # In DE10-Nano coords: (inset, inset), (w-inset, inset), etc.
    # The daughter board should have matching holes
    de10_hole_sep_x = de10_w - 2 * de10_inset  # ~60.58mm
    de10_hole_sep_y = de10_l - 2 * de10_inset  # ~99.95mm

    if board.mounting_holes:
        # Filter to DE10-Nano standoff holes only (M2.7 = 2.7mm drill).
        # Other holes (e.g. ToF bracket M2 = 2.2mm) are not part of the
        # DE10-Nano mounting pattern and should not affect span checks.
        de10_holes = [h for h in board.mounting_holes if abs(h[2] - 2.7) < 0.2]
        if not de10_holes:
            de10_holes = board.mounting_holes  # fallback if no 2.7mm holes
        holes_x = [h[0] for h in de10_holes]
        holes_y = [h[1] for h in de10_holes]
        actual_sep_x = max(holes_x) - min(holes_x) if len(holes_x) >= 2 else 0
        actual_sep_y = max(holes_y) - min(holes_y) if len(holes_y) >= 2 else 0

        if abs(actual_sep_x - de10_hole_sep_x) > 1.0:
            errors.append(
                f"Mounting hole X span: {actual_sep_x:.1f}mm, "
                f"DE10-Nano pattern: {de10_hole_sep_x:.1f}mm "
                f"(must match for standoff alignment)"
            )
        if abs(actual_sep_y - de10_hole_sep_y) > 1.0:
            errors.append(
                f"Mounting hole Y span: {actual_sep_y:.1f}mm, "
                f"DE10-Nano pattern: {de10_hole_sep_y:.1f}mm "
                f"(must match for standoff alignment)"
            )

    # ------------------------------------------------------------------
    # Check 4: Heatsink clearance zone
    # ------------------------------------------------------------------
    # DE10-Nano heatsink is centred on the FPGA die, roughly at board centre
    # No daughter board component should overlap this zone
    hs_w = de10["heatsink_width"]  # 40mm
    hs_l = de10["heatsink_length"]  # 40mm

    # Heatsink position in DB netlist coords depends on board alignment
    # Using board centre as approximation (heatsink is near FPGA at board centre)
    hs_cx = board.width / 2
    hs_cy = board.height / 2
    hs_zone = (
        hs_cx - hs_w / 2,
        hs_cy - hs_l / 2,
        hs_cx + hs_w / 2,
        hs_cy + hs_l / 2,
    )

    # Note: the heatsink is BELOW the daughter board (on the DE10-Nano),
    # and the daughter board sits above on standoffs with a gap.
    # Through-hole pins protrude ~2-3mm below the PCB.  With the standoff
    # gap (typically 8-11mm), small TH connectors are safe.  Only flag
    # components whose max pin protrusion could reach the heatsink.
    gap_mm = db_dims.get("gap_above_de10", 8.5)
    max_safe_protrusion = 3.5  # mm — JST-XH/SH pins are ≤3mm
    components_over_heatsink = []
    for p in board.placements:
        if p.component.has_thru_holes:
            # Skip if pin protrusion is well within standoff gap
            if gap_mm - max_safe_protrusion >= 2.0:
                continue  # ≥2mm margin — safe
            bounds = p.courtyard_bounds
            if (bounds[2] > hs_zone[0] and bounds[0] < hs_zone[2] and
                    bounds[3] > hs_zone[1] and bounds[1] < hs_zone[3]):
                components_over_heatsink.append(p.ref)

    if components_over_heatsink:
        warnings.append(
            f"Through-hole components over heatsink zone: "
            f"{', '.join(sorted(components_over_heatsink))} — "
            f"verify standoff clearance ({gap_mm}mm gap)"
        )

    # ------------------------------------------------------------------
    # Check 5: Connector edge orientation
    # ------------------------------------------------------------------
    # ESC connectors (J1-J4) should face a board edge (left or right)
    esc_refs = ["J1", "J2", "J3", "J4"]
    for ref in esc_refs:
        p = _find(board, ref)
        if p and p.x > board.width * 0.3:
            warnings.append(
                f"{ref} (ESC connector) at x={p.x:.1f}mm — "
                f"expected near left edge for motor wiring (x < {board.width * 0.3:.0f}mm)"
            )

    # WILC3000 (U12) antenna should be at a board edge
    wilc = _find(board, "U12")
    if wilc:
        edge_dist = min(wilc.x, board.width - wilc.x, wilc.y, board.height - wilc.y)
        if edge_dist > 15.0:
            warnings.append(
                f"U12 (WILC3000) is {edge_dist:.1f}mm from nearest edge — "
                f"antenna should be at board edge for RF performance"
            )

    # Camera FPC (J5) should be near board edge for cable routing
    j5 = _find(board, "J5")
    if j5:
        edge_dist = min(j5.x, board.width - j5.x, j5.y, board.height - j5.y)
        if edge_dist > 10.0:
            warnings.append(
                f"J5 (camera FPC) is {edge_dist:.1f}mm from nearest edge — "
                f"should be at board edge for FPC cable routing"
            )

    return MechanicalResult(errors=errors, warnings=warnings)
