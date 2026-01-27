#include "led_controller.h"
#include "config.h"
#include <stdio.h>
#include <unistd.h>
#include <errno.h>

int led_controller_init(led_controller_t* ctrl, fpga_uio_dev_t* uio_dev, 
                       size_t led_offset, int num_leds, bool active_low) {
    if (!ctrl || !uio_dev || num_leds <= 0) {
        errno = EINVAL;
        return -1;
    }

    ctrl->uio_dev = uio_dev;
    ctrl->led_offset = led_offset;
    ctrl->num_leds = num_leds;
    ctrl->active_low = active_low;
    ctrl->should_stop = false;

    // Initialize all LEDs to off
    return led_controller_set_mask(ctrl, ctrl->active_low ? 0xFFFFFFFF : 0);
}

int led_controller_set_led(led_controller_t* ctrl, int led_index, bool state) {
    if (!ctrl || led_index < 0 || led_index >= ctrl->num_leds) {
        errno = EINVAL;
        return -1;
    }

    uint32_t current_mask;
    if (fpga_uio_read32(ctrl->uio_dev, ctrl->led_offset, &current_mask) != 0) {
        return -1;
    }

    if (state ^ ctrl->active_low) {
        current_mask |= (1 << led_index);
    } else {
        current_mask &= ~(1 << led_index);
    }

    return fpga_uio_write32(ctrl->uio_dev, ctrl->led_offset, current_mask);
}

int led_controller_set_mask(led_controller_t* ctrl, uint32_t mask) {
    if (!ctrl) {
        errno = EINVAL;
        return -1;
    }

    // If active low, invert the mask
    if (ctrl->active_low) {
        mask = ~mask;
    }

    // Only use the bits we need based on num_leds
    mask &= ((1 << ctrl->num_leds) - 1);

    return fpga_uio_write32(ctrl->uio_dev, ctrl->led_offset, mask);
}

int led_controller_run_animation(led_controller_t* ctrl, int num_cycles) {
    if (!ctrl || num_cycles <= 0) {
        errno = EINVAL;
        return -1;
    }

    int cycle_count = 0;
    uint32_t led_mask = 0x01;
    bool direction = false;  // false = right to left, true = left to right

    ctrl->should_stop = false;

    while (cycle_count < num_cycles && !ctrl->should_stop) {
        if (led_controller_set_mask(ctrl, led_mask) != 0) {
            return -1;
        }

        usleep(ANIMATION_DELAY_MS * 1000);

        if (!direction) {
            led_mask <<= 1;
            if (led_mask >= (uint32_t)(1U << (ctrl->num_leds - 1))) {
                direction = true;
            }
        } else {
            led_mask >>= 1;
            if (led_mask == 0x01) {
                direction = false;
                cycle_count++;
            }
        }
    }

    // Turn off all LEDs when done
    return led_controller_set_mask(ctrl, 0);
}

void led_controller_stop(led_controller_t* ctrl) {
    if (ctrl) {
        ctrl->should_stop = true;
    }
}

void led_controller_cleanup(led_controller_t* ctrl) {
    if (ctrl) {
        // Turn off all LEDs
        led_controller_set_mask(ctrl, 0);
        ctrl->uio_dev = NULL;
    }
} 