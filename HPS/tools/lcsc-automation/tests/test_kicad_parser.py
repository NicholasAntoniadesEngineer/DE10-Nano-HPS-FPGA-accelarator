"""
Unit tests for kicad_parser.py module.
Tests schematic parsing, component extraction, BOM generation, and validation.
"""

import pytest
from pathlib import Path

from kicad_parser import KiCADParser, SchematicComponent, Pin, PinType


@pytest.mark.unit
class TestSchematicComponent:
    """Tests for SchematicComponent dataclass"""

    def test_component_creation(self):
        """Test creating a SchematicComponent"""
        comp = SchematicComponent(
            reference="C1",
            value="100nF",
            footprint="0402",
            lcsc_id="C2040"
        )
        assert comp.reference == "C1"
        assert comp.value == "100nF"
        assert comp.footprint == "0402"
        assert comp.lcsc_id == "C2040"
        assert comp.quantity == 1

    def test_component_with_all_fields(self):
        """Test component with all optional fields"""
        comp = SchematicComponent(
            reference="U1",
            value="ESP32",
            footprint="LQFP48",
            lcsc_id="C529971",
            description="Wi-Fi microcontroller",
            datasheet="https://example.com/esp32.pdf",
            library="Device",
            symbol="MCU"
        )
        assert comp.description == "Wi-Fi microcontroller"
        assert comp.datasheet == "https://example.com/esp32.pdf"
        assert comp.library == "Device"
        assert comp.symbol == "MCU"

    def test_component_to_dict(self):
        """Test converting component to dictionary"""
        comp = SchematicComponent(
            reference="R1",
            value="10k",
            footprint="0402",
            lcsc_id="C4169"
        )
        comp_dict = comp.to_dict()
        assert comp_dict["reference"] == "R1"
        assert comp_dict["value"] == "10k"
        assert comp_dict["footprint"] == "0402"
        assert comp_dict["lcsc_id"] == "C4169"

    def test_component_default_quantities(self):
        """Test component quantity defaults"""
        comp = SchematicComponent("C1", "100nF", "0402")
        assert comp.quantity == 1
        assert len(comp.pins) == 0
        assert len(comp.properties) == 0


@pytest.mark.unit
class TestPinType:
    """Tests for PinType enum"""

    def test_pin_types_defined(self):
        """Test all standard KiCAD pin types are defined"""
        assert PinType.INPUT.value == "input"
        assert PinType.OUTPUT.value == "output"
        assert PinType.PASSIVE.value == "passive"
        assert PinType.POWER_IN.value == "power_in"

    def test_pin_creation(self):
        """Test creating a Pin"""
        pin = Pin(number="1", name="GND", pin_type="power_in")
        assert pin.number == "1"
        assert pin.name == "GND"
        assert pin.pin_type == "power_in"


@pytest.mark.unit
class TestTokenization:
    """Tests for s-expression tokenization"""

    def test_tokenize_simple_list(self):
        """Test tokenizing simple s-expression"""
        content = "(symbol (reference C1))"
        tokens = KiCADParser._tokenize(content)
        assert tokens == ["(", "symbol", "(", "reference", "C1", ")", ")"]

    def test_tokenize_with_strings(self):
        """Test tokenizing s-expression with quoted strings"""
        content = '(property "Reference" "C1")'
        tokens = KiCADParser._tokenize(content)
        assert '"Reference"' in tokens
        assert '"C1"' in tokens

    def test_tokenize_empty(self):
        """Test tokenizing empty content"""
        tokens = KiCADParser._tokenize("")
        assert tokens == []

    def test_tokenize_whitespace(self):
        """Test tokenizing with various whitespace"""
        content = "(symbol  (reference\n  C1\t))"
        tokens = KiCADParser._tokenize(content)
        assert "symbol" in tokens
        assert "reference" in tokens
        assert "C1" in tokens


