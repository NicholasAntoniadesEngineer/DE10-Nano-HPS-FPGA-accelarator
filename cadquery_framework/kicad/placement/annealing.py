"""Multi-objective simulated annealing refinement pass."""

from __future__ import annotations

import math
import random

from cadquery_framework.kicad.component_library import NetConnection, Placement
from cadquery_framework.kicad.placement.config import (
    COURTYARD_GAP,
    HEAT_SENSITIVE,
    HEAT_SOURCES,
    SA_WEIGHTS,
)
from cadquery_framework.kicad.placement.geometry import BoardGeometry, SpatialIndex
from cadquery_framework.kicad.placement.utils import log


class SimulatedAnnealing:
    """Multi-objective simulated annealing refinement pass.

    Key design: initial placement is already overlap-free, so SA focuses
    on HPWL and thermal optimization.  Overlap penalty is still included
    as a safety net but should stay near zero.
    """

    def __init__(
        self,
        geometry: BoardGeometry,
        placements: list[Placement],
        fixed_refs: set[str],
        nets: dict[str, list[NetConnection]],
        subsystem_map: dict[str, list[str]] | None = None,
    ) -> None:
        self.geo = geometry
        self.placements = list(placements)
        self.fixed_refs = fixed_refs
        self.nets = nets
        self.subsystem_map = subsystem_map or {}

        self._ref_idx: dict[str, int] = {
            p.ref: i for i, p in enumerate(self.placements)
        }
        self._movable: list[int] = [
            i for i, p in enumerate(self.placements)
            if p.ref not in fixed_refs
        ]

        # Build spatial index for overlap checking.
        self._spatial = SpatialIndex(geometry.board_w, geometry.board_h)
        self._spatial.rebuild(self.placements)

        # Pre-compute heat/sensitive indices.
        self._heat_idxs = [
            i for i, p in enumerate(self.placements)
            if p.ref in HEAT_SOURCES
        ]
        self._sens_idxs = [
            i for i, p in enumerate(self.placements)
            if p.ref in HEAT_SENSITIVE
        ]

    def run(
        self,
        t_start: float = 80.0,
        alpha: float = 0.9988,
        t_min: float = 0.01,
        moves_per_temp: int = 5,
    ) -> list[Placement]:
        """Execute SA and return refined placements.

        Default params: ~6000 temp steps x 5 moves = ~30000 total moves.
        """
        if not self._movable:
            return self.placements

        current_cost = self._total_cost()
        best_cost = current_cost
        best_state = [(p.x, p.y, p.rotation) for p in self.placements]

        t = t_start
        accepted = 0
        rejected_invalid = 0
        total_steps = 0

        while t > t_min:
            for _ in range(moves_per_temp):
                move = self._perturb(t)
                if move is None:
                    continue

                old_states = self._apply_move(move)
                if old_states is None:
                    rejected_invalid += 1
                    continue

                new_cost = self._total_cost()
                delta = new_cost - current_cost

                if delta < 0 or random.random() < math.exp(-delta / max(t, 1e-12)):
                    current_cost = new_cost
                    accepted += 1
                    # Update spatial index for moved components.
                    for mi, _, _, _ in old_states:
                        b = self.placements[mi].courtyard_bounds
                        # Rebuild is expensive; we accept the stale index for now
                        # since overlap penalty catches issues
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_state = [
                            (pl.x, pl.y, pl.rotation) for pl in self.placements
                        ]
                else:
                    # Revert.
                    for mi, ox, oy, orot in old_states:
                        self.placements[mi].x = ox
                        self.placements[mi].y = oy
                        self.placements[mi].rotation = orot

            t *= alpha
            total_steps += 1

        # Restore best state.
        for i, (bx, by, br) in enumerate(best_state):
            self.placements[i].x = bx
            self.placements[i].y = by
            self.placements[i].rotation = br

        log(f"  SA: {total_steps} temps x {moves_per_temp} = "
            f"{total_steps * moves_per_temp} moves, "
            f"{accepted} accepted, {rejected_invalid} invalid, "
            f"best={best_cost:.1f}")
        return self.placements

    def _perturb(self, temperature: float) -> dict | None:
        """Generate a move proposal."""
        if not self._movable:
            return None

        sigma = max(temperature * 0.3, 0.3)
        r = random.random()

        if r < 0.55:
            idx = random.choice(self._movable)
            return {"type": "move", "indices": [idx],
                    "dx": random.gauss(0, sigma),
                    "dy": random.gauss(0, sigma), "drot": 0.0}

        elif r < 0.70:
            for _ in range(10):
                if not self.subsystem_map:
                    break
                sub_refs = random.choice(list(self.subsystem_map.values()))
                movable_in_sub = [
                    self._ref_idx[ref] for ref in sub_refs
                    if ref in self._ref_idx and ref not in self.fixed_refs
                ]
                if len(movable_in_sub) >= 2:
                    i, j = random.sample(movable_in_sub, 2)
                    return {"type": "swap", "i": i, "j": j}
            idx = random.choice(self._movable)
            return {"type": "move", "indices": [idx],
                    "dx": random.gauss(0, sigma),
                    "dy": random.gauss(0, sigma), "drot": 0.0}

        elif r < 0.80:
            idx = random.choice(self._movable)
            return {"type": "move", "indices": [idx],
                    "dx": 0.0, "dy": 0.0, "drot": 90.0}

        else:
            if self.subsystem_map:
                sub_refs = random.choice(list(self.subsystem_map.values()))
                movable_in_sub = [
                    self._ref_idx[ref] for ref in sub_refs
                    if ref in self._ref_idx and ref not in self.fixed_refs
                ]
                if len(movable_in_sub) >= 2:
                    dx = random.gauss(0, sigma * 0.4)
                    dy = random.gauss(0, sigma * 0.4)
                    return {"type": "move", "indices": movable_in_sub,
                            "dx": dx, "dy": dy, "drot": 0.0}
            idx = random.choice(self._movable)
            return {"type": "move", "indices": [idx],
                    "dx": random.gauss(0, sigma),
                    "dy": random.gauss(0, sigma), "drot": 0.0}

    def _apply_move(self, move: dict) -> list[tuple[int, float, float, float]] | None:
        """Apply a move proposal.  Returns old states or None if invalid.

        Checks both forbidden-zone validity and courtyard overlap with
        other components (hard constraint -- no overlaps allowed).
        """
        if move["type"] == "swap":
            i, j = move["i"], move["j"]
            pi, pj = self.placements[i], self.placements[j]
            old = [(i, pi.x, pi.y, pi.rotation),
                   (j, pj.x, pj.y, pj.rotation)]
            pi.x, pj.x = pj.x, pi.x
            pi.y, pj.y = pj.y, pi.y
            for mi in [i, j]:
                p = self.placements[mi]
                if not self.geo.is_placeable(
                    p.x, p.y, p.component.courtyard_w,
                    p.component.courtyard_h, p.rotation,
                ):
                    pi.x, pj.x = pj.x, pi.x
                    pi.y, pj.y = pj.y, pi.y
                    return None
            if self._moves_cause_overlap([i, j]):
                pi.x, pj.x = pj.x, pi.x
                pi.y, pj.y = pj.y, pi.y
                return None
            return old

        # Type == "move"
        indices = move["indices"]
        dx, dy, drot = move["dx"], move["dy"], move["drot"]
        old = []
        for mi in indices:
            p = self.placements[mi]
            old.append((mi, p.x, p.y, p.rotation))
            p.x += dx
            p.y += dy
            p.rotation = (p.rotation + drot) % 360.0

        for mi in indices:
            p = self.placements[mi]
            if not self.geo.is_placeable(
                p.x, p.y, p.component.courtyard_w,
                p.component.courtyard_h, p.rotation,
            ):
                for ri, ox, oy, orot in old:
                    self.placements[ri].x = ox
                    self.placements[ri].y = oy
                    self.placements[ri].rotation = orot
                return None

        if self._moves_cause_overlap(indices):
            for ri, ox, oy, orot in old:
                self.placements[ri].x = ox
                self.placements[ri].y = oy
                self.placements[ri].rotation = orot
            return None

        return old

    def _moves_cause_overlap(self, moved_indices: list[int]) -> bool:
        """Check if moved components now overlap any other component."""
        gap = COURTYARD_GAP
        n = len(self.placements)

        for mi in moved_indices:
            mb = self.placements[mi].courtyard_bounds
            mx0 = mb[0] - gap
            my0 = mb[1] - gap
            mx1 = mb[2] + gap
            my1 = mb[3] + gap

            for j in range(n):
                if j == mi:
                    continue
                jb = self.placements[j].courtyard_bounds
                if mx0 < jb[2] and mx1 > jb[0] and my0 < jb[3] and my1 > jb[1]:
                    return True
        return False

    # -- Cost functions --

    def _total_cost(self) -> float:
        w = SA_WEIGHTS
        c_hpwl = self._cost_hpwl()
        c_thermal = self._cost_thermal()
        c_overlap = self._cost_overlap()
        c_cutout = self._cost_cutout()
        c_spread = self._cost_spread()
        return (
            w.hpwl * c_hpwl
            + w.thermal * c_thermal
            + w.overlap * c_overlap
            + w.cutout * c_cutout
            + w.spread * c_spread
        )

    def _cost_hpwl(self) -> float:
        total = 0.0
        for net_name, conns in self.nets.items():
            if not net_name:
                continue
            xs: list[float] = []
            ys: list[float] = []
            for nc in conns:
                idx = self._ref_idx.get(nc.ref)
                if idx is not None:
                    p = self.placements[idx]
                    xs.append(p.x)
                    ys.append(p.y)
            if len(xs) >= 2:
                total += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return total

    def _cost_thermal(self) -> float:
        if not self._heat_idxs or not self._sens_idxs:
            return 0.0
        penalty = 0.0
        for hi in self._heat_idxs:
            hp = self.placements[hi]
            for si in self._sens_idxs:
                sp = self.placements[si]
                dist = math.hypot(hp.x - sp.x, hp.y - sp.y)
                penalty += 100.0 / max(dist, 5.0)
        return penalty

    def _cost_overlap(self) -> float:
        n = len(self.placements)
        total = 0.0
        bounds = [p.courtyard_bounds for p in self.placements]
        for i in range(n):
            ax0, ay0, ax1, ay1 = bounds[i]
            for j in range(i + 1, n):
                bx0, by0, bx1, by1 = bounds[j]
                ox = min(ax1, bx1) - max(ax0, bx0)
                if ox <= 0:
                    continue
                oy = min(ay1, by1) - max(ay0, by0)
                if oy <= 0:
                    continue
                total += ox * oy
        return total * 100.0

    def _cost_cutout(self) -> float:
        total = 0.0
        for p in self.placements:
            if not self.geo.is_placeable(
                p.x, p.y, p.component.courtyard_w,
                p.component.courtyard_h, p.rotation,
            ):
                total += p.component.courtyard_w * p.component.courtyard_h
        return total * 100.0

    def _cost_spread(self) -> float:
        if not self.subsystem_map:
            return 0.0
        penalty = 0.0
        for _sub, refs in self.subsystem_map.items():
            idxs = [self._ref_idx[r] for r in refs if r in self._ref_idx]
            if len(idxs) < 2:
                continue
            xs = [self.placements[i].x for i in idxs]
            ys = [self.placements[i].y for i in idxs]
            spread = (max(xs) - min(xs)) + (max(ys) - min(ys))
            if spread > 25.0:
                penalty += (spread - 25.0) ** 2
        return penalty
