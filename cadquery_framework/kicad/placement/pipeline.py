"""Placement-optimisation pipeline entry point."""

from __future__ import annotations

import random
from pathlib import Path

from cadquery_framework.kicad.component_library import (
    ComponentDef,
    KeepOutZone,
    NetConnection,
    Placement,
)
from cadquery_framework.kicad.placement.annealing import SimulatedAnnealing
from cadquery_framework.kicad.placement.geometry import (
    BoardGeometry,
    SpatialIndex,
    has_shapely,
    shapely_box,
    shapely_unary_union,
)
from cadquery_framework.kicad.placement.row_packer import RowPacker
from cadquery_framework.kicad.placement.subsystem_detection import auto_detect_subsystems
from cadquery_framework.kicad.placement.utils import log
from cadquery_framework.kicad.placement.zone_assigner import ZoneAssigner


def optimize_placements(
    components_and_refs: list[tuple[ComponentDef, str]],
    nets: dict[str, list[NetConnection]],
    fixed_placements: list[Placement],
    board_width: float,
    board_height: float,
    dims_path: Path,
    subsystem_groups: dict[str, list[str]] | None = None,
    seed: int = 42,
    frame_placements: list[Placement] | None = None,
    keep_out_zones: list[KeepOutZone] | None = None,
) -> list[Placement]:
    """Run the full placement-optimisation pipeline.

    Parameters
    ----------
    components_and_refs : (ComponentDef, ref) tuples to place.
    nets : netlist mapping net_name -> list of NetConnection.
    fixed_placements : pre-placed components in EZ coords (GPIO headers).
    board_width, board_height : PCB dimensions in mm.
    dims_path : path to ``dimensions.json``.
    subsystem_groups : manual grouping of refs by subsystem name.
    seed : PRNG seed for reproducibility.
    frame_placements : components in board coords (ToF connectors).
        Treated as immovable obstacles; NOT returned in result.
    keep_out_zones : board-coord keep-out zones (e.g. antenna area).
        Components (except zone owner) will not be placed here.

    Returns
    -------
    list[Placement] : optimised placements in electronics-zone coordinates.
    """
    random.seed(seed)

    log(f"Starting optimiser: {len(components_and_refs)} components, "
        f"{len(nets)} nets, board {board_width}x{board_height}mm")

    # 1. Board geometry.
    geo = BoardGeometry(board_width, board_height, dims_path)
    log(f"  Geometry built (shapely={'yes' if has_shapely() else 'no'})")

    # Add keep-out zones to forbidden area.
    keep_out_owner_refs: set[str] = set()
    if keep_out_zones and has_shapely() and geo._use_shapely:
        koz_polys = []
        for kz in keep_out_zones:
            koz_polys.append(shapely_box(kz.xmin, kz.ymin, kz.xmax, kz.ymax))
            keep_out_owner_refs.add(kz.owner_ref)
        if koz_polys:
            combined = shapely_unary_union(koz_polys + [geo.forbidden])
            geo.forbidden = combined
            geo.usable_area = shapely_box(0, 0, board_width, board_height).difference(combined)
            log(f"  {len(keep_out_zones)} keep-out zones added to forbidden area")

    # 2. Fixed placements -> board coords.
    fixed_refs: set[str] = {p.ref for p in fixed_placements}
    fixed_anchors: dict[str, tuple[float, float]] = {}
    all_fixed: list[Placement] = []

    ez_ox, ez_oy = geo.get_electronics_zone_offset()
    for fp in fixed_placements:
        bx = fp.x + ez_ox
        by = fp.y + ez_oy
        board_p = Placement(fp.component, fp.ref, bx, by, fp.rotation, fp.side)
        all_fixed.append(board_p)
        fixed_anchors[fp.ref] = (bx, by)

    # 2b. Frame placements (already in board coords).
    frame_fixed: list[Placement] = []
    frame_refs: set[str] = set()
    if frame_placements:
        for fp in frame_placements:
            frame_fixed.append(fp)
            fixed_refs.add(fp.ref)
            frame_refs.add(fp.ref)
            fixed_anchors[fp.ref] = (fp.x, fp.y)
        log(f"  {len(frame_fixed)} frame placements as obstacles")

    # 3. Subsystem grouping.
    comp_map = {ref: cdef for cdef, ref in components_and_refs}
    if subsystem_groups is None:
        subsystem_groups = auto_detect_subsystems(components_and_refs, nets)
    log(f"  {len(subsystem_groups)} subsystem groups")

    subsystems: dict[str, list[tuple[ComponentDef, str]]] = {}
    placed_refs: set[str] = set()
    for sub_name, refs in subsystem_groups.items():
        comps = []
        for ref in refs:
            if ref in fixed_refs:
                continue
            cdef = comp_map.get(ref)
            if cdef is not None:
                comps.append((cdef, ref))
                placed_refs.add(ref)
        if comps:
            subsystems[sub_name] = comps

    unassigned = [
        (cdef, ref) for cdef, ref in components_and_refs
        if ref not in placed_refs and ref not in fixed_refs
    ]
    if unassigned:
        subsystems["_unassigned"] = unassigned
        subsystem_groups["_unassigned"] = [ref for _, ref in unassigned]
        log(f"  {len(unassigned)} unassigned components")

    for fp in fixed_placements:
        found = any(fp.ref in refs for refs in subsystem_groups.values())
        if not found:
            subsystem_groups[fp.ref] = [fp.ref]

    # 4. Zone assignment.
    all_subsystems: dict[str, list[tuple[ComponentDef, str]]] = dict(subsystems)
    for fp in all_fixed:
        if fp.ref not in all_subsystems:
            all_subsystems[fp.ref] = [(fp.component, fp.ref)]

    zone_assigner = ZoneAssigner(geo, all_subsystems, nets)
    zones = zone_assigner.assign(fixed_anchors=fixed_anchors, iterations=800)
    log("  Zones assigned")

    # 5. Deterministic row-packing within zones.
    spatial = SpatialIndex(board_width, board_height)

    for p in all_fixed:
        spatial.add_placement(p)
    for p in frame_fixed:
        spatial.add_placement(p)

    packer = RowPacker(geo, spatial)
    all_placements: list[Placement] = list(all_fixed) + list(frame_fixed)

    sub_order = sorted(
        subsystems.items(),
        key=lambda kv: sum(c.courtyard_w * c.courtyard_h for c, _ in kv[1]),
        reverse=True,
    )

    for sub_name, comps in sub_order:
        zone = zones.get(sub_name)
        if zone is None:
            centroid = (board_width * 0.3, board_height * 0.3)
        else:
            centroid = (zone[0], zone[1])

        sub_placements = packer.pack_subsystem(comps, centroid)
        all_placements.extend(sub_placements)

    log(f"  Packed {len(all_placements)} components (0 overlaps guaranteed)")

    # 6. Simulated annealing refinement.
    sa = SimulatedAnnealing(
        geo, all_placements, fixed_refs, nets,
        subsystem_map=subsystem_groups,
    )
    initial_cost = sa._total_cost()
    log(f"  Initial cost: {initial_cost:.1f}")

    refined = sa.run(t_start=80.0, alpha=0.9988, t_min=0.01, moves_per_temp=5)
    log("  Refinement complete")

    # 7. Convert board coords -> EZ coords, exclude frame placements.
    result: list[Placement] = []
    for p in refined:
        if p.ref in frame_refs:
            continue
        ez_x = p.x - ez_ox
        ez_y = p.y - ez_oy
        result.append(Placement(p.component, p.ref, ez_x, ez_y, p.rotation, p.side))

    # 8. Summary.
    _print_summary(geo, result, nets, ez_ox, ez_oy)

    return result


