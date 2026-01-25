#!/bin/bash
# Cross-compile HPS (ARM) code for DE10-Nano
#
# Usage: build-hps.sh <directory> [options]
#
# Options:
#   --clean    Clean before building
#   --target   Specify make target (default: all)
#
# Example:
#   build-hps.sh examples/hps_fpga_examples/DE10_NANO_SoC_GHRD/HPS_LED_update

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
CLEAN=false
TARGET="all"

# Parse arguments
BUILD_DIR=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --target)
            TARGET="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: build-hps.sh <directory> [options]"
            echo ""
            echo "Options:"
            echo "  --clean       Clean before building"
            echo "  --target      Specify make target (default: all)"
            exit 0
            ;;
        *)
            if [[ -z "$BUILD_DIR" ]]; then
                BUILD_DIR="$1"
            fi
            shift
            ;;
    esac
done

# Validate input
if [[ -z "$BUILD_DIR" ]]; then
    echo -e "${RED}Error: No directory specified${NC}"
    echo "Usage: build-hps.sh <directory> [options]"
    exit 1
fi

if [[ ! -d "$BUILD_DIR" ]]; then
    echo -e "${RED}Error: Directory not found: $BUILD_DIR${NC}"
    exit 1
fi

# Check for Makefile
if [[ ! -f "$BUILD_DIR/Makefile" ]]; then
    echo -e "${RED}Error: No Makefile found in $BUILD_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}=== HPS Cross-Compilation ===${NC}"
echo "Directory: $BUILD_DIR"
echo "Target: $TARGET"
echo "Cross-compiler: ${CROSS_COMPILE}gcc"
echo ""

# Verify cross-compiler is available
if ! command -v ${CROSS_COMPILE}gcc &> /dev/null; then
    echo -e "${RED}Error: Cross-compiler not found: ${CROSS_COMPILE}gcc${NC}"
    exit 1
fi

# Show compiler version
echo -e "${YELLOW}Compiler version:${NC}"
${CROSS_COMPILE}gcc --version | head -1
echo ""

# Change to build directory
cd "$BUILD_DIR"

# Clean if requested
if [[ "$CLEAN" == true ]]; then
    echo -e "${YELLOW}Cleaning...${NC}"
    make clean 2>/dev/null || true
fi

# Build
echo -e "${YELLOW}Building...${NC}"
make CROSS_COMPILE=${CROSS_COMPILE} "$TARGET"

# List generated binaries
echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
echo "Generated files:"
find . -maxdepth 1 -type f \( -executable -o -name "*.o" -o -name "*.a" -o -name "*.so" \) 2>/dev/null | while read f; do
    if file "$f" | grep -q "ARM"; then
        echo -e "  ${GREEN}[ARM]${NC} $f"
    elif file "$f" | grep -q "ELF"; then
        echo -e "  ${YELLOW}[ELF]${NC} $f"
    else
        echo "  $f"
    fi
done
