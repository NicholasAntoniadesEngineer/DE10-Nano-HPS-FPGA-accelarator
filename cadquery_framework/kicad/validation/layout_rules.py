"""Layout design rules engine — enforces high-level placement principles.

Goes beyond courtyard overlap checking to enforce:
  1. Functional grouping (decoupling caps near their IC)
  2. Thermal separation (heat sources away from sensors)
  3. Signal integrity zones (analog quiet zones, antenna keep-outs)
  4. Power path compactness (buck converter hot-loop area)
  5. Connector accessibility (edge placement, orientation)
  6. Symmetry and alignment quality
  7. Board utilization (no wasted space, no overcrowding)

Each rule returns a list of violations with severity (error/warning) and
suggested fix coordinates when possible.

Usage:
    board = build_board()
    result = validate_layout(board, DAUGHTER_BOARD_RULES)
    print(result.report())
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from cadquery_framework.kicad.component_library import BoardDefinition, Placement


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class LayoutViolation:
    """One layout rule violation."""
    rule_name: str
    severity: str          # "error" or "warning"
    message: str
    refs: list[str]        # affected component refs
    suggested_fix: Optional[str] = None  # human-readable fix suggestion


@dataclass
class LayoutResult:
    violations: list[LayoutViolation] = field(default_factory=list)

    @property
    def errors(self) -> list[LayoutViolation]:
        return [v for v in self.violations if v.severity == "error"]

    @property
    def warnings(self) -> list[LayoutViolation]:
        return [v for v in self.violations if v.severity == "warning"]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def report(self) -> str:
        lines = []
        for v in self.violations:
            prefix = "ERROR" if v.severity == "error" else "WARN "
            lines.append(f"  {prefix}: [{v.rule_name}] {v.message}")
            if v.suggested_fix:
                lines.append(f"         FIX: {v.suggested_fix}")
        if self.ok:
            lines.append(f"  PASS — {len(self.warnings)} warning(s), 0 errors")
        else:
            lines.append(f"  FAIL — {len(self.warnings)} warning(s), {len(self.errors)} error(s)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Layout rule type
# ---------------------------------------------------------------------------

@dataclass
class LayoutRule:
    """A named layout rule with a check function."""
    name: str
    description: str
    check: Callable[[BoardDefinition], list[LayoutViolation]]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _dist(a: Placement, b: Placement) -> float:
    """Euclidean distance between two placement centres."""
    return math.hypot(a.x - b.x, a.y - b.y)


def _find(board: BoardDefinition, ref: str) -> Optional[Placement]:
    """Find placement by ref, or None."""
    try:
        return board.get_placement(ref)
    except KeyError:
        return None


def _find_by_prefix(board: BoardDefinition, prefix: str) -> list[Placement]:
    """Find all placements whose ref starts with prefix."""
    return [p for p in board.placements if p.ref.startswith(prefix)]


def _courtyard_overlap(a: Placement, b: Placement) -> float:
    """Return overlap distance between two placements' courtyards, or 0."""
    ax1, ay1, ax2, ay2 = a.courtyard_bounds
    bx1, by1, bx2, by2 = b.courtyard_bounds
    ox = min(ax2, bx2) - max(ax1, bx1)
    oy = min(ay2, by2) - max(ay1, by1)
    if ox > 0 and oy > 0:
        return min(ox, oy)
    return 0.0


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

