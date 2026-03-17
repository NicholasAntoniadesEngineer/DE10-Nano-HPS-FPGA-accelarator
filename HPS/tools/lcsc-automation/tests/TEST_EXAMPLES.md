# Test Suite Examples

Real examples of how to use and understand the test suite.

## Test File Organization

### Configuration Tests (`test_config.py`)

**Happy Path**: Loading configuration
```python
def test_config_from_yaml(temp_dir):
    """Test loading config from YAML file"""
    yaml_content = """
lcsc:
  api_enabled: true
  api_key: test_key_123
  rate_limit_rpm: 150
"""
    # Write YAML, load config, verify values
    assert config.lcsc.api_enabled is True
    assert config.lcsc.api_key == "test_key_123"
```

**Error Case**: Missing YAML falls back to defaults
```python
def test_config_with_missing_yaml_fallback(temp_dir, monkeypatch):
    """Test config falls back to defaults when YAML missing"""
    # Config file doesn't exist
    # Should not raise exception
    config._load_config()
    # Should have defaults
    assert config.lcsc.api_enabled is False
```

**Edge Case**: Cache expiration
```python
def test_cache_expiration(isolated_config, monkeypatch):
    """Test cache expires after TTL"""
    test_data = {"key": "value"}
    isolated_config.save_cache("test.json", test_data)

    # Simulate 40-day-old file (TTL is 30 days)
    old_time = time.time() - (40 * 86400)
    cache_path = isolated_config.get_cache_path("test.json")
    os.utime(cache_path, (old_time, old_time))

    # Should return None (expired)
    loaded = isolated_config.load_cache("test.json")
    assert loaded is None
```

### Schematic Parsing Tests (`test_kicad_parser.py`)

**Happy Path**: Parse valid schematic
```python
def test_parse_schematic_sample(sample_kicad_sch_content, temp_dir):
    """Test parsing sample schematic"""
    # Create schematic file
    sch_file = temp_dir / "test.kicad_sch"
    sch_file.write_text(sample_kicad_sch_content)

    # Parse it
    parser = KiCADParser()
    components = parser.parse_schematic(sch_file)

    # Verify
    assert len(components) > 0
    assert components[0].reference == "C1"
    assert components[0].value == "100nF"
    assert components[0].lcsc_id == "C2040"
```

**Error Case**: Non-existent file
```python
def test_parse_schematic_missing_file():
    """Test parsing non-existent file"""
    parser = KiCADParser()
    components = parser.parse_schematic(Path("/nonexistent/file.kicad_sch"))

    # Should return empty list, not exception
    assert components == []
```

**Validation**: Check for missing fields
```python
def test_validate_missing_lcsc_id(temp_dir):
    """Test validation detects missing LCSC ID"""
    sch_content = """(kicad_sch
      (symbol (lib_id "Device:C") (at 100 100 0)
        (property "Reference" "C1" (id 0 0))
        (property "Value" "100nF" (id 1 0))
        (property "Footprint" "0402" (id 2 0))
        # Missing LCSC property
      )
    )"""
    sch_file = temp_dir / "test.kicad_sch"
    sch_file.write_text(sch_content)

    parser = KiCADParser()
    issues = parser.validate_schematic(sch_file)

    assert "missing_lcsc_id" in issues
    assert len(issues["missing_lcsc_id"]) > 0
```

### BOM Generation Tests (`test_bom_generator.py`)

**Happy Path**: Generate BOM with aggregation
```python
def test_bom_generation_aggregation(sample_components):
    """Test BOM aggregation by value+footprint"""
    gen = BOMMGenerator(sample_components)

    # C1 and C2 should be aggregated (both 100nF)
    nf_items = [item for item in gen.bom if "100nF" in item.comment]
    assert len(nf_items) == 1
    assert nf_items[0].quantity == 2
    assert nf_items[0].designator == "C1,C2"
```

