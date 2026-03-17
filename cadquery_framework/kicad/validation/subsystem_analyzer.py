"""Subsystem-aware placement analysis and validation.

Models the PCB as a graph of functional subsystems, where each subsystem
is an IC (or active device) plus its satellite passives (decoupling caps,
pull-up/down resistors, protection diodes, etc.).  The analyser then
validates that each subsystem satisfies datasheet-driven placement rules:

  - Decoupling caps within max distance of their IC's power pins
  - Pull-up/down resistors on the correct signal side
  - Thermal separation between analog-sensitive and heat-generating ICs
  - Connector edge proximity for cable routing
  - RF keep-out clearance around antenna modules
  - Forbidden zone avoidance (heatsink cutout, mounting holes)

The subsystem graph is built automatically from the net connections:
if a passive shares a power net with an IC and also connects to GND,
it's classified as that IC's decoupling cap.  Pull-ups are identified
by connecting a signal net to a power rail through a resistor.

This replaces ad-hoc placement checks with a structured, extensible
system that understands *why* components are placed where they are.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from cadquery_framework.kicad.component_library import (
    BoardDefinition,
    KeepOutZone,
    NetConnection,
    Placement,
)


# ---------------------------------------------------------------------------
# Component classification
# ---------------------------------------------------------------------------

class ComponentRole(Enum):
    """Functional role of a component on the board."""
    IC_DIGITAL = auto()          # Digital IC (buffer, mux, translator)
    IC_ANALOG = auto()           # Analog/mixed-signal IC (IMU, barometer, ADC)
    IC_POWER = auto()            # Power regulator (buck, LDO)
    IC_RF = auto()               # RF module (WiFi, BLE, GPS)
    MOSFET_SWITCH = auto()       # Switching MOSFET (pump, buzzer driver)
    DECOUPLING_CAP = auto()      # Bypass/decoupling capacitor
    BULK_CAP = auto()            # Bulk/reservoir capacitor
    PULL_RESISTOR = auto()       # Pull-up or pull-down resistor
    SERIES_RESISTOR = auto()     # Current-limiting or series termination
    FEEDBACK_RESISTOR = auto()   # Voltage divider / feedback network
    PROTECTION = auto()          # TVS, Zener, Schottky diode
    INDUCTOR = auto()            # Power inductor
    CONNECTOR = auto()           # External connector (JST, FPC, header, barrel)
    LED = auto()                 # Status LED
    GPIO_HEADER = auto()         # GPIO pass-through header
    PASSIVE_OTHER = auto()       # Unclassified passive


class SubsystemType(Enum):
    """Broad category for placement rule selection."""
    POWER_SWITCHING = auto()     # Buck converter — tight hot loop, thermal isolation
    POWER_LINEAR = auto()        # LDO — moderate thermal, close to load
    SENSOR_ANALOG = auto()       # IMU, barometer — vibration/thermal sensitivity
    SENSOR_DIGITAL = auto()      # ToF hub, digital sensors — moderate constraints
    MOTOR_DRIVER = auto()        # DShot buffers + ESC connectors — edge placement
    RF_MODULE = auto()           # WiFi/BLE — antenna keep-out, edge placement
    CAMERA_INTERFACE = auto()    # Camera FPC + LDOs — signal integrity
    ACTUATOR_DRIVER = auto()     # Pump/buzzer MOSFET driver
    UI_INDICATOR = auto()        # LEDs, switches
    CURRENT_SENSE = auto()       # INA219 + shunt


# ---------------------------------------------------------------------------
# Datasheet-driven placement constraints
# ---------------------------------------------------------------------------

class PlacementConstraint:
    """One rule that a subsystem's components must satisfy."""

    def __init__(self, description: str, is_error: bool = True):
        self.description = description
        self.is_error = is_error

    def check(self, subsystem: "Subsystem", board: BoardDefinition) -> Optional[str]:
        """Return violation message, or None if satisfied."""
        raise NotImplementedError


