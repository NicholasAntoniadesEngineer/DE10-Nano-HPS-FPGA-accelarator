"""
Assembly package — component catalog and manifest builder.
"""

from .catalog import COMPONENT_CATALOG, INDIVIDUAL_PARTS
from .manifest import build_drone_manifest, get_assembly_constraints

__all__ = ["COMPONENT_CATALOG", "INDIVIDUAL_PARTS", "build_drone_manifest", "get_assembly_constraints"]
