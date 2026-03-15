"""Terasic DE10-Nano FPGA board with mounting holes, GPIO headers, heatsink, and connectors."""

import math
import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
DE10_H         = _D["de10_nano"]["pcb_thickness"]
DE10_COMPONENT_H = _D["de10_nano"]["tallest_component_height"]
HS_W           = _D["de10_nano"]["heatsink_width"]
HS_L           = _D["de10_nano"]["heatsink_length"]
HS_H           = _D["de10_nano"]["heatsink_height"]

CATALOG = {
    "de10_nano": {
        "material": "FR4 PCB + components",
        "dims": f"{DE10_W:.1f} x {DE10_L:.1f} x 1.6mm PCB (17mm tallest)",
        "mass_g": 65, "qty": 1,
        "supplier": "Terasic DE10-Nano",
        "notes": "Cyclone V SoC: dual ARM Cortex-A9 800MHz + 41K ALM FPGA",
        "interface": "4x M2.5 standoffs to bottom plate; GPIO for sensors+motors",
    },
}


def _intel_to_cq(intel_x, intel_y):
    """Convert Intel mechanical layout coords to CadQuery board-centered coords.

    Intel layout: x along 107mm length, y along 68.6mm width.
    CadQuery:     DE10_W (68.58) on x-axis, DE10_L (107.95) on y-axis.
    """
    cq_x = DE10_W / 2 - intel_y
    cq_y = intel_x - DE10_L / 2
    return cq_x, cq_y


def _make_anchors():
    """Build anchor dict (shared across all detail levels)."""
    connectors = _D["de10_nano"]["connectors"]
    hole_inset = _D["de10_nano"]["mounting_hole_inset"]

    anchors = {}
    if Anchor is not None:
        idx = 1
        for sx in [-1, 1]:
            for sy in [-1, 1]:
                hx = sx * (DE10_W / 2 - hole_inset)
                hy = sy * (DE10_L / 2 - hole_inset)
                anchors[f"mounting_hole_{idx}"] = Anchor(
                    point=(hx, hy, 0), normal=(0, 0, -1),
                    label=f"M3 mounting hole {idx} (sx={sx}, sy={sy})")
                idx += 1

        anchors["top_surface"] = Anchor(point=(0, 0, DE10_H), normal=(0, 0, 1), label="PCB top surface center")

        # Heatsink top — fan mounting surface (centered on board)
        anchors["heatsink_top"] = Anchor(
            point=(0, 0, DE10_H + HS_H),
            normal=(0, 0, 1),
            label="Heatsink top surface — cooling fan mount (40x40mm)",
        )

        for key in ("gpio0", "gpio1"):
            c = connectors[key]
            cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
            anchors[key] = Anchor(
                point=(cx, cy + c["length"] / 2, DE10_H + c["height"]),
                normal=(0, 0, 1),
                label=f"{key.upper()} 2x20 pin header top")

    return anchors


def _make_envelope():
    """Simple bounding box for the DE10-Nano."""
    total_h = DE10_H + DE10_COMPONENT_H
    board = cq.Workplane("XY").rect(DE10_W, DE10_L).extrude(total_h)
    return board


def _make_assembly():
    """Assembly-level DE10-Nano (original geometry)."""
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


