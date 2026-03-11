#!/bin/bash
# ============================================================================
# Internet Connectivity Check Helper
# ============================================================================
# Used by Makefiles/scripts to detect and wait for connectivity before
# performing network-dependent actions (git clone/fetch, apt-get, debootstrap).
# ============================================================================

set -euo pipefail

print_banner() {
    local banner_title="$1"

    local green_color='\033[0;32m'
    local reset_color='\033[0m'
    echo -e "${green_color}===========================================${reset_color}" >&2
    echo -e "${green_color}${banner_title}${reset_color}" >&2
    echo -e "${green_color}===========================================${reset_color}" >&2
}

print_message() {
    local message_color="$1"
    local message_text="$2"

    local reset_color='\033[0m'
    echo -e "${message_color}${message_text}${reset_color}" >&2
}

print_warning() {
    local warning_text="$1"
    print_message '\033[1;33m' "WARNING: ${warning_text}"
}

print_error() {
    local error_text="$1"
    print_message '\033[0;31m' "ERROR: ${error_text}"
}

print_info() {
    local info_text="$1"
    print_message '\033[0;32m' "${info_text}"
}

command_exists() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1
}

url_reachable() {
    local url_to_check="$1"
    local host_name=""
    local port_number=""

    if command_exists curl; then
        curl -fsI --max-time 10 "$url_to_check" >/dev/null 2>&1
        return $?
    fi

    if command_exists wget; then
        wget -q --spider --timeout=10 --tries=1 "$url_to_check" >/dev/null 2>&1
        return $?
    fi

    if [[ "$url_to_check" == https://* ]]; then
        port_number="443"
    elif [[ "$url_to_check" == http://* ]]; then
        port_number="80"
    else
        return 1
    fi

    host_name="${url_to_check#*://}"
    host_name="${host_name%%/*}"

    if [[ "$host_name" == *:* ]]; then
        port_number="${host_name##*:}"
        host_name="${host_name%%:*}"
    fi

    if [ -z "$host_name" ] || [ -z "$port_number" ]; then
        return 1
    fi

    if command_exists timeout; then
        timeout 5 bash -c "cat < /dev/null > /dev/tcp/${host_name}/${port_number}" >/dev/null 2>&1
        return $?
    fi

    return 1
}

wait_for_internet() {
    local requirement_name="$1"
    local retry_sleep_seconds="$2"
    shift 2

    local urls_to_check=("$@")
    if [ ${#urls_to_check[@]} -eq 0 ]; then
        print_error "No URLs provided to internet check"
        return 1
    fi

    if ! command_exists curl && ! command_exists wget && ! command_exists timeout; then
        print_error "Internet checks require one of: curl, wget, or timeout (for /dev/tcp checks)"
        print_error "Install with: sudo apt-get install -y curl (or wget)"
        return 1
    fi

    print_banner "Internet Check: ${requirement_name}"

    local attempt_count=0
    while true; do
        attempt_count=$((attempt_count + 1))

        for url_to_check in "${urls_to_check[@]}"; do
            if url_reachable "$url_to_check"; then
                print_info "Internet OK for ${requirement_name} (reachable: ${url_to_check})"
                return 0
            fi
        done

        print_warning "No internet connectivity for ${requirement_name}. Waiting for reconnect..."
        print_warning "Checked: ${urls_to_check[*]}"
        print_warning "Retrying in ${retry_sleep_seconds}s (attempt ${attempt_count}). Press Ctrl+C to abort."
        sleep "$retry_sleep_seconds"
    done
}

usage() {
    cat <<'EOF' >&2
Usage:
  check_internet.sh --name "<what>" --url "<url>" [--url "<url>"] [--sleep <seconds>]

Examples:
  ./check_internet.sh --name "Debian mirrors (apt/debootstrap)" --url "https://deb.debian.org" --url "https://security.debian.org"
  ./check_internet.sh --name "Kernel repo (git)" --url "https://github.com"
EOF
}

main() {
    local requirement_name=""
    local retry_sleep_seconds="5"
    local urls_to_check=()

    while [ $# -gt 0 ]; do
        case "$1" in
            --name)
                requirement_name="${2:-}"
                shift 2
                ;;
            --url)
                urls_to_check+=("${2:-}")
                shift 2
                ;;
            --sleep)
                retry_sleep_seconds="${2:-}"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown argument: $1"
                usage
                exit 1
                ;;
        esac
    done

    if [ -z "$requirement_name" ]; then
        print_error "--name is required"
        usage
        exit 1
    fi

    if [ ${#urls_to_check[@]} -eq 0 ]; then
        print_error "At least one --url is required"
        usage
        exit 1
    fi

    if ! [[ "$retry_sleep_seconds" =~ ^[0-9]+$ ]] || [ "$retry_sleep_seconds" -lt 1 ]; then
        print_error "--sleep must be a positive integer number of seconds"
        exit 1
    fi

    wait_for_internet "$requirement_name" "$retry_sleep_seconds" "${urls_to_check[@]}"
}

main "$@"
