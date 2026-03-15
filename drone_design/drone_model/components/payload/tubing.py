"""Silicone tubing for water path: reservoir → pump → frame edge → boom → drip nozzle.

Supports:
- make_tubing_segment(length): single straight hollow cylinder (legacy).
- make_tubing_path(waypoints, bend_radius, use_spline): one continuous hollow tube along
  a 3D path. use_spline=True (default) fits a smooth B-spline through waypoints for a
  natural pipe look; use_spline=False uses line segments with circular arc fillets.
Dimensions (OD/ID) from pump config in dimensions.json.
"""

import json
import math
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

TUBE_OD = _D["pump"]["tube_od"]
TUBE_ID = _D["pump"]["tube_id"]
TUBING_BEND_RADIUS = _D["pump"].get("tubing_bend_radius", 5.0)


def _vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_len(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec_scale(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec_normalize(v):
    length = _vec_len(v)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return _vec_scale(v, 1.0 / length)


def _vec_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _corner_fillet(before, corner, after, radius):
    """Compute tangent points and arc center for a fillet of given radius at corner.

    before, corner, after are 3D points. Returns (t1, t2, center, normal) for the arc
    from t1 to t2, or None if no fillet (colinear or radius too large).
    """
    u = _vec_normalize(_vec_sub(before, corner))
    v = _vec_normalize(_vec_sub(after, corner))
    cos_angle = _vec_dot(u, v)
    if cos_angle >= 1.0 - 1e-9:
        return None
    if cos_angle <= -1.0 + 1e-9:
        return None
    half_angle = math.acos(cos_angle) * 0.5
    sin_half = math.sin(half_angle)
    tan_half = math.tan(half_angle)
    if sin_half < 1e-9:
        return None
    dist = radius / tan_half
    len_prev = _vec_len(_vec_sub(corner, before))
    len_next = _vec_len(_vec_sub(after, corner))
    dist = min(dist, len_prev * 0.49, len_next * 0.49)
    if dist < 1e-6:
        return None
    t1 = _vec_add(corner, _vec_scale(u, dist))
    t2 = _vec_add(corner, _vec_scale(v, dist))
    bisector = _vec_normalize((-u[0] - v[0], -u[1] - v[1], -u[2] - v[2]))
    r_sin = radius / sin_half
    center = _vec_add(corner, _vec_scale(bisector, r_sin))
    dx = t1[0] - center[0]
    dy = t1[1] - center[1]
    dz = t1[2] - center[2]
    nx = (t2[0] - center[0]) * dz - (t2[2] - center[2]) * dy
    ny = (t2[2] - center[2]) * dx - (t2[0] - center[0]) * dz
    nz = (t2[0] - center[0]) * dy - (t2[1] - center[1]) * dx
    nn = math.sqrt(nx * nx + ny * ny + nz * nz)
    if nn < 1e-12:
        return None
    normal = (nx / nn, ny / nn, nz / nn)
    return (t1, t2, center, normal)


def _make_spline_wire(waypoints):
    """Build a 3D Wire as a smooth B-spline through all waypoints (natural pipe look)."""
    from OCP.gp import gp_Pnt
    from OCP.TColgp import TColgp_Array1OfPnt
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge

    n = len(waypoints)
    if n < 2:
        raise ValueError("spline wire requires at least 2 waypoints")
    if n == 2:
        return cq.Wire.assembleEdges([
            cq.Edge.makeLine(cq.Vector(*waypoints[0]), cq.Vector(*waypoints[1])),
        ])
    arr = TColgp_Array1OfPnt(1, n)
    for i, w in enumerate(waypoints):
        arr.SetValue(i + 1, gp_Pnt(float(w[0]), float(w[1]), float(w[2])))
    interp = GeomAPI_Interpolate(arr, False, 1e-6)
    interp.Perform()
    if not interp.IsDone():
        raise RuntimeError("GeomAPI_Interpolate failed to build spline through waypoints")
    curve = interp.Curve()
    edge = BRepBuilderAPI_MakeEdge(curve).Edge()
    return cq.Wire.assembleEdges([cq.Edge(edge)])


def _make_path_wire(waypoints, bend_radius):
    """Build a 3D Wire through waypoints with rounded corners. Uses OCP for arcs."""
    from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Circ
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge

    n = len(waypoints)
    if n < 2:
        raise ValueError("path wire requires at least 2 waypoints")
    if bend_radius <= 0 or n == 2:
        edges = []
        for i in range(n - 1):
            edges.append(cq.Edge.makeLine(cq.Vector(*waypoints[i]), cq.Vector(*waypoints[i + 1])))
        return cq.Wire.assembleEdges(edges)

    edges = []
    prev = waypoints[0]
    for k in range(1, n):
        if k + 1 < n:
            fil = _corner_fillet(waypoints[k - 1], waypoints[k], waypoints[k + 1], bend_radius)
            if fil is None:
                edges.append(cq.Edge.makeLine(cq.Vector(*prev), cq.Vector(*waypoints[k])))
                prev = waypoints[k]
            else:
                t1, t2, center, normal = fil
                edges.append(cq.Edge.makeLine(cq.Vector(*prev), cq.Vector(*t1)))
                circ = gp_Circ(gp_Ax2(gp_Pnt(*center), gp_Dir(*normal)), bend_radius)
                edge_arc = BRepBuilderAPI_MakeEdge(circ, gp_Pnt(*t1), gp_Pnt(*t2)).Edge()
                edges.append(cq.Edge(edge_arc))
                prev = t2
        else:
            edges.append(cq.Edge.makeLine(cq.Vector(*prev), cq.Vector(*waypoints[n - 1])))
    if not edges:
        raise RuntimeError("path wire produced no edges")
    return cq.Wire.assembleEdges(edges)


def make_tubing_path(waypoints, bend_radius=None, use_spline=True):
    """One continuous hollow tube along a 3D path for a natural pipe look.

    waypoints: list of (x, y, z) in world (Z-up) coordinates.
    bend_radius: when use_spline=False, corner fillet radius in mm.
    use_spline: if True (default), fit a smooth B-spline through waypoints so the
      tube has no right-angle sections; if False, use line segments with arc fillets.
    Returns (shape, anchors) with shape in local coordinates (path starts at origin).
    """
    if len(waypoints) < 2:
        raise ValueError("make_tubing_path requires at least 2 waypoints")
    if bend_radius is None:
        bend_radius = TUBING_BEND_RADIUS
    if use_spline:
        wire = _make_spline_wire(waypoints)
    else:
        wire = _make_path_wire(waypoints, bend_radius)
    first_pt = waypoints[0]
    wire_local = wire.transform(cq.Matrix().translate(cq.Vector(-first_pt[0], -first_pt[1], -first_pt[2])))
    path_length = wire_local.Length()
    profile = cq.Workplane("XY").circle(TUBE_OD / 2).circle(TUBE_ID / 2)
    swept = profile.sweep(wire_local, multisection=False)
    anchors = {}
    if Anchor is not None:
        anchors["start"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Path start")
        anchors["end"] = Anchor(point=(0, 0, path_length), normal=(0, 0, 1), label="Path end")
    return swept, anchors


def make_tubing_segment(length):
    """Silicone tubing segment: hollow cylinder along +Z from 0 to length.

    OD/ID from pump tube config. Start at (0,0,0), end at (0,0,length); assembly
    positions and orients each segment so start/end align with part anchors.
    """
    shape = (
        cq.Workplane("XY")
        .circle(TUBE_OD / 2)
        .circle(TUBE_ID / 2)
        .extrude(length)
    )

    anchors = {}
    if Anchor is not None:
        anchors["start"] = Anchor(
            point=(0, 0, 0),
            normal=(0, 0, -1),
            label="Start (connects to reservoir barb, pump stub, or previous segment)",
        )
        anchors["end"] = Anchor(
            point=(0, 0, length),
            normal=(0, 0, 1),
            label="End (connects to pump stub, waypoint, or nozzle barb)",
        )

    return shape, anchors
