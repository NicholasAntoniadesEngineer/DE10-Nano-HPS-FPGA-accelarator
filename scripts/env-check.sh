#!/usr/bin/env bash
# ============================================================================
# env-check.sh — Validate the DE10-Nano HPS-FPGA development environment
# ============================================================================
# Usage: ./scripts/env-check.sh [--fix] [--help]
#
# Checks:
#   1. Docker installed
#   2. Docker daemon running
#   3. Docker build image (de10-nano-dev) present
#   4. Git LFS installed
#   5. Git LFS objects fetched (no pending downloads)
#   6. Disk space (warn < 15 GB, error < 5 GB)
#   7. Network reachability (Debian mirror)
#   8. Kernel source cloned (linux-socfpga submodule)
#   9. HPS application binaries built
#
# Exit codes:
#   0  all checks passed or only warnings
#   1  one or more errors (will block build)
# ============================================================================

# ============================================================================
# Argument parsing
# ============================================================================
FIX_MODE=false

for arg in "$@"; do
    case "$arg" in
        --fix)
            FIX_MODE=true
            ;;
        --help|-h)
            echo "Usage: $0 [--fix] [--help]"
            echo ""
            echo "Validates the DE10-Nano HPS-FPGA development environment."
            echo ""
            echo "Options:"
            echo "  --fix   Attempt auto-remediation where safe (e.g., git lfs pull)"
            echo "  --help  Show this help and exit"
            echo ""
            echo "Exit codes:"
            echo "  0  All checks passed (OK or WARN only)"
            echo "  1  One or more errors that will block a build"
            exit 0
            ;;
        *)
            echo "Error: unknown option '$arg'" >&2
            echo "Run '$0 --help' for usage." >&2
            exit 1
            ;;
    esac
done

# ============================================================================
# Resolve paths
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ============================================================================
# Output helpers
# ============================================================================
# Detect whether the terminal supports unicode
_unicode_ok() {
    local lc="${LC_ALL:-${LC_CTYPE:-${LANG:-}}}"
    case "$lc" in
        *UTF-8*|*utf-8*|*utf8*) return 0 ;;
    esac
    # Also check TERM and stdout characteristics on macOS
    if [ -t 1 ] && locale 2>/dev/null | grep -qi 'utf'; then
        return 0
    fi
    return 1
}

if _unicode_ok; then
    SYM_OK="✓"
    SYM_WARN="!"
    SYM_FAIL="✗"
else
    SYM_OK="OK  "
    SYM_WARN="WARN"
    SYM_FAIL="FAIL"
fi

# ANSI colours (disabled automatically if not a tty)
if [ -t 1 ]; then
    C_GREEN='\033[0;32m'
    C_YELLOW='\033[1;33m'
    C_RED='\033[0;31m'
    C_RESET='\033[0m'
else
    C_GREEN=''
    C_YELLOW=''
    C_RED=''
    C_RESET=''
fi

WARN_COUNT=0
ERR_COUNT=0

# print_result <status> <label> <detail>
#   status: ok | warn | error
print_result() {
    local status="$1"
    local label="$2"
    local detail="${3:-}"

    # Pad label to 24 characters for column alignment
    local padded
    padded="$(printf '%-24s' "$label")"

    case "$status" in
        ok)
            printf "  ${C_GREEN}%s${C_RESET}  %s  %s\n" "$SYM_OK" "$padded" "$detail"
            ;;
        warn)
            WARN_COUNT=$(( WARN_COUNT + 1 ))
            printf "  ${C_YELLOW}%s${C_RESET}  %s  ${C_YELLOW}%s${C_RESET}\n" "$SYM_WARN" "$padded" "$detail"
            ;;
        error)
            ERR_COUNT=$(( ERR_COUNT + 1 ))
            printf "  ${C_RED}%s${C_RESET}  %s  ${C_RED}%s${C_RESET}\n" "$SYM_FAIL" "$padded" "$detail"
            ;;
    esac
}

# ============================================================================
# Individual checks
# ============================================================================

check_docker_installed() {
    local label="Docker installed:"
    if ! command -v docker > /dev/null 2>&1; then
        print_result error "$label" "not found — install Docker Desktop from https://www.docker.com/products/docker-desktop/"
        return
    fi
    local ver
    ver="$(docker --version 2>/dev/null | sed 's/Docker version //' | sed 's/,.*//')"
    print_result ok "$label" "docker $ver"
}

check_docker_running() {
    local label="Docker running:"
    if ! command -v docker > /dev/null 2>&1; then
        print_result error "$label" "skipped (Docker not installed)"
        return
    fi
    if ! docker info > /dev/null 2>&1; then
        print_result error "$label" "daemon not responding — start Docker Desktop"
        return
    fi
    print_result ok "$label" ""
}

check_docker_image() {
    local label="Docker image (dev):"
    if ! command -v docker > /dev/null 2>&1; then
        print_result warn "$label" "skipped (Docker not installed)"
        return
    fi
    if ! docker info > /dev/null 2>&1; then
        print_result warn "$label" "skipped (Docker not running)"
        return
    fi
    if docker image inspect de10-nano-dev > /dev/null 2>&1; then
        print_result ok "$label" "de10-nano-dev"
    else
        local msg="de10-nano-dev not found"
        if [ "$FIX_MODE" = true ]; then
            msg="$msg — run: cd docker && ./scripts/setup.sh"
        else
            msg="$msg — run: cd docker && ./scripts/setup.sh  (or use --fix)"
        fi
        print_result warn "$label" "$msg"
    fi
}

