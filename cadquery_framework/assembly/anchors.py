"""Anchor/constraint-based assembly system for CadQuery models.

Provides a declarative API for positioning parts relative to each other
using named anchor points and constraints (mate, offset, align), rather
than requiring absolute coordinates for every part.

No CadQuery import at module level — works standalone for constraint
solving; CadQuery is only needed when resolve() builds actual shapes.

Rotation convention: ZYX extrinsic euler angles in degrees, matching
stl_export.apply_transform (rz around world Z, then ry around world Y,
then rx around world X).
"""

from dataclasses import dataclass, field
from math import acos, atan2, cos, degrees, radians, sin, sqrt

__all__ = ["Anchor", "AssemblyBuilder"]


# ---------------------------------------------------------------------------
# Vector helpers (stdlib only, no numpy)
# ---------------------------------------------------------------------------

def _vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)


def _vec_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vec_norm(v):
    mag = sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if mag < 1e-12:
        return (0.0, 0.0, 0.0)
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def _vec_len(v):
    return sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


# ---------------------------------------------------------------------------
# 3x3 rotation matrix helpers (row-major)
# ---------------------------------------------------------------------------

def _rot_matrix_from_euler(rx_deg, ry_deg, rz_deg):
    """Build 3x3 rotation matrix from ZYX extrinsic euler angles (degrees).

    Standard active (CCW / right-hand rule) convention, matching CadQuery's
    shape.rotate().  R = Rx(rx) @ Ry(ry) @ Rz(rz), applied as rotated = R @ v.
    """
    rx, ry, rz = radians(rx_deg), radians(ry_deg), radians(rz_deg)
    cx, sx = cos(rx), sin(rx)
    cy, sy = cos(ry), sin(ry)
    cz, sz = cos(rz), sin(rz)

    return (
        (cy * cz,                -cy * sz,               sy),
        (cx * sz + sx * sy * cz,  cx * cz - sx * sy * sz, -sx * cy),
        (sx * sz - cx * sy * cz,  sx * cz + cx * sy * sz,  cx * cy),
    )


def _mat_mul_vec(m, v):
    """Multiply 3x3 matrix by 3-vector."""
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def _mat_mul(a, b):
    """Multiply two 3x3 matrices."""
    result = []
    for i in range(3):
        row = []
        for j in range(3):
            row.append(sum(a[i][k] * b[k][j] for k in range(3)))
        result.append(tuple(row))
    return tuple(result)


def _mat_transpose(m):
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def _euler_from_matrix(m):
    """Extract ZYX extrinsic euler angles (degrees) from 3x3 rotation matrix.

    Expects the standard active (CCW) convention matrix produced by
    _rot_matrix_from_euler.  Returns (rx, ry, rz) in degrees.
    """
    sy = m[0][2]
    sy = max(-1.0, min(1.0, sy))
    ry = asin_safe(sy)
    cy = cos(ry)

    if abs(cy) > 1e-6:
        rz = atan2(-m[0][1], m[0][0])
        rx = atan2(-m[1][2], m[2][2])
    else:
        rz = 0.0
        rx = atan2(m[2][1], m[1][1])

    return (degrees(rx), degrees(ry), degrees(rz))


def asin_safe(x):
    """Clamped asin to avoid domain errors from float imprecision."""
    from math import asin
    return asin(max(-1.0, min(1.0, x)))


def _rotation_matrix_from_axis_angle(axis, angle_rad):
    """Rodrigues' rotation: rotate by angle_rad around unit axis."""
    ax, ay, az = _vec_norm(axis)
    c = cos(angle_rad)
    s = sin(angle_rad)
    t = 1.0 - c
    return (
        (t * ax * ax + c,      t * ax * ay - s * az,  t * ax * az + s * ay),
        (t * ax * ay + s * az,  t * ay * ay + c,       t * ay * az - s * ax),
        (t * ax * az - s * ay,  t * ay * az + s * ax,  t * az * az + c),
    )


# ---------------------------------------------------------------------------
# Public rotation helper
# ---------------------------------------------------------------------------

def rotation_to_align_normals(src_normal, dst_normal, opposing=True):
    """Compute euler angles (rx, ry, rz) in degrees that rotate src_normal
    to align with dst_normal (if opposing=False) or to oppose dst_normal
    (if opposing=True, i.e. face-to-face contact).

    Returns (rx, ry, rz) in degrees, ZYX extrinsic convention.
    """
    src = _vec_norm(src_normal)
    dst = _vec_norm(dst_normal)

    if opposing:
        # We want rotated src to equal -dst
        target = _vec_scale(dst, -1.0)
    else:
        target = dst

    # Find rotation from src to target
    dot = _vec_dot(src, target)
    dot = max(-1.0, min(1.0, dot))

    if dot > 1.0 - 1e-9:
        # Already aligned
        return (0.0, 0.0, 0.0)

    if dot < -1.0 + 1e-9:
        # 180-degree rotation: pick an arbitrary perpendicular axis
        if abs(src[0]) < 0.9:
            perp = _vec_norm(_vec_cross(src, (1, 0, 0)))
        else:
            perp = _vec_norm(_vec_cross(src, (0, 1, 0)))
        mat = _rotation_matrix_from_axis_angle(perp, radians(180))
        return _euler_from_matrix(mat)

    axis = _vec_norm(_vec_cross(src, target))
    angle = acos(dot)
    mat = _rotation_matrix_from_axis_angle(axis, angle)
    return _euler_from_matrix(mat)


