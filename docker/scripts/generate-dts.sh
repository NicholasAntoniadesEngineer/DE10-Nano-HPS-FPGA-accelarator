#!/bin/bash
# Generate Device Tree Source from SOPC info
#
# Usage: generate-dts.sh <sopcinfo_file> [output_file]
#
# Example:
#   generate-dts.sh soc_system.sopcinfo soc_system.dts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SOPCINFO_FILE="$1"
OUTPUT_FILE="${2:-$(basename "$SOPCINFO_FILE" .sopcinfo).dts}"

if [[ -z "$SOPCINFO_FILE" ]]; then
    echo "Usage: generate-dts.sh <sopcinfo_file> [output_file]"
    exit 1
fi

if [[ ! -f "$SOPCINFO_FILE" ]]; then
    echo -e "${RED}Error: File not found: $SOPCINFO_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}=== Device Tree Generation ===${NC}"
echo "Input: $SOPCINFO_FILE"
echo "Output: $OUTPUT_FILE"
echo ""

# Check if sopc2dts is available (part of Quartus)
if command -v sopc2dts &> /dev/null; then
    echo -e "${YELLOW}Using sopc2dts...${NC}"
    sopc2dts --input "$SOPCINFO_FILE" --output "$OUTPUT_FILE" --type dts
elif command -v dtc &> /dev/null; then
    echo -e "${YELLOW}Note: sopc2dts not found, using dtc for compilation only${NC}"
    echo "To generate DTS from SOPCINFO, you need sopc2dts from Quartus tools."
    exit 1
else
    echo -e "${RED}Error: Neither sopc2dts nor dtc found${NC}"
    exit 1
fi

echo -e "${GREEN}Device tree source generated: $OUTPUT_FILE${NC}"

# Optionally compile to DTB
read -p "Compile to DTB? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    DTB_FILE="${OUTPUT_FILE%.dts}.dtb"
    echo -e "${YELLOW}Compiling to DTB...${NC}"
    dtc -I dts -O dtb -o "$DTB_FILE" "$OUTPUT_FILE"
    echo -e "${GREEN}Device tree blob generated: $DTB_FILE${NC}"
fi