def _make_detailed():
    """Detailed DE10-Nano with FPGA/HPS packages, buttons, LEDs, SD slot, shaped connectors."""
    det = _D["de10_nano"]["detailed"]
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

    # --- 4x M3 mounting holes ---
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

    # --- FPGA heatsink ---
    heatsink = (
        cq.Workplane("XY")
        .rect(HS_W, HS_L)
        .extrude(DE10_H + HS_H)
    )
    board = board.union(heatsink)

    # --- GPIO headers ---
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

    # --- FPGA BGA package (off-center toward board center-left) ---
    fpga_w = det["fpga_package_width"]
    fpga_l = det["fpga_package_length"]
    fpga_h = det["fpga_package_height"]
    fpga_pkg = (
        cq.Workplane("XY")
        .workplane(offset=DE10_H)
        .center(-5, -10)
        .rect(fpga_w, fpga_l)
        .extrude(fpga_h)
    )
    board = board.union(fpga_pkg)

    # --- HPS BGA package (adjacent to FPGA) ---
    hps_w = det["hps_package_width"]
    hps_l = det["hps_package_length"]
    hps_h = det["hps_package_height"]
    hps_pkg = (
        cq.Workplane("XY")
        .workplane(offset=DE10_H)
        .center(-5, -10 + fpga_l / 2 + hps_l / 2 + 3)
        .rect(hps_w, hps_l)
        .extrude(hps_h)
    )
    board = board.union(hps_pkg)

    # --- 2x pushbuttons on board edge ---
    btn_d = det["button_diameter"]
    btn_h = det["button_height"]
    btn_count = det["button_count"]
    for i in range(btn_count):
        bx = DE10_W / 2 - 8
        by = -DE10_L / 2 + 15 + i * 12
        btn = (
            cq.Workplane("XY")
            .workplane(offset=DE10_H)
            .center(bx, by)
            .circle(btn_d / 2)
            .extrude(btn_h)
        )
        board = board.union(btn)

    # --- 8x LEDs in a row ---
    led_w = det["led_width"]
    led_l = det["led_length"]
    led_h = det["led_height"]
    led_count = det["led_count"]
    led_start_x = -DE10_W / 2 + 10
    led_y = -DE10_L / 2 + 10
    for i in range(led_count):
        lx = led_start_x + i * (led_w + 1.5)
        led = (
            cq.Workplane("XY")
            .workplane(offset=DE10_H)
            .center(lx, led_y)
            .rect(led_w, led_l)
            .extrude(led_h)
        )
        board = board.union(led)

    # --- SD card slot (recessed into board edge) ---
    sd_w = det["sdcard_slot_width"]
    sd_l = det["sdcard_slot_length"]
    sd_h = det["sdcard_slot_height"]
    sd_slot = (
        cq.Workplane("XY")
        .center(DE10_W / 2 - sd_w / 2, 20)
        .rect(sd_w, sd_l)
        .extrude(DE10_H + sd_h)
    )
    board = board.union(sd_slot)

    # --- Connectors with profiled shapes ---
    # HDMI: wider rectangular with slight taper (trapezoid approximation)
    c = connectors["hdmi"]
    cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
    hdmi_body = (
        cq.Workplane("XY")
        .center(cx, cy)
        .rect(c["width"], c["length"])
        .extrude(DE10_H + c["height"])
    )
    # Add the metal shield overhang
    hdmi_shield = (
        cq.Workplane("XY")
        .center(cx, cy)
        .rect(c["width"] + 1.0, c["length"] + 1.0)
        .extrude(DE10_H + c["height"] - 1.0)
    )
    board = board.union(hdmi_shield).union(hdmi_body)

    # USB OTG: micro-USB profile (narrower top)
    c = connectors["usb_otg"]
    cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
    usb_body = (
        cq.Workplane("XY")
        .center(cx, cy)
        .rect(c["width"], c["length"])
        .extrude(DE10_H + c["height"])
    )
    # Recessed port opening
    usb_port = (
        cq.Workplane("XY")
        .workplane(offset=DE10_H + 0.5)
        .center(cx, cy)
        .rect(c["width"] - 1.5, c["length"] - 2.0)
        .extrude(c["height"] - 1.0)
    )
    board = board.union(usb_body).cut(usb_port)

    # Ethernet: RJ45 with stepped profile
    c = connectors["ethernet"]
    cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
    eth_lower = (
        cq.Workplane("XY")
        .center(cx, cy)
        .rect(c["width"], c["length"])
        .extrude(DE10_H + c["height"] * 0.6)
    )
    eth_upper = (
        cq.Workplane("XY")
        .workplane(offset=DE10_H + c["height"] * 0.6)
        .center(cx, cy)
        .rect(c["width"] - 1.0, c["length"] - 1.0)
        .extrude(c["height"] * 0.4)
    )
    board = board.union(eth_lower).union(eth_upper)

    # Barrel jack: cylindrical body
    c = connectors["barrel_jack"]
    cx, cy = _intel_to_cq(c["intel_x"], c["intel_y"])
    jack_r = min(c["width"], c["height"]) / 2
    jack_body = (
        cq.Workplane("XZ")
        .center(cx, DE10_H + jack_r)
        .circle(jack_r)
        .extrude(c["length"])
    )
    jack_body = jack_body.translate((0, cy + c["length"] / 2, 0))
    # Bore hole
    jack_bore = (
        cq.Workplane("XZ")
        .center(cx, DE10_H + jack_r)
        .circle(jack_r * 0.45)
        .extrude(c["length"])
    )
    jack_bore = jack_bore.translate((0, cy + c["length"] / 2, 0))
    board = board.union(jack_body).cut(jack_bore)

    return board


def make_de10_nano(detail="assembly"):
    """DE10-Nano FPGA board with mounting holes, GPIO headers, heatsink, and connectors.

    Parameters
    ----------
    detail : str
        Level of geometric detail: ``"envelope"``, ``"assembly"`` (default),
        or ``"detailed"``.
    """
    if detail == "envelope":
        board = _make_envelope()
    elif detail == "detailed":
        board = _make_detailed()
    else:
        board = _make_assembly()

    return board, _make_anchors()