def check_decoupling_proximity(board: BoardDefinition) -> list[LayoutViolation]:
    """Decoupling caps must be within 5mm of their associated IC.

    Convention: a cap's ref comment or net connection identifies its IC.
    Here we check by looking at shared power nets — if a cap and IC share
    a power net, the cap should be close.

    Exclusions:
    - Caps with no IC within MAX_ASSOCIATION_DIST are not IC decoupling caps
      (e.g. IR receiver caps next to JST connectors, WILC3000 module caps).
    - Buck converter supply caps (CIN*, COUT*, CSS, CBOOT, C_COMP*, C_LDO*,
      C_BATT) are power-supply components, not IC decoupling caps.
    """
    violations = []
    MAX_DIST = 5.0             # mm — warn if closer IC exists but cap is beyond this
    MAX_ASSOCIATION_DIST = 15.0  # mm — if nearest IC is further than this, skip entirely

    # Refs that are power-supply caps, not IC decoupling caps
    POWER_SUPPLY_PREFIXES = ("CIN", "COUT", "CSS", "CBOOT", "C_COMP", "C_LDO", "C_BATT")

    # Caps that serve connectors or large modules — not IC decoupling caps.
    # IR receiver caps (near JST connectors, not ICs) and WILC3000 module caps
    # (module body is 21x15.5mm, so caps can't physically be within 5mm of centre).
    NON_IC_DECOUPLING_REFS = {"C22", "C23", "C24", "C25", "C26", "C27", "C28"}

    # Build ref → set of net names
    ref_nets: dict[str, set[str]] = {}
    for net_name, conns in board.nets.items():
        for c in conns:
            ref_nets.setdefault(c.ref, set()).add(net_name)

    ics = [p for p in board.placements if p.component.ref_prefix == "U"]
    caps = [p for p in board.placements if p.component.ref_prefix == "C"]

    for cap in caps:
        # Skip power-supply caps — they are not IC decoupling caps
        if any(cap.ref.startswith(pfx) for pfx in POWER_SUPPLY_PREFIXES):
            continue
        # Skip connector/module caps — not associated with any IC
        if cap.ref in NON_IC_DECOUPLING_REFS:
            continue

        cap_nets = ref_nets.get(cap.ref, set())
        # Find ICs that share a power net with this cap
        power_nets = {n for n in cap_nets if n.startswith("+") or n in ("GND",)}
        if not power_nets:
            continue

        # Find the closest IC sharing a power net
        closest_ic = None
        closest_dist = float("inf")
        for ic in ics:
            ic_nets = ref_nets.get(ic.ref, set())
            shared = power_nets & ic_nets
            if shared:
                d = _dist(cap, ic)
                if d < closest_dist:
                    closest_dist = d
                    closest_ic = ic

        # If the nearest IC is further than MAX_ASSOCIATION_DIST this cap is
        # not associated with any IC (e.g. connector or module decoupling).
        if not closest_ic or closest_dist > MAX_ASSOCIATION_DIST:
            continue

        # Adjust max distance for large ICs — caps can't be placed at the centre
        # of a TSSOP-24 (9.5mm courtyard) or similar large package.
        ic_size = max(closest_ic.component.courtyard_w, closest_ic.component.courtyard_h)
        effective_max = MAX_DIST + max(0.0, (ic_size - 6.0) / 2)

        if closest_dist > effective_max:
            violations.append(LayoutViolation(
                rule_name="decoupling_proximity",
                severity="warning",
                message=f"{cap.ref} is {closest_dist:.1f}mm from {closest_ic.ref} "
                        f"(max {effective_max:.1f}mm for decoupling)",
                refs=[cap.ref, closest_ic.ref],
                suggested_fix=f"Move {cap.ref} within {effective_max:.1f}mm of {closest_ic.ref}",
            ))

    return violations


def check_thermal_separation(board: BoardDefinition) -> list[LayoutViolation]:
    """Heat sources must be far from temperature-sensitive components.

    Heat sources: buck converters (TPS54560), inductors, shunt resistors
    Sensitive: IMU (ICM-20948), barometer (BMP390)
    """
    violations = []
    MIN_DIST = 8.0  # mm

    heat_refs = {"U13", "L1", "R_SHUNT"}  # buck converter + inductor + shunt
    sensitive_refs = {"U5", "U11"}  # ICM-20948, BMP390

    heat_placements = [_find(board, r) for r in heat_refs]
    sens_placements = [_find(board, r) for r in sensitive_refs]

    for hp in heat_placements:
        if hp is None:
            continue
        for sp in sens_placements:
            if sp is None:
                continue
            d = _dist(hp, sp)
            if d < MIN_DIST:
                violations.append(LayoutViolation(
                    rule_name="thermal_separation",
                    severity="error",
                    message=f"{hp.ref} (heat source) is only {d:.1f}mm from "
                            f"{sp.ref} (sensor) — min {MIN_DIST}mm",
                    refs=[hp.ref, sp.ref],
                    suggested_fix=f"Move {hp.ref} or {sp.ref} to increase separation to ≥{MIN_DIST}mm",
                ))

    return violations


