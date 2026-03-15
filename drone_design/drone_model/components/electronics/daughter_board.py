"""Custom daughter board — sensor hub, level shifters, power regulation.

Mounts above DE10-Nano via M2.5 standoffs at the same hole pattern.
Two 2x20 GPIO receptacle headers connect to DE10-Nano GPIO0 and GPIO1.
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

DB_W = _D["daughter_board"]["width"]
DB_L = _D["daughter_board"]["length"]
DB_H = _D["daughter_board"]["pcb_thickness"]

# Mounting holes — same pattern as DE10-Nano
DE10_W         = _D["de10_nano"]["board_width"]
DE10_L         = _D["de10_nano"]["board_length"]
DB_MOUNT_HOLE_D = _D["daughter_board_mounting"]["mounting_hole_diameter"]
DB_MOUNT_INSET  = _D["daughter_board_mounting"]["mounting_hole_inset"]

# GPIO header receptacles
GPIO_PITCH  = _D["daughter_board_mounting"]["gpio_receptacle_pitch"]
GPIO_ROWS   = _D["daughter_board_mounting"]["gpio_receptacle_rows"]
GPIO_COLS   = _D["daughter_board_mounting"]["gpio_receptacle_cols"]
GPIO_LENGTH = (GPIO_COLS - 1) * GPIO_PITCH  # 48.26mm for 2x20
GPIO_WIDTH  = (GPIO_ROWS - 1) * GPIO_PITCH  # 2.54mm for 2-row
GPIO_HEADER_H = 8.5  # receptacle housing height (extends downward toward DE10)

CATALOG = {
    "daughter_board": {
        "material": "FR4 PCB + components",
        "dims": "85 x 100 x 1.6mm",
        "mass_g": 35, "qty": 1,
        "supplier": "Custom PCB (JLCPCB)",
        "notes": "Sensor hub: level shifter, I2C mux, barometer, power regulators",
        "interface": "Stacks above DE10-Nano on standoffs",
    },
}


def make_daughter_board():
    """Daughter board with M2.5 mounting holes, GPIO receptacles, and IC footprints."""
    board = (
        cq.Workplane("XY")
        .rect(DB_W, DB_L)
        .extrude(DB_H)
        .edges("|Z").fillet(1)
    )

    # M2.5 mounting holes (match DE10-Nano corner pattern)
    for dx in [-DE10_W/2 + DB_MOUNT_INSET, DE10_W/2 - DB_MOUNT_INSET]:
        for dy in [-DE10_L/2 + DB_MOUNT_INSET, DE10_L/2 - DB_MOUNT_INSET]:
            hole = (
                cq.Workplane("XY")
                .center(dx, dy)
                .circle(DB_MOUNT_HOLE_D / 2)
                .extrude(DB_H)
            )
            board = board.cut(hole)

    # GPIO receptacle headers (2x20, extending downward to mate with DE10-Nano)
    # Use Intel-to-CQ coordinate transform matching de10_nano.py
    gpio_connectors = _D["de10_nano"]["connectors"]
    for key in ("gpio0", "gpio1"):
        c = gpio_connectors[key]
        # Intel layout: x along 107mm length, y along 68.6mm width
        cq_x = c["intel_y"] - DE10_W / 2
        cq_y = c["intel_x"] - DE10_L / 2
        # Header block extending downward (negative Z)
        header = (
            cq.Workplane("XY")
            .center(cq_x, cq_y + c["length"] / 2)
            .rect(GPIO_WIDTH + 2.0, c["length"] + 2.0)
            .extrude(-GPIO_HEADER_H)
        )
        board = board.union(header)

    # IC component blocks (level shifters, mux, power regulators)
    for pos in [(0, 20), (-15, -15), (15, -15), (0, -30)]:
        ic = (
            cq.Workplane("XY")
            .center(pos[0], pos[1])
            .rect(8, 8)
            .extrude(DB_H + 2)
        )
        board = board.union(ic)

    # Anchor points
    anchors = {}
    if Anchor is not None:
        anchors["bottom_face"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Daughter board bottom mates with DE10 headers")

        # Mounting holes matching DE10-Nano corner pattern
        idx = 1
        for dx in [-DE10_W/2 + DB_MOUNT_INSET, DE10_W/2 - DB_MOUNT_INSET]:
            for dy in [-DE10_L/2 + DB_MOUNT_INSET, DE10_L/2 - DB_MOUNT_INSET]:
                anchors[f"mounting_hole_{idx}"] = Anchor(
                    point=(dx, dy, 0), normal=(0, 0, -1),
                    label=f"M2.5 mounting hole {idx}")
                idx += 1

        # GPIO receptacles at same positions as DE10 headers, pointing down
        for key, anchor_name in (("gpio0", "gpio0_receptacle"), ("gpio1", "gpio1_receptacle")):
            c = gpio_connectors[key]
            cq_x = c["intel_y"] - DE10_W / 2
            cq_y = c["intel_x"] - DE10_L / 2
            anchors[anchor_name] = Anchor(
                point=(cq_x, cq_y + c["length"] / 2, -GPIO_HEADER_H),
                normal=(0, 0, -1),
                label=f"{key.upper()} receptacle bottom")

    return board, anchors
