// ============================================================================
// Logging System for Calculator Driver and Tests
// ============================================================================
// Comprehensive logging with levels, timestamps, and file/line information
// ============================================================================

#ifndef CALCULATOR_LOGGER_H
#define CALCULATOR_LOGGER_H

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>
#include <sys/time.h>

// ============================================================================
// Log Levels
// ============================================================================
typedef enum {
    LOG_LEVEL_NONE = 0,
    LOG_LEVEL_ERROR = 1,
    LOG_LEVEL_WARN = 2,
    LOG_LEVEL_INFO = 3,
    LOG_LEVEL_DEBUG = 4,
    LOG_LEVEL_TRACE = 5
} log_level_t;

// ============================================================================
// Log Configuration
// ============================================================================
#define LOG_DEFAULT_LEVEL LOG_LEVEL_INFO
#define LOG_ENABLE_TIMESTAMP 1
#define LOG_ENABLE_FILE_LINE 1
#define LOG_ENABLE_COLOR 1

// ============================================================================
// Log Macros
// ============================================================================
#define LOG_ERROR(fmt, ...)   logger_log(LOG_LEVEL_ERROR, __FILE__, __LINE__, fmt, ##__VA_ARGS__)
#define LOG_WARN(fmt, ...)    logger_log(LOG_LEVEL_WARN, __FILE__, __LINE__, fmt, ##__VA_ARGS__)
#define LOG_INFO(fmt, ...)    logger_log(LOG_LEVEL_INFO, __FILE__, __LINE__, fmt, ##__VA_ARGS__)
#define LOG_DEBUG(fmt, ...)   logger_log(LOG_LEVEL_DEBUG, __FILE__, __LINE__, fmt, ##__VA_ARGS__)
#define LOG_TRACE(fmt, ...)   logger_log(LOG_LEVEL_TRACE, __FILE__, __LINE__, fmt, ##__VA_ARGS__)

// Specialized logging macros
#define LOG_REG_READ(offset, value)   LOG_DEBUG("REG READ:  offset=0x%02X, value=0x%08X", offset, value)
#define LOG_REG_WRITE(offset, value)  LOG_DEBUG("REG WRITE: offset=0x%02X, value=0x%08X", offset, value)
#define LOG_OP_START(op, a, b)         LOG_INFO("OP START:  operation=0x%X, operand_a=%.6f, operand_b=%.6f", op, a, b)
#define LOG_OP_COMPLETE(op, result)    LOG_INFO("OP COMPLETE: operation=0x%X, result=%.6f", op, result)
#define LOG_OP_ERROR(op, error_code)   LOG_ERROR("OP ERROR:  operation=0x%X, error_code=0x%08X", op, error_code)

// ============================================================================
// Function Prototypes
// ============================================================================

// Initialize logging system
void logger_init(log_level_t level, FILE *output_file);

// Set log level
void logger_set_level(log_level_t level);

// Get current log level
log_level_t logger_get_level(void);

// Enable/disable logging
void logger_enable(bool enable);

// Set output file (NULL for stderr)
void logger_set_output(FILE *output_file);

// Main logging function
void logger_log(log_level_t level, const char *file, int line, const char *format, ...);

// Log raw data (hex dump)
void logger_hex_dump(log_level_t level, const char *label, const void *data, size_t len);

// Log register dump
void logger_register_dump(log_level_t level, const char *label, volatile uint32_t *regs, size_t count);

// Format timestamp
void logger_format_timestamp(char *buffer, size_t buffer_size);

// Get log level name
const char *logger_level_name(log_level_t level);

// ============================================================================
// Initialization Helper
// ============================================================================
#define LOGGER_INIT_DEFAULT() logger_init(LOG_DEFAULT_LEVEL, stderr)
#define LOGGER_INIT_FILE(file) logger_init(LOG_DEFAULT_LEVEL, file)
#define LOGGER_INIT_LEVEL(level) logger_init(level, stderr)

#endif // CALCULATOR_LOGGER_H
