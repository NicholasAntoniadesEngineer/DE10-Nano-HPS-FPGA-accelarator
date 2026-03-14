"""Custom daughter board — sensor hub, level shifters, power regulation."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

DB_W = _D["daughter_board"]["width"]
DB_L = _D["daughter_board"]["length"]
DB_H = _D["daughter_board"]["pcb_thickness"]


def make_daughter_board():
    """Daughter board — sensor hub, level shifters, power regulation."""
    board = (
        cq.Workplane("XY")
        .rect(DB_W, DB_L)
        .extrude(DB_H)
        .edges("|Z").fillet(1)
    )
    for pos in [(0, 20), (-15, -15), (15, -15), (0, -30)]:
        ic = (
            cq.Workplane("XY")
            .center(pos[0], pos[1])
            .rect(8, 8)
            .extrude(DB_H + 2)
        )
        board = board.union(ic)
    return board
