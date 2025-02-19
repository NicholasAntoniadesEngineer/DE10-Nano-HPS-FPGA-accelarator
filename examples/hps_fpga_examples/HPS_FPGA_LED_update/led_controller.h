#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include "fpga_uio.h"
#include <stdbool.h>
#include <stddef.h>  // For size_t

typedef struct {
    fpga_uio_dev_t* uio_dev;
    size_t led_offset;
    int num_leds;
    bool active_low;
    volatile bool should_stop;
} led_controller_t;

// Initialize LED controller
int led_controller_init(led_controller_t* ctrl, fpga_uio_dev_t* uio_dev, 
                       size_t led_offset, int num_leds, bool active_low);

// Set specific LED state
int led_controller_set_led(led_controller_t* ctrl, int led_index, bool state);

// Set all LEDs at once using a bit mask
int led_controller_set_mask(led_controller_t* ctrl, uint32_t mask);

// Run the LED animation
int led_controller_run_animation(led_controller_t* ctrl, int num_cycles);

// Stop the animation
void led_controller_stop(led_controller_t* ctrl);

// Cleanup resources
void led_controller_cleanup(led_controller_t* ctrl);

#endif // LED_CONTROLLER_H 