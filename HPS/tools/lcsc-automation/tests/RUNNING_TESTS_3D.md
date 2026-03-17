# Running 3D Model Linking Tests

**Test File:** `test_library_manager_3d.py`
**Total Tests:** 33
**Pass Rate:** 100% (33/33)
**Execution Time:** ~70ms
**Status:** Ready for production

## Quick Start

### Run All Tests
```bash
cd /HPS/tools/lcsc-automation
pytest tests/test_library_manager_3d.py -v
```

### Expected Output
```
tests/test_library_manager_3d.py::TestFootprintModeling::test_link_3d_model_single_step_file PASSED
tests/test_library_manager_3d.py::TestFootprintModeling::test_link_3d_model_prefers_step_over_wrl PASSED
[... 31 more tests ...]
======================== 33 passed in 0.06s =========================
```

## Running Specific Tests

### By Test Class
```bash
# All footprint modeling tests
pytest tests/test_library_manager_3d.py::TestFootprintModeling -v

# All s-expression parsing tests
pytest tests/test_library_manager_3d.py::TestSExpressionParsing -v

# All edge case tests
pytest tests/test_library_manager_3d.py::TestEdgeCases -v

# All batch linking tests
pytest tests/test_library_manager_3d.py::TestBatchLinking -v

# All integration tests
pytest tests/test_library_manager_3d.py::TestIntegrationWithLibraryManager -v
```

### By Specific Test
```bash
pytest tests/test_library_manager_3d.py::TestFootprintModeling::test_link_3d_model_single_step_file -v
```

### By Test Marker
```bash
# Run only unit tests
pytest tests/test_library_manager_3d.py -v -m unit

# Run only integration tests
pytest tests/test_library_manager_3d.py -v -m integration
```

## Advanced Options

### Show Slowest Tests
```bash
pytest tests/test_library_manager_3d.py -v --durations=10
```

### Show Full Traceback on Failures
```bash
pytest tests/test_library_manager_3d.py -v --tb=long
```

### Generate HTML Coverage Report
```bash
pytest tests/test_library_manager_3d.py -v --cov=library_manager --cov-report=html
# Open: htmlcov/index.html
```

### Run with Verbose Output
```bash
pytest tests/test_library_manager_3d.py -vv
```

### Run with Print Statements Shown
```bash
pytest tests/test_library_manager_3d.py -v -s
```

### Run All Tests with Coverage
```bash
pytest tests/test_library_manager_3d.py -v --cov=library_manager --cov-report=term-missing
```

## Test Organization

### Unit Tests (25 tests)
Test individual functions in isolation:
- **TestFootprintModeling** (8 tests) - Footprint 3D model integration
- **TestSExpressionParsing** (9 tests) - S-expression parsing and formatting
- **TestEdgeCases** (8 tests) - Error handling and boundary conditions

### Integration Tests (8 tests)
Test complete workflows:
- **TestBatchLinking** (4 tests) - Batch operations with multiple parts
- **TestIntegrationWithLibraryManager** (4 tests) - End-to-end library management

## Test Details

### TestFootprintModeling (8 tests)
Tests the core 3D model linking functionality:
- Single STEP file linking
- STEP preferred over VRML
- Relative path calculation
- Existing reference preservation
- Multiple model files per part
- Missing models handling
- Format preservation
- Valid ${KIPRJMOD} syntax

**Run:** `pytest tests/test_library_manager_3d.py::TestFootprintModeling -v`

### TestSExpressionParsing (9 tests)
Tests KiCAD s-expression parsing:
- Simple s-expressions
- Quoted string handling
- Nested structures
- Footprint structure parsing
- Model element detection
- Insertion point location
- Model entry formatting
- Model reference detection

**Run:** `pytest tests/test_library_manager_3d.py::TestSExpressionParsing -v`

### TestEdgeCases (8 tests)
Tests error handling and edge cases:
- Unusual footprint structures
- Duplicate prevention
- Special characters in paths
- Missing files
- Permission errors
- Malformed input
- Long paths
- Circular references

**Run:** `pytest tests/test_library_manager_3d.py::TestEdgeCases -v`

### TestBatchLinking (4 tests)
Tests batch operations:
- Multiple parts linking
- Partial failures
- Order preservation
- Performance (< 500ms/part avg)

**Run:** `pytest tests/test_library_manager_3d.py::TestBatchLinking -v`

### TestIntegrationWithLibraryManager (4 tests)
Tests end-to-end workflows:
- Single part pipeline
- Multiple parts pipeline
- 3D model references verification
- Validation integration

**Run:** `pytest tests/test_library_manager_3d.py::TestIntegrationWithLibraryManager -v`

## Troubleshooting

