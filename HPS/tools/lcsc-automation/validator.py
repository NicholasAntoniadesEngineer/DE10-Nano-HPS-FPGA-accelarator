"""
Component validation: stock checks, DFM compliance, supply chain risk assessment.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from lcsc_fetcher import LCSCFetcher, LCSCPart
from bom_generator import BOMMGenerator
from kicad_parser import SchematicComponent

logger = logging.getLogger(__name__)


class ComponentValidator:
    """Validate components for manufacturability and supply chain"""

    def __init__(self):
        self.fetcher = LCSCFetcher()

    def validate_stock_availability(self, lcsc_ids: List[str],
                                   min_stock: int = 50) -> Dict[str, Dict[str, Any]]:
        """Check stock levels for parts"""
        results = {}

        for lcsc_id in lcsc_ids:
            part = self.fetcher.fetch_part(lcsc_id)
            if part:
                status = "in_stock" if part.stock >= min_stock else "low_stock"
                if part.stock <= 0:
                    status = "out_of_stock"

                results[lcsc_id] = {
                    "description": part.description,
                    "stock": part.stock,
                    "status": status,
                    "price": part.price,
                    "minimum_qty": part.minimum_qty
                }
            else:
                results[lcsc_id] = {
                    "status": "not_found",
                    "stock": 0,
                    "description": "LCSC part not found"
                }

        return results

    def validate_bom_stock(self, bom: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate entire BOM for stock availability"""
        issues = []
        all_parts = {}

        for item in bom:
            lcsc_id = item.get("LCSC Part #", "").strip()
            if not lcsc_id:
                issues.append({
                    "type": "missing_lcsc_id",
                    "value": item.get("Comment", ""),
                    "designators": item.get("Designator", "")
                })
                continue

            part = self.fetcher.fetch_part(lcsc_id)
            if not part:
                issues.append({
                    "type": "part_not_found",
                    "lcsc_id": lcsc_id,
                    "designators": item.get("Designator", "")
                })
                continue

            all_parts[lcsc_id] = part

            # Check stock
            quantity_needed = len(item.get("Designator", "").split(","))
            if part.stock < quantity_needed:
                issues.append({
                    "type": "insufficient_stock",
                    "lcsc_id": lcsc_id,
                    "needed": quantity_needed,
                    "available": part.stock,
                    "designators": item.get("Designator", "")
                })

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "parts_checked": len(all_parts),
            "parts_by_stock": self._group_by_stock(all_parts)
        }

    @staticmethod
    def _group_by_stock(parts: Dict[str, LCSCPart]) -> Dict[str, int]:
        """Group parts by stock level categories"""
        categories = {
            "in_stock_abundant": 0,  # >500
            "in_stock_good": 0,       # 100-500
            "in_stock_ok": 0,         # 10-100
            "in_stock_low": 0,        # 1-10
            "out_of_stock": 0
        }

        for part in parts.values():
            if part.stock > 500:
                categories["in_stock_abundant"] += 1
            elif part.stock > 100:
                categories["in_stock_good"] += 1
            elif part.stock > 10:
                categories["in_stock_ok"] += 1
            elif part.stock > 0:
                categories["in_stock_low"] += 1
            else:
                categories["out_of_stock"] += 1

        return categories

    def validate_dfm_compliance(self, components: List[SchematicComponent]) -> Dict[str, List[str]]:
        """Validate DFM (Design for Manufacturability) compliance"""
        issues = {
            "missing_footprint": [],
            "missing_lcsc_id": [],
            "unverified_footprint": []
        }

        for comp in components:
            if not comp.footprint:
                issues["missing_footprint"].append(comp.reference)
            if not comp.lcsc_id:
                issues["missing_lcsc_id"].append(comp.reference)

            # Check if part exists on LCSC
            if comp.lcsc_id:
                part = self.fetcher.fetch_part(comp.lcsc_id)
                if not part:
                    issues["unverified_footprint"].append(f"{comp.reference} ({comp.lcsc_id})")

        return issues

    def supply_chain_risk_assessment(self, bom: List[Dict[str, str]]) -> Dict[str, Any]:
        """Assess supply chain risks"""
        risks = {
            "single_source_parts": [],
            "long_lead_time": [],
            "obsolescence_risk": [],
            "price_volatility": []
        }

        part_prices = {}

        for item in bom:
            lcsc_id = item.get("LCSC Part #", "").strip()
            if not lcsc_id:
                continue

            part = self.fetcher.fetch_part(lcsc_id)
            if not part:
                continue

            # Track pricing
            if lcsc_id not in part_prices:
                part_prices[lcsc_id] = []
            part_prices[lcsc_id].append(part.price)

            # Check for single-source (arbitrary threshold: only 1 alternative)
            # This would require searching for alternatives, skipping for now

        # Detect price volatility (if multiple prices found)
        for lcsc_id, prices in part_prices.items():
            if len(prices) > 1:
                price_variance = max(prices) / min(prices)
                if price_variance > 1.2:  # 20% variance
                    risks["price_volatility"].append({
                        "lcsc_id": lcsc_id,
                        "variance": f"{price_variance:.2f}x"
                    })

        return {
            "risk_level": "high" if any(risks.values()) else "low",
            "risks": risks,
            "unique_parts": len(part_prices)
        }

    def generate_validation_report(self, bom_file: Path) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        from bom_generator import BOMMFromSchematic

        # For now, return basic structure
        report = {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "bom_file": str(bom_file),
            "sections": {}
        }

        return report


