#!/bin/bash
# ============================================================================
# Docker Clean Script
# ============================================================================
# Convenience script to clean all build artifacts in Docker container
#
# Usage:
#   ./docker-clean.sh           # Clean build artifacts (keeps kernel source)
#   ./docker-clean.sh --all     # Deep clean (removes kernel source too)
# ============================================================================

set -e

# Check for --all flag
if [ "$1" = "--all" ] || [ "$1" = "-a" ]; then
    echo "Running deep clean (removes kernel source)..."
    exec ./docker-make.sh clean-all
else
    echo "Running clean (keeps kernel source)..."
    echo "Use './docker-clean.sh --all' for deep clean"
    echo ""
    exec ./docker-make.sh clean
fi
