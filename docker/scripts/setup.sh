#!/bin/bash
# Quick setup script for DE10-Nano Docker development environment
#
# Usage: ./setup.sh
#
# This script will:
# 1. Check Docker is installed and configured
# 2. Build the development image
# 3. Start the container
# 4. Provide next steps

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       DE10-Nano Docker Development Environment Setup       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${YELLOW}Note: This setup is optimized for macOS. Some steps may differ on other platforms.${NC}"
fi

# Check if running on Apple Silicon
if [[ "$(uname -m)" == "arm64" ]]; then
    echo -e "${YELLOW}Detected Apple Silicon Mac${NC}"
    echo "FPGA builds will run via x86 emulation (~4x slower than native)"
    echo ""
    APPLE_SILICON=true
else
    APPLE_SILICON=false
fi

# Check Docker is installed
echo -e "${BLUE}[1/4] Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo ""
    echo "Please install Docker Desktop from:"
    echo "  https://www.docker.com/products/docker-desktop/"
    echo ""
    exit 1
fi

# Check Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo ""
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed and running${NC}"

# Check docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not available${NC}"
    exit 1
fi

# Check for Rosetta on Apple Silicon
if [[ "$APPLE_SILICON" == true ]]; then
    echo ""
    echo -e "${BLUE}[1.5/4] Checking Rosetta configuration...${NC}"
    echo -e "${YELLOW}For best performance on Apple Silicon:${NC}"
    echo "  1. Open Docker Desktop"
    echo "  2. Go to Settings > Features in development"
    echo "  3. Enable 'Use Rosetta for x86/amd64 emulation'"
    echo "  4. Apply & Restart Docker"
    echo ""
    read -p "Have you enabled Rosetta in Docker Desktop? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Consider enabling Rosetta for 4-5x better emulation performance${NC}"
    fi
fi

# Check disk space
echo ""
echo -e "${BLUE}[2/4] Checking disk space...${NC}"
AVAILABLE_GB=$(df -g . | awk 'NR==2 {print $4}')
if [[ "$AVAILABLE_GB" -lt 30 ]]; then
    echo -e "${RED}Warning: Only ${AVAILABLE_GB}GB available. Recommend 50GB+ for Quartus builds.${NC}"
else
    echo -e "${GREEN}✓ ${AVAILABLE_GB}GB available${NC}"
fi

# Build the image
echo ""
echo -e "${BLUE}[3/4] Building Docker image...${NC}"
echo "This will download ~15GB and may take 20-40 minutes on first run."
echo ""

cd "$(dirname "$0")"

if docker compose version &> /dev/null; then
    docker compose build
else
    docker-compose build
fi

echo -e "${GREEN}✓ Docker image built successfully${NC}"

# Start the container
echo ""
echo -e "${BLUE}[4/4] Starting development container...${NC}"

if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

echo -e "${GREEN}✓ Container started${NC}"

# Success message
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete!                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  ${GREEN}Build everything (FPGA + HPS + SD card image):${NC}"
echo -e "     ${YELLOW}./scripts/docker-build.sh${NC}"
echo ""
echo "  ${GREEN}Or build specific components:${NC}"
echo -e "     ${YELLOW}./scripts/docker-build.sh fpga         ${NC}# FPGA bitstream only"
echo -e "     ${YELLOW}./scripts/docker-build.sh applications ${NC}# HPS apps only"
echo ""
echo "  ${GREEN}Advanced - run any make command:${NC}"
echo -e "     ${YELLOW}./scripts/docker-make.sh help          ${NC}# Show all targets"
echo -e "     ${YELLOW}./scripts/docker-make.sh -C HPS kernel ${NC}# Build kernel only"
echo ""
echo "  ${GREEN}Clean build artifacts:${NC}"
echo -e "     ${YELLOW}./scripts/docker-clean.sh              ${NC}# Clean (keeps kernel source)"
echo -e "     ${YELLOW}./scripts/docker-clean.sh --all        ${NC}# Deep clean"
echo ""
echo -e "${YELLOW}Build times (Apple Silicon via Rosetta):${NC}"
echo "  • FPGA: 30-40 min  • Kernel: 10-15 min  • Rootfs: 15-20 min"
echo "  • Everything: ~60 minutes first time"
echo ""
echo -e "Final outputs: ${BLUE}output/${NC} directory"
echo -e "Documentation: ${BLUE}docker/README.md${NC}"
