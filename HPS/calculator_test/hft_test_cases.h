// ============================================================================
// HFT Test Cases - Header File
// ============================================================================
// Test cases for High-Frequency Trading calculator operations
// ============================================================================

#ifndef HFT_TEST_CASES_H
#define HFT_TEST_CASES_H

#include <stdint.h>
#include "calculator_driver.h"

// ============================================================================
// HFT Test Case Structure
// ============================================================================
typedef struct {
    calculator_operation_t operation;    // Operation to test
    const char *description;             // Test description
    float *prices;                       // Price data array
    uint16_t price_count;                // Number of prices
    uint16_t window_size;                // Window size for calculation
    float alpha;                         // Alpha parameter (for EMA)
    float expected_result;               // Expected result
} hft_test_case_t;

// ============================================================================
// Test Case Arrays
// ============================================================================
extern const hft_test_case_t hft_test_cases[];
extern const int num_hft_test_cases;

#endif // HFT_TEST_CASES_H
