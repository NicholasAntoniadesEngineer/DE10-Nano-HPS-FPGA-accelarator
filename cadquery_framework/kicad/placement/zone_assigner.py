"""Force-directed zone assignment for subsystem centroids."""

from __future__ import annotations

import math
from collections import defaultdict

from cadquery_framework.kicad.component_library import ComponentDef, NetConnection
from cadquery_framework.kicad.placement.config import POWER_NETS, make_edge_targets
from cadquery_framework.kicad.placement.geometry import BoardGeometry


class ZoneAssigner:
    """Force-directed simulation to assign subsystem centroids to board regions."""

    def __init__(
        self,
        geometry: BoardGeometry,
        subsystems: dict[str, list[tuple[ComponentDef, str]]],
        nets: dict[str, list[NetConnection]],
    ) -> None:
        self.geo = geometry
        self.subsystems = subsystems
        self.nets = nets
        self._subsystem_names = list(subsystems.keys())
        self._affinity = self._compute_affinity()

    def _compute_affinity(self) -> dict[tuple[str, str], int]:
        ref_to_sub: dict[str, str] = {}
        for sub_name, comps in self.subsystems.items():
            for _cdef, ref in comps:
                ref_to_sub[ref] = sub_name

        affinity: dict[tuple[str, str], int] = defaultdict(int)
        for net_name, conns in self.nets.items():
            if net_name in POWER_NETS or not net_name:
                continue
            subs_on_net: set[str] = set()
            for nc in conns:
                s = ref_to_sub.get(nc.ref)
                if s is not None:
                    subs_on_net.add(s)
            subs_list = sorted(subs_on_net)
            for i in range(len(subs_list)):
                for j in range(i + 1, len(subs_list)):
                    affinity[(subs_list[i], subs_list[j])] += 1
        return dict(affinity)

    def assign(
        self,
        fixed_anchors: dict[str, tuple[float, float]] | None = None,
        iterations: int = 800,
    ) -> dict[str, tuple[float, float, float]]:
        if fixed_anchors is None:
            fixed_anchors = {}

        names = self._subsystem_names
        n = len(names)
        if n == 0:
            return {}

        radii: dict[str, float] = {}
        for name, comps in self.subsystems.items():
            area = sum(c.courtyard_w * c.courtyard_h for c, _r in comps)
            radii[name] = max(math.sqrt(area / math.pi), 3.0)

        pos: dict[str, list[float]] = {}
        vel: dict[str, list[float]] = {}

        bw, bh = self.geo.board_w, self.geo.board_h

        edge_targets = make_edge_targets(bw, bh)

        # Initialise at edge targets if available, else random usable.
        for name in names:
            if name in fixed_anchors:
                px, py = fixed_anchors[name]
            elif name in edge_targets:
                px, py = edge_targets[name]
                px, py = self.geo.nearest_usable_point(px, py)
            else:
                px, py = self.geo.random_point_in_usable()
            pos[name] = [px, py]
            vel[name] = [0.0, 0.0]

        dt = 0.3
        damping = 0.85
        k_attract = 0.02
        k_repel = 200.0
        k_forbidden = 5.0
        k_edge = 0.15

        for _step in range(iterations):
            forces: dict[str, list[float]] = {nm: [0.0, 0.0] for nm in names}

            for i in range(n):
                a = names[i]
                if a in fixed_anchors:
                    continue
                ax, ay = pos[a]

                for j in range(i + 1, n):
                    b = names[j]
                    bx_p, by_p = pos[b]
                    dx = bx_p - ax
                    dy = by_p - ay
                    dist = math.hypot(dx, dy) + 1e-6
                    ux, uy = dx / dist, dy / dist

                    fr = k_repel / (dist * dist)
                    forces[a][0] -= fr * ux
                    forces[a][1] -= fr * uy
                    if b not in fixed_anchors:
                        forces[b][0] += fr * ux
                        forces[b][1] += fr * uy

                    key = (min(a, b), max(a, b))
                    aff = self._affinity.get(key, 0)
                    if aff > 0:
                        rest = radii[a] + radii[b] + 2.0
                        fa = k_attract * aff * (dist - rest)
                        forces[a][0] += fa * ux
                        forces[a][1] += fa * uy
                        if b not in fixed_anchors:
                            forces[b][0] -= fa * ux
                            forces[b][1] -= fa * uy

                d_forb = self.geo.distance_to_forbidden(ax, ay)
                if d_forb < 15.0:
                    strength = k_forbidden * math.exp(-d_forb / 5.0)
                    cx, cy = bw / 2, bh / 2
                    dx_c = ax - cx
                    dy_c = ay - cy
                    mag = math.hypot(dx_c, dy_c) + 1e-6
                    forces[a][0] += strength * dx_c / mag
                    forces[a][1] += strength * dy_c / mag

                if a in edge_targets:
                    tx, ty = edge_targets[a]
                    forces[a][0] += k_edge * (tx - ax)
                    forces[a][1] += k_edge * (ty - ay)

            for name in names:
                if name in fixed_anchors:
                    continue
                vel[name][0] = (vel[name][0] + forces[name][0] * dt) * damping
                vel[name][1] = (vel[name][1] + forces[name][1] * dt) * damping
                pos[name][0] += vel[name][0] * dt
                pos[name][1] += vel[name][1] * dt
                margin = radii.get(name, 3.0) + 2.0
                pos[name][0] = max(margin, min(bw - margin, pos[name][0]))
                pos[name][1] = max(margin, min(bh - margin, pos[name][1]))

        # Post-process: snap centroids to usable area.
        result: dict[str, tuple[float, float, float]] = {}
        for name in names:
            px, py = self.geo.nearest_usable_point(pos[name][0], pos[name][1])
            result[name] = (px, py, radii[name])

        return result
