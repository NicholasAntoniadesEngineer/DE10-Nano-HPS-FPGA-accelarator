"""
Pytest fixtures and configuration for LCSC automation tests.
Provides test data, temporary directories, and common utilities.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config, get_config
from kicad_parser import SchematicComponent, KiCADParser
from utils import natural_sort_key


@pytest.fixture(scope="session")
def test_data_dir():
    """Get path to test data directory"""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def project_root():
    """Get path to project root"""
    return Path(__file__).parent.parent.parent.parent.parent


@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp(prefix="lcsc_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def isolated_config(temp_dir, monkeypatch):
    """Create isolated config instance for testing"""
    # Monkeypatch Config to use temp directory
    config_instance = Config.__new__(Config)
    config_instance.tool_dir = temp_dir
    config_instance.project_root = temp_dir / "project"
    config_instance.config_file = temp_dir / "config.yaml"
    config_instance.log_file = temp_dir / "test.log"
    config_instance.data_dir = temp_dir / "data"
    config_instance.data_dir.mkdir(parents=True, exist_ok=True)

    # Reset singleton
    Config._instance = config_instance
    Config._initialized = False

    yield config_instance

    # Cleanup
    Config._instance = None


@pytest.fixture
def sample_components() -> List[SchematicComponent]:
    """Create sample components for testing"""
    return [
        SchematicComponent(
            reference="C1",
            value="100nF",
            footprint="Package_SMD:C_0402_1005Metric",
            lcsc_id="C2040",
            description="Ceramic capacitor",
            quantity=1,
            library="Device",
            symbol="C"
        ),
        SchematicComponent(
            reference="C2",
            value="100nF",
            footprint="Package_SMD:C_0402_1005Metric",
            lcsc_id="C2040",
            description="Ceramic capacitor",
            quantity=1,
            library="Device",
            symbol="C"
        ),
        SchematicComponent(
            reference="R1",
            value="10k",
            footprint="Package_SMD:R_0402_1005Metric",
            lcsc_id="C4169",
            description="Resistor",
            quantity=1,
            library="Device",
            symbol="R"
        ),
        SchematicComponent(
            reference="U1",
            value="ESP32",
            footprint="Package_QFP:LQFP-48_7x7mm_P0.5mm",
            lcsc_id="C529971",
            description="Wi-Fi + Bluetooth microcontroller",
            quantity=1,
            library="Device",
            symbol="MCU"
        ),
        SchematicComponent(
            reference="L1",
            value="10uH",
            footprint="Package_SMD:L_0603_1608Metric",
            lcsc_id="C4216",
            description="Inductor",
            quantity=1,
            library="Device",
            symbol="L"
        ),
    ]


@pytest.fixture
def sample_bom_dict() -> Dict[str, Dict[str, Any]]:
    """Create sample BOM dictionary"""
    return {
        "100nF_Package_SMD:C_0402_1005Metric": {
            "value": "100nF",
            "footprint": "Package_SMD:C_0402_1005Metric",
            "lcsc_id": "C2040",
            "references": ["C1", "C2"],
            "quantity": 2
        },
        "10k_Package_SMD:R_0402_1005Metric": {
            "value": "10k",
            "footprint": "Package_SMD:R_0402_1005Metric",
            "lcsc_id": "C4169",
            "references": ["R1"],
            "quantity": 1
        },
        "ESP32_Package_QFP:LQFP-48_7x7mm_P0.5mm": {
            "value": "ESP32",
            "footprint": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
            "lcsc_id": "C529971",
            "references": ["U1"],
            "quantity": 1
        },
    }


@pytest.fixture
def sample_kicad_sch_content() -> str:
    """Create sample KiCAD schematic s-expression format"""
    return """(kicad_sch (version 20230121) (generator eeschema)
  (uuid "12345678-1234-1234-1234-123456789012")
  (paper "A4")
  (title_block)

  (symbol (lib_id "Device:C") (at 100 100 0) (uuid "11111111-1111-1111-1111-111111111111")
    (property "Reference" "C1" (id 0 0))
    (property "Value" "100nF" (id 1 0))
    (property "Footprint" "Package_SMD:C_0402_1005Metric" (id 2 0))
    (property "LCSC" "C2040" (id 3 0))
  )

  (symbol (lib_id "Device:C") (at 120 100 0) (uuid "22222222-2222-2222-2222-222222222222")
    (property "Reference" "C2" (id 0 0))
    (property "Value" "100nF" (id 1 0))
    (property "Footprint" "Package_SMD:C_0402_1005Metric" (id 2 0))
    (property "LCSC" "C2040" (id 3 0))
  )

  (symbol (lib_id "Device:R") (at 140 100 0) (uuid "33333333-3333-3333-3333-333333333333")
    (property "Reference" "R1" (id 0 0))
    (property "Value" "10k" (id 1 0))
    (property "Footprint" "Package_SMD:R_0402_1005Metric" (id 2 0))
    (property "LCSC" "C4169" (id 3 0))
  )
)"""


@pytest.fixture
def mock_csv_data() -> List[Dict[str, str]]:
    """Create mock CSV data"""
    return [
        {"Comment": "100nF", "Designator": "C1,C2", "Footprint": "0402", "LCSC Part #": "C2040"},
        {"Comment": "10k", "Designator": "R1", "Footprint": "0402", "LCSC Part #": "C4169"},
        {"Comment": "ESP32", "Designator": "U1", "Footprint": "LQFP48", "LCSC Part #": "C529971"},
    ]


@pytest.fixture
def actual_schematic_file(project_root) -> Path:
    """Get path to actual daughter_board schematic if available"""
    possible_paths = [
        project_root / "drone_design/output/gerber/daughter_board_esp32.kicad_sch",
        project_root / "drone_design/drone_model/output/gerber/daughter_board.kicad_sch",
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return None


class MockHTTPResponse:
    """Mock HTTP response for testing"""
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")
