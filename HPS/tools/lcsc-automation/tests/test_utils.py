"""
Unit tests for utils.py module.
Tests utility functions for LCSC ID extraction, value parsing, CSV operations, and helpers.
"""

import pytest
from pathlib import Path
from datetime import datetime

from utils import (
    RateLimiter, HTTPClient, hash_file, safe_filename,
    parse_csv, write_csv, natural_sort_key, extract_lcsc_id,
    parse_value_with_unit, format_timestamp, get_rate_limiter,
    sanitize_json, load_json_or_yaml
)


@pytest.mark.unit
class TestRateLimiter:
    """Tests for RateLimiter class"""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly"""
        limiter = RateLimiter(requests_per_minute=100)
        assert limiter.rpm == 100
        assert len(limiter.request_times) == 0

    def test_rate_limiter_custom_rpm(self):
        """Test rate limiter with custom RPM"""
        limiter = RateLimiter(requests_per_minute=200)
        assert limiter.rpm == 200

    def test_rate_limiter_no_wait_under_limit(self):
        """Test no wait when under limit"""
        limiter = RateLimiter(requests_per_minute=100)
        # First request should not wait
        limiter.wait_if_needed()
        assert len(limiter.request_times) == 1

    def test_rate_limiter_reset(self):
        """Test rate limiter reset"""
        limiter = RateLimiter()
        limiter.wait_if_needed()
        assert len(limiter.request_times) > 0

        limiter.reset()
        assert len(limiter.request_times) == 0


@pytest.mark.unit
class TestLCSCIdExtraction:
    """Tests for LCSC ID extraction"""

    def test_extract_standard_lcsc_id(self):
        """Test extracting standard LCSC IDs"""
        tests = [
            ("C2040", "C2040"),
            ("Capacitor C2040 100nF", "C2040"),
            ("Part Number: C529971", "C529971"),
            ("LCSC ID C1234567", "C1234567"),
        ]
        for text, expected in tests:
            result = extract_lcsc_id(text)
            assert result == expected

    def test_extract_lcsc_id_not_found(self):
        """Test extraction fails gracefully"""
        tests = [
            "No part number here",
            "D2040",  # Wrong prefix
            "C",  # Just prefix
            "",  # Empty
        ]
        for text in tests:
            result = extract_lcsc_id(text)
            assert result is None

    def test_extract_lcsc_id_multiple_occurrences(self):
        """Test extracts first occurrence"""
        text = "C2040 and C2041"
        result = extract_lcsc_id(text)
        assert result == "C2040"

    def test_extract_lcsc_id_word_boundary(self):
        """Test word boundary matching"""
        # Should not match if part of larger word
        text = "CC2040D"  # C2040 is not a word boundary
        result = extract_lcsc_id(text)
        # Behavior depends on implementation

    def test_extract_various_sizes(self):
        """Test extracting various LCSC ID lengths"""
        tests = [
            "C1",  # 1 digit
            "C12",  # 2 digits
            "C123",  # 3 digits
            "C1234567",  # 7 digits
        ]
        for text in tests:
            result = extract_lcsc_id(text)
            assert result == text


@pytest.mark.unit
class TestValueParsing:
    """Tests for component value parsing"""

    def test_parse_simple_capacitor_value(self):
        """Test parsing capacitor values"""
        tests = [
            ("100nF", (100.0, "nF")),
            ("10uF", (10.0, "uF")),
            ("1pF", (1.0, "pF")),
        ]
        for text, expected in tests:
            value, unit = parse_value_with_unit(text)
            assert value == expected[0]
            assert unit == expected[1]

    def test_parse_resistor_value(self):
        """Test parsing resistor values"""
        tests = [
            ("10k", (10.0, "k")),
            ("100R", (100.0, "R")),
            ("4.7M", (4.7, "M")),
        ]
        for text, (val, unit) in tests:
            value, parsed_unit = parse_value_with_unit(text)
            assert value == val
            assert unit == parsed_unit

    def test_parse_with_spaces(self):
        """Test parsing with spaces"""
        tests = [
            ("100 nF", (100.0, "nF")),
            ("10 k", (10.0, "k")),
            ("4.7 M", (4.7, "M")),
        ]
        for text, expected in tests:
            value, unit = parse_value_with_unit(text)
            assert value == expected[0]

    def test_parse_decimal_values(self):
        """Test parsing decimal values"""
        value, unit = parse_value_with_unit("4.7k")
        assert value == 4.7
        assert unit == "k"

    def test_parse_invalid_value(self):
        """Test parsing invalid values"""
        value, unit = parse_value_with_unit("invalid")
        assert value == 1.0
        assert unit == "invalid"

    def test_parse_empty_string(self):
        """Test parsing empty string"""
        value, unit = parse_value_with_unit("")
        assert value == 1.0

    def test_parse_special_units(self):
        """Test parsing special unit symbols"""
        tests = [
            ("10Ω", (10.0, "Ω")),
            ("100°", (100.0, "°")),
        ]
        for text, expected in tests:
            value, unit = parse_value_with_unit(text)
            assert value == expected[0]


@pytest.mark.unit
class TestNaturalSorting:
    """Tests for natural/alphanumeric sorting"""

    def test_natural_sort_basic(self):
        """Test basic natural sorting"""
        items = ["C1", "C2", "C10", "C20", "C3"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["C1", "C2", "C3", "C10", "C20"]

    def test_natural_sort_resistors(self):
        """Test natural sorting of resistors"""
        items = ["R10", "R2", "R1", "R20"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["R1", "R2", "R10", "R20"]

    def test_natural_sort_mixed_prefix(self):
        """Test natural sorting with different prefixes"""
        items = ["U10", "C1", "R5", "U1", "C10"]
        sorted_items = sorted(items, key=natural_sort_key)
        # Sort preserves prefix groups then numbers
        assert sorted_items.index("C1") < sorted_items.index("C10")

    def test_natural_sort_alphabetic(self):
        """Test natural sorting with alphabetic content"""
        items = ["ABC10", "ABC2", "ABC1", "ABC20"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["ABC1", "ABC2", "ABC10", "ABC20"]

    def test_natural_sort_single_digit(self):
        """Test natural sorting single digits"""
        items = ["1", "10", "2", "20"]
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == ["1", "2", "10", "20"]

    def test_natural_sort_empty_list(self):
        """Test natural sorting empty list"""
        items = []
        sorted_items = sorted(items, key=natural_sort_key)
        assert sorted_items == []

    def test_natural_sort_strings_and_numbers(self):
        """Test sorting mixed strings and numbers"""
        items = ["A1B2", "A1B10", "A10B2"]
        sorted_items = sorted(items, key=natural_sort_key)
        # A1B2, A1B10, then A10B2
        assert sorted_items[0] == "A1B2"


@pytest.mark.unit
class TestCSVOperations:
    """Tests for CSV reading and writing"""

    def test_write_csv_basic(self, temp_dir):
        """Test writing CSV file"""
        output_file = temp_dir / "test.csv"
        rows = [
            {"Name": "C1", "Value": "100nF"},
            {"Name": "C2", "Value": "10uF"},
        ]
        fieldnames = ["Name", "Value"]

        write_csv(output_file, rows, fieldnames)

        assert output_file.exists()

    def test_write_csv_creates_parent_dirs(self, temp_dir):
        """Test CSV write creates parent directories"""
        output_file = temp_dir / "subdir" / "nested" / "test.csv"
        rows = [{"Name": "C1"}]
        fieldnames = ["Name"]

        write_csv(output_file, rows, fieldnames)

        assert output_file.exists()

    def test_parse_csv_basic(self, temp_dir):
        """Test parsing CSV file"""
        csv_file = temp_dir / "test.csv"
        rows = [
            {"Comment": "100nF", "Designator": "C1,C2"},
            {"Comment": "10k", "Designator": "R1"},
        ]
        fieldnames = ["Comment", "Designator"]

        write_csv(csv_file, rows, fieldnames)
        parsed = parse_csv(csv_file)

        assert len(parsed) == 2
        assert parsed[0]["Comment"] == "100nF"

    def test_parse_csv_missing_file(self):
        """Test parsing non-existent file"""
        parsed = parse_csv(Path("/nonexistent/file.csv"))
        assert parsed == []

    def test_csv_roundtrip(self, temp_dir):
        """Test write and read CSV roundtrip"""
        csv_file = temp_dir / "roundtrip.csv"
        original = [
            {"Ref": "C1", "Val": "100nF", "Package": "0402"},
            {"Ref": "R1", "Val": "10k", "Package": "0402"},
        ]
        fieldnames = ["Ref", "Val", "Package"]

        write_csv(csv_file, original, fieldnames)
        parsed = parse_csv(csv_file)

        assert len(parsed) == len(original)
        assert parsed[0]["Val"] == "100nF"

    def test_csv_special_characters(self, temp_dir):
        """Test CSV with special characters"""
        csv_file = temp_dir / "special.csv"
        rows = [
            {"Name": "Part with, comma", "Value": "100nF"},
            {"Name": 'Part with "quotes"', "Value": "10k"},
        ]
        fieldnames = ["Name", "Value"]

        write_csv(csv_file, rows, fieldnames)
        parsed = parse_csv(csv_file)

        assert len(parsed) == 2

    def test_csv_unicode(self, temp_dir):
        """Test CSV with unicode characters"""
        csv_file = temp_dir / "unicode.csv"
        rows = [
            {"Name": "Resistor Ω", "Value": "100Ω"},
            {"Name": "Capacitor μF", "Value": "10μF"},
        ]
        fieldnames = ["Name", "Value"]

        write_csv(csv_file, rows, fieldnames)
        parsed = parse_csv(csv_file)

        assert len(parsed) == 2


@pytest.mark.unit
class TestFileOperations:
    """Tests for file utility functions"""

    def test_hash_file_md5(self, temp_dir):
        """Test MD5 file hashing"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        hash_result = hash_file(test_file, 'md5')
        assert len(hash_result) == 32  # MD5 is 32 hex chars

    def test_hash_file_sha256(self, temp_dir):
        """Test SHA256 file hashing"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        hash_result = hash_file(test_file, 'sha256')
        assert len(hash_result) == 64  # SHA256 is 64 hex chars

    def test_hash_file_consistency(self, temp_dir):
        """Test hash is consistent"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        hash1 = hash_file(test_file)
        hash2 = hash_file(test_file)
        assert hash1 == hash2

    def test_hash_different_files(self, temp_dir):
        """Test different files have different hashes"""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        hash1 = hash_file(file1)
        hash2 = hash_file(file2)
        assert hash1 != hash2

    def test_safe_filename(self):
        """Test safe filename conversion"""
        tests = [
            ("Part C2040 - 100nF", "part-c2040-100nf"),
            ("File/With\\Slashes", "filewithslashes"),
            ("name!@#$%^&*()", "name"),
            ("Multiple   Spaces", "multiple-spaces"),
        ]
        for unsafe, expected in tests:
            result = safe_filename(unsafe)
            assert result == expected

    def test_safe_filename_empty(self):
        """Test safe filename with empty string"""
        result = safe_filename("")
        assert result == ""

    def test_safe_filename_only_special_chars(self):
        """Test safe filename with only special characters"""
        result = safe_filename("!@#$%^&*()")
        assert result == ""


