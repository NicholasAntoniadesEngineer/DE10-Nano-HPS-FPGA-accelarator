// ============================================================================
// Calculator Test Suite - Main Program
// ============================================================================
// Comprehensive test harness for hardware calculator IP
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <signal.h>
#include "calculator_driver.h"
#include "test_cases.h"
#include "logger.h"

// ============================================================================
// Configuration
// ============================================================================
#define FLOAT_TOLERANCE 0.001f  // Tolerance for floating point comparison
#define DELAY_BETWEEN_TESTS_US 500000  // 500ms delay to observe LEDs

// ============================================================================
// Color Output (ANSI codes)
// ============================================================================
#define COLOR_RESET   "\033[0m"
#define COLOR_RED     "\033[31m"
#define COLOR_GREEN   "\033[32m"
#define COLOR_YELLOW  "\033[33m"
#define COLOR_BLUE    "\033[34m"
#define COLOR_CYAN    "\033[36m"
#define COLOR_BOLD    "\033[1m"

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Compare two floats with tolerance
 */
static bool float_equals(float a, float b, float tolerance) {
    return fabsf(a - b) < tolerance;
}

/**
 * Print test banner
 */
static void print_banner(void) {
    printf("\n");
    printf("========================================================================\n");
    printf("                   FPGA CALCULATOR TEST SUITE\n");
    printf("========================================================================\n");
    printf("Hardware-Accelerated Floating Point Calculator Verification\n");
    printf("DE10-Nano SoC - HPS to FPGA Communication Test\n");
    printf("========================================================================\n");
}

/**
 * Print test summary
 */
static void print_summary(int total, int passed, int failed) {
    printf("\n");
    printf("========================================================================\n");
    printf("                        TEST SUMMARY\n");
    printf("========================================================================\n");
    printf("Total tests:    %s%d%s\n", COLOR_BOLD, total, COLOR_RESET);
    printf("Passed:         %s%s%d%s\n", COLOR_GREEN, COLOR_BOLD, passed, COLOR_RESET);
    printf("Failed:         %s%s%d%s\n", failed > 0 ? COLOR_RED : COLOR_GREEN, COLOR_BOLD, failed, COLOR_RESET);
    printf("Success rate:   %s%.1f%%%s\n",
           failed == 0 ? COLOR_GREEN : (passed > failed ? COLOR_YELLOW : COLOR_RED),
           (float)passed / total * 100.0f,
           COLOR_RESET);
    printf("========================================================================\n");

    if (failed == 0) {
        printf("%s%s✓ ALL TESTS PASSED!%s\n", COLOR_GREEN, COLOR_BOLD, COLOR_RESET);
        printf("Hardware calculator is functioning correctly.\n");
    } else {
        printf("%s%s✗ SOME TESTS FAILED%s\n", COLOR_RED, COLOR_BOLD, COLOR_RESET);
        printf("Please review the failures above.\n");
    }
    printf("========================================================================\n");
}

/**
 * Run a single test case
 */
