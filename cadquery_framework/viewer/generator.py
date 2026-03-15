"""Viewer HTML generator — reads native CSS/HTML/JS source files, injects
runtime data, and writes a single self-contained HTML file."""

import json
from pathlib import Path

_VIEWER_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _VIEWER_DIR / "static"


def generate_viewer_html(parts_data, output_path, kicad_files=None,
                         constraints=None,
                         title="3D Model Viewer", toolbar_title="3D Viewer",
                         loading_message="Loading model...",
                         build_result=None):
    """Generate self-contained viewer.html with embedded STL data.

    Reads template.html, style.css, and app.js from the viewer static
    directory (viewer/static/), inlines them, injects the provided data
    as JSON, and writes one portable HTML file to *output_path*.

    Args:
        parts_data: list of dicts with keys name, display, color,
            stl_b64, file_size, meta, anchors (optional), pos_zup, rot_zup.
        output_path: Path where the HTML file will be written.
        kicad_files: optional dict {filename: base64_content}.
        constraints: optional list of constraint dicts with keys
            child_part, child_anchor, parent_part, parent_anchor, kind.
        title: HTML page title.
        toolbar_title: text shown in the toolbar header.
        loading_message: text shown while parts are loading.
    """
    template_text = (_STATIC_DIR / "template.html").read_text(encoding="utf-8")
    css_text = (_STATIC_DIR / "style.css").read_text(encoding="utf-8")
    js_text = (_STATIC_DIR / "app.js").read_text(encoding="utf-8")

    parts_json = json.dumps([{
        "name": part["name"],
        "display": part["display"],
        "color": part["color"],
        "size": part["file_size"],
        "stl": part["stl_b64"],
        "meta": part.get("meta", {}),
        "pos_zup": part.get("pos_zup", [0, 0, 0]),
        "rot_zup": part.get("rot_zup", [0, 0, 0]),
        "anchors": part.get("anchors", []),
    } for part in parts_data], indent=None)

    kicad_json = json.dumps(kicad_files or {}, indent=None)
    constraints_json = json.dumps(constraints or [], indent=None)
    build_result_json = json.dumps(build_result or {}, indent=None)

    html = template_text
    html = html.replace("<!-- __INLINE_CSS__ -->", "<style>\n" + css_text + "\n</style>")
    html = html.replace("<!-- __INLINE_JS__ -->", "<script type=\"module\">\n" + js_text + "\n</script>")
    html = html.replace("__PAGE_TITLE__", title)
    html = html.replace("__TOOLBAR_TITLE__", toolbar_title)
    html = html.replace("__LOADING_MESSAGE__", loading_message)
    html = html.replace('"__PARTS_JSON__"', parts_json)
    html = html.replace('"__KICAD_JSON__"', kicad_json)
    html = html.replace('"__CONSTRAINTS_JSON__"', constraints_json)
    html = html.replace('"__BUILD_RESULT_JSON__"', build_result_json)

    output_path = Path(output_path)
    output_path.write_text(html, encoding="utf-8")
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Generated viewer.html ({size_mb:.1f} MB)")
