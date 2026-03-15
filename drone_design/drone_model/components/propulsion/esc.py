"""FVT LittleBee 30A BLHeli_32 electronic speed controller."""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

ESC_L     = _D["esc"]["length"]
ESC_W     = _D["esc"]["width"]
ESC_H     = _D["esc"]["height"]
ESC_PAD_L = _D["esc"]["solder_pad_length"]
ESC_PAD_W = _D["esc"]["solder_pad_width"]
ESC_PAD_H = _D["esc"]["solder_pad_height"]
ESC_PAD_N = _D["esc"]["solder_pad_count"]

CATALOG = {
    "esc": {
        "material": "FR4 PCB + MOSFETs",
        "dims": "35 x 17 x 5.5 mm",
        "mass_g": 8, "qty": 4,
        "supplier": "FVT LittleBee 30A BLHeli_32",
        "notes": "30A continuous, DShot600 input, BLHeli_32 firmware",
        "interface": "3-phase output to motor; signal wire to FPGA GPIO",
    },
}


def make_esc():
    """FVT LittleBee 30A BLHeli_32 — PCB body with solder pads."""
    body = (
        cq.Workplane("XY")
        .rect(ESC_L, ESC_W)
        .extrude(ESC_H)
        .edges("|Z").fillet(1)
    )

    pads_per_end = ESC_PAD_N // 2
    spacing = ESC_W / (pads_per_end + 1)

    for end_sign in (+1, -1):
        pad_cy = end_sign * (ESC_L / 2 - ESC_PAD_L / 2)
        for i in range(pads_per_end):
            pad_cx = -ESC_W / 2 + spacing * (i + 1)
            pad = (
                cq.Workplane("XY")
                .center(pad_cx, pad_cy)
                .rect(ESC_PAD_W, ESC_PAD_L)
                .extrude(ESC_H + ESC_PAD_H)
            )
            body = body.union(pad)

    anchors = {}
    if Anchor is not None:
        anchors["top"] = Anchor(point=(0, 0, ESC_H), normal=(0, 0, 1), label="ESC top surface")
        anchors["bottom"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="ESC bottom adhesive pad surface")

    return body, anchors
