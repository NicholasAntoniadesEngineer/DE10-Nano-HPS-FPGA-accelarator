"""
Integration tests for the LCSC automation framework.
Tests the full pipeline: schematic → parse → BOM → export.
Includes performance measurements and end-to-end validation.
"""

import pytest
import time
import json
from pathlib import Path

from config import get_config
from kicad_parser import KiCADParser, SchematicComponent
from bom_generator import BOMMFromSchematic, BOMMGenerator
from utils import parse_csv, write_csv


@pytest.mark.integration
class TestEndToEndPipeline:
    """Tests for the complete automation pipeline"""

    def test_full_pipeline_sample_schematic(self, sample_kicad_sch_content, temp_dir):
        """Test complete pipeline from schematic to BOM"""
        # 1. Create schematic file
        sch_file = temp_dir / "test_circuit.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)

        # 2. Parse schematic
        parser = KiCADParser()
        components = parser.parse_schematic(sch_file)
        assert len(components) > 0

        # 3. Generate BOM
        bom_gen = BOMMGenerator(components)
        assert len(bom_gen.bom) > 0
        assert len(bom_gen.cpl) > 0

        # 4. Export CSV files
        output_dir = temp_dir / "manufacturing"
        bom_file = output_dir / "BOM.csv"
        cpl_file = output_dir / "CPL.csv"

        bom_gen.export_bom_csv(bom_file)
        bom_gen.export_cpl_csv(cpl_file)

        # 5. Verify outputs
        assert bom_file.exists()
        assert cpl_file.exists()

        # 6. Validate data integrity
        bom_rows = parse_csv(bom_file)
        cpl_rows = parse_csv(cpl_file)

        assert len(bom_rows) > 0
        assert len(cpl_rows) > 0

    def test_full_pipeline_with_validation(self, sample_kicad_sch_content, temp_dir):
        """Test pipeline with validation at each step"""
        sch_file = temp_dir / "validated.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)

        # Step 1: Validate schematic parsing
        parser = KiCADParser()
        components = parser.parse_schematic(sch_file)
        assert all(hasattr(c, 'reference') for c in components)
        assert all(hasattr(c, 'value') for c in components)

        # Step 2: Validate BOM generation
        bom_gen = BOMMGenerator(components)
        summary = bom_gen.get_part_summary()
        assert summary['total_components'] == len(components)

        # Step 3: Validate BOM items
        for item in bom_gen.bom:
            assert item.comment  # Has value
            assert item.designator  # Has reference(s)
            assert item.quantity > 0

        # Step 4: Validate CPL items
        for item in bom_gen.cpl:
            assert item.designator  # Has reference
            assert item.footprint  # Has footprint
            assert item.lcsc_id or item.lcsc_id == ""  # Has LCSC or empty

    def test_pipeline_error_handling(self, temp_dir):
        """Test pipeline handles errors gracefully"""
        # Non-existent file
        parser = KiCADParser()
        components = parser.parse_schematic(Path("/nonexistent/file.kicad_sch"))
        assert components == []  # Returns empty list, not exception

        # Empty components
        bom_gen = BOMMGenerator([])
        assert len(bom_gen.bom) == 0
        assert len(bom_gen.cpl) == 0

    def test_pipeline_with_all_file_formats(self, sample_components, temp_dir):
        """Test pipeline creates correct file formats"""
        bom_gen = BOMMGenerator(sample_components)
        output_dir = temp_dir / "formats"
        output_dir.mkdir()

        # BOM CSV
        bom_file = output_dir / "BOM.csv"
        bom_gen.export_bom_csv(bom_file)
        assert bom_file.suffix == ".csv"

        # CPL CSV
        cpl_file = output_dir / "CPL.csv"
        bom_gen.export_cpl_csv(cpl_file)
        assert cpl_file.suffix == ".csv"

        # Verify both are valid CSVs
        bom_data = parse_csv(bom_file)
        cpl_data = parse_csv(cpl_file)
        assert all(isinstance(row, dict) for row in bom_data)
        assert all(isinstance(row, dict) for row in cpl_data)


