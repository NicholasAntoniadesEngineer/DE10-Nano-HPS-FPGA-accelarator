#!/bin/bash
# Build FPGA project using Quartus Prime
#
# Usage: build-fpga.sh <project.qpf> [options]
#
# Options:
#   --flow <flow>     Compilation flow: compile (default), analysis, synthesis
#   --rbf             Also generate RBF file for SD card boot
#   --clean           Clean before building
#
# Example:
#   build-fpga.sh examples/fpga_examples/my_project/my_project.qpf --rbf

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
FLOW="compile"
GENERATE_RBF=false
CLEAN=false

# Parse arguments
QPF_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --flow)
            FLOW="$2"
            shift 2
            ;;
        --rbf)
            GENERATE_RBF=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        -h|--help)
            echo "Usage: build-fpga.sh <project.qpf> [options]"
            echo ""
            echo "Options:"
            echo "  --flow <flow>  Compilation flow: compile, analysis, synthesis"
            echo "  --rbf          Generate RBF file for SD card boot"
            echo "  --clean        Clean before building"
            exit 0
            ;;
        *)
            if [[ -z "$QPF_FILE" ]]; then
                QPF_FILE="$1"
            fi
            shift
            ;;
    esac
done

# Validate input
if [[ -z "$QPF_FILE" ]]; then
    echo -e "${RED}Error: No project file specified${NC}"
    echo "Usage: build-fpga.sh <project.qpf> [options]"
    exit 1
fi

if [[ ! -f "$QPF_FILE" ]]; then
    echo -e "${RED}Error: Project file not found: $QPF_FILE${NC}"
    exit 1
fi

# Get project directory and name
PROJECT_DIR=$(dirname "$QPF_FILE")
PROJECT_NAME=$(basename "$QPF_FILE" .qpf)

echo -e "${GREEN}=== FPGA Build ===${NC}"
echo "Project: $PROJECT_NAME"
echo "Directory: $PROJECT_DIR"
echo "Flow: $FLOW"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Clean if requested
if [[ "$CLEAN" == true ]]; then
    echo -e "${YELLOW}Cleaning project...${NC}"
    rm -rf db/ incremental_db/ output_files/ *.qws
fi

# Run Quartus compilation
echo -e "${YELLOW}Starting Quartus $FLOW...${NC}"
echo "Note: This may take 30-60 minutes on emulated x86"
echo ""

# Use taskset to limit to single core for stability on emulation
if command -v taskset &> /dev/null; then
    taskset 1 quartus_sh --flow "$FLOW" "$PROJECT_NAME"
else
    quartus_sh --flow "$FLOW" "$PROJECT_NAME"
fi

# Check if SOF file was generated
SOF_FILE="output_files/${PROJECT_NAME}.sof"
if [[ -f "$SOF_FILE" ]]; then
    echo -e "${GREEN}SOF file generated: $SOF_FILE${NC}"

    # Generate RBF if requested
    if [[ "$GENERATE_RBF" == true ]]; then
        echo -e "${YELLOW}Generating RBF file...${NC}"
        RBF_FILE="output_files/${PROJECT_NAME}.rbf"
        quartus_cpf -c "$SOF_FILE" "$RBF_FILE"
        echo -e "${GREEN}RBF file generated: $RBF_FILE${NC}"
    fi
else
    echo -e "${YELLOW}Note: SOF file not found (may be expected for analysis flow)${NC}"
fi

echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
