// ============================================================================
// HFT Test Cases - Implementation
// ============================================================================
// Comprehensive test suite for HFT calculator operations
// ============================================================================

#include "hft_test_cases.h"

// ============================================================================
// Test Data Arrays
// ============================================================================

// SMA Test Data
static float sma_data_5[] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
static float sma_data_10[] = {
    100.0f, 102.0f, 101.5f, 103.0f, 102.5f,
    104.0f, 103.5f, 105.0f, 104.5f, 106.0f
};
static float sma_data_spy[] = {
    435.50f, 435.75f, 435.60f, 435.80f, 436.00f,
    436.20f, 436.10f, 435.90f, 436.15f, 436.30f
};
static float sma_data_zeros[] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
static float sma_data_negative[] = {-10.0f, -5.0f, -15.0f, -8.0f, -12.0f};
static float sma_data_volatile[] = {
    50.0f, 75.0f, 25.0f, 100.0f, 10.0f
};
static float sma_data_decimal[] = {
    1.11f, 2.22f, 3.33f, 4.44f, 5.55f
};
static float sma_data_single[] = {42.0f};
static float sma_data_large[] = {
    100.0f, 101.0f, 102.0f, 103.0f, 104.0f, 105.0f, 106.0f, 107.0f, 108.0f, 109.0f,
    110.0f, 111.0f, 112.0f, 113.0f, 114.0f, 115.0f, 116.0f, 117.0f, 118.0f, 119.0f
};

// EMA Test Data
static float ema_data_init[] = {100.0f};
static float ema_data_trend_up[] = {
    100.0f, 102.0f, 104.0f, 106.0f, 108.0f, 110.0f
};
static float ema_data_trend_down[] = {
    110.0f, 108.0f, 106.0f, 104.0f, 102.0f, 100.0f
};
static float ema_data_7[] = {22.0f, 23.0f, 24.0f, 23.0f, 22.0f, 21.0f, 20.0f};
static float ema_data_smooth[] = {
    100.0f, 100.5f, 101.0f, 101.5f, 102.0f, 102.5f
};
static float ema_data_rapid[] = {
    50.0f, 75.0f, 40.0f, 90.0f, 30.0f, 100.0f
};

// Statistical Test Data
static float stat_data_std[] = {10.0f, 12.0f, 23.0f, 23.0f, 16.0f, 23.0f, 21.0f, 16.0f};
static float stat_data_constant[] = {5.0f, 5.0f, 5.0f, 5.0f, 5.0f};
static float stat_data_range[] = {10.0f, 25.0f, 15.0f, 30.0f, 5.0f, 20.0f};
static float stat_data_mixed[] = {-5.0f, 10.0f, -15.0f, 20.0f, -10.0f};

// Real-World HFT Scenarios
static float vwap_prices[] = {100.0f, 101.0f, 99.5f, 100.5f, 101.5f};
// Note: VWAP also needs volume data (not implemented in this version)

static float bollinger_data[] = {
    100.0f, 102.0f, 101.0f, 103.0f, 102.0f,
    104.0f, 103.0f, 105.0f, 104.0f, 106.0f
};

static float rsi_up[] = {
    44.0f, 45.0f, 46.0f, 47.0f, 48.0f, 49.0f, 50.0f, 51.0f, 52.0f, 53.0f
};

static float momentum_data[] = {
    100.0f, 102.0f, 105.0f, 109.0f, 114.0f, 120.0f
};

