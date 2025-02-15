#include "fpga_uio.h"
#include "led_controller.h"
#include "config.h"
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <string.h>

static led_controller_t led_ctrl;
static volatile sig_atomic_t running = 1;

void signal_handler(int signum) {
    running = 0;
    led_controller_stop(&led_ctrl);
}

void setup_signal_handlers(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = signal_handler;
    
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);
}

int main(int argc, char *argv[]) {
    fpga_uio_dev_t uio_dev;
    int ret = 0;

    // Setup signal handlers for clean shutdown
    setup_signal_handlers();

    // Initialize UIO device
    if (fpga_uio_init(&uio_dev, UIO_DEVICE_PATH, UIO_MAP_SIZE) != 0) {
        fprintf(stderr, "Failed to initialize UIO device\n");
        return 1;
    }

    // Initialize LED controller
    if (led_controller_init(&led_ctrl, &uio_dev, LED_OFFSET, 
                           LED_COUNT, LED_ACTIVE_LOW) != 0) {
        fprintf(stderr, "Failed to initialize LED controller\n");
        ret = 1;
        goto cleanup_uio;
    }

    printf("Starting LED animation. Press Ctrl+C to stop.\n");

    // Run animation until interrupted
    if (led_controller_run_animation(&led_ctrl, ANIMATION_CYCLES) != 0) {
        fprintf(stderr, "Error during LED animation\n");
        ret = 1;
        goto cleanup_led;
    }

cleanup_led:
    led_controller_cleanup(&led_ctrl);

cleanup_uio:
    fpga_uio_cleanup(&uio_dev);

    return ret;
} 