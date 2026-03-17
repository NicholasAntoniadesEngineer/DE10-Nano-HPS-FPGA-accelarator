# LCSC Automation Framework - Quick Start Guide

## Installation

### 1. Install Dependencies

From the automation directory:

```bash
cd HPS/tools/lcsc-automation
pip install -r requirements.txt
```

Or run the setup script:

```bash
./setup.sh
```

### 2. (Optional) Configure Settings

Copy the example configuration and customize:

```bash
cp config.example.yaml config.yaml
# Edit config.yaml to customize (optional - defaults work fine)
```

## Usage

### Basic Commands

#### Generate BOM and CPL from Schematic
```bash
# From project root
./scripts/lcsc-automation.sh --generate-bom drone_design/output/gerber/daughter_board_esp32.kicad_sch

# Or directly from automation directory
cd HPS/tools/lcsc-automation
python3 lcsc_automation.py --generate-bom <path-to-schematic.kicad_sch>
```

This generates:
- `daughter_board_esp32_BOM.csv` - Bill of materials (value, designators, footprint, LCSC ID)
- `daughter_board_esp32_CPL.csv` - Component placement list (for pick-and-place machines)

#### Validate LCSC Part Codes
```bash
./scripts/lcsc-automation.sh --validate drone_design/drone_model/components/electronics/daughter_board_components.py
```

#### Download KiCAD Library Files
```bash
./scripts/lcsc-automation.sh --download-library daughter_board_esp32_BOM.csv
```

This downloads symbols, footprints, and 3D models using easyeda2kicad.

#### Check Stock Availability
```bash
./scripts/lcsc-automation.sh --validate-stock daughter_board_esp32_BOM.csv
```

#### Complete Workflow
```bash
./scripts/lcsc-automation.sh --full-refresh drone_design/output/gerber/daughter_board_esp32.kicad_sch
```

This does everything: BOM generation → validation → library download.

#### Print Configuration
```bash
./scripts/lcsc-automation.sh --config
```

#### Print DFM Design Rules
```bash
./scripts/lcsc-automation.sh --dfm-limits
```

## Workflow Example

### 1. Start with your KiCAD schematic
Create/update schematic with all components and assign LCSC part codes in component properties.

### 2. Generate BOM and CPL
```bash
python3 lcsc_automation.py --generate-bom your_design.kicad_sch
```

Output files:
- `your_design_BOM.csv` - For ordering from JLCPCB
- `your_design_CPL.csv` - For pick-and-place assembly

### 3. Validate Stock and Assembly
```bash
python3 lcsc_automation.py --validate-stock your_design_BOM.csv
```

### 4. Download Library (Optional)
If you want symbols and footprints from the parts:
```bash
python3 lcsc_automation.py --download-library your_design_BOM.csv
```

### 5. Order from JLCPCB
1. Go to https://jlcpcb.com
2. Upload Gerber files
3. Upload `your_design_BOM.csv` for component ordering
4. Upload `your_design_CPL.csv` for SMT assembly placement
5. Review and order

## Architecture

The framework is modular and extensible:

- **config.py** - Configuration management and caching
- **lcsc_fetcher.py** - Multi-source LCSC data retrieval (LCSC API, easyeda2kicad, jlcparts, web scraping)
- **kicad_parser.py** - KiCAD schematic parsing (s-expression format)
- **bom_generator.py** - BOM/CPL generation for manufacturing
- **library_manager.py** - KiCAD library organization (symbols, footprints, 3D models)
- **validator.py** - Component validation (stock, DFM, supply chain)
- **utils.py** - HTTP client, caching, CSV utilities

## Troubleshooting

### "easyeda2kicad not found"
Install easyeda2kicad:
```bash
pip install easyeda2kicad
```

### "No LCSC codes found in BOM"
Make sure your KiCAD schematic components have LCSC part codes in the "LCSC" property.

### Network errors when fetching parts
The framework caches all data locally. If online sources are unavailable:
1. First run will fail to fetch
2. Subsequent runs use cache (30 days default)
3. Update cache time in `config.yaml` if needed

### Missing footprints in BOM
Ensure all components in your schematic have valid KiCAD footprints assigned.

## Integration with Build System

The framework integrates with your project's build system:

```makefile
# Add to your Makefile
.PHONY: update-bom validate-bom download-kicad-lib

update-bom:
	python3 HPS/tools/lcsc-automation/lcsc_automation.py --generate-bom \
		drone_design/output/gerber/daughter_board_esp32.kicad_sch

validate-bom:
	python3 HPS/tools/lcsc-automation/lcsc_automation.py --validate-stock \
		drone_design/output/gerber/daughter_board_esp32_BOM.csv

download-kicad-lib:
	python3 HPS/tools/lcsc-automation/lcsc_automation.py --download-library \
		drone_design/output/gerber/daughter_board_esp32_BOM.csv
```

Then use:
```bash
make update-bom
make validate-bom
make download-kicad-lib
```

## Performance

- **First run**: ~30-60 seconds (downloads all data)
- **Cached runs**: <5 seconds (reads local cache)
- **Stock validation**: ~2-5 seconds per 50 parts
- **Library downloads**: ~10-30 seconds per part (parallel, 4 workers)

## Features

✓ Multi-source fallback chain (API → easyeda2kicad → jlcparts JSON → scraping)
✓ Automatic caching (30-day TTL, configurable)
✓ Rate limiting (respects 100-200 req/min LCSC limits)
✓ Real-time stock checking
✓ DFM compliance verification
✓ Supply chain risk assessment
✓ KiCAD library auto-organization
✓ JLCPCB manufacturing format output
✓ Extensible architecture

## Advanced Usage

### Python API

Use the framework from your own scripts:

```python
from pathlib import Path
from bom_generator import BOMMFromSchematic
from lcsc_fetcher import LCSCFetcher

# Generate BOM from schematic
bom = BOMMFromSchematic(Path("daughter_board.kicad_sch"))
bom.generate_all(Path("manufacturing"))

# Fetch part data
fetcher = LCSCFetcher()
part = fetcher.fetch_part("C2040")
print(f"{part.description}: ${part.price}, stock: {part.stock}")
```

### Custom Data Sources

The framework is extensible - add custom data sources by subclassing fetchers:

```python
from lcsc_fetcher import LCSCFetcher

# Add your own fetcher
class MyCustomFetcher(LCSCFetcher):
    def _try_custom_source(self, lcsc_id):
        # Your custom implementation
        pass
```

### Configuration via Environment Variables

Set API credentials via environment:

```bash
export LCSC_API_KEY="your_key"
export LCSC_API_SECRET="your_secret"
python3 lcsc_automation.py --validate-stock bom.csv
```

## Support & Contributions

- Documentation: see README.md
- Issues: Report in project repository
- Pull requests welcome!

## License

MIT - Part of DE10-Nano HPS-FPGA Accelerator project
