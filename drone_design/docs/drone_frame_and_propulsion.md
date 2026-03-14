# Drone Frame, Propulsion & Power -- PCB Mechanical Design

All structural components are FR4 PCBs manufactured at JLCPCB. No 3D-printed parts. Full PCBA for electronics boards; bare PCBs for structural pieces.

---

## 1. Design Constraints

| Constraint | Value | Notes |
|------------|-------|-------|
| Frame class | 450mm (motor-to-motor diagonal) | X-configuration |
| Target AUW | 1200-1500g | Including 300ml water payload |
| Thrust-to-weight ratio | ≥2:1 | Minimum for stable hover + maneuvering with payload |
| Required total thrust | ≥3000g | 4 motors × ≥750g each |
| Manufacturing | JLCPCB | Bare PCB for structure, PCBA for electronics |
| No 3D printing | Mandatory | All mechanical parts are PCB cutouts |
| Propeller size | 10x4.5" (254mm diameter) | Minimum motor spacing: 260mm |
| Motor mount pattern | M3 × 16-19mm | Standard for 22xx class motors |

---

## 2. Weight Budget

| Component | Weight | Notes |
|-----------|--------|-------|
| **Frame (skeleton optimized)** | | |
| Bottom plate (120×120mm, 2.0mm FR4, 2oz Cu, skeleton) | 30g | PDB pours + lightening cutouts |
| Top plate (120×120mm, 1.6mm FR4, skeleton) | 22g | Lattice ribs between features |
| Arms (4× 25×220mm, 1.6mm FR4, 2oz Cu, skeleton) | 34g | ~8.5g each, I-beam cutouts |
| Landing gear (4× L-shape, 2.0mm FR4, skeleton) | 22g | ~5.5g each, tapered + lightening holes |
| ToF sensor boards (6× 12×15mm, 1.0mm FR4) | 6g | 1g each |
| Pump bracket (25×40mm, 1.6mm FR4) | 2g | |
| Solder (all castellated + RA header joints) | 5g | |
| Remaining hardware (motor bolts, DE10 standoffs) | 12g | |
| **Frame subtotal** | **~133g** | |
| **Electronics** | | |
| DE10-Nano | 150g | With heatsink |
| Daughter board (PCBA) | 42g | All sensors mounted |
| BMS board (PCBA) | 8g | |
| Wiring + cables | 15g | Reduced -- ESC/ToF signals route through PCB traces |
| **Electronics subtotal** | **~215g** | |
| **Propulsion** | | |
| Motors (4× SunnySky X2212 980KV) | 228g | 57g each |
| ESCs (4× FVT LittleBee 30A BLHeli_32) | 32g | ~8g each |
| Propellers (4× GemFan 1045) | 64g | ~16g each with adapter |
| **Propulsion subtotal** | **~324g** | |
| **Power** | | |
| Battery (Tattu 4S 2200mAh 45C) | 180g | |
| **Water Delivery** | | |
| Peristaltic pump (Kamoer NKP-DC-S06B) | 75g | 12V, 37 ml/min |
| Reservoir (TPU soft flask, 300ml) | 30g | Collapsible |
| Tubing + drip nozzle + fittings | 15g | 1.5m silicone, 3mm ID |
| **Water delivery subtotal (dry)** | **~120g** | |
| **Payload** | | |
| Water (300ml) | 300g | |
| **Payload subtotal** | **~300g** | |
| | | |
| **Total AUW (loaded)** | **~1272g** | |
| **Total AUW (dry, no water)** | **~972g** | |
| **Required thrust (2:1)** | **2544g** | |
| **Available thrust (4× ~900g)** | **~3600g** | 2.8:1 ratio -- good margin |

---

## 3. PCB Frame Design

### Design Philosophy -- Soldered PCB Joinery

Every structural joint in this frame uses **soldered PCB-to-PCB connections** instead of bolts and standoffs. Two primary techniques:

1. **Castellated holes**: Plated half-vias along PCB edges. When one board's castellated edge sits against another board's pads, solder wicks into the barrel, creating a strong mechanical + electrical joint. Used for all structural joints (arms, landing gear).

2. **Right-angle pin headers**: Standard 2.54mm right-angle headers soldered between two perpendicular PCBs. Used where the joint must also carry electrical signals (ToF sensors, ESC signal routing). The header provides both the 90° mechanical structure AND the electrical connection -- dual-duty, no separate brackets or cables needed.

This eliminates ~80% of fastener hardware (no arm clamp bolts, no landing gear bolts, no ToF brackets, no ESC signal cables). Solder joints on 2oz copper pads with proper fillet formation withstand >20N per joint -- more than adequate for a 1.3kg drone. Vibration fatigue is mitigated by using Sn63Pb37 solder (best vibration resistance) and oversized pads.

### Material Properties -- FR4

| Property | Value | Notes |
|----------|-------|-------|
| Flexural strength | ~400 MPa | Stronger than aluminum (280 MPa) |
| Density | 1.85 g/cm³ | Heavier than carbon fiber (1.6 g/cm³) |
| Elastic modulus | ~20 GPa | Stiffer than nylon, less than aluminum |
| Failure mode | Brittle fracture | No plastic deformation -- cracks on impact |
| Standard thickness | 1.6mm or 2.0mm | 2.0mm for structural plates, 1.6mm elsewhere |
| JLCPCB cost | ~$2-5 per board (5 pcs) | Bare PCB, no assembly |

**Key advantage**: JLCPCB supports castellated holes (min 0.6mm diameter, 1.0mm pitch), routed board outlines (±0.1mm), and plated slots -- all at standard pricing.

### Skeleton Weight Optimization

Every PCB piece uses aggressive material removal to minimize weight. JLCPCB's CNC router cuts any arbitrary 2D outline at no extra cost -- we exploit this to create skeleton/truss patterns in all structural boards:

**Principle**: FR4 is strong but heavy (1.85 g/cm³). A solid 120×120mm plate weighs ~42g at 2.0mm. By removing material everywhere except load paths, mounting zones, and copper routing channels, we can reduce weight by 30-40%.

**Techniques applied to every board**:

1. **Plates (top/bottom)**: Large interior cutouts between arm slots. Only retain: arm slot perimeters (10mm border), mounting hole zones (5mm annular), copper pour regions (power traces), DE10-Nano mount area, edge castellation zones. The plate becomes a lattice of structural ribs connecting these features.

2. **Arms**: Remove material from the arm body center, leaving a channel-section profile. Keep 5mm edges on both long sides (structural flanges) + 3mm center strip (copper trace routing). The arm becomes an I-beam cross-section:
    ```
    ┌──┐     ┌──┐
    │  │     │  │   5mm edge flanges (structural)
    │  ├─────┤  │   3mm center strip (power + signal traces)
    │  │     │  │   Interior cutouts on each side
    └──┘     └──┘
    ```
    Weight savings: ~40% (13g → ~8g per arm, saving ~20g total).

3. **Landing gear legs**: Taper from 20mm at the plate joint to 12mm at the foot. Add oval lightening holes (6mm × 15mm) in the vertical section. Weight savings: ~25%.

