#!/bin/bash
# ============================================================================
# Docker Make Wrapper Script
# ============================================================================
# Convenient wrapper to run make commands inside the Docker container
#
# Usage:
#   ./docker-make.sh [make arguments]
#
# Examples:
#   ./docker-make.sh clean              # Clean all build artifacts
#   ./docker-make.sh everything         # Build everything (FPGA + HPS)
#   ./docker-make.sh -C FPGA sof        # Build FPGA bitstream
#   ./docker-make.sh -C HPS all         # Build HPS software only
#   ./docker-make.sh help               # Show make help
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

CONTAINER_NAME="de10-nano-dev"
COMPOSE_FILE="docker-compose.yml"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Container '${CONTAINER_NAME}' does not exist${NC}"
    echo "Run './setup.sh' to create the container first"
    exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Container '${CONTAINER_NAME}' is not running. Starting it...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d

    # Wait for container to be ready
    sleep 2
    echo -e "${GREEN}Container started${NC}"
fi

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    echo -e "${CYAN}Docker Make Wrapper${NC}"
    echo ""
    echo "Usage: $0 [make arguments]"
    echo ""
    echo "Common commands:"
    echo "  $0 clean              - Clean all build artifacts"
    echo "  $0 clean-all          - Deep clean (removes kernel source)"
    echo "  $0 everything         - Build everything (FPGA + HPS)"
    echo "  $0 -C FPGA sof        - Build FPGA bitstream"
    echo "  $0 -C HPS all         - Build HPS software"
    echo "  $0 -C HPS kernel      - Build Linux kernel only"
    echo "  $0 help               - Show detailed make help"
    echo ""
    echo "Running 'make help' in container:"
    docker exec "$CONTAINER_NAME" bash -c "cd /workspace && make help"
    exit 0
fi

# Determine the working directory based on -C argument
WORK_DIR="/workspace"
for arg in "$@"; do
    if [[ "$arg" == "-C" ]]; then
        # Next argument will be the directory
        continue
    elif [[ "$arg" =~ ^(FPGA|HPS)$ ]]; then
        WORK_DIR="/workspace/$arg"
        # Remove -C and directory from arguments we'll pass
        NEW_ARGS=()
        SKIP_NEXT=false
        for a in "$@"; do
            if [ "$SKIP_NEXT" = true ]; then
                SKIP_NEXT=false
                continue
            fi
            if [ "$a" = "-C" ]; then
                SKIP_NEXT=true
                continue
            fi
            NEW_ARGS+=("$a")
        done
        set -- "${NEW_ARGS[@]}"
        break
    fi
done

echo -e "${CYAN}Running: make $*${NC}"
echo -e "${CYAN}In container: $CONTAINER_NAME${NC}"
echo -e "${CYAN}Directory: $WORK_DIR${NC}"
echo ""

# Run make command in container
# Using 'script' to preserve colors if running interactively
if [ -t 1 ]; then
    # Interactive terminal - preserve colors
    docker exec -it "$CONTAINER_NAME" bash -c "cd $WORK_DIR && make $*"
else
    # Non-interactive - don't allocate tty
    docker exec "$CONTAINER_NAME" bash -c "cd $WORK_DIR && make $*"
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Command completed successfully${NC}"
else
    echo ""
    echo -e "${RED}✗ Command failed with exit code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
