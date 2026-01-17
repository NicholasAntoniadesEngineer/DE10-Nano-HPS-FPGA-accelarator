// ============================================================================
// Logging System Implementation
// ============================================================================
// Comprehensive logging with levels, timestamps, and file/line information
// ============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include "logger.h"

// ============================================================================
// Static Variables
// ============================================================================
static log_level_t current_level = LOG_DEFAULT_LEVEL;
static FILE *log_output = stderr;
static bool logging_enabled = true;

// Color codes for terminal output
#define COLOR_RESET   "\033[0m"
#define COLOR_ERROR   "\033[31m"  // Red
#define COLOR_WARN    "\033[33m"  // Yellow
#define COLOR_INFO    "\033[32m"  // Green
#define COLOR_DEBUG   "\033[36m"  // Cyan
#define COLOR_TRACE   "\033[35m"  // Magenta

// ============================================================================
// Initialize Logging System
// ============================================================================
void logger_init(log_level_t level, FILE *output_file) {
    current_level = level;
    log_output = (output_file != NULL) ? output_file : stderr;
    logging_enabled = true;
    
    LOG_INFO("Logging system initialized (level: %s)", logger_level_name(level));
}

// ============================================================================
// Set Log Level
// ============================================================================
void logger_set_level(log_level_t level) {
    log_level_t old_level = current_level;
    current_level = level;
    LOG_INFO("Log level changed: %s -> %s", logger_level_name(old_level), logger_level_name(level));
}

// ============================================================================
// Get Current Log Level
// ============================================================================
log_level_t logger_get_level(void) {
    return current_level;
}

// ============================================================================
// Enable/Disable Logging
// ============================================================================
void logger_enable(bool enable) {
    logging_enabled = enable;
    if (enable) {
        LOG_INFO("Logging enabled");
    }
}

// ============================================================================
// Set Output File
// ============================================================================
void logger_set_output(FILE *output_file) {
    log_output = (output_file != NULL) ? output_file : stderr;
    LOG_INFO("Log output redirected");
}

// ============================================================================
// Format Timestamp
// ============================================================================
void logger_format_timestamp(char *buffer, size_t buffer_size) {
    struct timeval tv;
    struct tm *tm_info;
    
    gettimeofday(&tv, NULL);
    tm_info = localtime(&tv.tv_sec);
    
    snprintf(buffer, buffer_size, "%04d-%02d-%02d %02d:%02d:%02d.%03ld",
             tm_info->tm_year + 1900,
             tm_info->tm_mon + 1,
             tm_info->tm_mday,
             tm_info->tm_hour,
             tm_info->tm_min,
             tm_info->tm_sec,
             tv.tv_usec / 1000);
}

// ============================================================================
// Get Log Level Name
// ============================================================================
const char *logger_level_name(log_level_t level) {
    switch (level) {
        case LOG_LEVEL_NONE:  return "NONE";
        case LOG_LEVEL_ERROR: return "ERROR";
        case LOG_LEVEL_WARN:  return "WARN";
        case LOG_LEVEL_INFO:  return "INFO";
        case LOG_LEVEL_DEBUG: return "DEBUG";
        case LOG_LEVEL_TRACE: return "TRACE";
        default:              return "UNKNOWN";
    }
}

// ============================================================================
// Get Log Level Color
// ============================================================================
static const char *logger_level_color(log_level_t level) {
    if (!LOG_ENABLE_COLOR) {
        return "";
    }
    
    switch (level) {
        case LOG_LEVEL_ERROR: return COLOR_ERROR;
        case LOG_LEVEL_WARN:  return COLOR_WARN;
        case LOG_LEVEL_INFO:  return COLOR_INFO;
        case LOG_LEVEL_DEBUG: return COLOR_DEBUG;
        case LOG_LEVEL_TRACE: return COLOR_TRACE;
        default:              return COLOR_RESET;
    }
}

