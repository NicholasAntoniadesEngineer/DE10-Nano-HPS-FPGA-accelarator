"""Terasic DE10-Nano FPGA board with mounting holes, GPIO headers, heatsink, and connectors."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
DE10_H         = _D["de10_nano"]["pcb_thickness"]
DE10_COMPONENT_H = _D["de10_nano"]["tallest_component_height"]
HS_W           = _D["de10_nano"]["heatsink_width"]
HS_L           = _D["de10_nano"]["heatsink_length"]
HS_H           = _D["de10_nano"]["heatsink_height"]


def _intel_to_cq(intel_x, intel_y):
    """Convert Intel mechanical layout coords to CadQuery board-centered coords.

    Intel layout: x along 107mm length, y along 68.6mm width.
    CadQuery:     DE10_W (68.58) on x-axis, DE10_L (107.95) on y-axis.
    """
    cq_x = intel_y - DE10_W / 2
    cq_y = intel_x - DE10_L / 2
    return cq_x, cq_y


def make_de10_nano():
    """DE10-Nano FPGA board with mounting holes, GPIO headers, heatsink, and connectors."""
    connectors = _D["de10_nano"]["connectors"]
    hole_d = _D["de10_nano"]["mounting_hole_diameter"]
    hole_inset = _D["de10_nano"]["mounting_hole_inset"]

    # --- Main PCB ---
    board = (
        cq.Workplane("XY")
        .rect(DE10_W, DE10_L)
        .extrude(DE10_H)
        .edges("|Z").fillet(1)
    )

    # --- 4x M3 mounting holes (through-hole cutouts near corners) ---
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (DE10_W / 2 - hole_inset)
            hy = sy * (DE10_L / 2 - hole_inset)
            hole = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(hole_d / 2)
                .extrude(DE10_H)
            )
            board = board.cut(hole)

    # --- FPGA heatsink (centered on board) ---
    heatsink = (
        cq.Workplane("XY")
        .rect(HS_W, HS_L)
        .extrude(DE10_H + HS_H)
    )
    board = board.union(heatsink)

    # --- GPIO headers (2x20 pin) ---
    for key in ("gpio0", "gpio1"):
        c = connectors[key]
        cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
        header = (
            cq.Workplane("XY")
            .center(cx, cy + c["length"] / 2)
            .rect(c["width"], c["length"])
            .extrude(DE10_H + c["height"])
        )
        board = board.union(header)

    # --- Connectors as simple raised blocks ---
    for key in ("hdmi", "usb_otg", "ethernet", "barrel_jack"):
        c = connectors[key]
        cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
        block = (
            cq.Workplane("XY")
            .center(cx, cy)
            .rect(c["width"], c["length"])
            .extrude(DE10_H + c["height"])
        )
        board = board.union(block)

    return board
