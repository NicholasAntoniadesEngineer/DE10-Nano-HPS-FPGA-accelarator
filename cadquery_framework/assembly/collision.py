"""Axis-Aligned Bounding Box (AABB) collision detection for CadQuery assemblies.

Computes bounding boxes for each positioned part and checks all pairwise
intersections. Reports any significant overlaps (> threshold volume).

Usage:
    from cadquery_framework.assembly.collision import check_assembly_overlaps
    overlaps = check_assembly_overlaps(positioned_parts, allowed_pairs=my_pairs)
"""


def compute_aabb(shape):
    """Compute axis-aligned bounding box of a CadQuery shape.

    Returns dict with 'min' and 'max' tuples (x, y, z).
    """
    bb = shape.val().BoundingBox()
    return {
        "min": (bb.xmin, bb.ymin, bb.zmin),
        "max": (bb.xmax, bb.ymax, bb.zmax),
    }


def aabb_overlap(a, b):
    """Check if two AABBs overlap.

    Returns overlap dimensions (dx, dy, dz) or None if no overlap.
    """
    overlap = []
    for i in range(3):
        lo = max(a["min"][i], b["min"][i])
        hi = min(a["max"][i], b["max"][i])
        if lo >= hi:
            return None
        overlap.append(hi - lo)
    return tuple(overlap)


def aabb_volume(dims):
    """Volume of an overlap region."""
    return dims[0] * dims[1] * dims[2]


def aabb_size(aabb):
    """Size of a bounding box (dx, dy, dz)."""
    return tuple(aabb["max"][i] - aabb["min"][i] for i in range(3))


def aabb_center(aabb):
    """Center point of a bounding box."""
    return tuple((aabb["min"][i] + aabb["max"][i]) / 2 for i in range(3))


def _mesh_intersects(shape_a, shape_b):
    """Check if two CadQuery shapes actually intersect at the mesh level.

    Returns True only if the boolean intersection has non-trivial volume.
    This catches AABB false positives (e.g. circular prop disc boxed into
    a rectangle appearing to overlap a nearby standoff).
    """
    try:
        intersection = shape_a.intersect(shape_b)
        bb = intersection.val().BoundingBox()
        vol = (bb.xmax - bb.xmin) * (bb.ymax - bb.ymin) * (bb.zmax - bb.zmin)
        return vol > 1.0  # > 1mm³ real intersection
    except Exception:
        # "Bnd_Box is void" = empty intersection = no real collision
        return False


def check_assembly_overlaps(parts, volume_threshold=10.0, allowed_pairs=None,
                            verify_mesh=True):
    """Check all pairwise AABB overlaps between positioned parts.

    Args:
        parts: list of dicts with 'name' and 'shape' keys.
               'shape' is a positioned CadQuery shape (after apply_transform,
               before to_yup).
        volume_threshold: minimum overlap volume (mm^3) to report.
        allowed_pairs: optional set of frozenset pairs to skip (intentional overlaps).
        verify_mesh: if True, AABB overlaps are verified with actual mesh
            boolean intersection to eliminate false positives from axis-aligned
            bounding boxes (e.g. circular props boxed into rectangles).

    Returns:
        list of dicts with overlap details, sorted by volume descending.
    """
    if allowed_pairs is None:
        allowed_pairs = set()

    part_bboxes = []
    parts_by_name = {}
    for p in parts:
        try:
            aabb = compute_aabb(p["shape"])
            part_bboxes.append({"name": p["name"], "aabb": aabb})
            parts_by_name[p["name"]] = p
        except Exception as e:
            print(f"  AABB warning: {p['name']}: {e}")

    aabb_hits = 0
    mesh_filtered = 0
    allowed_skipped = 0
    near_misses = []
    overlaps = []
    n = len(part_bboxes)
    for i in range(n):
        for j in range(i + 1, n):
            pair = frozenset({part_bboxes[i]["name"], part_bboxes[j]["name"]})
            if pair in allowed_pairs:
                # Still compute overlap for diagnostics
                dims = aabb_overlap(part_bboxes[i]["aabb"], part_bboxes[j]["aabb"])
                if dims and aabb_volume(dims) >= volume_threshold:
                    allowed_skipped += 1
                continue

            dims = aabb_overlap(part_bboxes[i]["aabb"], part_bboxes[j]["aabb"])
            if dims is None:
                # Check near-miss (gap < 3mm on all axes)
                gap = _min_gap(part_bboxes[i]["aabb"], part_bboxes[j]["aabb"])
                if gap is not None and gap < 3.0:
                    near_misses.append({
                        "part_a": part_bboxes[i]["name"],
                        "part_b": part_bboxes[j]["name"],
                        "gap_mm": gap,
                    })
                continue

            vol = aabb_volume(dims)
            if vol < volume_threshold:
                continue

            aabb_hits += 1

            # Verify with actual mesh intersection to eliminate AABB false positives
            if verify_mesh:
                name_a = part_bboxes[i]["name"]
                name_b = part_bboxes[j]["name"]
                shape_a = parts_by_name[name_a]["shape"]
                shape_b = parts_by_name[name_b]["shape"]
                if not _mesh_intersects(shape_a, shape_b):
                    mesh_filtered += 1
                    continue

            overlaps.append({
                "part_a": part_bboxes[i]["name"],
                "part_b": part_bboxes[j]["name"],
                "overlap_dims_mm": dims,
                "volume_mm3": vol,
                "aabb_a": part_bboxes[i]["aabb"],
                "aabb_b": part_bboxes[j]["aabb"],
            })

    if verify_mesh and (mesh_filtered > 0 or aabb_hits > 0):
        print(f"  Mesh verification: {aabb_hits} AABB hits, "
              f"{mesh_filtered} filtered as false positives, "
              f"{len(overlaps)} confirmed real")
    if allowed_skipped > 0:
        print(f"  Allowed-pair overlaps skipped: {allowed_skipped}")
    if near_misses:
        print(f"  Near-misses (gap < 3mm): {len(near_misses)}")
        for nm in sorted(near_misses, key=lambda x: x["gap_mm"])[:5]:
            print(f"    {nm['part_a']} <-> {nm['part_b']}: "
                  f"{nm['gap_mm']:.1f}mm gap")

    overlaps.sort(key=lambda x: x["volume_mm3"], reverse=True)
    return overlaps


