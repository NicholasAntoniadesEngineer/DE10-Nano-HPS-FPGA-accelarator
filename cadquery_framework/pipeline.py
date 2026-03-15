"""Generic export pipeline for CadQuery assemblies.

Takes an assembly manifest and runs: build parts, collision check,
STL export, and viewer HTML generation.

Viewer edits can be persisted: save configuration from the viewer as
model_configuration.json in the output directory; the next build will
apply those position/rotation overrides so the exported assembly
matches the edited layout.
"""

import base64
import json
from pathlib import Path

from .exporters.stl_export import export_stl, stl_to_bytes, apply_transform, to_yup
from .assembly.collision import check_assembly_overlaps, print_overlap_report, print_bbox_summary
from .viewer.generator import generate_viewer_html
from .viewer.overlay import load_overlay
from .modifiers import apply_op

CONFIG_FILENAME = "model_configuration.json"


def _viewer_pos_to_zup(viewer_pos):
    """Convert viewer (Y-up) position [x, y, z] to pipeline (Z-up) [x, -z, y]."""
    if not viewer_pos or len(viewer_pos) != 3:
        return None
    return [float(viewer_pos[0]), float(-viewer_pos[2]), float(viewer_pos[1])]


def _load_viewer_overrides(output_dir):
    """Load position/rotation overrides from viewer_overlay.json or model_configuration.json.

    Prefers viewer_overlay.json "parts" when present; otherwise falls back to
    model_configuration.json for backward compatibility.

    Returns a dict part_name -> {"pos": [x,y,z] z-up, "rot": [rx,ry,rz] degrees}
    or {} if no file or invalid.
    """
    overlay = load_overlay(Path(output_dir))
    if overlay.get("parts"):
        overrides = {}
        for name, p in overlay["parts"].items():
            if "position" in p and len(p["position"]) == 3:
                overrides.setdefault(name, {})["pos"] = p["position"]
            if "rotation" in p and len(p["rotation"]) == 3:
                overrides.setdefault(name, {})["rot"] = p["rotation"]
        return overrides
    path = Path(output_dir) / CONFIG_FILENAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    parts_list = data.get("parts")
    if not parts_list or not isinstance(parts_list, list):
        return {}
    overrides = {}
    for cp in parts_list:
        name = cp.get("name")
        if not name:
            continue
        pos_zup = _viewer_pos_to_zup(cp.get("position"))
        rot = cp.get("rotation")
        if pos_zup is not None:
            overrides.setdefault(name, {})["pos"] = pos_zup
        if rot and len(rot) == 3:
            overrides.setdefault(name, {})["rot"] = [
                float(rot[0]), float(rot[1]), float(rot[2]),
            ]
    return overrides


def build_assembly(manifest, overlay_modifications=None):
    """Build all parts from manifest, apply transforms, return positioned parts list.

    Each returned dict has: name, display, color, shape (z-up transformed),
    shape_yup (y-up for viewer), meta, pos_zup, rot_zup.

    If overlay_modifications is a dict part_name -> list of op dicts, each op
    is applied in order to the raw shape (in part local space) before transform.
    """
    parts = []
    mods = overlay_modifications or {}
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
            for op in mods.get(name, []):
                raw = apply_op(raw, op)
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


def _derive_connected_pairs(constraints):
    """Derive pairs of directly constrained parts from constraint metadata.

    Parts connected by mate/offset/align constraints are physically mating —
    AABB overlap between them is expected and should not trigger collision
    errors.  This is standard CAD behaviour (SolidWorks, Fusion 360, etc.).
    """
    pairs = set()
    if not constraints:
        return pairs
    for c in constraints:
        pairs.add(frozenset({c["child_part"], c["parent_part"]}))
    return pairs


def _derive_exclude_names(manifest):
    """Return set of part names that should be excluded from collision checks.

    Parts flagged with ``no_collision=True`` (e.g. visualization-only
    clearance volumes) are not physical and must never participate in
    collision detection.
    """
    return {e["name"] for e in manifest if e.get("no_collision")}


