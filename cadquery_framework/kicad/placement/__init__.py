"""Algorithmic PCB component placement optimizer for the drone daughter board.

Pipeline overview
-----------------
1. **BoardGeometry** -- builds a Shapely polygon representing usable PCB area
   (110x110mm board minus heatsink cutout, propeller arcs, and mounting holes).
2. **ZoneAssigner** -- force-directed simulation assigns each subsystem's
   centroid to a region of the board, respecting edge preferences and
   inter-subsystem signal affinity.
3. **RowPacker** -- deterministic row-based packing places components within
   assigned zones.  Largest components first, left-to-right, top-to-bottom.
   Guarantees zero courtyard overlaps.
4. **SimulatedAnnealing** -- multi-objective SA refines the full placement,
   minimising HPWL wirelength, thermal coupling, and subsystem spread
   while maintaining zero overlaps.

Entry point: ``optimize_placements()`` runs the full pipeline and returns a
deterministic list of ``Placement`` objects (seeded PRNG).
"""

from cadquery_framework.kicad.placement.pipeline import optimize_placements

__all__ = ["optimize_placements"]