def _min_gap(a, b):
    """Minimum axis-aligned gap between two non-overlapping AABBs.

    Returns None if they overlap on all axes, otherwise the smallest
    positive gap across any axis.
    """
    gaps = []
    for i in range(3):
        if a["max"][i] < b["min"][i]:
            gaps.append(b["min"][i] - a["max"][i])
        elif b["max"][i] < a["min"][i]:
            gaps.append(a["min"][i] - b["max"][i])
    return min(gaps) if gaps else None


def _axis_label(axis_idx):
    return "XYZ"[axis_idx]


def _penetration_analysis(a, b):
    """Determine which axis has the smallest penetration (easiest fix)."""
    axes = []
    for i in range(3):
        lo = max(a["min"][i], b["min"][i])
        hi = min(a["max"][i], b["max"][i])
        if lo < hi:
            axes.append((_axis_label(i), hi - lo))
    axes.sort(key=lambda x: x[1])
    return axes


def _separation_needed(a, b, gap=1.0):
    """For each axis, compute how much one part needs to move to clear."""
    fixes = []
    for i in range(3):
        lo = max(a["min"][i], b["min"][i])
        hi = min(a["max"][i], b["max"][i])
        if lo < hi:
            move = hi - lo + gap
            axis = _axis_label(i)
            # Which direction to move part_b
            a_center = (a["min"][i] + a["max"][i]) / 2
            b_center = (b["min"][i] + b["max"][i]) / 2
            direction = "+" if b_center >= a_center else "-"
            fixes.append((axis, move, direction))
    return fixes


