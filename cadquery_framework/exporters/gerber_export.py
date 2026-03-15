"""Generic KiCad PCB file exporter.

Takes a list of (name, generator_function) pairs, calls each generator
to produce KiCad PCB content, and writes the files to disk.
"""

from pathlib import Path


def export_gerber_pcbs(pcb_generators, output_dir, readme_text=None, verbose=False):
    """Run PCB generator functions and write .kicad_pcb files.

    Args:
        pcb_generators: list of (name, generator_func) tuples.
            Each generator_func() returns a string of KiCad PCB content.
        output_dir: Path to output directory for .kicad_pcb files.
        readme_text: optional string to write as README.txt in output_dir.
        verbose: if True, print file sizes.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating KiCad PCB files...")
    for name, generator in pcb_generators:
        path = output_dir / f"{name}.kicad_pcb"
        content = generator()
        path.write_text(content, encoding="utf-8")
        size_kb = path.stat().st_size / 1024
        print(f"  {name}.kicad_pcb ({size_kb:.1f} KB)")

    if readme_text:
        readme = output_dir / "README.txt"
        readme.write_text(readme_text, encoding="utf-8")

    print(f"Generated {len(pcb_generators)} KiCad PCB files in: {output_dir}/")
