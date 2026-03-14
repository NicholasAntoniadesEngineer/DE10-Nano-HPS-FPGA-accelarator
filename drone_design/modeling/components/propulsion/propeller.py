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

    The blade is constructed from five extruded segments unioned together,
    each with the interpolated chord width at that radial station.
    If *flip* is True the blade is mirrored to the -X axis.
    """
    blade_length = (PROP_DIAMETER - PROP_HUB_D) / 2
    hub_r = PROP_HUB_D / 2
    n_segments = 5
    sign = -1.0 if flip else 1.0

    result = None
    for i in range(n_segments):
        t0 = i / n_segments
        t1 = (i + 1) / n_segments
        t_mid = (t0 + t1) / 2.0

        r_inner = hub_r + t0 * blade_length
        r_outer = hub_r + t1 * blade_length
        seg_len = r_outer - r_inner
        chord = _blade_chord_at(t_mid)

        cx = sign * (r_inner + seg_len / 2.0)
        seg = (
            cq.Workplane("XY")
            .center(cx, 0)
            .ellipse(seg_len / 2.0, chord / 2.0)
            .extrude(PROP_BLADE_T)
        )
        result = seg if result is None else result.union(seg)

    return result


def make_prop_hub():
    """GemFan 1045 propeller hub only."""
    return cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)


def make_propeller():
    """GemFan 1045 — 2-blade prop with tapered-chord blades."""
    hub = cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)
    blade1 = _make_tapered_blade(flip=False)
    blade2 = _make_tapered_blade(flip=True)
    return hub.union(blade1).union(blade2)
