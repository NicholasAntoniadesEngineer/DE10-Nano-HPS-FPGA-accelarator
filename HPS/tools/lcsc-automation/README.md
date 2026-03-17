# LCSC Automation Framework

Production-grade LCSC component sourcing and KiCAD integration system. Fully automated BOM generation, library management, and inventory verification.

## Features

- **LCSC Data Fetching**: Multi-source integration (LCSC API, easyeda2kicad, jlcparts JSON, web scraping)
- **KiCAD Library Generation**: Automated symbol, footprint, and 3D model download + placement
- **BOM/CPL Generation**: Parse KiCad schematics → production-ready manufacturing files
- **Component Validation**: Real-time stock checks, DFM compliance, supply chain risk assessment
- **Caching & Rate Limiting**: Local cache prevents redundant API calls, respects LCSC rate limits
- **Scaleable Architecture**: Extensible for new part types, data sources, and design rules

## Quick Start

### 1. Install Dependencies

```bash
cd HPS/tools/lcsc-automation
pip install -r requirements.txt
```

### 2. Configure (Optional)

Edit `config.yaml` to set:
- LCSC API credentials (if approved)
- Fallback data sources
- Cache location
- KiCAD library path

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

### 3. Run Automation

#### Validate parts in component definitions:
```bash
python lcsc_automation.py --validate drone_design/drone_model/components/electronics/daughter_board_components.py
```

#### Generate BOM/CPL from schematic:
```bash
python lcsc_automation.py --generate-bom drone_design/drone_model/components/electronics/daughter_board_esp32.kicad_sch
```

#### Download complete KiCAD library:
```bash
python lcsc_automation.py --download-library daughter_board_esp32_BOM.csv --output-dir kicad_lib/
```

#### End-to-end: Update everything from schematic:
```bash
python lcsc_automation.py --full-refresh daughter_board_esp32.kicad_sch
```

## Architecture

```
lcsc-automation/
├── config.py               # Configuration, caching, settings
├── lcsc_fetcher.py         # LCSC data acquisition (multi-source)
├── kicad_parser.py         # KiCad schematic/footprint parsing
├── library_manager.py      # Symbol, footprint, 3D model management
├── bom_generator.py        # BOM/CPL CSV generation
├── validator.py            # Stock, DFM, supply chain validation
├── easyeda_wrapper.py      # easyeda2kicad CLI batch processing
├── utils.py                # Helpers (logging, caching, HTTP)
├── lcsc_automation.py      # Main CLI
├── requirements.txt        # Python dependencies
├── config.example.yaml     # Template configuration
├── tests/                  # Unit + integration tests
└── data/                   # Cached LCSC parts, 3D models, footprints
```

## Usage Examples

### Verify all parts in component definition

```python
from lcsc_fetcher import verify_component_list
parts = verify_component_list("daughter_board_components.py")
# Returns dict: {part_name: {lcsc_code, status, stock, price, ...}}
```

### Fetch single part data

```python
from lcsc_fetcher import fetch_part_data
part = fetch_part_data("C2040")  # LCSC ID for a capacitor
print(f"Part: {part['description']}, Stock: {part['stock']}, Price: ${part['price']}")
```

### Download symbols + footprints + 3D models

```python
from library_manager import KiCADLibraryManager
lib_mgr = KiCADLibraryManager("kicad_lib/")
lib_mgr.add_part("C2040", download_3d=True, download_models=True)
lib_mgr.save_library("daughter_board.kicad_sym")
```

### Parse schematic → generate BOM

```python
from kicad_parser import KiCADSchematicParser
from bom_generator import BOMMGenerator
parser = KiCADSchematicParser("daughter_board_esp32.kicad_sch")
components = parser.get_components()
bom = BOMMGenerator(components)
bom.export_csv("daughter_board_BOM.csv")
bom.export_cpl("daughter_board_CPL.csv")
```

## Key Modules

### config.py
- Loads `config.yaml` or environment variables
- Manages cache location, API keys, fallback chains
- Logging configuration
- Rate limit tracking

### lcsc_fetcher.py
- **Primary**: Official LCSC REST API (if approved)
- **Fallback 1**: easyeda2kicad CLI (local conversion)
- **Fallback 2**: jlcparts JSON (GitHub-hosted JSON for all JLCPCB parts)
- **Fallback 3**: Web scraping (BeautifulSoup + Selenium)
- Caching prevents redundant fetches
- Respects rate limits (100-200 req/min)

### kicad_parser.py
- Parse KiCad v6+ schematic files (.kicad_sch, s-expression format)
- Extract components, reference designators, values, footprints, LCSC codes (from properties)
- Validate schematic integrity (missing footprints, unmapped parts)
- Export component list

### library_manager.py
- Batch-download symbols, footprints, 3D models from easyeda2kicad
- Organize into KiCAD library tables (separate symbol/footprint libs)
- Verify footprints match schematic properties
- Generate KiCAD 6.0+ symbol lib files
- Cache downloaded models locally

