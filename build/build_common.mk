# ============================================================================
# Common Build Infrastructure
# ============================================================================
# Shared macros, timing, logging, and parallel task support
# Include this file in all Makefiles: include $(REPO_ROOT)/build/build_common.mk
# ============================================================================

# Prevent multiple inclusion
ifndef BUILD_COMMON_MK_INCLUDED
BUILD_COMMON_MK_INCLUDED := 1

# ============================================================================
# Path Detection
# ============================================================================

# Find repository root (look for .git directory)
ifndef REPO_ROOT
REPO_ROOT := $(shell \
    dir="$$(pwd)"; \
    while [ "$$dir" != "/" ]; do \
        if [ -d "$$dir/.git" ]; then \
            echo "$$dir"; \
            break; \
        fi; \
        dir="$$(dirname "$$dir")"; \
    done \
)
endif

# Build artifacts directory
BUILD_ARTIFACTS_DIR := $(REPO_ROOT)/build

# ============================================================================
# Colors for Output
# ============================================================================

# Terminal color codes (disabled if not a TTY)
ifneq ($(shell test -t 1 && echo yes),yes)
    # Not a terminal - disable colors
    COLOR_RESET :=
    COLOR_RED :=
    COLOR_GREEN :=
    COLOR_YELLOW :=
    COLOR_BLUE :=
    COLOR_MAGENTA :=
    COLOR_CYAN :=
    COLOR_BOLD :=
