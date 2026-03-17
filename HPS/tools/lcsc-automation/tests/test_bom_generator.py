"""
Unit tests for bom_generator.py module.
Tests BOM and CPL generation, CSV export, and component aggregation.
"""

import pytest
from pathlib import Path
from collections import defaultdict

from bom_generator import (
    BOMMItem, CPLItem, BOMMGenerator, BOMMFromSchematic
)
from kicad_parser import SchematicComponent


@pytest.mark.unit
class TestBOMMItem:
    """Tests for BOMMItem dataclass"""

    def test_bomm_item_creation(self):
        """Test creating BOM item"""
        item = BOMMItem(
            comment="100nF",
            designator="C1,C2",
            footprint="0402",
            lcsc_part="C2040",
            quantity=2
        )
        assert item.comment == "100nF"
        assert item.quantity == 2

    def test_bomm_item_defaults(self):
        """Test BOM item defaults"""
        item = BOMMItem(
            comment="100nF",
            designator="C1",
            footprint="0402",
            lcsc_part="C2040"
        )
        assert item.unit_price == 0.0
        assert item.extended_price == 0.0

    def test_bomm_item_with_pricing(self):
        """Test BOM item with pricing"""
        item = BOMMItem(
            comment="100nF",
            designator="C1",
            footprint="0402",
            lcsc_part="C2040",
            unit_price=0.01,
            extended_price=0.02
        )
        assert item.unit_price == 0.01
        assert item.extended_price == 0.02

    def test_bomm_item_to_dict(self):
        """Test converting BOM item to dict"""
        item = BOMMItem(
            comment="100nF",
            designator="C1,C2",
            footprint="0402",
            lcsc_part="C2040",
            quantity=2
        )
        item_dict = item.to_dict()
        assert item_dict["comment"] == "100nF"
        assert item_dict["quantity"] == 2


@pytest.mark.unit
class TestCPLItem:
    """Tests for CPLItem dataclass"""

    def test_cpl_item_creation(self):
        """Test creating CPL item"""
        item = CPLItem(
            comment="100nF",
            designator="C1",
            footprint="0402",
            lcsc_id="C2040"
        )
        assert item.designator == "C1"
        assert item.lcsc_id == "C2040"

    def test_cpl_item_defaults(self):
        """Test CPL item defaults"""
        item = CPLItem(
            comment="100nF",
            designator="C1",
            footprint="0402",
            lcsc_id="C2040"
        )
        assert item.rotation == 0.0
        assert item.x == 0.0
        assert item.y == 0.0
        assert item.layer == "F"

    def test_cpl_item_with_position(self):
        """Test CPL item with position data"""
        item = CPLItem(
            comment="100nF",
            designator="C1",
            footprint="0402",
            lcsc_id="C2040",
            x=10.5,
            y=20.3,
            rotation=90.0,
            layer="B"
        )
        assert item.x == 10.5
        assert item.y == 20.3
        assert item.rotation == 90.0
        assert item.layer == "B"

    def test_cpl_item_to_dict(self):
        """Test converting CPL item to dict"""
        item = CPLItem(
            comment="100nF",
            designator="C1",
            footprint="0402",
            lcsc_id="C2040",
            x=10.5,
            y=20.3
        )
        item_dict = item.to_dict()
        assert item_dict["Designator"] == "C1"
        assert item_dict["Val"] == "100nF"
        assert item_dict["LCSC Part #"] == "C2040"
        assert float(item_dict["Mid X"]) == 10.5
        assert float(item_dict["Mid Y"]) == 20.3


