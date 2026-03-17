"""
Configuration management for LCSC automation framework.
Loads settings from config.yaml, environment variables, or defaults.
Manages caching, API credentials, and source priorities.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from functools import lru_cache
import yaml

# Ensure we can import from parent directory
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class LCSCConfig:
    """LCSC API configuration"""
    api_enabled: bool = False
    api_key: str = ""
    api_secret: str = ""
    rate_limit_rpm: int = 100
    base_url: str = "https://ips.lcsc.com"


@dataclass
class CacheConfig:
    """Caching configuration"""
    enabled: bool = True
    directory: Path = None
    ttl_days: int = 30


@dataclass
class KiCADConfig:
    """KiCAD integration configuration"""
    library_dir: Path = None
    symbol_lib: str = "lcsc_parts.kicad_sym"
    footprint_lib: str = "lcsc_parts.pretty"
    models_dir: str = "3dmodels"


class Config:
    """Global configuration manager for LCSC automation"""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.tool_dir = Path(__file__).parent
        self.project_root = self.tool_dir.parent.parent.parent
        self.config_file = self.tool_dir / "config.yaml"
        self.log_file = self.tool_dir / "lcsc_automation.log"
        self.data_dir = self.tool_dir / "data"

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self._load_config()

        # Setup logging
        self._setup_logging()

        self._initialized = True

    def _load_config(self):
        """Load configuration from YAML or defaults"""
        defaults = {
            "lcsc": {
                "api_enabled": False,
                "api_key": "",
                "api_secret": "",
                "rate_limit_rpm": 100,
                "base_url": "https://ips.lcsc.com"
            },
            "sources": {
                "priority": [
                    "lcsc_api",
                    "easyeda2kicad",
                    "jlcparts_json",
                    "web_scraping"
                ]
            },
            "cache": {
                "enabled": True,
                "directory": "data/lcsc_cache/",
                "ttl_days": 30
            },
            "kicad": {
                "library_dir": "../../FPGA/kicad_lib/",
                "symbol_lib": "lcsc_parts.kicad_sym",
                "footprint_lib": "lcsc_parts.pretty/",
                "models_dir": "3dmodels/"
            },
            "logging": {
                "level": "INFO",
                "file": "lcsc_automation.log"
            }
        }

        # Try to load from YAML
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                    # Deep merge with defaults
                    self._deep_merge(defaults, file_config)
            except Exception as e:
                print(f"Warning: Could not load config.yaml: {e}. Using defaults.", file=sys.stderr)
        else:
            # Try to load from environment variables
            if "LCSC_API_KEY" in os.environ:
                defaults["lcsc"]["api_key"] = os.environ["LCSC_API_KEY"]
                defaults["lcsc"]["api_enabled"] = True
            if "LCSC_API_SECRET" in os.environ:
                defaults["lcsc"]["api_secret"] = os.environ["LCSC_API_SECRET"]

        self.config = defaults

        # Convert relative paths to absolute
        self.lcsc = LCSCConfig(**self.config["lcsc"])
        self.sources = self.config["sources"]["priority"]

        cache_dir = self.config["cache"]["directory"]
        if not Path(cache_dir).is_absolute():
            cache_dir = self.tool_dir / cache_dir
        self.cache = CacheConfig(
            enabled=self.config["cache"]["enabled"],
            directory=Path(cache_dir),
            ttl_days=self.config["cache"]["ttl_days"]
        )
        self.cache.directory.mkdir(parents=True, exist_ok=True)

        kicad_lib = self.config["kicad"]["library_dir"]
        if not Path(kicad_lib).is_absolute():
            kicad_lib = self.tool_dir / kicad_lib
        self.kicad = KiCADConfig(
            library_dir=Path(kicad_lib),
            symbol_lib=self.config["kicad"]["symbol_lib"],
            footprint_lib=self.config["kicad"]["footprint_lib"],
            models_dir=self.config["kicad"]["models_dir"]
        )
        self.kicad.library_dir.mkdir(parents=True, exist_ok=True)

        self.log_level = self.config["logging"]["level"]

    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge override dict into base dict"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _setup_logging(self):
        """Setup logging configuration"""
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        log_level = getattr(logging, self.log_level, logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(self.log_file, mode='a')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        self._logger = logging.getLogger("lcsc_automation")

    @property
    def logger(self) -> logging.Logger:
        """Get logger instance"""
        if self._logger is None:
            self._setup_logging()
        return self._logger

    def get_cache_path(self, filename: str) -> Path:
        """Get cache file path, creating parent directories as needed"""
        cache_file = self.cache.directory / filename
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        return cache_file

    def is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache file is valid (exists and not expired)"""
        if not self.cache.enabled or not cache_file.exists():
            return False

        import time
        file_age_days = (time.time() - cache_file.stat().st_mtime) / 86400
        return file_age_days < self.cache.ttl_days

    def save_cache(self, filename: str, data: Dict[str, Any]):
        """Save data to cache"""
        if not self.cache.enabled:
            return

        cache_file = self.get_cache_path(filename)
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache {filename}: {e}")

    def load_cache(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load data from cache"""
        cache_file = self.get_cache_path(filename)

        if not self.is_cache_valid(cache_file):
            return None

        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load cache {filename}: {e}")
            return None

    def clear_cache(self, pattern: str = "*"):
        """Clear cache files matching pattern"""
        import glob
        cache_pattern = self.cache.directory / pattern
        for cache_file in glob.glob(str(cache_pattern)):
            try:
                Path(cache_file).unlink()
                self.logger.info(f"Cleared cache: {cache_file}")
            except Exception as e:
                self.logger.warning(f"Failed to clear cache {cache_file}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "lcsc": {
                "api_enabled": self.lcsc.api_enabled,
                "api_key": self.lcsc.api_key or "(not set)",
                "rate_limit_rpm": self.lcsc.rate_limit_rpm,
                "base_url": self.lcsc.base_url
            },
            "sources": {"priority": self.sources},
            "cache": {
                "enabled": self.cache.enabled,
                "directory": str(self.cache.directory),
                "ttl_days": self.cache.ttl_days
            },
            "kicad": {
                "library_dir": str(self.kicad.library_dir),
                "symbol_lib": self.kicad.symbol_lib,
                "footprint_lib": self.kicad.footprint_lib,
                "models_dir": self.kicad.models_dir
            },
            "paths": {
                "tool_dir": str(self.tool_dir),
                "project_root": str(self.project_root),
                "data_dir": str(self.data_dir),
                "log_file": str(self.log_file)
            }
        }

    def validate(self) -> bool:
        """Validate configuration"""
        errors = []

        # Check required directories exist
        if not self.kicad.library_dir.exists():
            errors.append(f"KiCAD library directory does not exist: {self.kicad.library_dir}")

        # Check LCSC API if enabled
        if self.lcsc.api_enabled:
            if not self.lcsc.api_key or not self.lcsc.api_secret:
                errors.append("LCSC API enabled but credentials not set")

        if errors:
            for error in errors:
                self.logger.error(f"Configuration error: {error}")
            return False

        return True


def get_config() -> Config:
    """Get global configuration instance"""
    return Config()


if __name__ == "__main__":
    # Test configuration
    cfg = get_config()
    print("LCSC Automation Configuration:")
    print(json.dumps(cfg.to_dict(), indent=2))
    print(f"\nConfiguration valid: {cfg.validate()}")