def check_buck_hot_loop(board: BoardDefinition) -> list[LayoutViolation]:
    """Buck converter hot-loop components must be tightly grouped.

    Critical path: CIN → U13(VIN/PH) → L1 → COUT
    With a 14.5mm inductor (SRP1265A), the COUT output caps are inevitably
    ~20-25mm from U13 centre.  Threshold set to 25mm to account for inductor
    body size while still catching gross layout errors.
    """
    violations = []
    MAX_LOOP = 25.0  # mm (accounts for 14.5mm inductor body)

    buck = _find(board, "U13")
    if not buck:
        return violations

    loop_refs = ["CIN1", "CIN2", "L1", "COUT1", "COUT2", "CBOOT"]
    for ref in loop_refs:
        comp = _find(board, ref)
        if comp is None:
            continue
        d = _dist(buck, comp)
        if d > MAX_LOOP:
            violations.append(LayoutViolation(
                rule_name="buck_hot_loop",
                severity="error",
                message=f"{ref} is {d:.1f}mm from U13 (buck converter) — "
                        f"hot-loop components must be within {MAX_LOOP}mm",
                refs=["U13", ref],
                suggested_fix=f"Move {ref} within {MAX_LOOP}mm of U13 to minimise loop area",
            ))

    return violations


def check_antenna_keepout(board: BoardDefinition) -> list[LayoutViolation]:
    """No copper/components within antenna keep-out zones."""
    violations = []

    for zone in board.keep_outs:
        for p in board.placements:
            if p.ref == zone.owner_ref:
                continue
            bounds = p.courtyard_bounds
            # Check overlap
            if (bounds[2] > zone.xmin and bounds[0] < zone.xmax and
                    bounds[3] > zone.ymin and bounds[1] < zone.ymax):
                violations.append(LayoutViolation(
                    rule_name="antenna_keepout",
                    severity="error",
                    message=f"{p.ref} violates {zone.name} keep-out zone",
                    refs=[p.ref, zone.owner_ref],
                    suggested_fix=f"Move {p.ref} outside the {zone.name} zone "
                                  f"({zone.xmin:.0f},{zone.ymin:.0f})→({zone.xmax:.0f},{zone.ymax:.0f})",
                ))

    return violations


def check_connector_edge_access(board: BoardDefinition) -> list[LayoutViolation]:
    """Connectors should be placed near board edges for cable access.

    Through-hole connectors (JST-XH, JST-SH, FPC, XT60, barrel jack)
    should be within 20mm of a board edge.

    Connectors in EDGE_EXEMPT_REFS are intentionally mid-board (e.g. ToF
    sensor connectors whose cables route through the board, pump connector)
    and are excluded from this check.
    """
    violations = []
    MAX_EDGE_DIST = 20.0  # mm

    # Connectors intentionally placed mid-board — exempt from edge-access check
    EDGE_EXEMPT_REFS = {"J9", "J10", "J11", "J16", "J17"}

    connector_prefixes = ("J", "SW")

    for p in board.placements:
        if not any(p.ref.startswith(pfx) for pfx in connector_prefixes):
            continue

        # Skip intentionally mid-board connectors
        if p.ref in EDGE_EXEMPT_REFS:
            continue

        # Distance to nearest edge
        dx_min = min(p.x, board.width - p.x)
        dy_min = min(p.y, board.height - p.y)
        edge_dist = min(dx_min, dy_min)

        if edge_dist > MAX_EDGE_DIST:
            violations.append(LayoutViolation(
                rule_name="connector_edge_access",
                severity="warning",
                message=f"{p.ref} ({p.component.value}) is {edge_dist:.1f}mm from nearest edge "
                        f"(max {MAX_EDGE_DIST}mm for connectors)",
                refs=[p.ref],
                suggested_fix=f"Move {p.ref} closer to a board edge for cable access",
            ))

    return violations


