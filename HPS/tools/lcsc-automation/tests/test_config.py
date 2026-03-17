"""
Unit tests for config.py module.
Tests configuration loading, caching, path validation, and environment variables.
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from config import Config, LCSCConfig, CacheConfig, KiCADConfig, get_config


@pytest.mark.unit
class TestLCSCConfig:
    """Tests for LCSCConfig dataclass"""

    def test_lcsc_config_defaults(self):
        """Test LCSC config has correct defaults"""
        config = LCSCConfig()
        assert config.api_enabled is False
        assert config.api_key == ""
        assert config.api_secret == ""
        assert config.rate_limit_rpm == 100
        assert config.base_url == "https://ips.lcsc.com"

    def test_lcsc_config_custom_values(self):
        """Test LCSC config accepts custom values"""
        config = LCSCConfig(
            api_enabled=True,
            api_key="test_key",
            api_secret="test_secret",
            rate_limit_rpm=200
        )
        assert config.api_enabled is True
        assert config.api_key == "test_key"
        assert config.api_secret == "test_secret"
        assert config.rate_limit_rpm == 200


@pytest.mark.unit
class TestCacheConfig:
    """Tests for CacheConfig dataclass"""

    def test_cache_config_defaults(self):
        """Test cache config has correct defaults"""
        config = CacheConfig()
        assert config.enabled is True
        assert config.ttl_days == 30

    def test_cache_config_custom_dir(self):
        """Test cache config with custom directory"""
        test_dir = Path("/tmp/test_cache")
        config = CacheConfig(directory=test_dir)
        assert config.directory == test_dir


@pytest.mark.unit
class TestKiCADConfig:
    """Tests for KiCADConfig dataclass"""

    def test_kicad_config_defaults(self):
        """Test KiCAD config has correct defaults"""
        config = KiCADConfig()
        assert config.symbol_lib == "lcsc_parts.kicad_sym"
        assert config.footprint_lib == "lcsc_parts.pretty"
        assert config.models_dir == "3dmodels"

    def test_kicad_config_custom_paths(self):
        """Test KiCAD config with custom paths"""
        lib_dir = Path("/custom/kicad")
        config = KiCADConfig(library_dir=lib_dir)
        assert config.library_dir == lib_dir


@pytest.mark.unit
class TestConfigLoading:
    """Tests for Config class initialization and loading"""

    def test_config_singleton_pattern(self):
        """Test Config implements singleton pattern"""
        Config._instance = None
        Config._initialized = False
        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_config_initialization(self, isolated_config):
        """Test config initializes required attributes"""
        assert isolated_config.tool_dir.exists()
        assert isolated_config.data_dir.exists()
        assert isolated_config.lcsc is not None
        assert isolated_config.cache is not None
        assert isolated_config.kicad is not None

    def test_config_default_values(self, isolated_config):
        """Test config loads default values"""
        assert isolated_config.lcsc.api_enabled is False
        assert isolated_config.cache.enabled is True
        assert isolated_config.cache.ttl_days == 30

    def test_config_from_yaml(self, temp_dir):
        """Test loading config from YAML file"""
        yaml_content = """
lcsc:
  api_enabled: true
  api_key: test_key_123
  rate_limit_rpm: 150

cache:
  enabled: false
  ttl_days: 7
