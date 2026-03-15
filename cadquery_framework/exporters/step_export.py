"""Generic STEP export module for cadquery_framework.

Exports a full assembly STEP file and optionally individual part STEP files
from a manifest list of part descriptors.
"""

from pathlib import Path
import cadquery as cq


def export_step_assembly(manifest, output_dir, assembly_name="assembly",
                         individual_parts=None, verbose=False):
    """Build cq.Assembly from manifest and export STEP files.

    Args:
        manifest: list of part dicts with keys: name, builder, args, pos, rot, color
        output_dir: Path to output directory for STEP files
        assembly_name: filename stem for the assembly STEP file
        individual_parts: optional dict of {name: (builder, args)} for
            origin-position STEPs (exported without assembly transforms)
        verbose: print dimension summary
    """
    # Build assembly from manifest
    assy = cq.Assembly()
    for entry in manifest:
        builder = entry["builder"]
        args = entry["args"]
        raw = builder(*args)
        # Handle builders returning (shape, anchors) tuples
        part = raw[0] if isinstance(raw, tuple) else raw
        pos = entry["pos"]
        rot = entry.get("rot")
        name = entry["name"]
        color_hex = entry["color"].lstrip("#")
        r = int(color_hex[0:2], 16) / 255
        g = int(color_hex[2:4], 16) / 255
        b = int(color_hex[4:6], 16) / 255

        loc_args = (pos,) if rot is None or all(abs(v) < 1e-9 for v in rot) else (pos, rot)
        assy.add(part, loc=cq.Location(*loc_args), name=name,
                 color=cq.Color(r, g, b, 1.0))

    # Export assembly
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assy_path = output_dir / f"{assembly_name}.step"
    print(f"Exporting assembly -> {assy_path}")
    assy.save(str(assy_path))

    # Export individual parts at origin
    if individual_parts:
        for name, (func, args) in individual_parts.items():
            path = output_dir / f"{name}.step"
            raw = func(*args)
            part = raw[0] if isinstance(raw, tuple) else raw
            cq.exporters.export(part, str(path))
            print(f"  {name}.step")

    print(f"Done! Files in: {output_dir}/")