@pytest.mark.integration
class TestDataIntegrity:
    """Tests for data integrity throughout the pipeline"""

    def test_component_data_preserved(self, sample_components, temp_dir):
        """Test component data is preserved through pipeline"""
        bom_gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "test_bom.csv"
        bom_gen.export_bom_csv(output_file)

        rows = parse_csv(output_file)

        # Verify all components represented
        all_designators = []
        for row in rows:
            designators = row["Designator"].split(",")
            all_designators.extend(designators)

        assert len(all_designators) == len(sample_components)

    def test_bom_aggregation_preserves_data(self, sample_components):
        """Test aggregation doesn't lose component data"""
        bom_gen = BOMMGenerator(sample_components)

        # Total quantity should match component count
        total_qty = sum(item.quantity for item in bom_gen.bom)
        assert total_qty == len(sample_components)

    def test_csv_roundtrip_data_integrity(self, sample_components, temp_dir):
        """Test data integrity in CSV roundtrip"""
        bom_gen = BOMMGenerator(sample_components)
        bom_file = temp_dir / "roundtrip.csv"
        bom_gen.export_bom_csv(bom_file)

        # Read back
        rows = parse_csv(bom_file)

        # Original components values should be in BOM
        original_values = set(c.value for c in sample_components)
        bom_values = set(row["Comment"] for row in rows)

        # All original values should be in BOM
        assert original_values.issubset(bom_values)

    def test_lcsc_id_preservation(self, temp_dir):
        """Test LCSC IDs are correctly preserved"""
        components = [
            SchematicComponent("C1", "100nF", "0402", "C2040"),
            SchematicComponent("R1", "10k", "0402", "C4169"),
        ]
        bom_gen = BOMMGenerator(components)
        output_file = temp_dir / "lcsc_preservation.csv"
        bom_gen.export_bom_csv(output_file)

        rows = parse_csv(output_file)
        lcsc_ids = [row["LCSC Part #"] for row in rows]

        assert "C2040" in lcsc_ids
        assert "C4169" in lcsc_ids

    def test_natural_sort_in_output(self, temp_dir):
        """Test output is naturally sorted"""
        components = [
            SchematicComponent("C10", "100nF", "0402", "C2040"),
            SchematicComponent("C2", "100nF", "0402", "C2040"),
            SchematicComponent("C1", "100nF", "0402", "C2040"),
            SchematicComponent("C20", "100nF", "0402", "C2040"),
        ]
        bom_gen = BOMMGenerator(components)
        output_file = temp_dir / "sorting.csv"
        bom_gen.export_bom_csv(output_file)

        rows = parse_csv(output_file)
        designators = rows[0]["Designator"].split(",")

        # Should be naturally sorted: C1, C2, C10, C20
        assert designators == ["C1", "C2", "C10", "C20"]


@pytest.mark.integration
class TestPerformance:
    """Tests for performance characteristics"""

    @pytest.mark.slow
    def test_large_bom_generation(self, temp_dir):
        """Test performance with larger BOM"""
        # Create 100 components
        components = [
            SchematicComponent(
                f"C{i}",
                f"{(i % 5) * 100}nF",
                "0402",
                f"C{2000 + i}"
            )
            for i in range(1, 101)
        ]

        start = time.time()
        bom_gen = BOMMGenerator(components)
        parse_time = time.time() - start

        output_file = temp_dir / "large_bom.csv"
        start = time.time()
        bom_gen.export_bom_csv(output_file)
        export_time = time.time() - start

        assert parse_time < 1.0  # Should be fast
        assert export_time < 1.0
        assert output_file.exists()

    def test_csv_parsing_performance(self, sample_components, temp_dir):
        """Test CSV parsing performance"""
        # Create and export
        bom_gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "perf_test.csv"
        bom_gen.export_bom_csv(output_file)

        # Time parsing
        start = time.time()
        rows = parse_csv(output_file)
        parse_time = time.time() - start

        assert parse_time < 0.5  # Should be very fast
        assert len(rows) > 0


@pytest.mark.integration
class TestConfigIntegration:
    """Tests for configuration integration"""

    def test_config_usage_in_pipeline(self, isolated_config):
        """Test config is accessible during pipeline"""
        cfg = get_config()
        assert cfg is not None
        assert cfg.lcsc is not None
        assert cfg.cache is not None

    def test_config_paths_for_output(self, isolated_config, temp_dir):
        """Test config provides correct paths for output"""
        cfg = get_config()
        output_dir = cfg.data_dir / "manufacturing"
        output_dir.mkdir(parents=True, exist_ok=True)

        assert output_dir.exists()
        assert output_dir.is_absolute()


