"""OV5640 camera on adapter PCB — lens facing DOWN (-Z), FPC connector on top.

Includes M2 mounting holes for boom attachment.
"""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

CAM_W      = _D["camera"]["adapter_pcb_width"]
CAM_L      = _D["camera"]["adapter_pcb_length"]
CAM_H      = _D["camera"]["adapter_pcb_thickness"]
CAM_LENS_D = _D["camera"]["lens_barrel_diameter"]
CAM_LENS_H = _D["camera"]["lens_barrel_height"]
CAM_FPC_W  = _D["camera"]["fpc_connector_width"]
CAM_FPC_H  = _D["camera"]["fpc_connector_height"]

# Mounting holes
CAM_MOUNT = _D["camera_mounting"]
CAM_HOLE_D   = CAM_MOUNT["mounting_hole_diameter"]
CAM_HOLE_IX  = CAM_MOUNT["mounting_hole_inset_x"]
CAM_HOLE_IY  = CAM_MOUNT["mounting_hole_inset_y"]


def make_camera():
    """OV5640 camera on adapter PCB — lens down, FPC on top, M2 mounting holes."""
    pcb = (
        cq.Workplane("XY")
        .rect(CAM_W, CAM_L)
        .extrude(CAM_H)
        .edges("|Z")
        .fillet(0.5)
    )

    # M2 mounting holes (4 corners)
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (CAM_W / 2 - CAM_HOLE_IX)
            hy = sy * (CAM_L / 2 - CAM_HOLE_IY)
            hole = (
                cq.Workplane("XY")
                .center(hx, hy)
                .circle(CAM_HOLE_D / 2)
                .extrude(CAM_H)
            )
            pcb = pcb.cut(hole)

    # Lens barrel (extends downward)
    lens = (
        cq.Workplane("XY")
        .circle(CAM_LENS_D / 2)
        .extrude(-CAM_LENS_H)
    )

    # FPC connector block on top
    fpc_depth = 5.0
    fpc = (
        cq.Workplane("XY")
        .workplane(offset=CAM_H)
        .center(0, -CAM_L / 2 + fpc_depth / 2)
        .rect(CAM_FPC_W, fpc_depth)
        .extrude(CAM_FPC_H)
    )

    return pcb.union(lens).union(fpc)