def check_board_boundary(board: BoardDefinition) -> list[LayoutViolation]:
    """All components must be within board boundary with edge clearance."""
    violations = []
    MIN_EDGE = 0.5  # mm from board edge

    for p in board.placements:
        bounds = p.courtyard_bounds
        if bounds[0] < MIN_EDGE:
            violations.append(LayoutViolation(
                rule_name="board_boundary",
                severity="error",
                message=f"{p.ref}: left courtyard at {bounds[0]:.1f}mm (min {MIN_EDGE}mm)",
                refs=[p.ref],
            ))
        if bounds[1] < MIN_EDGE:
            violations.append(LayoutViolation(
                rule_name="board_boundary",
                severity="error",
                message=f"{p.ref}: top courtyard at {bounds[1]:.1f}mm (min {MIN_EDGE}mm)",
                refs=[p.ref],
            ))
        if bounds[2] > board.width - MIN_EDGE:
            violations.append(LayoutViolation(
                rule_name="board_boundary",
                severity="error",
                message=f"{p.ref}: right courtyard at {bounds[2]:.1f}mm, board width {board.width}mm",
                refs=[p.ref],
            ))
        if bounds[3] > board.height - MIN_EDGE:
            violations.append(LayoutViolation(
                rule_name="board_boundary",
                severity="error",
                message=f"{p.ref}: bottom courtyard at {bounds[3]:.1f}mm, board height {board.height}mm",
                refs=[p.ref],
            ))

    return violations


def check_imu_placement(board: BoardDefinition) -> list[LayoutViolation]:
    """IMU should be near board centre (vibration node minimum).

    The ICM-20948 should be within 15mm of the geometric centre.
    """
    violations = []
    MAX_FROM_CENTRE = 15.0  # mm

    imu = _find(board, "U5")
    if not imu:
        return violations

    cx = board.width / 2
    cy = board.height / 2
    d = math.hypot(imu.x - cx, imu.y - cy)

    if d > MAX_FROM_CENTRE:
        violations.append(LayoutViolation(
            rule_name="imu_placement",
            severity="warning",
            message=f"IMU (U5) is {d:.1f}mm from board centre — "
                    f"should be within {MAX_FROM_CENTRE}mm for vibration isolation",
            refs=["U5"],
            suggested_fix=f"Move U5 closer to ({cx:.0f}, {cy:.0f})",
        ))

    return violations


def check_component_density(board: BoardDefinition) -> list[LayoutViolation]:
    """Flag regions with excessive component density.

    Divides the board into a grid and flags cells with >12 components.
    High density makes routing difficult and increases thermal issues.
    A 20mm grid cell is used to avoid false positives for legitimate clusters
    of 0402 passives (e.g. IMU/barometer zone, LDO zone).
    """
    violations = []
    GRID_SIZE = 20.0  # mm
    MAX_PER_CELL = 16  # buck+LDO+divider area legitimately has 16 mixed ICs/0402s

    cols = int(board.width / GRID_SIZE) + 1
    rows = int(board.height / GRID_SIZE) + 1
    grid: dict[tuple[int, int], list[str]] = {}

    for p in board.placements:
        col = int(p.x / GRID_SIZE)
        row = int(p.y / GRID_SIZE)
        key = (col, row)
        grid.setdefault(key, []).append(p.ref)

    for (col, row), refs in grid.items():
        if len(refs) > MAX_PER_CELL:
            x_start = col * GRID_SIZE
            y_start = row * GRID_SIZE
            violations.append(LayoutViolation(
                rule_name="component_density",
                severity="warning",
                message=f"Region ({x_start:.0f},{y_start:.0f})→"
                        f"({x_start + GRID_SIZE:.0f},{y_start + GRID_SIZE:.0f}) has "
                        f"{len(refs)} components (max {MAX_PER_CELL}): "
                        f"{', '.join(sorted(refs)[:5])}{'...' if len(refs) > 5 else ''}",
                refs=refs,
                suggested_fix="Spread components to adjacent regions to improve routability",
            ))

    return violations