@pytest.mark.integration
@pytest.mark.requires_files
class TestRealSchematicPipeline:
    """Integration tests with actual schematic files"""

    def test_real_schematic_full_pipeline(self, actual_schematic_file, temp_dir):
        """Test full pipeline with actual schematic"""
        if actual_schematic_file is None:
            pytest.skip("Actual schematic file not found")

        # Parse
        parser = KiCADParser()
        components = parser.parse_schematic(actual_schematic_file)
        assert len(components) > 0

        # Generate BOM
        bom_gen = BOMMGenerator(components)

        # Export
        output_dir = temp_dir / "real_schematic_output"
        bom_file = output_dir / "real_BOM.csv"
        cpl_file = output_dir / "real_CPL.csv"

        bom_gen.export_bom_csv(bom_file)
        bom_gen.export_cpl_csv(cpl_file)

        # Validate
        assert bom_file.exists()
        assert cpl_file.exists()
        assert bom_file.stat().st_size > 0
        assert cpl_file.stat().st_size > 0

    def test_real_schematic_validation(self, actual_schematic_file):
        """Test validation of real schematic"""
        if actual_schematic_file is None:
            pytest.skip("Actual schematic file not found")

        parser = KiCADParser()
        issues = parser.validate_schematic(actual_schematic_file)

        # Should have issue structure even if no issues
        assert isinstance(issues, dict)
        assert all(isinstance(v, list) for v in issues.values())

    def test_real_schematic_bom_completeness(self, actual_schematic_file, temp_dir):
        """Test BOM from real schematic is complete"""
        if actual_schematic_file is None:
            pytest.skip("Actual schematic file not found")

        bom_from_sch = BOMMFromSchematic(actual_schematic_file)
        results = bom_from_sch.generate_all(temp_dir / "real_output")

        assert "bom" in results
        assert "cpl" in results
        assert "summary" in results

        summary = results["summary"]
        assert summary["total_components"] > 0
        assert summary["bom_items"] > 0


@pytest.mark.integration
class TestComponentAggregationIntegration:
    """Integration tests for component aggregation"""

    def test_aggregation_maintains_references(self, sample_components):
        """Test that aggregation maintains all references"""
        bom_gen = BOMMGenerator(sample_components)

        # Collect all references from BOM
        all_refs = []
        for item in bom_gen.bom:
            refs = item.designator.split(",")
            all_refs.extend(refs)

        # Should match original components
        original_refs = set(c.reference for c in sample_components)
        bom_refs = set(all_refs)

        assert bom_refs == original_refs

    def test_aggregation_accurate_counts(self, temp_dir):
        """Test aggregation counts are accurate"""
        # Create 10 identical components
        components = [
            SchematicComponent(f"C{i}", "100nF", "0402", "C2040")
            for i in range(1, 11)
        ]

        bom_gen = BOMMGenerator(components)
        summary = bom_gen.get_part_summary()

        assert summary["total_components"] == 10
        assert summary["total_unique_parts"] == 1
        assert bom_gen.bom[0].quantity == 10

    def test_mixed_component_aggregation(self, temp_dir):
        """Test aggregation with mixed components"""
        components = [
            SchematicComponent("C1", "100nF", "0402", "C2040"),
            SchematicComponent("C2", "100nF", "0402", "C2040"),
            SchematicComponent("R1", "10k", "0402", "C4169"),
            SchematicComponent("R2", "10k", "0402", "C4169"),
            SchematicComponent("R3", "4.7k", "0402", "C4170"),
            SchematicComponent("U1", "ESP32", "LQFP48", "C529971"),
        ]

        bom_gen = BOMMGenerator(components)
        summary = bom_gen.get_part_summary()

        assert summary["total_components"] == 6
        assert summary["total_unique_parts"] == 4
        assert summary["missing_lcsc_ids"] == 0


