#!/bin/bash
# Helper script to find SoC EDS installation

echo "Searching for SoC EDS installation..."
echo ""

# Common installation locations
SEARCH_PATHS=(
    "/c/intelFPGA"
    "/c/altera"
    "/c/Program Files/intelFPGA"
    "/c/Program Files/altera"
    "$HOME/intelFPGA"
    "$HOME/altera"
)

FOUND=0

for base_path in "${SEARCH_PATHS[@]}"; do
    if [ -d "$base_path" ]; then
        echo "Checking $base_path..."
        # Find embedded directories
        find "$base_path" -type d -name "embedded" 2>/dev/null | while read embedded_dir; do
            # Check if it contains version.txt
            if [ -f "$embedded_dir/version.txt" ]; then
                echo ""
                echo "Found SoC EDS installation: $embedded_dir"
                echo ""
                echo "To use this installation, run:"
                echo "  export SOCEDS_DEST_ROOT=\"$embedded_dir\""
                
                # Check for bsp-create-settings in common locations
                if [ -f "$embedded_dir/host_tools/bin/bsp-create-settings" ]; then
                    echo "  export PATH=\"\$SOCEDS_DEST_ROOT/host_tools/bin:\$PATH\""
                    echo ""
                    echo "Tool found at: $embedded_dir/host_tools/bin/bsp-create-settings"
                elif [ -f "$embedded_dir/bin/bsp-create-settings" ]; then
                    echo "  export PATH=\"\$SOCEDS_DEST_ROOT/bin:\$PATH\""
                    echo ""
                    echo "Tool found at: $embedded_dir/bin/bsp-create-settings"
                else
                    echo ""
                    echo "WARNING: bsp-create-settings not found in expected locations"
                    echo "Searching for bsp-create-settings..."
                    find "$embedded_dir" -name "bsp-create-settings*" 2>/dev/null | head -3
                fi
                echo ""
                FOUND=1
            fi
        done
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "SoC EDS installation not found in common locations."
    echo ""
    echo "Please:"
    echo "1. Install Intel SoC EDS (Embedded Design Suite)"
    echo "2. Or manually set SOCEDS_DEST_ROOT to your installation directory"
    echo ""
    echo "You can also search manually:"
    echo "  find /c -name 'bsp-create-settings*' 2>/dev/null"
fi
