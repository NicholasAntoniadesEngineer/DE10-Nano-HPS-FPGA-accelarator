#!/usr/bin/env python3
"""
STL Exporter for Plant-Watering Drone 3D Model

Exports:
  1. Individual parts at origin (for CNC / 3D printing)
  2. Positioned parts in assembly layout (for interactive viewer)
  3. Self-contained viewer.html with all positioned STLs embedded as base64

All dimensions sourced from cad/dimensions.json via drone_3d_model.py.

Usage:
    source .venv/bin/activate
    python drone_design/modeling/export_stl.py

Output:
    drone_design/cad/exports/*.stl           (individual parts at origin)
    drone_design/cad/exports/assembly/*.stl   (positioned parts)
    drone_design/cad/exports/viewer.html      (self-contained 3D viewer)
"""

import sys
import json
import math
import base64
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cadquery as cq
from drone_3d_model import (
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
    # Constants
    BOTTOM_THICK, TOP_THICK, DE10_STANDOFF,
    PLATE_SIZE,
    MOTOR_R, ARM_LENGTH, ARM_TAB, ARM_THICK, ARM_ANGLES,
    MOTOR_TOTAL_H, ESC_H, ESC_RADIAL_FRAC,
    LEG_ANGLES,
    DE10_W, DE10_L,
    BATT_H, BATT_CG_OFFSET,
    RES_H, RES_OFFSET_X,
    PUMP_W, PUMP_BRACKET_H, PUMP_BRACKET_T,
    BOOM_LENGTH, BOOM_THICK,
    TOF_H, TOF_L,
    GROUND_Z, BOTTOM_Z, TOP_Z, DE10_Z, DB_Z, ARM_CENTER_Z,
)


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


