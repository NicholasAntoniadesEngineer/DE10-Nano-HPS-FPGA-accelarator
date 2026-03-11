// ============================================================================
// Calculator Demo - Continuous FPGA Interaction Loop
// ============================================================================
// Runs a continuous demonstration of the FPGA calculator IP, cycling through
// ADD, SUB, MUL, DIV operations with representative operands and displaying
// the result's low byte on LED[7:0] in real time.
//
// The calculator hardware drives LED[7:0] with result[7:0] via its led_output
// conduit. LED patterns are achieved by performing calculator operations whose
// results produce the desired low-byte pattern.
//
// Designed to run as a systemd service at boot to provide immediate visual
// confirmation that the FPGA-HPS bridge and calculator IP are functioning.
//
// Usage:
//   calculator_demo              # run continuous loop (use as service)
//   calculator_demo --once       # run one full cycle and exit (0 = all pass)
//   calculator_demo --interval N # seconds between operations (default: 2)
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <math.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <time.h>

#include "calculator_driver.h"

// ============================================================================
// Configuration
// ============================================================================
#define DEFAULT_INTERVAL_S   2       // seconds between each operation

// ============================================================================
// Demo Operations Table
// ============================================================================
typedef struct {
    calculator_operation_t op;
    float a;
    float b;
    float expected;
    const char *label;
} demo_op_t;

static const demo_op_t demo_ops[] = {
    { CALC_OP_ADD,  1.0f,    2.0f,    3.0f,      "1.0 + 2.0 = 3.0"          },
    { CALC_OP_MUL,  3.0f,    4.0f,   12.0f,      "3.0 * 4.0 = 12.0"         },
    { CALC_OP_SUB, 10.0f,    3.5f,    6.5f,      "10.0 - 3.5 = 6.5"         },
    { CALC_OP_DIV, 22.0f,    7.0f,    3.142857f, "22.0 / 7.0 ≈ 3.1429 (pi)" },
    { CALC_OP_ADD,  0.1f,    0.2f,    0.3f,      "0.1 + 0.2 ≈ 0.3"          },
    { CALC_OP_MUL,  2.0f,    3.14159f, 6.28318f, "2.0 * π ≈ 6.2832 (2π)"   },
    { CALC_OP_DIV,  1.0f,    3.0f,    0.333333f, "1.0 / 3.0 ≈ 0.3333"       },
    { CALC_OP_SUB, 100.0f, 100.0f,    0.0f,      "100.0 - 100.0 = 0.0"      },
};
static const int num_demo_ops = (int)(sizeof(demo_ops) / sizeof(demo_ops[0]));

// ============================================================================
// LED control via calculator hardware
// ============================================================================
// The calculator IP drives LED[7:0] with result[7:0] via its led_output
// conduit. To display a specific LED pattern, we perform ADD(0, value)
// where the IEEE 754 representation of 'value' has the desired low byte.
// For simple patterns we use integer bit patterns reinterpreted as floats.
// ============================================================================

static void led_set_pattern(uint8_t pattern) {
    // The calculator hardware drives LED[7:0] with result[7:0] (the low byte
    // of the IEEE 754 result). To display a specific LED pattern, we perform
    // ADD(x, 0.0) where x is a normal float whose IEEE 754 low byte matches
    // the desired pattern. We use exponent 0x7F (value near 1.0) to stay in
    // the normal float range — denormals risk being flushed to zero by the
    // ARM FPU during parameter passing.
    //
    // IEEE 754 layout: [sign(1)][exponent(8)][mantissa(23)]
    // We set: sign=0, exponent=0x7F, mantissa[22:8]=0, mantissa[7:0]=pattern
    // Result bits: 0x3F800000 | pattern
    uint32_t target_bits = 0x3F800000u | (uint32_t)pattern;
    float a_val;
    memcpy(&a_val, &target_bits, sizeof(a_val));
    float result;
    calculator_perform_operation(CALC_OP_ADD, a_val, 0.0f, &result);
}

// ============================================================================
// Signal handling — clean shutdown
// ============================================================================
static volatile bool running = true;

static void handle_signal(int sig) {
    (void)sig;
    running = false;
}

// ============================================================================
// Startup LED sweep: fill LEDs left-to-right then clear
// Provides visual confirmation that the FPGA bridge is working
// ============================================================================
static void startup_sweep(void) {
    const uint8_t patterns[] = {
        0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF,
        0xFF, 0xFF, 0xFF,   /* hold full */
        0x00
    };
    for (int i = 0; i < (int)(sizeof(patterns)); i++) {
        led_set_pattern(patterns[i]);
        usleep(80000); /* 80 ms per step */
    }
}

