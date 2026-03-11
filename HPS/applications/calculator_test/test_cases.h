// ============================================================================
// Calculator Test Cases - Header
// ============================================================================
// Defines test cases for calculator hardware verification
// ============================================================================

#ifndef TEST_CASES_H
#define TEST_CASES_H

#include "calculator_driver.h"

// ============================================================================
// Test Case Structure
// ============================================================================
typedef struct {
    calculator_operation_t operation;
    float operand_a;
    float operand_b;
    float expected_result;
    const char *description;
    bool expect_error;  // true = test passes when driver returns error
} test_case_t;

// ============================================================================
// Test Case Array
// ============================================================================
extern const test_case_t test_cases[];
extern const int num_test_cases;

#endif // TEST_CASES_H
