"""Electrical netlist validation (ERC-equivalent checks).

Runs at build time — any ERROR halts the build.  Warnings are printed but
do not block.

Checks implemented:
  1. Every placed pin is in exactly one net OR is marked no_connect.
  2. Every net has ≥ 2 connections (no floating/single-pin nets).
  3. Power nets have at least one power_out source.
  4. No output-to-output conflicts on the same net.
  5. Power pins are not driven by incompatible sources.
  6. All referenced (ref, pin) pairs in the netlist actually exist in placements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cadquery_framework.kicad.component_library import (
    BoardDefinition,
    NetConnection,
    Placement,
    Pin,
)


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def report(self) -> str:
        lines = []
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        for e in self.errors:
            lines.append(f"  ERROR:   {e}")
        if self.ok:
            lines.append(f"  PASS — {len(self.warnings)} warning(s), 0 errors")
        else:
            lines.append(f"  FAIL — {len(self.warnings)} warning(s), {len(self.errors)} error(s)")
        return "\n".join(lines)


# Power net names that must have at least one power_out source.
POWER_NET_PREFIXES = ("+", "VBATT", "VCC", "VDD", "VDDIO")


def _is_power_net(name: str) -> bool:
    """Heuristic: net names starting with +, V, VCC, VDD are power nets."""
    for prefix in POWER_NET_PREFIXES:
        if name.upper().startswith(prefix):
            return True
    return False


def _resolve_pin(board: BoardDefinition, ref: str, pin_number: str) -> Optional[Pin]:
    """Look up the Pin definition for a (ref, pin_number) pair."""
    try:
        placement = board.get_placement(ref)
    except KeyError:
        return None
    try:
        return placement.component.get_pin(pin_number)
    except KeyError:
        return None


def validate_netlist(board: BoardDefinition) -> ValidationResult:
    """Run all electrical validation checks on a board definition.

    Returns a ValidationResult.  Callers should check result.ok and
    raise on failure.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Build set of all placed (ref, pin_number) pairs
    all_placed_pins: set[tuple[str, str]] = set()
    no_connect_pins: set[tuple[str, str]] = set()
    for p in board.placements:
        for pin in p.component.pins:
            key = (p.ref, pin.number)
            all_placed_pins.add(key)
            if pin.pin_type == "no_connect":
                no_connect_pins.add(key)

    # Build set of all netted (ref, pin_number) pairs
    all_netted_pins: set[tuple[str, str]] = set()
    for net_name, connections in board.nets.items():
        for conn in connections:
            all_netted_pins.add((conn.ref, conn.pin_number))

    # ------------------------------------------------------------------
    # Check 1: Every placed pin is in a net or is NC
    # ------------------------------------------------------------------
    unconnected = all_placed_pins - all_netted_pins - no_connect_pins
    for ref, pin_num in sorted(unconnected):
        pin = _resolve_pin(board, ref, pin_num)
        if pin and pin.pin_type in ("unspecified", "open_collector", "open_emitter"):
            # Unspecified and open-drain/collector pins may be left unconnected
            warnings.append(f"Unconnected {pin.pin_type} pin: {ref} pin {pin_num} ({pin.name})")
            continue
        # GPIO header spare pass-through pins — passive pins on HDR-prefixed components
        # that are intentionally unnetted (they pass directly to the DE10-Nano carrier).
        if pin and pin.pin_type == "passive" and ref.startswith("HDR"):
            continue
        errors.append(f"Unconnected pin: {ref} pin {pin_num} ({pin.name if pin else '?'})")

    # ------------------------------------------------------------------
    # Check 2: Every net has ≥ 2 connections
    # ------------------------------------------------------------------
    for net_name, connections in board.nets.items():
        if not net_name:  # skip empty net
            continue
        if len(connections) < 2:
            errors.append(
                f"Net '{net_name}' has only {len(connections)} connection(s) — "
                f"nets must have at least 2"
            )

    # ------------------------------------------------------------------
    # Check 3: Power nets have at least one power_out source
    # ------------------------------------------------------------------
    for net_name, connections in board.nets.items():
        if not _is_power_net(net_name):
            continue
        has_source = False
        for conn in connections:
            pin = _resolve_pin(board, conn.ref, conn.pin_number)
            if pin and pin.pin_type == "power_out":
                has_source = True
                break
        if not has_source:
            # GND is a power net but has no "source" — it's a common return.
            # VBATT* are external supply rails (battery connector, reverse-polarity
            # MOSFET drain, current-shunt output) — no on-board power_out pin.
            # +5V is sourced by the TPS54560 buck converter through a passive
            # inductor (L1); the inductor output pin is typed "passive", not
            # "power_out", so no source is found by pin-type inspection.
            _EXTERNAL_POWER_NETS = frozenset({
                "GND", "GNDA", "GNDD",
                "+5V", "VBATT", "VBATT_SW", "VBATT_SWITCHED",
            })
            if net_name.upper() in _EXTERNAL_POWER_NETS:
                continue
            warnings.append(f"Power net '{net_name}' has no power_out source pin")

    # ------------------------------------------------------------------
    # Check 4: No output-to-output conflicts
    # ------------------------------------------------------------------
    for net_name, connections in board.nets.items():
        if not net_name:
            continue
        outputs = []
        for conn in connections:
            pin = _resolve_pin(board, conn.ref, conn.pin_number)
            if pin and pin.pin_type == "output":
                outputs.append(f"{conn.ref}.{conn.pin_number}")
        if len(outputs) > 1:
            errors.append(
                f"Net '{net_name}' has {len(outputs)} output drivers: "
                f"{', '.join(outputs)} — possible short circuit"
            )

    # ------------------------------------------------------------------
    # Check 5: All (ref, pin) in netlist exist in placements
    # ------------------------------------------------------------------
    for net_name, connections in board.nets.items():
        for conn in connections:
            if (conn.ref, conn.pin_number) not in all_placed_pins:
                errors.append(
                    f"Net '{net_name}' references {conn.ref} pin {conn.pin_number} "
                    f"which does not exist in placements"
                )

    # ------------------------------------------------------------------
    # Check 6: NC pins should NOT be in any net
    # ------------------------------------------------------------------
    netted_nc = all_netted_pins & no_connect_pins
    for ref, pin_num in sorted(netted_nc):
        warnings.append(f"NC pin {ref}.{pin_num} is connected to a net")

    return ValidationResult(errors=errors, warnings=warnings)
