"""Generic export pipeline for CadQuery assemblies.

Takes an assembly manifest and runs: build parts, collision check,
STL export, and viewer HTML generation.
"""

import base64
from pathlib import Path

from .exporters.stl_export import export_stl, stl_to_bytes, apply_transform, to_yup
from .assembly.collision import check_assembly_overlaps, print_overlap_report, print_bbox_summary
from .viewer.generator import generate_viewer_html


def build_assembly(manifest):
    """Build all parts from manifest, apply transforms, return positioned parts list.

    Each returned dict has: name, display, color, shape (z-up transformed),
    shape_yup (y-up for viewer), meta, pos_zup, rot_zup.
    """
    parts = []
    for entry in manifest:
        name = entry["name"]
        display = entry["display"]
        color = entry["color"]
        builder = entry["builder"]
        args = entry["args"]
        pos = entry["pos"]
        rot = entry.get("rot")
        meta = entry.get("meta", {})

        try:
            raw = builder(*args)
            # Handle builders that return (shape, anchors_dict) tuples
            if isinstance(raw, tuple) and len(raw) == 2:
                raw, builder_anchors = raw
            else:
                builder_anchors = None
            shape_zup = apply_transform(raw, pos, rot)
            shape_yup = to_yup(shape_zup)
            # Collect anchors: prefer manifest entry, fall back to builder output
            anchors = entry.get("anchors", {})
            if not anchors and builder_anchors:
                anchors = builder_anchors

            parts.append({
                "name": name,
                "display": display,
                "color": color,
                "shape": shape_zup,
                "shape_yup": shape_yup,
                "meta": meta,
                "pos_zup": pos,
                "rot_zup": rot,
                "anchors": anchors,
            })
        except Exception as e:
            print(f"  WARNING: Failed to build {name}: {e}")

    print(f"  {len(parts)} parts built")
    return parts


def export_assembly(manifest, output_dir, title="3D Model Viewer",
                    toolbar_title="3D Viewer", loading_message="Loading model...",
                    allowed_pairs=None, kicad_files=None, individual_parts=None,
                    verbose=False, constraints=None):
    """Full export pipeline: build, collision check, STL export, viewer generation.

    Args:
        manifest: list of part dicts (the assembly manifest).
        output_dir: Path to output directory.
        title/toolbar_title/loading_message: viewer customization strings.
        allowed_pairs: optional set of frozenset pairs for collision detection.
        kicad_files: optional dict of {filename: base64_content} for embedding.
        individual_parts: optional dict of {name: (builder, args)} for
            origin-position STLs (exported without assembly transforms).
        verbose: if True, print bounding box summary.
        constraints: optional list of constraint dicts with keys
            {child_part, child_anchor, parent_part, parent_anchor, kind}
            for rendering mate lines in the viewer.
    """
    output_dir = Path(output_dir)
    parts_dir = output_dir / "stl" / "parts"
    assembly_dir = output_dir / "stl" / "assembly"
    parts_dir.mkdir(parents=True, exist_ok=True)
    assembly_dir.mkdir(parents=True, exist_ok=True)

    # Export individual parts at origin (no assembly transforms)
    if individual_parts:
        print("\nExporting individual parts at origin...")
        for part_name, (builder, args) in individual_parts.items():
            result = builder(*args)
            # Handle builders returning (shape, anchors) tuples
            shape = result[0] if isinstance(result, tuple) else result
            stl_path = parts_dir / f"{part_name}.stl"
            export_stl(shape, stl_path)
            print(f"  {stl_path.name} ({stl_path.stat().st_size / 1024:.1f} KB)")

    # Build positioned assembly
    print("\nBuilding assembly...")
    parts = build_assembly(manifest)

    # Collision check
    print("\nRunning collision check...")
    overlaps = check_assembly_overlaps(parts, allowed_pairs=allowed_pairs)
    print_overlap_report(overlaps)

    if verbose:
        print_bbox_summary(parts)

    # Export positioned STLs and collect base64 data for viewer
    print("\nExporting positioned STLs...")
    viewer_parts = []
    for p in parts:
        stl_path = assembly_dir / f"{p['name']}.stl"
        export_stl(p["shape_yup"], stl_path)
        stl_bytes = stl_path.read_bytes()
        file_size = len(stl_bytes)

        print(f"  {stl_path.name} ({file_size / 1024:.1f} KB)")

        viewer_parts.append({
            "name": p["name"],
            "display": p["display"],
            "color": p["color"],
            "stl_b64": base64.b64encode(stl_bytes).decode("ascii"),
            "file_size": file_size,
            "meta": p["meta"],
            "pos_zup": list(p["pos_zup"]) if p["pos_zup"] else [0, 0, 0],
            "rot_zup": list(p["rot_zup"]) if p["rot_zup"] else [0, 0, 0],
            "anchors": [
                {"name": aname, "point": list(a.point), "normal": list(a.normal), "label": a.label}
                for aname, a in p.get("anchors", {}).items()
            ],
        })

    # Generate viewer HTML
    viewer_path = output_dir / "viewer.html"
    viewer_kwargs = dict(
        kicad_files=kicad_files,
        title=title,
        toolbar_title=toolbar_title,
        loading_message=loading_message,
    )
    if constraints is not None:
        viewer_kwargs["constraints"] = constraints
    generate_viewer_html(viewer_parts, viewer_path, **viewer_kwargs)

    # Summary
    total_kb = sum(vp["file_size"] for vp in viewer_parts) / 1024
    viewer_kb = viewer_path.stat().st_size / 1024
    print(f"\nExport complete:")
    print(f"  Parts: {len(viewer_parts)}")
    print(f"  STL total: {total_kb:.1f} KB")
    print(f"  Viewer: {viewer_path} ({viewer_kb:.1f} KB)")
    if overlaps:
        print(f"  Collisions: {len(overlaps)} overlap(s) detected")
    else:
        print(f"  Collisions: none")