def _print_summary(
    geo: BoardGeometry,
    placements: list[Placement],
    nets: dict[str, list[NetConnection]],
    ez_ox: float,
    ez_oy: float,
) -> None:
    ref_idx = {p.ref: i for i, p in enumerate(placements)}
    n = len(placements)

    total_hpwl = 0.0
    for net_name, conns in nets.items():
        if not net_name:
            continue
        xs, ys = [], []
        for nc in conns:
            idx = ref_idx.get(nc.ref)
            if idx is not None:
                xs.append(placements[idx].x)
                ys.append(placements[idx].y)
        if len(xs) >= 2:
            total_hpwl += (max(xs) - min(xs)) + (max(ys) - min(ys))

    overlap_count = 0
    for i in range(n):
        bi = placements[i].courtyard_bounds
        for j in range(i + 1, n):
            bj = placements[j].courtyard_bounds
            if (bi[0] < bj[2] and bi[2] > bj[0]
                    and bi[1] < bj[3] and bi[3] > bj[1]):
                overlap_count += 1

    cutout_violations = 0
    for p in placements:
        bx = p.x + ez_ox
        by = p.y + ez_oy
        if not geo.is_placeable(
            bx, by, p.component.courtyard_w, p.component.courtyard_h, p.rotation,
        ):
            cutout_violations += 1

    log("--- Placement Summary ---")
    log(f"  Components: {n}")
    log(f"  HPWL:       {total_hpwl:.1f}mm")
    log(f"  Overlaps:   {overlap_count}")
    log(f"  Cutout vio: {cutout_violations}")
    log("-------------------------")
