"""JLCPCB BOM and CPL (pick-and-place) CSV generators.

Produces two CSV files required for JLCPCB SMT assembly:

  1. BOM (Bill of Materials):
     Comment, Designator, Footprint, LCSC Part #

  2. CPL (Component Placement List):
     Designator, Mid X(mm), Mid Y(mm), Rotation, Layer

Both files are generated from a BoardDefinition instance, ensuring
consistency with the PCB and schematic.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict

from cadquery_framework.kicad.component_library import BoardDefinition, Placement


def generate_bom_csv(board: BoardDefinition) -> str:
    """Generate JLCPCB BOM CSV content.

    Groups components by (value, package, LCSC#) and lists all designators
    sharing that part on one row.  Components without an LCSC number are
    omitted (customer-supplied).

    Returns CSV string.
    """
    # Group placements by (value, package, lcsc)
    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for p in board.placements:
        if not p.component.lcsc:
            continue  # customer-supplied — not in JLCPCB BOM
        key = (p.component.value, p.component.package, p.component.lcsc)
        groups[key].append(p.ref)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])

    for (value, package, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1]):
        refs_sorted = sorted(refs)
        writer.writerow([value, ",".join(refs_sorted), package, lcsc])

    return buf.getvalue()


def generate_cpl_csv(board: BoardDefinition) -> str:
    """Generate JLCPCB CPL (pick-and-place) CSV content.

    Coordinates reference the board top-left corner as origin (matching
    the Placement coordinate system).  Rotation is counter-clockwise.
    Only JLCPCB-assembled components (with LCSC#) are included.

    Returns CSV string.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Designator", "Mid X(mm)", "Mid Y(mm)", "Rotation", "Layer"])

    placements = sorted(board.placements, key=lambda p: p.ref)
    for p in placements:
        if not p.component.lcsc:
            continue  # customer-supplied
        layer = "top" if p.side == "F" else "bottom"
        writer.writerow([
            p.ref,
            f"{p.x:.3f}",
            f"{p.y:.3f}",
            f"{p.rotation:.1f}",
            layer,
        ])

    return buf.getvalue()


def bom_rows(board: BoardDefinition) -> list[dict[str, str]]:
    """Return BOM as list of dicts (for cross-reference validation)."""
    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for p in board.placements:
        if not p.component.lcsc:
            continue
        key = (p.component.value, p.component.package, p.component.lcsc)
        groups[key].append(p.ref)

    rows = []
    for (value, package, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1]):
        refs_sorted = sorted(refs)
        rows.append({
            "Comment": value,
            "Designator": ",".join(refs_sorted),
            "Footprint": package,
            "LCSC Part #": lcsc,
        })
    return rows


def cpl_rows(board: BoardDefinition) -> list[dict[str, str]]:
    """Return CPL as list of dicts (for cross-reference validation)."""
    rows = []
    for p in sorted(board.placements, key=lambda p: p.ref):
        if not p.component.lcsc:
            continue
        rows.append({
            "Designator": p.ref,
            "Mid X(mm)": f"{p.x:.3f}",
            "Mid Y(mm)": f"{p.y:.3f}",
            "Rotation": f"{p.rotation:.1f}",
            "Layer": "top" if p.side == "F" else "bottom",
        })
    return rows
