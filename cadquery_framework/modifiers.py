"""Parametric modification ops applied to CadQuery shapes.

Used by the pipeline when overlay contains per-part modifications (cut_box,
cut_cylinder, add_box, add_cylinder). Ops are applied in order in part local space.
"""

import cadquery as cq


def apply_op(shape, op):
    """Apply a single modification op to a shape (in part local space).

    Op dict keys:
      type: "cut_box" | "cut_cylinder" | "add_box" | "add_cylinder"
      pos: [x, y, z]
      size: [wx, wy, wz] for box
      r, h: radius and height for cylinder
      rot_deg: [rx, ry, rz] optional, degrees

    Returns the modified CadQuery shape.
    """
    op_type = op.get("type")
    if not op_type:
        return shape
    pos = op.get("pos", [0, 0, 0])
    rot_deg = op.get("rot_deg") or [0, 0, 0]
    rx, ry, rz = rot_deg[0], rot_deg[1], rot_deg[2]

    if op_type in ("cut_box", "add_box"):
        size = op.get("size", [10, 10, 10])
        wx, wy, wz = float(size[0]), float(size[1]), float(size[2])
        tool = cq.Workplane("XY").box(wx, wy, wz, centered=(True, True, True))
    elif op_type in ("cut_cylinder", "add_cylinder"):
        r = float(op.get("r", 5))
        h = float(op.get("h", 10))
        tool = cq.Workplane("XY").cylinder(h, r, centered=(True, True, True))
    else:
        return shape

    if rz:
        tool = tool.rotate((0, 0, 0), (0, 0, 1), rz)
    if ry:
        tool = tool.rotate((0, 0, 0), (0, 1, 0), ry)
    if rx:
        tool = tool.rotate((0, 0, 0), (1, 0, 0), rx)
    tool = tool.translate((float(pos[0]), float(pos[1]), float(pos[2])))
    tool_shape = tool.val()

    if op_type in ("cut_box", "cut_cylinder"):
        return shape.cut(tool_shape)
    return shape.fuse(tool_shape)