def print_overlap_report(overlaps):
    """Print a detailed overlap report with geometry analysis and fix suggestions."""
    if not overlaps:
        print("\n  COLLISION CHECK: No significant overlaps detected.")
        return

    print(f"\n  COLLISION CHECK: {len(overlaps)} overlap(s) detected!")
    print("  " + "=" * 100)
    for idx, o in enumerate(overlaps, 1):
        dx, dy, dz = o["overlap_dims_mm"]
        vol = o["volume_mm3"]
        severity = "CRITICAL" if vol > 1000 else "WARNING" if vol > 100 else "minor"
        a, b = o["aabb_a"], o["aabb_b"]

        # Part sizes
        a_size = aabb_size(a)
        b_size = aabb_size(b)
        a_center = aabb_center(a)
        b_center = aabb_center(b)

        # Overlap region
        ox_lo = max(a["min"][0], b["min"][0])
        ox_hi = min(a["max"][0], b["max"][0])
        oy_lo = max(a["min"][1], b["min"][1])
        oy_hi = min(a["max"][1], b["max"][1])
        oz_lo = max(a["min"][2], b["min"][2])
        oz_hi = min(a["max"][2], b["max"][2])

        # Penetration analysis
        pen = _penetration_analysis(a, b)
        fixes = _separation_needed(a, b, gap=1.0)

        print(f"\n  [{idx}/{len(overlaps)}] [{severity}] {o['part_a']} <-> {o['part_b']}")
        print(f"  {'─' * 98}")

        # Overlap details
        print(f"    Overlap size:   {dx:.1f} x {dy:.1f} x {dz:.1f} mm  "
              f"(volume: {vol:.0f} mm³)")
        print(f"    Overlap region: X[{ox_lo:.1f}, {ox_hi:.1f}]  "
              f"Y[{oy_lo:.1f}, {oy_hi:.1f}]  "
              f"Z[{oz_lo:.1f}, {oz_hi:.1f}]")
        print(f"    Overlap center: ({(ox_lo+ox_hi)/2:.1f}, "
              f"{(oy_lo+oy_hi)/2:.1f}, {(oz_lo+oz_hi)/2:.1f})")

        # Part A details
        print(f"    {o['part_a']}:")
        print(f"      AABB:   X[{a['min'][0]:.1f}, {a['max'][0]:.1f}]  "
              f"Y[{a['min'][1]:.1f}, {a['max'][1]:.1f}]  "
              f"Z[{a['min'][2]:.1f}, {a['max'][2]:.1f}]")
        print(f"      Size:   {a_size[0]:.1f} x {a_size[1]:.1f} x {a_size[2]:.1f} mm  "
              f"Center: ({a_center[0]:.1f}, {a_center[1]:.1f}, {a_center[2]:.1f})")

        # Part B details
        print(f"    {o['part_b']}:")
        print(f"      AABB:   X[{b['min'][0]:.1f}, {b['max'][0]:.1f}]  "
              f"Y[{b['min'][1]:.1f}, {b['max'][1]:.1f}]  "
              f"Z[{b['min'][2]:.1f}, {b['max'][2]:.1f}]")
        print(f"      Size:   {b_size[0]:.1f} x {b_size[1]:.1f} x {b_size[2]:.1f} mm  "
              f"Center: ({b_center[0]:.1f}, {b_center[1]:.1f}, {b_center[2]:.1f})")

        # Penetration per axis
        print(f"    Penetration depth per axis:")
        for axis, depth in pen:
            pct_a = depth / a_size["XYZ".index(axis)] * 100 if a_size["XYZ".index(axis)] > 0 else 0
            pct_b = depth / b_size["XYZ".index(axis)] * 100 if b_size["XYZ".index(axis)] > 0 else 0
            print(f"      {axis}: {depth:.1f} mm  "
                  f"({pct_a:.0f}% of {o['part_a']}, "
                  f"{pct_b:.0f}% of {o['part_b']})")

        # Fix suggestion
        easiest = pen[0]  # smallest penetration = easiest to fix
        fix = fixes[0] if fixes else None
        if fix:
            print(f"    Suggested fix: move {o['part_b']} by {fix[2]}{fix[1]:.1f} mm "
                  f"in {fix[0]} (smallest penetration axis)")

    print("\n  " + "=" * 100)
    total_vol = sum(o["volume_mm3"] for o in overlaps)
    print(f"  TOTAL: {len(overlaps)} collision(s), "
          f"{total_vol:.0f} mm³ total overlap volume")
    print("  " + "=" * 100)


def print_bbox_summary(parts):
    """Print bounding box summary for all parts (debug aid)."""
    print("\n  BOUNDING BOX SUMMARY:")
    print(f"  {'Part':<30} {'X range':>20} {'Y range':>20} {'Z range':>20}")
    print("  " + "-" * 92)
    for p in parts:
        try:
            aabb = compute_aabb(p["shape"])
            xr = f"[{aabb['min'][0]:6.1f}, {aabb['max'][0]:6.1f}]"
            yr = f"[{aabb['min'][1]:6.1f}, {aabb['max'][1]:6.1f}]"
            zr = f"[{aabb['min'][2]:6.1f}, {aabb['max'][2]:6.1f}]"
            print(f"  {p['name']:<30} {xr:>20} {yr:>20} {zr:>20}")
        except Exception:
            print(f"  {p['name']:<30} (failed to compute)")
