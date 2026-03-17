"""
LCSC component data fetcher with multi-source fallback chain.
Sources: LCSC API > easyeda2kicad > jlcparts JSON > web scraping
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hmac
import hashlib
from urllib.parse import urlencode
import uuid

from config import get_config
from utils import HTTPClient, extract_lcsc_id, safe_filename, retry_on_error

logger = logging.getLogger(__name__)


@dataclass
class LCSCPart:
    """LCSC component data"""
    lcsc_id: str
    manufacturer: str
    model: str
    description: str
    category: str
    package: str
    stock: int
    price: float
    minimum_qty: int = 1
    rosh: bool = False
    datasheet_url: Optional[str] = None
    symbols_available: bool = False
    footprints_available: bool = False
    models_3d_available: bool = False
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class LCSCAPIFetcher:
    """Official LCSC REST API client"""

    def __init__(self):
        self.cfg = get_config()
        self.base_url = self.cfg.lcsc.base_url
        self.api_key = self.cfg.lcsc.api_key
        self.api_secret = self.cfg.lcsc.api_secret
        self.http_client = HTTPClient(base_url=self.base_url)

    def is_enabled(self) -> bool:
        """Check if API is enabled and credentials available"""
        return self.cfg.lcsc.api_enabled and bool(self.api_key and self.api_secret)

    def _generate_signature(self, params: Dict[str, str]) -> Tuple[str, str]:
        """Generate LCSC API signature and timestamp"""
        timestamp = str(int(time.time()))
        nonce = str(uuid.uuid4())[:8]

        # Build signature string
        param_str = urlencode(sorted(params.items()))
        sign_str = f"{param_str}{self.api_secret}{timestamp}{nonce}{self.api_secret}"

        signature = hashlib.md5(sign_str.encode()).hexdigest()
        return signature, timestamp, nonce

    def search_product(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for products by keyword"""
        if not self.is_enabled():
            logger.debug("LCSC API not enabled, skipping API search")
            return []

        params = {
            "apikey": self.api_key,
            "keyword": keyword,
            "pageNo": "1",
            "pageSize": str(limit),
            "isHighlight": "0"
        }

        signature, timestamp, nonce = self._generate_signature(params)
        params.update({
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature
        })

        try:
            result = self.http_client.get("/api/products/search", params=params)
            if result and result.get("code") == "0":
                products = result.get("data", {}).get("products", [])
                logger.info(f"API search '{keyword}': found {len(products)} products")
                return products
            else:
                logger.warning(f"API search failed: {result}")
                return []
        except Exception as e:
            logger.warning(f"LCSC API error: {e}")
            return []

    def get_product_detail(self, lcsc_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by LCSC ID"""
        if not self.is_enabled():
            return None

        params = {
            "apikey": self.api_key,
            "componentCode": lcsc_id
        }

        signature, timestamp, nonce = self._generate_signature(params)
        params.update({
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature
        })

        try:
            result = self.http_client.get("/api/products/detail", params=params)
            if result and result.get("code") == "0":
                product = result.get("data", {})
                logger.debug(f"API detail for {lcsc_id}: {product.get('productCode')}")
                return product
            return None
        except Exception as e:
            logger.warning(f"LCSC API detail error: {e}")
            return None


class EasyEDAFetcher:
    """easyeda2kicad CLI wrapper for part lookup"""

    def __init__(self):
        self.cfg = get_config()

    def is_available(self) -> bool:
        """Check if easyeda2kicad is installed"""
        try:
            result = subprocess.run(
                ["easyeda2kicad", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_part_data(self, lcsc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch part data using easyeda2kicad"""
        if not self.is_available():
            logger.debug("easyeda2kicad not available")
            return None

        try:
            # easyeda2kicad can query part info
            result = subprocess.run(
                ["easyeda2kicad", "--info", "--lcsc_id", lcsc_id],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse JSON output if available
                try:
                    data = json.loads(result.stdout)
                    logger.debug(f"easyeda2kicad data for {lcsc_id}: {data.get('title')}")
                    return data
                except json.JSONDecodeError:
                    logger.debug(f"easyeda2kicad returned non-JSON for {lcsc_id}")
                    return None
            else:
                logger.debug(f"easyeda2kicad query failed for {lcsc_id}: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning(f"easyeda2kicad timeout for {lcsc_id}")
            return None
        except Exception as e:
            logger.warning(f"easyeda2kicad error: {e}")
            return None


class JLCPartsFetcher:
    """Community jlcparts JSON data source (no rate limits)"""

    def __init__(self):
        self.cfg = get_config()
        self.http_client = HTTPClient()
        # jlcparts provides static JSON files per category
        self.jlcparts_base = "https://yaqwsx.github.io/jlcparts"
        self.categories = {}
        self.parts_index = {}

    def load_parts_index(self) -> bool:
        """Load jlcparts index from GitHub"""
        cache_key = "jlcparts_index.json"
        cached_index = self.cfg.load_cache(cache_key)

        if cached_index:
            self.parts_index = cached_index
            logger.info(f"Loaded jlcparts index from cache: {len(cached_index)} parts")
            return True

        try:
            # jlcparts provides a parts.json index file
            url = f"{self.jlcparts_base}/data/parts.json"
            logger.info(f"Downloading jlcparts index from {url}...")

            result = self.http_client.get(url, use_cache=False)
            if result and isinstance(result, dict):
                self.parts_index = result
                self.cfg.save_cache(cache_key, result)
                logger.info(f"Loaded jlcparts index: {len(result)} parts")
                return True
        except Exception as e:
            logger.warning(f"Failed to load jlcparts index: {e}")

        return False

    def get_part_data(self, lcsc_id: str) -> Optional[Dict[str, Any]]:
        """Get part data from jlcparts"""
        # Try to find in loaded index
        if lcsc_id in self.parts_index:
            return self.parts_index[lcsc_id]

        # Try category-specific JSON if index is available
        if not self.parts_index:
            self.load_parts_index()

        if lcsc_id in self.parts_index:
            return self.parts_index[lcsc_id]

        return None


class WebScrapeFetcher:
    """Fallback: scrape LCSC product pages directly"""

    def __init__(self):
        self.cfg = get_config()
        self.http_client = HTTPClient(base_url="https://www.lcsc.com")

    def get_part_data(self, lcsc_id: str) -> Optional[Dict[str, Any]]:
        """Scrape LCSC product page for part data"""
        try:
            # Try LCSC API search endpoint (usually available without auth)
            url = f"/api/products/search"
            params = {"q": lcsc_id, "pageSize": "1"}

            result = self.http_client.get(url, params=params, use_cache=True)
            if result and result.get("result") and len(result["result"]) > 0:
                product = result["result"][0]
                logger.debug(f"Web scrape data for {lcsc_id}: {product.get('productTitle')}")
                return product

        except Exception as e:
            logger.debug(f"Web scrape failed for {lcsc_id}: {e}")

        return None


class LCSCFetcher:
    """Multi-source LCSC component fetcher with fallback chain"""

    def __init__(self):
        self.cfg = get_config()
        self.api = LCSCAPIFetcher()
        self.easyeda = EasyEDAFetcher()
        self.jlcparts = JLCPartsFetcher()
        self.webscrape = WebScrapeFetcher()
        self.source_priority = self.cfg.sources

    @retry_on_error(max_retries=2, delay=1.0)
    def fetch_part(self, lcsc_id: str) -> Optional[LCSCPart]:
        """Fetch part data using fallback chain"""
        lcsc_id = lcsc_id.upper()

        # Try cache first
        cache_key = f"part_{lcsc_id}.json"
        cached_part = self.cfg.load_cache(cache_key)
        if cached_part:
            logger.debug(f"Cache hit for {lcsc_id}")
            return LCSCPart(**cached_part)

        logger.info(f"Fetching {lcsc_id}...")

        # Try each source in priority order
        for source in self.source_priority:
            if source == "lcsc_api":
                part = self._try_api(lcsc_id)
            elif source == "easyeda2kicad":
                part = self._try_easyeda(lcsc_id)
            elif source == "jlcparts_json":
                part = self._try_jlcparts(lcsc_id)
            elif source == "web_scraping":
                part = self._try_webscrape(lcsc_id)
            else:
                continue

            if part:
                logger.info(f"Found {lcsc_id} via {source}")
                # Cache result
                self.cfg.save_cache(cache_key, asdict(part))
                return part

        logger.warning(f"Could not fetch data for {lcsc_id} from any source")
        return None

    def _try_api(self, lcsc_id: str) -> Optional[LCSCPart]:
        """Try LCSC API"""
        if not self.api.is_enabled():
            return None

        try:
            data = self.api.get_product_detail(lcsc_id)
            if data:
                return self._parse_api_response(lcsc_id, data)
        except Exception as e:
            logger.debug(f"API fetch failed for {lcsc_id}: {e}")

        return None

    def _try_easyeda(self, lcsc_id: str) -> Optional[LCSCPart]:
        """Try easyeda2kicad"""
        try:
            data = self.easyeda.get_part_data(lcsc_id)
            if data:
                return self._parse_easyeda_response(lcsc_id, data)
        except Exception as e:
            logger.debug(f"easyeda2kicad fetch failed for {lcsc_id}: {e}")

        return None

    def _try_jlcparts(self, lcsc_id: str) -> Optional[LCSCPart]:
        """Try jlcparts JSON"""
        try:
            if not self.jlcparts.parts_index:
                self.jlcparts.load_parts_index()

            data = self.jlcparts.get_part_data(lcsc_id)
            if data:
                return self._parse_jlcparts_response(lcsc_id, data)
        except Exception as e:
            logger.debug(f"jlcparts fetch failed for {lcsc_id}: {e}")

        return None

    def _try_webscrape(self, lcsc_id: str) -> Optional[LCSCPart]:
        """Try web scraping"""
        try:
            data = self.webscrape.get_part_data(lcsc_id)
            if data:
                return self._parse_webscrape_response(lcsc_id, data)
        except Exception as e:
            logger.debug(f"Web scrape failed for {lcsc_id}: {e}")

        return None

    @staticmethod
    def _parse_api_response(lcsc_id: str, data: Dict[str, Any]) -> Optional[LCSCPart]:
        """Parse LCSC API response"""
        try:
            return LCSCPart(
                lcsc_id=lcsc_id,
                manufacturer=data.get("manufacturerEn", ""),
                model=data.get("productModel", ""),
                description=data.get("productTitle", ""),
                category=data.get("categoryEn", ""),
                package=data.get("package", ""),
                stock=int(data.get("stock", 0)),
                price=float(data.get("price", 0)),
                minimum_qty=int(data.get("minBuy", 1)),
                rosh=data.get("rosh", False),
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            logger.warning(f"Failed to parse API response for {lcsc_id}: {e}")
            return None

    @staticmethod
    def _parse_easyeda_response(lcsc_id: str, data: Dict[str, Any]) -> Optional[LCSCPart]:
        """Parse easyeda2kicad response"""
        try:
            return LCSCPart(
                lcsc_id=lcsc_id,
                manufacturer=data.get("manufacturer", ""),
                model=data.get("model", ""),
                description=data.get("title", data.get("description", "")),
                category=data.get("category", ""),
                package=data.get("package", ""),
                stock=int(data.get("stock", 0)),
                price=float(data.get("price", 0)),
                symbols_available=data.get("symbols_available", False),
                footprints_available=data.get("footprints_available", False),
                models_3d_available=data.get("models_3d_available", False),
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            logger.warning(f"Failed to parse easyeda response for {lcsc_id}: {e}")
            return None

    @staticmethod
    def _parse_jlcparts_response(lcsc_id: str, data: Dict[str, Any]) -> Optional[LCSCPart]:
        """Parse jlcparts JSON response"""
        try:
            return LCSCPart(
                lcsc_id=lcsc_id,
                manufacturer=data.get("mfr", ""),
                model=data.get("mfrPN", ""),
                description=data.get("title", ""),
                category=data.get("category", ""),
                package=data.get("package", ""),
                stock=int(data.get("stock", 0)),
                price=float(data.get("price", 0)),
                datasheet_url=data.get("datasheet", ""),
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            logger.warning(f"Failed to parse jlcparts response for {lcsc_id}: {e}")
            return None

    @staticmethod
    def _parse_webscrape_response(lcsc_id: str, data: Dict[str, Any]) -> Optional[LCSCPart]:
        """Parse web scrape response"""
        try:
            return LCSCPart(
                lcsc_id=lcsc_id,
                manufacturer=data.get("brand", ""),
                model=data.get("type", ""),
                description=data.get("productTitle", ""),
                category=data.get("categories", [{}])[0].get("categoryEn", ""),
                package=data.get("package", ""),
                stock=int(data.get("inStock", 0)),
                price=float(data.get("price", 0)),
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            logger.warning(f"Failed to parse web scrape response for {lcsc_id}: {e}")
            return None

    def verify_parts_list(self, part_ids: List[str]) -> Dict[str, Optional[LCSCPart]]:
        """Verify multiple parts"""
        results = {}
        for lcsc_id in part_ids:
            results[lcsc_id] = self.fetch_part(lcsc_id)
        return results

    def search_parts(self, keyword: str, limit: int = 10) -> List[LCSCPart]:
        """Search for parts by keyword"""
        if self.api.is_enabled():
            products = self.api.search_product(keyword, limit)
            results = []
            for product in products:
                lcsc_id = product.get("componentCode")
                part = self._parse_api_response(lcsc_id, product)
                if part:
                    results.append(part)
            return results

        logger.warning("Part search requires LCSC API, which is not enabled")
        return []


if __name__ == "__main__":
    # Test fetcher
    fetcher = LCSCFetcher()

    # Test single part
    print("Testing single part fetch...")
    part = fetcher.fetch_part("C2040")
    if part:
        print(f"Found: {part.description} (Stock: {part.stock}, Price: ${part.price})")
    else:
        print("Part not found")

    # Test multiple parts
    print("\nTesting multiple parts...")
    parts = fetcher.verify_parts_list(["C2040", "C1525", "C24112"])
    for lcsc_id, part in parts.items():
        if part:
            print(f"  {lcsc_id}: {part.description} (${part.price})")
        else:
            print(f"  {lcsc_id}: NOT FOUND")
