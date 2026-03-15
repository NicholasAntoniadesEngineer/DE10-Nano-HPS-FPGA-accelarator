"""GemFan 1045 — 2-blade propeller with tapered-chord blades."""

import math
import json
import cadquery as cq
from pathlib import Path

try:
    from cadquery_framework.assembly.anchors import Anchor
except ImportError:
    Anchor = None

_D = json.loads((Path(__file__).resolve().parents[2] / "dimensions.json").read_text())

PROP_DIAMETER    = _D["propeller"]["diameter"]
PROP_HUB_D       = _D["propeller"]["hub_diameter"]
PROP_HUB_H       = _D["propeller"]["hub_height"]
PROP_BLADE_T     = _D["propeller"]["blade_thickness"]
PROP_TIP_CHORD   = _D["propeller"]["blade_tip_chord"]
PROP_ROOT_CHORD  = _D["propeller"]["blade_root_chord"]
PROP_MAX_CHORD   = _D["propeller"]["blade_max_chord"]
PROP_MAX_STATION = _D["propeller"]["blade_max_chord_station"]

CATALOG = {
    "propeller": {
        "material": "Glass-filled nylon",
        "dims": "\u00d8254mm (10 inch), 4.5 inch pitch",
        "mass_g": 14, "qty": 4,
        "supplier": "GemFan 1045",
        "notes": "2-blade, CW/CCW pairs. ~800g thrust at full throttle",
        "interface": "Press-fit/collet on 3.17mm motor shaft",
    },
}


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

    # Build the blade outline: leading edge root->tip, then trailing edge tip->root
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


def _make_anchors():
    """Build anchor dict (shared across all detail levels)."""
    anchors = {}
    if Anchor is not None:
        anchors["hub_base"] = Anchor(point=(0, 0, 0), normal=(0, 0, -1), label="Hub base sits on motor shaft")
    return anchors


def _make_envelope():
    """Simple bounding disc for the propeller."""
    prop = cq.Workplane("XY").circle(PROP_DIAMETER / 2).extrude(PROP_BLADE_T)
    return prop


def _make_assembly():
    """Assembly-level propeller (original geometry)."""
    hub = cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)
    blade1 = _make_tapered_blade(flip=False)
    blade2 = _make_tapered_blade(flip=True)
    prop = hub.union(blade1).union(blade2)
    return prop


def _make_detailed():
    """Detailed propeller with airfoil cross-sections, twist, and knurled hub."""
    det = _D["propeller"]["detailed"]
    blade_length = (PROP_DIAMETER - PROP_HUB_D) / 2
    hub_r = PROP_HUB_D / 2
    n_stations = 16  # more stations for smooth twist
    max_t_ratio = det["airfoil_max_thickness_ratio"]
    twist_root = det["twist_root_deg"]
    twist_tip = det["twist_tip_deg"]

    # --- Hub ---
    hub = cq.Workplane("XY").circle(hub_r).extrude(PROP_HUB_H)

    # --- Knurl pattern on hub ---
    knurl_count = det["hub_knurl_count"]
    knurl_depth = det["hub_knurl_depth"]
    for i in range(knurl_count):
        angle = math.radians(i * 360.0 / knurl_count)
        kx = hub_r * math.cos(angle)
        ky = hub_r * math.sin(angle)
        # Small radial groove
        groove = (
            cq.Workplane("XY")
            .center(kx, ky)
            .rect(knurl_depth * 2, knurl_depth * 2)
            .extrude(PROP_HUB_H)
        )
        groove = groove.rotateAboutCenter((0, 0, 1), math.degrees(angle))
        hub = hub.cut(groove)

    # --- Blades with airfoil cross-section and twist ---
    blade_count = det["blade_count"]
    for blade_idx in range(blade_count):
        blade_angle = blade_idx * 360.0 / blade_count
        sign = 1.0 if blade_idx == 0 else -1.0

        # Build blade as lofted sections with airfoil profiles
        # Use multiple elliptical cross-section solids unioned together
        prev_solid = None
        for i in range(n_stations):
            t0 = i / n_stations
            t1 = (i + 1) / n_stations
            t_mid = (t0 + t1) / 2.0

            r0 = hub_r + t0 * blade_length
            r1 = hub_r + t1 * blade_length
            r_mid = (r0 + r1) / 2.0

            chord = _blade_chord_at(t_mid)
            # Airfoil thickness: elliptical distribution, thicker at root
            root_scale = 1.0 + 0.5 * (1.0 - t_mid)  # thicker near root
            thickness = chord * max_t_ratio * root_scale * 2  # full thickness
            thickness = max(thickness, PROP_BLADE_T * 0.5)

            # Twist angle at this station (linear interpolation)
            twist_deg = twist_root + t_mid * (twist_tip - twist_root)

            # Chord distribution: wider at ~35% station
            half_chord = chord / 2.0
            section_span = r1 - r0

            # Build elliptical cross-section at this span segment
            # The cross-section is in the radial plane
            section = (
                cq.Workplane("XY")
                .center(sign * r_mid, 0)
                .ellipse(section_span / 2, half_chord)
                .extrude(thickness)
            )
            # Translate so the airfoil is centered on blade mid-plane
            section = section.translate((0, 0, -thickness / 2 + PROP_BLADE_T / 2))

            # Apply twist rotation around the radial axis
            section = section.rotateAboutCenter(
                (sign * 1, 0, 0), twist_deg * (1.0 if blade_idx == 0 else -1.0)
            )

            if prev_solid is None:
                prev_solid = section
            else:
                prev_solid = prev_solid.union(section)

        hub = hub.union(prev_solid)

    return hub


def make_prop_hub():
    """GemFan 1045 propeller hub only."""
    return cq.Workplane("XY").circle(PROP_HUB_D / 2).extrude(PROP_HUB_H)


def make_propeller(detail="assembly"):
    """GemFan 1045 — 2-blade prop with tapered-chord blades.

    Parameters
    ----------
    detail : str
        Level of geometric detail: ``"envelope"``, ``"assembly"`` (default),
        or ``"detailed"``.
    """
    if detail == "envelope":
        prop = _make_envelope()
    elif detail == "detailed":
        prop = _make_detailed()
    else:
        prop = _make_assembly()

    return prop, _make_anchors()
