#!/bin/bash
#
# Convenient wrapper for LCSC automation framework
# Usage: ./scripts/lcsc-automation.sh [arguments]
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AUTOMATION_DIR="$PROJECT_ROOT/HPS/tools/lcsc-automation"

# Check if automation framework exists
if [ ! -d "$AUTOMATION_DIR" ]; then
    echo "Error: LCSC automation framework not found at $AUTOMATION_DIR"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Setup Python path
export PYTHONPATH="$AUTOMATION_DIR:$PYTHONPATH"

# Change to automation directory and run
cd "$AUTOMATION_DIR"
python3 lcsc_automation.py "$@"