class DFMChecker:
    """Design for Manufacturability checker"""

    # JLCPCB/standard PCB manufacturing limits
    MIN_TRACE_WIDTH = 0.15  # mm
    MIN_TRACE_SPACING = 0.15  # mm
    MIN_VIA_DIAMETER = 0.3  # mm
    MIN_VIA_SPACING = 0.5  # mm
    MIN_PAD_SIZE = 0.2  # mm

    @staticmethod
    def check_trace_width(width_mm: float) -> bool:
        """Check if trace width is within DFM limits"""
        return width_mm >= DFMChecker.MIN_TRACE_WIDTH

    @staticmethod
    def check_spacing(spacing_mm: float) -> bool:
        """Check if spacing is within DFM limits"""
        return spacing_mm >= DFMChecker.MIN_TRACE_SPACING

    @staticmethod
    def check_via_diameter(diameter_mm: float) -> bool:
        """Check if via diameter is within DFM limits"""
        return diameter_mm >= DFMChecker.MIN_VIA_DIAMETER

    @staticmethod
    def check_via_spacing(spacing_mm: float) -> bool:
        """Check if via spacing is within DFM limits"""
        return spacing_mm >= DFMChecker.MIN_VIA_SPACING

    @staticmethod
    def print_dfm_limits():
        """Print DFM design rules"""
        print("\n=== JLCPCB DFM Design Rules ===")
        print(f"Minimum trace width: {DFMChecker.MIN_TRACE_WIDTH} mm")
        print(f"Minimum trace spacing: {DFMChecker.MIN_TRACE_SPACING} mm")
        print(f"Minimum via diameter: {DFMChecker.MIN_VIA_DIAMETER} mm")
        print(f"Minimum via spacing: {DFMChecker.MIN_VIA_SPACING} mm")
        print(f"Minimum pad size: {DFMChecker.MIN_PAD_SIZE} mm")


if __name__ == "__main__":
    # Test validator
    validator = ComponentValidator()

    # Test stock check
    print("Testing stock availability...")
    stock = validator.validate_stock_availability(["C2040", "C24112", "C1234567"])
    for lcsc_id, info in stock.items():
        print(f"  {lcsc_id}: {info['status']} (stock: {info['stock']})")

    # Print DFM limits
    DFMChecker.print_dfm_limits()