static int run_test_case(const test_case_t *test, int test_num) {
    float result;
    int ret;

    LOG_INFO("========================================");
    LOG_INFO("Test %d/%d: %s", test_num, num_test_cases, test->description);
    LOG_INFO("========================================");
    LOG_DEBUG("Operation: %s (0x%X)", calculator_operation_to_string(test->operation), test->operation);
    LOG_DEBUG("Operand A: %.6f (0x%08X)", test->operand_a, *((uint32_t *)&test->operand_a));
    LOG_DEBUG("Operand B: %.6f (0x%08X)", test->operand_b, *((uint32_t *)&test->operand_b));
    LOG_DEBUG("Expected:  %.6f (0x%08X)", test->expected_result, *((uint32_t *)&test->expected_result));
    LOG_DEBUG("Tolerance: %.6f", FLOAT_TOLERANCE);

    // Print test header
    printf("\n");
    printf("%s────────────────────────────────────────────────────────────────────────%s\n",
           COLOR_CYAN, COLOR_RESET);
    printf("%s[Test %d/%d]%s %s\n",
           COLOR_BOLD, test_num, num_test_cases, COLOR_RESET, test->description);
    printf("%s────────────────────────────────────────────────────────────────────────%s\n",
           COLOR_CYAN, COLOR_RESET);

    // Print test details
    printf("  Operation:    %s%s%s\n",
           COLOR_YELLOW, calculator_operation_to_string(test->operation), COLOR_RESET);
    printf("  Operand A:    %.6f\n", test->operand_a);
    printf("  Operand B:    %.6f\n", test->operand_b);
    printf("  Expected:     %.6f\n", test->expected_result);

    // Perform calculation
    LOG_DEBUG("Executing calculation operation...");
    ret = calculator_perform_operation(
        test->operation,
        test->operand_a,
        test->operand_b,
        &result
    );

    if (ret != 0) {
        LOG_ERROR("Test %d FAILED: Operation returned error code %d", test_num, ret);
        printf("  %sResult:       ERROR (operation failed)%s\n", COLOR_RED, COLOR_RESET);
        printf("  %sStatus:       ✗ FAIL%s\n", COLOR_RED, COLOR_RESET);
        return 0;  // Test failed
    }

    LOG_DEBUG("Operation completed successfully");
    LOG_DEBUG("Actual result: %.6f (0x%08X)", result, *((uint32_t *)&result));
    printf("  Result:       %.6f\n", result);

    // Verify result
    float diff = fabsf(result - test->expected_result);
    LOG_DEBUG("Result comparison: actual=%.6f, expected=%.6f, diff=%.6f, tolerance=%.6f",
             result, test->expected_result, diff, FLOAT_TOLERANCE);
    
    if (float_equals(result, test->expected_result, FLOAT_TOLERANCE)) {
        LOG_INFO("Test %d PASSED: Result matches expected value", test_num);
        printf("  %sStatus:       ✓ PASS%s\n", COLOR_GREEN, COLOR_RESET);
        return 1;  // Test passed
    } else {
        LOG_ERROR("Test %d FAILED: Result mismatch", test_num);
        LOG_ERROR("  Expected: %.6f (0x%08X)", test->expected_result, *((uint32_t *)&test->expected_result));
        LOG_ERROR("  Actual:   %.6f (0x%08X)", result, *((uint32_t *)&result));
        LOG_ERROR("  Diff:     %.6f (tolerance: %.6f)", diff, FLOAT_TOLERANCE);
        printf("  %sDifference:   %.6f (tolerance: %.6f)%s\n",
               COLOR_RED, diff, FLOAT_TOLERANCE, COLOR_RESET);
        printf("  %sStatus:       ✗ FAIL%s\n", COLOR_RED, COLOR_RESET);
        return 0;  // Test failed
    }
}

/**
 * Print usage information
 */
static void print_usage(const char *program_name) {
    printf("Usage: %s [options]\n", program_name);
    printf("\n");
    printf("Options:\n");
    printf("  -h, --help     Show this help message\n");
    printf("  -q, --quick    Quick mode (no delays between tests)\n");
    printf("  -v, --verbose  Verbose output (DEBUG log level)\n");
    printf("  -vv, --trace   Trace output (TRACE log level, maximum verbosity)\n");
    printf("\n");
    printf("Log Levels:\n");
    printf("  Default: INFO  - Normal operation messages\n");
    printf("  -v:      DEBUG - Detailed debugging information\n");
    printf("  -vv:     TRACE - Maximum verbosity (register dumps, etc.)\n");
    printf("\n");
    printf("Note: This program must be run as root or with appropriate permissions.\n");
    printf("      Use: sudo %s\n", program_name);
    printf("\n");
    printf("Logging: All operations are logged with timestamps and file/line info.\n");
    printf("         Use -v or -vv for detailed debugging output.\n");
}

