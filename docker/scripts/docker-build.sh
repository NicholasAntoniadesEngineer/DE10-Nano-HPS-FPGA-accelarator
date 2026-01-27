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
NC='\033[0m'

case "$1" in
    fpga)
        echo -e "${CYAN}Building FPGA bitstream...${NC}"
        exec ./docker-make.sh -C FPGA sof
        ;;
    hps)
        echo -e "${CYAN}Building HPS software...${NC}"
        exec ./docker-make.sh -C HPS all
        ;;
    kernel)
        echo -e "${CYAN}Building Linux kernel...${NC}"
        exec ./docker-make.sh -C HPS kernel
        ;;
    applications|apps)
        echo -e "${CYAN}Building HPS applications...${NC}"
        exec ./docker-make.sh -C HPS applications
        ;;
    "")
        echo -e "${CYAN}Building everything (FPGA + HPS)...${NC}"
        echo -e "${YELLOW}This will take 30-60 minutes on Apple Silicon (Rosetta 2)${NC}"
        echo ""
        exec ./docker-make.sh everything
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
        echo "For more options, use: ./docker-make.sh help"
        exit 1
        ;;
esac
