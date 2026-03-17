"""
Utility functions for LCSC automation framework.
HTTP client, caching, CSV generation, and helper functions.
"""

import os
import sys
import time
import json
import csv
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from functools import wraps
from datetime import datetime
from urllib.parse import urljoin, quote
import re

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    requests = None

from config import get_config


logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to respect LCSC API limits (100-200 req/min)"""

    def __init__(self, requests_per_minute: int = 100):
        self.rpm = requests_per_minute
        self.request_times = []
        self.lock_time = 0.0

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        window_start = now - 60.0

        # Remove old requests outside the window
        self.request_times = [t for t in self.request_times if t > window_start]

        if len(self.request_times) >= self.rpm:
            wait_time = self.request_times[0] + 60.0 - now
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s before next request")
                time.sleep(wait_time)
                self.request_times = []

        self.request_times.append(time.time())

    def reset(self):
        """Reset rate limiter"""
        self.request_times = []


_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        cfg = get_config()
        _rate_limiter = RateLimiter(cfg.lcsc.rate_limit_rpm)
    return _rate_limiter


class HTTPClient:
    """HTTP client with retries, caching, and rate limiting"""

    def __init__(self, base_url: str = "", cache_key_prefix: str = "http_"):
        self.base_url = base_url
        self.cache_key_prefix = cache_key_prefix
        self.session = self._create_session()

    @staticmethod
    def _create_session():
        """Create requests session with retry strategy"""
        session = requests.Session() if requests else None
        if not session:
            return None

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # User agent to avoid blocking
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        return session

    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from URL and parameters"""
        cache_str = url
        if params:
            cache_str += json.dumps(params, sort_keys=True)

        hash_obj = hashlib.md5(cache_str.encode())
        return f"{self.cache_key_prefix}{hash_obj.hexdigest()}.json"

    def get(self, url: str, params: Optional[Dict] = None, use_cache: bool = True,
            timeout: int = 10) -> Optional[Dict[str, Any]]:
        """GET request with caching and rate limiting"""
        if not self.session:
            logger.error("requests library not available")
            return None

        # Check cache first
        cache_key = self._get_cache_key(url, params)
        if use_cache:
            cfg = get_config()
            cached_data = cfg.load_cache(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_data

        try:
            # Rate limit
            get_rate_limiter().wait_if_needed()

            # Make request
            full_url = urljoin(self.base_url, url) if self.base_url else url
            logger.debug(f"GET {full_url} params={params}")

            response = self.session.get(full_url, params=params, timeout=timeout)
            response.raise_for_status()

            data = response.json() if response.text else {}

            # Cache result
            if use_cache:
                cfg = get_config()
                cfg.save_cache(cache_key, data)

            return data

        except requests.RequestException as e:
            logger.error(f"HTTP GET failed: {e}")
            return None

    def post(self, url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None,
             use_cache: bool = False, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """POST request with optional caching"""
        if not self.session:
            logger.error("requests library not available")
            return None

        try:
            # Rate limit
            get_rate_limiter().wait_if_needed()

            full_url = urljoin(self.base_url, url) if self.base_url else url
            logger.debug(f"POST {full_url} data={data is not None} json={json_data is not None}")

            response = self.session.post(
                full_url, data=data, json=json_data, timeout=timeout
            )
            response.raise_for_status()

            result = response.json() if response.text else {}

            # Cache if requested
            if use_cache:
                cache_key = self._get_cache_key(url, json_data or data)
                cfg = get_config()
                cfg.save_cache(cache_key, result)

            return result

        except requests.RequestException as e:
            logger.error(f"HTTP POST failed: {e}")
            return None


def hash_file(filepath: Path, algorithm: str = 'md5') -> str:
    """Calculate file hash"""
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def safe_filename(name: str) -> str:
    """Convert string to safe filename"""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-').lower()


def parse_csv(filepath: Path) -> List[Dict[str, str]]:
    """Parse CSV file into list of dicts"""
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
    except Exception as e:
        logger.error(f"Failed to parse CSV {filepath}: {e}")
    return data


def write_csv(filepath: Path, rows: List[Dict[str, str]], fieldnames: List[str]):
    """Write list of dicts to CSV file"""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Wrote CSV: {filepath} ({len(rows)} rows)")
    except Exception as e:
        logger.error(f"Failed to write CSV {filepath}: {e}")


def natural_sort_key(text: str) -> Tuple:
    """Key function for natural (alphanumeric) sorting"""
    def atoi(text):
        return int(text) if text.isdigit() else text
    return tuple(atoi(c) for c in re.split(r'(\d+)', text))


def extract_lcsc_id(text: str) -> Optional[str]:
    """Extract LCSC part ID from text (e.g., C2040, C1234567)"""
    match = re.search(r'\b(C\d{1,7})\b', text)
    return match.group(1) if match else None


def parse_value_with_unit(value_str: str) -> Tuple[float, str]:
    """Parse component value with unit (e.g., '100nF' -> (100, 'nF'))"""
    match = re.match(r'^([\d.]+)\s*([a-zA-Z°ΩΩ]*)$', value_str.strip())
    if match:
        try:
            return float(match.group(1)), match.group(2).strip()
        except ValueError:
            pass
    return 1.0, value_str


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp as ISO8601"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat(timespec='seconds')


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry function on exception"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"{func.__name__} attempt {attempt+1} failed: {e}, retrying...")
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
        return wrapper
    return decorator


def get_python_venv() -> Optional[Path]:
    """Detect active Python virtual environment"""
    if hasattr(sys, 'real_prefix'):
        return Path(sys.real_prefix)
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        return Path(sys.prefix)
    return None


def check_command_available(command: str) -> bool:
    """Check if command is available in PATH"""
    import shutil
    return shutil.which(command) is not None


def human_filesize(num_bytes: int) -> str:
    """Convert bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f}TB"


def sanitize_json(data: Any) -> Any:
    """Recursively sanitize data for JSON serialization"""
    if isinstance(data, dict):
        return {k: sanitize_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json(item) for item in data]
    elif isinstance(data, Path):
        return str(data)
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        return str(data)


def load_json_or_yaml(filepath: Path) -> Dict[str, Any]:
    """Load JSON or YAML file automatically"""
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        if filepath.suffix in ['.json']:
            with open(filepath, 'r') as f:
                return json.load(f)
        elif filepath.suffix in ['.yaml', '.yml']:
            try:
                import yaml
                with open(filepath, 'r') as f:
                    return yaml.safe_load(f) or {}
            except ImportError:
                logger.error("PyYAML not installed, cannot load YAML files")
                raise
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")
    except Exception as e:
        logger.error(f"Failed to load {filepath}: {e}")
        raise


if __name__ == "__main__":
    # Test utilities
    print("Testing HTTPClient...")
    client = HTTPClient(base_url="https://httpbin.org")
    result = client.get("/get", params={"test": "value"})
    if result:
        print(f"GET request successful: {result.get('args')}")

    print("\nTesting utilities...")
    print(f"Safe filename: {safe_filename('Part C2040 - 100nF')}")
    print(f"LCSC ID extract: {extract_lcsc_id('Capacitor C2040')}")
    print(f"Value parsing: {parse_value_with_unit('100nF')}")
    print(f"Natural sort: {sorted(['C1', 'C10', 'C2'], key=natural_sort_key)}")