**CSV Export**: Verify JLCPCB format
```python
def test_bom_csv_format_jlcpcb(sample_components, temp_dir):
    """Test BOM CSV follows JLCPCB format"""
    gen = BOMMGenerator(sample_components)
    output_file = temp_dir / "jlcpcb_bom.csv"

    gen.export_bom_csv(output_file)

    # Verify format
    rows = parse_csv(output_file)
    required = {"Comment", "Designator", "Footprint", "LCSC Part #"}
    actual_fields = set(rows[0].keys())
    assert required.issubset(actual_fields)
```

**Sorting**: Natural order (not lexicographic)
```python
def test_natural_sort_in_output(temp_dir):
    """Test output is naturally sorted"""
    components = [
        SchematicComponent("C10", "100nF", "0402", "C2040"),
        SchematicComponent("C2", "100nF", "0402", "C2040"),
        SchematicComponent("C1", "100nF", "0402", "C2040"),
        SchematicComponent("C20", "100nF", "0402", "C2040"),
    ]

    gen = BOMMGenerator(components)
    output_file = temp_dir / "sorting.csv"
    gen.export_bom_csv(output_file)

    rows = parse_csv(output_file)
    designators = rows[0]["Designator"].split(",")

    # Should be C1, C2, C10, C20 (not C1, C10, C2, C20)
    assert designators == ["C1", "C2", "C10", "C20"]
```

### Utility Function Tests (`test_utils.py`)

**LCSC ID Extraction**:
```python
def test_extract_standard_lcsc_id():
    """Test extracting LCSC IDs"""
    tests = [
        ("C2040", "C2040"),
        ("Capacitor C2040 100nF", "C2040"),
        ("LCSC ID C1234567", "C1234567"),
    ]
    for text, expected in tests:
        result = extract_lcsc_id(text)
        assert result == expected

def test_extract_lcsc_id_not_found():
    """Test extraction fails gracefully"""
    result = extract_lcsc_id("No part number here")
    assert result is None
```

**Value Parsing**:
```python
def test_parse_capacitor_value():
    """Test parsing capacitor values"""
    tests = [
        ("100nF", (100.0, "nF")),
        ("10uF", (10.0, "uF")),
        ("4.7nF", (4.7, "nF")),
    ]
    for text, (expected_val, expected_unit) in tests:
        value, unit = parse_value_with_unit(text)
        assert value == expected_val
        assert unit == expected_unit
```

**Natural Sorting**:
```python
def test_natural_sort_basic():
    """Test C1, C2, C10 ordering"""
    items = ["C1", "C2", "C10", "C20", "C3"]
    sorted_items = sorted(items, key=natural_sort_key)

    # Not: C1, C10, C2, C20, C3 (lexicographic)
    # But: C1, C2, C3, C10, C20 (natural)
    assert sorted_items == ["C1", "C2", "C3", "C10", "C20"]
```

**CSV Operations**:
```python
def test_csv_roundtrip(temp_dir):
    """Test write and read CSV"""
    csv_file = temp_dir / "roundtrip.csv"
    original = [
        {"Ref": "C1", "Val": "100nF", "Package": "0402"},
        {"Ref": "R1", "Val": "10k", "Package": "0402"},
    ]
    fieldnames = ["Ref", "Val", "Package"]

    # Write
    write_csv(csv_file, original, fieldnames)

    # Read back
    parsed = parse_csv(csv_file)

    # Verify
    assert len(parsed) == len(original)
    assert parsed[0]["Val"] == "100nF"
```

### Integration Tests (`test_integration.py`)

**Full Pipeline**:
```python
def test_full_pipeline_sample_schematic(sample_kicad_sch_content, temp_dir):
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

    # 4. Export CSV files
    output_dir = temp_dir / "manufacturing"
    bom_file = output_dir / "BOM.csv"
    cpl_file = output_dir / "CPL.csv"

    bom_gen.export_bom_csv(bom_file)
    bom_gen.export_cpl_csv(cpl_file)

    # 5. Verify outputs exist
    assert bom_file.exists()
    assert cpl_file.exists()

    # 6. Validate data
    bom_rows = parse_csv(bom_file)
    cpl_rows = parse_csv(cpl_file)

    assert len(bom_rows) > 0
    assert len(cpl_rows) > 0
```

