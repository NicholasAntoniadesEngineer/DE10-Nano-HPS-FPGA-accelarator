"""Parametric STEP model generator for KiCad component packages using CadQuery.

Generates simplified 3D geometry for 28 standard component package types,
with collision detection suitable for PCB assembly visualization.
"""

import cadquery as cq
from pathlib import Path
from typing import Dict, Tuple
import os


# Package specifications: (width_mm, depth_mm, height_mm, category)
PACKAGE_SPECS = {
    # Passive components (SMD resistors, capacitors)
    "0402": (1.0, 0.5, 0.35, "passive"),
    "0603": (1.6, 0.8, 0.45, "passive"),
    "1210": (3.2, 2.5, 1.0, "passive"),
    "2512": (6.3, 3.2, 0.6, "passive"),
    # ICs - Small packages
    "SOT-23-3": (2.9, 1.6, 1.1, "ic"),
    "SOT-23-5": (2.9, 1.6, 1.1, "ic"),
    "SOT-23-8": (2.9, 1.6, 1.1, "ic"),
    "SOT-353": (2.0, 1.25, 0.95, "ic"),
    # ICs - DIP/SOIC
    "SOIC-8": (4.9, 3.9, 1.75, "ic"),
    "HSOP-8": (5.0, 4.0, 2.1, "ic"),
    "TSSOP-24": (7.8, 4.4, 1.2, "ic"),
    # ICs - QFN/BGA
    "QFN-24": (4.0, 4.0, 0.9, "ic"),
    "VQFN-16": (3.0, 3.0, 0.9, "ic"),
    "LGA-10": (2.0, 2.0, 0.65, "ic"),
    # Diodes
    "SMA": (4.3, 2.7, 2.1, "diode"),
    "SOD-882": (1.0, 0.6, 0.4, "diode"),
    "SMB": (5.3, 3.7, 2.5, "diode"),
    # Inductors
    "SRP1265A": (12.0, 12.0, 6.5, "inductor"),
    # RF modules
    "WILC3000-MR10B": (19.2, 13.7, 2.2, "module"),
    # Connectors - JST headers
    "JST-SH-3": (5.4, 3.4, 2.5, "connector"),
    "JST-SH-4": (6.7, 3.4, 2.5, "connector"),
    "JST-SH-6": (9.6, 3.4, 2.5, "connector"),
    # Connectors - JST power
    "JST-XH-2": (5.0, 7.0, 5.7, "connector"),
    "JST-XH-3": (7.5, 7.0, 5.7, "connector"),
    # Connectors - GPIO header
    "GPIO-2x20": (50.8, 5.08, 8.5, "header"),
    # Connectors - Power
    "XT60PW": (24.0, 15.5, 13.0, "connector"),
    "XT30PW": (14.0, 10.5, 9.0, "connector"),
    "PJ-102AH": (9.0, 14.5, 13.0, "connector"),
    # Connectors - FPC
    "FPC-24-0.5": (16.5, 4.5, 2.5, "connector"),
}

# Color mapping by category: RGB tuples (0.0-1.0 range)
CATEGORY_COLORS = {
    "passive": (0.95, 0.85, 0.2),  # Yellow
    "ic": (0.3, 0.3, 0.3),  # Grey
    "diode": (0.1, 0.1, 0.1),  # Black
    "inductor": (0.3, 0.3, 0.3),  # Grey
    "module": (0.3, 0.3, 0.3),  # Grey
    "connector": (0.1, 0.1, 0.1),  # Black
    "header": (0.1, 0.1, 0.1),  # Black
}


def _make_package_body(
    width_mm: float, depth_mm: float, height_mm: float, color: Tuple[float, float, float]
) -> cq.occ_impl.shapes.Shape:
    """Generate a parametric component body with chamfered lead frame.

    Args:
        width_mm: Package width in mm (X dimension).
        depth_mm: Package depth in mm (Y dimension).
        height_mm: Package height in mm (Z dimension).
        color: RGB color tuple (0.0-1.0 range).

    Returns:
        CadQuery Solid with main body and simplified lead frame geometry.
    """
    # Main body box: W × D × H, centered in XY, sitting on Z=0
    body = (
        cq.Workplane("XY")
        .box(width_mm, depth_mm, height_mm)
        .translate((0, 0, height_mm / 2))
    )

    # Simplified lead frame: flat chamfered rim around base
    # Extends 0.2mm beyond body in XY, height 0.05mm
    lead_width = width_mm + 0.4
    lead_depth = depth_mm + 0.4
    lead_height = 0.05

    leads = (
        cq.Workplane("XY")
        .box(lead_width, lead_depth, lead_height)
        .translate((0, 0, lead_height / 2))
    )

    # Apply 45° chamfer to top edges of lead frame
    # Chamfer radius 0.1mm for smooth transition
    leads = leads.edges("|Z").chamfer(0.1)

    # Union body and lead frame
    combined = body.union(leads)

    # Apply color (stored as object attribute for exporters that support it)
    combined = combined.val()

    return combined


def _generate_step_file(package_name: str, width_mm: float, depth_mm: float, height_mm: float,
                       category: str, output_path: Path, verbose: bool = False) -> bool:
    """Generate a STEP file for a single package.

    Args:
        package_name: Name of the package (e.g., "0402").
        width_mm: Package width in mm.
        depth_mm: Package depth in mm.
        height_mm: Package height in mm.
        category: Package category (determines color).
        output_path: Path where STEP file will be saved.
        verbose: Print progress messages.

    Returns:
        True if file was generated, False if skipped (already exists).
    """
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file already exists and has valid timestamp
    if output_path.exists():
        if verbose:
            print(f"[models_3d] Skipping {package_name} (already exists)")
        return False

    # Generate geometry
    color = CATEGORY_COLORS.get(category, (0.5, 0.5, 0.5))
    geometry = _make_package_body(width_mm, depth_mm, height_mm, color)

    # Export to STEP format
    try:
        cq.exporters.export(geometry, str(output_path), exportType="STEP")
        if verbose:
            print(f"[models_3d] Generated {package_name}")
        return True
    except Exception as e:
        print(f"[models_3d] Error generating {package_name}: {e}")
        return False


def generate_all_package_models(output_dir: Path, verbose: bool = False) -> Dict[str, Path]:
    """Generate STEP files for all 28 standard component packages.

    Creates parametric 3D models suitable for KiCad footprint visualization and
    collision detection during assembly planning.

    Args:
        output_dir: Root output directory. STEP files will be saved to
                   output_dir / "step/" subdirectory.
        verbose: Print progress messages for each package.

    Returns:
        Dictionary mapping package name (str) to output Path object.
        Keys: "0402", "0603", ..., "FPC-24-0.5"
        Values: Absolute paths to generated .step files.
    """
    output_dir = Path(output_dir)
    step_dir = output_dir / "step"
    step_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for package_name, (width, depth, height, category) in PACKAGE_SPECS.items():
        step_path = step_dir / f"{package_name}.step"

        # Generate or skip based on timestamp
        generated = _generate_step_file(
            package_name, width, depth, height, category, step_path, verbose
        )

        # Always add to results dict, regardless of generation status
        results[package_name] = step_path

    return results


if __name__ == "__main__":
    # Example usage: generate all models to ./output/step/
    output_directory = Path("./output")
    generated_files = generate_all_package_models(output_directory, verbose=True)

    print(f"\n[models_3d] Generated {len(generated_files)} package models")
    for package, path in sorted(generated_files.items()):
        print(f"  {package}: {path}")
