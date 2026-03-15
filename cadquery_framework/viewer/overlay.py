"""Viewer overlay schema and loader.

Single overlay file (viewer_overlay.json) in the project output directory
holds: position/rotation overrides per part, viewer-added anchors per part,
viewer-added constraints, parametric modifications per part, and new parts.

Build applies overlay after core assembly: merge anchors, add constraints,
apply position overrides; pipeline may apply modifications when building shapes.
"""

from pathlib import Path
import json

OVERLAY_FILENAME = "viewer_overlay.json"


def _viewer_pos_to_zup(viewer_pos):
    """Convert viewer (Y-up) position [x, y, z] to pipeline (Z-up) [x, -z, y]."""
    if not viewer_pos or len(viewer_pos) != 3:
        return None
    return (
        float(viewer_pos[0]),
        float(-viewer_pos[2]),
        float(viewer_pos[1]),
    )


def load_overlay(output_dir):
    """Load viewer_overlay.json from output_dir if present.

    Returns a dict with optional keys:
      - parts: dict part_name -> { "position": [x,y,z] z-up, "rotation": [rx,ry,rz] deg }
      - anchors: dict part_name -> [ { "name", "point": [x,y,z], "normal": [nx,ny,nz] } ]
      - constraints: [ { "child_part", "child_anchor", "parent_part", "parent_anchor", "kind", "gap"? } ]
      - modifications: dict part_name -> [ { "id", "type", "pos", "size" or "r"/"h", "rot_deg"? } ]
      - new_parts: [ { "name", "display", "geometry", "anchors"? } ]

    Position in overlay is stored in viewer (Y-up); we convert to Z-up for "parts".
    Returns {} if file missing or invalid.
    """
    path = Path(output_dir) / OVERLAY_FILENAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}

    result = {}
    # parts: normalize to z-up and dict by part name
    parts_raw = data.get("parts")
    if isinstance(parts_raw, dict):
        result["parts"] = {}
        for name, p in parts_raw.items():
            pos_zup = _viewer_pos_to_zup(p.get("position"))
            rot = p.get("rotation")
            result["parts"][name] = {}
            if pos_zup is not None:
                result["parts"][name]["position"] = list(pos_zup)
            if rot and len(rot) == 3:
                result["parts"][name]["rotation"] = [float(rot[0]), float(rot[1]), float(rot[2])]
    elif isinstance(parts_raw, list):
        result["parts"] = {}
        for p in parts_raw:
            name = p.get("name")
            if not name:
                continue
            pos_zup = _viewer_pos_to_zup(p.get("position"))
            rot = p.get("rotation")
            result["parts"][name] = {}
            if pos_zup is not None:
                result["parts"][name]["position"] = list(pos_zup)
            if rot and len(rot) == 3:
                result["parts"][name]["rotation"] = [float(rot[0]), float(rot[1]), float(rot[2])]

    if "anchors" in data and isinstance(data["anchors"], dict):
        result["anchors"] = data["anchors"]
    if "constraints" in data and isinstance(data["constraints"], list):
        result["constraints"] = data["constraints"]
    if "modifications" in data and isinstance(data["modifications"], dict):
        result["modifications"] = data["modifications"]
    if "new_parts" in data and isinstance(data["new_parts"], list):
        result["new_parts"] = data["new_parts"]

    return result