# ---------------------------------------------------------------------------
# Transform an anchor from local to world space
# ---------------------------------------------------------------------------

def transform_anchor(anchor, pos, rot):
    """Transform an Anchor from local space to world space.

    Args:
        anchor: Anchor instance in local coordinates.
        pos: (x, y, z) world translation.
        rot: (rx, ry, rz) euler angles in degrees (ZYX extrinsic), or None.

    Returns:
        New Anchor with world-space point and normal.
    """
    if rot and any(abs(r) > 1e-9 for r in rot):
        mat = _rot_matrix_from_euler(*rot)
        world_point = _vec_add(_mat_mul_vec(mat, anchor.point), pos)
        world_normal = _vec_norm(_mat_mul_vec(mat, anchor.normal))
    else:
        world_point = _vec_add(anchor.point, pos)
        world_normal = anchor.normal

    return Anchor(point=world_point, normal=world_normal, label=anchor.label)


# ---------------------------------------------------------------------------
# Anchor dataclass
# ---------------------------------------------------------------------------

@dataclass
class Anchor:
    """A named attachment point on a part, defined in local coordinates.

    Attributes:
        point: (x, y, z) position in the part's local coordinate system.
        normal: (nx, ny, nz) outward-facing direction at this anchor.
        label: Optional human-readable name for display/debugging.
    """
    point: tuple
    normal: tuple = (0.0, 0.0, 1.0)
    label: str = ""


# ---------------------------------------------------------------------------
# Internal constraint types
# ---------------------------------------------------------------------------

@dataclass
class _Placement:
    """Absolute placement of a part."""
    part: str
    pos: tuple
    rot: tuple  # (rx, ry, rz) or (0,0,0)


@dataclass
class _Constraint:
    """A constraint linking a child anchor to a parent anchor."""
    child_part: str
    child_anchor: str
    parent_part: str
    parent_anchor: str
    kind: str  # "mate", "offset", "align"
    gap: float = 0.0
    spin: float = 0.0


@dataclass
class _PartEntry:
    """Internal record for a registered part."""
    name: str
    builder: object  # callable
    args: tuple
    color: str
    display: str
    meta: dict = field(default_factory=dict)
    no_collision: bool = False


# ---------------------------------------------------------------------------
# AssemblyBuilder
# ---------------------------------------------------------------------------

