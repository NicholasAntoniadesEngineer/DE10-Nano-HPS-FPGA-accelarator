"""M2.5 hex standoff for board mounting."""

import cadquery as cq


def make_standoff(h):
    """M2.5 hex standoff."""
    return cq.Workplane("XY").polygon(6, 5).extrude(h)