def build_positioned_parts():
    """Build all assembly parts at their positioned locations.

    Returns list of dicts: {name, display, color_hex, shape (Z-up), shape_yup (Y-up)}
    """
    parts = []

    def add(name, display, color_hex, builder, args, pos, rot=None):
        try:
            shape = builder(*args)
            shape = apply_transform(shape, pos, rot)
            shape_yup = to_yup(shape)
            parts.append({
                "name": name,
                "display": display,
                "color": color_hex,
                "shape": shape,
                "shape_yup": shape_yup,
            })
        except Exception as e:
            print(f"  WARNING: Failed {name}: {e}")

    # ── Plates ──
    add("bottom_plate", "Bottom Plate (FR4 2.0mm)", "#B87333",
        make_skeleton_plate, (BOTTOM_THICK, True), (0, 0, BOTTOM_Z))
    add("top_plate", "Top Plate (FR4 1.6mm)", "#1A7326",
        make_skeleton_plate, (TOP_THICK, False), (0, 0, TOP_Z))

    # ── Arms (4x) ──
    arm_offset = ARM_LENGTH / 2 - ARM_TAB / 2
    for i, angle in enumerate(ARM_ANGLES):
        rad = math.radians(angle)
        cx = arm_offset * math.cos(rad)
        cy = arm_offset * math.sin(rad)
        add(f"arm_{i+1}", f"Arm {i+1} (FR4 I-beam)", "#B87333",
            make_arm, (), (cx, cy, ARM_CENTER_Z - ARM_THICK / 2), (0, 0, angle))

    # ── Motors + Propellers + ESCs (4x each) ──
    for i, angle in enumerate(ARM_ANGLES):
        rad = math.radians(angle)
        mx = MOTOR_R * math.cos(rad)
        my = MOTOR_R * math.sin(rad)
        motor_z = ARM_CENTER_Z + ARM_THICK / 2

        add(f"motor_{i+1}", f"Motor {i+1} (X2212)", "#333333",
            make_motor, (), (mx, my, motor_z))

        add(f"prop_{i+1}", f"Propeller {i+1} (1045)", "#262626",
            make_propeller, (), (mx, my, motor_z + MOTOR_TOTAL_H), (0, 0, angle + 30))

        esc_r = MOTOR_R * ESC_RADIAL_FRAC
        ex = esc_r * math.cos(rad)
        ey = esc_r * math.sin(rad)
        add(f"esc_{i+1}", f"ESC {i+1} (30A)", "#1A1A1A",
            make_esc, (), (ex, ey, ARM_CENTER_Z - ARM_THICK / 2 - ESC_H), (0, 0, angle))

    # ── Landing Gear (4x) ──
    for i, angle in enumerate(LEG_ANGLES):
        rad = math.radians(angle)
        lx = (PLATE_SIZE / 2 + 2) * math.cos(rad)
        ly = (PLATE_SIZE / 2 + 2) * math.sin(rad)
        add(f"leg_{i+1}", f"Landing Leg {i+1}", "#155A1F",
            make_landing_leg, (), (lx, ly, GROUND_Z), (0, 0, angle))

    # ── DE10-Nano ──
    add("de10_nano", "DE10-Nano FPGA Board", "#004D99",
        make_de10_nano, (), (0, 0, DE10_Z))

    # ── Standoffs (4x) ──
    for j, (dx, dy) in enumerate([
        (-DE10_W / 2 + 4, -DE10_L / 2 + 4),
        (-DE10_W / 2 + 4, DE10_L / 2 - 4),
        (DE10_W / 2 - 4, -DE10_L / 2 + 4),
        (DE10_W / 2 - 4, DE10_L / 2 - 4),
    ]):
        add(f"standoff_{j+1}", f"Standoff {j+1} (M2.5)", "#BFBFC7",
            make_standoff, (DE10_STANDOFF,), (dx, dy, BOTTOM_Z + BOTTOM_THICK))

    # ── Daughter Board ──
    add("daughter_board", "Daughter Board", "#801A1A",
        make_daughter_board, (), (0, 0, DB_Z))

    # ── Battery ──
    add("battery", "Battery (4S 2200mAh)", "#262626",
        make_battery, (), (BATT_CG_OFFSET, 0, BOTTOM_Z - BATT_H - 3))

    # ── Reservoir ──
    add("reservoir", "Water Reservoir (300ml)", "#4D99E6",
        make_reservoir, (), (RES_OFFSET_X, 0, BOTTOM_Z - RES_H - 3))

    # ── Pump bracket + pump ──
    add("pump_bracket", "Pump Bracket (FR4)", "#1A7326",
        make_pump_bracket, (), (PLATE_SIZE / 2 - 5, 0, BOTTOM_Z - PUMP_BRACKET_H))

    add("pump", "Peristaltic Pump", "#4D4D4D",
        make_pump, (), (PLATE_SIZE / 2 - 5, -(PUMP_BRACKET_T + PUMP_W / 2),
                        BOTTOM_Z - PUMP_BRACKET_H / 2))

    # ── Nose boom ──
    boom_center_x = PLATE_SIZE / 2 + BOOM_LENGTH / 2
    add("nose_boom", "Nose Boom (FR4 I-beam)", "#1A7326",
        make_nose_boom, (), (boom_center_x, 0, ARM_CENTER_Z - BOOM_THICK / 2))

    # ── Camera ──
    cam_x = PLATE_SIZE / 2 + 30
    cam_z = ARM_CENTER_Z - BOOM_THICK / 2 - 2
    add("camera", "OV5640 Camera Module", "#1A1A1A",
        make_camera, (), (cam_x, 0, cam_z))

    # ── Drip nozzle ──
    nozzle_x = PLATE_SIZE / 2 + BOOM_LENGTH
    add("drip_nozzle", "Drip Nozzle", "#666666",
        make_drip_nozzle, (), (nozzle_x, 0, ARM_CENTER_Z - BOOM_THICK / 2 - 5), (180, 0, 0))

    # ── ToF sensors (6x) ──
    tof_positions = [
        ("tof_down", "ToF Down", (0, 0, BOTTOM_Z - TOF_H - 2), (180, 0, 0)),
        ("tof_up", "ToF Up", (0, 0, TOP_Z + TOP_THICK + 2), None),
        ("tof_front", "ToF Front", (0, PLATE_SIZE / 2, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (90, 0, 0)),
        ("tof_back", "ToF Back", (0, -PLATE_SIZE / 2 + 5, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (-90, 0, 0)),
        ("tof_left", "ToF Left", (-PLATE_SIZE / 2, 0, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (0, -90, 0)),
        ("tof_right", "ToF Right", (PLATE_SIZE / 2, 0, TOP_Z + TOP_THICK / 2 + TOF_L / 2), (0, 90, 0)),
    ]
    for name, display, pos, rot in tof_positions:
        add(name, display, "#991A99", make_tof_board, (), pos, rot)

    return parts


def generate_viewer_html(parts_data, output_path):
    """Generate self-contained viewer.html with embedded STL data.

    parts_data: list of {name, display, color, stl_b64, file_size}
    """
    # Build the embedded parts JSON
    parts_json = json.dumps([{
        "name": p["name"],
        "display": p["display"],
        "color": p["color"],
        "size": p["file_size"],
        "stl": p["stl_b64"],
    } for p in parts_data], indent=None)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Drone 3D Model Viewer</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        background: #1a1a2e;
        color: #e0e0e0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        overflow: hidden;
        height: 100vh;
    }}
    #toolbar {{
        position: fixed; top: 0; left: 0; right: 0; z-index: 100;
        background: rgba(16, 16, 32, 0.92);
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 10px 20px;
        display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
    }}
    #toolbar h1 {{ font-size: 15px; font-weight: 600; color: #8ecae6; white-space: nowrap; }}
    .sep {{ width: 1px; height: 22px; background: rgba(255,255,255,0.12); }}
    .btn {{
        padding: 5px 14px; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px;
        background: rgba(255,255,255,0.06); color: #e0e0e0; font-size: 12px;
        cursor: pointer; transition: all 0.2s; white-space: nowrap;
    }}
    .btn:hover {{ background: rgba(142,202,230,0.15); border-color: #8ecae6; color: #8ecae6; }}
    .btn-primary {{ background: rgba(142,202,230,0.2); border-color: #8ecae6; color: #8ecae6; }}
    .btn.active {{ background: rgba(142,202,230,0.25); border-color: #8ecae6; color: #8ecae6; }}
    #file-input {{ display: none; }}
    label.btn {{ display: inline-flex; align-items: center; gap: 6px; }}
    .ctrl {{ display: flex; align-items: center; gap: 6px; }}
    .ctrl span {{ font-size: 11px; color: #999; }}
    #color-picker {{ width: 28px; height: 24px; border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; background: none; cursor: pointer; padding: 1px; }}

    #parts-list {{
        position: fixed; top: 54px; left: 0; bottom: 0; width: 220px; z-index: 90;
        background: rgba(16, 16, 32, 0.92); backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255,255,255,0.08);
        overflow-y: auto; padding: 8px 0;
    }}
    #parts-list h3 {{ padding: 8px 14px; font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
    .part-item {{
        padding: 6px 14px; font-size: 12px; cursor: pointer; display: flex;
        justify-content: space-between; align-items: center; transition: background 0.15s;
    }}
    .part-item:hover {{ background: rgba(142,202,230,0.1); }}
    .part-item.selected {{ background: rgba(142,202,230,0.2); color: #8ecae6; }}
    .part-item .eye {{ cursor: pointer; opacity: 0.4; font-size: 14px; margin-right: 6px; }}
    .part-item .eye.visible {{ opacity: 1.0; }}
    .part-item .size {{ font-size: 10px; color: #555; font-family: monospace; }}

    #selection-panel {{
        position: fixed; top: 54px; right: 0; z-index: 100; width: 320px;
        background: rgba(16, 16, 32, 0.95); backdrop-filter: blur(12px);
        border-left: 1px solid rgba(142,202,230,0.3); border-bottom: 1px solid rgba(142,202,230,0.3);
        border-radius: 0 0 0 8px;
        padding: 16px 20px; font-size: 12px; line-height: 1.7; display: none;
    }}
    #selection-panel h3 {{ color: #8ecae6; font-size: 14px; margin-bottom: 8px; font-weight: 600; }}
    .sel-row {{ display: flex; justify-content: space-between; font-family: 'SF Mono','Fira Code',monospace; font-size: 11px; }}
    .sel-label {{ color: #888; }}
    .sel-value {{ color: #e0e0e0; }}
    .sel-highlight {{ color: #ffa040; }}
    .sel-section {{ margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.06); }}
    .sel-section-title {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #555; margin-bottom: 4px; }}

    #cursor-coords {{
        position: fixed; bottom: 16px; right: 16px; z-index: 100;
        background: rgba(16,16,32,0.9); backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
        padding: 10px 16px; font-family: 'SF Mono','Fira Code',monospace; font-size: 11px;
        color: #8ecae6; line-height: 1.5; min-width: 200px;
    }}
    #cursor-coords .lbl {{ color: #555; font-size: 9px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }}
    .cline {{ display: flex; justify-content: space-between; }}
    .caxis {{ color: #666; }}
    .cval {{ color: #8ecae6; }}

    #info-panel {{
        position: fixed; bottom: 16px; left: 16px; z-index: 100;
        background: rgba(16,16,32,0.85); backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
        padding: 10px 16px; font-size: 11px; color: #888; line-height: 1.8;
    }}
    #info-panel .key {{ display: inline-block; padding: 1px 5px; background: rgba(255,255,255,0.08); border-radius: 3px; font-family: monospace; font-size: 10px; color: #aaa; margin: 0 2px; }}

    #loading {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); z-index: 200; background: rgba(16,16,32,0.95); border: 1px solid rgba(142,202,230,0.3); border-radius: 12px; padding: 24px 40px; text-align: center; }}
    #loading .spinner {{ width: 36px; height: 36px; border: 3px solid rgba(142,202,230,0.2); border-top-color: #8ecae6; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

    #drop-zone {{ position: fixed; top:0;left:0;right:0;bottom:0; z-index: 300; background: rgba(142,202,230,0.1); border: 3px dashed #8ecae6; display: none; align-items: center; justify-content: center; font-size: 22px; color: #8ecae6; }}
    #canvas-container {{ width: 100%; height: 100%; }}
</style>
</head>
<body>

<div id="toolbar">
    <h1>Drone 3D Viewer</h1>
    <div class="sep"></div>
    <label class="btn" for="file-input">+ Add STL</label>
    <input type="file" id="file-input" accept=".stl" multiple>
    <div class="sep"></div>
    <div class="ctrl"><span>Color:</span><input type="color" id="color-picker" value="#8ecae6"></div>
    <button class="btn" id="btn-wireframe">Wireframe</button>
    <button class="btn" id="btn-reset">Reset View</button>
    <button class="btn" id="btn-center">Fit All</button>
    <button class="btn" id="btn-axes">Axes</button>
    <div class="ctrl">
        <span>BG:</span>
        <button class="btn" id="btn-bg-dark">Dark</button>
        <button class="btn" id="btn-bg-mid">Mid</button>
        <button class="btn" id="btn-bg-light">Light</button>
    </div>
</div>

<div id="parts-list">
    <h3>Components</h3>
    <div id="parts-container"></div>
</div>

<div id="loading"><div class="spinner"></div><div id="loading-msg">Loading drone...</div></div>
<div id="drop-zone">Drop STL files here</div>
<div id="canvas-container"></div>

<div id="info-panel">
    <span class="key">LMB</span> Rotate &nbsp;
    <span class="key">RMB</span> Pan &nbsp;
    <span class="key">Scroll</span> Zoom &nbsp;
    <span class="key">Click</span> Select part &nbsp;
    <span class="key">Drop</span> Add STLs
</div>

<div id="cursor-coords">
    <div class="lbl">Cursor (mm)</div>
    <div class="cline"><span class="caxis">X:</span> <span class="cval" id="coord-x">---</span></div>
    <div class="cline"><span class="caxis">Y:</span> <span class="cval" id="coord-y">---</span></div>
    <div class="cline"><span class="caxis">Z:</span> <span class="cval" id="coord-z">---</span></div>
</div>

<div id="selection-panel">
    <h3 id="sel-title">Component</h3>
    <div class="sel-row"><span class="sel-label">Triangles:</span> <span class="sel-value" id="sel-tris">-</span></div>
    <div class="sel-row"><span class="sel-label">File size:</span> <span class="sel-value" id="sel-fsize">-</span></div>
    <div class="sel-section">
        <div class="sel-section-title">Bounding Box</div>
        <div class="sel-row"><span class="sel-label">Size:</span> <span class="sel-value" id="sel-bbox">-</span></div>
        <div class="sel-row"><span class="sel-label">Min:</span> <span class="sel-value" id="sel-min">-</span></div>
        <div class="sel-row"><span class="sel-label">Max:</span> <span class="sel-value" id="sel-max">-</span></div>
        <div class="sel-row"><span class="sel-label">Center:</span> <span class="sel-value" id="sel-center">-</span></div>
    </div>
    <div class="sel-section">
        <div class="sel-section-title">Click Point</div>
        <div class="sel-row"><span class="sel-label">Position:</span> <span class="sel-value" id="sel-pos">-</span></div>
        <div class="sel-row"><span class="sel-label">Normal:</span> <span class="sel-value" id="sel-normal">-</span></div>
        <div class="sel-row"><span class="sel-label">From origin:</span> <span class="sel-value sel-highlight" id="sel-dist">-</span></div>
    </div>
</div>

<script type="importmap">
{{
    "imports": {{
        "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
        "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
    }}
}}
</script>

<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
import {{ STLLoader }} from 'three/addons/loaders/STLLoader.js';

// ---- Embedded part data (base64 STL) ----
var EMBEDDED_PARTS = {parts_json};

(function() {{
    var container = document.getElementById('canvas-container');
    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    scene.fog = new THREE.Fog(0x1a1a2e, 2000, 8000);

    var cam = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 50000);
    cam.position.set(400, 300, 500);

    var renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    var controls = new OrbitControls(cam, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 1;
    controls.maxDistance = 20000;
    controls.target.set(0, 40, 0);
    controls.update();

    // Lighting
    scene.add(new THREE.AmbientLight(0x404060, 0.6));
    scene.add(new THREE.HemisphereLight(0x8ecae6, 0x2a2a4a, 0.5));
    var keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(150, 300, 200);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.near = 10; keyLight.shadow.camera.far = 1500;
    keyLight.shadow.camera.left = -500; keyLight.shadow.camera.right = 500;
    keyLight.shadow.camera.top = 500; keyLight.shadow.camera.bottom = -500;
    scene.add(keyLight);
    var fillLight = new THREE.DirectionalLight(0x8ecae6, 0.4);
    fillLight.position.set(-100, 150, -100); scene.add(fillLight);
    var rimLight = new THREE.DirectionalLight(0xffa040, 0.3);
    rimLight.position.set(-50, 50, 200); scene.add(rimLight);

    // Grid + ground
    scene.add(new THREE.GridHelper(2000, 100, 0x2a2a4a, 0x1e1e38));
    var gnd = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), new THREE.ShadowMaterial({{ opacity: 0.3 }}));
    gnd.rotation.x = -Math.PI / 2; gnd.position.y = -0.5; gnd.receiveShadow = true; scene.add(gnd);

    // Axes
    var axH = new THREE.AxesHelper(60);
    axH.position.set(-500, 0, -500); scene.add(axH);
    function mkLabel(t, c, p) {{
        var cv = document.createElement('canvas'); cv.width = 64; cv.height = 32;
        var cx = cv.getContext('2d'); cx.fillStyle = c; cx.font = 'bold 24px sans-serif';
        cx.textAlign = 'center'; cx.textBaseline = 'middle'; cx.fillText(t, 32, 16);
        var s = new THREE.Sprite(new THREE.SpriteMaterial({{ map: new THREE.CanvasTexture(cv), depthTest: false }}));
        s.position.copy(p); s.scale.set(30, 15, 1); return s;
    }}
    var axLabels = new THREE.Group();
    axLabels.add(mkLabel('X','#ff4444',new THREE.Vector3(-430,5,-500)));
    axLabels.add(mkLabel('Y','#44ff44',new THREE.Vector3(-500,70,-500)));
    axLabels.add(mkLabel('Z','#4444ff',new THREE.Vector3(-500,5,-430)));
    scene.add(axLabels);

    // Selection
    var selMarker = new THREE.Mesh(
        new THREE.SphereGeometry(2.5, 16, 16),
        new THREE.MeshBasicMaterial({{ color: 0xffa040, depthTest: false }})
    );
    selMarker.visible = false; selMarker.renderOrder = 999; scene.add(selMarker);
    var highlightedMesh = null;
    var outlineMat = new THREE.MeshBasicMaterial({{ color: 0xffa040, wireframe: true, transparent: true, opacity: 0.4 }});

    // State
    var parts = {{}};
    var partOrder = [];
    var selectedPart = null;
    var wireframeOn = false;
    var raycaster = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    var loader = new STLLoader();

    function addPart(name, display, colorHex, geometry, fileSize) {{
        var color = new THREE.Color(colorHex);
        var mat = new THREE.MeshPhysicalMaterial({{
            color: color, metalness: 0.2, roughness: 0.4, clearcoat: 0.3, clearcoatRoughness: 0.2,
            wireframe: wireframeOn, side: THREE.DoubleSide
        }});
        var mesh = new THREE.Mesh(geometry, mat);
        mesh.castShadow = true; mesh.receiveShadow = true;
        mesh.userData.partName = name;
        scene.add(mesh);
        parts[name] = {{ mesh: mesh, geometry: geometry, fileSize: fileSize, color: colorHex, display: display, visible: true }};
        if (partOrder.indexOf(name) === -1) partOrder.push(name);
        updatePartsList();
    }}

    function togglePart(name) {{
        var p = parts[name];
        if (!p) return;
        p.visible = !p.visible;
        p.mesh.visible = p.visible;
        if (!p.visible && selectedPart === name) {{
            selectedPart = null; clearHighlight(); selMarker.visible = false;
            document.getElementById('selection-panel').style.display = 'none';
        }}
        updatePartsList();
    }}

    function clearHighlight() {{
        if (highlightedMesh) {{
            scene.remove(highlightedMesh); highlightedMesh.geometry.dispose(); highlightedMesh.material.dispose();
            highlightedMesh = null;
        }}
    }}

    function fitCamera() {{
        var box = new THREE.Box3();
        var names = Object.keys(parts);
        if (names.length === 0) return;
        for (var i = 0; i < names.length; i++) {{
            var p = parts[names[i]];
            if (!p.visible) continue;
            p.geometry.computeBoundingBox();
            box.union(p.geometry.boundingBox.clone().applyMatrix4(p.mesh.matrixWorld));
        }}
        if (box.isEmpty()) return;
        var center = new THREE.Vector3(); box.getCenter(center);
        var size = new THREE.Vector3(); box.getSize(size);
        var dist = Math.max(size.x, size.y, size.z) * 1.8;
        cam.position.set(center.x + dist * 0.6, center.y + dist * 0.4, center.z + dist * 0.7);
        controls.target.copy(center); controls.update();
    }}

    function updatePartsList() {{
        var c = document.getElementById('parts-container');
        c.innerHTML = '';
        for (var i = 0; i < partOrder.length; i++) {{
            var name = partOrder[i];
            var p = parts[name];
            if (!p) continue;
            var div = document.createElement('div');
            div.className = 'part-item' + (selectedPart === name ? ' selected' : '');
            var sizeKB = p.fileSize ? (p.fileSize / 1024).toFixed(1) + ' KB' : '';
            div.innerHTML = '<span class="eye ' + (p.visible ? 'visible' : '') + '" data-part="' + name + '">&#9679;</span>' +
                '<span style="flex:1">' + p.display + '</span><span class="size">' + sizeKB + '</span>';
            div.setAttribute('data-part', name);
            div.addEventListener('click', function(e) {{
                if (e.target.classList.contains('eye')) {{
                    togglePart(e.target.getAttribute('data-part'));
                }} else {{
                    selectPart(this.getAttribute('data-part'), null);
                }}
            }});
            c.appendChild(div);
        }}
    }}

    function selectPart(name, hitPoint) {{
        selectedPart = name;
        var p = parts[name];
        if (!p) return;
        clearHighlight();
        highlightedMesh = new THREE.Mesh(p.geometry.clone(), outlineMat.clone());
        highlightedMesh.position.copy(p.mesh.position);
        highlightedMesh.rotation.copy(p.mesh.rotation);
        highlightedMesh.scale.copy(p.mesh.scale);
        scene.add(highlightedMesh);

        p.geometry.computeBoundingBox();
        var box = p.geometry.boundingBox;
        var size = new THREE.Vector3(); box.getSize(size);
        var center = new THREE.Vector3(); box.getCenter(center);
        var tris = p.geometry.attributes.position.count / 3;

        document.getElementById('selection-panel').style.display = 'block';
        document.getElementById('sel-title').textContent = p.display;
        document.getElementById('sel-tris').textContent = tris.toLocaleString();
        document.getElementById('sel-fsize').textContent = p.fileSize ? (p.fileSize / 1024).toFixed(1) + ' KB' : '-';
        document.getElementById('sel-bbox').textContent = size.x.toFixed(1) + ' x ' + size.y.toFixed(1) + ' x ' + size.z.toFixed(1) + ' mm';
        document.getElementById('sel-min').textContent = '(' + box.min.x.toFixed(1) + ', ' + box.min.y.toFixed(1) + ', ' + box.min.z.toFixed(1) + ')';
        document.getElementById('sel-max').textContent = '(' + box.max.x.toFixed(1) + ', ' + box.max.y.toFixed(1) + ', ' + box.max.z.toFixed(1) + ')';
        document.getElementById('sel-center').textContent = '(' + center.x.toFixed(1) + ', ' + center.y.toFixed(1) + ', ' + center.z.toFixed(1) + ')';

        if (hitPoint) {{
            var pt = hitPoint.point;
            document.getElementById('sel-pos').textContent = '(' + pt.x.toFixed(1) + ', ' + pt.y.toFixed(1) + ', ' + pt.z.toFixed(1) + ')';
            if (hitPoint.face) {{
                var n = hitPoint.face.normal;
                document.getElementById('sel-normal').textContent = '(' + n.x.toFixed(3) + ', ' + n.y.toFixed(3) + ', ' + n.z.toFixed(3) + ')';
            }}
            document.getElementById('sel-dist').textContent = pt.length().toFixed(1) + ' mm';
            selMarker.position.copy(pt); selMarker.visible = true;
        }} else {{
            document.getElementById('sel-pos').textContent = '-';
            document.getElementById('sel-normal').textContent = '-';
            document.getElementById('sel-dist').textContent = '-';
            selMarker.visible = false;
        }}
        updatePartsList();
    }}

    // Click detection
    var mouseDownPos = null;
    renderer.domElement.addEventListener('mousedown', function(e) {{ mouseDownPos = {{ x: e.clientX, y: e.clientY }}; }});
    renderer.domElement.addEventListener('mouseup', function(e) {{
        if (!mouseDownPos) return;
        if (Math.abs(e.clientX - mouseDownPos.x) > 5 || Math.abs(e.clientY - mouseDownPos.y) > 5) return;
        mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, cam);
        var meshes = [];
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) if (parts[names[i]].visible) meshes.push(parts[names[i]].mesh);
        var hits = raycaster.intersectObjects(meshes);
        if (hits.length > 0) {{
            selectPart(hits[0].object.userData.partName, hits[0]);
        }} else {{
            selectedPart = null; clearHighlight(); selMarker.visible = false;
            document.getElementById('selection-panel').style.display = 'none';
            updatePartsList();
        }}
    }});

    renderer.domElement.addEventListener('mousemove', function(e) {{
        mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, cam);
        var meshes = [];
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) if (parts[names[i]].visible) meshes.push(parts[names[i]].mesh);
        var hits = raycaster.intersectObjects(meshes);
        if (hits.length > 0) {{
            var pt = hits[0].point;
            document.getElementById('coord-x').textContent = pt.x.toFixed(1);
            document.getElementById('coord-y').textContent = pt.y.toFixed(1);
            document.getElementById('coord-z').textContent = pt.z.toFixed(1);
            renderer.domElement.style.cursor = 'pointer';
        }} else {{
            document.getElementById('coord-x').textContent = '---';
            document.getElementById('coord-y').textContent = '---';
            document.getElementById('coord-z').textContent = '---';
            renderer.domElement.style.cursor = 'default';
        }}
    }});

    // File input for adding custom STLs
    document.getElementById('file-input').addEventListener('change', function(e) {{
        var files = Array.prototype.slice.call(e.target.files);
        files.forEach(function(file) {{
            var reader = new FileReader();
            reader.onload = function(ev) {{
                try {{
                    var geo = loader.parse(ev.target.result);
                    geo.computeVertexNormals();
                    var name = file.name.replace(/\\.stl$/i, '');
                    addPart(name, file.name, '#8ecae6', geo, file.size);
                    fitCamera();
                }} catch(err) {{ console.error('Failed:', file.name, err); }}
            }};
            reader.readAsArrayBuffer(file);
        }});
        e.target.value = '';
    }});

    // Drag and drop
    var dragCounter = 0;
    var dropZone = document.getElementById('drop-zone');
    document.addEventListener('dragenter', function(e) {{ e.preventDefault(); dragCounter++; dropZone.style.display = 'flex'; }});
    document.addEventListener('dragover', function(e) {{ e.preventDefault(); }});
    document.addEventListener('dragleave', function() {{ dragCounter--; if (dragCounter <= 0) {{ dragCounter = 0; dropZone.style.display = 'none'; }} }});
    document.addEventListener('drop', function(e) {{
        e.preventDefault(); dragCounter = 0; dropZone.style.display = 'none';
        var items = e.dataTransfer.files;
        for (var i = 0; i < items.length; i++) {{
            if (!items[i].name.toLowerCase().endsWith('.stl')) continue;
            (function(file) {{
                var reader = new FileReader();
                reader.onload = function(ev) {{
                    try {{
                        var geo = loader.parse(ev.target.result);
                        geo.computeVertexNormals();
                        var name = file.name.replace(/\\.stl$/i, '');
                        addPart(name, file.name, '#8ecae6', geo, file.size);
                        fitCamera();
                    }} catch(err) {{ console.error('Failed:', file.name, err); }}
                }};
                reader.readAsArrayBuffer(file);
            }})(items[i]);
        }}
    }});

    // Toolbar
    document.getElementById('color-picker').addEventListener('input', function(e) {{
        if (selectedPart && parts[selectedPart]) parts[selectedPart].mesh.material.color.set(e.target.value);
    }});
    document.getElementById('btn-wireframe').addEventListener('click', function() {{
        wireframeOn = !wireframeOn;
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) parts[names[i]].mesh.material.wireframe = wireframeOn;
        this.classList.toggle('active', wireframeOn);
    }});
    document.getElementById('btn-reset').addEventListener('click', function() {{
        cam.position.set(400, 300, 500); controls.target.set(0, 40, 0); controls.update();
    }});
    document.getElementById('btn-center').addEventListener('click', fitCamera);
    var axesVis = true;
    document.getElementById('btn-axes').addEventListener('click', function() {{
        axesVis = !axesVis; axH.visible = axesVis; axLabels.visible = axesVis;
        this.classList.toggle('active', axesVis);
    }});
    var bgColors = {{ dark: 0x1a1a2e, mid: 0x2d2d44, light: 0x4a4a6a }};
    ['dark', 'mid', 'light'].forEach(function(key) {{
        document.getElementById('btn-bg-' + key).addEventListener('click', function() {{
            scene.background.setHex(bgColors[key]); scene.fog.color.setHex(bgColors[key]);
        }});
    }});
    window.addEventListener('resize', function() {{
        cam.aspect = window.innerWidth / window.innerHeight;
        cam.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    // Render loop
    function animate() {{ requestAnimationFrame(animate); controls.update(); renderer.render(scene, cam); }}
    animate();

    // ---- Auto-load embedded parts ----
    var loadingMsg = document.getElementById('loading-msg');
    var loadingEl = document.getElementById('loading');
    var total = EMBEDDED_PARTS.length;
    var loaded = 0;

    function loadEmbeddedPart(idx) {{
        if (idx >= total) {{
            loadingEl.style.display = 'none';
            fitCamera();
            console.log('[VIEWER] All ' + total + ' parts loaded');
            return;
        }}
        var p = EMBEDDED_PARTS[idx];
        loadingMsg.textContent = 'Loading ' + (idx + 1) + '/' + total + ': ' + p.display;
        try {{
            var binary = atob(p.stl);
            var bytes = new Uint8Array(binary.length);
            for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            var geo = loader.parse(bytes.buffer);
            geo.computeVertexNormals();
            addPart(p.name, p.display, p.color, geo, p.size);
            loaded++;
        }} catch (e) {{
            console.error('[VIEWER] Failed to load embedded part:', p.name, e);
        }}
        // Use setTimeout to avoid blocking UI during loading
        setTimeout(function() {{ loadEmbeddedPart(idx + 1); }}, 0);
    }}

    loadEmbeddedPart(0);
}})();
</script>
</body>
</html>'''

    output_path.write_text(html, encoding="utf-8")
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Generated viewer.html ({size_mb:.1f} MB)")


def main():
    out_dir = Path(__file__).resolve().parent.parent / "cad" / "exports"
    assy_dir = out_dir / "assembly"
    out_dir.mkdir(parents=True, exist_ok=True)
    assy_dir.mkdir(parents=True, exist_ok=True)

    # ── Individual parts at origin (for manufacturing) ──
    print("Exporting individual parts at origin...")
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
    for name, (func, args) in individual_parts.items():
        path = out_dir / f"{name}.stl"
        try:
            export_stl(func(*args), path)
            print(f"  {name}.stl")
        except Exception as e:
            print(f"  WARNING: {name}: {e}")

    # ── Positioned parts for assembly viewer ──
    print("\nBuilding positioned assembly parts...")
    positioned = build_positioned_parts()
    print(f"  {len(positioned)} parts built")

    # Export positioned STLs and collect base64 data for viewer
    print("\nExporting positioned parts + generating viewer...")
    parts_data = []
    for p in positioned:
        stl_path = assy_dir / f"{p['name']}.stl"
        try:
            export_stl(p["shape_yup"], stl_path)
            stl_bytes = stl_path.read_bytes()
            parts_data.append({
                "name": p["name"],
                "display": p["display"],
                "color": p["color"],
                "file_size": len(stl_bytes),
                "stl_b64": base64.b64encode(stl_bytes).decode("ascii"),
            })
            print(f"  {p['name']}.stl ({len(stl_bytes)/1024:.1f} KB)")
        except Exception as e:
            print(f"  WARNING: {p['name']}: {e}")

    # ── Generate self-contained viewer ──
    generate_viewer_html(parts_data, out_dir / "viewer.html")

    # ── Summary ──
    all_stls = sorted(out_dir.glob("*.stl")) + sorted(assy_dir.glob("*.stl"))
    total_kb = sum(f.stat().st_size for f in all_stls) / 1024
    print(f"\n{'=' * 60}")
    print(f"Exported {len(all_stls)} STL files ({total_kb:.0f} KB total)")
    print(f"  Individual parts: {out_dir}/")
    print(f"  Positioned parts: {assy_dir}/")
    print(f"  Viewer:           {out_dir}/viewer.html")
    print(f"{'=' * 60}")
    print("Open viewer.html in a browser — drone loads automatically.")


if __name__ == "__main__":
    main()
