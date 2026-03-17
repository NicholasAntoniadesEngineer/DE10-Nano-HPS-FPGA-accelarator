#!/bin/bash
#
# Setup script for LCSC Automation Framework
# Installs dependencies and configures environment
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "=== LCSC Automation Framework Setup ==="
echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"

# Check Python version
echo ""
echo "Checking Python version..."
python3 --version

# Create/activate virtual environment (optional)
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "Virtual environment already exists"
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r "$SCRIPT_DIR/requirements.txt"

# Copy configuration template
if [ ! -f "$SCRIPT_DIR/config.yaml" ]; then
    echo ""
    echo "Creating configuration file from template..."
    cp "$SCRIPT_DIR/config.example.yaml" "$SCRIPT_DIR/config.yaml"
    echo "Configuration template created: $SCRIPT_DIR/config.yaml"
    echo "Please edit config.yaml to customize settings"
else
    echo "Configuration file already exists: $SCRIPT_DIR/config.yaml"
fi

# Verify installation
echo ""
echo "Verifying installation..."
python3 -c "from lcsc_automation import __version__; print(f'LCSC Automation v{__version__}')"

# Check for easyeda2kicad
echo ""
echo "Checking for easyeda2kicad..."
if command -v easyeda2kicad &> /dev/null; then
    easyeda2kicad --version
    echo "✓ easyeda2kicad is installed"
else
    echo "✗ easyeda2kicad not found in PATH"
    echo "  Install with: pip install easyeda2kicad"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Quick start:"
echo "  1. Edit config.yaml to customize settings"
echo "  2. Run: python3 lcsc_automation.py --help"
echo "  3. Generate BOM: python3 lcsc_automation.py --generate-bom <schematic.kicad_sch>"
echo ""
echo "Documentation: see README.md"
