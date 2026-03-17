"""JLCPCB manufacturing constraints — single source of truth for all PCB files.

Process: JLCPCB standard 4-layer FR4 1.6mm, ENIG finish.
Stackup: JLC04161H-7628 (symmetric, 1oz outer / half-oz inner).

All values here are imported by:
  - cadquery_framework/kicad/primitives.py  (kicad_pcb_wrapper, text_sexpr, header_pad_row)
  - drone_design components that generate .kicad_pcb files
  - gerber_export.py  (writes the .kicad_dru alongside every .kicad_pcb)

To change manufacturer or process, update ONLY this file.
"""

# =============================================================================
# JLCPCB PROCESS FLOORS  (absolute minimums — violation triggers surcharge / reject)
# =============================================================================
JLCPCB_MIN_TRACE_MM       = 0.089   # 3.5 mil — absolute process floor
JLCPCB_MIN_CLEARANCE_MM   = 0.089   # 3.5 mil — same as trace
JLCPCB_MIN_DRILL_MM       = 0.200   # absolute minimum drill (extra charge below 0.3mm)
JLCPCB_PREFERRED_VIA_DRILL_MM = 0.300  # no surcharge at this size
JLCPCB_MIN_ANNULAR_MM     = 0.150   # per side (via pad = drill + 2×0.15mm)
JLCPCB_COPPER_TO_EDGE_MM  = 0.200   # minimum copper setback from board edge
JLCPCB_HOLE_TO_EDGE_MM    = 0.300   # minimum drill-edge to board-edge
JLCPCB_HOLE_TO_HOLE_MM    = 0.254   # edge-to-edge between any two holes (IPC-2221B Class B)
JLCPCB_SILK_LINE_MM       = 0.153   # 6 mil minimum silkscreen line width
JLCPCB_SILK_TEXT_HEIGHT_MM = 1.000  # minimum legible silkscreen text height
JLCPCB_SILK_TO_PAD_MM     = 0.150   # silkscreen ink must not overlap pad opening

# =============================================================================
# DESIGN RULE MARGINS  (what to actually use — adds safety margin over process floors)
# =============================================================================
DRM_MIN_CLEARANCE_MM      = 0.100   # IPC-2221B Class B external, 0–15V
DRM_MIN_TRACE_MM          = 0.150   # 50% margin over IPC min; default net class
DRM_POWER_TRACE_MM        = 0.500   # +5V / +3V3 / +1V8 / GND rails
DRM_VBATT_TRACE_MM        = 1.000   # VBATT rail (5A continuous / 10A peak)
DRM_HIGH_SPEED_TRACE_MM   = 0.150   # DShot, IMU SPI, Camera DVP data
DRM_IMPEDANCE_TRACE_MM    = 0.450   # 50Ω microstrip on outer layers (see stackup below)
DRM_I2C_TRACE_MM          = 0.150   # I2C bus (400kHz — completely lumped)
DRM_PWM_TRACE_MM          = 0.200   # pump / buzzer PWM

DRM_POWER_CLEARANCE_MM    = 0.200   # between power rails
DRM_VBATT_CLEARANCE_MM    = 0.500   # VBATT isolation from logic (16.8V max)
DRM_HS_TO_HS_CLEARANCE_MM = 0.200   # high-speed to high-speed
DRM_HS_TO_PWR_CLEARANCE_MM = 0.300  # high-speed to power
DRM_IMPEDANCE_CLEARANCE_MM = 0.500  # controlled-impedance trace spacing
DRM_IMU_TO_DSHOT_MM       = 2.000   # analog-quiet zone: IMU/baro to DShot

DRM_POWER_VIA_DRILL_MM    = 0.400   # power net vias (GND, +5V, +3V3, +1V8)
DRM_VBATT_VIA_DRILL_MM    = 0.500   # VBATT high-current vias

DRM_THERMAL_GAP_MM        = 0.250   # thermal relief spoke-to-pad gap
DRM_THERMAL_SPOKE_MM      = 0.250   # default thermal spoke width
DRM_POWER_SPOKE_MM        = 0.500   # power-pad thermal spoke width