class MaxDistanceConstraint(PlacementConstraint):
    """A satellite component must be within max_mm of the IC centre."""

    def __init__(self, description: str, satellite_ref: str, ic_ref: str,
                 max_mm: float, is_error: bool = True):
        super().__init__(description, is_error)
        self.satellite_ref = satellite_ref
        self.ic_ref = ic_ref
        self.max_mm = max_mm

    def check(self, subsystem: "Subsystem", board: BoardDefinition) -> Optional[str]:
        sat = _find_placement(board, self.satellite_ref)
        ic = _find_placement(board, self.ic_ref)
        if not sat or not ic:
            return None
        dist = math.hypot(sat.x - ic.x, sat.y - ic.y)
        if dist > self.max_mm:
            return (
                f"{self.satellite_ref} is {dist:.1f}mm from {self.ic_ref} "
                f"(max {self.max_mm}mm per datasheet) — {self.description}"
            )
        return None


class MinSeparationConstraint(PlacementConstraint):
    """Two components must be at least min_mm apart."""

    def __init__(self, description: str, ref_a: str, ref_b: str,
                 min_mm: float, is_error: bool = True):
        super().__init__(description, is_error)
        self.ref_a = ref_a
        self.ref_b = ref_b
        self.min_mm = min_mm

    def check(self, subsystem: "Subsystem", board: BoardDefinition) -> Optional[str]:
        a = _find_placement(board, self.ref_a)
        b = _find_placement(board, self.ref_b)
        if not a or not b:
            return None
        dist = math.hypot(a.x - b.x, a.y - b.y)
        if dist < self.min_mm:
            return (
                f"{self.ref_a} ↔ {self.ref_b}: {dist:.1f}mm apart "
                f"(min {self.min_mm}mm) — {self.description}"
            )
        return None


class EdgeProximityConstraint(PlacementConstraint):
    """Component must be within max_mm of the nearest board edge."""

    def __init__(self, description: str, ref: str, max_mm: float,
                 is_error: bool = True):
        super().__init__(description, is_error)
        self.ref = ref
        self.max_mm = max_mm

    def check(self, subsystem: "Subsystem", board: BoardDefinition) -> Optional[str]:
        p = _find_placement(board, self.ref)
        if not p:
            return None
        edge_dist = min(p.x, board.width - p.x, p.y, board.height - p.y)
        if edge_dist > self.max_mm:
            return (
                f"{self.ref} is {edge_dist:.1f}mm from nearest edge "
                f"(max {self.max_mm}mm) — {self.description}"
            )
        return None


class ForbiddenZoneConstraint(PlacementConstraint):
    """Component must NOT be inside the given rectangular zone."""

    def __init__(self, description: str, ref: str, zone_name: str,
                 xmin: float, ymin: float, xmax: float, ymax: float,
                 is_error: bool = True):
        super().__init__(description, is_error)
        self.ref = ref
        self.zone_name = zone_name
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    def check(self, subsystem: "Subsystem", board: BoardDefinition) -> Optional[str]:
        p = _find_placement(board, self.ref)
        if not p:
            return None
        bounds = p.courtyard_bounds
        if (bounds[2] > self.xmin and bounds[0] < self.xmax and
                bounds[3] > self.ymin and bounds[1] < self.ymax):
            return (
                f"{self.ref} at ({p.x:.1f}, {p.y:.1f}) is inside "
                f"'{self.zone_name}' zone [{self.xmin:.0f},{self.ymin:.0f}]-"
                f"[{self.xmax:.0f},{self.ymax:.0f}] — {self.description}"
            )
        return None


class PinSidePlacementConstraint(PlacementConstraint):
    """Satellite should be on a specific side of the IC."""

    def __init__(self, description: str, satellite_ref: str, ic_ref: str,
                 preferred_side: str, is_error: bool = False):
        super().__init__(description, is_error)
        self.satellite_ref = satellite_ref
        self.ic_ref = ic_ref
        self.preferred_side = preferred_side

    def check(self, subsystem: "Subsystem", board: BoardDefinition) -> Optional[str]:
        sat = _find_placement(board, self.satellite_ref)
        ic = _find_placement(board, self.ic_ref)
        if not sat or not ic:
            return None
        dx = sat.x - ic.x
        dy = sat.y - ic.y
        if abs(dx) > abs(dy):
            actual_side = "right" if dx > 0 else "left"
        else:
            actual_side = "bottom" if dy > 0 else "top"

        if actual_side != self.preferred_side:
            return (
                f"{self.satellite_ref} is {actual_side} of {self.ic_ref}, "
                f"but should be {self.preferred_side} — {self.description}"
            )
        return None


# ---------------------------------------------------------------------------
# Subsystem definition
# ---------------------------------------------------------------------------