// ============================================================================
// Main Logging Function
// ============================================================================
void logger_log(log_level_t level, const char *file, int line, const char *format, ...) {
    if (!logging_enabled || level > current_level) {
        return;
    }
    
    va_list args;
    char timestamp[64] = "";
    char file_line[128] = "";
    
    // Format timestamp
    if (LOG_ENABLE_TIMESTAMP) {
        logger_format_timestamp(timestamp, sizeof(timestamp));
    }
    
    // Format file and line
    if (LOG_ENABLE_FILE_LINE) {
        // Extract just the filename from the full path
        const char *filename = strrchr(file, '/');
        if (filename == NULL) {
            filename = strrchr(file, '\\');
        }
        if (filename == NULL) {
            filename = file;
        } else {
            filename++;  // Skip the slash
        }
        snprintf(file_line, sizeof(file_line), "%s:%d", filename, line);
    }
    
    // Get color code
    const char *color = logger_level_color(level);
    const char *reset = (LOG_ENABLE_COLOR && *color) ? COLOR_RESET : "";
    
    // Print log header
    if (LOG_ENABLE_TIMESTAMP && LOG_ENABLE_FILE_LINE) {
        fprintf(log_output, "%s[%s] [%s] %s%-5s%s ",
                color, timestamp, file_line, color, logger_level_name(level), reset);
    } else if (LOG_ENABLE_TIMESTAMP) {
        fprintf(log_output, "%s[%s] %s%-5s%s ",
                color, timestamp, color, logger_level_name(level), reset);
    } else if (LOG_ENABLE_FILE_LINE) {
        fprintf(log_output, "%s[%s] %s%-5s%s ",
                color, file_line, color, logger_level_name(level), reset);
    } else {
        fprintf(log_output, "%s%-5s%s ", color, logger_level_name(level), reset);
    }
    
    // Print log message
    va_start(args, format);
    vfprintf(log_output, format, args);
    va_end(args);
    
    fprintf(log_output, "\n");
    fflush(log_output);
}

// ============================================================================
// Hex Dump
// ============================================================================
void logger_hex_dump(log_level_t level, const char *label, const void *data, size_t len) {
    if (!logging_enabled || level > current_level) {
        return;
    }
    
    const uint8_t *bytes = (const uint8_t *)data;
    const char *color = logger_level_color(level);
    const char *reset = (LOG_ENABLE_COLOR && *color) ? COLOR_RESET : "";
    char timestamp[64] = "";
    
    if (LOG_ENABLE_TIMESTAMP) {
        logger_format_timestamp(timestamp, sizeof(timestamp));
        fprintf(log_output, "%s[%s] %s%-5s%s %s:\n",
                color, timestamp, color, logger_level_name(level), reset, label);
    } else {
        fprintf(log_output, "%s%-5s%s %s:\n",
                color, logger_level_name(level), reset, label);
    }
    
    for (size_t i = 0; i < len; i += 16) {
        fprintf(log_output, "  %04zX: ", i);
        
        // Print hex bytes
        for (size_t j = 0; j < 16; j++) {
            if (i + j < len) {
                fprintf(log_output, "%02X ", bytes[i + j]);
            } else {
                fprintf(log_output, "   ");
            }
            if (j == 7) {
                fprintf(log_output, " ");
            }
        }
        
        fprintf(log_output, " |");
        
        // Print ASCII characters
        for (size_t j = 0; j < 16 && (i + j) < len; j++) {
            char c = bytes[i + j];
            fprintf(log_output, "%c", (c >= 32 && c < 127) ? c : '.');
        }
        
        fprintf(log_output, "|\n");
    }
    
    fflush(log_output);
}

// ============================================================================
// Register Dump
// ============================================================================
void logger_register_dump(log_level_t level, const char *label, volatile uint32_t *regs, size_t count) {
    if (!logging_enabled || level > current_level) {
        return;
    }
    
    const char *color = logger_level_color(level);
    const char *reset = (LOG_ENABLE_COLOR && *color) ? COLOR_RESET : "";
    char timestamp[64] = "";
    
    if (LOG_ENABLE_TIMESTAMP) {
        logger_format_timestamp(timestamp, sizeof(timestamp));
        fprintf(log_output, "%s[%s] %s%-5s%s %s:\n",
                color, timestamp, color, logger_level_name(level), reset, label);
    } else {
        fprintf(log_output, "%s%-5s%s %s:\n",
                color, logger_level_name(level), reset, label);
    }
    
    for (size_t i = 0; i < count; i++) {
        uint32_t value = (regs != NULL) ? regs[i] : 0;
        float float_value = *((float *)&value);
        
        fprintf(log_output, "  [%02zX] 0x%08X  %10u  %+.6e  %+.6f\n",
                i * 4, value, value, float_value, float_value);
    }
    
    fflush(log_output);
}