4. **Pump bracket**: Small enough that skeleton optimization is unnecessary (2g).

**Estimated weight savings from skeleton optimization**:

| Part | Solid weight | Skeleton weight | Savings |
|------|-------------|-----------------|---------|
| Bottom plate | 45g | ~30g | 15g |
| Top plate | 34g | ~22g | 12g |
| Arms (4×) | 56g | ~34g | 22g |
| Landing gear (4×) | 28g | ~22g | 6g |
| **Total frame savings** | | | **~55g** |

This brings the frame subtotal from ~188g to ~133g, and total AUW from ~1327g to ~1272g -- improving the thrust-to-weight ratio to ~2.8:1.

**Design rule**: Maintain minimum 3mm web width between any cutout and a board edge, hole, or castellated pad. This ensures structural integrity at solder joints and prevents cracking under vibration.

### 3a. Bottom Plate (Main Structural PCB + PDB)

The primary load-bearing element. Arms solder into slots. Landing gear solders to edge castellations. Also serves as the power distribution board with 2oz copper pours.

**Dimensions**: 120mm × 120mm, **2.0mm FR4, 2oz copper outer layers**

```
         120mm
    ┌─────────────────┐
    │  ╱ARM1╲   ╱ARM2╲│    Arm slots: 1.7mm wide (arm + 0.1mm clearance)
    │ ╱ SLOT  ╲╱ SLOT  ╲             × 40mm long, at 45° diagonals
    │╱         ╲       ╱│
    │     ┌─────╳──┐   │   120mm
    │╲    │  DE10  │  ╱│    Castellated pads along slot edges
    │ ╲   │  Nano  │ ╱ │    for soldering arm tabs
    │  ╲ARM3╱  ╲ARM4╱  │
    └─────────────────┘
     ●                ●     ← Landing gear castellated edge pads (4 edges)
```

**Features**:

| Feature | Detail |
|---------|--------|
| 4× arm slots | 1.7mm × 40mm, at 45° diagonals. **Castellated pads** on both sides of each slot (6 pads per side, 12 per slot) for soldering arm tab |
| 4× DE10-Nano M2.5 holes | Matching DE10-Nano mounting pattern (centered) |
| 2× battery strap slots | 3mm × 25mm, parallel, 40mm apart (for 20mm velcro strap) |
| 2× reservoir strap slots | 3mm × 25mm, 30mm offset from battery slots |
| 4× edge castellated zones | 10 castellated holes per edge (20mm zone) for landing gear solder joints |
| 4× ESC power pad pairs | V+ and GND solder pads at each arm slot exit (2oz copper pour, 5mm × 3mm each) |
| 1× XT60 footprint | Edge-mounted XT60 connector pads (battery input) |
| 1× 5mm clear hole at center | Downward-facing VL53L1X (soldered on underside via right-angle 4-pin header) |
| 2× pump mount castellations | 4 castellated holes at one plate edge for pump bracket solder joint |
| Board outline | Rounded corners (2mm radius), weight-relief cutouts between arm slots |

**Arm slot detail (cross-section)**:

```
    Bottom plate (2.0mm)
    ┌──────┬───────┬──────┐
    │ PADS │ SLOT  │ PADS │   Slot is 1.7mm wide (arm slides through vertically)
    │ ●●●  │ 1.7mm │ ●●●  │   Castellated pads on each side, 1.0mm pitch
    │ ●●●  │       │ ●●●  │   Solder arm edge castellations to plate pads
    └──────┴───────┴──────┘
```

**Weight-relief cutouts**: Remove FR4 material between arm slots where there are no mounting holes, traces, or power pours. Reduces weight by ~15-20%.

### 3b. Top Plate

Mirrors the bottom plate slot pattern. Arms pass through both plates. The two plates plus solder joints form a rigid sandwich.

**Dimensions**: 120mm × 120mm, **1.6mm FR4, 1oz copper**

**Features**:
- 4× arm slots with castellated pads (matching bottom plate pattern exactly)
- Central cutout: ~70mm × 110mm rectangular hole for DE10-Nano clearance (USB, barrel jack, Ethernet, HDMI)
- 4× right-angle 4-pin header footprints at plate edges (front/back/left/right) for horizontal ToF sensor boards -- these headers simultaneously provide the 90° mechanical mount AND carry I2C signals (VCC, GND, SDA, SCL)
- 1× right-angle 4-pin header footprint at center for upward-facing ToF sensor board
- The daughter board sits above the top plate, connected to DE10-Nano via GPIO headers through the central cutout

**Assembly note**: DE10-Nano mounts to the bottom plate via M2.5 standoffs (15mm). Its top surface (with GPIO headers) protrudes through the top plate's central cutout.

### 3c. Arms (4 identical)

Straight PCB arms with castellated edges on the inner tab for soldering into the plate slots. Copper traces along the arm carry ESC signals and power from the center plates to the motor end.

**Dimensions**: 25mm × 220mm, **1.6mm FR4, 2oz copper**

```
     Inner (center)                                      Outer (motor)
    ┌─────┬──────────────────────────────────────────────┬──────────┐
    │CAST.│          ARM BODY                            │  MOTOR   │
    │EDGE │  ═══════════════════════════════              │  MOUNT   │
    │●●●●●│  ESC signal trace (top layer)  ═══► [pad]   │ ○   ○    │ 25mm
    │●●●●●│  V+ power trace (bottom, 2oz)  ═══► [pad]   │          │
    │●●●●●│  GND power trace (bottom, 2oz) ═══► [pad]   │ ○   ○    │
    └─────┴──────────────────────────────────────────────┴──────────┘
      40mm                  140mm                           40mm
    ◄─────►◄────────────────────────────────────────────►◄─────────►
                         220mm total
```

**Inner tab (40mm) -- castellated edges**:
- Both long edges of the 40mm tab have **castellated holes** (6 per side, 1.0mm pitch, 0.6mm diameter)
- Tab thickness (1.6mm) slides into the 1.7mm plate slots
- Once inserted, solder wicks from plate pads into arm castellations -- permanent structural bond
- **Electrical routing through castellations**: 3 of the 6 castellations per side carry signals:
  - 1× DShot600 motor signal (from daughter board → through plate → along arm → to ESC)
  - 1× V+ battery power (from PDB copper pour → through plate → along arm → to ESC)
  - 1× GND return (from PDB copper pour → through plate → along arm → to ESC)
  - 3× structural only (no trace, solder-for-strength)

**This eliminates all ESC signal wiring and power wiring**: The arm PCB itself IS the wiring. DShot signal traces route from the plate solder joint along the arm's top copper layer to an ESC signal pad near the motor end. V+ and GND traces route along the bottom copper layer (2oz, 3mm wide = handles >20A).

**Body (140mm)**:
- Top layer: DShot600 signal trace (0.2mm, minimal current)
- Bottom layer: V+ power trace (3mm wide, 2oz copper) and GND power trace (3mm wide, 2oz copper)
- ESC solder pads at ~160mm from inner edge: 3 pads (signal, V+, GND) for direct ESC wire soldering -- no JST connectors, no zip ties, no separate wiring
- Silkscreen: arm number (1-4), motor rotation direction arrow (CW/CCW)

