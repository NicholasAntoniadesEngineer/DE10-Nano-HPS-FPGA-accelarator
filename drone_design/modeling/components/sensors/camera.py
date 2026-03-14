"""OV5640 camera on adapter PCB — lens facing DOWN (-Z), FPC connector on top."""

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


def make_camera():
    """OV5640 camera on adapter PCB — lens facing DOWN (-Z), FPC connector on top."""
    pcb = (
        cq.Workplane("XY")
        .rect(CAM_W, CAM_L)
        .extrude(CAM_H)
        .edges("|Z")
        .fillet(0.5)
    )
    lens = (
        cq.Workplane("XY")
        .circle(CAM_LENS_D / 2)
        .extrude(-CAM_LENS_H)
    )
    fpc_depth = 5.0
    fpc = (
        cq.Workplane("XY")
        .workplane(offset=CAM_H)
        .center(0, -CAM_L / 2 + fpc_depth / 2)
        .rect(CAM_FPC_W, fpc_depth)
        .extrude(CAM_FPC_H)
    )
    return pcb.union(lens).union(fpc)
