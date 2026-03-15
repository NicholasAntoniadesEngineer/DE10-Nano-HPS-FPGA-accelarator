"""Silicone tubing: per-segment cylinders with sphere joints.

Each straight run between waypoints is a separate cylinder. Sphere joints
at corners give a smooth appearance. Each segment is a separate manifest
entry with a tight AABB for accurate collision detection.

Dimensions (OD/ID) from pump config in dimensions.json.
"""

import json
import math
import cadquery as cq
from pathlib import Path

from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeSphere

from cadquery_framework.assembly.anchors import Anchor

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

TUBE_OD = _D["pump"]["tube_od"]
TUBE_R = TUBE_OD / 2


def _vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def _vec_len(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])

def _vec_normalize(v):
    d = _vec_len(v)
    return (v[0] / d, v[1] / d, v[2] / d) if d > 1e-12 else (0, 0, 0)


def make_tube_segment(p1, p2):
    """Single cylinder from p1 to p2 in world coordinates.

    Returns (shape, anchors) with shape at origin (p1 = local origin).
    Placed at pos=p1 in the manifest.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-6:
        raise ValueError(f"zero-length segment: {p1} -> {p2}")

    nx, ny, nz = dx / length, dy / length, dz / length
    axis = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(nx, ny, nz))
    cyl = BRepPrimAPI_MakeCylinder(axis, TUBE_R, length).Shape()
    shape = cq.Workplane("XY").newObject([cq.Shape(cyl)])

    end_local = (dx, dy, dz)
    anchors = {
        "start": Anchor(point=(0, 0, 0), normal=(-nx, -ny, -nz), label="Segment start"),
        "end": Anchor(point=end_local, normal=(nx, ny, nz), label="Segment end"),
    }
    return shape, anchors


def make_tube_joint(radius=None):
    """Sphere at origin for smooth joint between segments.

    Returns (shape, anchors). Placed at pos=waypoint in the manifest.
    """
    r = radius or TUBE_R
    sph = BRepPrimAPI_MakeSphere(r).Shape()
    shape = cq.Workplane("XY").newObject([cq.Shape(sph)])
    anchors = {
        "center": Anchor(point=(0, 0, 0), normal=(0, 0, 1), label="Joint center"),
    }
    return shape, anchors


def decompose_path(waypoints):
    """Decompose a waypoint path into segments and joints.

    Returns list of dicts, each with:
      - type: "segment" or "joint"
      - For segments: p1, p2 (world coords)
      - For joints: center (world coords)
    """
    pieces = []
    n = len(waypoints)
    for i in range(n - 1):
        pieces.append({"type": "segment", "p1": waypoints[i], "p2": waypoints[i + 1]})
        if i + 1 < n - 1:
            pieces.append({"type": "joint", "center": waypoints[i + 1]})
    return pieces