def export_assembly(manifest, output_dir, title="3D Model Viewer",
                    toolbar_title="3D Viewer", loading_message="Loading model...",
                    allowed_pairs=None, kicad_files=None, individual_parts=None,
                    verbose=False, constraints=None, validation=None):
    """Full export pipeline: build, collision check, STL export, viewer generation.

    Collision check is blocking: if any overlaps remain (after filtering)
    RuntimeError is raised and STL/viewer export is not performed.

    Automatically excluded from collision detection:
    - Pairs of parts that are directly constrained together (mate/offset/align)
      — these are physically mating surfaces, not collisions.
    - Parts flagged with ``no_collision=True`` in the manifest (e.g.
      visualization-only clearance volumes).

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
        validation: optional dict from manifest build (e.g. overlay_constraints_skipped).
    """
    output_dir = Path(output_dir)
    parts_dir = output_dir / "stl" / "parts"
    assembly_dir = output_dir / "stl" / "assembly"
    parts_dir.mkdir(parents=True, exist_ok=True)
    assembly_dir.mkdir(parents=True, exist_ok=True)

    overlay = load_overlay(output_dir)
    overrides = {}
    if overlay.get("parts"):
        for name, p in overlay["parts"].items():
            overrides[name] = {}
            if "position" in p and len(p["position"]) == 3:
                overrides[name]["pos"] = p["position"]
            if "rotation" in p and len(p["rotation"]) == 3:
                overrides[name]["rot"] = p["rotation"]
    if not overrides:
        overrides = _load_viewer_overrides(output_dir)
    if overrides:
        for entry in manifest:
            name = entry.get("name")
            if name not in overrides:
                continue
            o = overrides[name]
            if "pos" in o:
                entry["pos"] = tuple(o["pos"])
            if "rot" in o:
                entry["rot"] = tuple(o["rot"])
        print(f"  Applied viewer overrides for {len(overrides)} part(s)")
    overlay_modifications = overlay.get("modifications")

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
    parts = build_assembly(manifest, overlay_modifications=overlay_modifications)

    # Collision check (blocking: pipeline fails if any overlaps remain)
    # Only exclusion: directly constrained mating pairs (surface contact is
    # expected at bolted/mated joints — standard CAD behaviour).
    # No allowed_pairs, no no_collision flags.
    print("\nRunning collision check...")

    connected = _derive_connected_pairs(constraints)
    if connected:
        print(f"  Auto-excluded: {len(connected)} constrained mating pairs")

    overlaps = check_assembly_overlaps(parts, allowed_pairs=connected)
    print_overlap_report(overlaps)
    if overlaps:
        raise RuntimeError(
            f"Collision check failed: {len(overlaps)} overlap(s) detected. "
            "Fix assembly or add allowed pairs; export aborted."
        )

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
    skipped = (validation or {}).get("overlay_constraints_skipped", [])
    build_result = {
        "success": True,
        "parts": len(viewer_parts),
        "collisions": len(overlaps) if overlaps else 0,
        "overlay_constraints_skipped": len(skipped),
        "message": "Export complete.",
    }
    if skipped:
        build_result["message"] = "Export complete. {} overlay constraint(s) skipped.".format(len(skipped))
    viewer_kwargs = dict(
        kicad_files=kicad_files,
        title=title,
        toolbar_title=toolbar_title,
        loading_message=loading_message,
        build_result=build_result,
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


def _run_drone_model():
    """Run drone model export when pipeline is invoked with drone_design/drone_model path."""
    import sys
    repo_root = Path(__file__).resolve().parents[1]
    project_dir = repo_root / "drone_design" / "drone_model"
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(project_dir))
    from drone_3d_model import main
    main()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m cadquery_framework.pipeline <project_path>")
        print("  Example: python -m cadquery_framework.pipeline drone_design/drone_model")
        sys.exit(1)
    arg = Path(sys.argv[1]).resolve()
    repo = Path(__file__).resolve().parents[1]
    if "drone_model" in str(arg) or (repo / "drone_design" / "drone_model").resolve() == arg:
        _run_drone_model()
    else:
        print("Unknown project path. Supported: drone_design/drone_model")
        sys.exit(1)