**Data Integrity**:
```python
def test_component_data_preserved(sample_components, temp_dir):
    """Test data preserved through pipeline"""
    bom_gen = BOMMGenerator(sample_components)
    output_file = temp_dir / "test_bom.csv"
    bom_gen.export_bom_csv(output_file)

    rows = parse_csv(output_file)

    # Verify all components represented
    all_designators = []
    for row in rows:
        designators = row["Designator"].split(",")
        all_designators.extend(designators)

    # Total count should match
    assert len(all_designators) == len(sample_components)
```

**Error Recovery**:
```python
def test_invalid_schematic_recovery(temp_dir):
    """Test pipeline recovers from invalid schematic"""
    invalid_file = temp_dir / "invalid.kicad_sch"
    invalid_file.write_text("not valid s-expression")

    parser = KiCADParser()
    components = parser.parse_schematic(invalid_file)

    # Should return empty list, not crash
    assert components == []
```

## Using Test Fixtures

### Available Fixtures

From `conftest.py`:

```python
def test_with_temp_dir(temp_dir):
    """Auto-cleaned temporary directory"""
    output_file = temp_dir / "test.csv"
    output_file.write_text("test")
    assert output_file.exists()
    # Auto-cleaned after test

def test_with_sample_components(sample_components):
    """Pre-built test components"""
    assert len(sample_components) == 5
    assert sample_components[0].reference == "C1"

def test_with_kicad_content(sample_kicad_sch_content):
    """Valid s-expression schematic"""
    assert "(kicad_sch" in sample_kicad_sch_content
    assert "(symbol" in sample_kicad_sch_content

def test_with_real_file(actual_schematic_file):
    """Actual board schematic if available"""
    if actual_schematic_file is None:
        pytest.skip("Real file not available")
    # Use actual_schematic_file
```

## Test Markers

```python
@pytest.mark.unit
def test_fast_operation():
    """Unit test - runs quickly"""
    pass

@pytest.mark.integration
def test_full_pipeline():
    """Integration test - tests multiple modules"""
    pass

@pytest.mark.slow
def test_large_bom():
    """Performance test - takes time"""
    pass

@pytest.mark.requires_files
def test_real_schematic():
    """Requires actual project files"""
    if actual_schematic_file is None:
        pytest.skip("File not found")
```

## Running Examples

```bash
# Run all tests
pytest

# Run just unit tests (fast)
pytest -m unit

# Run just integration tests
pytest -m integration

# Run a specific example
pytest test_utils.py::TestLCSCIdExtraction::test_extract_standard_lcsc_id -v

# Run with coverage
pytest --cov=.. --cov-report=term-missing

# Show test output
pytest -s test_config.py

# Enter debugger on failure
pytest --pdb test_config.py
```

## Common Patterns

**Arrange-Act-Assert**:
```python
def test_example():
    # Arrange - setup
    input_data = "C2040"

    # Act - execute
    result = extract_lcsc_id(input_data)

    # Assert - verify
    assert result == "C2040"
```

**Testing Exceptions**:
```python
def test_invalid_file():
    with pytest.raises(FileNotFoundError):
        load_json_or_yaml(Path("/nonexistent/file.json"))
```

**Testing with Temporary Files**:
```python
def test_file_operations(temp_dir):
    test_file = temp_dir / "test.csv"
    # Write, read, verify
    test_file.write_text("data")
    # Auto-cleaned after test
```

**Parametrized Tests**:
```python
@pytest.mark.parametrize("lcsc_id,expected", [
    ("C2040", "C2040"),
    ("C1234567", "C1234567"),
])
def test_lcsc_ids(lcsc_id, expected):
    assert extract_lcsc_id(lcsc_id) == expected
```
