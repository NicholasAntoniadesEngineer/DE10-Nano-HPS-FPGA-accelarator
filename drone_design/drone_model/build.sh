#!/usr/bin/env bash
# Build drone 3D model exports (STL, STEP, Gerber)
#
# Usage:
#   ./drone_design/drone_model/build.sh          # build all
#   ./drone_design/drone_model/build.sh stl      # STL + viewer only
#   ./drone_design/drone_model/build.sh step     # STEP export only
#   ./drone_design/drone_model/build.sh gerber   # Gerber/KiCad only

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="$REPO_ROOT/.venv"

if [ ! -f "$VENV/bin/activate" ]; then
    echo "ERROR: Python venv not found at $VENV"
    echo "Create it with:  python3 -m venv .venv && .venv/bin/pip install cadquery"
    exit 1
fi

source "$VENV/bin/activate"

# Set PYTHONPATH so exporters can find cadquery_framework (repo root) and
# components/assembly (drone_model dir)
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/drone_design/drone_model${PYTHONPATH:+:$PYTHONPATH}"

# Verify CadQuery is available
python -c "import cadquery" 2>/dev/null || {
    echo "ERROR: CadQuery not installed in venv"
    echo "Install with:  .venv/bin/pip install cadquery"
    exit 1
}

# Parse arguments
TARGET="${1:-all}"
shift || true
EXTRA_ARGS="$*"

run_target() {
    echo "==> Building $1 exports..."
    python "$REPO_ROOT/drone_design/drone_model/drone_3d_model.py" "$1" $EXTRA_ARGS
}

case "$TARGET" in
    stl)    run_target stl ;;
    step)   run_target step ;;
    gerber) run_target gerber ;;
    all)    run_target all ;;
    *)
        echo "Usage: $0 [all|stl|step|gerber] [--verbose] [--detail=<level>]"
        exit 1
        ;;
esac

echo ""
echo "Done. Outputs:"
echo "  drone_design/drone_model/output/stl/       (STL files)"
echo "  drone_design/drone_model/output/step/      (STEP files)"
echo "  drone_design/drone_model/output/gerber/    (KiCad PCBs)"
echo "  drone_design/drone_model/output/viewer.html (3D viewer)"