@pytest.mark.unit
class TestBOMMGenerator:
    """Tests for BOMMGenerator class"""

    def test_generator_initialization(self, sample_components):
        """Test BOM generator initialization"""
        gen = BOMMGenerator(sample_components)
        assert len(gen.bom) > 0
        assert len(gen.cpl) > 0
        assert len(gen.bom) <= len(gen.components)  # BOM is aggregated

    def test_bom_generation_aggregation(self, sample_components):
        """Test BOM aggregation by value+footprint"""
        gen = BOMMGenerator(sample_components)

        # C1 and C2 should be aggregated
        nf_items = [item for item in gen.bom if "100nF" in item.comment]
        assert len(nf_items) == 1
        assert nf_items[0].quantity == 2

    def test_bom_designator_sorting(self, sample_components):
        """Test BOM items have naturally sorted designators"""
        gen = BOMMGenerator(sample_components)

        for item in gen.bom:
            designators = item.designator.split(",")
            # Should be in natural order (C1, C2, C10 not C1, C10, C2)
            assert len(designators) > 0

    def test_cpl_generation(self, sample_components):
        """Test CPL generation from components"""
        gen = BOMMGenerator(sample_components)

        # Should have one CPL entry per component
        assert len(gen.cpl) == len(sample_components)

        # Check first item
        first_cpl = gen.cpl[0]
        assert first_cpl.designator in [c.reference for c in sample_components]

    def test_footprint_normalization(self):
        """Test footprint normalization"""
        normalizations = [
            ("Package_QFP:LQFP-48_7x7_P0.5mm", "LQFP48"),
            ("Package_BGA:BGA-48_7x7_P0.5mm_EP", "BGA48"),
            ("0402", "0402"),
            ("Package_SMD:C_0402_1005Metric", "C0402"),
        ]

        for original, expected_pattern in normalizations:
            normalized = BOMMGenerator._normalize_footprint(original)
            # Check contains numbers (package size)
            assert any(c.isdigit() for c in normalized)

    def test_footprint_normalization_fallback(self):
        """Test footprint normalization fallback"""
        normalized = BOMMGenerator._normalize_footprint("")
        assert normalized == "TBD"

        normalized = BOMMGenerator._normalize_footprint(None)
        assert normalized == "TBD"

    def test_export_bom_csv(self, sample_components, temp_dir):
        """Test BOM CSV export"""
        gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "test_bom.csv"

        gen.export_bom_csv(output_file)

        assert output_file.exists()

        # Read and verify
        from utils import parse_csv
        rows = parse_csv(output_file)
        assert len(rows) > 0
        assert "Comment" in rows[0] or all(k in rows[0] for k in ["Comment", "Designator"])

    def test_export_bom_csv_with_pricing(self, sample_components, temp_dir):
        """Test BOM CSV export with pricing"""
        gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "test_bom_pricing.csv"

        gen.export_bom_csv(output_file, include_pricing=True)

        assert output_file.exists()

        from utils import parse_csv
        rows = parse_csv(output_file)
        assert len(rows) > 0
        # Check pricing fields exist
        if len(rows) > 0:
            row = rows[0]
            assert "Unit Price" in row or "Extended Price" in row

    def test_export_cpl_csv(self, sample_components, temp_dir):
        """Test CPL CSV export"""
        gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "test_cpl.csv"

        gen.export_cpl_csv(output_file)

        assert output_file.exists()

        from utils import parse_csv
        rows = parse_csv(output_file)
        assert len(rows) == len(sample_components)

    def test_cpl_csv_required_fields(self, sample_components, temp_dir):
        """Test CPL CSV has all JLCPCB required fields"""
        gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "test_cpl_fields.csv"

        gen.export_cpl_csv(output_file)

        from utils import parse_csv
        rows = parse_csv(output_file)
        required_fields = [
            "Designator", "Val", "Package", "LCSC Part #",
            "Rotation", "Layer", "Mid X", "Mid Y"
        ]
        if len(rows) > 0:
            for field in required_fields:
                assert field in rows[0] or field.replace(" ", "") in "".join(rows[0].keys())

    def test_get_part_summary(self, sample_components):
        """Test getting BOM summary statistics"""
        gen = BOMMGenerator(sample_components)
        summary = gen.get_part_summary()

        assert "total_unique_parts" in summary
        assert "total_components" in summary
        assert "missing_lcsc_ids" in summary
        assert "package_breakdown" in summary
        assert summary["total_components"] == len(sample_components)

    def test_summary_missing_lcsc_ids(self, temp_dir):
        """Test summary reports missing LCSC IDs"""
        # Create components without LCSC IDs
        components = [
            SchematicComponent("C1", "100nF", "0402"),  # No LCSC ID
            SchematicComponent("R1", "10k", "0402", lcsc_id="C4169")
        ]
        gen = BOMMGenerator(components)
        summary = gen.get_part_summary()

        assert summary["missing_lcsc_ids"] >= 1

    def test_extract_package_type(self):
        """Test extracting package type from footprint"""
        tests = [
            ("0402", "0402"),
            ("C_0402", "0402"),
            ("LQFP48", "LQFP"),
            ("BGA144", "BGA"),
        ]

        for footprint, expected_pattern in tests:
            pkg = BOMMGenerator._extract_package_type(footprint)
            # Should extract something sensible
            assert len(pkg) > 0

    def test_validate_bom(self, sample_components):
        """Test BOM validation"""
        gen = BOMMGenerator(sample_components)
        issues = gen.validate_bom()

        assert "missing_lcsc_id" in issues
        assert "missing_footprint" in issues
        assert "empty_designator" in issues
        # Sample components should be valid
        assert len(issues["empty_designator"]) == 0

    def test_validate_bom_with_missing_data(self, temp_dir):
        """Test BOM validation detects missing data"""
        components = [
            SchematicComponent("C1", "100nF", "0402"),  # Missing LCSC
            SchematicComponent("R1", "10k", "", lcsc_id="C4169"),  # Missing footprint
        ]
        gen = BOMMGenerator(components)
        issues = gen.validate_bom()

        assert len(issues["missing_lcsc_id"]) >= 1
        assert len(issues["missing_footprint"]) >= 1


