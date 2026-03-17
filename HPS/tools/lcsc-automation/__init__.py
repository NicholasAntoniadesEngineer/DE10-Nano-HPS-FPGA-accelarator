"""
LCSC Automation Framework
High-quality, scaleable LCSC component sourcing and KiCAD integration system.
"""

__version__ = "1.0.0"
__author__ = "DE10-Nano HPS-FPGA Accelerator Project"
__license__ = "MIT"

from .config import Config, get_config
from .lcsc_fetcher import LCSCFetcher, LCSCPart
from .kicad_parser import KiCADParser, SchematicComponent
from .bom_generator import BOMMGenerator, BOMMFromSchematic
from .library_manager import KiCADLibraryManager
from .validator import ComponentValidator, DFMChecker

__all__ = [
    "Config",
    "get_config",
    "LCSCFetcher",
    "LCSCPart",
    "KiCADParser",
    "SchematicComponent",
    "BOMMGenerator",
    "BOMMFromSchematic",
    "KiCADLibraryManager",
    "ComponentValidator",
    "DFMChecker",
]
