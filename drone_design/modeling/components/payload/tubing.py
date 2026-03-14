"""Silicone tubing segment (3mm ID x 5mm OD)."""

import cadquery as cq


def make_tubing_segment(length):
    """Silicone tubing segment (3mm ID x 5mm OD)."""
    return (
        cq.Workplane("XY")
        .circle(2.5)
        .circle(1.5)
        .extrude(length)
    )
