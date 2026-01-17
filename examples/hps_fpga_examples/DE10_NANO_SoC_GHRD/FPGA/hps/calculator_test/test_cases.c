// ============================================================================
// Calculator Test Cases - Implementation
// ============================================================================
// Comprehensive test suite for calculator hardware
// ============================================================================

#include "test_cases.h"

// ============================================================================
// Test Case Definitions
// ============================================================================
const test_case_t test_cases[] = {
    // ========================================================================
    // Addition Tests
    // ========================================================================
    {CALC_OP_ADD, 1.0f, 2.0f, 3.0f, "Basic addition: 1.0 + 2.0 = 3.0"},
    {CALC_OP_ADD, -5.5f, 3.2f, -2.3f, "Negative + Positive: -5.5 + 3.2 = -2.3"},
    {CALC_OP_ADD, 0.0f, 0.0f, 0.0f, "Zero addition: 0.0 + 0.0 = 0.0"},
    {CALC_OP_ADD, 100.25f, 200.75f, 301.0f, "Decimal addition: 100.25 + 200.75 = 301.0"},
    {CALC_OP_ADD, -10.5f, -20.5f, -31.0f, "Negative addition: -10.5 + -20.5 = -31.0"},

    // ========================================================================
    // Subtraction Tests
    // ========================================================================
    {CALC_OP_SUB, 5.0f, 3.0f, 2.0f, "Basic subtraction: 5.0 - 3.0 = 2.0"},
    {CALC_OP_SUB, -10.0f, -5.0f, -5.0f, "Negative subtraction: -10.0 - (-5.0) = -5.0"},
    {CALC_OP_SUB, 0.0f, 7.5f, -7.5f, "Zero minus positive: 0.0 - 7.5 = -7.5"},
    {CALC_OP_SUB, 100.0f, 100.0f, 0.0f, "Equal operands: 100.0 - 100.0 = 0.0"},
    {CALC_OP_SUB, 3.14159f, 3.0f, 0.14159f, "Pi subtraction: 3.14159 - 3.0 ≈ 0.14159"},

    // ========================================================================
    // Multiplication Tests
    // ========================================================================
    {CALC_OP_MUL, 2.0f, 3.0f, 6.0f, "Basic multiplication: 2.0 * 3.0 = 6.0"},
    {CALC_OP_MUL, -4.0f, 5.0f, -20.0f, "Negative multiplication: -4.0 * 5.0 = -20.0"},
    {CALC_OP_MUL, 0.5f, 8.0f, 4.0f, "Fractional multiplication: 0.5 * 8.0 = 4.0"},
    {CALC_OP_MUL, 0.0f, 100.0f, 0.0f, "Zero multiplication: 0.0 * 100.0 = 0.0"},
    {CALC_OP_MUL, -3.0f, -4.0f, 12.0f, "Negative * Negative: -3.0 * -4.0 = 12.0"},
    {CALC_OP_MUL, 1.5f, 2.5f, 3.75f, "Decimal multiplication: 1.5 * 2.5 = 3.75"},

    // ========================================================================
    // Division Tests
    // ========================================================================
    {CALC_OP_DIV, 10.0f, 2.0f, 5.0f, "Basic division: 10.0 / 2.0 = 5.0"},
    {CALC_OP_DIV, 15.0f, 3.0f, 5.0f, "Even division: 15.0 / 3.0 = 5.0"},
    {CALC_OP_DIV, -20.0f, 4.0f, -5.0f, "Negative division: -20.0 / 4.0 = -5.0"},
    {CALC_OP_DIV, 1.0f, 4.0f, 0.25f, "Fractional division: 1.0 / 4.0 = 0.25"},
    {CALC_OP_DIV, 7.0f, 2.0f, 3.5f, "Decimal result: 7.0 / 2.0 = 3.5"},
    {CALC_OP_DIV, 100.0f, 3.0f, 33.333332f, "Repeating decimal: 100.0 / 3.0 ≈ 33.333"},

    // ========================================================================
    // Edge Cases and Special Values
    // ========================================================================
    {CALC_OP_ADD, 1.0e10f, 1.0e-10f, 1.0e10f, "Large + Small: 1e10 + 1e-10 ≈ 1e10"},
    {CALC_OP_MUL, 1.0e20f, 1.0e-20f, 1.0f, "Very large * Very small: 1e20 * 1e-20 = 1.0"},
    {CALC_OP_DIV, 1.0f, 1.0f, 1.0f, "Unity division: 1.0 / 1.0 = 1.0"},
    {CALC_OP_MUL, 10.0f, 0.1f, 1.0f, "Decimal precision: 10.0 * 0.1 = 1.0"},

    // ========================================================================
    // Real-World Calculation Examples
    // ========================================================================
    {CALC_OP_MUL, 3.14159f, 2.0f, 6.28318f, "2*Pi calculation: π * 2 ≈ 6.28318"},
    {CALC_OP_DIV, 1.0f, 3.0f, 0.333333f, "One third: 1.0 / 3.0 ≈ 0.333333"},
    {CALC_OP_ADD, 273.15f, 100.0f, 373.15f, "Temperature: 273.15 + 100 = 373.15"},
    {CALC_OP_MUL, 9.8f, 10.0f, 98.0f, "Physics: 9.8 * 10 = 98.0"},
};

// Number of test cases
const int num_test_cases = sizeof(test_cases) / sizeof(test_cases[0]);
