"""Forward-extending PCB boom arm with I-beam skeleton profile and root header holes."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

BOOM_LENGTH = _D["nose_boom"]["length"]
BOOM_WIDTH  = _D["nose_boom"]["width"]
BOOM_THICK  = _D["nose_boom"]["thickness"]
BOOM_FLANGE = _D["nose_boom"]["flange_width"]
BOOM_WEB    = _D["nose_boom"]["web_width"]

# Pin header connection specs
HEADER_PITCH     = _D["connections"]["header_pitch"]
HEADER_HOLE_D    = _D["connections"]["header_hole_diameter"]
BOOM_HEADER_PINS = _D["connections"]["boom_header_pins"]
BOOM_HEADER_INSET = _D["connections"]["boom_header_inset"]


def make_nose_boom():
    """Forward-extending PCB boom arm with I-beam profile and root header holes.

    The root end (closest to frame) has two rows of through-holes for
    male-to-male pin header connection to the frame plates.
    """
    boom = (
        cq.Workplane("XY")
        .rect(BOOM_LENGTH, BOOM_WIDTH)
        .extrude(BOOM_THICK)
    )

    # I-beam cutouts (weight reduction)
    cutout_length = BOOM_LENGTH - 60
    cutout_width = (BOOM_WIDTH - BOOM_WEB) / 2 - BOOM_FLANGE
    if cutout_width > 1 and cutout_length > 1:
        for side in [-1, 1]:
            cy = side * (BOOM_WEB / 2 + BOOM_FLANGE + cutout_width / 2)
            icut = (
                cq.Workplane("XY")
                .center(0, cy)
                .rect(cutout_length, cutout_width)
                .extrude(BOOM_THICK)
            )
            boom = boom.cut(icut)

    # Root end header holes (two rows along Y axis at the -X end)
    hole_r = HEADER_HOLE_D / 2
    span = (BOOM_HEADER_PINS - 1) * HEADER_PITCH
    root_x = -BOOM_LENGTH / 2 + BOOM_HEADER_INSET + 10  # 10mm from root edge

    for row_offset in [-4.0, 4.0]:  # two rows offset from centerline
        for i in range(BOOM_HEADER_PINS):
            hy = -span / 2 + i * HEADER_PITCH
            hole = (
                cq.Workplane("XY")
                .center(root_x + row_offset, hy)
                .circle(hole_r)
                .extrude(BOOM_THICK)
            )
            boom = boom.cut(hole)

    return boom
