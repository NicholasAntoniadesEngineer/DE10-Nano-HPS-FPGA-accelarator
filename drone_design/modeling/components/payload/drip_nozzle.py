"""Adjustable drip irrigation emitter — cone shape."""

import cadquery as cq


def make_drip_nozzle():
    """Adjustable drip emitter — cone shape."""
    base = cq.Workplane("XY").circle(5).extrude(5)
    tip = (
        cq.Workplane("XY")
        .workplane(offset=5)
        .circle(4)
        .workplane(offset=12)
        .circle(1.5)
        .loft()
    )
    try:
        return base.union(tip)
    except Exception:
        return cq.Workplane("XY").circle(4).extrude(15)