### bom_generator.py
- Parse schematic components → BOM CSV (Comment, Designator, Footprint, LCSC Part #)
- Generate CPL CSV (Component, Value, Device, LCSC ID, Rotation, X, Y, Layer)
- Quantity aggregation (same value/footprint = one line)
- JLCPCB-format compatible

### validator.py
- Real-time stock checks against LCSC API
- DFM compliance (footprint dimensions, trace widths, via spacing)
- Supply chain risk (single-source parts, lead time warnings)
- RoHS compliance verification
- Alternative part suggestions (same footprint/value)

### easyeda_wrapper.py
- Wraps easyeda2kicad CLI for batch processing
- Parallel downloads (multiprocessing)
- Retry logic for failed parts
- Local caching of downloaded libraries
- Progress tracking

### utils.py
- HTTP client with caching + rate limiting
- S-expression parser (for KiCad files)
- CSV export helpers
- Logging utilities
- File I/O with backup

## Configuration (config.yaml)

```yaml
lcsc:
  api_enabled: false                 # Set true if LCSC API approved
  api_key: ""                        # LCSC API key
  api_secret: ""                     # LCSC API secret
  rate_limit_rpm: 100                # Requests per minute (safe default)

sources:
  priority:
    - lcsc_api                       # Try official API first
    - easyeda2kicad                  # Fallback to CLI tool
    - jlcparts_json                  # Fallback to community JSON
    - web_scraping                   # Last resort

cache:
  enabled: true
  directory: "data/lcsc_cache/"
  ttl_days: 30                       # Refresh parts older than 30 days

kicad:
  library_dir: "../../FPGA/kicad_lib/"
  symbol_lib: "lcsc_parts.kicad_sym"
  footprint_lib: "lcsc_parts.pretty/"
  3d_models_dir: "3dmodels/"

logging:
  level: INFO
  file: "lcsc_automation.log"
```

## Supported Part Sources

### LCSC API (Official)
- Requires approval: https://www.lcsc.com/docs/openapi/index.html
- Rate limit: 1000 req/day standard, upgradeable
- Data: pricing, stock, RoHS, manufacturer specs

### easyeda2kicad (Fallback 1)
- GitHub: https://github.com/uPesy/easyeda2kicad.py
- CLI-based: automatic symbol, footprint, 3D model download
- Installation: `pip install easyeda2kicad`

### jlcparts (Fallback 2)
- GitHub: https://github.com/yaqwsx/jlcparts
- JSON dump: all JLCPCB parts with specs
- No rate limits (GitHub-hosted static JSON)

### Web Scraping (Fallback 3)
- Direct LCSC product page scraping (BeautifulSoup)
- Slower but always available
- Respects rate limits (100 req/min)

## Integration with Build System

### Makefile targets

```bash
make update-bom                    # Regenerate BOM/CPL from schematic
make validate-parts               # Verify all parts in stock on LCSC
make download-kicad-library       # Download/update KiCAD symbols, footprints, 3D
make full-refresh                 # Complete rebuild: validate → download → generate
```

### CI/CD Integration

Include in build pipeline:
```bash
# Validate before commit
python HPS/tools/lcsc-automation/lcsc_automation.py --validate drone_design/drone_model/components/electronics/daughter_board_components.py

# Regenerate manufacturing files
python HPS/tools/lcsc-automation/lcsc_automation.py --generate-bom drone_design/drone_model/components/electronics/daughter_board_esp32.kicad_sch
```

## Testing

```bash
cd HPS/tools/lcsc-automation
python -m pytest tests/ -v

# Test specific module
python -m pytest tests/test_lcsc_fetcher.py -v

# Test with real LCSC data (uses cache)
python -m pytest tests/ --use-live-data -v
```

## Performance Notes

- **First run**: ~30-60 sec (downloads all symbols, footprints, 3D models for ~10-20 parts)
- **Cached runs**: <5 sec (reads local cache)
- **Validation**: ~2-5 sec per 50 parts (uses cached LCSC data)
- **Parallel downloads**: 4 workers by default, configurable

## Troubleshooting

### Part not found on LCSC
```bash
# Search for alternatives
python lcsc_automation.py --search-alternatives --part "ESP32" --footprint "QFN-48"
```

### Rate limit hit
```
# Wait 1 minute, then retry. Cache prevents redundant requests.
# Configure longer cache TTL in config.yaml
```

### 3D models not downloading
```bash
# Verify easyeda2kicad installed
pip install --upgrade easyeda2kicad

# Check connectivity to EasyEDA
python -c "from easyeda2kicad import easyeda_connector; easyeda_connector.test_connection()"
```

## Roadmap

- [ ] LCSC API approval workflow (automated request)
- [ ] Real-time stock alert service (Slack/email)
- [ ] Component lifecycle tracking (obsolescence warnings)
- [ ] Historical pricing analytics
- [ ] Alternative part fuzzy-matching (same specs, different vendor)
- [ ] Manufacturing cost optimization (MOQ, volume discounts)
- [ ] Supply chain risk dashboard (single-source, lead time)

## License

MIT - Part of DE10-Nano HPS-FPGA Accelerator project
