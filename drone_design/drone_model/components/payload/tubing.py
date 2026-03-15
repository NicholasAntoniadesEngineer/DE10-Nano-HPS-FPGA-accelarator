"""Silicone tubing for water path: reservoir → pump → frame edge → boom → drip nozzle.

Supports:
- make_tubing_segment(length): single straight hollow cylinder (legacy).
- make_tubing_path(waypoints, bend_radius): one continuous hollow tube along a 3D path
  with rounded corners of given bend radius (no 90-degree joints).
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
    bisector = _vec_normalize((u[0] + v[0], u[1] + v[1], u[2] + v[2]))
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


def _make_path_wire(waypoints, bend_radius):
    """Build a 3D Wire through waypoints with rounded corners. Uses OCP for arcs."""
    from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Circ
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.TopoDS import TopoDS_Edge, TopoDS_Wire

    n = len(waypoints)
    if n < 2:
        return None
    if bend_radius <= 0 or n == 2:
        edges = []
        for i in range(n - 1):
            p1 = waypoints[i]
            p2 = waypoints[i + 1]
            edges.append(cq.Edge.makeLine(cq.Vector(*p1), cq.Vector(*p2)))
        return cq.Wire.assembleEdges(edges)

    edges = []
    for i in range(n - 1):
        a = waypoints[i]
        b = waypoints[i + 1]
        if i == 0:
            if n == 2:
                edges.append(cq.Edge.makeLine(cq.Vector(*a), cq.Vector(*b)))
                break
            fil = _corner_fillet(a, b, waypoints[i + 2], bend_radius) if n > 2 else None
            if fil is None:
                edges.append(cq.Edge.makeLine(cq.Vector(*a), cq.Vector(*b)))
            else:
                t1, t2, center, normal = fil
                edges.append(cq.Edge.makeLine(cq.Vector(*a), cq.Vector(*t1)))
                circ = gp_Circ(gp_Ax2(gp_Pnt(*center), gp_Dir(*normal)), bend_radius)
                edge_arc = BRepBuilderAPI_MakeEdge(circ, gp_Pnt(*t1), gp_Pnt(*t2)).Edge()
                edges.append(cq.Edge(edge_arc))
        else:
            c = waypoints[i + 1]
            if i + 2 < n:
                fil = _corner_fillet(a, b, waypoints[i + 2], bend_radius)
                if fil is None:
                    edges.append(cq.Edge.makeLine(cq.Vector(*a), cq.Vector(*b)))
                else:
                    t1, t2, center, normal = fil
                    edges.append(cq.Edge.makeLine(cq.Vector(*a), cq.Vector(*t1)))
                    circ = gp_Circ(gp_Ax2(gp_Pnt(*center), gp_Dir(*normal)), bend_radius)
                    edge_arc = BRepBuilderAPI_MakeEdge(circ, gp_Pnt(*t1), gp_Pnt(*t2)).Edge()
                    edges.append(cq.Edge(edge_arc))
            else:
                edges.append(cq.Edge.makeLine(cq.Vector(*a), cq.Vector(*c)))
    if not edges:
        return None
    return cq.Wire.assembleEdges(edges)


def make_tubing_path(waypoints, bend_radius=None):
    """One continuous hollow tube along a 3D path with rounded corners.

    waypoints: list of (x, y, z) in world (Z-up) coordinates.
    bend_radius: corner fillet radius in mm; default from dimensions (tubing_bend_radius).
    Returns (shape, anchors) with shape in local coordinates (path starts at origin).
    """
    if bend_radius is None:
        bend_radius = TUBING_BEND_RADIUS
    if len(waypoints) < 2:
        return make_tubing_segment(0.1)
    wire = _make_path_wire(waypoints, bend_radius)
    if wire is None:
        return make_tubing_segment(0.1)
    first_pt = waypoints[0]
    wire_translated = wire.transform(cq.Matrix().translate(cq.Vector(-first_pt[0], -first_pt[1], -first_pt[2])))
    profile = (
        cq.Workplane("XY")
        .circle(TUBE_OD / 2)
        .circle(TUBE_ID / 2)
    )
    face = profile.val().wrapped if hasattr(profile.val(), "wrapped") else profile.faces().val().wrapped
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.TopoDS import TopoDS_Shape
    wire_ocp = wire_translated.wrapped if hasattr(wire_translated, "wrapped") else wire_translated
    try:
        sweep = (
            cq.Workplane("XY")
            .sweep(wire_translated, multisection=False, transition="right", clean=True)
        )
    except Exception:
        outer = cq.Workplane("XY").circle(TUBE_OD / 2).extrude(1)
        inner = cq.Workplane("XY").circle(TUBE_ID / 2).extrude(1)
        sweep = outer.cut(inner)
    path_edges = wire_translated.Edges()
    if path_edges:
        profile_plane = cq.Workplane("XY").circle(TUBE_OD / 2).circle(TUBE_ID / 2)
        sweep = profile_plane.sweep(path_edges[0].val() if hasattr(path_edges[0], "val") else path_edges[0], multisection=False)
    sweep = cq.Workplane("XY").add(cq.Workplane("XY").circle(TUBE_OD / 2).circle(TUBE_ID / 2).val()).sweep(wire_translated, multisection=False)
    shape = sweep
    length = wire_translated.Length()
    anchors = {}
    if Anchor is not None:
        anchors["start"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Path start")
        anchors["end"] = Anchor(point=(0, 0, length), normal=(0, 0, 1), label="Path end")
    return shape, anchors


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