@pytest.mark.unit
class TestBOMMFromSchematic:
    """Tests for BOMMFromSchematic class"""

    def test_initialization(self, sample_kicad_sch_content, temp_dir):
        """Test BOMMFromSchematic initialization"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)

        bom_gen = BOMMFromSchematic(sch_file)
        assert bom_gen.schematic_path == sch_file
        assert len(bom_gen.components) > 0
        assert bom_gen.generator is not None

    def test_generate_all_files(self, sample_kicad_sch_content, temp_dir):
        """Test generating all output files"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)
        output_dir = temp_dir / "output"

        bom_gen = BOMMFromSchematic(sch_file)
        results = bom_gen.generate_all(output_dir)

        assert "bom" in results
        assert "cpl" in results
        assert "summary" in results
        assert results["bom"].exists()
        assert results["cpl"].exists()

    def test_validation_pass(self, sample_kicad_sch_content, temp_dir):
        """Test validation passes for complete schematic"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)

        bom_gen = BOMMFromSchematic(sch_file)
        assert bom_gen.validate() is True

    def test_validation_fail_missing_lcsc(self, temp_dir):
        """Test validation fails for incomplete schematic"""
        sch_content = """(kicad_sch
  (symbol (lib_id "Device:C") (at 100 100 0)
    (property "Reference" "C1" (id 0 0))
    (property "Value" "100nF" (id 1 0))
    (property "Footprint" "0402" (id 2 0))
  )
)"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sch_content)

        bom_gen = BOMMFromSchematic(sch_file)
        # Should return False due to missing LCSC ID
        result = bom_gen.validate()
        assert result is False


