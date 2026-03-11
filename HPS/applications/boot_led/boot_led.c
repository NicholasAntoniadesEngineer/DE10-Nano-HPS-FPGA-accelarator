// ============================================================================
// Boot LED Indicator - DE10-Nano (Calculator-Driven)
// ============================================================================
// Drives LED patterns by running computations on the FPGA calculator IP.
// The calculator_led_display module shows result[7:0] on LEDs after each
// calculation completes (result_valid pulse).
//
// Uses the shared calculator_driver for hardware access — no direct /dev/mem.
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <unistd.h>
#include <signal.h>
#include <string.h>
#include <time.h>

#include "calculator_driver.h"
#include "logger.h"

// Frame rate
#define FRAME_DELAY_US  33333   // ~30 Hz
#define ONESHOT_FRAMES  150     // 5 seconds at 30 Hz

// ============================================================================
// Global State
// ============================================================================
static volatile sig_atomic_t keep_running = 1;

static void signal_handler(int signum) {
    (void)signum;
    keep_running = 0;
}

// ============================================================================
// 30 Hz Random LED Pattern
// ============================================================================
// Generates pseudo-random LED patterns at 30 Hz by chaining FPGA calculator
// operations. Each result's low byte (result[7:0]) is latched onto LEDs by
// the calculator_led_display hardware module on every calc_done pulse.
//
// The PRNG uses a software xorshift32 to pick operands and operations,
// producing visually random LED flicker at exactly 30 frames per second.
// ============================================================================

static uint32_t xorshift_state = 0xDEADBEEF;

static uint32_t xorshift32(void) {
    uint32_t x = xorshift_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    xorshift_state = x;
    return x;
}

static void run_sequence(bool oneshot) {
    // Seed PRNG with something that varies per boot
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) == 0)
        xorshift_state ^= (uint32_t)(ts.tv_nsec);

    int frame = 0;
    float result;
    while (keep_running) {
        uint32_t rng = xorshift32();
        calculator_operation_t op = (calculator_operation_t)(rng & 0x3);
        float a = (float)((rng >> 2) & 0xFF) + 1.0f;
        float b = (float)((rng >> 10) & 0xFF) + 1.0f;

        // Result value is unused — we just want the LED side effect
        calculator_perform_operation(op, a, b, &result);
        usleep(FRAME_DELAY_US);

        if (oneshot && ++frame >= ONESHOT_FRAMES)
            break;
    }
}

// ============================================================================
// Main
// ============================================================================
int main(int argc, char *argv[]) {
    bool daemon_mode = false;
    bool oneshot_mode = false;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--daemon") == 0)
            daemon_mode = true;
        else if (strcmp(argv[i], "-o") == 0 || strcmp(argv[i], "--oneshot") == 0)
            oneshot_mode = true;
        else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            fprintf(stderr, "Usage: %s [-d|--daemon] [-o|--oneshot] [-h|--help]\n", argv[0]);
            fprintf(stderr, "Drives LEDs via FPGA calculator computations at ~30 Hz.\n");
            return 0;
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            return 1;
        }
    }

    struct sigaction sa = {0};
    sa.sa_handler = signal_handler;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    if (calculator_init() != 0) return 1;

    if (daemon_mode) {
        pid_t pid = fork();
        if (pid < 0) { calculator_cleanup(); return 1; }
        if (pid > 0) return 0;
        setsid();
    }

    LOG_INFO("boot_led: starting %s mode", oneshot_mode ? "oneshot" : "continuous");
    run_sequence(oneshot_mode);
    LOG_INFO("boot_led: shutting down");

    calculator_cleanup();
    return 0;
}