@dataclass
class Subsystem:
    """A functional group: one primary IC + its satellite passives."""
    name: str
    subsystem_type: SubsystemType
    primary_ref: str                          # IC reference designator
    satellite_refs: list[str] = field(default_factory=list)
    constraints: list[PlacementConstraint] = field(default_factory=list)
    roles: dict[str, ComponentRole] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_placement(board: BoardDefinition, ref: str) -> Optional[Placement]:
    try:
        return board.get_placement(ref)
    except KeyError:
        return None


def _distance(board: BoardDefinition, ref_a: str, ref_b: str) -> float:
    a = _find_placement(board, ref_a)
    b = _find_placement(board, ref_b)
    if not a or not b:
        return float("inf")
    return math.hypot(a.x - b.x, a.y - b.y)


# ---------------------------------------------------------------------------
# Subsystem builder — auto-discover from netlist topology
# ---------------------------------------------------------------------------

def _classify_ref(ref: str, value: str, package: str) -> ComponentRole:
    """Heuristic classification from reference designator and value."""
    prefix = "".join(c for c in ref if c.isalpha() or c == "_")
    if prefix in ("HDR",):
        return ComponentRole.GPIO_HEADER
    if prefix in ("J",):
        return ComponentRole.CONNECTOR
    if prefix in ("LED",):
        return ComponentRole.LED
    if prefix in ("L",):
        return ComponentRole.INDUCTOR
    if prefix in ("D",):
        return ComponentRole.PROTECTION
    if prefix in ("Q",):
        return ComponentRole.MOSFET_SWITCH
    if prefix in ("U",):
        # Distinguish IC types by package/value heuristics
        val_lower = value.lower()
        if any(k in val_lower for k in ("tps54", "tps62", "lm25", "mp2")):
            return ComponentRole.IC_POWER
        if any(k in val_lower for k in ("icm", "bmp", "bmi", "lis", "ina")):
            return ComponentRole.IC_ANALOG
        if any(k in val_lower for k in ("wilc", "esp", "nrf", "cc26")):
            return ComponentRole.IC_RF
        if any(k in val_lower for k in ("ap2112", "tps7a", "ams1117")):
            return ComponentRole.IC_POWER
        return ComponentRole.IC_DIGITAL
    if prefix in ("C",):
        # Caps > 4.7uF are bulk, otherwise decoupling
        val_lower = value.lower()
        for bulk_val in ("10uf", "22uf", "47uf", "100uf"):
            if bulk_val in val_lower.replace(" ", ""):
                return ComponentRole.BULK_CAP
        return ComponentRole.DECOUPLING_CAP
    if prefix in ("R",):
        return ComponentRole.PULL_RESISTOR  # refined later by net analysis
    return ComponentRole.PASSIVE_OTHER


# Power rail nets connect dozens of components and shouldn't drive
# satellite assignment.  Exclude them from "meaningful shared nets".
_POWER_RAIL_NETS = {
    "GND", "+3V3", "+5V", "+1V8", "+2V8", "+1V5", "VBATT",
    "VCC", "VDD", "VDDIO", "3V3", "5V", "1V8",
}


