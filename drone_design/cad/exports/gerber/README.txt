Drone FR4 Frame Parts — KiCad PCB Files
========================================

Generated: 2026-03-14 22:26

These are MECHANICAL PCBs — no copper traces, no electrical components.
Order as standard FR4 PCB from any fabricator (JLCPCB, PCBWay, OSH Park).

Files:
  bottom_plate.kicad_pcb  — 120x120mm, 2.0mm FR4, Kagome lattice cutouts
  top_plate.kicad_pcb     — 120x120mm, 1.6mm FR4, central opening + cutouts
  arm.kicad_pcb           — 245x25mm, 1.6mm FR4, I-beam profile, M3 motor holes
  landing_leg.kicad_pcb   — L-shape, 2.0mm FR4, capsule lightening holes
  nose_boom.kicad_pcb     — 380x20mm, 1.6mm FR4, I-beam profile
  pump_bracket.kicad_pcb  — 25x40mm, 1.6mm FR4

Fabrication specs:
  Material:     FR4 (standard glass-epoxy)
  Finish:       HASL or bare copper (cosmetic only)
  Solder mask:  Optional (green default)
  Silkscreen:   White (part labels)
  Min hole:     2.5mm (M2.5 standoff) / 3.2mm (M3 motor mount)
  Copper:       Not required — these are structural, not electrical

To generate Gerber files (requires KiCad 7+):
  kicad-cli pcb export gerbers -o gerber_out/ bottom_plate.kicad_pcb
  kicad-cli pcb export drill -o gerber_out/ bottom_plate.kicad_pcb

Or open in KiCad GUI: File → Fabrication Outputs → Gerbers

Quantities per drone:
  bottom_plate × 1
  top_plate    × 1
  arm          × 4
  landing_leg  × 4
  nose_boom    × 1
  pump_bracket × 1
  Total: 12 PCBs per drone
