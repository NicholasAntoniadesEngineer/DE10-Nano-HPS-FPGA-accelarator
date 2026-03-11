#!/usr/bin/env bash
# ============================================================================
# generate-app-framework.sh — Scaffold a new HPS application
# ============================================================================
# Usage: ./scripts/generate-app-framework.sh <app_name> [--no-service]
#
# Creates:
#   HPS/applications/<app_name>/          — C source, Makefile, service file
#
# After running, implement your logic in:
#   HPS/applications/<app_name>/<app_name>.c
#
# Then create the rootfs install script:
#   HPS/linux_image/rootfs/scripts/install_<app_name>.sh
# ============================================================================

set -euo pipefail

# ============================================================================
# Parse arguments
# ============================================================================
SKIP_SERVICE=false
APP_NAME=""

for arg in "$@"; do
    case "$arg" in
        --no-service)
            SKIP_SERVICE=true
            ;;
        --help|-h)
            echo "Usage: $0 <app_name> [--no-service]"
            echo ""
            echo "Scaffolds a new HPS application with a C source skeleton, Makefile,"
            echo "and an optional systemd service file."
            echo ""
            echo "Options:"
            echo "  --no-service  Skip creating the .service file"
            echo "  --help        Show this help"
            exit 0
            ;;
        -*)
            echo "Error: unknown option '$arg'" >&2
            exit 1
            ;;
        *)
            if [ -n "$APP_NAME" ]; then
                echo "Error: multiple app names given ('$APP_NAME' and '$arg')" >&2
                exit 1
            fi
            APP_NAME="$arg"
            ;;
    esac
done

if [ -z "$APP_NAME" ]; then
    echo "Error: app name required" >&2
    echo "Usage: $0 <app_name> [--no-service]" >&2
    exit 1
fi

# Validate name: lowercase alphanumeric + underscores only, must start with a letter
if ! echo "$APP_NAME" | grep -qE '^[a-z][a-z0-9_]*$'; then
    echo "Error: app name must be lowercase alphanumeric with underscores (e.g., my_sensor_app)" >&2
    exit 1
fi

# ============================================================================
# Resolve paths
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

HPS_DIR="$PROJECT_ROOT/HPS"
TEMPLATE_DIR="$HPS_DIR/applications/template"
APP_DIR="$HPS_DIR/applications/$APP_NAME"

# Uppercase version for C macros (e.g., my_app -> MY_APP)
APP_UPPER=$(echo "$APP_NAME" | tr '[:lower:]' '[:upper:]')

# Hyphenated version for service filename (e.g., my_app -> my-app.service)
APP_HYPHEN=$(echo "$APP_NAME" | tr '_' '-')

# ============================================================================
# Pre-flight checks
# ============================================================================
if [ -d "$APP_DIR" ]; then
    echo "Error: $APP_DIR already exists" >&2
    exit 1
fi

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "Error: application template not found at $TEMPLATE_DIR" >&2
    exit 1
fi

# ============================================================================
# Copy and rename application template
# ============================================================================
echo "Creating HPS application: $APP_DIR"
cp -r "$TEMPLATE_DIR" "$APP_DIR"

cd "$APP_DIR"

# Rename template.c -> <app_name>.c
[ -f "template.c" ] && mv "template.c" "${APP_NAME}.c"

# Rename template.service -> <app_name_hyphen>.service
[ -f "template.service" ] && mv "template.service" "${APP_HYPHEN}.service"

# Substitute content in all relevant files
for f in *.c *.h Makefile *.service; do
    [ -f "$f" ] || continue
    sed -i.bak "s/template/${APP_NAME}/g"   "$f"
    sed -i.bak "s/TEMPLATE/${APP_UPPER}/g"  "$f"
    rm -f "$f.bak"
done

# Fix the service Description and ExecStart to use the hyphenated name where appropriate
SERVICE_FILE="${APP_HYPHEN}.service"
if [ -f "$SERVICE_FILE" ]; then
    # Update Description line to use the app name
    sed -i.bak "s/Description=${APP_NAME} - HPS Application/Description=${APP_NAME} - HPS Application/" "$SERVICE_FILE"
    # ExecStart path already updated by the template substitution above
    rm -f "$SERVICE_FILE.bak"
fi

# Remove service file if --no-service was passed
if [ "$SKIP_SERVICE" = true ]; then
    rm -f "$SERVICE_FILE"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "============================================"
echo "  Scaffold complete: ${APP_NAME}"
echo "============================================"
echo ""
echo "Files created:"
echo "  HPS/applications/${APP_NAME}/"
for f in "$APP_DIR"/*; do
    echo "    $(basename "$f")"
done
echo ""
echo "Next steps:"
echo "  1. Implement logic in:"
echo "       HPS/applications/${APP_NAME}/${APP_NAME}.c"
echo ""
echo "  2. Create rootfs install script:"
echo "       HPS/linux_image/rootfs/scripts/install_${APP_NAME}.sh"
echo "     (see install_calculator_demo.sh for reference)"
echo ""
echo "  3. Build:"
echo "       docker/scripts/docker-make.sh -C HPS applications"
if [ ! "$SKIP_SERVICE" = true ]; then
    echo ""
    echo "  4. Enable service by:"
    echo "     a. Calling install from install_${APP_NAME}.sh"
    echo "     b. Adding ${APP_HYPHEN}.service to"
    echo "          HPS/linux_image/rootfs/scripts/setup_services.sh"
fi
echo ""
