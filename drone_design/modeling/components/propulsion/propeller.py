"""GemFan 1045 — 2-blade propeller with tapered-chord blades."""

import json
import cadquery as cq
from pathlib import Path

_D = json.loads((Path(__file__).resolve().parents[3] / "cad" / "dimensions.json").read_text())

PROP_DIAMETER    = _D["propeller"]["diameter"]
PROP_HUB_D       = _D["propeller"]["hub_diameter"]
PROP_HUB_H       = _D["propeller"]["hub_height"]
PROP_BLADE_T     = _D["propeller"]["blade_thickness"]
PROP_TIP_CHORD   = _D["propeller"]["blade_tip_chord"]
PROP_ROOT_CHORD  = _D["propeller"]["blade_root_chord"]
PROP_MAX_CHORD   = _D["propeller"]["blade_max_chord"]
PROP_MAX_STATION = _D["propeller"]["blade_max_chord_station"]


def _blade_chord_at(t):
    """Return chord width at normalised span station *t* (0=root, 1=tip).

    Linearly interpolates between three control points:
      root (t=0) -> max-chord (t=PROP_MAX_STATION) -> tip (t=1).
    """
    if t <= PROP_MAX_STATION:
        frac = t / PROP_MAX_STATION
        return PROP_ROOT_CHORD + frac * (PROP_MAX_CHORD - PROP_ROOT_CHORD)
    else:
        frac = (t - PROP_MAX_STATION) / (1.0 - PROP_MAX_STATION)
        return PROP_MAX_CHORD + frac * (PROP_TIP_CHORD - PROP_MAX_CHORD)


def _make_tapered_blade(flip=False):
    """Build one tapered-chord propeller blade along the +X axis.

    The blade planform is traced as a 2D polygon (leading edge + trailing
    edge outline at multiple span stations) and extruded to blade thickness.
    Rounded tip via a semicircular arc.
    If *flip* is True the blade is mirrored to the -X axis.
    """
    blade_length = (PROP_DIAMETER - PROP_HUB_D) / 2
    hub_r = PROP_HUB_D / 2
    n_stations = 12
    sign = -1.0 if flip else 1.0

    # Collect (x, half_chord) at each station from root to tip
    stations = []
    for i in range(n_stations + 1):
        t = i / n_stations
        r = hub_r + t * blade_length
        half_c = _blade_chord_at(t) / 2.0
        stations.append((sign * r, half_c))

    # Build the blade outline: leading edge root→tip, then trailing edge tip→root
    # Leading edge (+Y side)
    pts_leading = [(x, +hc) for x, hc in stations]
    # Trailing edge (-Y side), reversed
    pts_trailing = [(x, -hc) for x, hc in reversed(stations)]

    # Combine into a closed polyline
    outline = pts_leading + pts_trailing

    # Build 2D wire and extrude
    wp = cq.Workplane("XY").moveTo(*outline[0])
    for pt in outline[1:]:
        wp = wp.lineTo(*pt)
    wp = wp.close()
    blade = wp.extrude(PROP_BLADE_T)

    return blade


def make_prop_hub():
    """GemFan 1045 propeller hub only."""
    return cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)


def make_propeller():
    """GemFan 1045 — 2-blade prop with tapered-chord blades."""
    hub = cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)
    blade1 = _make_tapered_blade(flip=False)
    blade2 = _make_tapered_blade(flip=True)
    return hub.union(blade1).union(blade2)