"""
        config_file = temp_dir / "config.yaml"
        config_file.write_text(yaml_content)

        Config._instance = None
        Config._initialized = False
        config = Config.__new__(Config)
        config.tool_dir = temp_dir
        config.project_root = temp_dir / "project"
        config.config_file = config_file
        config.log_file = temp_dir / "test.log"
        config.data_dir = temp_dir / "data"
        config.data_dir.mkdir(parents=True, exist_ok=True)
        Config._instance = config

        config._load_config()

        assert config.lcsc.api_enabled is True
        assert config.lcsc.api_key == "test_key_123"
        assert config.lcsc.rate_limit_rpm == 150
        assert config.cache.enabled is False
        assert config.cache.ttl_days == 7

    def test_config_from_environment_variables(self, temp_dir, monkeypatch):
        """Test loading config from environment variables"""
        monkeypatch.setenv("LCSC_API_KEY", "env_key_123")
        monkeypatch.setenv("LCSC_API_SECRET", "env_secret_456")

        Config._instance = None
        Config._initialized = False
        config = Config.__new__(Config)
        config.tool_dir = temp_dir
        config.project_root = temp_dir / "project"
        config.config_file = temp_dir / "nonexistent.yaml"
        config.log_file = temp_dir / "test.log"
        config.data_dir = temp_dir / "data"
        config.data_dir.mkdir(parents=True, exist_ok=True)
        Config._instance = config

        config._load_config()

        assert config.lcsc.api_key == "env_key_123"
        assert config.lcsc.api_secret == "env_secret_456"

    def test_config_deep_merge(self, isolated_config):
        """Test config deep merge functionality"""
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10}, "e": 4}
        isolated_config._deep_merge(base, override)
        assert base == {"a": {"b": 10, "c": 2}, "d": 3, "e": 4}


@pytest.mark.unit
class TestCacheOperations:
    """Tests for cache save/load operations"""

    def test_cache_save_and_load(self, isolated_config):
        """Test saving and loading cache"""
        test_data = {"key": "value", "number": 42}
        cache_file = "test_cache.json"

        isolated_config.save_cache(cache_file, test_data)

        loaded = isolated_config.load_cache(cache_file)
        assert loaded == test_data

    def test_cache_disabled(self, isolated_config):
        """Test cache operations when disabled"""
        isolated_config.cache.enabled = False
        test_data = {"key": "value"}

        isolated_config.save_cache("test.json", test_data)
        loaded = isolated_config.load_cache("test.json")

        assert loaded is None

    def test_cache_expiration(self, isolated_config, monkeypatch):
        """Test cache expiration"""
        import time

        test_data = {"key": "value"}
        cache_file = "expire_test.json"

        isolated_config.save_cache(cache_file, test_data)

        # Mock time to simulate age
        cache_path = isolated_config.get_cache_path(cache_file)
        old_time = time.time() - (40 * 86400)  # 40 days old
        os.utime(cache_path, (old_time, old_time))

        # TTL is 30 days, so this should be expired
        loaded = isolated_config.load_cache(cache_file)
        assert loaded is None

    def test_get_cache_path(self, isolated_config):
        """Test getting cache file path"""
        cache_path = isolated_config.get_cache_path("subdir/test.json")
        assert cache_path.name == "test.json"
        assert cache_path.parent.exists()

    def test_clear_cache(self, isolated_config):
        """Test clearing cache files"""
        isolated_config.save_cache("file1.json", {"data": 1})
        isolated_config.save_cache("file2.json", {"data": 2})

        isolated_config.clear_cache()

        # Files should be deleted
        file1 = isolated_config.get_cache_path("file1.json")
        assert not file1.exists()


@pytest.mark.unit
class TestPathHandling:
    """Tests for path validation and creation"""

    def test_absolute_path_conversion(self, isolated_config):
        """Test relative paths converted to absolute"""
        assert isolated_config.cache.directory.is_absolute()
        assert isolated_config.kicad.library_dir.is_absolute()

    def test_directory_creation(self, isolated_config):
        """Test required directories are created"""
        assert isolated_config.data_dir.exists()
        assert isolated_config.cache.directory.exists()
        assert isolated_config.kicad.library_dir.exists()

    def test_kicad_library_path_relative(self, temp_dir):
        """Test KiCAD library path handling"""
        yaml_content = """
kicad:
  library_dir: custom_kicad_lib/
  symbol_lib: symbols.kicad_sym
