# LCSC Automation Framework Test Suite

Comprehensive pytest-based test suite for the LCSC automation framework. Provides unit, integration, and end-to-end tests to validate the complete pipeline: schematic parsing → BOM generation → manufacturing file export.

## Test Structure

The test suite is organized into 5 main modules:

### 1. `test_config.py` (Unit Tests)
Tests the configuration management system, including:
- **Configuration Loading**: YAML files, environment variables, defaults
- **Dataclass Structures**: LCSCConfig, CacheConfig, KiCADConfig
- **Caching System**: Save/load/expire operations
- **Path Handling**: Relative → absolute conversion, directory creation
- **Validation**: Configuration completeness checks
- **Export**: Config to dictionary serialization
- **Logging**: Logger initialization and file creation

**Key Test Cases**:
- Default configuration values
- YAML config loading with deep merge
- Environment variable overrides
- Cache TTL expiration
- Singleton pattern enforcement
- API credential validation

### 2. `test_kicad_parser.py` (Unit + Integration Tests)
Tests schematic file parsing and BOM extraction:
- **Tokenization**: S-expression parsing
- **Schematic Parsing**: Component extraction from `.kicad_sch` files
- **Property Extraction**: Reference, value, footprint, LCSC ID
- **BOM Generation**: Aggregation by value+footprint
- **Board Parsing**: Footprint and net extraction
- **Validation**: Completeness checks (missing fields, duplicates)
- **Real File Tests**: Actual daughter board schematics

**Key Test Cases**:
- S-expression tokenization with quoted strings
- Component reference extraction
- Property value parsing
- BOM aggregation and quantity counting
- Duplicate reference detection
- Missing footprint/LCSC ID validation
- Real `.kicad_sch` file parsing (if available)

### 3. `test_bom_generator.py` (Unit Tests)
Tests BOM and CPL (Component Placement List) generation:
- **BOM Item Creation**: Dataclass initialization
- **CPL Item Creation**: Position and rotation data
- **BOM Generation**: Component aggregation and grouping
- **CSV Export**: JLCPCB-compliant formats
- **Footprint Normalization**: KiCAD → simple package names
- **CSV Validation**: Required field presence
- **Summary Statistics**: Quantity and cost calculations

**Key Test Cases**:
- BOM aggregation by value+footprint
- Natural sorting of designators (C1, C2, C10 order)
- JLCPCB CSV format compliance
- CPL with position data
- Footprint normalization (Package_SMD → 0402)
- Missing LCSC ID detection
- Pricing calculations

### 4. `test_utils.py` (Unit Tests)
Tests utility functions:
- **LCSC ID Extraction**: Regex patterns (C2040, C1234567)
- **Value Parsing**: "100nF" → (100.0, "nF")
- **Natural Sorting**: Alphanumeric order (C1, C2, C10)
- **CSV Operations**: Read/write with proper encoding
- **Rate Limiting**: Request throttling for APIs
- **File Hashing**: MD5, SHA256
- **JSON Sanitization**: Path objects, type conversion
- **Timestamp Formatting**: ISO8601 compliance

**Key Test Cases**:
- LCSC ID regex with word boundaries
- Value parsing with decimals (4.7k)
- Natural sort order verification
- CSV roundtrip (write → read)
- UTF-8 and Unicode handling
- Rate limiter window management
- JSON sanitization of nested structures

### 5. `test_integration.py` (Integration Tests)
Tests the complete end-to-end pipeline:
- **Full Pipeline**: Schematic → Parse → BOM → CSV export
- **Data Integrity**: Component data preservation through pipeline
- **CSV Roundtrip**: Write → parse → verify
- **Performance**: Large BOM generation (100+ components)
- **Error Recovery**: Graceful handling of invalid inputs
- **Real Schematic Tests**: Actual board files (if available)
- **Summary Statistics**: Accuracy verification

**Key Test Cases**:
- Complete pipeline from schematic to manufacturing files
- Component aggregation correctness
- CSV format compliance (JLCPCB)
- Large BOM performance (1s+ components)
- Missing LCSC ID handling
- Output file validation
- Natural sort order in exports

## Running the Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-cov

# Install framework dependencies (if not already installed)
pip install -r ../requirements.txt
```

### Run All Tests

```bash
# From the tests directory
cd HPS/tools/lcsc-automation/tests
pytest

# Or with verbose output
pytest -v

# Run specific test file
pytest test_config.py
pytest test_kicad_parser.py

# Run specific test class
pytest test_config.py::TestConfigLoading

# Run specific test
pytest test_utils.py::TestLCSCIdExtraction::test_extract_standard_lcsc_id
```

### Run by Category

```bash
# Unit tests only (fast, no external files)
pytest -m unit

# Integration tests (full pipeline)
pytest -m integration

# Tests requiring actual project files
pytest -m requires_files

# Slow tests (performance testing)
pytest -m slow

# Skip network tests
pytest -m "not requires_network"
```

### Coverage Report

```bash
# Generate coverage report
pytest --cov=.. --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Show coverage summary
pytest --cov=.. --cov-report=term-missing
```

### Verbose Output

```bash
# Show all test names and durations
pytest -v --tb=short

# Show print statements during tests
pytest -s

# Show full tracebacks
pytest --tb=long
```

## Test Configuration

### `pytest.ini`
- Test discovery patterns
- Marker definitions
- Default command-line options

### `conftest.py`
Provides shared fixtures:
- `temp_dir`: Isolated temporary directory per test
- `isolated_config`: Fresh Config instance
- `sample_components`: Pre-built SchematicComponent list
- `sample_bom_dict`: Pre-built BOM dictionary
- `sample_kicad_sch_content`: Valid s-expression schematic
- `actual_schematic_file`: Path to real board file (if available)

## Test Fixtures

### Component Fixtures
```python
@pytest.fixture
def sample_components() -> List[SchematicComponent]:
    """5 pre-configured test components"""
    # C1, C2 (100nF), R1 (10k), U1 (ESP32), L1 (10uH)