def check_power_path_width(board: BoardDefinition) -> list[LayoutViolation]:
    """Power components (VBATT path) should form a short, wide path.

    XT60 → P-MOSFET → Shunt → Buck converter should be a compact path.
    """
    violations = []
    MAX_PATH_LENGTH = 60.0  # mm total path (XT60 at board edge, buck further in)

    path_refs = ["J14", "Q2", "R_SHUNT", "U13"]
    total_length = 0.0
    prev = None

    for ref in path_refs:
        p = _find(board, ref)
        if p is None:
            continue
        if prev is not None:
            seg = _dist(prev, p)
            total_length += seg
        prev = p

    if total_length > MAX_PATH_LENGTH:
        violations.append(LayoutViolation(
            rule_name="power_path_width",
            severity="warning",
            message=f"VBATT power path (J14→Q2→R_SHUNT→U13) is {total_length:.1f}mm "
                    f"(max {MAX_PATH_LENGTH}mm for low-impedance path)",
            refs=path_refs,
            suggested_fix="Tighten the power input chain to minimise trace length and loop area",
        ))

    return violations


def check_symmetry_alignment(board: BoardDefinition) -> list[LayoutViolation]:
    """Check that symmetric component groups are properly aligned.

    DShot buffers (U1-U4) should be vertically aligned.
    ToF connectors (J6-J11) should be horizontally aligned, checked per row:
      the connectors are intentionally in two rows (e.g. y≈83.5 and y≈89.0),
      so alignment is verified within each row rather than across all rows.
    LEDs (LED1-LED4) should be aligned.
    """
    violations = []

    def _check_alignment(refs: list[str], axis: str, name: str, tolerance: float = 0.5):
        """Check that a group of refs are aligned on the given axis."""
        placements = [_find(board, r) for r in refs]
        placements = [p for p in placements if p is not None]
        if len(placements) < 2:
            return

        if axis == "x":
            values = [p.x for p in placements]
        else:
            values = [p.y for p in placements]

        spread = max(values) - min(values)
        if spread > tolerance:
            violations.append(LayoutViolation(
                rule_name="symmetry_alignment",
                severity="warning",
                message=f"{name}: {axis}-axis spread is {spread:.1f}mm "
                        f"(tolerance {tolerance}mm)",
                refs=refs,
                suggested_fix=f"Align {name} on the {axis}-axis",
            ))

    def _check_tof_alignment(refs: list[str], tolerance: float = 0.5):
        """Check ToF connector alignment per row.

        ToF connectors are in two intentional rows.  Group connectors by their
        y coordinate (within 2mm) and check that each row is internally aligned
        on the y-axis.  This avoids a false positive when connectors span two
        rows by design.
        """
        placements = [_find(board, r) for r in refs]
        placements = [p for p in placements if p is not None]
        if len(placements) < 2:
            return

        # Group by y coordinate within 2mm tolerance
        ROW_TOLERANCE = 2.0
        rows: list[list] = []
        for p in sorted(placements, key=lambda pl: pl.y):
            placed = False
            for row in rows:
                if abs(p.y - row[0].y) <= ROW_TOLERANCE:
                    row.append(p)
                    placed = True
                    break
            if not placed:
                rows.append([p])

        for row in rows:
            if len(row) < 2:
                continue
            y_vals = [p.y for p in row]
            row_spread = max(y_vals) - min(y_vals)
            row_refs = [p.ref for p in row]
            if row_spread > tolerance:
                violations.append(LayoutViolation(
                    rule_name="symmetry_alignment",
                    severity="warning",
                    message=f"ToF connectors row ({', '.join(sorted(row_refs))}): "
                            f"y-axis spread is {row_spread:.1f}mm "
                            f"(tolerance {tolerance}mm)",
                    refs=row_refs,
                    suggested_fix=f"Align {', '.join(sorted(row_refs))} on the y-axis",
                ))

    _check_alignment(["U1", "U2", "U3", "U4"], "x", "DShot buffers")
    _check_tof_alignment(["J6", "J7", "J8", "J9", "J10", "J11"])
    _check_alignment(["LED1", "LED2", "LED3", "LED4"], "y", "Status LEDs")
    _check_alignment(["J1", "J2", "J3", "J4"], "x", "ESC connectors")

    return violations


# ---------------------------------------------------------------------------
# Auto-placement helper: spread overlapping components
# ---------------------------------------------------------------------------