// ============================================================================
// Test Case Definitions
// ============================================================================
const hft_test_case_t hft_test_cases[] = {
    // ========================================================================
    // SMA (Simple Moving Average) Tests - 10 cases
    // ========================================================================
    {
        CALC_OP_SMA,
        "SMA: Basic 5-period [1,2,3,4,5] = 3.0",
        sma_data_5,
        5,
        5,
        0.0f,
        3.0f
    },
    {
        CALC_OP_SMA,
        "SMA: 10-period price data",
        sma_data_10,
        10,
        10,
        0.0f,
        103.25f  // Average of 100-106
    },
    {
        CALC_OP_SMA,
        "SMA: SPY 5-min data (10 periods)",
        sma_data_spy,
        10,
        10,
        0.0f,
        435.93f
    },
    {
        CALC_OP_SMA,
        "SMA: All zeros",
        sma_data_zeros,
        5,
        5,
        0.0f,
        0.0f
    },
    {
        CALC_OP_SMA,
        "SMA: Negative prices",
        sma_data_negative,
        5,
        5,
        0.0f,
        -10.0f  // (-10-5-15-8-12)/5
    },
    {
        CALC_OP_SMA,
        "SMA: High volatility data",
        sma_data_volatile,
        5,
        5,
        0.0f,
        52.0f  // (50+75+25+100+10)/5
    },
    {
        CALC_OP_SMA,
        "SMA: Decimal precision",
        sma_data_decimal,
        5,
        5,
        0.0f,
        3.33f  // (1.11+2.22+3.33+4.44+5.55)/5
    },
    {
        CALC_OP_SMA,
        "SMA: Single value (window=1)",
        sma_data_single,
        1,
        1,
        0.0f,
        42.0f
    },
    {
        CALC_OP_SMA,
        "SMA: Large window (20 periods)",
        sma_data_large,
        20,
        20,
        0.0f,
        109.5f  // Average of 100-119
    },
    {
        CALC_OP_SMA,
        "SMA: Partial window (3 of 5)",
        sma_data_5,
        3,
        3,
        0.0f,
        2.0f  // (1+2+3)/3
    },

    // ========================================================================
    // EMA (Exponential Moving Average) Tests - 8 cases
    // ========================================================================
    {
        CALC_OP_EMA,
        "EMA: Initialization (first value)",
        ema_data_init,
        1,
        1,
        0.5f,
        100.0f  // First EMA equals first price
    },
    {
        CALC_OP_EMA,
        "EMA: Upward trend (α=0.1)",
        ema_data_trend_up,
        6,
        19,  // α = 2/(19+1) = 0.1
        0.1f,
        104.5f  // Approximate EMA value
    },
    {
        CALC_OP_EMA,
        "EMA: Downward trend (α=0.1)",
        ema_data_trend_down,
        6,
        19,
        0.1f,
        105.5f  // Approximate EMA value
    },
    {
        CALC_OP_EMA,
        "EMA: α=0.333 (window=5)",
        ema_data_7,
        7,
        5,  // α = 2/(5+1) ≈ 0.333
        0.333f,
        21.39f  // Final EMA after 7 prices
    },
    {
        CALC_OP_EMA,
        "EMA: Smooth movement (α=0.2)",
        ema_data_smooth,
        6,
        9,  // α = 2/(9+1) = 0.2
        0.2f,
        101.5f  // Approximate
    },
    {
        CALC_OP_EMA,
        "EMA: Rapid price changes (α=0.5)",
        ema_data_rapid,
        6,
        3,  // α = 2/(3+1) = 0.5
        0.5f,
        65.0f  // Highly responsive EMA
    },
    {
        CALC_OP_EMA,
        "EMA: vs SMA comparison (same data)",
        sma_data_5,
        5,
        5,
        0.333f,
        3.5f  // EMA will differ from SMA(3.0)
    },
    {
        CALC_OP_EMA,
        "EMA: Alpha validation (α=0.25)",
        ema_data_trend_up,
        6,
        7,  // α = 2/(7+1) = 0.25
        0.25f,
        105.0f  // Approximate
    },

    // ========================================================================
    // Statistical Tests - 6 cases
    // ========================================================================
    {
        CALC_OP_STD_DEV,
        "STD_DEV: Basic data set",
        stat_data_std,
        8,
        8,
        0.0f,
        5.24f  // Standard deviation
    },
    {
        CALC_OP_STD_DEV,
        "STD_DEV: Constant values (should be ~0)",
        stat_data_constant,
        5,
        5,
        0.0f,
        0.0f
    },
    {
        CALC_OP_MIN,
        "MIN: Find minimum in range",
        stat_data_range,
        6,
        6,
        0.0f,
        5.0f
    },
    {
        CALC_OP_MAX,
        "MAX: Find maximum in range",
        stat_data_range,
        6,
        6,
        0.0f,
        30.0f
    },
    {
        CALC_OP_RANGE,
        "RANGE: Max - Min",
        stat_data_range,
        6,
        6,
        0.0f,
        25.0f  // 30 - 5
    },
    {
        CALC_OP_MIN,
        "MIN: Mixed positive/negative",
        stat_data_mixed,
        5,
        5,
        0.0f,
        -15.0f
    },

    // ========================================================================
    // Real-World HFT Scenarios - 5 cases
    // ========================================================================
    {
        CALC_OP_VWAP,
        "VWAP: Volume-weighted average (simplified)",
        vwap_prices,
        5,
        5,
        0.0f,
        100.5f  // Simplified without volume weighting
    },
    {
        CALC_OP_BOLLINGER_UP,
        "Bollinger Upper: Mean + 2σ",
        bollinger_data,
        10,
        10,
        0.0f,
        107.0f  // Approximate: mean + 2*std
    },
    {
        CALC_OP_BOLLINGER_DN,
        "Bollinger Lower: Mean - 2σ",
        bollinger_data,
        10,
        10,
        0.0f,
        101.0f  // Approximate: mean - 2*std
    },
    {
        CALC_OP_RSI,
        "RSI: Upward momentum",
        rsi_up,
        10,
        10,
        0.0f,
        100.0f  // Pure uptrend = RSI ~100
    },
    {
        CALC_OP_SMA,
        "HFT: Price momentum tracking",
        momentum_data,
        6,
        3,
        0.0f,
        114.33f  // SMA of last 3: (109+114+120)/3
    }
};

// Number of test cases
const int num_hft_test_cases = sizeof(hft_test_cases) / sizeof(hft_test_cases[0]);