DRM_SOLDER_MASK_SLIVER_MM = 0.100   # minimum solder mask sliver between adjacent pads
DRM_COURTYARD_CLEARANCE_MM = 0.100  # IPC-7351B between adjacent component courtyards
DRM_STANDOFF_CLEARANCE_MM = 0.250   # copper clearance around M2.5 mounting holes

DRM_BARO_VENT_HOLE_MM     = 1.000   # BMP390 pressure vent hole diameter (NPTH)
DRM_BARO_VENT_CLEARANCE_MM = 2.000  # copper-free radius around vent hole
DRM_SILK_TO_COPPER_MM     = max(JLCPCB_SILK_TO_PAD_MM, DRM_MIN_CLEARANCE_MM)  # silkscreen must clear all copper and holes

# =============================================================================
# SOLDER MASK  (ENIG finish, JLCPCB default)
# =============================================================================
SOLDER_MASK_EXPANSION_MM  = 0.050   # pad-to-mask clearance per side
SOLDER_MASK_MIN_WIDTH_MM  = 0.050   # minimum solder mask width (sliver guard)
SOLDER_MASK_THICKNESS_MM  = 0.010   # nominal solder mask layer thickness

# =============================================================================
# PCB STACKUP — JLC04161H-7628  (1.6mm total, symmetric)
# =============================================================================
# Outer copper (F.Cu / B.Cu) — 1 oz
CU_OUTER_MM               = 0.035

# Inner copper (In1.Cu / In2.Cu) — half oz
CU_INNER_MM               = 0.0152

# Prepreg layers (F.Cu→In1.Cu and In2.Cu→B.Cu)
PREPREG_THICKNESS_MM      = 0.2104
PREPREG_MATERIAL          = "7628"
PREPREG_DK                = 4.4
PREPREG_LOSS_TANGENT      = 0.02

# Core layer (In1.Cu→In2.Cu)
CORE_THICKNESS_MM         = 1.065
CORE_MATERIAL             = "7628"
CORE_DK                   = 4.6
CORE_LOSS_TANGENT         = 0.02

# 2-layer fallback (structural boards: arms, plates, landing gear)
# Core = PCB thickness minus both copper layers
FR4_2L_DK                 = 4.5
FR4_2L_LOSS_TANGENT       = 0.02

# =============================================================================
# FOOTPRINT DEFAULTS
# =============================================================================
# GPIO / pin header through-hole pads (2.54mm pitch connectors)
TH_GPIO_DRILL_MM          = 1.000
TH_GPIO_PAD_MM            = 1.700   # annular = (1.7 - 1.0) / 2 = 0.35mm per side

# M2.5 standoff mounting holes
TH_M25_DRILL_MM           = 2.700   # M2.5 + 0.2mm clearance
TH_M25_PAD_MM             = 3.900   # annular = (3.9 - 2.7) / 2 = 0.6mm per side

# Generic through-hole pad = drill + this annular on each side
TH_DEFAULT_ANNULAR_MM     = 0.250   # generous default; specific rules override

# =============================================================================
# SILKSCREEN TEXT STANDARDS
# =============================================================================
SILK_LARGE_SIZE_MM        = 1.500   # board title / primary labels
SILK_LARGE_THICK_MM       = 0.150

SILK_REF_SIZE_MM          = 1.200   # component reference designators (R1, C3 …)
SILK_REF_THICK_MM         = 0.150

SILK_SMALL_SIZE_MM        = 1.000   # board specs / secondary annotations (JLCPCB min)
SILK_SMALL_THICK_MM       = 0.153   # JLCPCB minimum silkscreen line width

SILK_MICRO_SIZE_MM        = 1.000   # compact labels — at JLCPCB minimum (no smaller on F.SilkS)
SILK_MICRO_THICK_MM       = 0.153   # JLCPCB minimum silkscreen line width

SILK_FAB_SIZE_MM          = 0.700   # fab layer component value text
SILK_FAB_THICK_MM         = 0.090