// ============================================================================
// Main Function
// ============================================================================
int main(int argc, char *argv[]) {
    int passed = 0;
    int failed = 0;
    int i;
    bool quick_mode = false;
    bool verbose_mode = false;
    log_level_t log_level = LOG_LEVEL_INFO;

    // Parse command line arguments
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else if (strcmp(argv[i], "-q") == 0 || strcmp(argv[i], "--quick") == 0) {
            quick_mode = true;
        } else if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--verbose") == 0) {
            verbose_mode = true;
            log_level = LOG_LEVEL_DEBUG;
        } else if (strcmp(argv[i], "-vv") == 0 || strcmp(argv[i], "--trace") == 0) {
            verbose_mode = true;
            log_level = LOG_LEVEL_TRACE;
        }
    }

    // Initialize logging system
    logger_init(log_level, stderr);
    LOG_INFO("Calculator Test Suite Starting");
    LOG_INFO("Arguments: argc=%d", argc);
    for (i = 0; i < argc; i++) {
        LOG_DEBUG("  argv[%d] = '%s'", i, argv[i]);
    }
    LOG_DEBUG("Quick mode: %s", quick_mode ? "enabled" : "disabled");
    LOG_DEBUG("Verbose mode: %s (log level: %s)", verbose_mode ? "enabled" : "disabled", logger_level_name(log_level));

    // Print banner
    print_banner();

    // Initialize calculator driver
    LOG_INFO("Initializing calculator driver...");
    printf("\nInitializing calculator driver...\n");
    if (calculator_init() != 0) {
        LOG_ERROR("Failed to initialize calculator driver");
        printf("\n%sERROR: Failed to initialize calculator driver%s\n", COLOR_RED, COLOR_RESET);
        printf("\nTroubleshooting:\n");
        printf("  1. Ensure you are running as root (sudo)\n");
        printf("  2. Verify FPGA is programmed with calculator design\n");
        printf("  3. Check that calculator IP is properly integrated in QSys\n");
        printf("  4. Confirm base address matches QSys configuration\n");
        printf("\n");
        return 1;
    }

    LOG_INFO("Calculator driver initialized successfully");
    printf("\n%s✓ Calculator driver initialized successfully%s\n", COLOR_GREEN, COLOR_RESET);
    LOG_INFO("Running %d test cases...", num_test_cases);
    printf("\nRunning %d test cases...\n", num_test_cases);

    if (!quick_mode) {
        printf("\n%sNote: Watch LED[7:0] to see result register bits change in real-time!%s\n",
               COLOR_YELLOW, COLOR_RESET);
        printf("Delays between tests allow LED observation (use -q for quick mode).\n");
    }

    // Run all test cases
    LOG_INFO("Starting test execution...");
    for (i = 0; i < num_test_cases; i++) {
        LOG_DEBUG("Executing test case %d/%d", i + 1, num_test_cases);
        
        if (run_test_case(&test_cases[i], i + 1)) {
            passed++;
            LOG_DEBUG("Test %d passed (total passed: %d, failed: %d)", i + 1, passed, failed);
        } else {
            failed++;
            LOG_WARN("Test %d failed (total passed: %d, failed: %d)", i + 1, passed, failed);
        }

        // Delay between tests to observe LED changes (unless quick mode)
        if (!quick_mode && i < num_test_cases - 1) {
            LOG_TRACE("Delaying %d microseconds before next test...", DELAY_BETWEEN_TESTS_US);
            usleep(DELAY_BETWEEN_TESTS_US);
        }
    }

    // Print summary
    LOG_INFO("Test execution complete: %d passed, %d failed out of %d total", passed, failed, num_test_cases);
    print_summary(num_test_cases, passed, failed);

    // Cleanup
    LOG_INFO("Cleaning up...");
    calculator_cleanup();
    LOG_INFO("Test suite completed");

    // Return exit code (0 if all passed, 1 if any failed)
    return (failed == 0) ? 0 : 1;
}