**Motor mount (40mm)**:
- 4× M3 through-holes on 16mm × 19mm rectangular pattern (standard 22xx motor mount)
- Additional 4× M3 holes on 16mm × 16mm pattern (alternative motor compatibility)
- Slotted holes (3.5mm × 5mm) for ±1.5mm motor position adjustment

**ESC mounting**: ESC board solders directly to the arm's ESC pads (signal + V+ + GND). No zip ties, no connectors. Motor phase wires solder to ESC output pads. The entire propulsion wiring for each arm is: arm PCB traces + direct solder joints.

**Arm strength analysis** (simplified):
- 1.6mm × 25mm FR4 cross-section
- Moment of inertia I = (25 × 1.6³) / 12 = 8.53 mm⁴
- With 200g motor+prop at 180mm from clamp: M = 0.2 × 9.81 × 0.18 = 0.353 Nm
- Max bending stress = M × c / I = 0.353 × 0.8 / 8.53e-12 = ~33 MPa
- Safety factor vs FR4 flexural strength (400 MPa): **~12:1** -- more than adequate
- Crash loads (5-10g) still within ~3:1 safety factor
- Solder joint at plate: 12 castellations × ~20N each = 240N capacity >> 2N static load

### 3d. Landing Gear (4 identical)

Flat PCB legs that solder perpendicularly to the bottom plate edge via castellated holes. No bolts.

**Dimensions**: 20mm × 80mm (vertical portion) + 20mm × 40mm (horizontal foot), **2.0mm FR4**

```
    Castellated top edge (solders to bottom plate)
    ●●●●●●●●●●
    ┌──────────┐
    │          │ 20mm wide
    │          │
    │          │ 80mm vertical
    │          │
    │          │
    │          │
    └──────────┴──────────┐
               │          │ 40mm horizontal foot
               │  (grip)  │ 20mm wide
               └──────────┘

    Silicone bumper pad adhered to foot underside
```

**Top edge**: 10 castellated holes across the 20mm width (2.0mm pitch). These mate with the corresponding castellated pads on the bottom plate edge.

**Soldering**: Hold leg perpendicular to plate edge. Iron touches both the plate edge pad and the leg's castellated half-barrel simultaneously. Solder wicks into the joint. 10 joints per leg = ~200N shear capacity -- far exceeds landing loads.

**Ground clearance**: 80mm (enough for battery + BMS + reservoir + drip nozzle hanging below bottom plate)

**Foot**: 40mm horizontal extension provides stability. 3M silicone bumper pads (self-adhesive) on each foot for vibration damping and grip. The foot also serves as a crush zone -- in a hard landing, the FR4 foot fractures before the main structure, absorbing impact energy.

**Lateral stiffness**: 2.0mm FR4 at 20mm width is reasonably stiff. For additional rigidity, a thin cross-brace PCB strip can solder between adjacent leg pairs (optional).

### 3e. ToF Sensor Boards (6 identical mini-PCBs)

Small 12mm × 15mm daughter PCBs, each carrying one VL53L1X module and a right-angle 4-pin header. The header provides both the 90° mechanical mount and the I2C electrical connection.

```
    ┌─────────────┐
    │  VL53L1X    │ 12mm × 15mm mini-PCB
    │  [sensor]   │ 1.0mm FR4
    │             │
    └──┤├──┤├──┤├─┘
       RA  RA  RA    ← Right-angle 4-pin header (2.54mm pitch)
       pins facing    Pins: VCC, GND, SDA, SCL
       toward plate
```

**Mounting**: The right-angle header's through-hole pins solder to matching pads on the top plate (for horizontal sensors) or on the bottom/top plate center (for vertical sensors). One component serves as:
- **Mechanical mount**: Header body + solder joints hold the sensor board at 90° to the plate
- **Electrical connection**: VCC, GND, SDA, SCL routed through the same header pins
- **No separate cables**: I2C signals route from the header pads through plate traces to the daughter board's I2C bus via the TCA9548A mux

**6 sensor positions**:

| Position | Mounts to | Header orientation | Purpose |
|----------|-----------|-------------------|---------|
| Down | Bottom plate underside, center | Vertical, facing ground | Altitude hold |
| Up | Top plate topside, center | Vertical, facing ceiling | Ceiling proximity |
| Front | Top plate front edge | Horizontal, facing forward | Forward obstacle avoidance |
| Back | Top plate rear edge | Horizontal, facing backward | Reverse obstacle avoidance |
| Left | Top plate left edge | Horizontal, facing left | Lateral avoidance |
| Right | Top plate right edge | Horizontal, facing right | Lateral avoidance |

**I2C routing**: All 6 ToF sensor header pads connect via top plate traces to a central I2C bus that routes through the top plate to the daughter board's TCA9548A mux (connectors J6-J11 eliminated -- signals route through PCB traces instead of cables).

**Propeller interference**: VL53L1X uses 940nm VCSEL laser with 27° FoV. Horizontal sensors mount at plate edges, perpendicular to nearest arm -- prop disc is above the sensor plane. Down/up sensors at center are 130mm+ from prop tips. Brief transient dropouts during aggressive maneuvers are filtered by the FPGA's median filter.

### 3f. Pump Bracket

A small 25mm × 40mm PCB tab that solders perpendicularly to the bottom plate edge via 4 castellated holes, hanging the pump below the frame.

```
    Bottom plate edge
    ────●●●●────
        │    │
        │    │ 40mm
        │    │
        │ ○○ │ ← M2.5 holes for pump mounting
        │    │
        └────┘
         25mm
```

The pump (Kamoer NKP-DC-S06B) bolts to this bracket with 2× M2.5 screws. Silicone vibration pads between pump body and bracket prevent motor vibration from coupling into the frame and affecting IMU readings.

### 3g. Assembly

**Exploded view (top to bottom)**:

```
                        [Propellers]
                        [Motors bolted to arm tips]
                ┌───────────────────────────┐
                │      ARM (4×)              │ ← ESCs soldered to arm pads
                └───────┬───────────────────┘   Motor signal + power via arm traces
                   [ToF UP — soldered via RA header]
                ┌───────┴───────┐
                │  Daughter Board│ ← Plugged into DE10-Nano GPIO headers
                │  (85×100mm)   │
                ├───────────────┤
                │  DE10-Nano     │ ← M2.5 standoffs to bottom plate
                │  (68.6×107mm)  │
    ┌───────────┼───────────────┼───────────┐
◄ToF├           │  TOP PLATE    │           ├ToF►   ← Horizontal ToF boards
    │           │  (120×120mm)  │           │        soldered via RA headers
    │ ARM TABS  │  Central      │ ARM TABS  │
    │(soldered) │  cutout       │(soldered) │
    ├───────────┼───────────────┼───────────┤
    │           │ BOTTOM PLATE  │           │ ← PDB + structural plate
    │           │ (120×120mm)   │           │
    └───────────┴───────┬───────┴───────────┘
                        │
                   [Reservoir — velcro-strapped between plates or below]
                   [Pump bracket — soldered to plate edge, pump bolted on]
                   [Battery — velcro-strapped below]
                   [BMS board — mounted below]
                   [ToF DOWN — soldered via RA header to bottom plate center]
                   [Drip nozzle — hangs below pump bracket]
                   [Landing gear — soldered to plate edges]
                        │
                ┌───────┴───────┐
                │  Landing Gear  │ ← 4× legs soldered to bottom plate
                │  (80mm height) │    via castellated edge joints
                └───────────────┘
                [Ground]
```