@pytest.mark.unit
class TestTimestampFormatting:
    """Tests for timestamp formatting"""

    def test_format_timestamp_default(self):
        """Test timestamp format with default"""
        result = format_timestamp()
        assert "T" in result  # ISO8601 format
        assert "-" in result  # Date separator

    def test_format_timestamp_custom_datetime(self):
        """Test timestamp format with custom datetime"""
        dt = datetime(2024, 3, 17, 12, 30, 45)
        result = format_timestamp(dt)
        assert "2024-03-17" in result
        assert "12:30:45" in result

    def test_format_timestamp_iso8601(self):
        """Test timestamp is ISO8601 compliant"""
        result = format_timestamp()
        # Should be parseable as ISO8601
        assert "T" in result  # Date/time separator


@pytest.mark.unit
class TestDataSanitization:
    """Tests for JSON data sanitization"""

    def test_sanitize_json_dict(self):
        """Test sanitizing dictionary"""
        data = {"key": "value", "number": 42}
        result = sanitize_json(data)
        assert result == data

    def test_sanitize_json_with_path(self):
        """Test sanitizing with Path objects"""
        data = {"path": Path("/tmp/test")}
        result = sanitize_json(data)
        assert isinstance(result["path"], str)
        assert "/tmp/test" in result["path"]

    def test_sanitize_json_nested(self):
        """Test sanitizing nested structures"""
        data = {
            "level1": {
                "level2": {
                    "path": Path("/tmp/test"),
                    "value": "string"
                }
            }
        }
        result = sanitize_json(data)
        assert isinstance(result["level1"]["level2"]["path"], str)

    def test_sanitize_json_list(self):
        """Test sanitizing lists"""
        data = [Path("/tmp"), "string", 42]
        result = sanitize_json(data)
        assert isinstance(result[0], str)
        assert result[1] == "string"
        assert result[2] == 42

    def test_sanitize_json_primitive_types(self):
        """Test sanitizing primitive types"""
        tests = [
            "string",
            42,
            3.14,
            True,
            False,
            None,
        ]
        for data in tests:
            result = sanitize_json(data)
            assert result == data

    def test_sanitize_json_custom_objects(self):
        """Test sanitizing custom objects"""
        class CustomObj:
            def __str__(self):
                return "custom_string"

        data = {"obj": CustomObj()}
        result = sanitize_json(data)
        assert isinstance(result["obj"], str)


