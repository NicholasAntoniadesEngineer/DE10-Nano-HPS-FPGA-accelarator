#!/usr/bin/env python3
"""
STL Exporter for Plant-Watering Drone 3D Model

Exports each individual part and the full assembly as STL files.
The assembly is rotated so drone is upright in Y-up viewers.

All dimensions sourced from cad/dimensions.json via drone_3d_model.py.

Usage:
    source .venv/bin/activate
    python drone_design/modeling/export_stl.py

Output:
    drone_design/cad/exports/*.stl
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cadquery as cq
from drone_3d_model import (
    build_assembly,
    make_skeleton_plate,
    make_arm,
    make_landing_leg,
    make_tof_board,
    make_pump_bracket,
    make_motor,
    make_propeller,
    make_esc,
    make_de10_nano,
    make_daughter_board,
    make_battery,
    make_reservoir,
    make_pump,
    make_standoff,
    make_drip_nozzle,
    make_camera,
    make_nose_boom,
    BOTTOM_THICK,
    TOP_THICK,
    DE10_STANDOFF,
)


def export_stl(shape, path, tolerance=0.01, angular_tolerance=0.1):
    """Export a CadQuery shape to STL.

    tolerance:         max linear deviation from true surface (mm)
    angular_tolerance: max angle between adjacent facet normals (degrees)
    Lower values = smoother mesh but larger file size.
    """
    cq.exporters.export(
        shape,
        str(path),
        exportType="STL",
        tolerance=tolerance,
        angularTolerance=angular_tolerance,
    )


def main():
    # All STL files land in drone_design/cad/exports/
    out_dir = Path(__file__).resolve().parent.parent / "cad" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Individual parts ──
    # Each entry maps a filename stem to (builder_function, args).
    # Builder functions come from drone_3d_model.py and return CadQuery Workplane objects.
    individual_parts = {
        "bottom_plate": (make_skeleton_plate, (BOTTOM_THICK, True)),
        "top_plate": (make_skeleton_plate, (TOP_THICK, False)),
        "arm": (make_arm, ()),
        "landing_leg": (make_landing_leg, ()),
        "tof_board": (make_tof_board, ()),
        "pump_bracket": (make_pump_bracket, ()),
        "motor": (make_motor, ()),
        "propeller": (make_propeller, ()),
        "esc": (make_esc, ()),
        "de10_nano": (make_de10_nano, ()),
        "daughter_board": (make_daughter_board, ()),
        "battery": (make_battery, ()),
        "reservoir": (make_reservoir, ()),
        "pump": (make_pump, ()),
        "standoff": (make_standoff, (DE10_STANDOFF,)),
        "drip_nozzle": (make_drip_nozzle, ()),
        "camera": (make_camera, ()),
        "nose_boom": (make_nose_boom, ()),
    }

    # Export each part independently — failures are non-fatal so one bad
    # part doesn't block the rest of the batch.
    for name, (func, args) in individual_parts.items():
        path = out_dir / f"{name}.stl"
        print(f"Exporting {name} -> {path}")
        try:
            part = func(*args)
            export_stl(part, path)
        except Exception as e:
            print(f"  WARNING: Failed to export {name}: {e}")

    # ── Full assembly as merged STL ──
    # build_assembly() positions every part at its real-world location and
    # returns a CadQuery Assembly object (parts + transforms, not yet fused).
    print("\nBuilding full assembly...")
    assy = build_assembly()

    # Merge all positioned parts into one STL so viewers can load the whole
    # drone in a single file.  The -90° X rotation converts CadQuery's Z-up
    # coordinate system to Y-up, which most STL viewers (including Three.js)
    # expect.
    print("Merging assembly into single STL...")
    merged_path = out_dir / "drone_assembly.stl"
    try:
        # Primary path: toCompound() merges the assembly tree into one OCCT shape.
        compound = assy.toCompound()
        compound = cq.Workplane("XY").add(compound).rotateAboutCenter((1, 0, 0), -90).val()
        export_stl(cq.Workplane("XY").add(compound), merged_path)
        print(f"Exported merged assembly -> {merged_path}")
    except Exception as e:
        # Fallback: if toCompound() fails (e.g. non-manifold geometry), walk
        # the assembly objects and fuse shapes one by one.  Individual fuse
        # failures are silently skipped so we get a partial result.
        print(f"  WARNING: Compound merge failed ({e}), trying shape-by-shape...")
        try:
            shapes = []
            for name_key, obj in assy.objects.items():
                if hasattr(obj, "shape"):
                    shapes.append(obj.shape)
            if shapes:
                merged = shapes[0]
                for s in shapes[1:]:
                    try:
                        merged = merged.fuse(s)
                    except Exception:
                        pass
                merged_wp = cq.Workplane("XY").add(merged).rotateAboutCenter((1, 0, 0), -90)
                export_stl(merged_wp, merged_path)
                print(f"Exported assembly (partial merge) -> {merged_path}")
        except Exception as e2:
            print(f"  ERROR: Could not export merged assembly: {e2}")

    # Summary
    stl_files = sorted(out_dir.glob("*.stl"))
    print(f"\n{'=' * 60}")
    print(f"Exported {len(stl_files)} STL files to: {out_dir}/")
    print(f"{'=' * 60}")
    for f in stl_files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:30s} ({size_kb:7.1f} KB)")
    print(f"\nOpen viewer.html in a browser to view interactively.")


if __name__ == "__main__":
    main()
