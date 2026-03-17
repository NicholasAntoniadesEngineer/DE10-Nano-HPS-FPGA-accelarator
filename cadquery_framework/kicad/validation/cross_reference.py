"""Cross-reference validation between PCB, schematic, BOM, and CPL outputs.

Ensures all generated files are consistent with each other and with the
source netlist definition.  Run after all files are generated.
"""

from __future__ import annotations

from dataclasses import dataclass

from cadquery_framework.kicad.component_library import BoardDefinition


@dataclass
class CrossRefResult:
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


def validate_bom_against_board(
    board: BoardDefinition,
    bom_rows: list[dict[str, str]],
) -> CrossRefResult:
    """Check BOM designators match board placements."""
    errors: list[str] = []
    warnings: list[str] = []

    # Expand BOM designators (e.g. "C1,C2,C3" → {"C1", "C2", "C3"})
    bom_refs: set[str] = set()
    for row in bom_rows:
        for ref in row.get("Designator", "").split(","):
            ref = ref.strip()
            if ref:
                bom_refs.add(ref)

    placement_refs = board.all_refs()

    missing_from_bom = placement_refs - bom_refs
    extra_in_bom = bom_refs - placement_refs

    for ref in sorted(missing_from_bom):
        # Customer-supplied parts (no LCSC#) are intentionally omitted from
        # the JLCPCB BOM — this is expected, not a warning.
        p = board.get_placement(ref)
        if p.component.lcsc:
            errors.append(f"BOM missing: {ref} ({p.component.value}) has LCSC# but not in BOM")

    for ref in sorted(extra_in_bom):
        errors.append(f"BOM extra: {ref} not in board placements")

    return CrossRefResult(errors=errors, warnings=warnings)


def validate_cpl_against_board(
    board: BoardDefinition,
    cpl_rows: list[dict[str, str]],
) -> CrossRefResult:
    """Check CPL positions match board placements."""
    errors: list[str] = []
    warnings: list[str] = []

    cpl_by_ref = {row["Designator"].strip(): row for row in cpl_rows}
    placement_refs = board.all_refs()

    # Every JLCPCB-assembled component should be in CPL
    for p in board.placements:
        if not p.component.lcsc:
            continue  # customer-supplied, not in CPL
        if p.ref not in cpl_by_ref:
            errors.append(f"CPL missing: {p.ref} ({p.component.value})")
            continue

        row = cpl_by_ref[p.ref]
        try:
            cpl_x = float(row["Mid X(mm)"])
            cpl_y = float(row["Mid Y(mm)"])
        except (KeyError, ValueError):
            errors.append(f"CPL format error for {p.ref}")
            continue

        dx = abs(cpl_x - p.x)
        dy = abs(cpl_y - p.y)
        if dx > 0.05 or dy > 0.05:
            errors.append(
                f"CPL position mismatch: {p.ref} — "
                f"CPL ({cpl_x:.3f}, {cpl_y:.3f}) vs board ({p.x:.3f}, {p.y:.3f})"
            )

    return CrossRefResult(errors=errors, warnings=warnings)


def validate_net_table_against_board(
    board: BoardDefinition,
    pcb_net_names: set[str],
) -> CrossRefResult:
    """Check PCB net table matches netlist definition."""
    errors: list[str] = []
    warnings: list[str] = []

    netlist_names = board.all_net_names()
    missing = netlist_names - pcb_net_names
    extra = pcb_net_names - netlist_names

    for name in sorted(missing):
        errors.append(f"Net '{name}' in netlist but not in PCB net table")
    for name in sorted(extra):
        warnings.append(f"Net '{name}' in PCB but not in netlist (auto-generated?)")

    return CrossRefResult(errors=errors, warnings=warnings)