check_git_lfs_installed() {
    local label="Git LFS installed:"
    if git lfs version > /dev/null 2>&1; then
        local ver
        ver="$(git lfs version 2>/dev/null | sed 's/git-lfs\///' | awk '{print $1}')"
        print_result ok "$label" "git-lfs/$ver"
    else
        print_result warn "$label" "not found — install with: brew install git-lfs"
    fi
}

check_git_lfs_objects() {
    local label="Git LFS objects:"
    if ! git lfs version > /dev/null 2>&1; then
        print_result warn "$label" "skipped (Git LFS not installed)"
        return
    fi

    # Check for any pending downloads via dry-run
    local dry_output
    dry_output="$(cd "$PROJECT_ROOT" && git lfs pull --dry-run 2>&1)" || true

    if echo "$dry_output" | grep -q 'download'; then
        if [ "$FIX_MODE" = true ]; then
            printf "  ${C_YELLOW}!${C_RESET}  %-24s  ${C_YELLOW}%s${C_RESET}\n" "$label" "fetching LFS objects..."
            if (cd "$PROJECT_ROOT" && git lfs pull 2>&1); then
                print_result ok "$label" "fetched successfully"
            else
                print_result warn "$label" "git lfs pull failed — retry manually"
            fi
        else
            print_result warn "$label" "objects pending download — run: git lfs pull  (or use --fix)"
        fi
    else
        print_result ok "$label" ""
    fi
}

check_disk_space() {
    local label="Disk space:"
    local avail_gb

    # macOS uses -g; GNU coreutils uses -BG (fallback)
    if df -g . > /dev/null 2>&1; then
        avail_gb="$(df -g "$PROJECT_ROOT" 2>/dev/null | awk 'NR==2 {print $4}')"
    else
        avail_gb="$(df -BG "$PROJECT_ROOT" 2>/dev/null | awk 'NR==2 {gsub(/G/,"",$4); print $4}')"
    fi

    if [ -z "$avail_gb" ]; then
        print_result warn "$label" "could not determine disk space"
        return
    fi

    if [ "$avail_gb" -lt 5 ]; then
        print_result error "$label" "${avail_gb} GB free — need at least 5 GB to build (15 GB recommended)"
    elif [ "$avail_gb" -lt 15 ]; then
        print_result warn "$label" "${avail_gb} GB free — 15 GB recommended (full build ~23 min needs headroom)"
    else
        print_result ok "$label" "${avail_gb} GB free"
    fi
}

check_network() {
    local label="Network (Debian):"
    if curl -s --max-time 5 https://deb.debian.org/debian/dists/stable/Release -o /dev/null 2>/dev/null; then
        print_result ok "$label" ""
    else
        print_result warn "$label" "deb.debian.org unreachable — rootfs build may fail"
    fi
}

check_kernel_source() {
    local label="Kernel source:"
    local kernel_dir="$PROJECT_ROOT/HPS/linux_image/kernel/linux-socfpga"

    if [ -d "$kernel_dir/.git" ]; then
        # Try to extract the checked-out branch/tag name
        local branch
        branch="$(git -C "$kernel_dir" symbolic-ref --short HEAD 2>/dev/null || git -C "$kernel_dir" describe --tags --always 2>/dev/null || echo "unknown")"
        print_result ok "$label" "linux-socfpga ($branch)"
    else
        print_result warn "$label" "not cloned — run: git submodule update --init HPS/linux_image/kernel/linux-socfpga"
    fi
}

check_app_binaries() {
    local label="App binaries:"
    local apps=("calculator_demo" "boot_led" "calculator_test")
    local missing=()

    for app in "${apps[@]}"; do
        local bin="$PROJECT_ROOT/HPS/applications/$app/$app"
        if [ ! -f "$bin" ]; then
            missing+=("$app")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        print_result ok "$label" "all present (${#apps[@]}/${#apps[@]})"
    else
        local names
        names="$(printf '%s, ' "${missing[@]}" | sed 's/, $//')"
        local built=$(( ${#apps[@]} - ${#missing[@]} ))
        print_result warn "$label" "${built}/${#apps[@]} built — missing: $names"
        printf "                             ${C_YELLOW}run: docker/scripts/docker-make.sh -C HPS applications${C_RESET}\n"
    fi
}

# ============================================================================
# Main
# ============================================================================
echo ""
echo "Checking DE10-Nano build environment..."
echo ""

check_docker_installed
check_docker_running
check_docker_image
check_git_lfs_installed
check_git_lfs_objects
check_disk_space
check_network
check_kernel_source
check_app_binaries

echo ""

# Summary line
if [ "$ERR_COUNT" -eq 0 ] && [ "$WARN_COUNT" -eq 0 ]; then
    printf "  ${C_GREEN}All checks passed.${C_RESET}\n"
elif [ "$ERR_COUNT" -eq 0 ]; then
    printf "  ${C_YELLOW}%d warning(s), 0 error(s)${C_RESET}\n" "$WARN_COUNT"
else
    printf "  ${C_YELLOW}%d warning(s)${C_RESET}, ${C_RED}%d error(s)${C_RESET}\n" "$WARN_COUNT" "$ERR_COUNT"
fi

echo ""

# Exit non-zero only if there are errors (errors block the build; warnings do not)
if [ "$ERR_COUNT" -gt 0 ]; then
    exit 1
fi
exit 0
