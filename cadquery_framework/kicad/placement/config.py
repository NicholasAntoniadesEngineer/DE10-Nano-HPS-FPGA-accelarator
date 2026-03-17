"""Placement optimizer constants and configuration.

All tuneable parameters are collected here so they can be adjusted
without touching algorithm code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet


# ---------------------------------------------------------------------------
# Power nets excluded from signal-affinity calculations
# ---------------------------------------------------------------------------

POWER_NETS: FrozenSet[str] = frozenset({
    "GND", "+5V", "+3V3", "+1V8", "+2V8", "+1V5", "VBATT",
    "GND_0", "VCC", "VBUS", "VDD", "VSS", "AGND", "DGND",
})

# ---------------------------------------------------------------------------
# Electronics-zone to board-coordinate offset (EZ origin is inset on the
# frame).
# ---------------------------------------------------------------------------

EZ_OFFSET_X: float = 12.5
EZ_OFFSET_Y: float = 1.0

# ---------------------------------------------------------------------------
# Courtyard gap
# ---------------------------------------------------------------------------

# Minimum gap between courtyards (mm).
# Must exceed DRM_COURTYARD_CLEARANCE_MM (0.1 mm) which the validator adds
# as margin to AABB checks.  0.40 mm gives 0.30 mm clearance after the
# 0.1 mm expansion.
COURTYARD_GAP: float = 0.40


# ---------------------------------------------------------------------------
# Simulated-annealing weights
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SAWeights:
    """Objective-function weights for multi-objective SA."""

    hpwl: float = 1.0
    thermal: float = 30.0
    overlap: float = 500.0       # Lower since initial should be overlap-free
    cutout: float = 5000.0
    spread: float = 5.0


SA_WEIGHTS = SAWeights()


@dataclass(frozen=True)
class SASchedule:
    """Cooling-schedule parameters for simulated annealing."""

    t_start: float = 80.0
    alpha: float = 0.9988
    t_min: float = 0.01
    moves_per_temp: int = 5


SA_SCHEDULE = SASchedule()


# ---------------------------------------------------------------------------
# Thermal-awareness component lists
# ---------------------------------------------------------------------------

HEAT_SOURCES: FrozenSet[str] = frozenset({"U13", "L1", "R_SHUNT"})
HEAT_SENSITIVE: FrozenSet[str] = frozenset({"U5", "U11"})


# ---------------------------------------------------------------------------
# Edge-preference targets (callable factory — needs board dimensions)
# ---------------------------------------------------------------------------

def make_edge_targets(bw: float, bh: float) -> dict[str, tuple[float, float]]:
    """Return subsystem-name -> (x, y) preferred positions.

    Called once per optimiser run after board dimensions are known.
    """
    return {
        "power_buck": (bw * 0.35, 8.0),
        "power_ldo_3v3": (bw * 0.45, 15.0),
        "current_sense": (bw * 0.55, 10.0),
        "dshot_ch1": (15.0, bh * 0.20),
        "dshot_ch2": (15.0, bh * 0.35),
        "dshot_ch3": (15.0, bh * 0.65),
        "dshot_ch4": (15.0, bh * 0.80),
        "wifi_ble": (bw * 0.78, bh * 0.82),
        "camera": (bw * 0.3, bh - 12.0),
        "imu": (bw * 0.5, bh * 0.40),
        "barometer": (bw * 0.6, bh * 0.55),
        "ir_front": (bw - 15.0, bh * 0.3),
        "ir_left": (bw * 0.3, 15.0),
        "ir_right": (bw * 0.7, bh - 15.0),
        "ir_rear": (15.0, bh * 0.7),
        "tof_hub": (bw * 0.45, bh * 0.45),
        "leds": (bw - 15.0, bh * 0.50),
        "switches": (bw - 15.0, bh * 0.65),
        "pump_driver": (bw * 0.6, bh - 12.0),
        "buzzer_driver": (bw * 0.7, bh - 12.0),
    }
