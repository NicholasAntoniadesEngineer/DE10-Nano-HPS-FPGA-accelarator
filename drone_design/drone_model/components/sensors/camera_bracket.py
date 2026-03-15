"""Forward-facing camera bracket — mounts on top of nose boom, lens forward (+X).

Base plate bolts to boom top; vertical wall at +X presents a face for the camera
PCB so the lens points forward. One pivot hole and one linear slot in the base
allow mechanical tilt adjustment (loosen front bolt, rotate, tighten).
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

_CB = _D["camera_bracket"]
BASE_LX = _CB["base_length_x"]
BASE_LY = _CB["base_width_y"]
BRACKET_T = _CB["thickness"]
WALL_H = _CB["wall_height"]
HOLE_D = _CB["hole_diameter"]
PIVOT_PITCH = _CB["pivot_slot_pitch"]
SLOT_LEN = _CB["tilt_slot_length"]

CAM_MOUNT = _D["camera_mounting"]
CAM_HOLE_IX = CAM_MOUNT["mounting_hole_inset_x"]
CAM_HOLE_IY = CAM_MOUNT["mounting_hole_inset_y"]
CAM_W = _D["camera"]["adapter_pcb_width"]
CAM_L = _D["camera"]["adapter_pcb_length"]

CATALOG = {
    "camera_bracket": {
        "material": "FR4 Glass Epoxy",
        "thickness": "1.6mm",
        "dims": f"{BASE_LX} x {BASE_LY} base + {WALL_H}mm wall",
        "mass_g": 4,
        "qty": 1,
        "supplier": "JLCPCB (mechanical PCB)",
        "notes": "Forward-facing bracket on boom top; pivot + slot for tilt adjustment",
        "interface": "2x M2 to boom (pivot + slot); 4x M2 to camera PCB",
    },
}


def make_camera_bracket():
    """Bracket: horizontal base (mates to boom top) and forward vertical wall (camera face).

    Local coords: base in XY, bottom at Z=0. Base center at origin. Wall at +X;
    its front face (normal +X) carries the camera. Pivot hole at -X, tilt slot at +X.
    """
    # Base plate — bottom at Z=0, top at Z=BRACKET_T, centered in XY
    base = (
        cq.Workplane("XY")
        .box(BASE_LX, BASE_LY, BRACKET_T, centered=(True, True, False))
    )

    # Pivot hole (rear, frame side)
    pivot_x = -PIVOT_PITCH / 2
    base = (
        base.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .center(pivot_x, 0)
        .circle(HOLE_D / 2)
        .cutThruAll()
    )

    # Tilt slot (front) — linear slot so bracket can rotate about pivot
    slot_center_x = PIVOT_PITCH / 2
    slot_half = SLOT_LEN / 2
    base = (
        base.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .center(slot_center_x, 0)
        .rect(SLOT_LEN, HOLE_D, centered=True)
        .cutThruAll()
    )

    # Vertical wall at +X edge of base (forward face for camera)
    wall_x_back = BASE_LX / 2 - BRACKET_T
    wall_x_front = BASE_LX / 2
    wall = (
        cq.Workplane("XY")
        .box(BRACKET_T, BASE_LY, WALL_H, centered=(False, True, False))
        .translate((wall_x_back, 0, BRACKET_T))
    )

    # Camera PCB mounting holes on wall front face (YZ plane at X=wall_x_front)
    wall_center_z = BRACKET_T + WALL_H / 2
    for sy in [-1, 1]:
        for sz in [-1, 1]:
            hy = sy * (CAM_W / 2 - CAM_HOLE_IX)
            hz_offset = sz * (CAM_L / 2 - CAM_HOLE_IY)
            hole = (
                cq.Workplane("YZ")
                .workplane(offset=wall_x_front)
                .center(hy, wall_center_z + hz_offset)
                .circle(HOLE_D / 2)
                .extrude(-BRACKET_T)
            )
            wall = wall.cut(hole)

    shape = base.union(wall)

    anchors = {}
    if Anchor is not None:
        # Base bottom face — mates to boom top (bracket sits on boom)
        anchors["boom_mount"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Base bottom for boom top attachment",
        )
        # Wall front face center — camera PCB mounts here, lens then points +X
        anchors["camera_mount"] = Anchor(
            point=(BASE_LX / 2, 0, BRACKET_T + WALL_H / 2),
            normal=(1, 0, 0),
            label="Vertical wall face for camera PCB (forward-facing)",
        )

    return shape, anchors
