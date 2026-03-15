"""30x30x7mm DC brushless cooling fan — sits on DE10-Nano heatsink."""

import json
import math
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

FRAME_SIZE   = _D["cooling_fan"]["frame_size"]
FRAME_H      = _D["cooling_fan"]["frame_height"]
FRAME_CR     = _D["cooling_fan"]["frame_corner_radius"]
HUB_D        = _D["cooling_fan"]["hub_diameter"]
HUB_H        = _D["cooling_fan"]["hub_height"]
BLADE_COUNT  = _D["cooling_fan"]["blade_count"]
BLADE_OD     = _D["cooling_fan"]["blade_outer_diameter"]
MOUNT_SPACING = _D["cooling_fan"]["mount_hole_spacing"]
MOUNT_HOLE_D = _D["cooling_fan"]["mount_hole_diameter"]
WIRE_D       = _D["cooling_fan"]["wire_diameter"]
WIRE_LEN     = _D["cooling_fan"]["wire_exit_length"]

CATALOG = {
    "cooling_fan": {
        "material": "PBT plastic frame, POM impeller",
        "dims": f"{FRAME_SIZE}x{FRAME_SIZE}x{FRAME_H}mm",
        "mass_g": 3.5, "qty": 1,
        "supplier": "Sunon MF30070V1-1000U-A99 or equivalent",
        "notes": "5V DC, 0.12A, 4.6 CFM, 24mm bolt pattern, ball bearing",
        "interface": "2-pin JST-PH to daughter board 5V rail",
    },
}


def make_cooling_fan():
    """30x30x7mm axial fan with mounting holes, hub, and blade disc."""
    half = FRAME_SIZE / 2

    # Outer frame — rounded square
    frame = (
        cq.Workplane("XY")
        .rect(FRAME_SIZE, FRAME_SIZE)
        .extrude(FRAME_H)
        .edges("|Z").fillet(FRAME_CR)
    )

    # Central airflow opening — circular, leaving ~1.5mm wall
    opening_d = FRAME_SIZE - 3.0
    opening = (
        cq.Workplane("XY")
        .circle(opening_d / 2)
        .extrude(FRAME_H)
    )
    frame = frame.cut(opening)

    # 4x corner mounting holes (M3, at 24mm square pattern)
    mh = MOUNT_SPACING / 2
    for dx, dy in [(-mh, -mh), (-mh, mh), (mh, -mh), (mh, mh)]:
        hole = cq.Workplane("XY").center(dx, dy).circle(MOUNT_HOLE_D / 2).extrude(FRAME_H)
        frame = frame.cut(hole)

    # Hub — central motor housing
    hub = (
        cq.Workplane("XY")
        .circle(HUB_D / 2)
        .extrude(HUB_H)
        .translate((0, 0, FRAME_H - HUB_H))
    )

    # Blade disc — simplified as a thin annular disc between hub and frame
    blade_disc = (
        cq.Workplane("XY")
        .circle(BLADE_OD / 2)
        .circle(HUB_D / 2)
        .extrude(1.0)
        .translate((0, 0, FRAME_H - HUB_H + 1.0))
    )

    # Wire exit (2 wires from -Y face)
    wire_block = (
        cq.Workplane("XY")
        .center(0, -(half + WIRE_LEN / 2))
        .rect(WIRE_D * 4, WIRE_LEN)
        .extrude(2.0)
        .translate((0, 0, 1.0))
    )

    shape = frame.union(hub).union(blade_disc).union(wire_block)

    anchors = {}
    if Anchor is not None:
        # Bottom face — mounts onto heatsink top surface
        anchors["mount_face"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Fan bottom face — mounts on heatsink top surface",
        )
        # Top face — air exhaust
        anchors["exhaust"] = Anchor(
            point=(0, 0, FRAME_H),
            normal=(0, 0, 1),
            label="Fan top face — air exhaust",
        )

    return shape, anchors