@pytest.mark.integration
class TestOutputFileValidation:
    """Tests for output file validation"""

    def test_bom_csv_format_valid(self, sample_components, temp_dir):
        """Test BOM CSV is in valid JLCPCB format"""
        bom_gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "valid_bom.csv"
        bom_gen.export_bom_csv(output_file)

        rows = parse_csv(output_file)

        # Check required JLCPCB fields
        if len(rows) > 0:
            required = {"Comment", "Designator", "Footprint", "LCSC Part #"}
            actual = set(rows[0].keys())
            assert required.issubset(actual)

    def test_cpl_csv_format_valid(self, sample_components, temp_dir):
        """Test CPL CSV is in valid JLCPCB format"""
        bom_gen = BOMMGenerator(sample_components)
        output_file = temp_dir / "valid_cpl.csv"
        bom_gen.export_cpl_csv(output_file)

        rows = parse_csv(output_file)

        # Check required JLCPCB fields
        if len(rows) > 0:
            required = {
                "Designator", "Val", "Package", "LCSC Part #",
                "Rotation", "Layer", "Mid X", "Mid Y"
            }
            actual = set(rows[0].keys())
            assert required.issubset(actual)

    def test_output_files_readable(self, sample_components, temp_dir):
        """Test output files are readable"""
        bom_gen = BOMMGenerator(sample_components)
        bom_file = temp_dir / "readable_bom.csv"
        cpl_file = temp_dir / "readable_cpl.csv"

        bom_gen.export_bom_csv(bom_file)
        bom_gen.export_cpl_csv(cpl_file)

        # Should be readable without errors
        bom_content = bom_file.read_text(encoding='utf-8')
        cpl_content = cpl_file.read_text(encoding='utf-8')

        assert len(bom_content) > 0
        assert len(cpl_content) > 0

    def test_output_files_non_empty(self, sample_components, temp_dir):
        """Test output files are not empty"""
        bom_gen = BOMMGenerator(sample_components)
        bom_file = temp_dir / "non_empty_bom.csv"
        cpl_file = temp_dir / "non_empty_cpl.csv"

        bom_gen.export_bom_csv(bom_file)
        bom_gen.export_cpl_csv(cpl_file)

        assert bom_file.stat().st_size > 0
        assert cpl_file.stat().st_size > 0


@pytest.mark.integration
class TestErrorRecovery:
    """Tests for error recovery in pipeline"""

    def test_invalid_schematic_recovery(self, temp_dir):
        """Test pipeline recovers from invalid schematic"""
        invalid_file = temp_dir / "invalid.kicad_sch"
        invalid_file.write_text("not valid s-expression")

        parser = KiCADParser()
        components = parser.parse_schematic(invalid_file)

        # Should return empty list, not crash
        assert components == []

    def test_empty_components_recovery(self):
        """Test pipeline handles empty components"""
        bom_gen = BOMMGenerator([])

        summary = bom_gen.get_part_summary()
        assert summary["total_components"] == 0
        assert summary["total_unique_parts"] == 0

    def test_missing_lcsc_ids_recovery(self):
        """Test pipeline handles missing LCSC IDs"""
        components = [
            SchematicComponent("C1", "100nF", "0402"),  # No LCSC ID
            SchematicComponent("R1", "10k", "0402"),  # No LCSC ID
        ]

        bom_gen = BOMMGenerator(components)
        summary = bom_gen.get_part_summary()

        assert summary["missing_lcsc_ids"] == 2
        # Pipeline should still work
        assert summary["total_components"] == 2

    def test_invalid_footprint_recovery(self):
        """Test pipeline handles invalid footprints"""
        components = [
            SchematicComponent("C1", "100nF", "", "C2040"),  # Empty footprint
            SchematicComponent("R1", "10k", "INVALID", "C4169"),
        ]

        bom_gen = BOMMGenerator(components)
        # Should still generate output
        assert len(bom_gen.bom) > 0


@pytest.mark.integration
class TestSummaryStatistics:
    """Tests for summary statistics generation"""

    def test_summary_statistics_accuracy(self, sample_components):
        """Test summary statistics are accurate"""
        bom_gen = BOMMGenerator(sample_components)
        summary = bom_gen.get_part_summary()

        # Verify accuracy
        assert summary["total_components"] == len(sample_components)
        assert summary["total_unique_parts"] <= len(sample_components)
        assert summary["bom_items"] == len(bom_gen.bom)
        assert summary["cpl_items"] == len(bom_gen.cpl)

    def test_package_breakdown_completeness(self, sample_components):
        """Test package breakdown includes all components"""
        bom_gen = BOMMGenerator(sample_components)
        summary = bom_gen.get_part_summary()

        # All components should be in package breakdown
        total_by_package = sum(summary["package_breakdown"].values())
        assert total_by_package == summary["total_components"]

    def test_missing_lcsc_count_accuracy(self, temp_dir):
        """Test missing LCSC count is accurate"""
        components = [
            SchematicComponent("C1", "100nF", "0402", "C2040"),
            SchematicComponent("C2", "100nF", "0402"),  # Missing
            SchematicComponent("R1", "10k", "0402"),  # Missing
        ]

        bom_gen = BOMMGenerator(components)
        summary = bom_gen.get_part_summary()

        assert summary["missing_lcsc_ids"] == 2