def build_subsystems_from_netlist(board: BoardDefinition) -> list[Subsystem]:
    """Automatically discover subsystems from the board's net connections.

    Strategy:
      1. Identify all ICs/active devices as subsystem primaries
      2. For each passive, find which IC it shares the most nets with
      3. Assign passives to the nearest IC that shares a net
      4. Generate datasheet-driven constraints per subsystem type
    """
    # Build reverse index: ref → list of net names it appears in
    ref_nets: dict[str, set[str]] = {}
    for net_name, connections in board.nets.items():
        for conn in connections:
            ref_nets.setdefault(conn.ref, set()).add(net_name)

    # Classify all components
    roles: dict[str, ComponentRole] = {}
    for p in board.placements:
        roles[p.ref] = _classify_ref(p.ref, p.component.value, p.component.package)

    # Identify primaries (ICs, MOSFETs, RF modules)
    primary_roles = {
        ComponentRole.IC_DIGITAL, ComponentRole.IC_ANALOG,
        ComponentRole.IC_POWER, ComponentRole.IC_RF,
        ComponentRole.MOSFET_SWITCH,
    }
    primaries = [p.ref for p in board.placements if roles.get(p.ref) in primary_roles]

    # Assign each passive to the closest IC that shares a net
    passive_roles = {
        ComponentRole.DECOUPLING_CAP, ComponentRole.BULK_CAP,
        ComponentRole.PULL_RESISTOR, ComponentRole.SERIES_RESISTOR,
        ComponentRole.FEEDBACK_RESISTOR, ComponentRole.PROTECTION,
        ComponentRole.PASSIVE_OTHER,
    }
    passive_refs = [p.ref for p in board.placements if roles.get(p.ref) in passive_roles]

    # For each passive, find which primary shares the most nets AND is closest
    assignment: dict[str, str] = {}  # passive_ref → primary_ref
    for pref in passive_refs:
        p_nets = ref_nets.get(pref, set())
        best_primary = None
        best_score = -1
        best_dist = float("inf")

        for ic_ref in primaries:
            ic_nets = ref_nets.get(ic_ref, set())
            # Signal nets only (exclude power rails that connect everything)
            shared_signal = p_nets & ic_nets - _POWER_RAIL_NETS
            # Power rail connections as weak tie-breaker, but only if there's
            # at least one signal net shared.  A cap that only shares "+3V3"
            # with an IC is a generic rail cap, not that IC's decoupling cap.
            shared_power = (p_nets & ic_nets) & _POWER_RAIL_NETS - {"GND"}
            if shared_signal:
                score = len(shared_signal) * 10 + len(shared_power)
            else:
                # Power-only connection: only count if the passive is
                # physically close (< 8mm) — likely a local decoupling cap.
                dist = _distance(board, pref, ic_ref)
                if dist < 8.0 and shared_power:
                    score = len(shared_power)
                else:
                    score = 0

            if score > 0:
                dist = _distance(board, pref, ic_ref)
                # Prefer higher net overlap, break ties by distance
                if score > best_score or (score == best_score and dist < best_dist):
                    best_primary = ic_ref
                    best_score = score
                    best_dist = dist

        if best_primary:
            assignment[pref] = best_primary

    # Build subsystems
    subsystem_members: dict[str, list[str]] = {ic: [] for ic in primaries}
    for pref, ic_ref in assignment.items():
        subsystem_members[ic_ref].append(pref)

    # Determine subsystem types
    subsystem_type_map = {
        ComponentRole.IC_POWER: SubsystemType.POWER_SWITCHING,
        ComponentRole.IC_ANALOG: SubsystemType.SENSOR_ANALOG,
        ComponentRole.IC_DIGITAL: SubsystemType.SENSOR_DIGITAL,
        ComponentRole.IC_RF: SubsystemType.RF_MODULE,
        ComponentRole.MOSFET_SWITCH: SubsystemType.ACTUATOR_DRIVER,
    }

    subsystems: list[Subsystem] = []
    for ic_ref in primaries:
        ic_role = roles[ic_ref]
        ss_type = subsystem_type_map.get(ic_role, SubsystemType.SENSOR_DIGITAL)

        # Refine type based on specific component
        placement = _find_placement(board, ic_ref)
        if placement:
            val = placement.component.value.lower()
            if "ap2112" in val or "tps7a" in val:
                ss_type = SubsystemType.POWER_LINEAR
            elif "ina219" in val:
                ss_type = SubsystemType.CURRENT_SENSE
            elif "icm" in val or "bmp" in val:
                ss_type = SubsystemType.SENSOR_ANALOG
            elif "74lvc" in val:
                ss_type = SubsystemType.MOTOR_DRIVER
            elif "tca9548" in val:
                ss_type = SubsystemType.SENSOR_DIGITAL

        ss = Subsystem(
            name=f"{ic_ref} subsystem",
            subsystem_type=ss_type,
            primary_ref=ic_ref,
            satellite_refs=subsystem_members[ic_ref],
            roles={ic_ref: ic_role, **{r: roles[r] for r in subsystem_members[ic_ref]}},
        )
        subsystems.append(ss)

    return subsystems


# ---------------------------------------------------------------------------
# Constraint generator — applies datasheet rules per subsystem type
# ---------------------------------------------------------------------------

