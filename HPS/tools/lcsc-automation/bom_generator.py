"""
BOM and CPL (Component Placement List) generator for JLCPCB manufacturing.
Generates production-ready CSV files from KiCad schematic.
"""

import logging
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from kicad_parser import KiCADParser, SchematicComponent
from utils import write_csv, natural_sort_key

logger = logging.getLogger(__name__)


@dataclass
class BOMMItem:
    """BOM entry (aggregated by value + footprint)"""
    comment: str  # Value (e.g., "100nF")
    designator: str  # Reference designators (e.g., "C1,C2,C3")
    footprint: str  # KiCAD footprint (e.g., "0402")
    lcsc_part: str  # LCSC part number (e.g., "C2040")
    quantity: int = 1
    unit_price: float = 0.0
    extended_price: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CPLItem:
    """Component placement list entry"""
    comment: str  # Value
    designator: str  # Reference (single, e.g., "C1")
    footprint: str  # Footprint
    lcsc_id: str  # LCSC part number
    rotation: float = 0.0  # Rotation in degrees
    x: float = 0.0  # X coordinate (mm)
    y: float = 0.0  # Y coordinate (mm)
    layer: str = "F"  # F or B (front/back)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            "Designator": self.designator,
            "Val": self.comment,
            "Package": self.footprint,
            "LCSC Part #": self.lcsc_id,
            "Rotation": str(int(self.rotation)),
            "Layer": self.layer,
            "Mid X": f"{self.x:.2f}",
            "Mid Y": f"{self.y:.2f}"
        }


class BOMMGenerator:
    """Generate BOM and CPL files for JLCPCB manufacturing"""

    def __init__(self, components: List[SchematicComponent]):
        self.components = components
        self.bom = self._generate_bom()
        self.cpl = self._generate_cpl()

    def _generate_bom(self) -> List[BOMMItem]:
        """Generate BOM from components"""
        # Group by value + footprint
        groups = defaultdict(list)

        for comp in self.components:
            key = (comp.value, comp.footprint, comp.lcsc_id or "")
            groups[key].append(comp)

        # Create BOM items
        bom_items = []
        for (value, footprint, lcsc_id), comps in groups.items():
            # Collect all reference designators
            designators = sorted(
                [c.reference for c in comps],
                key=natural_sort_key
            )

            item = BOMMItem(
                comment=value,
                designator=",".join(designators),
                footprint=self._normalize_footprint(footprint),
                lcsc_part=lcsc_id or "",
                quantity=len(comps)
            )
            bom_items.append(item)

        # Sort by reference
        bom_items.sort(key=lambda x: natural_sort_key(x.designator))

        return bom_items

    def _generate_cpl(self) -> List[CPLItem]:
        """Generate component placement list from components"""
        cpl_items = []

        for comp in self.components:
            item = CPLItem(
                comment=comp.value,
                designator=comp.reference,
                footprint=self._normalize_footprint(comp.footprint),
                lcsc_id=comp.lcsc_id or "",
                rotation=0.0,  # Extracted from KiCAD board if available
                layer="F"  # Default to front, should be parsed from board
            )
            cpl_items.append(item)

        # Sort by reference
        cpl_items.sort(key=lambda x: natural_sort_key(x.designator))

        return cpl_items

    @staticmethod
    def _normalize_footprint(footprint: str) -> str:
        """Normalize footprint string (extract package type)"""
        # Convert KiCAD footprint to simple package designation
        # e.g., "Package_BGA:BGA-48_7x7_P0.5mm_EP" -> "BGA48"
        # e.g., "Package_QFP:LQFP-48_7x7_P0.5mm" -> "LQFP48"

        if not footprint:
            return "TBD"

        # Extract last component (package type)
        parts = footprint.split(':')
        if len(parts) > 1:
            pkg = parts[1]
        else:
            pkg = parts[0]

        # Extract numbers for simple representation
        import re
        match = re.search(r'(\w+?)[-_]?(\d+)', pkg)
        if match:
            pkg_type = match.group(1)
            pkg_size = match.group(2)
            return f"{pkg_type}{pkg_size}"

        return pkg[:10]  # Fallback: truncate

    def export_bom_csv(self, filepath: Path, include_pricing: bool = False):
        """Export BOM as CSV (JLCPCB format)"""
        fieldnames = ["Comment", "Designator", "Footprint", "LCSC Part #"]

        if include_pricing:
            fieldnames.extend(["Unit Price", "Extended Price"])

        rows = []
        for item in self.bom:
            row = {
                "Comment": item.comment,
                "Designator": item.designator,
                "Footprint": item.footprint,
                "LCSC Part #": item.lcsc_part
            }
            if include_pricing:
                row["Unit Price"] = f"${item.unit_price:.4f}"
                row["Extended Price"] = f"${item.extended_price:.2f}"
            rows.append(row)

        write_csv(filepath, rows, fieldnames)
        logger.info(f"Exported BOM: {filepath} ({len(rows)} unique parts)")

    def export_cpl_csv(self, filepath: Path):
        """Export component placement list as CSV (JLCPCB format)"""
        fieldnames = [
            "Designator",
            "Val",
            "Package",
            "LCSC Part #",
            "Rotation",
            "Layer",
            "Mid X",
            "Mid Y"
        ]

        rows = [item.to_dict() for item in self.cpl]
        write_csv(filepath, rows, fieldnames)
        logger.info(f"Exported CPL: {filepath} ({len(rows)} components)")

    def get_part_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        total_quantity = sum(item.quantity for item in self.bom)
        total_unique = len(self.bom)
        missing_lcsc = len([item for item in self.bom if not item.lcsc_part])

        # Group by package type
        packages = defaultdict(int)
        for item in self.bom:
            pkg = self._extract_package_type(item.footprint)
            packages[pkg] += item.quantity

        return {
            "total_unique_parts": total_unique,
            "total_components": total_quantity,
            "missing_lcsc_ids": missing_lcsc,
            "package_breakdown": dict(packages),
            "bom_items": len(self.bom),
            "cpl_items": len(self.cpl)
        }

    @staticmethod
    def _extract_package_type(footprint: str) -> str:
        """Extract package type (0402, LQFP48, BGA, etc.)"""
        # Simple extraction: look for common patterns
        import re

        patterns = [
            r'(\d{4})',  # 0402, 1206, etc.
            r'([A-Z]+)[-_]?\d+',  # LQFP48, QFN24, etc.
            r'([A-Z]+)',  # Generic
        ]

        for pattern in patterns:
            match = re.search(pattern, footprint)
            if match:
                return match.group(1)

        return "Other"

    def validate_bom(self) -> Dict[str, List[str]]:
        """Validate BOM completeness"""
        issues = {
            "missing_lcsc_id": [],
            "missing_footprint": [],
            "empty_designator": []
        }

        for item in self.bom:
            if not item.lcsc_part:
                issues["missing_lcsc_id"].append(item.comment)
            if not item.footprint or item.footprint == "TBD":
                issues["missing_footprint"].append(item.comment)
            if not item.designator:
                issues["empty_designator"].append(item.comment)

        return issues

    def print_summary(self):
        """Print BOM summary"""
        summary = self.get_part_summary()
        print("\n=== BOM Summary ===")
        print(f"Unique parts: {summary['total_unique_parts']}")
        print(f"Total components: {summary['total_components']}")
        print(f"Missing LCSC IDs: {summary['missing_lcsc_ids']}")
        print(f"\nPackage breakdown:")
        for pkg, qty in sorted(summary['package_breakdown'].items()):
            print(f"  {pkg}: {qty}")

        # Check for issues
        issues = self.validate_bom()
        if any(issues.values()):
            print(f"\nValidation issues:")
            for issue_type, items in issues.items():
                if items:
                    print(f"  {issue_type}: {', '.join(items)}")
        else:
            print("\n✓ BOM validation passed!")