### Tests Not Found
```bash
# Make sure pytest is installed
pip install pytest pytest-cov

# Make sure you're in the right directory
cd /HPS/tools/lcsc-automation
```

### Import Errors
```bash
# Make sure conftest.py is in tests/ directory
ls tests/conftest.py

# Check PYTHONPATH includes parent directory
export PYTHONPATH=/HPS/tools/lcsc-automation:$PYTHONPATH
```

### Permission Errors
The `test_footprint_file_permission_denied` test modifies file permissions.
If it fails:
```bash
# Ensure the temp directory is writable
chmod 755 /tmp
```

### Timeout Issues
Some tests create many files. If tests hang:
```bash
# Run with explicit timeout
pytest tests/test_library_manager_3d.py -v --timeout=30
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Test 3D Models
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt pytest
      - run: pytest tests/test_library_manager_3d.py -v --tb=short
```

### GitLab CI Example
```yaml
test_3d_models:
  stage: test
  image: python:3.9
  script:
    - cd HPS/tools/lcsc-automation
    - pip install -r requirements.txt pytest
    - pytest tests/test_library_manager_3d.py -v --tb=short
```

## Performance Benchmarks

| Operation | Time | Status |
|-----------|------|--------|
| Single model link | < 1ms | ✅ |
| Batch (10 parts) | ~10ms | ✅ |
| Per-part average | < 1ms | ✅ |
| Full suite (33 tests) | ~70ms | ✅ |

## Test Data & Fixtures

All tests use:
- **`temp_dir` fixture** - Isolated temporary directory per test
- **In-test generated files** - Real KiCAD files (not mocks)
- **Automatic cleanup** - No filesystem pollution

Test data includes:
- KiCAD footprint files (.kicad_mod)
- 3D model files (.step, .wrl)
- Symbol files (.kicad_sym)
- Complete directory structure (footprints/, 3dmodels/, symbols/)

## Key Test Validations

### 1. Model Linking
```python
assert "(model " in footprint_content
assert "../../3dmodels/C2040_PAD1206.step" in footprint_content
assert "(offset (xyz 0 0 0))" in footprint_content
```

### 2. Path Calculation
```python
assert rel_path == Path("..") / ".." / "3dmodels" / model_name
assert "/" in str(rel_path)  # Forward slashes
assert "\\" not in str(rel_path)  # No backslashes
```

### 3. Format Preference
```python
# STEP preferred over VRML
assert "C2040_PAD1206.step" in content
assert ".wrl" not in content
```

### 4. No Overwrite
```python
# Existing models preserved
assert existing_model in content
assert new_model not in content
```

## Files & Documentation

- **Test File:** `/HPS/tools/lcsc-automation/tests/test_library_manager_3d.py` (912 lines)
- **Summary:** `/HPS/tools/lcsc-automation/tests/TEST_3D_MODELS_SUMMARY.md`
- **This Guide:** `/HPS/tools/lcsc-automation/tests/RUNNING_TESTS_3D.md`

## Contributing

To add new tests:

1. Add test method to appropriate class:
   ```python
   def test_new_scenario(self, temp_dir):
       """Test description"""
       from library_manager import KiCADLibraryManager
       mgr = KiCADLibraryManager(library_base_dir=temp_dir)

       # Create test data
       # Run test
       # Assert results
   ```

2. Use descriptive names starting with `test_`
3. Add docstring explaining what's tested
4. Use `@pytest.mark.unit` or `@pytest.mark.integration`
5. Use `temp_dir` fixture for file operations
6. Run full suite to ensure no regressions:
   ```bash
   pytest tests/test_library_manager_3d.py -v
   ```

## Maintenance

### Updating Tests
When library_manager.py changes:
1. Run tests: `pytest tests/test_library_manager_3d.py -v`
2. Update tests if behavior changes
3. Add new tests for new functionality
4. Verify all 33 tests still pass

### Adding Coverage
Check coverage gaps:
```bash
pytest tests/test_library_manager_3d.py -v \
  --cov=library_manager \
  --cov-report=html \
  --cov-report=term-missing
```

## Support

For test issues:
1. Check the test file: `test_library_manager_3d.py`
2. Read test docstrings for expected behavior
3. Check error messages and tracebacks
4. Review `TEST_3D_MODELS_SUMMARY.md` for details
5. Run with `-vv` flag for verbose output

## Summary

The test suite provides **comprehensive, maintainable coverage** of 3D model linking:
- ✅ 33 tests covering all major functionality
- ✅ 100% pass rate
- ✅ ~70ms execution time
- ✅ Real file-based testing
- ✅ Complete edge case coverage
- ✅ Performance validation
- ✅ Ready for production use

Run tests immediately with:
```bash
pytest tests/test_library_manager_3d.py -v
```
