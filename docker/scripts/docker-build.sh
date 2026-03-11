#!/bin/bash
# ============================================================================
# Docker Build Script
# ============================================================================
# Convenience script to build the complete DE10-Nano system in Docker
#
# Usage:
#   ./docker-build.sh              # Build everything (FPGA + HPS)
#   ./docker-build.sh fpga         # Build FPGA only
#   ./docker-build.sh hps          # Build HPS only
#   ./docker-build.sh kernel       # Build kernel only
#   ./docker-build.sh applications # Build applications only
# ============================================================================

set -e

# Colors
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure Git LFS files are present (kernel, bootloader) before building
if command -v git &> /dev/null && git -C "$SCRIPT_DIR/../.." lfs version &> /dev/null 2>&1; then
    echo -e "${CYAN}Pulling Git LFS files (kernel, bootloader binaries)...${NC}"
    git -C "$SCRIPT_DIR/../.." lfs pull
    echo -e "${GREEN}✓ Git LFS files up-to-date${NC}"
fi

case "$1" in
    fpga)
        echo -e "${CYAN}Building FPGA bitstream...${NC}"
        exec "$SCRIPT_DIR/docker-make.sh" -C FPGA sof
        ;;
    hps)
        echo -e "${CYAN}Building HPS software...${NC}"
        exec "$SCRIPT_DIR/docker-make.sh" -C HPS all
        ;;
    kernel)
        echo -e "${CYAN}Building Linux kernel...${NC}"
        exec "$SCRIPT_DIR/docker-make.sh" -C HPS kernel
        ;;
    applications|apps)
        echo -e "${CYAN}Building HPS applications...${NC}"
        exec "$SCRIPT_DIR/docker-make.sh" -C HPS applications
        ;;
    "")
        echo -e "${CYAN}Building everything (FPGA + HPS)...${NC}"
        echo -e "${YELLOW}This will take 30-60 minutes on Apple Silicon (Rosetta 2)${NC}"
        echo ""
        exec "$SCRIPT_DIR/docker-make.sh" everything
        ;;
    *)
        echo "Usage: $0 [target]"
        echo ""
        echo "Targets:"
        echo "  (none)       - Build everything (FPGA + HPS)"
        echo "  fpga         - Build FPGA bitstream only"
        echo "  hps          - Build HPS software only"
        echo "  kernel       - Build Linux kernel only"
        echo "  applications - Build applications only"
        echo ""
        echo "For more options, use: $SCRIPT_DIR/docker-make.sh help"
        exit 1
        ;;
esac
