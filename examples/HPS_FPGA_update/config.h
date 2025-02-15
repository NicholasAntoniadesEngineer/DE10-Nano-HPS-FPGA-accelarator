#ifndef CONFIG_H
#define CONFIG_H

// UIO device configuration
#define UIO_DEVICE_PATH "/dev/uio0"
#define UIO_MAP_SIZE    0x1000
#define LED_OFFSET      0x0

// LED configuration
#define LED_COUNT       8
#define LED_ACTIVE_LOW  1

// Animation configuration
#define ANIMATION_DELAY_MS 100
#define ANIMATION_CYCLES   60

// Logging configuration
#define LOG_LEVEL_ERROR   3
#define LOG_LEVEL_WARNING 2
#define LOG_LEVEL_INFO    1
#define LOG_LEVEL_DEBUG   0

#define CURRENT_LOG_LEVEL LOG_LEVEL_INFO

#endif // CONFIG_H 