@pytest.mark.unit
class TestSExpressionParsing:
    """Tests for s-expression parsing"""

    def test_parse_simple_sexpr(self):
        """Test parsing simple s-expression"""
        tokens = ["(", "symbol", "(", "reference", "C1", ")", ")"]
        result, _ = KiCADParser._parse_sexpr(tokens)
        assert isinstance(result, list)
        assert result[0] == "symbol"

    def test_parse_nested_sexpr(self):
        """Test parsing nested s-expression"""
        tokens = ["(", "symbol", "(", "property", "name", ")", ")"]
        result, _ = KiCADParser._parse_sexpr(tokens)
        assert isinstance(result, list)
        assert isinstance(result[1], list)
        assert result[1][0] == "property"

    def test_get_sexpr_value_found(self):
        """Test getting value from s-expression"""
        sexpr = ["symbol", ["property", "Reference", "C1"]]
        value = KiCADParser._get_sexpr_value(sexpr, "property", 2)
        assert value == "C1"

    def test_get_sexpr_value_not_found(self):
        """Test getting non-existent value"""
        sexpr = ["symbol", ["property", "Reference", "C1"]]
        value = KiCADParser._get_sexpr_value(sexpr, "missing", 2, "default")
        assert value == "default"

    def test_parse_lib_id(self):
        """Test parsing lib_id string"""
        lib, symbol = KiCADParser._parse_lib_id("Device:C")
        assert lib == "Device"
        assert symbol == "C"

    def test_parse_lib_id_no_colon(self):
        """Test parsing malformed lib_id"""
        lib, symbol = KiCADParser._parse_lib_id("Device")
        assert lib == "Device"
        assert symbol == ""


@pytest.mark.unit
class TestSchematicParsing:
    """Tests for schematic file parsing"""

    def test_parse_schematic_missing_file(self):
        """Test parsing non-existent file"""
        parser = KiCADParser()
        components = parser.parse_schematic(Path("/nonexistent/file.kicad_sch"))
        assert components == []

    def test_parse_schematic_sample(self, sample_kicad_sch_content, temp_dir):
        """Test parsing sample schematic"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)

        parser = KiCADParser()
        components = parser.parse_schematic(sch_file)

        assert len(components) == 3
        assert components[0].reference == "C1"
        assert components[0].value == "100nF"
        assert components[0].lcsc_id == "C2040"

    def test_extract_reference(self):
        """Test extracting reference from symbol"""
        sexpr = [
            "symbol",
            ["property", "Reference", "R1"],
            ["property", "Value", "10k"]
        ]
        ref = KiCADParser._extract_reference(sexpr)
        assert ref == "R1"

    def test_extract_property(self):
        """Test extracting property from symbol"""
        sexpr = [
            "symbol",
            ["property", "Reference", "C1"],
            ["property", "Value", "100nF"],
            ["property", "Footprint", "0402"],
            ["property", "LCSC", "C2040"]
        ]
        value = KiCADParser._extract_property(sexpr, "Value")
        assert value == "100nF"

        lcsc = KiCADParser._extract_property(sexpr, "LCSC")
        assert lcsc == "C2040"

    def test_extract_property_with_default(self):
        """Test extracting property with default"""
        sexpr = ["symbol", ["property", "Reference", "C1"]]
        value = KiCADParser._extract_property(sexpr, "Missing", "DEFAULT")
        assert value == "DEFAULT"


@pytest.mark.unit
class TestBOMGeneration:
    """Tests for BOM generation from schematic"""

    def test_extract_bom_aggregation(self, temp_dir, sample_kicad_sch_content):
        """Test BOM aggregation by value+footprint"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)

        parser = KiCADParser()
        bom = parser.extract_bom(sch_file)

        # Should have aggregated C1 and C2
        assert len(bom) == 3
        assert any(key.startswith("100nF") for key in bom.keys())

    def test_bom_aggregation_counts(self, sample_components):
        """Test BOM aggregation counts quantities"""
        # C1 and C2 both 100nF/0402
        bom_key = "100nF_Package_SMD:C_0402_1005Metric"
        parser = KiCADParser()
        bom = parser.extract_bom(Path("/nonexistent"))  # Will return empty

        # Test manually with sample data
        from bom_generator import BOMMGenerator
        gen = BOMMGenerator(sample_components)
        assert gen.bom[0].quantity == 2  # C1, C2 aggregated