**Assembly order** (solder joints are permanent -- plan order carefully):

1. **Solder landing gear legs** to bottom plate edge castellations (4 legs × 10 solder joints each). Use a jig or right-angle fixture to hold perpendicular during soldering.
2. **Solder pump bracket** to bottom plate edge (4 castellated joints).
3. **Insert arms** into bottom plate slots. Solder arm castellated edges to plate pads (12 joints per arm × 4 arms = 48 joints).
4. **Place top plate** over arm tabs. Solder arm castellated edges to top plate pads (48 more joints). Frame is now rigid.
5. **Solder 6× ToF sensor boards** to their right-angle header positions on top/bottom plates.
6. **Mount DE10-Nano** to bottom plate (M2.5 standoffs + nuts -- only bolted joint remaining).
7. **Plug daughter board** into DE10-Nano GPIO headers through top plate cutout.
8. **Solder ESCs** to arm pads (signal + V+ + GND, 3 joints per ESC × 4 = 12 joints).
9. **Bolt motors** to arm tips (4× M3 per motor -- bolted, must be removable for prop changes).
10. **Bolt pump** to pump bracket (2× M2.5 with silicone vibration pads).
11. **Install reservoir**, secure with velcro cinch strap.
12. **Route tubing**: reservoir → pump → drip nozzle.
13. **Attach propellers** (correct CW/CCW per motor position).
14. **Velcro-strap battery** to bottom plate underside.

**Remaining fastener hardware** (dramatically reduced):

| Item | Spec | Qty | Purpose |
|------|------|-----|---------|
| M3 × 6mm bolt | Stainless steel | 16 | Motor mounting (4 per motor) |
| M3 locknut | Nylon insert | 16 | Motor mounting |
| M2.5 × 15mm standoff (M-F) | Nylon | 4 | DE10-Nano mount |
| M2.5 × 6mm bolt | Stainless steel | 4 | DE10-Nano (top) |
| M2.5 nut | Standard | 4 | DE10-Nano (bottom plate) |
| M2.5 × 8mm bolt | Stainless steel | 2 | Pump to bracket |
| M2.5 nut | Nylon locknut | 2 | Pump to bracket |
| Velcro strap (20mm wide) | 250mm length | 2 | Battery + reservoir retention |

**Eliminated** (vs. bolt-together design): 4× M3 corner standoffs, 8× arm clamp bolts/nuts, 4× landing gear bolts/nuts, 16× ESC zip ties, 4× ToF bracket bolts, all ESC signal cables, all ToF sensor cables. Total hardware savings: ~15g and ~40 parts.

---

## 4. Motor Selection

### Requirements

