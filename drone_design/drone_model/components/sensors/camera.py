"""OV5640 camera on adapter PCB — lens facing DOWN (-Z), FPC connector on top.

Includes M2 mounting holes for boom attachment.
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

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

CATALOG = {
    "camera": {
        "material": "FR4 PCB + CMOS sensor + lens",
        "dims": "25 x 30 x 1.6mm PCB + lens barrel",
        "mass_g": 8, "qty": 1,
        "supplier": "Custom adapter PCB + OV5640 module",
        "notes": "OV5640 5MP camera, 1080p@30fps, DVP parallel mode",
        "interface": "16-pin ribbon to GPIO0; 5V from header",
    },
}


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

    shape = pcb.union(lens).union(fpc)

    anchors = {}
    if Anchor is not None:
        # Top of PCB (Z=CAM_H), normal up — bracket attachment face
        anchors["mount_face"] = Anchor(
            point=(0, 0, CAM_H),
            normal=(0, 0, 1),
            label="PCB top face for bracket attachment",
        )
        # Lens optical center, pointing down (-Z) — lens extends below PCB
        anchors["lens_axis"] = Anchor(
            point=(0, 0, -CAM_LENS_H),
            normal=(0, 0, -1),
            label="Optical center of lens barrel",
        )

    return shape, anchors
