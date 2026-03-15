"""Generate a CadQuery component module for a viewer-created (new) part.

Used when overlay contains new_parts: each entry becomes a Python file under
project_dir/components/custom/<name>.py that builds the shape and returns anchors.
"""

from pathlib import Path


def _sanitize_name(name):
    """Return a valid Python identifier for use in module and function names."""
    s = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    return s or "custom_part"


def generate_custom_part_module(project_dir, new_part, overwrite=False):
    """Generate components/custom/<name>.py for a new part from overlay.

    Args:
        project_dir: Path to the project (e.g. drone_design/drone_model).
        new_part: Dict with name, display, geometry (type, size or r/h, pos, rot), meta (optional).
        overwrite: If False, do not overwrite an existing file.

    Returns:
        Path to the generated file, or None if skipped (e.g. exists and not overwrite).
    """
    project_dir = Path(project_dir)
    custom_dir = project_dir / "components" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    name = (new_part.get("name") or "custom_part").strip()
    if not name:
        return None
    safe_name = _sanitize_name(name)
    display = (new_part.get("display") or name).strip()
    geometry = new_part.get("geometry") or {}
    geo_type = geometry.get("type", "box")
    pos = geometry.get("pos", [0, 0, 0])
    rot = geometry.get("rot", [0, 0, 0])
    if len(pos) != 3:
        pos = [0, 0, 0]
    if len(rot) != 3:
        rot = [0, 0, 0]

    out_path = custom_dir / f"{safe_name}.py"
    if out_path.exists() and not overwrite:
        return out_path

    if geo_type == "cylinder":
        r = float(geometry.get("r", 5))
        h = float(geometry.get("h", 10))
        body = f'    shape = cq.Workplane("XY").cylinder({h}, {r}, centered=(True, True, True))'
    else:
        size = geometry.get("size", [10, 10, 10])
        if len(size) != 3:
            size = [10, 10, 10]
        wx, wy, wz = float(size[0]), float(size[1]), float(size[2])
        body = f'    shape = cq.Workplane("XY").box({wx}, {wy}, {wz}, centered=(True, True, True))'

    func_name = f"make_{safe_name}"

    source = f'''"""Generated custom part: {display}."""

import cadquery as cq

from cadquery_framework.assembly.anchors import Anchor


def {func_name}():
    """Build the custom part (from viewer overlay)."""
{body}
    anchors = {{
        "mount": Anchor(point=(0, 0, 0), normal=(0, 0, 1), label="Default mount"),
    }}
    return shape, anchors
'''
    out_path.write_text(source, encoding="utf-8")
    return out_path
