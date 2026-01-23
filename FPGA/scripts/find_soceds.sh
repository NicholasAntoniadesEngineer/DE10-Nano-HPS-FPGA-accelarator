#!/bin/bash
# ============================================================================
# Find Intel SoC EDS installation (WSL/Windows-friendly)
# ============================================================================
# This script tries to locate an Intel SoC EDS install by looking for:
#   - embedded_command_shell.sh
#   - bsp-create-settings(.exe)
#
# It prints a recommended SOCEDS_DEST_ROOT export and how to source the shell.
# ============================================================================

set -euo pipefail

print_error() {
    echo "ERROR: $1" >&2
}

print_info() {
    echo "$1" >&2
}

print_usage() {
    cat <<'EOF' >&2
Usage:
  ./scripts/find_soceds.sh

What it does:
  - Searches common Windows/WSL install roots for an Intel SoC EDS "embedded" folder
  - Prints the recommended SOCEDS_DEST_ROOT and how to source embedded_command_shell.sh

Notes:
  - If you installed SoC EDS on Windows, WSL usually sees it under /mnt/c/...
EOF
}

find_first_existing_file() {
    local -a candidate_paths=("$@")
    local candidate_path=""

    for candidate_path in "${candidate_paths[@]}"; do
        if [ -f "$candidate_path" ]; then
            echo "$candidate_path"
            return 0
        fi
    done

    return 1
}

main() {
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        print_usage
        exit 0
    fi

    # Use limited globbing patterns (avoid recursive filesystem walks on /mnt/c).
    # Typical Windows installs:
    #   C:\intelFPGA\20.1\embedded
    #   C:\intelFPGA_lite\20.1\embedded
    #   C:\intelFPGA_pro\20.1\embedded
    shopt -s nullglob

    local -a embedded_shell_candidates=()
    local -a possible_roots=(
        /mnt/c/intelFPGA
        /mnt/c/intelFPGA_lite
        /mnt/c/intelFPGA_pro
        /mnt/c/intelFPGA_standard
        /mnt/c/intelFPGA_premium
        /mnt/c/IntelFPGA
        /mnt/c/IntelFPGA_lite
        /mnt/c/IntelFPGA_pro
        /mnt/c/IntelFPGA_standard
        /mnt/c/IntelFPGA_premium
        /c/intelFPGA
        /c/intelFPGA_lite
        /c/intelFPGA_pro
        /c/intelFPGA_standard
        /c/intelFPGA_premium
        /c/IntelFPGA
        /c/IntelFPGA_lite
        /c/IntelFPGA_pro
        /c/IntelFPGA_standard
        /c/IntelFPGA_premium
    )

    local install_root=""
    for install_root in "${possible_roots[@]}"; do
        if [ -d "$install_root" ]; then
            # Match version directories under the install root.
            # Examples: 20.1, 21.1, 22.1, 23.1, etc.
            local version_dir=""
            for version_dir in "$install_root"/*; do
                if [ -d "$version_dir/embedded" ] && [ -f "$version_dir/embedded/embedded_command_shell.sh" ]; then
                    embedded_shell_candidates+=("$version_dir/embedded/embedded_command_shell.sh")
                fi
            done
        fi
    done

    local embedded_shell_path=""
    if embedded_shell_path="$(find_first_existing_file "${embedded_shell_candidates[@]}")"; then
        local soceds_dest_root=""
        soceds_dest_root="$(cd "$(dirname "$embedded_shell_path")" && pwd)"

        print_info "Found SoC EDS embedded command shell:"
        print_info "  $embedded_shell_path"
        print_info ""
        print_info "Use these commands in WSL before running FPGA HPS-software targets:"
        print_info "  export SOCEDS_DEST_ROOT=\"$soceds_dest_root\""
        print_info "  source \"$soceds_dest_root/embedded_command_shell.sh\""
        print_info ""
        print_info "Then run:"
        print_info "  cd FPGA && make preloader uboot dtb"
        exit 0
    fi

    print_error "Could not find an SoC EDS installation under common locations."
    print_error "Install Intel SoC EDS (separate from Quartus Lite), then rerun this script."
    print_error "If you know your install path, set SOCEDS_DEST_ROOT to the 'embedded' directory."
    exit 1
}

main "$@"

