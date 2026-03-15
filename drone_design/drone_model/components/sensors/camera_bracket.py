"""L-bracket camera mount — 1.6mm FR4, bolts to nose boom underside.

Geometry: horizontal base plate (bolts to boom bottom) and vertical
drop-down face (camera PCB bolts to this). Similar to tof_bracket
but sized for the OV5640 adapter PCB.
"""

import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads(
    (Path(__file__).resolve().parents[2] / "dimensions.json").read_text()
)

CAM_BRACKET_BASE_W = 30.0    # mm, along boom (X direction)
CAM_BRACKET_BASE_D = 15.0    # mm, across boom (Y direction)
CAM_BRACKET_TAB_H  = 20.0    # mm, vertical drop for camera face
CAM_BRACKET_T      = 1.6     # mm, FR4 thickness
CAM_BRACKET_HOLE_D = 2.2     # mm, M2 holes

CATALOG = {
    "camera_bracket": {
        "material": "FR4 Glass Epoxy", "thickness": "1.6mm",
        "dims": "30 x 15 x 20mm L-bracket",
        "mass_g": 3, "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "L-bracket for OV5640 camera, bolts to boom underside",
        "interface": "2x M2 to boom; 4x M2 to camera PCB",
    },
}


def make_camera_bracket():
    """L-bracket camera mount with boom and camera mounting holes.

    Base face lies in XY plane (bolts to boom underside).
    Tab extends downward from -Y edge (camera PCB bolts to tab face).
    """
    # Base plate — sits under boom
    base = (
        cq.Workplane("XY")
        .rect(CAM_BRACKET_BASE_W, CAM_BRACKET_BASE_D)
        .extrude(CAM_BRACKET_T)
    )
    # 2x M2 boom mounting holes
    for sx in [-1, 1]:
        hx = sx * (CAM_BRACKET_BASE_W / 2 - 4)
        hole = (
            cq.Workplane("XY")
            .center(hx, 0)
            .circle(CAM_BRACKET_HOLE_D / 2)
            .extrude(CAM_BRACKET_T)
        )
        base = base.cut(hole)

    # Vertical tab — drops from -Y edge of base
    tab = (
        cq.Workplane("XZ")
        .center(0, -CAM_BRACKET_TAB_H / 2)
        .rect(CAM_BRACKET_BASE_W, CAM_BRACKET_TAB_H)
        .extrude(CAM_BRACKET_T)
        .translate((0, -CAM_BRACKET_BASE_D / 2, 0))
    )
    # 4x M2 camera PCB mounting holes (match camera adapter)
    cam_hole_inset_x = _D["camera_mounting"]["mounting_hole_inset_x"]
    cam_hole_inset_y = _D["camera_mounting"]["mounting_hole_inset_y"]
    cam_w = _D["camera"]["adapter_pcb_width"]
    cam_l = _D["camera"]["adapter_pcb_length"]
    for sx in [-1, 1]:
        for sy in [-1, 1]:
            hx = sx * (cam_w / 2 - cam_hole_inset_x)
            hz = -CAM_BRACKET_TAB_H / 2 + sy * (min(cam_l, CAM_BRACKET_TAB_H) / 2 - cam_hole_inset_y)
            hole = (
                cq.Workplane("XZ")
                .center(hx, hz)
                .circle(CAM_BRACKET_HOLE_D / 2)
                .extrude(CAM_BRACKET_T)
                .translate((0, -CAM_BRACKET_BASE_D / 2, 0))
            )
            tab = tab.cut(hole)

    shape = base.union(tab)

    anchors = {}
    if Anchor is not None:
        # Base plate top face (Z=CAM_BRACKET_T), normal up — bolts to boom underside
        anchors["boom_mount"] = Anchor(
            point=(0, 0, CAM_BRACKET_T),
            normal=(0, -1, 0),
            label="Base plate top face for boom attachment",
        )
        # Vertical tab outer face (-Y side), normal -Y — camera PCB bolts here
        anchors["camera_mount"] = Anchor(
            point=(0, -CAM_BRACKET_BASE_D / 2 - CAM_BRACKET_T, -CAM_BRACKET_TAB_H / 2),
            normal=(0, -1, 0),
            label="Tab face for camera PCB mounting",
        )

    return shape, anchors