| Parameter | Minimum | Preferred |
|-----------|---------|-----------|
| Thrust (per motor, 4S, 10×4.5 prop) | 750g | ≥850g |
| KV range | 880-1000 | 920-950 |
| Stator size | 22×13mm minimum | 22×13mm |
| Weight | <65g | <58g |
| Mounting | M3 standard | 16×19mm pattern |
| Shaft | 3.17mm (1/8") or 5mm | 5mm (prop adapter included) |

### 4S Thermal Note

Most 2212/1000KV motors are rated for 2-3S. Running on 4S with 1045 props pushes current and heat limits. The EMAX MT2213 935KV datasheet recommends 8045 props on 4S (not 1045). The SunnySky X2212 980KV handles 4S/1045 better due to superior winding and bearings. Consider 9047 props as a compromise if thermals are a concern -- still yields ~800-900g thrust per motor.

### Primary Recommendation: SunnySky X2212 980KV (V3)

| Spec | Value |
|------|-------|
| Model | SunnySky X2212-III 980KV (Multirotor version) |
| Stator | 22 × 12mm |
| KV | 980 RPM/V |
| Motor weight | 57g |
| Shaft diameter | 3mm |
| Mounting pattern | M3, 16mm × 19mm (rectangular) |
| Internal resistance | 92 mΩ |
| Max continuous current | 18A (26A burst/30s) |
| Max thrust (4S, 1045 prop) | ~850-1000g |
| Configuration | 12N14P |
| Connector | 3.5mm bullet (3 wires) |
| Price | ~$23 each |
| Availability | ReadyMadeRC, Amazon, Banggood |

**Why this motor**: Best-in-class build quality for 22xx multirotor motors -- hand-wound coils, NMB bearings, well-documented. Safely handles 4S with 1045 props within thermal limits. Lower internal resistance (92mΩ vs 180mΩ for EMAX) means less heat and better efficiency.

**CW/CCW pairs**: Available in CW/CCW thread versions. Or buy all standard thread and use nylon locknuts.

### Thrust Calculation

With SunnySky X2212 980KV on 4S (14.8V nominal) with 10×4.5 nylon props:

| Throttle | RPM (est.) | Thrust/motor | Total thrust | Current/motor |
|----------|-----------|-------------|-------------|---------------|
| 25% | ~3450 | ~220g | 880g | ~2A |
| 50% | ~6900 | ~520g | 2080g | ~6A |
| 75% | ~10400 | ~750g | 3000g | ~11A |
| 100% | ~13800 | ~900g | 3600g | ~15A |

**Hover point**: At 1272g AUW, hover throttle ≈ 35% (~318g/motor, ~3.3A/motor). Total hover current: ~13A. With 2200mAh battery: **~10 minutes hover endurance** (accounting for 20% reserve).

---

## 5. ESC Selection

### Requirements

| Parameter | Minimum | Preferred |
|-----------|---------|-----------|
| Continuous current | 25A | ≥30A |
| Firmware | BLHeli_32 | BLHeli_32 (for DShot600) |
| Protocol | DShot600 | DShot600 (DShot300/1200 also fine) |
| Input voltage | 4S (16.8V) | 2-6S |
| Form factor | Individual (not 4-in-1) | Compact for arm mounting |
| Signal input voltage | 3.3V compatible | Direct from FPGA GPIO |
| Weight | <12g | <10g |

### Primary Recommendation: FVT LittleBee Summer 30A BLHeli_32

| Spec | Value |
|------|-------|
| Model | Favourite FVT LittleBee Summer 30A BLHeli_32 |
| Firmware | BLHeli_32 (STM32F051 ARM 48MHz) |
| Continuous current | 30A |
| Burst current | 35A (10s) |
| Input voltage | 2-6S (7.4V - 25.2V) |
| Protocols | DShot150/300/600/1200, OneShot125/42, MultiShot, PWM |
| Signal voltage | 3.3V compatible (direct FPGA connection) |
| Current sensor | Built-in (configurable via BLHeli Suite) |
| Current limiting | Yes (configurable) |
| Dimensions | 31 × 17mm |
| Weight | ~8g |
| BEC | None (opto) -- separate 5V regulator on daughter board |
| Price | ~$6.25 each (~$25 for 4-pack) |
| Availability | GetFPV, Banggood |

**Why this ESC**: Community favorite with proven reliability. 30A continuous is more than enough for 22xx motors at 15-18A max. Built-in current limiting prevents thermal damage. The configurable current sensor enables per-motor monitoring via DShot telemetry. Excellent value at ~$25 for all four ESCs.

**DShot600 confirmation**: All BLHeli_32 ESCs support DShot600. The FPGA generates DShot frames at 600 kbit/s -- each bit is 1.67us. The ESC input is 3.3V tolerant (standard for BLHeli_32). No level shifting needed. The 74LVC1G17 Schmitt buffer on the daughter board cleans up the signal edges.

### ESC-to-Daughter-Board Wiring

ESCs mount on arm undersides via zip ties. Signal wires route along the arms to JST-XH 3-pin connectors on the daughter board (J1-J4):

```
Motor ─── (3× bullet connectors) ─── ESC ─── (signal wire along arm) ─── J1-J4 on daughter board
                                       │
                                 (power wires)
                                       │
                               Battery via XT60
```

**Power distribution**: ESC battery wires connect to the main XT60 battery connector. Options:
- Solder a small power distribution board (PDB) -- or simply use the bottom plate PCB as a PDB by adding copper pours for battery V+ and GND with solder pads for each ESC
- Wire a 4-way XT60 splitter (simplest for prototype)

**Bottom plate as PDB**: Add 2oz copper pour on the bottom plate's power/ground layers. Solder pads at each arm position for ESC battery wires. XT60 connector at one edge. This eliminates a separate PDB and saves weight/wiring.

---

## 6. Propellers

### Primary: GemFan 1045 (10×4.5)

| Spec | Value |
|------|-------|
| Model | GemFan 1045 Nylon |
| Diameter × Pitch | 10" × 4.5" (254mm × 114mm) |
| Material | Glass-fiber reinforced nylon |
| Hub bore | 6mm with reducer rings (3mm, 3.17mm, 4mm, 5mm included) |
| Weight | ~16g each (with adapter) |
| Pack | 2× CW + 2× CCW per pack |
| Price | ~$3 per pack of 4 |
| Availability | Amazon, Banggood -- extremely common |

**Why 1045**: Standard prop for 22xx class motors on 4S. Well-characterized thrust curves. Nylon is cheap and disposable (buy 5+ sets for crash replacements).

### Motor-Propeller Rotation

```
      FRONT
    1(CCW)  2(CW)
       \   /
        \ /
         X        ← Center stack
        / \
       /   \
    3(CW)  4(CCW)
      REAR
```

- Motor 1 (front-left): CCW rotation, CCW prop (pusher)
- Motor 2 (front-right): CW rotation, CW prop (pusher)
- Motor 3 (rear-left): CW rotation, CW prop (pusher)
- Motor 4 (rear-right): CCW rotation, CCW prop (pusher)

Opposite corners spin the same direction. This is the standard X-frame quadcopter configuration.

---

## 7. Battery

### Requirements

| Parameter | Minimum | Preferred |
|-----------|---------|-----------|
| Cell count | 4S | 4S |
| Capacity | 2000mAh | 2200-2600mAh |
| C-rating | 30C | ≥45C |
| Connector | XT60 | XT60 |
| Balance connector | JST-XH 5-pin | Standard 4S balance |
| Weight | <300g | <270g |
| Dimensions | Fits under 120mm plate | <35mm × 70mm × 120mm |

### Primary: Tattu 4S 2200mAh 45C

| Spec | Value |
|------|-------|
| Model | Tattu 4S1P 2200mAh 45C LiPo |
| Cells | 4S (14.8V nominal, 16.8V full, 14.0V cutoff) |
| Capacity | 2200mAh |
| Continuous discharge | 45C (99A) -- far exceeds our ~14A hover |
| Burst discharge | 90C (198A) |
| Connector | XT60 discharge, JST-XHR-5P balance |
| Weight | ~180g |
| Dimensions | 75 × 34 × 34mm |
| Internal resistance | <10mΩ per cell |
| Price | ~$45 |
| Availability | Banggood, Amazon |

**Endurance estimate**: At 13A hover current, 2200mAh / 13A = 0.169h ≈ **10.2 minutes hover**. With 20% reserve: **~8 minutes usable flight time**. Adequate for a plant-watering mission (takeoff → fly to plant → water → return → dock ≈ 3-5 minutes per cycle).

**Why Tattu**: Gens Ace/Tattu is a premium brand with consistent cell quality and accurate C-ratings. Lightest 2200mAh option at 180g.

### Battery Mounting

Battery hangs below the bottom plate, centered, secured with a 20mm velcro strap through the bottom plate's strap slots.

```
          Bottom Plate (bottom view)
    ┌─────────────────────────┐
    │                         │
    │  ┌──[strap slot]──┐    │
    │  │                 │    │
    │  │   BATTERY       │    │
    │  │   (velcro strap)│    │
    │  │                 │    │
    │  └──[strap slot]──┘    │
    │                         │
    └─────────────────────────┘
```

Low-mounted battery keeps the center of gravity below the propeller plane, improving stability.

---

## 8. Battery Management System (BMS)

### Why Onboard BMS

For autonomous dock charging, the drone must:
1. Accept charge current through pogo pads (V+ and GND only -- no balance connector cable)
2. Balance cells internally during charge
3. Protect against over-voltage, under-voltage, over-current, short circuit
4. Report per-cell voltages to the HPS for accurate state-of-charge estimation

A standard RC LiPo pack has NO onboard BMS -- it relies on an external balance charger connected via the JST-XH balance lead. For autonomous docking, we need an onboard BMS that handles balancing.

### Architecture

```
        Pogo Pads (from dock)          Battery (4S LiPo)
        V+ ──────────┐                    ┌── B+ (16.8V max)
                      │                    │
                      ├── CHG FET ─────────┤
        GND ──────┐   │                    │
                  │   ├── DSG FET ─────────┤── To daughter board XT60
                  │   │                    │
                  │   │   ┌──────────┐     │
                  │   └───┤ BQ76920  ├─────┤── Cell taps (B+, B3, B2, B1, B-)
                  │       │          │     │
                  │       │ I2C ─────┼─────┤── To GPIO_1[5-6] (shared I2C bus)
                  │       │          │     │
                  └───────┤ VSS      │     └── B- (0V)
                          └──────────┘
```

### BMS IC: TI BQ76920

| Spec | Value |
|------|-------|
| Part number | BQ76920DBTR |
| Cell count | 3-5 series cells |
| Cell voltage range | 1.5V - 4.5V per cell |
| Overvoltage protection | Configurable (4.25V default) |
| Undervoltage protection | Configurable (2.8V default) |
| Overcurrent detection | Yes (via external shunt) |
| Cell balancing | Passive (external FETs + resistors) |
| Balance current | Set by external resistor (typ. 50-100mA) |
| Communication | I2C (address 0x08) |
| Package | TSSOP-20 |
| Price | ~$3.50 |
| Quiescent current | 200uA (normal), 10uA (shipping mode) |

**No I2C address conflict**: BQ76920 is at 0x08 (fixed). Existing bus: TCA9548A (0x70), BMP390 (0x77), INA219 (0x40). All unique.

### BMS PCB Design

Small PCB that mounts below the bottom plate, inline with the battery wiring.

**Dimensions**: 30mm × 40mm, 1.6mm FR4 (JLCPCB PCBA)

**Components**:

| Ref | Part Number | Description | Package | Qty | Unit $ |
|-----|------------|-------------|---------|-----|--------|
| U1 | BQ76920DBTR | 3-5 cell battery monitor | TSSOP-20 | 1 | $3.50 |
| U2 | BQ76200PW | High-side/low-side FET driver | TSSOP-14 | 1 | $1.80 |
| Q1 | CSD18540Q5B | N-FET charge protect (60V, 100A) | SON 5×6mm | 1 | $1.20 |
| Q2 | CSD18540Q5B | N-FET discharge protect | SON 5×6mm | 1 | $1.20 |
| Q3-Q6 | BSS138 | N-FET cell balance switches | SOT-23 | 4 | $0.15 |
| R_BAL1-4 | 68Ω 1W | Cell balance bleed resistors | 2512 | 4 | $0.10 |
| R_SHUNT | 5mΩ 3W | Current sense | 2512 | 1 | $0.80 |
| C1-C3 | 100nF | Decoupling | 0402 | 3 | $0.02 |
| C4 | 10uF | Bulk | 0603 | 1 | $0.08 |
| J1 | JST-XH 5-pin | Battery balance connector | TH | 1 | $0.20 |
| J2 | JST-XH 2-pin | Charge input (from pogo pads) | TH | 1 | $0.14 |
| J3 | XT60 female | Load output (to daughter board) | TH | 1 | $1.20 |
| **BMS board total** | | | | | **~$12.00** |

### Cell Balancing

Passive balancing: During charge, when any cell exceeds 4.18V, the BQ76920 activates its balance FET. Current flows through the 68Ω bleed resistor, dissipating excess energy as heat:

```
Cell n: 4.20V ──[BSS138 ON]──[68Ω]──GND
                                │
              Balance current = 4.20V / 68Ω ≈ 62mA
              Power dissipation = 0.26W per resistor
```

At 62mA balance current, a 100mAh cell imbalance takes ~1.6 hours to equalize. This is fine for a dock-charging drone that has hours between flights.

### Charge Path (Dock → Battery)

1. Drone lands on dock. Pogo pads make contact (V+ and GND).
2. Base station charger provides CC/CV at 16.8V max, 1A charge current.
3. BMS BQ76920 monitors cell voltages during charge.
4. BQ76200 keeps charge FET (Q1) enabled while cell voltages are in range.
5. If any cell hits 4.25V, charge FET opens (overvoltage protection).
6. As cells approach full, balance FETs activate on higher cells.
7. Charge complete when current drops below 50mA at 16.8V.
8. BQ76920 reports "fully charged" via I2C to HPS.

### Discharge Path (Battery → Drone)

1. BQ76920 monitors cell voltages during flight.
2. If any cell drops below 3.2V: set undervoltage flag, HPS triggers return-to-dock.
3. If any cell drops below 2.8V: BQ76200 opens discharge FET (Q2) -- hard cutoff, motors die.
4. Overcurrent protection: if total current exceeds threshold (configurable, default 44A for the BQ76920 with 5mΩ shunt), discharge FET opens.

### Linux Integration

```bash
# BQ76920 I2C address: 0x08
# Read on shared bus GPIO_1[5-6], same as TCA9548A, BMP390, INA219

# Read cell voltages (registers 0x0C-0x13):
i2cget -y 1 0x08 0x0C w  # Cell 1 voltage (14-bit ADC, 382uV/LSB)
i2cget -y 1 0x08 0x0E w  # Cell 2
i2cget -y 1 0x08 0x10 w  # Cell 3
i2cget -y 1 0x08 0x12 w  # Cell 4

# Read pack voltage (register 0x2A-0x2B):
i2cget -y 1 0x08 0x2A w  # Total pack voltage

# Read temperature (register 0x2C-0x2D):
i2cget -y 1 0x08 0x2C w  # Die temperature or external NTC

# Read status (register 0x00):
# Bit 0: SCD (short circuit), Bit 1: OCD (overcurrent discharge)
# Bit 2: UV (undervoltage), Bit 3: OV (overvoltage)
```

### Base Station Charger

The dock's charger is simple -- just a CC/CV power supply at 16.8V, 1-2A:

| Option | Part | Price | Notes |
|--------|------|-------|-------|
| RC charger module | HiLetgo 4S balance charger module | ~$8 | Simple, off-the-shelf |
| Lab supply | Any 16.8V CC/CV supply | ~$15-30 | More flexible |
| Custom | LM317 + current limit | ~$3 | DIY, simple circuit |
| TP5100 (2S only) | NOT suitable | -- | Only supports 1-2S, need 4S |

**Recommended**: A simple CC/CV buck converter set to 16.8V, 1A. The BMS handles all protection and balancing. The dock charger just provides dumb power through the pogo pads.

---

## 9. Water Delivery System

### Overview

The drone carries 300ml of water in a collapsible reservoir, dispensed through a peristaltic pump controlled by FPGA PWM via a logic-level MOSFET on GPIO_0[20].

### Peristaltic Pump: Kamoer NKP-DC-S06B

| Spec | Value |
|------|-------|
| Model | Kamoer NKP-DC-S06B |
| Voltage | 12V DC |
| Flow rate | 37 ml/min (±5%) |
| Current | 0.25A (3W) |
| Weight | ~75g |
| Tubing | Silicone 3mm ID × 5mm OD |
| Motor life | 800+ hours |
| Price | ~$15 |

**Why peristaltic**: Self-priming, inherently prevents backflow when stopped (roller always compresses tubing), reversible, no contamination (fluid only contacts tubing), PWM-controllable for variable flow rate.

**Control**: FPGA GPIO_0[20] outputs 3.3V PWM at 5 kHz → 220Ω gate resistor → IRLZ44N MOSFET (logic-level, Vgs(th) ~1.5V). Pump motor connects between 12V rail and MOSFET drain. 1N4007 flyback diode across motor terminals.

**Flow control**: Linear proportional to PWM duty cycle. 50% duty ≈ 18 ml/min, 100% ≈ 37 ml/min. Below ~30% the motor stalls. At 100% duty, 300ml takes ~8 minutes to fully dispense. A typical plant watering of 50-100ml takes 1.5-3 minutes.

### Reservoir: TPU Collapsible Soft Flask (300ml)

| Spec | Value |
|------|-------|
| Material | TPU (thermoplastic polyurethane), food-grade, BPA-free |
| Capacity | 300ml |
| Weight (empty) | ~30g |
| Collapsed dimensions | ~40mm × 80mm × 10mm |
| Full dimensions | ~120mm × 80mm × 30mm |
| Price | ~$12-18 |

**Why collapsible**: As water is dispensed the bladder collapses, reducing air gaps and sloshing. The CG shift is gradual and predictable -- autopilot trims easily. A rigid container would slosh unpredictably and trap air.

**Mounting**: The reservoir sits between the top and bottom plates, centered on the frame. A velcro cinch strap through dedicated 3mm × 25mm strap slots in both plates secures it. The bladder rests on the bottom plate surface alongside the battery or above it depending on CG preference.

### Tubing and Nozzle

| Component | Spec | Weight | Price |
|-----------|------|--------|-------|
| Silicone tubing | 3mm ID × 5mm OD, 1.5m total | ~10g | $3 |
| Drip nozzle | Adjustable drip emitter (0-70 ml/min) | ~5g | $2 |

**Routing**: Reservoir outlet → 30cm tubing → pump inlet → pump → 80cm tubing → drip nozzle mounted below drone belly.

**Drip nozzle**: An adjustable drip emitter (DIG or Rain Bird brand) mounted below the bottom plate on a short rigid tube pointing straight down. Drip delivery avoids prop wash deflection -- water drops fall ballistically rather than being blown as mist would be. The nozzle hangs ~50mm below the bottom plate, between the landing gear legs.

```
    [Top plate]
    [Reservoir — centered between plates]
    [Bottom plate]
         │
    ┌────┴────┐
    │  Pump   │ ← Mounted to bottom plate edge via M2.5 standoffs + silicone pads
    └────┬────┘
         │ (tubing)
    ┌────┴────┐
    │  Drip   │ ← Hangs below bottom plate, between landing gear legs
    │  Nozzle │    Pointed straight down at plant pot
    └─────────┘
```

### CG Management

| State | Water mass | CG offset from geometric center |
|-------|-----------|--------------------------------|
| Full (300ml) | 300g | ~0mm (reservoir centered) |
| Half (150ml) | 150g | ~0mm (bladder collapses symmetrically) |
| Empty | 0g | ~0mm (30g empty bladder, negligible) |

The reservoir is centered on the frame, so water depletion changes total weight (affecting hover throttle) but does not shift CG laterally. Vertical CG rises ~5-10mm as water mass is removed, which improves stability.

**Pump offset**: The pump (75g) mounts at the bottom plate edge, creating a slight asymmetry. This is compensated by positioning it opposite the XT60 connector and any cable-heavy side. The ~2mm CG offset is within autopilot trim range.

### Water Delivery Components BOM

| Ref | Part | Qty | Unit $ | Weight |
|-----|------|-----|--------|--------|
| Kamoer NKP-DC-S06B | 12V peristaltic pump | 1 | $15.00 | 75g |
| TPU soft flask | 300ml collapsible reservoir | 1 | $15.00 | 30g |
| Silicone tubing 3×5mm | 1.5 meters | 1 | $3.00 | 10g |
| Drip emitter (adjustable) | DIG/Rain Bird | 1 | $2.00 | 5g |
| **Total** | | | **~$35** | **~120g** |

### Dock Water Refill

The charging dock includes a small water reservoir (~2L) with a gravity-fed fill port. When the drone docks, a second set of pogo-style spring contacts align a fill tube with the drone's reservoir inlet. The dock pump (or gravity head) refills the 300ml bladder in ~30-60 seconds while the battery charges.

This is a future design extension -- for initial testing, fill the reservoir manually before each flight.

---

## 10. Power Distribution

Power distribution is integrated into the bottom plate and arm PCBs -- no separate PDB or ESC power wiring needed.

### Bottom Plate PDB Design

The bottom plate's bottom copper layer (2oz) carries battery power to each arm slot via wide copper pours:

```
    Bottom Plate (bottom copper layer)

    ┌─────────────────────────────────┐
    │                                 │
    │   [ARM4 slot]      [ARM2 slot]  │   V+ and GND route through castellated
    │        \               /        │   joints into arm power traces
    │         \             /         │
    │          \    [XT60] /          │   ← Edge-mounted XT60 connector
    │           \    V+   /           │
    │            \  GND  /            │
    │           ──────────            │   ← 2oz copper pour (V+ and GND polygons)
    │          /          \           │
    │         /            \          │
    │        /              \         │
    │   [ARM3 slot]      [ARM1 slot]  │
    │                                 │
    └─────────────────────────────────┘
```

- **V+ polygon**: Connects XT60 V+ to the V+ castellated pad at each arm slot. 2oz copper, 10mm+ pour width.
- **GND polygon**: Connects XT60 GND to the GND castellated pad at each arm slot. 2oz copper, 10mm+ pour width.
- When arms solder into the slots, the power castellations connect directly to the arm's V+ and GND traces that run to the ESC solder pads.
- **No separate ESC power wiring**: Battery current flows: XT60 → bottom plate copper pour → castellated joint → arm PCB traces → ESC solder pads. All copper, all soldered.

### Current Path

```
Battery XT60 ──► Bottom plate V+ pour ──► Arm slot castellation ──► Arm V+ trace (3mm, 2oz) ──► ESC V+ pad
                 Bottom plate GND pour ──► Arm slot castellation ──► Arm GND trace (3mm, 2oz) ──► ESC GND pad
```

**Current capacity**: 2oz copper, 3mm trace width handles ~6A continuous at 25°C rise. With 10mm+ pour width on the bottom plate: >30A capacity -- well above the ~15A peak per arm.

### DShot Signal Path

```
Daughter board J1-J4 ──► Top plate signal trace ──► Arm slot castellation ──► Arm signal trace ──► ESC signal pad
```

DShot600 signal traces are 0.2mm (minimal current) on the top copper layer. They route from the daughter board connector pads through top plate traces to the arm slot castellations, then along each arm to the ESC signal pad. **No signal cables needed**.

---

## 12. JLCPCB Order Strategy

### Order 1: Daughter Board (PCBA)

| Detail | Value |
|--------|-------|
| Board | 85×100mm, 4-layer, 1.6mm, ENIG |
| Assembly | Top side SMD + through-hole |
| Qty | 5 |
| PCB cost | ~$12 |
| Assembly cost | ~$25-40 (depending on part count) |
| Parts cost | ~$50 (BOM from LCSC) |
| **Total** | **~$87-102 for 5 boards** |

### Order 2: BMS Board (PCBA)

| Detail | Value |
|--------|-------|
| Board | 30×40mm, 2-layer, 1.6mm, HASL |
| Assembly | Top side SMD + through-hole |
| Qty | 5 |
| PCB cost | ~$2 |
| Assembly cost | ~$10-15 |
| Parts cost | ~$12 (BOM from LCSC) |
| **Total** | **~$24-29 for 5 boards** |

### Order 3: Structural + Signal PCBs (bare boards, no assembly)

All structural boards require **castellated holes** -- specify this in JLCPCB order notes.

| Board | Dimensions | Qty per panel | Panels | Thickness | Cu weight | Special |
|-------|-----------|---------------|--------|-----------|-----------|---------|
| Bottom plate | 120×120mm | 1 | 5 | 2.0mm | 2oz outer | Castellated arm slots + edge pads, XT60 footprint |
| Top plate | 120×120mm | 1 | 5 | 1.6mm | 1oz | Castellated arm slots, RA header footprints for ToF |
| Arms (4 per drone) | 25×220mm | 4 panelized on 110×220mm | 5 | 1.6mm | 2oz | Castellated tab edges, signal + power traces |
| Landing gear (4 per drone) | 20×120mm (L unfolded) | 4 panelized on 80×120mm | 5 | 2.0mm | 1oz | Castellated top edge |
| ToF sensor boards (6 per drone) | 12×15mm | 12 on 60×30mm panel | 5 | 1.0mm | 1oz | VL53L1X footprint + RA header |
| Pump bracket | 25×40mm | 4 on 50×40mm panel | 5 | 1.6mm | 1oz | Castellated top edge |

**Panelization**: JLCPCB supports V-score and tab-route panelization. Arms: 4 per 110×220mm panel. Landing gear: 4 per 80×120mm panel. ToF boards: 12 per 60×30mm panel (2 drones' worth). Pump brackets: 4 per 50×40mm panel.

| Panel | Size | Cost (5 panels) | Notes |
|-------|------|-----------------|-------|
| Bottom plate | 120×120mm | ~$7 | 2oz copper + castellated surcharge |
| Top plate | 120×120mm | ~$5 | Castellated surcharge |
| Arms panel | 110×220mm | ~$8 | 2oz copper + castellated edges |
| Legs panel | 80×120mm | ~$5 | 2.0mm + castellated edges |
| ToF panel | 60×30mm | ~$3 | Thin 1.0mm + castellated |
| Pump bracket panel | 50×40mm | ~$2 | Castellated |
| **Structural total** | | **~$30 for 5 sets** | ~$6.00 per drone frame |

**Castellated hole surcharge**: JLCPCB charges ~$1-3 extra per board for castellated holes (minimum 0.6mm diameter, 1.0mm pitch). This is offset by eliminating all bracket hardware and most fasteners.

### Order 4: Base Station PCB (PCBA, future)

IR LED driver + charger circuit for the dock. Defer to a later design iteration.

---

## 13. Complete BOM -- Per Drone

### Per-Drone Cost

| Category | Items | Cost |
|----------|-------|------|
| **PCB Frame** | Bottom plate, top plate, 4 arms, 4 legs, 6 ToF boards, pump bracket | $6.00 |
| **Hardware** | M3/M2.5 bolts, nuts, velcro straps, solder | $3.00 |
| **Motors** | 4× SunnySky X2212 980KV | $92.00 |
| **ESCs** | 4× FVT LittleBee 30A BLHeli_32 | $25.00 |
| **Propellers** | 2× GemFan 1045 pack (4+4 props) | $6.00 |
| **Battery** | 1× Tattu 4S 2200mAh 45C | $45.00 |
| **Daughter board** (PCBA) | 1× assembled | $18.00 |
| **BMS board** (PCBA) | 1× assembled | $5.00 |
| **DE10-Nano** | 1× dev board | $130.00 |
| **External sensors** | 6× VL53L1X, 1× OV5640, 4× TSOP38238 | $75.00 |
| **Water delivery** | Pump, reservoir, tubing, nozzle | $35.00 |
| **Peripherals** | Buzzer, cables, connectors | $10.00 |
| **Base station** | IR beacon + charger (estimate) | $30.00 |
| | | |
| **Total per drone** | | **~$480** |

---

## 14. Flight Performance Estimates

| Parameter | Value | Notes |
|-----------|-------|-------|
| AUW (dry, no water) | ~972g | Dry weight |
| AUW (300ml water) | ~1272g | Full payload |
| Thrust-to-weight (dry) | 3.7:1 | Aggressive maneuvering possible |
| Thrust-to-weight (loaded) | 2.8:1 | Stable hover + moderate agility |
| Hover throttle (loaded) | ~35% | Efficient operating point |
| Hover current (total) | ~13A | All 4 motors combined |
| Flight time (loaded) | ~8 min | 2200mAh, 20% reserve |
| Flight time (dry, no water) | ~11 min | Lower current draw |
| Max horizontal speed | ~8 m/s | Limited by indoor safety, not power |
| Max climb rate | ~3 m/s | With 300ml water |

### Mission Profile

```
[DOCK] ──take off──> [2m altitude] ──fly to plant──> [hover] ──water──> [fly back] ──land──> [DOCK]
  0s                    5s              15s              30s        45s        55s          65s

Power phases:
  Climb (5s):    ~28A total, 38.9mAh consumed
  Cruise (40s):  ~13A total, 144.4mAh consumed
  Hover+Water(15s): ~15A total, 62.5mAh consumed
  Descent (5s):  ~7A total, 9.7mAh consumed

Total per mission cycle: ~256mAh
Missions per charge: 2200mAh × 0.8 (reserve) / 256mAh ≈ 6-7 plants per charge
```

---

## 15. Assembly Checklist

- [ ] Order all PCBs from JLCPCB (daughter board PCBA, BMS PCBA, structural bare boards, ToF L-brackets)
- [ ] Order motors, ESCs, battery, props, hardware from Amazon/Banggood
- [ ] Order external sensors (6× VL53L1X, 1× OV5640, 4× TSOP38238) from DigiKey/Adafruit
- [ ] Order water delivery components (pump, reservoir, tubing, drip nozzle)
- [ ] Break apart arm, leg, and ToF bracket panels (V-score snap)
- [ ] Bend ToF L-brackets to 90° (heat with heat gun at V-score line)
- [ ] Assemble frame: bottom plate → standoffs → DE10-Nano → arms → top plate → landing gear
- [ ] Mount motors to arm tips (4× M3 bolts per motor, use Loctite 242 threadlock)
- [ ] Mount ESCs to arm undersides (zip ties, or solder battery wires to bottom plate PDB)
- [ ] Route ESC signal wires along arms to daughter board JST-XH connectors (J1-J4)
- [ ] Mount ToF sensors: down sensor on bottom plate center, up sensor on top plate center, 4× horizontal sensors on L-brackets at plate edges
- [ ] Connect ToF sensors via JST-SH cables to daughter board J6-J11
- [ ] Connect BMS: battery balance lead to BMS J1, BMS output to daughter board XT60
- [ ] Plug daughter board into DE10-Nano GPIO headers
- [ ] Connect LTC bridge cable: daughter board J13 → DE10-Nano LTC connector (J10)
- [ ] Attach camera module via FPC cable to daughter board J5
- [ ] Connect IR receivers via JST-SH cables to daughter board J12A-J12D
- [ ] Mount peristaltic pump to bottom plate edge (M2.5 standoffs + silicone vibration pads)
- [ ] Install reservoir between plates, secure with velcro cinch strap
- [ ] Route tubing: reservoir → pump inlet → pump outlet → drip nozzle below bottom plate
- [ ] Attach propellers (correct CW/CCW per motor position)
- [ ] Velcro-strap battery to bottom plate underside
- [ ] Pre-flight: check motor spin direction, verify DShot communication, test all 6 ToF sensors, test pump flow via SSH
