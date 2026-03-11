// ============================================================================
// template — HPS Application Template
// ============================================================================
// Replace this file with your application logic.
// This skeleton provides signal handling, argument parsing, and logger setup
// following the conventions used by all other HPS applications.
//
// Usage:
//   template              # run continuously (default)
//   template --once       # run one iteration and exit (0 = success)
//   template --verbose    # enable verbose logging
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

#include "logger.h"

// ============================================================================
// Signal handling — clean shutdown
// ============================================================================
static volatile bool running = true;

static void handle_signal(int sig) {
    (void)sig;
    running = false;
}

// ============================================================================
// Main
// ============================================================================
int main(int argc, char *argv[]) {
    bool once    = false;
    bool verbose = false;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--once") == 0) {
            once = true;
        } else if (strcmp(argv[i], "--verbose") == 0 || strcmp(argv[i], "-v") == 0) {
            verbose = true;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            printf("Usage: %s [--once] [--verbose]\n", argv[0]);
            printf("  --once     Run one iteration then exit (0 = success)\n");
            printf("  --verbose  Enable verbose logging\n");
            return 0;
        } else {
            fprintf(stderr, "Unknown argument: %s\n", argv[i]);
            return 1;
        }
    }

    logger_init(verbose ? LOG_LEVEL_DEBUG : LOG_LEVEL_INFO);

    signal(SIGTERM, handle_signal);
    signal(SIGINT,  handle_signal);

    LOG_INFO("template: starting");

    // -------------------------------------------------------------------------
    // TODO: Initialize your hardware or resources here
    // -------------------------------------------------------------------------

    int errors = 0;

    while (running) {
        // ---------------------------------------------------------------------
        // TODO: Replace with your application logic
        // ---------------------------------------------------------------------
        LOG_DEBUG("template: iteration");

        if (once) break;
        sleep(1);
    }

    // -------------------------------------------------------------------------
    // TODO: Cleanup your hardware or resources here
    // -------------------------------------------------------------------------

    LOG_INFO("template: done (errors=%d)", errors);
    return (errors == 0) ? 0 : 1;
}
