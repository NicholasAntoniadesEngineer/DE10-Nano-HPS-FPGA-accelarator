"""STL export utilities and coordinate transforms for CadQuery shapes."""

import tempfile
from pathlib import Path

import cadquery as cq


def export_stl(shape, path, tolerance=0.01, angular_tolerance=0.1):
    """Export a CadQuery shape to STL."""
    cq.exporters.export(
        shape, str(path), exportType="STL",
        tolerance=tolerance, angularTolerance=angular_tolerance,
    )


def stl_to_bytes(shape, tolerance=0.01, angular_tolerance=0.1):
    """Export a CadQuery shape to STL bytes (in memory)."""
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=True) as f:
        export_stl(shape, f.name, tolerance, angular_tolerance)
        f.seek(0)
        return Path(f.name).read_bytes()


def apply_transform(shape, pos, rot=None):
    """Apply rotation then translation to a CadQuery shape.

    rot is (rx, ry, rz) in degrees, matching cq.Location intrinsic XYZ Euler.
    In extrinsic (world axis) order: Z, then Y, then X.
    """
    if rot:
        rx, ry, rz = rot
        if rz:
            shape = shape.rotate((0, 0, 0), (0, 0, 1), rz)
        if ry:
            shape = shape.rotate((0, 0, 0), (0, 1, 0), ry)
        if rx:
            shape = shape.rotate((0, 0, 0), (1, 0, 0), rx)
    shape = shape.translate(pos)
    return shape


def to_yup(shape):
    """Rotate from CadQuery Z-up to Three.js Y-up (-90 deg about X)."""
    return shape.rotate((0, 0, 0), (1, 0, 0), -90)