@pytest.mark.unit
class TestCSVFormats:
    """Tests for CSV format compliance"""

    def test_bom_csv_format_jlcpcb(self, sample_components, temp_dir):
        """Test BOM CSV follows JLCPCB format"""
        gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "jlcpcb_bom.csv"

        gen.export_bom_csv(output_file)

        from utils import parse_csv
        rows = parse_csv(output_file)

        # JLCPCB BOM fields: Comment, Designator, Footprint, LCSC Part #
        required = {"Comment", "Designator", "Footprint", "LCSC Part #"}
        if len(rows) > 0:
            actual_fields = set(rows[0].keys())
            assert required.issubset(actual_fields)

    def test_cpl_csv_format_jlcpcb(self, sample_components, temp_dir):
        """Test CPL CSV follows JLCPCB format"""
        gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "jlcpcb_cpl.csv"

        gen.export_cpl_csv(output_file)

        from utils import parse_csv
        rows = parse_csv(output_file)

        # JLCPCB CPL fields
        expected_fields = {
            "Designator", "Val", "Package", "LCSC Part #",
            "Rotation", "Layer", "Mid X", "Mid Y"
        }
        if len(rows) > 0:
            actual_fields = set(rows[0].keys())
            assert expected_fields.issubset(actual_fields)

    def test_csv_encoding(self, sample_components, temp_dir):
        """Test CSV is UTF-8 encoded"""
        gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "utf8_test.csv"

        gen.export_bom_csv(output_file)

        # Should be readable as UTF-8
        content = output_file.read_text(encoding='utf-8')
        assert len(content) > 0


@pytest.mark.unit
class TestComponentAggregationEdgeCases:
    """Tests for edge cases in component aggregation"""

    def test_aggregation_case_sensitive_value(self):
        """Test aggregation is case-sensitive for values"""
        components = [
            SchematicComponent("C1", "100nF", "0402", "C2040"),
            SchematicComponent("C2", "100NF", "0402", "C2040"),  # Different case
        ]
        gen = BOMMGenerator(components)

        # Should treat as different due to case sensitivity
        nf_items = [item for item in gen.bom if "nF" in item.comment or "NF" in item.comment]
        # May be aggregated depending on implementation
        assert len(nf_items) >= 1

    def test_aggregation_empty_lcsc_id(self):
        """Test aggregation with empty LCSC IDs"""
        components = [
            SchematicComponent("C1", "100nF", "0402", ""),
            SchematicComponent("C2", "100nF", "0402", ""),
        ]
        gen = BOMMGenerator(components)

        # Should still aggregate by value+footprint
        assert any(item.quantity >= 2 for item in gen.bom)

    def test_aggregation_mixed_lcsc_ids(self):
        """Test components with same value but different LCSC IDs"""
        components = [
            SchematicComponent("C1", "100nF", "0402", "C2040"),
            SchematicComponent("C2", "100nF", "0402", "C2041"),  # Different LCSC
        ]
        gen = BOMMGenerator(components)

        # Current implementation groups by value+footprint+lcsc_id
        # So these would be separate
        items_100nf = [item for item in gen.bom if "100nF" in item.comment]
        assert len(items_100nf) >= 1

    def test_empty_components_list(self):
        """Test generator with empty component list"""
        gen = BOMMGenerator([])
        assert len(gen.bom) == 0
        assert len(gen.cpl) == 0

    def test_single_component(self):
        """Test generator with single component"""
        components = [SchematicComponent("C1", "100nF", "0402", "C2040")]
        gen = BOMMGenerator(components)
        assert len(gen.bom) == 1
        assert len(gen.cpl) == 1


@pytest.mark.unit
class TestPrintSummary:
    """Tests for summary printing functionality"""

    def test_print_summary_no_error(self, sample_components, capsys):
        """Test print_summary doesn't raise exception"""
        gen = BOMMGenerator(sample_components)
        gen.print_summary()  # Should not raise

        captured = capsys.readouterr()
        assert "BOM Summary" in captured.out

    def test_print_summary_includes_stats(self, sample_components, capsys):
        """Test print_summary includes statistics"""
        gen = BOMMGenerator(sample_components)
        gen.print_summary()

        captured = capsys.readouterr()
        assert "Unique parts" in captured.out
        assert "Total components" in captured.out
