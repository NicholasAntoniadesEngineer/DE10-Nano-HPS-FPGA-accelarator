"""KiCad schematic (.kicad_sch) S-expression generator.

Generates a flat schematic from a BoardDefinition, placing one symbol per
component with net labels on every connected pin.  The schematic is intended
for visual review — it is NOT a layout-grade schematic, but it accurately
represents every electrical connection defined in the netlist.

Output format: KiCad 7/8 .kicad_sch (version 20231120).
"""

from __future__ import annotations

import uuid as _uuid
from collections import defaultdict
from datetime import datetime

from cadquery_framework.kicad.component_library import (
    BoardDefinition,
    ComponentDef,
    Pin,
    Placement,
)


def _uid() -> str:
    return str(_uuid.uuid4())


# Symbol grid constants (mils → mm conversion: 1 mil = 0.0254 mm)
# KiCad schematics use mm internally but symbols are laid out on a 2.54mm grid
GRID = 2.54  # mm — standard schematic grid


# ---------------------------------------------------------------------------
# Pin direction mapping
# ---------------------------------------------------------------------------
_PIN_DIR = {
    "input": "input",
    "output": "output",
    "bidirectional": "bidirectional",
    "tri_state": "tri_state",
    "passive": "passive",
    "power_in": "power_in",
    "power_out": "power_out",
    "open_collector": "open_collector",
    "open_emitter": "open_emitter",
    "no_connect": "no_connect",
    "free": "free",
    "unspecified": "unspecified",
}


def _pin_electrical_type(pin_type: str) -> str:
    return _PIN_DIR.get(pin_type, "unspecified")


# ---------------------------------------------------------------------------
# Symbol generation
# ---------------------------------------------------------------------------

def _generate_lib_symbol(comp: ComponentDef) -> str:
    """Generate a lib_symbols entry for one component type."""
    symbol_name = f"{comp.ref_prefix}_{comp.value}_{comp.package}"
    # Sanitise for S-expression
    symbol_name = symbol_name.replace(" ", "_").replace("/", "_")

    pin_count = len(comp.pins)
    # Layout: pins on left and right sides of a rectangular body
    left_pins = (pin_count + 1) // 2
    right_pins = pin_count - left_pins
    body_h = max(left_pins, right_pins) * GRID + GRID
    body_w = max(8 * GRID, 10 * GRID)  # minimum body width

    lines = []
    lines.append(f'    (symbol "{symbol_name}" (in_bom yes) (on_board yes)')
    lines.append(f'      (property "Reference" "{comp.ref_prefix}" (at 0 {body_h / 2 + GRID:.2f} 0)')
    lines.append(f'        (effects (font (size 1.27 1.27)))')
    lines.append(f'      )')
    lines.append(f'      (property "Value" "{comp.value}" (at 0 {-body_h / 2 - GRID:.2f} 0)')
    lines.append(f'        (effects (font (size 1.27 1.27)))')
    lines.append(f'      )')
    lines.append(f'      (property "Footprint" "{comp.package}" (at 0 {-body_h / 2 - 2 * GRID:.2f} 0)')
    lines.append(f'        (effects (font (size 1.27 1.27)) hide)')
    lines.append(f'      )')
    lines.append(f'      (property "Datasheet" "{comp.datasheet}" (at 0 {-body_h / 2 - 3 * GRID:.2f} 0)')
    lines.append(f'        (effects (font (size 1.27 1.27)) hide)')
    lines.append(f'      )')
    lines.append(f'      (property "LCSC" "{comp.lcsc}" (at 0 {-body_h / 2 - 4 * GRID:.2f} 0)')
    lines.append(f'        (effects (font (size 1.27 1.27)) hide)')
    lines.append(f'      )')

    # Symbol unit 1 — body rectangle + pins
    lines.append(f'      (symbol "{symbol_name}_1_1"')
    hw = body_w / 2
    hh = body_h / 2
    lines.append(f'        (rectangle (start {-hw:.2f} {hh:.2f}) (end {hw:.2f} {-hh:.2f})')
    lines.append(f'          (stroke (width 0.254) (type default))')
    lines.append(f'          (fill (type background))')
    lines.append(f'        )')

    # Place pins — left side (input/passive), right side (output/power)
    for i, pin in enumerate(comp.pins):
        if i < left_pins:
            # Left side — pin extends left from body
            py = hh - (i + 1) * GRID
            px = -hw - GRID * 2
            angle = 0
        else:
            # Right side — pin extends right from body
            j = i - left_pins
            py = hh - (j + 1) * GRID
            px = hw + GRID * 2
            angle = 180

        etype = _pin_electrical_type(pin.pin_type)
        lines.append(f'        (pin {etype} line (at {px:.2f} {py:.2f} {angle})')
        lines.append(f'          (length {GRID * 2:.2f})')
        lines.append(f'          (name "{pin.name}" (effects (font (size 1.0 1.0))))')
        lines.append(f'          (number "{pin.number}" (effects (font (size 1.0 1.0))))')
        lines.append(f'        )')

    lines.append(f'      )')  # end symbol_1_1
    lines.append(f'    )')  # end symbol

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schematic file generation
# ---------------------------------------------------------------------------