class AssemblyBuilder:
    """Declarative constraint-based assembly builder.

    Usage::

        asm = AssemblyBuilder()
        asm.add("plate", make_plate, color="#B87333", display="Plate")
        asm.add("arm", make_arm, color="#B87333", display="Arm")
        asm.place("plate", at=(0, 0, 0))
        asm.mate("arm.frame_end", "plate.arm_slot")
        manifest = asm.resolve()

    Parts are registered with ``add()``, root positions set with ``place()``,
    and relationships declared with ``mate()``, ``offset()``, or ``align()``.
    ``resolve()`` builds all parts, solves the constraint tree, and returns
    a manifest list compatible with ``pipeline.build_assembly()``.
    """

    def __init__(self):
        self._parts = {}         # name -> _PartEntry
        self._placements = {}    # name -> _Placement
        self._constraints = []   # list of _Constraint
        self._constraint_order = []  # child names in insertion order
        self._viewer_anchors = {}  # name -> list of (anchor_name, point, normal) for merge in resolve()

    def add(self, name, builder, args=(), color="#888888", display=None,
            meta=None, no_collision=False):
        """Register a part with its builder function.

        Args:
            name: Unique part identifier (used in constraint references).
            builder: Callable that returns a CadQuery shape, or a tuple
                of (shape, anchors_dict) where anchors_dict maps anchor
                names to Anchor instances.
            args: Positional arguments to pass to builder.
            color: Hex color string for viewer display.
            display: Human-readable name (defaults to name).
            meta: Optional metadata dict.
            no_collision: If True, exclude from collision detection
                (e.g. visualization-only clearance volumes).
        """
        if name in self._parts:
            raise ValueError(f"Part '{name}' already registered")
        self._parts[name] = _PartEntry(
            name=name,
            builder=builder,
            args=args if isinstance(args, tuple) else (args,),
            color=color,
            display=display or name,
            meta=meta or {},
            no_collision=no_collision,
        )

    def place(self, part, at=(0, 0, 0), rot=(0, 0, 0)):
        """Place a part at an absolute world position (root of constraint tree).

        Args:
            part: Part name (must be registered with add()).
            at: (x, y, z) world position.
            rot: (rx, ry, rz) euler rotation in degrees.
        """
        if part not in self._parts:
            raise ValueError(f"Unknown part '{part}'")
        self._placements[part] = _Placement(part=part, pos=at, rot=rot)

    def _parse_ref(self, ref):
        """Parse 'part_name.anchor_name' into (part_name, anchor_name)."""
        if "." not in ref:
            raise ValueError(
                f"Constraint reference '{ref}' must be 'part.anchor' format"
            )
        dot = ref.index(".")
        return ref[:dot], ref[dot + 1:]

    def mate(self, child_ref, parent_ref, spin=0.0):
        """Face-to-face constraint: child anchor opposes parent anchor normal.

        Args:
            child_ref: 'child_part.anchor_name' string.
            parent_ref: 'parent_part.anchor_name' string.
            spin: Rotation in degrees around the mating normal after alignment.
        """
        child_part, child_anchor = self._parse_ref(child_ref)
        parent_part, parent_anchor = self._parse_ref(parent_ref)
        self._constraints.append(_Constraint(
            child_part=child_part, child_anchor=child_anchor,
            parent_part=parent_part, parent_anchor=parent_anchor,
            kind="mate", spin=spin,
        ))
        if child_part not in self._constraint_order:
            self._constraint_order.append(child_part)

    def offset(self, child_ref, parent_ref, gap=0.0, spin=0.0):
        """Mate with gap: child is shifted along parent normal by gap amount.

        Args:
            child_ref: 'child_part.anchor_name' string.
            parent_ref: 'parent_part.anchor_name' string.
            gap: Distance along parent anchor normal.
            spin: Rotation in degrees around the mating normal after alignment.
        """
        child_part, child_anchor = self._parse_ref(child_ref)
        parent_part, parent_anchor = self._parse_ref(parent_ref)
        self._constraints.append(_Constraint(
            child_part=child_part, child_anchor=child_anchor,
            parent_part=parent_part, parent_anchor=parent_anchor,
            kind="offset", gap=gap, spin=spin,
        ))
        if child_part not in self._constraint_order:
            self._constraint_order.append(child_part)

    def align(self, child_ref, parent_ref, spin=0.0):
        """Same-direction constraint: child normal aligns with parent normal.

        Unlike mate(), normals point the same way (not opposing).

        Args:
            child_ref: 'child_part.anchor_name' string.
            parent_ref: 'parent_part.anchor_name' string.
            spin: Rotation in degrees around the mating normal after alignment.
        """
        child_part, child_anchor = self._parse_ref(child_ref)
        parent_part, parent_anchor = self._parse_ref(parent_ref)
        self._constraints.append(_Constraint(
            child_part=child_part, child_anchor=child_anchor,
            parent_part=parent_part, parent_anchor=parent_anchor,
            kind="align", spin=spin,
        ))
        if child_part not in self._constraint_order:
            self._constraint_order.append(child_part)

    def add_anchor(self, part_name, anchor_name, point, normal=(0.0, 0.0, 1.0)):
        """Add a viewer-defined anchor to a part (merged at resolve time).

        Args:
            part_name: Part identifier (must be registered with add()).
            anchor_name: Name for this anchor (used in constraint refs).
            point: (x, y, z) in part local space.
            normal: (nx, ny, nz) outward direction (default +Z).
        """
        if part_name not in self._parts:
            raise ValueError(f"Unknown part '{part_name}' for viewer anchor")
        pt = (float(point[0]), float(point[1]), float(point[2]))
        nm = (float(normal[0]), float(normal[1]), float(normal[2]))
        self._viewer_anchors.setdefault(part_name, []).append(
            (anchor_name, pt, nm)
        )

    def resolve(self):
        """Build all parts, solve constraints, return pipeline-compatible manifest.

        Returns a list of dicts, each with keys: name, display, color,
        builder, args, pos, rot, meta, anchors.

        The constraint graph must form a forest (trees rooted at placed parts).
        Raises ValueError if any part is neither placed nor constrained,
        or if a cycle is detected.
        """
        # --- Step 1: Build all parts and extract anchors ---
        built_shapes = {}   # name -> CadQuery shape (local space)
        local_anchors = {}  # name -> {anchor_name: Anchor}

        for name, entry in self._parts.items():
            result = entry.builder(*entry.args)
            if isinstance(result, tuple) and len(result) == 2:
                shape, anchors = result
                if isinstance(anchors, dict):
                    local_anchors[name] = anchors
                else:
                    local_anchors[name] = {}
                built_shapes[name] = shape
            else:
                built_shapes[name] = result
                local_anchors[name] = {}

        # Merge viewer-added anchors into local_anchors
        for part_name, anchor_list in self._viewer_anchors.items():
            if part_name not in local_anchors:
                local_anchors[part_name] = {}
            for anchor_name, point, normal in anchor_list:
                local_anchors[part_name][anchor_name] = Anchor(
                    point=point, normal=normal, label=f"viewer:{anchor_name}"
                )

        # --- Step 2: Build constraint graph ---
        # Map child -> constraint (each child has at most one parent constraint)
        child_to_constraint = {}
        for c in self._constraints:
            if c.child_part in child_to_constraint:
                raise ValueError(
                    f"Part '{c.child_part}' has multiple parent constraints"
                )
            child_to_constraint[c.child_part] = c

        # --- Step 3: Resolve world transforms ---
        world_pos = {}  # name -> (x, y, z)
        world_rot = {}  # name -> (rx, ry, rz)
        world_anchors = {}  # name -> {anchor_name: Anchor in world space}

        def _resolve_anchors(name):
            """Compute world-space anchors for a resolved part."""
            anchors_w = {}
            for aname, anchor in local_anchors[name].items():
                anchors_w[aname] = transform_anchor(
                    anchor, world_pos[name], world_rot[name]
                )
            world_anchors[name] = anchors_w

        def _resolve_part(name, visited):
            """Recursively resolve a part's world transform."""
            if name in world_pos:
                return  # already resolved
            if name in visited:
                raise ValueError(f"Cycle detected involving part '{name}'")
            visited.add(name)

            if name in self._placements:
                pl = self._placements[name]
                world_pos[name] = pl.pos
                world_rot[name] = pl.rot
                _resolve_anchors(name)
                return

            if name not in child_to_constraint:
                raise ValueError(
                    f"Part '{name}' is neither placed nor constrained"
                )

            constraint = child_to_constraint[name]
            parent = constraint.parent_part

            # Ensure parent is resolved first
            _resolve_part(parent, visited)

            # Get parent's world-space anchor
            if constraint.parent_anchor not in world_anchors.get(parent, {}):
                raise ValueError(
                    f"Parent part '{parent}' has no anchor "
                    f"'{constraint.parent_anchor}'"
                )
            parent_anchor_w = world_anchors[parent][constraint.parent_anchor]

            # Get child's local anchor
            if constraint.child_anchor not in local_anchors.get(name, {}):
                raise ValueError(
                    f"Child part '{name}' has no anchor "
                    f"'{constraint.child_anchor}'"
                )
            child_anchor_local = local_anchors[name][constraint.child_anchor]

            # Compute child rotation
            opposing = constraint.kind in ("mate", "offset")
            rot_euler = rotation_to_align_normals(
                child_anchor_local.normal,
                parent_anchor_w.normal,
                opposing=opposing,
            )

            # Compute child's anchor point in rotated local space
            rot_mat = _rot_matrix_from_euler(*rot_euler)

            # Apply spin around parent normal if specified
            if abs(constraint.spin) > 1e-9:
                spin_mat = _rotation_matrix_from_axis_angle(
                    parent_anchor_w.normal, radians(constraint.spin)
                )
                rot_mat = _mat_mul(spin_mat, rot_mat)
                rot_euler = _euler_from_matrix(rot_mat)

            child_anchor_rotated = _mat_mul_vec(rot_mat, child_anchor_local.point)

            # Target point: parent anchor world position (+ offset if applicable)
            target = parent_anchor_w.point
            if constraint.kind == "offset" and abs(constraint.gap) > 1e-12:
                target = _vec_add(
                    target,
                    _vec_scale(parent_anchor_w.normal, constraint.gap),
                )

            # Child world position: target - rotated child anchor offset
            child_pos = _vec_sub(target, child_anchor_rotated)

            world_pos[name] = child_pos
            world_rot[name] = rot_euler
            _resolve_anchors(name)

        # Resolve all parts
        for name in self._parts:
            _resolve_part(name, set())

        # --- Step 4: Build manifest ---
        manifest = []
        for name, entry in self._parts.items():
            entry_dict = {
                "name": name,
                "display": entry.display,
                "color": entry.color,
                "builder": entry.builder,
                "args": entry.args,
                "pos": world_pos[name],
                "rot": world_rot[name],
                "meta": entry.meta,
                "anchors": world_anchors.get(name, {}),
            }
            manifest.append(entry_dict)

        return manifest

    def to_manifest(self):
        """Alias for resolve() — returns pipeline-compatible manifest list.

        Each entry contains: name, display, color, builder, args, pos, rot,
        meta, and anchors (world-space Anchor dict).

        The returned list can be passed directly to
        ``pipeline.export_assembly()``.
        """
        return self.resolve()