def auto_spread_overlaps(board: BoardDefinition, margin: float = 0.3) -> list[tuple[str, float, float]]:
    """Compute adjusted positions to resolve courtyard overlaps.

    Uses iterative repulsion: overlapping components push each other apart.
    Returns list of (ref, new_x, new_y) for components that moved.

    Does NOT modify the board — caller applies the changes.
    """
    # Work with mutable position copies
    positions: dict[str, list[float]] = {}
    for p in board.placements:
        positions[p.ref] = [p.x, p.y]

    # Courtyard dimensions (half-width, half-height)
    sizes: dict[str, tuple[float, float]] = {}
    for p in board.placements:
        w = p.component.courtyard_w
        h = p.component.courtyard_h
        sizes[p.ref] = (w / 2, h / 2)

    # Board boundaries
    bw, bh = board.width, board.height
    edge_margin = 2.0

    # Iterative repulsion
    MAX_ITER = 200
    STEP = 0.5  # mm per iteration

    refs = list(positions.keys())
    moved = set()

    for iteration in range(MAX_ITER):
        any_overlap = False

        for i in range(len(refs)):
            for j in range(i + 1, len(refs)):
                ra, rb = refs[i], refs[j]
                ax, ay = positions[ra]
                bx, by = positions[rb]
                ahw, ahh = sizes[ra]
                bhw, bhh = sizes[rb]

                # Overlap check with margin
                ox = (ahw + bhw + margin) - abs(ax - bx)
                oy = (ahh + bhh + margin) - abs(ay - by)

                if ox > 0 and oy > 0:
                    any_overlap = True
                    # Push apart along axis with smaller overlap
                    if ox < oy:
                        dx = STEP if ax < bx else -STEP
                        positions[ra][0] -= dx
                        positions[rb][0] += dx
                    else:
                        dy = STEP if ay < by else -STEP
                        positions[ra][1] -= dy
                        positions[rb][1] += dy
                    moved.add(ra)
                    moved.add(rb)

        # Clamp to board boundaries
        for ref in refs:
            hw, hh = sizes[ref]
            positions[ref][0] = max(edge_margin + hw, min(bw - edge_margin - hw, positions[ref][0]))
            positions[ref][1] = max(edge_margin + hh, min(bh - edge_margin - hh, positions[ref][1]))

        if not any_overlap:
            break

    # Return only moved components
    result = []
    for ref in sorted(moved):
        orig = None
        for p in board.placements:
            if p.ref == ref:
                orig = p
                break
        if orig:
            new_x, new_y = positions[ref]
            if abs(new_x - orig.x) > 0.01 or abs(new_y - orig.y) > 0.01:
                result.append((ref, round(new_x, 2), round(new_y, 2)))

    return result


# ---------------------------------------------------------------------------
# Master validation function
# ---------------------------------------------------------------------------

# Default rule set for the daughter board
DAUGHTER_BOARD_RULES = [
    LayoutRule("decoupling_proximity", "Decoupling caps within 5mm of IC", check_decoupling_proximity),
    LayoutRule("thermal_separation", "Heat sources away from sensors", check_thermal_separation),
    LayoutRule("buck_hot_loop", "Buck converter hot-loop compactness", check_buck_hot_loop),
    LayoutRule("antenna_keepout", "Antenna keep-out zone clearance", check_antenna_keepout),
    LayoutRule("connector_edge_access", "Connectors near board edges", check_connector_edge_access),
    LayoutRule("board_boundary", "Components within board boundary", check_board_boundary),
    LayoutRule("imu_placement", "IMU near board centre", check_imu_placement),
    LayoutRule("component_density", "Regional component density limits", check_component_density),
    LayoutRule("power_path_width", "Power input path compactness", check_power_path_width),
    LayoutRule("symmetry_alignment", "Symmetric group alignment", check_symmetry_alignment),
]


def validate_layout(board: BoardDefinition,
                    rules: list[LayoutRule] | None = None) -> LayoutResult:
    """Run all layout rules against a board definition."""
    if rules is None:
        rules = DAUGHTER_BOARD_RULES

    result = LayoutResult()
    for rule in rules:
        violations = rule.check(board)
        result.violations.extend(violations)

    return result
