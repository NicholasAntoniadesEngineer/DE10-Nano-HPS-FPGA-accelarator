"""Component data model for PCB generation.

Defines the core dataclasses used to describe electronic components at the
pin and pad level.  Every ComponentDef carries enough information to:
  1. Generate a KiCad footprint (pads + courtyard + silkscreen)
  2. Generate a KiCad schematic symbol (pins + properties)
  3. Produce JLCPCB BOM and CPL CSV rows
  4. Run electrical and physical validation

All pad dimensions MUST come from manufacturer datasheets or IPC-7351B.
Never guess pad geometry — cite the source in the footprint generator that
produces the PadGeometry list.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Pin definition (electrical)
# ---------------------------------------------------------------------------

# Allowed pin types — used for ERC validation.
PIN_TYPES = frozenset({
    "power_in",       # VCC, GND — consumes power
    "power_out",      # regulator output — supplies power
    "input",          # logic / analog input
    "output",         # logic / analog output
    "bidirectional",  # I2C SDA, SPI MISO (tri-state)
    "passive",        # resistor / capacitor terminal
    "no_connect",     # explicitly unused pin
    "open_collector", # open-drain / open-collector output
    "open_emitter",   # open-emitter output (rare)
    "unspecified",    # for pins where type is unknown / don't-care
})


@dataclass(frozen=True)
class Pin:
    """One electrical pin of a component."""

    number: str        # pad/pin number as string ("1", "A1", "EP")
    name: str          # human-readable name ("VCC", "SDA", "GND_PAD")
    pin_type: str      # one of PIN_TYPES

    def __post_init__(self):
        if self.pin_type not in PIN_TYPES:
            raise ValueError(
                f"Pin {self.number} ({self.name}): invalid pin_type "
                f"'{self.pin_type}'. Must be one of {sorted(PIN_TYPES)}"
            )


# ---------------------------------------------------------------------------
# Pad geometry (physical)
# ---------------------------------------------------------------------------

# Allowed pad shapes.
PAD_SHAPES = frozenset({"circle", "rect", "roundrect", "oval", "custom"})
PAD_TYPES = frozenset({"smd", "thru_hole", "np_thru_hole", "connect"})

# Standard layer sets.
SMD_FRONT_LAYERS = ("F.Cu", "F.Paste", "F.Mask")
SMD_BACK_LAYERS = ("B.Cu", "B.Paste", "B.Mask")
TH_LAYERS = ("*.Cu", "*.Mask")
NPTH_LAYERS = ("*.Cu", "*.Mask")


@dataclass(frozen=True)
class PadGeometry:
    """Physical pad for a PCB footprint.

    Coordinates are relative to the component centre (mm).
    For through-hole pads, ``drill`` is the finished hole diameter.
    """

    number: str                        # matches Pin.number
    x: float                           # mm, relative to component centre
    y: float                           # mm
    width: float                       # pad width (mm)
    height: float                      # pad height (mm)
    shape: str = "rect"                # one of PAD_SHAPES
    pad_type: str = "smd"              # one of PAD_TYPES
    layers: tuple[str, ...] = SMD_FRONT_LAYERS
    drill: float = 0.0                 # finished hole diameter (mm), 0 for SMD
    roundrect_rratio: float = 0.25     # corner radius ratio for roundrect

    def __post_init__(self):
        if self.shape not in PAD_SHAPES:
            raise ValueError(f"Pad {self.number}: invalid shape '{self.shape}'")
        if self.pad_type not in PAD_TYPES:
            raise ValueError(f"Pad {self.number}: invalid pad_type '{self.pad_type}'")
        if self.pad_type == "thru_hole" and self.drill <= 0:
            raise ValueError(f"Pad {self.number}: thru_hole pad must have drill > 0")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Pad {self.number}: width and height must be > 0")


# ---------------------------------------------------------------------------
# Component definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComponentDef:
    """Complete definition of an electronic component.

    Carries everything needed to generate footprint, symbol, and BOM data.
    Instances are typically created once per unique part and reused across
    placements (e.g. the same 100nF 0402 cap used 15+ times on a board).
    """

    ref_prefix: str          # "U", "R", "C", "J", "D", "Q", "L", "LED", etc.
    value: str               # "10k", "100nF", "ICM-20948"
    package: str             # "0402", "QFN-24", "SOT-23-5"
    description: str         # human-readable description
    mpn: str                 # manufacturer part number
    lcsc: str                # LCSC part number for JLCPCB assembly ("" if N/A)
    datasheet: str           # URL or filename of source datasheet
    pins: tuple[Pin, ...]    # all electrical pins
    pads: tuple[PadGeometry, ...]  # all physical pads
    courtyard_w: float       # bounding box width (mm) — includes margin
    courtyard_h: float       # bounding box height (mm)

    def __post_init__(self):
        # Validate that every pad number corresponds to a pin number
        pin_numbers = {p.number for p in self.pins}
        pad_numbers = {p.number for p in self.pads}
        missing = pad_numbers - pin_numbers
        if missing:
            raise ValueError(
                f"{self.mpn}: pads {missing} have no matching pin definition"
            )

    @property
    def pin_count(self) -> int:
        return len(self.pins)

    def get_pin(self, number: str) -> Pin:
        """Look up a pin by its number."""
        for p in self.pins:
            if p.number == number:
                return p
        raise KeyError(f"{self.mpn}: no pin with number '{number}'")

    def get_pad(self, number: str) -> PadGeometry:
        """Look up a pad by its number."""
        for p in self.pads:
            if p.number == number:
                return p
        raise KeyError(f"{self.mpn}: no pad with number '{number}'")

    @property
    def has_thru_holes(self) -> bool:
        return any(p.pad_type in ("thru_hole", "np_thru_hole") for p in self.pads)


# ---------------------------------------------------------------------------
# Board placement
# ---------------------------------------------------------------------------

@dataclass
class Placement:
    """One component placed on a PCB at a specific location.

    The same ComponentDef may appear in many Placements with different
    reference designators and positions.
    """

    component: ComponentDef
    ref: str               # reference designator: "U5", "R1", "C12"
    x: float               # board X position (mm), origin = board top-left
    y: float               # board Y position (mm)
    rotation: float = 0.0  # degrees, counter-clockwise
    side: str = "F"        # "F" (front/top) or "B" (back/bottom)

    def __post_init__(self):
        if self.side not in ("F", "B"):
            raise ValueError(f"{self.ref}: side must be 'F' or 'B', got '{self.side}'")

    @property
    def courtyard_bounds(self) -> tuple[float, float, float, float]:
        """Return (xmin, ymin, xmax, ymax) of the rotated courtyard AABB."""
        w = self.component.courtyard_w
        h = self.component.courtyard_h
        # Compute rotated bounding box
        rad = math.radians(self.rotation)
        cos_a = abs(math.cos(rad))
        sin_a = abs(math.sin(rad))
        rot_w = w * cos_a + h * sin_a
        rot_h = w * sin_a + h * cos_a
        return (
            self.x - rot_w / 2,
            self.y - rot_h / 2,
            self.x + rot_w / 2,
            self.y + rot_h / 2,
        )


# ---------------------------------------------------------------------------
# Net connection (for netlist)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NetConnection:
    """One pin connected to a net."""

    ref: str        # placement reference designator
    pin_number: str # pin number on that component


# ---------------------------------------------------------------------------
# Keep-out zone (for courtyard checking)
# ---------------------------------------------------------------------------

@dataclass
class KeepOutZone:
    """A rectangular keep-out zone on the board."""

    name: str       # e.g. "WILC3000 antenna keep-out"
    owner_ref: str  # ref of component that owns this zone (excluded from check)
    xmin: float
    ymin: float
    xmax: float
    ymax: float


# ---------------------------------------------------------------------------
# Board definition (ties everything together)
# ---------------------------------------------------------------------------

@dataclass
class BoardDefinition:
    """Complete board definition for PCB generation and validation."""

    title: str
    width: float              # mm
    height: float             # mm
    corner_radius: float      # mm
    thickness: float          # mm (PCB thickness)
    placements: list[Placement] = field(default_factory=list)
    nets: dict[str, list[NetConnection]] = field(default_factory=dict)
    keep_outs: list[KeepOutZone] = field(default_factory=list)
    mounting_holes: list[tuple[float, float, float]] = field(default_factory=list)  # (x, y, drill_d)

    def get_placement(self, ref: str) -> Placement:
        """Look up a placement by reference designator."""
        for p in self.placements:
            if p.ref == ref:
                return p
        raise KeyError(f"No placement with ref '{ref}'")

    def all_refs(self) -> set[str]:
        """Return all reference designators."""
        return {p.ref for p in self.placements}

    def all_net_names(self) -> set[str]:
        """Return all net names (excluding empty net)."""
        return {n for n in self.nets if n}

    def net_count(self) -> int:
        """Total number of named nets."""
        return len(self.all_net_names())