else
    COLOR_RESET := \033[0m
    COLOR_RED := \033[0;31m
    COLOR_GREEN := \033[0;32m
    COLOR_YELLOW := \033[1;33m
    COLOR_BLUE := \033[0;34m
    COLOR_MAGENTA := \033[0;35m
    COLOR_CYAN := \033[0;36m
    COLOR_BOLD := \033[1m
endif

# ============================================================================
# Logging Macros
# ============================================================================

# Current timestamp
TIMESTAMP = $(shell date '+%Y-%m-%d %H:%M:%S')

# Log levels
define log_info
    @echo -e "$(COLOR_CYAN)[INFO]$(COLOR_RESET) $(TIMESTAMP) | $1"
endef

define log_step
    @echo -e "$(COLOR_BLUE)[STEP]$(COLOR_RESET) $(TIMESTAMP) | $1"
endef

define log_success
    @echo -e "$(COLOR_GREEN)[OK]$(COLOR_RESET)   $(TIMESTAMP) | $1"
endef

define log_warning
    @echo -e "$(COLOR_YELLOW)[WARN]$(COLOR_RESET) $(TIMESTAMP) | $1"
endef

define log_error
    @echo -e "$(COLOR_RED)[ERROR]$(COLOR_RESET) $(TIMESTAMP) | $1"
endef

define log_header
    @echo ""
    @echo -e "$(COLOR_BOLD)============================================================================$(COLOR_RESET)"
    @echo -e "$(COLOR_BOLD) $1$(COLOR_RESET)"
    @echo -e "$(COLOR_BOLD)============================================================================$(COLOR_RESET)"
endef

define log_subheader
    @echo ""
    @echo -e "$(COLOR_CYAN)--- $1 ---$(COLOR_RESET)"
endef

# ============================================================================
# Build Timing Infrastructure
# ============================================================================

# Timing state directory
TIMING_DIR := $(BUILD_ARTIFACTS_DIR)/.timing

# Start timing a build phase
# Usage: $(call start_timing,phase_name)
define start_timing
    @mkdir -p $(TIMING_DIR)
    @date +%s > $(TIMING_DIR)/$1.start
    $(call log_step,Starting: $1)
endef

# End timing and report duration
# Usage: $(call end_timing,phase_name)
define end_timing
    @if [ -f "$(TIMING_DIR)/$1.start" ]; then \
        start_time=$$(cat $(TIMING_DIR)/$1.start); \
        end_time=$$(date +%s); \
        duration=$$((end_time - start_time)); \
        minutes=$$((duration / 60)); \
        seconds=$$((duration % 60)); \
        echo -e "$(COLOR_GREEN)[OK]$(COLOR_RESET)   $(TIMESTAMP) | Completed: $1 ($$minutes min $$seconds sec)"; \
        echo "$1,$$start_time,$$end_time,$$duration" >> $(TIMING_DIR)/build_times.csv; \
        rm -f $(TIMING_DIR)/$1.start; \
    else \
        echo -e "$(COLOR_YELLOW)[WARN]$(COLOR_RESET) $(TIMESTAMP) | No start time found for: $1"; \
    fi
endef

# Report all build timings
define report_build_times
    @echo ""
    @echo -e "$(COLOR_BOLD)Build Timing Summary$(COLOR_RESET)"
    @echo "---------------------------------------------"
    @if [ -f "$(TIMING_DIR)/build_times.csv" ]; then \
        while IFS=, read -r phase start end duration; do \
            minutes=$$((duration / 60)); \
            seconds=$$((duration % 60)); \
            printf "  %-30s %3dm %02ds\n" "$$phase:" "$$minutes" "$$seconds"; \
        done < $(TIMING_DIR)/build_times.csv; \
        total=$$(awk -F, '{sum += $$4} END {print sum}' $(TIMING_DIR)/build_times.csv); \
        total_min=$$((total / 60)); \
        total_sec=$$((total % 60)); \
        echo "---------------------------------------------"; \
        printf "  %-30s %3dm %02ds\n" "TOTAL:" "$$total_min" "$$total_sec"; \
    else \
        echo "  No timing data available"; \
    fi
    @echo ""
endef

# Clear timing data
define clear_timing
    @rm -rf $(TIMING_DIR)
    $(call log_info,Timing data cleared)
endef

# ============================================================================
# Parallel Task Infrastructure
# ============================================================================
# 
# This system allows defining tasks that can run in parallel or serial.
# Tasks are defined as make targets and can be grouped for parallel execution.
#
# Usage:
#   1. Define individual task targets (e.g., task-kernel, task-rootfs)
#   2. Use parallel-tasks or serial-tasks to run them
#
# Configuration:
#   PARALLEL_BUILD=0  : Force serial execution (for debugging)
#   PARALLEL_BUILD=1  : Enable parallel execution (default)
#   PARALLEL_JOBS=N   : Number of parallel jobs (default: 2)
# ============================================================================

# Parallel build configuration
PARALLEL_BUILD ?= 1
PARALLEL_JOBS ?= 2

# Execute tasks in parallel or serial based on configuration
# Usage: $(call run_tasks,task1 task2 task3)
define run_tasks
    @if [ "$(PARALLEL_BUILD)" = "1" ]; then \
        echo -e "$(COLOR_BLUE)[PARALLEL]$(COLOR_RESET) $(TIMESTAMP) | Running $(words $1) tasks in parallel (jobs=$(PARALLEL_JOBS))"; \
        echo -e "$(COLOR_BLUE)[PARALLEL]$(COLOR_RESET) $(TIMESTAMP) | Tasks: $1"; \
        $(MAKE) -j$(PARALLEL_JOBS) $1; \
    else \
        echo -e "$(COLOR_BLUE)[SERIAL]$(COLOR_RESET) $(TIMESTAMP) | Running $(words $1) tasks sequentially"; \
        echo -e "$(COLOR_BLUE)[SERIAL]$(COLOR_RESET) $(TIMESTAMP) | Tasks: $1"; \
        for task in $1; do \
            $(MAKE) $$task || exit 1; \
        done; \
    fi
endef

# Helper to run specific tasks in parallel (always parallel)
# Usage: $(call force_parallel,task1 task2,num_jobs)
define force_parallel
    @echo -e "$(COLOR_BLUE)[PARALLEL]$(COLOR_RESET) $(TIMESTAMP) | Running $(words $1) tasks in parallel (jobs=$2)"
    @$(MAKE) -j$2 $1
endef

# Helper to run specific tasks in serial (always serial)
# Usage: $(call force_serial,task1 task2)
define force_serial
    @echo -e "$(COLOR_BLUE)[SERIAL]$(COLOR_RESET) $(TIMESTAMP) | Running $(words $1) tasks sequentially"
    @for task in $1; do $(MAKE) $$task || exit 1; done
endef

# ============================================================================
# Dependency Tracking
# ============================================================================

# Check if any source file is newer than target
# Usage: $(call needs_rebuild,target_file,source_files)
# Returns: "yes" if rebuild needed, "" otherwise
define needs_rebuild
$(shell \
    target="$1"; \
    if [ ! -f "$$target" ]; then \
        echo "yes"; \
    else \
        for src in $2; do \
            if [ -f "$$src" ] && [ "$$src" -nt "$$target" ]; then \
                echo "yes"; \
                break; \
            fi; \
        done; \
    fi \
)
endef

# ============================================================================
# ccache Support
# ============================================================================

# Detect ccache
CCACHE := $(shell command -v ccache 2>/dev/null)

# ccache statistics helper
define show_ccache_stats
    @if [ -n "$(CCACHE)" ]; then \
        echo ""; \
        echo -e "$(COLOR_CYAN)ccache Statistics:$(COLOR_RESET)"; \
        ccache -s 2>/dev/null | head -10 || true; \
    fi
endef

# ============================================================================
# Utility Functions
# ============================================================================

# Get file size in human-readable format
define file_size
$(shell du -h "$1" 2>/dev/null | cut -f1 || echo "N/A")
endef

# Get file modification time
define file_mtime
$(shell date -r "$1" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$1" 2>/dev/null | cut -d. -f1 || echo "N/A")
endef

# Check if running as root
IS_ROOT := $(shell [ "$$(id -u)" -eq 0 ] && echo "yes" || echo "no")

# CPU count for parallel builds
NPROC := $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

endif # BUILD_COMMON_MK_INCLUDED