# Decoupling cap max distance from IC, per subsystem type (mm)
_DECAP_MAX_DIST = {
    SubsystemType.SENSOR_ANALOG: 5.0,     # ICM-20948 DS: "as close as possible" — 5mm practical
                                           # minimum given QFN-24 3mm body + courtyard margins
    SubsystemType.POWER_SWITCHING: 5.0,    # TPS54560: tight input cap loop
    SubsystemType.POWER_LINEAR: 5.0,       # LDO: close output cap (SOT-23 body + cap courtyard)
    SubsystemType.SENSOR_DIGITAL: 5.0,     # TCA9548A: standard
    SubsystemType.RF_MODULE: 5.0,          # WILC3000: close VCC bypass
    SubsystemType.ACTUATOR_DRIVER: 8.0,    # MOSFET: relaxed
    SubsystemType.MOTOR_DRIVER: 5.0,       # Buffer: standard
    SubsystemType.CURRENT_SENSE: 5.0,      # INA219: standard
    SubsystemType.CAMERA_INTERFACE: 5.0,
    SubsystemType.UI_INDICATOR: 10.0,
}

# Thermal separation requirements: (sensitive_type, heat_type) → min distance
_THERMAL_PAIRS: list[tuple[SubsystemType, SubsystemType, float, str]] = [
    (SubsystemType.SENSOR_ANALOG, SubsystemType.POWER_SWITCHING, 25.0,
     "Analog sensor must be thermally isolated from switching regulator"),
    # Note: ACTUATOR_DRIVER includes small signal MOSFETs (BSS138 <1mW)
    # alongside power MOSFETs (AO3400A ~1W).  The 8mm threshold is a
    # compromise — true high-power drivers should be further, but signal-
    # level translators don't generate meaningful heat.
    (SubsystemType.SENSOR_ANALOG, SubsystemType.ACTUATOR_DRIVER, 5.0,
     "Analog sensor should be away from MOSFET heat sources"),
]


