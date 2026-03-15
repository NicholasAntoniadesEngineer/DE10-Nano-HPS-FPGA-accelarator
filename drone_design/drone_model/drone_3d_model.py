#!/usr/bin/env python3
"""
Plant-Watering Drone — DE10-Nano — 3D Model Export

Single entry point for all drone model exports (STL, STEP, KiCad PCB).
Passes project-specific data into the generic cadquery_framework pipeline.

Usage:
    python drone_design/drone_model/drone_3d_model.py          # all exports
    python drone_design/drone_model/drone_3d_model.py stl      # STL + viewer
    python drone_design/drone_model/drone_3d_model.py step     # STEP files
    python drone_design/drone_model/drone_3d_model.py gerber   # KiCad PCBs

Output:
    drone_design/drone_model/output/stl/       (STL parts + assembly)
    drone_design/drone_model/output/step/      (STEP parts + assembly)
    drone_design/drone_model/output/gerber/    (KiCad PCB files)
    drone_design/drone_model/output/viewer.html (3D viewer)
"""

import sys
import base64
from pathlib import Path
from datetime import datetime

_DRONE_MODEL_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _DRONE_MODEL_DIR.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_DRONE_MODEL_DIR))

from assembly.manifest import build_drone_manifest, get_assembly_constraints
from assembly.catalog import INDIVIDUAL_PARTS
from cadquery_framework.pipeline import export_assembly
from cadquery_framework.exporters.step_export import export_step_assembly
from cadquery_framework.exporters.gerber_export import export_gerber_pcbs

# PCB generators from component files
from components.frame.skeleton_plate import generate_bottom_plate_pcb, generate_top_plate_pcb
from components.frame.arm import generate_arm_pcb
from components.landing_gear.landing_leg import generate_landing_leg_pcb
from components.frame.nose_boom import generate_nose_boom_pcb
from components.payload.pump_bracket import generate_pump_bracket_pcb

from components.assembly_constants import (
    PLATE_SIZE, BOTTOM_THICK, TOP_THICK,
    ARM_LENGTH, ARM_WIDTH, ARM_THICK,
    LEG_THICK,
    BOOM_LENGTH, BOOM_WIDTH, BOOM_THICK,
    _D,
)

PCB_GENERATORS = [
    ("bottom_plate", generate_bottom_plate_pcb),
    ("top_plate", generate_top_plate_pcb),
    ("arm", generate_arm_pcb),
    ("landing_leg", generate_landing_leg_pcb),
    ("nose_boom", generate_nose_boom_pcb),
    ("pump_bracket", generate_pump_bracket_pcb),
]

HEADER_HOLE_D = _D["connections"]["header_hole_diameter"]
LEG_HEADER_PINS = _D["connections"]["leg_header_pins"]
BOOM_HEADER_PINS = _D["connections"]["boom_header_pins"]

FABRICATION_README = f"""Drone FR4 Frame Parts — KiCad PCB Files
========================================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

These are MECHANICAL PCBs — no copper traces, no electrical components.
Order as standard FR4 PCB from any fabricator (JLCPCB, PCBWay, OSH Park).

Files:
  bottom_plate.kicad_pcb  — {PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm, {BOTTOM_THICK:.1f}mm FR4, Kagome cutouts + arm/leg header holes
  top_plate.kicad_pcb     — {PLATE_SIZE:.0f}x{PLATE_SIZE:.0f}mm, {TOP_THICK:.1f}mm FR4, central opening + cutouts
  arm.kicad_pcb           — {ARM_LENGTH:.0f}x{ARM_WIDTH:.0f}mm, {ARM_THICK:.1f}mm FR4, I-beam, M3 motor holes + 6x M2 mounting flange holes
  landing_leg.kicad_pcb   — L-shape, {LEG_THICK:.1f}mm FR4, lightening holes + {LEG_HEADER_PINS} header pads
  nose_boom.kicad_pcb     — {BOOM_LENGTH:.0f}x{BOOM_WIDTH:.0f}mm, {BOOM_THICK:.1f}mm FR4, I-beam + 2x{BOOM_HEADER_PINS} root header pads
  pump_bracket.kicad_pcb  — unfolded U-channel clip for RP-Q1 pump, {_D['pump_bracket']['thickness']:.1f}mm FR4, fold lines + frame mounting holes

Fabrication specs:
  Material:     FR4 (standard glass-epoxy)
  Finish:       HASL or bare copper (cosmetic only)
  Solder mask:  Optional (green default)
  Silkscreen:   White (part labels)
  Min hole:     {HEADER_HOLE_D}mm (pin header) / 2.5mm (M2.5 standoff) / 3.2mm (M3 motor mount)
  Copper:       Not required — these are structural, not electrical

To generate Gerber files (requires KiCad 7+):
  kicad-cli pcb export gerbers -o gerber_out/ bottom_plate.kicad_pcb
  kicad-cli pcb export drill -o gerber_out/ bottom_plate.kicad_pcb

Quantities per drone:
  bottom_plate x 1
  top_plate    x 1
  arm          x 4
  landing_leg  x 4
  nose_boom    x 1
  pump_bracket x 1
  Total: 12 PCBs per drone
"""


def main():
    output_dir = _DRONE_MODEL_DIR / "output"

    # Parse args
    target = "all"
    verbose = False
    for arg in sys.argv[1:]:
        if arg in ("stl", "step", "gerber", "all"):
            target = arg
        elif arg in ("--verbose", "-v"):
            verbose = True

    # Build manifest (shared by STL and STEP)
    manifest = None
    validation = None
    constraints = None
    if target in ("stl", "step", "all"):
        manifest, validation, tubing_allowed = build_drone_manifest(overlay_path=output_dir)

    # STL + viewer
    if target in ("stl", "all"):
        constraints = get_assembly_constraints()
        kicad_files = {}
        gerber_dir = output_dir / "gerber"
        if gerber_dir.exists():
            for kf in sorted(gerber_dir.glob("*.kicad_pcb")):
                kicad_files[kf.name] = base64.b64encode(kf.read_bytes()).decode("ascii")

        export_assembly(
            manifest=manifest,
            output_dir=output_dir,
            title="Drone 3D Model Viewer",
            toolbar_title="Drone 3D Viewer",
            loading_message="Loading drone...",
            allowed_pairs=tubing_allowed,
            kicad_files=kicad_files or None,
            individual_parts=INDIVIDUAL_PARTS,
            verbose=verbose,
            constraints=constraints,
            validation=validation,
            overlay_save_hint=(
                "Parametric modifications (fillet/chamfer/cut) only apply after you:\n\n"
                "1. Save the downloaded file as viewer_overlay.json in:\n   drone_design/drone_model/output/\n\n"
                "2. Re-run: python drone_design/drone_model/drone_3d_model.py stl\n\n"
                "Then re-open the new viewer.html to see the updated model."
            ),
        )

    # STEP
    if target in ("step", "all"):
        export_step_assembly(
            manifest=manifest,
            output_dir=output_dir / "step",
            assembly_name="drone_assembly",
            individual_parts=INDIVIDUAL_PARTS,
            verbose=verbose,
        )

    # Gerber/KiCad
    if target in ("gerber", "all"):
        export_gerber_pcbs(
            pcb_generators=PCB_GENERATORS,
            output_dir=output_dir / "gerber",
            readme_text=FABRICATION_README,
            verbose=verbose,
        )


if __name__ == "__main__":
    main()