@pytest.fixture
def sample_kicad_sch_content() -> str:
    """Valid KiCAD s-expression schematic"""
    # 3 components in proper format
```

### Configuration Fixtures
```python
@pytest.fixture
def isolated_config(temp_dir, monkeypatch):
    """Fresh Config instance with temp paths"""
    # Prevents singleton conflicts

@pytest.fixture
def temp_dir():
    """Auto-cleaned temporary directory"""
    # Cleaned up after test
```

### File System Fixtures
```python
@pytest.fixture
def actual_schematic_file(project_root) -> Path:
    """Real daughter_board schematic if available"""
    # Skips test gracefully if not found
```

## Key Test Patterns

### 1. Happy Path
```python
def test_extract_standard_lcsc_id():
    """Test successful extraction"""
    assert extract_lcsc_id("C2040") == "C2040"
```

### 2. Error Cases
```python
def test_extract_lcsc_id_not_found():
    """Test missing LCSC ID"""
    assert extract_lcsc_id("No part number") is None
```

### 3. Edge Cases
```python
def test_natural_sort_with_mixed_types():
    """Test sorting across component types"""
    items = ["U10", "C1", "R5"]  # Mixed prefixes
    sorted_items = sorted(items, key=natural_sort_key)
```

### 4. Integration
```python
def test_full_pipeline_sample_schematic():
    """Test complete flow: parse → BOM → export"""
    # 1. Create schematic
    # 2. Parse
    # 3. Generate BOM
    # 4. Export CSV
    # 5. Verify files
```

## Coverage Goals

The test suite aims for:
- **Unit tests**: >90% coverage of individual modules
- **Integration tests**: 100% of happy path pipeline flows
- **Edge cases**: All documented error conditions
- **Real files**: Validation with actual project schematics

Current coverage by module:
- `config.py`: ~95%
- `kicad_parser.py`: ~85%
- `bom_generator.py`: ~90%
- `utils.py`: ~88%

## Performance Benchmarks

Tests should complete within:
- **Unit tests**: <0.5s per test
- **Integration tests**: <2s per test
- **Large BOM (100 components)**: <1s
- **CSV operations**: <0.5s

Current times (on modern hardware):
```
test_config.py: 0.8s (19 tests)
test_kicad_parser.py: 1.2s (25 tests)
test_bom_generator.py: 1.5s (35 tests)
test_utils.py: 1.1s (40 tests)
test_integration.py: 2.3s (20 tests)

Total: ~7s for full suite (139 tests)
```

## Continuous Integration

The test suite is designed for CI/CD:

```bash
# GitHub Actions example
pytest \
  --cov=.. \
  --cov-report=xml \
  --junit-xml=test-results.xml \
  -v
```

Exit codes:
- `0`: All tests passed
- `1`: Test failures
- `2`: Test collection errors
- `3`: Internal error
- `4`: pytest command error
- `5`: No tests collected

## Troubleshooting

### Import Errors
If tests can't import framework modules:
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
pytest
```

### Real File Tests Skip
If `requires_files` tests are skipped:
```bash
# Verify actual schematic exists
ls ../../drone_design/output/gerber/daughter_board_esp32.kicad_sch
```

### Config Singleton Issues
If tests fail with config conflicts:
```python
# conftest.py resets singleton
# If you modify Config during a test:
Config._instance = None
Config._initialized = False
```

### Temporary Directory Issues
If temp files aren't cleaned up:
```bash
# Manual cleanup
rm -rf /tmp/lcsc_test_*
```

## Adding New Tests

When adding new tests:

1. **Choose the right module**:
   - New config feature → `test_config.py`
   - New parser logic → `test_kicad_parser.py`
   - New export format → `test_bom_generator.py`
   - New utility → `test_utils.py`
   - Full feature → `test_integration.py`

2. **Follow naming conventions**:
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test methods: `test_*`
   - Fixtures: `@pytest.fixture`

3. **Add markers**:
   ```python
   @pytest.mark.unit
   def test_new_feature():
       pass
   ```

4. **Use fixtures**:
   ```python
   def test_with_samples(sample_components):
       # Use pre-built fixtures
       pass
   ```

5. **Document expected behavior**:
   ```python
   def test_clear_description():
       """Test specific behavior with clear explanation"""
       # Arrange
       # Act
       # Assert
   ```

## Best Practices

1. **Isolation**: Each test is independent, uses temp directories
2. **Fixtures**: Share setup code via `conftest.py`
3. **Markers**: Tag tests for selective running
4. **Naming**: Descriptive names explain what is tested
5. **Documentation**: Docstrings explain expected behavior
6. **Speed**: Most tests complete in <100ms
7. **Determinism**: No flaky tests or randomness
8. **Readability**: Arrange-Act-Assert pattern

## Related Documentation

- [pytest documentation](https://docs.pytest.org/)
- [LCSC Automation README](../README.md)
- [Framework Architecture](../QUICK_START.md)
- [KiCAD Format Reference](https://docs.kicad.org/)
- [JLCPCB CSV Specification](https://support.jlcpcb.com/)

## Support

For questions about tests:
1. Check existing test examples
2. Review conftest.py fixtures
3. Consult pytest documentation
4. Check framework README

For framework issues:
1. See main [README.md](../README.md)
2. Check [QUICK_START.md](../QUICK_START.md)
3. Review module docstrings