def generate_constraints(
    subsystems: list[Subsystem],
    board: BoardDefinition,
    forbidden_zones: Optional[list[tuple[str, float, float, float, float]]] = None,
) -> None:
    """Populate each subsystem's constraint list based on its type.

    Args:
        subsystems: List of discovered subsystems (modified in place).
        board: Board definition for placement lookups.
        forbidden_zones: List of (name, xmin, ymin, xmax, ymax) zones where
            no component may be placed (e.g. heatsink cutout).
    """
    # Index subsystems by ref
    ref_to_ss: dict[str, Subsystem] = {}
    for ss in subsystems:
        ref_to_ss[ss.primary_ref] = ss
        for sat in ss.satellite_refs:
            ref_to_ss[sat] = ss

    # Build ref → nets index for decoupling cap filtering
    ref_nets: dict[str, set[str]] = {}
    for net_name, connections in board.nets.items():
        for conn in connections:
            ref_nets.setdefault(conn.ref, set()).add(net_name)

    for ss in subsystems:
        # --- Decoupling cap distance constraints ---
        # Only apply to caps that are actually on a power rail (VCC/GND pair).
        # Caps on signal nets only (e.g. RC filter, AC coupling) are not
        # decoupling caps and shouldn't have tight distance requirements.
        max_dist = _DECAP_MAX_DIST.get(ss.subsystem_type, 6.0)
        for sat_ref in ss.satellite_refs:
            role = ss.roles.get(sat_ref, ComponentRole.PASSIVE_OTHER)
            if role in (ComponentRole.DECOUPLING_CAP, ComponentRole.BULK_CAP):
                sat_nets = ref_nets.get(sat_ref, set())
                is_power_decap = bool(sat_nets & _POWER_RAIL_NETS - {"GND"})
                if not is_power_decap:
                    continue  # RC filter / AC coupling cap — skip distance rule
                ss.constraints.append(MaxDistanceConstraint(
                    description=(
                        f"Decoupling cap must be within {max_dist}mm of IC "
                        f"(datasheet recommendation for {ss.subsystem_type.name})"
                    ),
                    satellite_ref=sat_ref,
                    ic_ref=ss.primary_ref,
                    max_mm=max_dist,
                ))

        # --- Thermal separation ---
        for other_ss in subsystems:
            if other_ss is ss:
                continue
            for sens_type, heat_type, min_dist, reason in _THERMAL_PAIRS:
                if ss.subsystem_type == sens_type and other_ss.subsystem_type == heat_type:
                    ss.constraints.append(MinSeparationConstraint(
                        description=reason,
                        ref_a=ss.primary_ref,
                        ref_b=other_ss.primary_ref,
                        min_mm=min_dist,
                    ))

        # --- Connector edge proximity ---
        if ss.subsystem_type == SubsystemType.RF_MODULE:
            ss.constraints.append(EdgeProximityConstraint(
                description="RF module antenna must be at board edge",
                ref=ss.primary_ref,
                max_mm=20.0,  # WILC3000 module is 19.2mm wide; centre can be up to
                              # ~10mm from edge and still have antenna at edge
            ))

        # All connectors should be near edges
        for sat_ref in ss.satellite_refs:
            role = ss.roles.get(sat_ref, ComponentRole.PASSIVE_OTHER)
            if role == ComponentRole.CONNECTOR:
                p = _find_placement(board, sat_ref)
                if p and p.component.has_thru_holes:
                    ss.constraints.append(EdgeProximityConstraint(
                        description="Through-hole connector should be near board edge",
                        ref=sat_ref,
                        max_mm=20.0,
                        is_error=False,
                    ))

        # --- Forbidden zone constraints ---
        if forbidden_zones:
            all_refs = [ss.primary_ref] + ss.satellite_refs
            for ref in all_refs:
                for zone_name, xmin, ymin, xmax, ymax in forbidden_zones:
                    ss.constraints.append(ForbiddenZoneConstraint(
                        description=f"Component in physical cutout — no PCB material here",
                        ref=ref,
                        zone_name=zone_name,
                        xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax,
                    ))


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass
class SubsystemResult:
    errors: list[str]
    warnings: list[str]
    subsystems: list[Subsystem]
    unassigned_refs: list[str]  # components not assigned to any subsystem

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def report(self) -> str:
        lines = []
        lines.append(f"  Subsystems discovered: {len(self.subsystems)}")
        for ss in self.subsystems:
            lines.append(
                f"    {ss.primary_ref} ({ss.subsystem_type.name}): "
                f"{len(ss.satellite_refs)} satellites, "
                f"{len(ss.constraints)} rules"
            )
        if self.unassigned_refs:
            lines.append(
                f"  Unassigned components: {', '.join(sorted(self.unassigned_refs))}"
            )
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        for e in self.errors:
            lines.append(f"  ERROR:   {e}")
        if self.ok:
            lines.append(
                f"  PASS — {len(self.warnings)} warning(s), 0 errors"
            )
        else:
            lines.append(
                f"  FAIL — {len(self.warnings)} warning(s), "
                f"{len(self.errors)} error(s)"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def validate_subsystems(
    board: BoardDefinition,
    forbidden_zones: Optional[list[tuple[str, float, float, float, float]]] = None,
) -> SubsystemResult:
    """Discover subsystems, apply constraints, and validate.

    Args:
        board: Complete board definition.
        forbidden_zones: List of (name, xmin, ymin, xmax, ymax) rectangular
            forbidden zones (e.g. heatsink cutout in 110×110 board coords).

    Returns:
        SubsystemResult with all discovered subsystems and violations.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Discover subsystems from netlist topology
    subsystems = build_subsystems_from_netlist(board)

    # 2. Generate constraints based on subsystem type + datasheet rules
    generate_constraints(subsystems, board, forbidden_zones)

    # 3. Find unassigned components
    assigned = set()
    for ss in subsystems:
        assigned.add(ss.primary_ref)
        assigned.update(ss.satellite_refs)
    all_refs = {p.ref for p in board.placements}
    unassigned = sorted(all_refs - assigned)

    # 4. Check forbidden zones for unassigned components too
    if forbidden_zones:
        for ref in unassigned:
            for zone_name, xmin, ymin, xmax, ymax in forbidden_zones:
                p = _find_placement(board, ref)
                if not p:
                    continue
                bounds = p.courtyard_bounds
                if (bounds[2] > xmin and bounds[0] < xmax and
                        bounds[3] > ymin and bounds[1] < ymax):
                    errors.append(
                        f"{ref} at ({p.x:.1f}, {p.y:.1f}) is inside "
                        f"'{zone_name}' forbidden zone — no PCB material here"
                    )

    # 5. Run all constraints
    for ss in subsystems:
        for constraint in ss.constraints:
            msg = constraint.check(ss, board)
            if msg:
                if constraint.is_error:
                    errors.append(msg)
                else:
                    warnings.append(msg)

    return SubsystemResult(
        errors=errors,
        warnings=warnings,
        subsystems=subsystems,
        unassigned_refs=unassigned,
    )
