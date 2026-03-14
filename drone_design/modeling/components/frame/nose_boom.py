"""Forward-extending PCB boom arm with I-beam skeleton profile."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

BOOM_LENGTH = _D["nose_boom"]["length"]
BOOM_WIDTH  = _D["nose_boom"]["width"]
BOOM_THICK  = _D["nose_boom"]["thickness"]
BOOM_FLANGE = _D["nose_boom"]["flange_width"]
BOOM_WEB    = _D["nose_boom"]["web_width"]


def make_nose_boom():
    """Forward-extending PCB boom arm with I-beam skeleton profile."""
    boom = (
        cq.Workplane("XY")
        .rect(BOOM_LENGTH, BOOM_WIDTH)
        .extrude(BOOM_THICK)
    )
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
    return boom