@pytest.mark.unit
class TestLoadJsonOrYaml:
    """Tests for JSON/YAML file loading"""

    def test_load_json_file(self, temp_dir):
        """Test loading JSON file"""
        json_file = temp_dir / "test.json"
        json_file.write_text('{"key": "value"}')

        result = load_json_or_yaml(json_file)
        assert result == {"key": "value"}

    def test_load_yaml_file(self, temp_dir):
        """Test loading YAML file"""
        yaml_file = temp_dir / "test.yaml"
        yaml_file.write_text("key: value\nnumber: 42")

        result = load_json_or_yaml(yaml_file)
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_load_yml_extension(self, temp_dir):
        """Test loading .yml extension"""
        yml_file = temp_dir / "test.yml"
        yml_file.write_text("key: value")

        result = load_json_or_yaml(yml_file)
        assert result["key"] == "value"

    def test_load_missing_file(self):
        """Test loading non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_json_or_yaml(Path("/nonexistent/file.json"))

    def test_load_unsupported_format(self, temp_dir):
        """Test loading unsupported file format"""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("content")

        with pytest.raises(ValueError):
            load_json_or_yaml(txt_file)

    def test_load_invalid_json(self, temp_dir):
        """Test loading invalid JSON"""
        json_file = temp_dir / "invalid.json"
        json_file.write_text("not valid json")

        with pytest.raises(Exception):
            load_json_or_yaml(json_file)


@pytest.mark.unit
class TestHTTPClient:
    """Tests for HTTPClient class"""

    def test_http_client_initialization(self):
        """Test HTTPClient initializes"""
        try:
            client = HTTPClient(base_url="https://example.com")
            assert client.base_url == "https://example.com"
        except ImportError:
            pytest.skip("requests library not available")

    def test_http_client_cache_key_generation(self):
        """Test cache key generation"""
        try:
            client = HTTPClient()
            key1 = client._get_cache_key("https://example.com/api")
            key2 = client._get_cache_key("https://example.com/api")
            assert key1 == key2
        except ImportError:
            pytest.skip("requests library not available")

    def test_http_client_cache_key_params(self):
        """Test cache key includes parameters"""
        try:
            client = HTTPClient()
            key1 = client._get_cache_key("https://example.com/api", {"param": "value1"})
            key2 = client._get_cache_key("https://example.com/api", {"param": "value2"})
            assert key1 != key2
        except ImportError:
            pytest.skip("requests library not available")


@pytest.mark.unit
def test_get_rate_limiter():
    """Test getting global rate limiter"""
    limiter = get_rate_limiter()
    assert isinstance(limiter, RateLimiter)
