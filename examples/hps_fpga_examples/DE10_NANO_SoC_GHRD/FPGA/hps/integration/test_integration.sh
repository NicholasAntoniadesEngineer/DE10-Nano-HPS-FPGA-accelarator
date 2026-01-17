#!/bin/bash
# ============================================================================
# Linux Integration Test Suite
# ============================================================================
# Tests the calculator driver integration into Linux kernel
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FPGA_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DRIVER_SRC="$FPGA_ROOT/hps/calculator_test"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# Test Functions
# ============================================================================

test_file_exists() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file (NOT FOUND)"
        ((TESTS_FAILED++))
        return 1
    fi
}

test_compiles() {
    local source="$1"
    local description="$2"
    local temp_dir=$(mktemp -d)
    
    echo "  Compiling $source..."
    if gcc -c "$source" -o "$temp_dir/test.o" -I"$DRIVER_SRC" 2>&1 | tee "$temp_dir/compile.log"; then
        echo -e "${GREEN}✓${NC} $description: compiles successfully"
        rm -rf "$temp_dir"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description: compilation failed"
        cat "$temp_dir/compile.log"
        rm -rf "$temp_dir"
        ((TESTS_FAILED++))
        return 1
    fi
}

test_library_builds() {
    local target_dir="$1"
    local description="$2"
    
    if [[ ! -d "$target_dir" ]]; then
        echo -e "${YELLOW}⚠${NC} $description: target directory not found, skipping"
        return 0
    fi
    
    echo "  Building library in $target_dir..."
    if (cd "$target_dir" && make clean && make 2>&1 | tee build.log); then
        if [[ -f "$target_dir/libcalculator.so" ]] || [[ -f "$target_dir/libcalculator.a" ]]; then
            echo -e "${GREEN}✓${NC} $description: library builds successfully"
            ((TESTS_PASSED++))
            return 0
        else
            echo -e "${RED}✗${NC} $description: library file not created"
            ((TESTS_FAILED++))
            return 1
        fi
    else
        echo -e "${RED}✗${NC} $description: build failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# ============================================================================
# Main Test Suite
# ============================================================================

main() {
    echo "============================================================================"
    echo "Linux Integration Test Suite"
    echo "============================================================================"
    echo "Testing calculator driver integration"
    echo ""
    
    # Test 1: Driver source files exist
    echo "Test 1: Driver Source Files"
    echo "----------------------------"
    test_file_exists "$DRIVER_SRC/calculator_driver.h" "Driver header"
    test_file_exists "$DRIVER_SRC/calculator_driver.c" "Driver source"
    test_file_exists "$DRIVER_SRC/logger.h" "Logger header"
    test_file_exists "$DRIVER_SRC/logger.c" "Logger source"
    echo ""
    
    # Test 2: Integration script exists
    echo "Test 2: Integration Scripts"
    echo "---------------------------"
    test_file_exists "$SCRIPT_DIR/integrate_linux_driver.sh" "Integration script (bash)"
    test_file_exists "$SCRIPT_DIR/integrate_linux_driver.bat" "Integration script (Windows)"
    test_file_exists "$SCRIPT_DIR/example_userspace_makefile" "Example Makefile"
    echo ""
    
    # Test 3: Driver compiles (if GCC available)
    if command -v gcc &> /dev/null; then
        echo "Test 3: Driver Compilation"
        echo "-------------------------"
        test_compiles "$DRIVER_SRC/calculator_driver.c" "Driver source"
        test_compiles "$DRIVER_SRC/logger.c" "Logger source"
        echo ""
    else
        echo "Test 3: Driver Compilation (SKIPPED - GCC not found)"
        echo ""
    fi
    
    # Test 4: Device tree file exists
    echo "Test 4: Device Tree Files"
    echo "-------------------------"
    test_file_exists "$FPGA_ROOT/qsys/calculator.dtsi" "Device tree overlay"
    echo ""
    
    # Test 5: Documentation exists
    echo "Test 5: Documentation"
    echo "--------------------"
    test_file_exists "$FPGA_ROOT/docs/LINUX_INTEGRATION.md" "Integration guide"
    echo ""
    
    # Summary
    echo "============================================================================"
    echo "Test Summary"
    echo "============================================================================"
    echo "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo "Failed: ${RED}$TESTS_FAILED${NC}"
    echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All integration tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed. Please review the output above.${NC}"
        return 1
    fi
}

# Run tests
main
