"""Auto-detection of subsystem groups from netlist connectivity."""

from __future__ import annotations

from collections import defaultdict, deque

from cadquery_framework.kicad.component_library import ComponentDef, NetConnection
from cadquery_framework.kicad.placement.config import POWER_NETS


def auto_detect_subsystems(
    components: list[tuple[ComponentDef, str]],
    nets: dict[str, list[NetConnection]],
) -> dict[str, list[str]]:
    """Cluster components into subsystems via BFS over signal nets."""
    ref_set = {ref for _c, ref in components}
    comp_map = {ref: cdef for cdef, ref in components}

    adj: dict[str, set[str]] = defaultdict(set)
    for net_name, conns in nets.items():
        if net_name in POWER_NETS or not net_name:
            continue
        refs_on_net = [nc.ref for nc in conns if nc.ref in ref_set]
        for i in range(len(refs_on_net)):
            for j in range(i + 1, len(refs_on_net)):
                adj[refs_on_net[i]].add(refs_on_net[j])
                adj[refs_on_net[j]].add(refs_on_net[i])

    visited: set[str] = set()
    groups: dict[str, list[str]] = {}

    for ref in sorted(ref_set):
        if ref in visited:
            continue
        queue = deque([ref])
        component_refs: list[str] = []
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            component_refs.append(current)
            for neighbour in adj.get(current, []):
                if neighbour not in visited:
                    queue.append(neighbour)

        primary = _find_primary(component_refs, comp_map)
        groups[primary] = component_refs

    return groups


def _find_primary(refs: list[str], comp_map: dict[str, ComponentDef]) -> str:
    """Pick the primary (largest IC, or largest component) as group name."""
    u_refs = [r for r in refs if r in comp_map and comp_map[r].ref_prefix == "U"]
    if u_refs:
        return max(u_refs, key=lambda r: (
            comp_map[r].courtyard_w * comp_map[r].courtyard_h
        ))
    return max(refs, key=lambda r: (
        comp_map[r].courtyard_w * comp_map[r].courtyard_h
        if r in comp_map else 0.0
    ))