// ============================================================================
// Error blink: rapid alternating pattern indicating FPGA not reachable
// ============================================================================
static void error_blink(int count) {
    for (int i = 0; i < count; i++) {
        led_set_pattern(0xAA);
        usleep(200000);
        led_set_pattern(0x55);
        usleep(200000);
    }
    led_set_pattern(0x00);
}

// ============================================================================
// Timestamp helper
// ============================================================================
static void print_ts(void) {
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    printf("[%02d:%02d:%02d] ", tm->tm_hour, tm->tm_min, tm->tm_sec);
}

// ============================================================================
// Run one complete cycle of all demo operations.
// Returns number of failures.
// Each operation triggers the calculator hardware, which automatically
// updates LED[7:0] with result[7:0] via the led_output conduit.
// ============================================================================
static int run_cycle(int cycle_num) {
    int failures = 0;

    printf("\n=== Cycle %d ===\n", cycle_num);

    for (int i = 0; i < num_demo_ops && running; i++) {
        const demo_op_t *op = &demo_ops[i];
        float result = 0.0f;

        int ret = calculator_perform_operation(op->op, op->a, op->b, &result);

        /* Extract low byte of the IEEE 754 result bits for display */
        uint32_t result_bits;
        memcpy(&result_bits, &result, sizeof(result_bits));
        uint8_t led_pattern = (uint8_t)(result_bits & 0xFF);

        print_ts();

        if (ret == 0) {
            float diff = fabsf(result - op->expected);
            bool pass = diff < 0.001f;
            if (!pass) failures++;

            printf("%-28s → %10.6f  LED=0x%02X  %s\n",
                   op->label, result, led_pattern,
                   pass ? "PASS" : "FAIL");
        } else {
            failures++;
            printf("%-28s → ERROR(%d)              FAIL\n",
                   op->label, ret);
            led_set_pattern(0xFF); /* all LEDs on to signal error */
        }

        /* Brief pause so LED pattern is visible between operations */
        usleep(500000);
    }

    return failures;
}

// ============================================================================
// Main
// ============================================================================
int main(int argc, char *argv[]) {
    bool once        = false;
    int  interval_s  = DEFAULT_INTERVAL_S;

    /* Parse arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--once") == 0) {
            once = true;
        } else if (strcmp(argv[i], "--interval") == 0 && i + 1 < argc) {
            interval_s = atoi(argv[++i]);
            if (interval_s < 0) interval_s = 0;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            printf("Usage: %s [--once] [--interval N]\n", argv[0]);
            printf("  --once        Run one cycle then exit (0 = all pass)\n");
            printf("  --interval N  Seconds between operations (default: %d)\n",
                   DEFAULT_INTERVAL_S);
            return 0;
        }
    }

    /* Signal handlers for clean shutdown */
    signal(SIGTERM, handle_signal);
    signal(SIGINT,  handle_signal);

    printf("============================================================\n");
    printf("  DE10-Nano Calculator FPGA Demo\n");
    printf("  Cycling through ADD / SUB / MUL / DIV every %ds\n", interval_s);
    printf("  Watch LED[7:0] for live result display\n");
    printf("  Send SIGTERM or Ctrl-C to stop\n");
    printf("============================================================\n");

    /* Initialise calculator driver */
    if (calculator_init() != 0) {
        fprintf(stderr, "ERROR: Failed to initialise calculator driver.\n");
        fprintf(stderr, "  Check the following:\n");
        fprintf(stderr, "  1. DIP switch SW10 (MSEL) set for HPS FPGA programming\n");
        fprintf(stderr, "     (power cycle required after changing — MSEL sampled at power-on)\n");
        fprintf(stderr, "  2. FPGA bitstream loaded (boot.scr runs 'fpga load')\n");
        fprintf(stderr, "  3. HPS-to-FPGA bridges enabled ('bridge enable' in boot.scr)\n");
        fprintf(stderr, "  4. Running as root (needed for /dev/mem access)\n");
        fprintf(stderr, "  Diagnostic: devmem2 0xff20003c w  (expect 0x00010001)\n");
        return 1;
    }

    printf("Calculator driver initialised. Starting demo...\n\n");

    /* Startup sweep to show the system is alive */
    startup_sweep();

    int cycle     = 1;
    int total_fail = 0;

    while (running) {
        int failures = run_cycle(cycle++);
        total_fail += failures;

        if (once) break;

        /* Sleep between cycles, waking early on signal */
        for (int s = 0; s < interval_s && running; s++) {
            sleep(1);
        }
    }

    printf("\nShutting down. Total failures: %d\n", total_fail);

    led_set_pattern(0x00);
    calculator_cleanup();

    return (total_fail == 0) ? 0 : 1;
}