class BOMMFromSchematic:
    """Generate BOM directly from schematic file"""

    def __init__(self, schematic_path: Path):
        self.parser = KiCADParser()
        self.schematic_path = schematic_path
        self.components = self.parser.parse_schematic(schematic_path)
        self.generator = BOMMGenerator(self.components)

    def generate_all(self, output_dir: Path):
        """Generate all output files"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate BOM
        bom_file = output_dir / f"{self.schematic_path.stem}_BOM.csv"
        self.generator.export_bom_csv(bom_file)

        # Generate CPL
        cpl_file = output_dir / f"{self.schematic_path.stem}_CPL.csv"
        self.generator.export_cpl_csv(cpl_file)

        logger.info(f"Generated manufacturing files in {output_dir}")
        return {
            "bom": bom_file,
            "cpl": cpl_file,
            "summary": self.generator.get_part_summary()
        }

    def validate(self) -> bool:
        """Validate schematic"""
        issues = self.parser.validate_schematic(self.schematic_path)

        if any(issues.values()):
            logger.error("Schematic validation failed:")
            for issue_type, items in issues.items():
                if items:
                    logger.error(f"  {issue_type}: {items}")
            return False

        logger.info("✓ Schematic validation passed")
        return True


if __name__ == "__main__":
    # Test BOM generation
    from pathlib import Path

    sch_path = Path("../../../drone_design/drone_model/components/electronics/daughter_board_esp32.kicad_sch")

    if sch_path.exists():
        print("Generating BOM from schematic...")
        bom_gen = BOMMFromSchematic(sch_path)

        # Validate
        bom_gen.validate()

        # Generate files
        output_dir = sch_path.parent / "manufacturing"
        results = bom_gen.generate_all(output_dir)

        # Print summary
        bom_gen.generator.print_summary()

        print(f"\nGenerated files:")
        print(f"  BOM: {results['bom']}")
        print(f"  CPL: {results['cpl']}")
    else:
        print(f"Schematic not found: {sch_path}")