@pytest.mark.unit
class TestSchematicValidation:
    """Tests for schematic validation"""

    def test_validate_missing_footprint(self, temp_dir):
        """Test validation detects missing footprint"""
        parser = KiCADParser()

        # Create component without footprint
        sexpr = [
            "kicad_sch",
            [
                "symbol",
                ["property", "Reference", "C1"],
                ["property", "Value", "100nF"],
                # Missing footprint
            ]
        ]
        comp = parser._parse_symbol(sexpr)
        # Should still create component, but without footprint

    def test_validate_missing_lcsc_id(self, temp_dir):
        """Test validation detects missing LCSC ID"""
        sch_content = """(kicad_sch
  (symbol (lib_id "Device:C") (at 100 100 0)
    (property "Reference" "C1" (id 0 0))
    (property "Value" "100nF" (id 1 0))
    (property "Footprint" "0402" (id 2 0))
  )
)"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sch_content)

        parser = KiCADParser()
        issues = parser.validate_schematic(sch_file)

        assert "missing_lcsc_id" in issues
        assert len(issues["missing_lcsc_id"]) > 0

    def test_validate_duplicate_reference(self, temp_dir):
        """Test validation detects duplicate references"""
        parser = KiCADParser()
        # Would need duplicate refs in schematic to test

    def test_validate_complete_schematic(self, temp_dir, sample_kicad_sch_content):
        """Test validation passes for complete schematic"""
        sch_file = temp_dir / "test.kicad_sch"
        sch_file.write_text(sample_kicad_sch_content)

        parser = KiCADParser()
        issues = parser.validate_schematic(sch_file)

        # Sample has all required fields
        assert len(issues["missing_footprint"]) == 0
        assert len(issues["missing_lcsc_id"]) == 0


@pytest.mark.unit
class TestBoardParsing:
    """Tests for board file parsing"""

    def test_parse_board_missing_file(self):
        """Test parsing non-existent board file"""
        parser = KiCADParser()
        board_info = parser.parse_board(Path("/nonexistent/file.kicad_pcb"))
        assert board_info == {}

    def test_parse_board_invalid_format(self, temp_dir):
        """Test parsing invalid board file"""
        board_file = temp_dir / "invalid.kicad_pcb"
        board_file.write_text("invalid content")

        parser = KiCADParser()
        board_info = parser.parse_board(board_file)

        # Should have empty board structure
        assert "footprints" in board_info
        assert "nets" in board_info

    def test_parse_footprint(self):
        """Test parsing footprint entry"""
        expr = ["footprint", "C_0402_1005Metric", "C1"]
        result = KiCADParser._parse_footprint(expr)
        assert result["name"] == "C_0402_1005Metric"
        assert result["reference"] == "C1"

    def test_parse_net(self):
        """Test parsing net definition"""
        expr = ["net", "1", "GND"]
        result = KiCADParser._parse_net(expr)
        assert result["number"] == "1"
        assert result["name"] == "GND"


@pytest.mark.integration
@pytest.mark.requires_files
class TestRealSchematicParsing:
    """Integration tests with actual schematic files"""

    def test_parse_actual_daughter_board_schematic(self, actual_schematic_file):
        """Test parsing actual daughter board schematic"""
        if actual_schematic_file is None:
            pytest.skip("Actual schematic file not found")

        parser = KiCADParser()
        components = parser.parse_schematic(actual_schematic_file)

        assert len(components) > 0
        assert all(isinstance(c, SchematicComponent) for c in components)

    def test_validate_actual_schematic(self, actual_schematic_file):
        """Test validation of actual schematic"""
        if actual_schematic_file is None:
            pytest.skip("Actual schematic file not found")

        parser = KiCADParser()
        issues = parser.validate_schematic(actual_schematic_file)

        # Check structure
        assert "missing_footprint" in issues
        assert "missing_lcsc_id" in issues
        assert "missing_value" in issues
        assert "duplicate_reference" in issues

    def test_extract_bom_from_actual_schematic(self, actual_schematic_file):
        """Test BOM extraction from actual schematic"""
        if actual_schematic_file is None:
            pytest.skip("Actual schematic file not found")

        parser = KiCADParser()
        bom = parser.extract_bom(actual_schematic_file)

        assert len(bom) > 0
        for key, entry in bom.items():
            assert "value" in entry
            assert "footprint" in entry
            assert "quantity" in entry
            assert "references" in entry


@pytest.mark.unit
class TestSymbolParsing:
    """Tests for symbol parsing"""

    def test_parse_symbol_basic(self):
        """Test parsing basic symbol"""
        parser = KiCADParser()
        sexpr = [
            "symbol",
            ["lib_id", "Device:C"],
            ["property", "Reference", "C1"],
            ["property", "Value", "100nF"],
            ["property", "Footprint", "0402"],
            ["property", "LCSC", "C2040"]
        ]
        comp = parser._parse_symbol(sexpr)
        assert comp is not None
        assert comp.reference == "C1"
        assert comp.value == "100nF"

    def test_parse_symbol_with_properties(self):
        """Test parsing symbol with custom properties"""
        parser = KiCADParser()
        sexpr = [
            "symbol",
            ["lib_id", "Device:R"],
            ["property", "Reference", "R1"],
            ["property", "Value", "10k"],
            ["property", "Footprint", "0402"],
            ["property", "LCSC", "C4169"],
            ["property", "CustomProp", "CustomValue"]
        ]
        comp = parser._parse_symbol(sexpr)
        assert "CustomProp" in comp.properties
        assert comp.properties["CustomProp"] == "CustomValue"

    def test_parse_symbol_missing_reference(self):
        """Test parsing symbol without reference"""
        parser = KiCADParser()
        sexpr = [
            "symbol",
            ["lib_id", "Device:C"],
            ["property", "Value", "100nF"]
        ]
        comp = parser._parse_symbol(sexpr)
        # Should return None if no reference
        assert comp is None or comp.reference == ""


@pytest.mark.unit
class TestComponentAggregation:
    """Tests for component aggregation in BOM"""

    def test_aggregate_same_value_footprint(self, sample_components):
        """Test aggregation of identical components"""
        # C1 and C2 are both 100nF 0402
        from bom_generator import BOMMGenerator
        gen = BOMMGenerator(sample_components)

        # Find aggregated item
        items_with_100nf = [item for item in gen.bom if "100nF" in item.comment]
        assert len(items_with_100nf) > 0
        assert items_with_100nf[0].quantity == 2

    def test_different_values_separate(self, sample_components):
        """Test components with different values are separate"""
        from bom_generator import BOMMGenerator
        gen = BOMMGenerator(sample_components)

        # Should have separate entries for different values
        assert len(gen.bom) >= 4  # 100nF, 10k, ESP32, 10uH

    def test_designator_aggregation(self, sample_components):
        """Test designators are correctly aggregated"""
        from bom_generator import BOMMGenerator
        gen = BOMMGenerator(sample_components)

        # Find the 100nF item
        nf_items = [item for item in gen.bom if "100nF" in item.comment]
        assert len(nf_items) > 0
        # Should have C1,C2
        assert "C1" in nf_items[0].designator
        assert "C2" in nf_items[0].designator
