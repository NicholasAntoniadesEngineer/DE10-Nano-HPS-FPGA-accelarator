"""
KiCAD schematic and board parser.
Extracts component information from KiCad files (v6.0+ s-expression format).
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PinType(Enum):
    """KiCAD pin types"""
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    TRISTATE = "tri_state"
    PASSIVE = "passive"
    POWER_IN = "power_in"
    POWER_OUT = "power_out"
    OPEN_COLLECTOR = "open_collector"
    OPEN_EMITTER = "open_emitter"
    UNSPECIFIED = "unspecified"


@dataclass
class Pin:
    """Component pin information"""
    number: str
    name: str
    pin_type: str = "unspecified"


@dataclass
class SchematicComponent:
    """Component from KiCAD schematic"""
    reference: str  # e.g., "U1", "C1"
    value: str  # e.g., "ESP32", "100nF"
    footprint: str  # e.g., "Package_QFP:LQFP-48_7x7mm_P0.5mm"
    lcsc_id: Optional[str] = None  # e.g., "C2040"
    description: str = ""
    datasheet: str = ""
    quantity: int = 1
    properties: Dict[str, str] = field(default_factory=dict)
    pins: List[Pin] = field(default_factory=list)
    library: str = ""  # e.g., "Device"
    symbol: str = ""  # e.g., "C"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "reference": self.reference,
            "value": self.value,
            "footprint": self.footprint,
            "lcsc_id": self.lcsc_id,
            "description": self.description,
            "datasheet": self.datasheet,
            "quantity": self.quantity,
            "library": self.library,
            "symbol": self.symbol,
            "properties": self.properties
        }


class KiCADParser:
    """Parse KiCAD schematic and board files"""

    def __init__(self):
        pass

    @staticmethod
    def _tokenize(content: str) -> List[str]:
        """Tokenize s-expression"""
        tokens = []
        current = ""
        in_string = False
        i = 0

        while i < len(content):
            char = content[i]

            if char == '"' and (i == 0 or content[i-1] != '\\'):
                in_string = not in_string
                current += char
            elif in_string:
                current += char
            elif char in '()':
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(char)
            elif char.isspace():
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

            i += 1

        if current:
            tokens.append(current)

        return tokens

    @staticmethod
    def _parse_sexpr(tokens: List[str], index: int = 0) -> tuple:
        """Parse s-expression tokens recursively"""
        if index >= len(tokens):
            return None, index

        token = tokens[index]

        if token == '(':
            result = []
            index += 1
            while index < len(tokens) and tokens[index] != ')':
                item, index = KiCADParser._parse_sexpr(tokens, index)
                if item is not None:
                    result.append(item)
            return result, index + 1
        elif token == ')':
            return None, index
        else:
            # Remove quotes from strings
            if token.startswith('"') and token.endswith('"'):
                token = token[1:-1]
            return token, index + 1

    @staticmethod
    def _get_sexpr_value(expr: Any, key: str, index: int = 1, default: Any = None) -> Any:
        """Get value from s-expression by key"""
        if not isinstance(expr, list):
            return default

        for i, item in enumerate(expr):
            if isinstance(item, list) and len(item) > 0 and item[0] == key:
                if len(item) > index:
                    return item[index]
                return default

        return default

    def parse_schematic(self, filepath: Path) -> List[SchematicComponent]:
        """Parse KiCAD schematic file (.kicad_sch)"""
        if not filepath.exists():
            logger.error(f"Schematic file not found: {filepath}")
            return []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read schematic: {e}")
            return []

        # Tokenize and parse s-expression
        tokens = self._tokenize(content)
        sexpr, _ = self._parse_sexpr(tokens)

        components = []
        if not isinstance(sexpr, list):
            logger.warning("Invalid schematic format")
            return components

        # Find symbol instances in schematic
        for item in sexpr:
            if isinstance(item, list) and len(item) > 0:
                if item[0] == "symbol":
                    component = self._parse_symbol(item)
                    if component:
                        components.append(component)

        logger.info(f"Parsed {len(components)} components from {filepath}")
        return components

    def _parse_symbol(self, symbol_expr: List[Any]) -> Optional[SchematicComponent]:
        """Parse symbol (component instance) from schematic s-expression"""
        try:
            # symbol expr format: (symbol (lib_id ...) (at ...) (property "Reference" ...) ...)
            reference = self._get_sexpr_value(symbol_expr, "property", 2, "")
            if not reference or not isinstance(reference, str):
                # Try alternate format
                reference = self._extract_reference(symbol_expr)

            if not reference:
                return None

            # Get properties
            value = self._extract_property(symbol_expr, "Value", "")
            footprint = self._extract_property(symbol_expr, "Footprint", "")
            lcsc_id = self._extract_property(symbol_expr, "LCSC", "")
            datasheet = self._extract_property(symbol_expr, "Datasheet", "")
            description = self._extract_property(symbol_expr, "Description", "")

            # Parse library and symbol from lib_id
            lib_id = self._get_sexpr_value(symbol_expr, "lib_id", 1, "")
            library, symbol = self._parse_lib_id(lib_id)

            component = SchematicComponent(
                reference=reference,
                value=value,
                footprint=footprint,
                lcsc_id=lcsc_id,
                datasheet=datasheet,
                description=description,
                library=library,
                symbol=symbol
            )

            # Extract all properties
            for item in symbol_expr:
                if isinstance(item, list) and len(item) > 0 and item[0] == "property":
                    prop_name = self._get_sexpr_value(item, "property", 1, "")
                    prop_value = self._get_sexpr_value(item, "property", 2, "")
                    if prop_name and prop_value:
                        component.properties[prop_name] = prop_value

            return component

        except Exception as e:
            logger.debug(f"Failed to parse symbol: {e}")
            return None

    @staticmethod
    def _extract_reference(expr: List[Any]) -> Optional[str]:
        """Extract reference designator (e.g., U1, C1) from symbol"""
        for item in expr:
            if isinstance(item, list) and len(item) >= 3:
                if item[0] == "property" and item[1] == "Reference":
                    if isinstance(item[2], str):
                        return item[2]
        return None

    @staticmethod
    def _extract_property(expr: List[Any], property_name: str, default: str = "") -> str:
        """Extract property value by name from symbol"""
        for item in expr:
            if isinstance(item, list) and len(item) >= 3:
                if item[0] == "property" and item[1] == property_name:
                    if isinstance(item[2], str):
                        return item[2]
        return default

    @staticmethod
    def _parse_lib_id(lib_id: str) -> tuple:
        """Parse lib_id string (e.g., 'Device:C') into (library, symbol)"""
        parts = lib_id.split(':')
        library = parts[0] if len(parts) > 0 else ""
        symbol = parts[1] if len(parts) > 1 else ""
        return library, symbol

    def parse_board(self, filepath: Path) -> Dict[str, Any]:
        """Parse KiCAD board file (.kicad_pcb)"""
        if not filepath.exists():
            logger.error(f"Board file not found: {filepath}")
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read board: {e}")
            return {}

        # Tokenize and parse
        tokens = self._tokenize(content)
        sexpr, _ = self._parse_sexpr(tokens)

        board_info = {
            "footprints": [],
            "nets": [],
            "tracks": [],
            "zones": []
        }

        if not isinstance(sexpr, list):
            logger.warning("Invalid board format")
            return board_info

        # Extract board elements
        for item in sexpr:
            if isinstance(item, list) and len(item) > 0:
                if item[0] == "footprint":
                    board_info["footprints"].append(self._parse_footprint(item))
                elif item[0] == "net":
                    board_info["nets"].append(self._parse_net(item))

        logger.info(f"Parsed board: {len(board_info['footprints'])} footprints, {len(board_info['nets'])} nets")
        return board_info

    @staticmethod
    def _parse_footprint(expr: List[Any]) -> Dict[str, str]:
        """Parse footprint entry from board"""
        return {
            "name": expr[1] if len(expr) > 1 else "",
            "reference": expr[2] if len(expr) > 2 else ""
        }

    @staticmethod
    def _parse_net(expr: List[Any]) -> Dict[str, Any]:
        """Parse net definition from board"""
        return {
            "number": expr[1] if len(expr) > 1 else "",
            "name": expr[2] if len(expr) > 2 else ""
        }

    def extract_bom(self, schematic_path: Path) -> Dict[str, Dict[str, Any]]:
        """Extract BOM from schematic"""
        components = self.parse_schematic(schematic_path)

        # Aggregate by value + footprint
        bom = {}
        for comp in components:
            key = f"{comp.value}_{comp.footprint}"
            if key not in bom:
                bom[key] = {
                    "value": comp.value,
                    "footprint": comp.footprint,
                    "lcsc_id": comp.lcsc_id,
                    "references": [],
                    "quantity": 0
                }
            bom[key]["references"].append(comp.reference)
            bom[key]["quantity"] += 1

        logger.info(f"Extracted BOM: {len(bom)} unique parts")
        return bom

    def validate_schematic(self, filepath: Path) -> Dict[str, List[str]]:
        """Validate schematic completeness"""
        components = self.parse_schematic(filepath)

        issues = {
            "missing_footprint": [],
            "missing_lcsc_id": [],
            "missing_value": [],
            "duplicate_reference": []
        }

        seen_refs = set()

        for comp in components:
            if not comp.footprint:
                issues["missing_footprint"].append(comp.reference)
            if not comp.lcsc_id:
                issues["missing_lcsc_id"].append(comp.reference)
            if not comp.value:
                issues["missing_value"].append(comp.reference)
            if comp.reference in seen_refs:
                issues["duplicate_reference"].append(comp.reference)
            seen_refs.add(comp.reference)

        return issues


if __name__ == "__main__":
    # Test parser
    parser = KiCADParser()

    # Test schematic parsing
    test_sch = Path("../../../drone_design/drone_model/components/electronics/daughter_board_esp32.kicad_sch")
    if test_sch.exists():
        print("Testing schematic parser...")
        components = parser.parse_schematic(test_sch)
        for comp in components[:5]:
            print(f"  {comp.reference}: {comp.value} ({comp.lcsc_id})")

        print("\nValidating schematic...")
        issues = parser.validate_schematic(test_sch)
        for issue_type, items in issues.items():
            if items:
                print(f"  {issue_type}: {items}")
    else:
        print(f"Test schematic not found: {test_sch}")
