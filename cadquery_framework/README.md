# cadquery_framework

Shared tooling for generating CadQuery 3D models, KiCad PCB files, and assembly outputs.

## Structure

```
cadquery_framework/
├── kicad/
│   ├── jlcpcb_constraints.py   ← PCB manufacturing constraints (SINGLE SOURCE OF TRUTH)
│   └── primitives.py           ← KiCad S-expression generators (imports constraints)
├── exporters/
│   ├── gerber_export.py        ← Writes .kicad_pcb + .kicad_dru (imports constraints)
│   ├── step_export.py
│   └── stl_export.py
├── assembly/
│   ├── anchors.py
│   └── collision.py
├── viewer/
│   └── ...
├── modifiers.py
└── pipeline.py
```

## Manufacturing Constraints

**All PCB manufacturing tolerances live in one place:**

```
cadquery_framework/kicad/jlcpcb_constraints.py
```

This file must be imported by any code that:
- Generates `.kicad_pcb` files (board wrappers, footprint generators)
- Outputs `.kicad_dru` design rule files
- Embeds stackup definitions, trace widths, drill sizes, clearances, or text sizes

### What is centralised

| Constant group | Examples |
|---|---|
| JLCPCB process floors | `JLCPCB_MIN_TRACE_MM`, `JLCPCB_MIN_DRILL_MM` |
| Design rule margins | `DRM_MIN_TRACE_MM`, `DRM_POWER_TRACE_MM`, `DRM_VBATT_TRACE_MM` |
| Stackup (JLC04161H-7628) | `CU_OUTER_MM`, `CU_INNER_MM`, `PREPREG_THICKNESS_MM`, `CORE_THICKNESS_MM`, `PREPREG_DK` |
| Solder mask | `SOLDER_MASK_EXPANSION_MM`, `SOLDER_MASK_MIN_WIDTH_MM` |
| Footprint pads | `TH_GPIO_DRILL_MM`, `TH_GPIO_PAD_MM`, `TH_M25_DRILL_MM`, `TH_M25_PAD_MM` |
| Silkscreen text | `SILK_LARGE_SIZE_MM`, `SILK_REF_SIZE_MM`, `SILK_SMALL_SIZE_MM`, `SILK_MICRO_SIZE_MM` |
| Drawing widths | `EDGE_CUTS_WIDTH_MM`, `COURTYARD_WIDTH_MM` |

### DRU auto-generation

`gerber_export.py` automatically writes `jlcpcb_constraints.kicad_dru` alongside
every `.kicad_pcb` it generates. The DRU content is produced by `dru_content()` in
`jlcpcb_constraints.py` — so the file is always in sync with the Python constants.
Load this DRU in KiCad via: **File → Board Setup → Design Rules → Custom Rules → Load**.

### Changing manufacturer or process

1. Edit `cadquery_framework/kicad/jlcpcb_constraints.py`
2. Regenerate all PCBs: `python3 drone_design/drone_model/drone_3d_model.py gerber`
3. The updated `.kicad_dru` is written automatically

Do **not** hardcode manufacturing values in individual component files.