# =============================================================================
# DRAWING LAYER WIDTHS
# =============================================================================
EDGE_CUTS_WIDTH_MM        = 0.050   # board outline (Edge.Cuts)
COURTYARD_WIDTH_MM        = 0.050   # component courtyard lines
FAB_LAYER_WIDTH_MM        = 0.100   # fab layer lines

# =============================================================================
# IMPEDANCE REFERENCE  (informational — used in comments and DRU)
# =============================================================================
IMPEDANCE_TARGET_OHM      = 50
IMPEDANCE_TOLERANCE_PCT   = 10
# 50Ω microstrip width calculated for JLC04161H-7628 outer layers:
#   h = 0.2104mm (prepreg), t = 0.035mm (1oz Cu), Dk = 4.4
#   W ≈ 0.41mm → use 0.45mm nominal (within ±10% tolerance)
IMPEDANCE_TRACE_WIDTH_MM  = DRM_IMPEDANCE_TRACE_MM  # 0.45mm


def dru_content():
    """Return the complete .kicad_dru file content derived from this module's constants.

    This is the authoritative source for the design rules file. Any KiCad PCB that
    needs DRC enforcement should have this file written alongside it.
    """
    return f"""\
# =============================================================================
# KiCad Design Rules — generated from cadquery_framework/kicad/jlcpcb_constraints.py
# Manufacturer: JLCPCB  |  Process: 4-layer FR4 1.6mm  |  Finish: ENIG
# Stackup: JLC04161H-7628
# =============================================================================
#
# Standards: IPC-2221B Class B, IPC-2141A, IPC-7351B
# To change any value, edit jlcpcb_constraints.py — do NOT edit this file directly.
#
# Stackup (JLC04161H-7628, symmetric, 1.6mm total):
#   F.Cu  {CU_OUTER_MM}mm (1oz)  →  prepreg {PREPREG_THICKNESS_MM}mm {PREPREG_MATERIAL} Dk={PREPREG_DK}
#   In1.Cu {CU_INNER_MM}mm (½oz) →  core    {CORE_THICKNESS_MM}mm  {CORE_MATERIAL} Dk={CORE_DK}
#   In2.Cu {CU_INNER_MM}mm (½oz) →  prepreg {PREPREG_THICKNESS_MM}mm {PREPREG_MATERIAL} Dk={PREPREG_DK}
#   B.Cu  {CU_OUTER_MM}mm (1oz)
#   50Ω microstrip on outer layers: {IMPEDANCE_TRACE_WIDTH_MM}mm trace (±{IMPEDANCE_TOLERANCE_PCT}%)
#
(version 1)

# ─── SECTION 1: Global baseline clearances ───────────────────────────────────

(rule "Global minimum clearance"
   (constraint clearance (min {DRM_MIN_CLEARANCE_MM}mm))
)
(rule "Global physical clearance"
   (constraint physical_clearance (min {DRM_MIN_CLEARANCE_MM}mm))
)
(rule "Copper to board edge"
   (constraint edge_clearance (min {JLCPCB_COPPER_TO_EDGE_MM}mm))
)
(rule "PTH hole to board edge"
   (constraint physical_hole_clearance (min {JLCPCB_HOLE_TO_EDGE_MM}mm))
)

# ─── SECTION 2: Holes and vias ───────────────────────────────────────────────

(rule "Hole to hole"
   (constraint hole_to_hole (min {JLCPCB_HOLE_TO_HOLE_MM}mm))
)
(rule "Minimum via drill (signal)"
   (constraint hole_size (min {JLCPCB_PREFERRED_VIA_DRILL_MM}mm))
   (condition "A.Type == 'Via'")
)
(rule "Minimum via annular ring"
   (constraint annular_width (min {JLCPCB_MIN_ANNULAR_MM}mm))
   (condition "A.Type == 'Via'")
)
(rule "Minimum PTH annular ring"
   (constraint annular_width (min 0.05mm))
   (condition "A.Type == 'Pad' && A.Pad.Type == 'Through hole'")
)
(rule "No buried vias"
   (constraint disallow buried_via)
)
(rule "No micro vias"
   (constraint disallow micro_via)
)
(rule "No blind vias"
   (constraint disallow blind_via)
)
(rule "Power via minimum drill"
   (constraint hole_size (min {DRM_POWER_VIA_DRILL_MM}mm))
   (condition "A.Type == 'Via' && (A.Net.Name == 'GND' || A.Net.Name == '+5V' || A.Net.Name == '+3V3' || A.Net.Name == '+1V8')")
)
(rule "VBATT via minimum drill"
   (constraint hole_size (min {DRM_VBATT_VIA_DRILL_MM}mm))
   (condition "A.Type == 'Via' && (A.Net.Name =~ 'VBATT.*')")
)

# ─── SECTION 3: Trace widths by net class ────────────────────────────────────

(rule "Default minimum track width"
   (constraint track_width (min {DRM_MIN_TRACE_MM}mm))
)
(rule "Power net track width"
   (condition "A.NetClass == 'POWER' || A.Net.Name == '+5V' || A.Net.Name == '+3V3' || A.Net.Name == '+1V8' || A.Net.Name == 'GND'")
   (constraint track_width (min {DRM_POWER_TRACE_MM}mm))
)
(rule "VBATT net track width"
   (condition "A.Net.Name =~ 'VBATT.*'")
   (constraint track_width (min {DRM_VBATT_TRACE_MM}mm))
)
(rule "High-speed signal minimum width"
   (condition "A.NetClass == 'HIGH_SPEED' || A.Net.Name =~ 'DSHOT_.*' || A.Net.Name =~ 'IMU_SPI_.*' || A.Net.Name =~ 'CAM_D[0-9].*'")
   (constraint track_width (min {DRM_HIGH_SPEED_TRACE_MM}mm) (opt 0.2mm))
)
(rule "50-ohm controlled impedance trace width"
   (condition "A.NetClass == 'IMPEDANCE' || A.Net.Name == 'CAM_PCLK' || A.Net.Name == 'IMU_SPI_SCLK'")
   (constraint track_width (min 0.4mm) (opt {DRM_IMPEDANCE_TRACE_MM}mm) (max 0.5mm))
)
(rule "I2C bus track width"
   (condition "A.Net.Name =~ 'TOF_I2C_.*' || A.Net.Name =~ 'CAM_SI.*' || A.Net.Name =~ '.*_SCL' || A.Net.Name =~ '.*_SDA'")
   (constraint track_width (min {DRM_I2C_TRACE_MM}mm))
)
(rule "PWM signal track width"
   (condition "A.Net.Name =~ '.*_PWM' || A.NetClass == 'PWM'")
   (constraint track_width (min {DRM_PWM_TRACE_MM}mm))
)

# ─── SECTION 4: Clearances by net class ──────────────────────────────────────

(rule "Power to power clearance"
   (condition "(A.NetClass == 'POWER') && (B.NetClass == 'POWER')")
   (constraint clearance (min {DRM_POWER_CLEARANCE_MM}mm))
)
(rule "VBATT to signal clearance"
   (condition "A.Net.Name =~ 'VBATT.*' && B.NetClass != 'VBATT'")
   (constraint clearance (min {DRM_VBATT_CLEARANCE_MM}mm))
)
(rule "High-speed to high-speed clearance"
   (condition "(A.NetClass == 'HIGH_SPEED') && (B.NetClass == 'HIGH_SPEED')")
   (constraint clearance (min {DRM_HS_TO_HS_CLEARANCE_MM}mm))
)
(rule "High-speed to power clearance"
   (condition "(A.NetClass == 'HIGH_SPEED') && (B.NetClass == 'POWER')")
   (constraint clearance (min {DRM_HS_TO_PWR_CLEARANCE_MM}mm))
)
(rule "Controlled impedance trace clearance"
   (condition "A.NetClass == 'IMPEDANCE' || B.NetClass == 'IMPEDANCE'")
   (constraint clearance (min {DRM_IMPEDANCE_CLEARANCE_MM}mm))
)
(rule "IMU signals to DShot clearance"
   (condition "(A.Net.Name =~ 'IMU_.*' || A.Net.Name =~ 'BARO_.*') && (B.Net.Name =~ 'DSHOT_.*')")
   (constraint clearance (min {DRM_IMU_TO_DSHOT_MM}mm))
)

# ─── SECTION 5: Silkscreen ───────────────────────────────────────────────────

(rule "Silkscreen minimum line width"
   (constraint text_thickness (min {JLCPCB_SILK_LINE_MM}mm))
   (condition "A.Layer == 'F.SilkS' || A.Layer == 'B.SilkS'")
)
(rule "Silkscreen text minimum height"
   (constraint text_height (min {JLCPCB_SILK_TEXT_HEIGHT_MM}mm))
   (condition "A.Layer == 'F.SilkS' || A.Layer == 'B.SilkS'")
)
(rule "Silkscreen to copper, pads, vias, and holes"
   (constraint silk_clearance (min {DRM_SILK_TO_COPPER_MM}mm))
   (condition "A.Layer == 'F.SilkS' || A.Layer == 'B.SilkS'")
   (severity error)
)
(rule "Silkscreen to silkscreen clearance"
   (constraint silk_clearance (min 0.1mm))
)

# ─── SECTION 6: Courtyard ────────────────────────────────────────────────────

(rule "Courtyard clearance"
   (constraint courtyard_clearance (min {DRM_COURTYARD_CLEARANCE_MM}mm))
)

# ─── SECTION 7: Solder mask ──────────────────────────────────────────────────

(rule "Solder mask sliver minimum"
   (constraint solder_mask_sliver (min {DRM_SOLDER_MASK_SLIVER_MM}mm))
)
(rule "Solder mask expansion check"
   (constraint solder_mask_expansion (min 0.025mm) (max 0.075mm))
)

# ─── SECTION 8: Thermal relief ───────────────────────────────────────────────

(rule "Default thermal relief gap"
   (constraint thermal_relief_gap (min {DRM_THERMAL_GAP_MM}mm))
)
(rule "Default thermal spoke width"
   (constraint thermal_spoke_width (min {DRM_THERMAL_SPOKE_MM}mm))
)
(rule "Power zone thermal spoke width"
   (condition "A.NetClass == 'POWER' || A.Net.Name == 'GND' || A.Net.Name == '+5V' || A.Net.Name == '+3V3'")
   (constraint thermal_spoke_width (min {DRM_POWER_SPOKE_MM}mm))
)
(rule "Power pad minimum spokes"
   (condition "A.NetClass == 'POWER' || A.Net.Name == 'GND'")
   (constraint min_resolved_spokes 4)
)

# ─── SECTION 9: Mechanical / mounting holes ──────────────────────────────────

(rule "M2.5 standoff hole copper clearance"
   (condition "A.Drill.Diameter >= 2.6mm && A.Drill.Diameter <= 2.8mm")
   (constraint clearance (min {DRM_STANDOFF_CLEARANCE_MM}mm))
)
(rule "Barometer vent hole to copper clearance"
   (condition "A.Net.Name == '' && A.Drill.Diameter >= 0.9mm && A.Drill.Diameter <= 1.1mm")
   (constraint clearance (min {DRM_BARO_VENT_CLEARANCE_MM}mm))
)

# ─── SECTION 10: JLCPCB absolute process floors (severity error) ─────────────

(rule "JLCPCB absolute minimum trace width"
   (constraint track_width (min {JLCPCB_MIN_TRACE_MM}mm))
   (severity error)
)
(rule "JLCPCB absolute minimum clearance"
   (constraint clearance (min {JLCPCB_MIN_CLEARANCE_MM}mm))
   (severity error)
)
(rule "JLCPCB minimum drill"
   (constraint hole_size (min {JLCPCB_MIN_DRILL_MM}mm))
   (severity error)
)
"""