def _build_pin_net_map(board: BoardDefinition) -> dict[str, dict[str, str]]:
    """Build ref → {pin_number → net_name} mapping."""
    result: dict[str, dict[str, str]] = defaultdict(dict)
    for net_name, connections in board.nets.items():
        for conn in connections:
            result[conn.ref][conn.pin_number] = net_name
    return dict(result)


def generate_schematic(board: BoardDefinition) -> str:
    """Generate a complete .kicad_sch file from a BoardDefinition.

    Places all components on a flat schematic sheet with net labels
    on every connected pin.  Power symbols (+3V3, +5V, GND, etc.)
    are represented as net labels.

    Returns the .kicad_sch file content as a string.
    """
    pin_net_map = _build_pin_net_map(board)

    # Collect unique component types for lib_symbols
    seen_types: dict[str, ComponentDef] = {}
    for p in board.placements:
        key = f"{p.component.ref_prefix}_{p.component.value}_{p.component.package}"
        key = key.replace(" ", "_").replace("/", "_")
        if key not in seen_types:
            seen_types[key] = p.component

    # Generate lib_symbols block
    lib_symbols_lines = []
    for comp in seen_types.values():
        lib_symbols_lines.append(_generate_lib_symbol(comp))

    # Layout components on schematic grid
    # Arrange in rows — ~6 components per row, spaced 40mm apart
    cols_per_row = 6
    col_spacing = 50.0  # mm between component centres
    row_spacing = 60.0  # mm between rows
    margin_x = 30.0
    margin_y = 30.0

    symbol_instances = []
    symbol_instance_entries = []  # for symbol_instances block
    net_labels = []
    no_connect_markers = []
    wires = []

    for idx, placement in enumerate(board.placements):
        col = idx % cols_per_row
        row = idx // cols_per_row
        sx = margin_x + col * col_spacing
        sy = margin_y + row * row_spacing

        comp = placement.component
        symbol_name = f"{comp.ref_prefix}_{comp.value}_{comp.package}"
        symbol_name = symbol_name.replace(" ", "_").replace("/", "_")

        pin_count = len(comp.pins)
        left_pins = (pin_count + 1) // 2
        body_h = max(left_pins, pin_count - left_pins) * GRID + GRID
        body_w = max(8 * GRID, 10 * GRID)
        hw = body_w / 2
        hh = body_h / 2

        inst_uuid = _uid()
        symbol_instance_entries.append(
            f'    (path "/{inst_uuid}" (reference "{placement.ref}") (unit 1))'
        )
        symbol_instances.append(
            f'  (symbol (lib_id "{symbol_name}") (at {sx:.2f} {sy:.2f} 0) '
            f'(unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) '
            f'(dnp no) (uuid "{inst_uuid}")\n'
            f'    (property "Reference" "{placement.ref}" (at {sx:.2f} {sy - hh - GRID:.2f} 0)\n'
            f'      (effects (font (size 1.27 1.27)))\n'
            f'    )\n'
            f'    (property "Value" "{comp.value}" (at {sx:.2f} {sy + hh + GRID:.2f} 0)\n'
            f'      (effects (font (size 1.27 1.27)))\n'
            f'    )\n'
            f'  )'
        )

        # Place net labels on each pin
        ref_nets = pin_net_map.get(placement.ref, {})
        for i, pin in enumerate(comp.pins):
            if i < left_pins:
                py = sy - hh + (i + 1) * GRID
                px = sx - hw - GRID * 2
            else:
                j = i - left_pins
                py = sy - hh + (j + 1) * GRID
                px = sx + hw + GRID * 2

            net_name = ref_nets.get(pin.number)
            if net_name:
                # Place a net label at the pin endpoint
                net_labels.append(
                    f'  (label "{net_name}" (at {px:.2f} {py:.2f} 0) '
                    f'(fields_autoplaced yes) (uuid "{_uid()}")\n'
                    f'    (effects (font (size 1.0 1.0)) (justify left))\n'
                    f'  )'
                )
            elif pin.pin_type == "no_connect":
                no_connect_markers.append(
                    f'  (no_connect (at {px:.2f} {py:.2f}) (uuid "{_uid()}"))'
                )

    # Assemble the file
    now = datetime.now().strftime("%Y-%m-%d")
    top_uuid = _uid()
    content = f"""(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")

  (uuid "{top_uuid}")

  (paper "A1")
  (title_block
    (title "{board.title}")
    (date "{now}")
    (rev "1.0")
    (comment 1 "{board.width:.0f} x {board.height:.0f} mm, {board.thickness:.1f}mm, 4-layer FR4")
    (comment 2 "{len(board.placements)} components, {board.net_count()} nets")
  )

  (lib_symbols
{chr(10).join(lib_symbols_lines)}
  )

{chr(10).join(symbol_instances)}

{chr(10).join(net_labels)}

{chr(10).join(no_connect_markers)}

{chr(10).join(wires)}

  (symbol_instances
{chr(10).join(symbol_instance_entries)}
  )

  (sheet_instances
    (path "/" (page "1"))
  )
)
"""
    return content