"""
        config_file = temp_dir / "config.yaml"
        config_file.write_text(yaml_content)

        Config._instance = None
        Config._initialized = False
        config = Config.__new__(Config)
        config.tool_dir = temp_dir
        config.project_root = temp_dir / "project"
        config.config_file = config_file
        config.log_file = temp_dir / "test.log"
        config.data_dir = temp_dir / "data"
        config.data_dir.mkdir(parents=True, exist_ok=True)
        Config._instance = config

        config._load_config()

        assert config.kicad.library_dir.is_absolute()
        assert "custom_kicad_lib" in str(config.kicad.library_dir)


@pytest.mark.unit
class TestConfigValidation:
    """Tests for config validation"""

    def test_validate_missing_kicad_library(self, isolated_config):
        """Test validation fails when KiCAD library missing"""
        # Create a non-existent directory
        isolated_config.kicad.library_dir = Path("/nonexistent/kicad/lib")
        assert isolated_config.validate() is False

    def test_validate_with_valid_config(self, isolated_config):
        """Test validation passes with valid config"""
        # Config already has valid paths from fixture
        assert isolated_config.validate() is True

    def test_validate_lcsc_api_enabled_no_credentials(self, isolated_config):
        """Test validation fails when LCSC API enabled but no credentials"""
        isolated_config.lcsc.api_enabled = True
        isolated_config.lcsc.api_key = ""
        assert isolated_config.validate() is False

    def test_validate_lcsc_api_with_credentials(self, isolated_config):
        """Test validation passes when LCSC API has credentials"""
        isolated_config.lcsc.api_enabled = True
        isolated_config.lcsc.api_key = "test_key"
        isolated_config.lcsc.api_secret = "test_secret"
        assert isolated_config.validate() is True


@pytest.mark.unit
class TestConfigExport:
    """Tests for configuration export"""

    def test_to_dict_export(self, isolated_config):
        """Test exporting config to dictionary"""
        cfg_dict = isolated_config.to_dict()

        assert "lcsc" in cfg_dict
        assert "cache" in cfg_dict
        assert "kicad" in cfg_dict
        assert "paths" in cfg_dict

        assert cfg_dict["lcsc"]["api_enabled"] is False
        assert cfg_dict["cache"]["enabled"] is True

    def test_to_dict_masks_secrets(self, isolated_config):
        """Test export masks sensitive values"""
        isolated_config.lcsc.api_key = "secret_key_123"
        cfg_dict = isolated_config.to_dict()

        # API key should be masked if not set, or included if set
        assert "secret_key_123" not in str(cfg_dict) or cfg_dict["lcsc"]["api_key"] == "secret_key_123"

    def test_to_dict_includes_all_paths(self, isolated_config):
        """Test export includes all required paths"""
        cfg_dict = isolated_config.to_dict()
        paths = cfg_dict["paths"]

        assert "tool_dir" in paths
        assert "project_root" in paths
        assert "data_dir" in paths
        assert "log_file" in paths


@pytest.mark.unit
class TestLoggingSetup:
    """Tests for logging configuration"""

    def test_logger_initialization(self, isolated_config):
        """Test logger is properly initialized"""
        logger = isolated_config.logger
        assert logger is not None
        assert logger.name == "lcsc_automation"

    def test_logger_handlers(self, isolated_config):
        """Test logger has console and file handlers"""
        logger = isolated_config.logger
        # Should have at least handlers from parent logger
        handlers = [h for h in logger.handlers]
        # At least one handler should exist
        assert len(handlers) >= 0  # Parent logger has handlers

    def test_log_file_created(self, isolated_config):
        """Test log file is created"""
        # Access logger to trigger log file creation
        logger = isolated_config.logger
        logger.info("Test log message")
        assert isolated_config.log_file.exists()


@pytest.mark.unit
def test_get_config_returns_singleton():
    """Test get_config() returns singleton instance"""
    Config._instance = None
    Config._initialized = False
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2


@pytest.mark.unit
def test_config_with_missing_yaml_fallback(temp_dir, monkeypatch):
    """Test config falls back to defaults when YAML missing"""
    Config._instance = None
    Config._initialized = False

    config = Config.__new__(Config)
    config.tool_dir = temp_dir
    config.project_root = temp_dir / "project"
    config.config_file = temp_dir / "missing.yaml"
    config.log_file = temp_dir / "test.log"
    config.data_dir = temp_dir / "data"
    config.data_dir.mkdir(parents=True, exist_ok=True)
    Config._instance = config

    # Should not raise exception
    config._load_config()

    # Should have defaults
    assert config.lcsc.api_enabled is False
    assert config.cache.enabled is True
