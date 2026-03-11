################################################
#
# Makefile to Manage QuartusII/QSys Design
#
# Copyright Altera (c) 2016
# All Rights Reserved
#
################################################

SHELL := /bin/bash

.SUFFIXES: # Delete the default suffixes

################################################
# Tools

CAT := cat
CD := cd
CHMOD := chmod
CP := cp -rf
ECHO := echo
DATE := date
FIND := find
GREP := grep
HEAD := head
MKDIR := mkdir -p
MV := mv
RM := rm -rf
SED := sed
TAR := tar
TOUCH := touch
WHICH := which

# Helpful Macros
SPACE := $(empty) $(empty)

# Colors for output  
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m

ifndef COMSPEC
ifdef ComSpec
COMSPEC = $(ComSpec)
endif # ComSpec
endif # COMSPEC

ifdef COMSPEC # if Windows OS
IS_WINDOWS_HOST := 1
endif

ifeq ($(IS_WINDOWS_HOST),1)
ifneq ($(shell $(WHICH) cygwin1.dll 2>/dev/null),)
IS_CYGWIN_HOST := 1
endif
endif

################################################
# Fast-path for Clean Targets
################################################
# Skip expensive tool detection when running clean targets.
# This prevents hangs during 'make clean' operations.
################################################

CLEAN_TARGETS := clean clean-all clear-tool-cache show-tool-cache

# Check if we're only running clean targets (no tool detection needed)
ifneq ($(filter $(CLEAN_TARGETS),$(MAKECMDGOALS)),)
ifeq ($(filter-out $(CLEAN_TARGETS),$(MAKECMDGOALS)),)
SKIP_TOOL_DETECTION := 1
endif
endif

################################################
# Quartus Parallel Compilation
################################################
# Quartus Prime supports parallel compilation using multiple CPU cores.
# This can significantly reduce FPGA compilation time (30-50% faster).
#
# Configuration:
#   QUARTUS_PARALLEL_JOBS=N : Number of parallel jobs (default: auto-detect)
#   QUARTUS_PARALLEL_JOBS=1 : Disable parallel compilation
#
# Note: Quartus uses environment variable NUM_PARALLEL_PROCESSORS
################################################

# Auto-detect CPU count for parallel Quartus compilation
NPROC := $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
QUARTUS_PARALLEL_JOBS ?= $(NPROC)

# Export for Quartus to use
export NUM_PARALLEL_PROCESSORS := $(QUARTUS_PARALLEL_JOBS)

################################################
# Tool Detection with Caching
################################################
# Tool paths are cached to avoid expensive find operations on every make invocation.
# Cache is stored in .tool_cache.mk and expires after 1 hour.
#
# Configuration:
#   TOOL_CACHE_DISABLE=1  : Disable caching (always detect)
#   make clear-tool-cache : Manually clear the cache
################################################

# Always define these (needed for clean targets)
TOOL_CACHE_FILE := $(CURDIR)/.tool_cache.mk
TOOL_CACHE_MAX_AGE_MINUTES := 60

# Skip expensive tool detection for clean targets (fast path)
ifneq ($(SKIP_TOOL_DETECTION),1)

# Check if cache exists and is recent (less than TOOL_CACHE_MAX_AGE_MINUTES old)
TOOL_CACHE_VALID := $(shell \
	if [ -f "$(TOOL_CACHE_FILE)" ] && [ "$(TOOL_CACHE_DISABLE)" != "1" ]; then \
		cache_age=$$(find "$(TOOL_CACHE_FILE)" -mmin -$(TOOL_CACHE_MAX_AGE_MINUTES) 2>/dev/null); \
		if [ -n "$$cache_age" ]; then \
			echo "1"; \
		fi; \
	fi \
)

# Load cached tool paths if cache is valid
ifeq ($(TOOL_CACHE_VALID),1)
-include $(TOOL_CACHE_FILE)
TOOL_CACHE_LOADED := 1
endif

# Only run expensive tool detection if cache not loaded
ifneq ($(TOOL_CACHE_LOADED),1)

# Check for Quartus tools
# On Windows, quartus_sh.exe is the main command-line tool
# On Unix/Linux, quartus_sh is available
# From WSL, we can also use Windows Quartus installations
QUARTUS_SH := $(shell $(WHICH) quartus_sh 2>/dev/null)
ifneq ($(QUARTUS_SH),)
HAVE_QUARTUS := 1
else
QUARTUS_SH := $(shell $(WHICH) quartus_sh.exe 2>/dev/null)
ifneq ($(QUARTUS_SH),)
HAVE_QUARTUS := 1
else
QUARTUS_SH := $(shell $(WHICH) quartus 2>/dev/null)
ifneq ($(QUARTUS_SH),)
HAVE_QUARTUS := 1
else
# Try common Windows Quartus installation paths (for WSL/MINGW64/Git Bash)
# Use find to search for quartus_sh.exe in common installation directories
# MINGW64/Git Bash uses /c/, WSL uses /mnt/c/
QUARTUS_SH := $(shell \
	for base in /c /mnt/c; do \
		for dir in intelFPGA_lite intelFPGA altera; do \
			if [ -d "$$base/$$dir" ]; then \
				result=$$(find "$$base/$$dir" -name "quartus_sh.exe" -type f 2>/dev/null | head -1); \
				if [ -n "$$result" ]; then \
					echo "$$result"; \
					exit 0; \
				fi; \
			fi; \
		done; \
	done \
)
ifneq ($(QUARTUS_SH),)
HAVE_QUARTUS := 1
endif
endif
endif
endif

# Check for QSys tools (qsys-generate is required for QSys generation)
# On Windows, qsys-generate.exe is the command-line tool
# On Unix/Linux, qsys-generate is available
# From WSL, we can also use Windows QSys installations
QSYS_GENERATE := $(shell $(WHICH) qsys-generate 2>/dev/null)
ifneq ($(QSYS_GENERATE),)
HAVE_QSYS_GENERATE := 1
else
QSYS_GENERATE := $(shell $(WHICH) qsys-generate.exe 2>/dev/null)
ifneq ($(QSYS_GENERATE),)
HAVE_QSYS_GENERATE := 1
else
# Try common Windows QSys installation paths (for WSL)
# Use find to search for qsys-generate.exe in common installation directories
QSYS_GENERATE := $(shell \
	for base in /c /mnt/c; do \
		for dir in intelFPGA_lite intelFPGA altera; do \
			if [ -d "$$base/$$dir" ]; then \
				result=$$(find "$$base/$$dir" -name "qsys-generate.exe" -type f 2>/dev/null | head -1); \
				if [ -n "$$result" ]; then \
					echo "$$result"; \
					exit 0; \
				fi; \
			fi; \
		done; \
	done \
)
ifneq ($(QSYS_GENERATE),)
HAVE_QSYS_GENERATE := 1
endif
endif
endif

# Save detected tool paths to cache (only if we did detection)
$(shell \
	echo "# Tool cache - auto-generated, do not edit" > $(TOOL_CACHE_FILE); \
	echo "# Generated: $$(date)" >> $(TOOL_CACHE_FILE); \
	echo "# Cache expires after $(TOOL_CACHE_MAX_AGE_MINUTES) minutes" >> $(TOOL_CACHE_FILE); \
	echo "" >> $(TOOL_CACHE_FILE); \
	echo "QUARTUS_SH := $(QUARTUS_SH)" >> $(TOOL_CACHE_FILE); \
	echo "HAVE_QUARTUS := $(HAVE_QUARTUS)" >> $(TOOL_CACHE_FILE); \
	echo "QSYS_GENERATE := $(QSYS_GENERATE)" >> $(TOOL_CACHE_FILE); \
	echo "HAVE_QSYS_GENERATE := $(HAVE_QSYS_GENERATE)" >> $(TOOL_CACHE_FILE); \
)

endif # TOOL_CACHE_LOADED

# HAVE_QSYS is set if we have either quartus or qsys-generate
ifeq ($(HAVE_QUARTUS),1)
HAVE_QSYS := 1
endif
ifeq ($(HAVE_QSYS_GENERATE),1)
HAVE_QSYS := 1
endif

# Set Quartus tool variables (use detected path or default to command name)
# This allows using Windows Quartus from WSL/MINGW64
ifeq ($(HAVE_QUARTUS),1)
ifneq ($(QUARTUS_SH),)
QUARTUS_SH_CMD := $(QUARTUS_SH)
# Handle both .exe and non-.exe cases for Windows compatibility
QUARTUS_STP_CMD := $(subst quartus_sh.exe,quartus_stp.exe,$(subst quartus_sh,quartus_stp,$(QUARTUS_SH)))
QUARTUS_CPF_CMD := $(subst quartus_sh.exe,quartus_cpf.exe,$(subst quartus_sh,quartus_cpf,$(QUARTUS_SH)))
QUARTUS_STA_CMD := $(subst quartus_sh.exe,quartus_sta.exe,$(subst quartus_sh,quartus_sta,$(QUARTUS_SH)))
QUARTUS_PGM_CMD := $(subst quartus_sh.exe,quartus_pgm.exe,$(subst quartus_sh,quartus_pgm,$(QUARTUS_SH)))
QUARTUS_MAP_CMD := $(subst quartus_sh.exe,quartus_map.exe,$(subst quartus_sh,quartus_map,$(QUARTUS_SH)))
QUARTUS_CDB_CMD := $(subst quartus_sh.exe,quartus_cdb.exe,$(subst quartus_sh,quartus_cdb,$(QUARTUS_SH)))
else
# Fallback to command name if path not detected
QUARTUS_SH_CMD := quartus_sh
QUARTUS_STP_CMD := quartus_stp
QUARTUS_CPF_CMD := quartus_cpf
QUARTUS_STA_CMD := quartus_sta
QUARTUS_PGM_CMD := quartus_pgm
QUARTUS_MAP_CMD := quartus_map
QUARTUS_CDB_CMD := quartus_cdb
endif
else
# Set defaults even if Quartus not detected (for error messages)
QUARTUS_SH_CMD := quartus_sh
QUARTUS_STP_CMD := quartus_stp
QUARTUS_CPF_CMD := quartus_cpf
QUARTUS_STA_CMD := quartus_sta
QUARTUS_PGM_CMD := quartus_pgm
QUARTUS_MAP_CMD := quartus_map
QUARTUS_CDB_CMD := quartus_cdb
endif

# Set QSys tool variables (use detected path or default to command name)
# This allows using Windows QSys tools from WSL
ifeq ($(HAVE_QSYS_GENERATE),1)
ifneq ($(QSYS_GENERATE),)
QSYS_GENERATE_CMD := $(QSYS_GENERATE)
QSYS_EDIT_CMD := $(patsubst %qsys-generate%,%qsys-edit%,$(QSYS_GENERATE))
QSYS_SCRIPT_CMD := $(patsubst %qsys-generate%,%qsys-script%,$(QSYS_GENERATE))
else
# Fallback to command name if path not detected
QSYS_GENERATE_CMD := qsys-generate
QSYS_EDIT_CMD := qsys-edit
QSYS_SCRIPT_CMD := qsys-script
endif
else
# Set defaults even if QSys not detected (for error messages)
QSYS_GENERATE_CMD := qsys-generate
QSYS_EDIT_CMD := qsys-edit
QSYS_SCRIPT_CMD := qsys-script
endif

endif # SKIP_TOOL_DETECTION (end of fast-path skip for clean targets)

################################################

################################################
# Directory structure
HDL_DIR := hdl
QUARTUS_DIR := quartus
QSYS_DIR := $(QUARTUS_DIR)/qsys
BUILD_DIR := build
GENERATED_DIR := generated
DOCS_DIR := docs

# Fast build targets that don't require SoC EDS
FAST_TARGETS := fast fast-flash fast-rbf qsys-generate quartus-compile qsys_compile quartus_compile qsys_edit quartus_edit sof rbf

################################################
.PHONY: default
default: help

.PHONY: check-tools
check-tools:
	@$(ECHO) "==========================================="
	@$(ECHO) "Checking for Quartus and QSys tools"
	@$(ECHO) "==========================================="
	@$(ECHO) ""
	@$(ECHO) "Quartus detection:"
	@if [ -n "$(QUARTUS_SH)" ]; then \
		$(ECHO) "  [OK] Found: $(QUARTUS_SH)"; \
		$(ECHO) "  HAVE_QUARTUS: $(HAVE_QUARTUS)"; \
	else \
		$(ECHO) "  [NOT FOUND] Not found in PATH or standard locations"; \
	fi
	@$(ECHO) ""
	@$(ECHO) "QSys detection:"
	@if [ -n "$(QSYS_GENERATE)" ]; then \
		$(ECHO) "  [OK] Found: $(QSYS_GENERATE)"; \
		$(ECHO) "  HAVE_QSYS_GENERATE: $(HAVE_QSYS_GENERATE)"; \
	else \
		$(ECHO) "  [NOT FOUND] Not found in PATH or standard locations"; \
	fi
	@$(ECHO) ""
	@$(ECHO) "Searching common installation directories..."
	@for base in /c /mnt/c; do \
		for dir in intelFPGA_lite intelFPGA altera; do \
			if [ -d "$$base/$$dir" ]; then \
				$(ECHO) "  Found directory: $$base/$$dir"; \
			fi; \
		done; \
	done
	@$(ECHO) ""
	@$(ECHO) "If tools are not found, you can manually set:"
	@$(ECHO) "  export PATH=\$$PATH:/path/to/quartus/bin64"
	@$(ECHO) ""
	@$(ECHO) ""

.PHONY: soceds-find
soceds-find:
	@$(ECHO) "==========================================="
	@$(ECHO) "Finding SoC EDS Installation"
	@$(ECHO) "==========================================="
	@$(ECHO) ""
	@set -e; \
		tmp_script="./scripts/.find_soceds.normalized.$$$$"; \
		trap 'rm -f "$$tmp_script"' EXIT; \
		tr -d '\015' < "./scripts/find_soceds.sh" > "$$tmp_script" 2>/dev/null || cat "./scripts/find_soceds.sh" > "$$tmp_script"; \
		chmod +x "$$tmp_script"; \
		bash "$$tmp_script" || { \
			$(ECHO) "ERROR: Could not find SoC EDS installation."; \
			$(ECHO) ""; \
			$(ECHO) "Install SoC EDS from:"; \
			$(ECHO) "  https://www.intel.com/content/www/us/en/programmable/downloads/download-center.html"; \
			$(ECHO) ""; \
			$(ECHO) "Then set SOCEDS_DEST_ROOT to the 'embedded' directory, e.g.:"; \
			$(ECHO) "  export SOCEDS_DEST_ROOT=\"/mnt/c/intelFPGA/20.1/embedded\""; \
			exit 1; \
		}

################################################

################################################
# Build all components in correct order:
# 1. QSys generation (required for everything, but only if QSys file exists)
# 2. FPGA bitstream (if Quartus available)
# 3. HPS software (if SoC EDS available)
# Note: ALL_DEPS is populated after QSYS_FILE and other variables are defined (see below)
ALL_DEPS :=
################################################

################################################
# Build Everything Target
# This target builds ALL components that are possible with available tools
.PHONY: everything
everything:
	@$(ECHO) "==========================================="
	@$(ECHO) "Building FPGA Components"
	@$(ECHO) "==========================================="
	@$(ECHO) ""
	@$(ECHO) "Step 1: QSys Generation"
	@$(ECHO) "-------------------------------------------"
ifneq ($(QSYS_FILE),)
	@$(ECHO) "QSys file found: $(QSYS_FILE)"
	@$(MAKE) qsys-generate
else
	@$(ECHO) "WARNING: No QSys file found in $(QSYS_DIR)/"
	@$(ECHO) "Skipping QSys generation"
endif
	@$(ECHO) ""
	@$(ECHO) "Step 2: FPGA Bitstream Generation"
	@$(ECHO) "-------------------------------------------"
ifeq ($(HAVE_QUARTUS),1)
ifneq ($(QUARTUS_BASE),)
	@$(MAKE) sof rbf
	@$(ECHO) "FPGA bitstream generation complete"
else
	@$(ECHO) "WARNING: No Quartus project file found in $(QUARTUS_DIR)/"
	@$(ECHO) "Skipping FPGA bitstream generation"
endif
else
	@$(ECHO) "WARNING: Quartus not found in PATH — skipping FPGA bitstream"
endif
	@$(ECHO) ""
	@$(ECHO) "==========================================="
	@$(ECHO) "FPGA build summary"
	@$(ECHO) "==========================================="
	@$(ECHO) ""
ifneq ($(QSYS_FILE),)
	@$(ECHO) "[OK] QSys generation: Complete"
	@if [ -f "$(QSYS_SOPCINFO)" ]; then $(ECHO) "  - SOPCINFO: $(QSYS_SOPCINFO)"; fi
else
	@$(ECHO) "[SKIP] QSys generation: Skipped (no QSys file)"
endif
	@$(ECHO) ""
ifeq ($(HAVE_QUARTUS),1)
ifneq ($(QUARTUS_BASE),)
	@$(ECHO) "[OK] FPGA bitstream: Complete"
	@if [ -f "$(QUARTUS_SOF)" ]; then $(ECHO) "  - SOF: $(QUARTUS_SOF)"; fi
	@if [ -f "$(QUARTUS_RBF)" ]; then $(ECHO) "  - RBF: $(QUARTUS_RBF)"; fi
else
	@$(ECHO) "[SKIP] FPGA bitstream: Skipped (no Quartus project)"
endif
else
	@$(ECHO) "[SKIP] FPGA bitstream: Skipped (Quartus not available)"
endif
	@$(ECHO) ""
	@$(ECHO) "To build HPS software and SD image, run from the repo root:"
	@$(ECHO) "  make sd-image"
	@$(ECHO) ""
	@$(ECHO) "[DONE]"
	fi
	@$(ECHO) ""
	@$(ECHO) "==========================================="
	@$(ECHO) "Everything build complete!"
	@$(ECHO) "==========================================="

HELP_TARGETS += everything
everything.HELP := Build FPGA components: QSys generation + Quartus compile + RBF

################################################
# Fast Iteration Targets (FPGA only, no HPS software)
.PHONY: fast
ifneq ($(QSYS_FILE),)
ifneq ($(QUARTUS_BASE),)
fast: qsys-generate quartus-compile
	@$(ECHO) "==========================================="
	@$(ECHO) "Fast build complete (FPGA only)"
	@$(ECHO) "SOF file: $(BUILD_DIR)/output_files/$(QUARTUS_BASE).sof"
	@$(ECHO) "==========================================="
else
fast:
	@$(ECHO) "ERROR: No Quartus project file found"
	@$(ECHO) "Searched: $(QUARTUS_DIR)/"
	@exit 1
endif
else
fast:
	@$(ECHO) "ERROR: No QSys file found"
	@$(ECHO) "Searched: $(QSYS_DIR)/"
		@$(ECHO) "Please create a QSys file in quartus/qsys/ directory"
	@exit 1
endif

.PHONY: fast-flash
fast-flash: fast
ifneq ($(QUARTUS_BASE),)
	@$(ECHO) "Programming FPGA via JTAG..."
	quartus_pgm -c USB-Blaster -m JTAG -o "p;$(BUILD_DIR)/output_files/$(QUARTUS_BASE).sof"
else
	@$(ECHO) "ERROR: No Quartus project file found"
	@exit 1
endif

.PHONY: fast-rbf
fast-rbf: fast
ifneq ($(QUARTUS_BASE),)
	@$(ECHO) "Generating RBF file..."
	quartus_cpf -c $(QUARTUS_CPF_ARGS) $(BUILD_DIR)/output_files/$(QUARTUS_BASE).sof $(BUILD_DIR)/output_files/$(QUARTUS_BASE).rbf
	@$(ECHO) "RBF file: $(BUILD_DIR)/output_files/$(QUARTUS_BASE).rbf"
else
	@$(ECHO) "ERROR: No Quartus project file found"
	@exit 1
endif

.PHONY: qsys-generate
qsys-generate:
	@if [ -z "$(strip $(QSYS_FILE))" ]; then \
		$(ECHO) "WARNING: No QSys file found in $(QSYS_DIR)"; \
		$(ECHO) "Searched for: *top*.qsys, *main*.qsys, *soc*.qsys, *.qsys"; \
		$(ECHO) "Directory contents:"; \
		ls -la $(QSYS_DIR)/*.qsys 2>/dev/null || $(ECHO) "  (no .qsys files found)"; \
		$(ECHO) "Skipping QSys generation. Create a QSys file to enable this step."; \
		$(ECHO) ""; \
	else \
		$(ECHO) "Found QSys file: $(QSYS_FILE)"; \
		$(MAKE) qsys_compile; \
	fi

.PHONY: quartus-compile
quartus-compile: quartus_compile
################################################

################################################
# Target Stamping

SOCEDS_VERSION := $(if $(wildcard $(SOCEDS_DEST_ROOT)/version.txt),$(shell $(CAT) $(SOCEDS_DEST_ROOT)/version.txt 2>/dev/null | $(GREP) Version | $(HEAD) -n1 | $(SED) -e 's,^Version[: \t=]*\([0-9.]*\).*,\1,g' 2>/dev/null))

define get_stamp_dir
stamp$(if $(SOCEDS_VERSION),/$(SOCEDS_VERSION))
endef

define get_stamp_target
$(get_stamp_dir)$(if $1,/$1.stamp,$(error ERROR: Arg 1 missing to $0 function))
endef

define stamp_target
@$(MKDIR) $(@D)
@$(TOUCH) $@
endef

HELP_TARGETS += clean
clean.HELP := Remove all build artifacts and generated files (including Platform Designer outputs)

.PHONY: clean
clean:
	@$(ECHO) "Cleaning all build artifacts and generated files..."
	@$(ECHO) "  - Build artifacts (stamps, databases, reports)..."
	@$(RM) $(get_stamp_dir)
	@$(RM) $(BUILD_DIR)/output_files $(BUILD_DIR)/reports $(BUILD_DIR)/db
	@$(RM) hps_isw_handoff
	@$(RM) $(wildcard $(BUILD_DIR)/output_files/*.sof $(BUILD_DIR)/output_files/*.rbf)
	@$(RM) $(wildcard $(QUARTUS_DIR)/db $(QUARTUS_DIR)/incremental_db)
	@$(RM) $(wildcard $(QUARTUS_DIR)/*.rpt $(QUARTUS_DIR)/*.summary $(QUARTUS_DIR)/*.done)
	@$(RM) $(wildcard $(QUARTUS_DIR)/*.jdi $(QUARTUS_DIR)/*.pin $(QUARTUS_DIR)/*.qws)
	@$(RM) $(wildcard $(QUARTUS_DIR)/*.sopcinfo $(QUARTUS_DIR)/*.sopcinfo.bak)
	@$(ECHO) "  - Platform Designer (QSys) generated files..."
	@$(RM) $(wildcard .qsys_edit)
	@$(RM) $(wildcard $(GENERATED_DIR)/*/synthesis $(GENERATED_DIR)/*/synth)
	@$(RM) $(wildcard $(GENERATED_DIR)/*.sopcinfo)
	@$(RM) $(wildcard $(QSYS_DIR)/*/synthesis $(QSYS_DIR)/*/synth)
	@$(RM) $(wildcard $(QSYS_DIR)/*.sopcinfo $(QSYS_DIR)/*.qip)
	@if [ -n "$(QSYS_BASE)" ]; then \
		$(RM) $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)) $(wildcard $(QSYS_DIR)/$(QSYS_BASE)); \
	fi
	@$(ECHO) "  - Device tree files..."
	@$(RM) $(wildcard $(GENERATED_DIR)/*.dts $(GENERATED_DIR)/*.dtb)
	@$(ECHO) "Build artifacts and generated files cleaned successfully"
	@$(ECHO) "  Run 'make all' to rebuild everything"

HELP_TARGETS += clean-all
clean-all.HELP := Deep clean including all cached and downloaded content

.PHONY: clean-all
clean-all: clean
	@$(ECHO) "==========================================="
	@$(ECHO) "Performing deep clean..."
	@$(ECHO) "==========================================="
	@$(ECHO) "Removing QSys generated directories..."
	@$(RM) $(GENERATED_DIR)
	@$(ECHO) "Removing all Quartus project cache..."
	@$(RM) $(wildcard $(QUARTUS_DIR)/db $(QUARTUS_DIR)/incremental_db $(QUARTUS_DIR)/greybox_tmp)
	@$(RM) $(wildcard $(QUARTUS_DIR)/simulation)
	@$(ECHO) "Removing HPS handoff files..."
	@$(RM) $(wildcard hps_isw_handoff)
	@$(RM) $(wildcard quartus/hps_isw_handoff)
	@$(ECHO) "Removing tool cache..."
	@$(RM) $(TOOL_CACHE_FILE)
	@$(ECHO) "==========================================="
	@$(ECHO) "Deep clean complete!"
	@$(ECHO) "==========================================="

HELP_TARGETS += clear-tool-cache
clear-tool-cache.HELP := Clear cached tool paths (Quartus, QSys) to force re-detection

.PHONY: clear-tool-cache
clear-tool-cache:
	@$(ECHO) "Clearing tool cache..."
	@$(RM) $(TOOL_CACHE_FILE)
	@$(ECHO) "Tool cache cleared"
	@$(ECHO) "Next 'make' invocation will re-detect tool paths"

HELP_TARGETS += show-tool-cache
show-tool-cache.HELP := Display cached tool paths and cache status

.PHONY: show-tool-cache
show-tool-cache:
	@$(ECHO) "==========================================="
	@$(ECHO) "Tool Detection Cache Status"
	@$(ECHO) "==========================================="
ifeq ($(TOOL_CACHE_LOADED),1)
	@$(ECHO) "Cache status: LOADED (using cached paths)"
	@$(ECHO) "Cache file:   $(TOOL_CACHE_FILE)"
	@$(ECHO) "Cache age:    $$(stat -c %y "$(TOOL_CACHE_FILE)" 2>/dev/null | cut -d. -f1 || date -r "$(TOOL_CACHE_FILE)" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "unknown")"
	@$(ECHO) ""
	@$(ECHO) "Cached values:"
	@$(CAT) $(TOOL_CACHE_FILE) 2>/dev/null | $(GREP) -v "^#" | $(GREP) -v "^$$" || $(ECHO) "  (cache file not found)"
else
	@$(ECHO) "Cache status: NOT LOADED (detected fresh)"
	@$(ECHO) "Reason:       Cache missing, stale, or disabled"
endif
	@$(ECHO) ""
	@$(ECHO) "Current tool paths:"
	@$(ECHO) "  QUARTUS_SH:     $(QUARTUS_SH)"
	@$(ECHO) "  HAVE_QUARTUS:   $(HAVE_QUARTUS)"
	@$(ECHO) "  QSYS_GENERATE:  $(QSYS_GENERATE)"
	@$(ECHO) "  HAVE_QSYS:      $(HAVE_QSYS)"
	@$(ECHO) ""
	@$(ECHO) "To disable caching: make TOOL_CACHE_DISABLE=1 <target>"
	@$(ECHO) "To clear cache:     make clear-tool-cache"
################################################


################################################
# Archiving & Cleaning your QuartusII/QSys Project

AR_TIMESTAMP := $(if $(SOCEDS_VERSION),$(subst .,_,$(SOCEDS_VERSION))_)$(subst $(SPACE),,$(shell $(DATE) +%m%d%Y_%k%M%S))

AR_DIR := tgz
AR_FILE := $(AR_DIR)/$(basename $(firstword $(wildcard *.qpf)))_$(AR_TIMESTAMP).tar.gz

AR_REGEX += \
	Makefile ip readme.txt ds5 \
	altera_avalon* *.qpf *.qsf *.sdc *.v *.sv *.vhd *.qsys *.tcl *.terp *.stp \
	*.sed quartus.ini *.sof *.rbf *.sopcinfo *.jdi output_files \
	hps_isw_handoff */*.svd */synthesis/*.svd */synth/*.svd *.dts *.dtb *.xml

AR_FILTER_OUT += %_tb.qsys
################################################



################################################
# Build QuartusII/QSys Project
#

#############
# QSys
# Only require QSYS_FILE for targets that need it (not for clean/scrub/help)
# Allow QSYS_FILE to be empty - targets will handle it gracefully
# Search for QSys files in quartus/qsys/ directory
QSYS_FILE := $(firstword \
	$(wildcard $(QSYS_DIR)/*top*.qsys) \
	$(wildcard $(QSYS_DIR)/*main*.qsys) \
	$(wildcard $(QSYS_DIR)/*soc*.qsys) \
	$(wildcard $(QSYS_DIR)/*.qsys) \
)
QSYS_DEPS += $(wildcard $(QSYS_DIR)/*.qsys)
# Only define QSys variables if QSYS_FILE exists
# Check both generated/ (command-line) and qsys/ (GUI) locations
ifneq ($(QSYS_FILE),)
QSYS_BASE := $(basename $(notdir $(QSYS_FILE)))
QSYS_QIP := $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/synthesis/$(QSYS_BASE).qip) $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/$(QSYS_BASE).qip) $(wildcard $(QSYS_DIR)/$(QSYS_BASE)/synthesis/$(QSYS_BASE).qip)
QSYS_SOPCINFO := $(GENERATED_DIR)/$(QSYS_BASE).sopcinfo
else
# Dummy values for clean targets
QSYS_BASE := 
QSYS_QIP := 
QSYS_SOPCINFO := 
endif
QSYS_STAMP := $(call get_stamp_target,qsys)

# Populate ALL_DEPS now that QSYS_FILE is defined
ifneq ($(strip $(QSYS_FILE)),)
ALL_DEPS += qsys-generate
endif

# Build FPGA bitstream (if Quartus available)
ifeq ($(HAVE_QUARTUS),1)
ALL_DEPS += sof rbf
endif

# Under cygwin, ensure TMP env variable is not a cygwin style path
# before calling ip-generate
ifeq ($(IS_CYGWIN_HOST),1)
ifneq ($(shell $(WHICH) cygpath 2>/dev/null),)
SET_QSYS_GENERATE_ENV = TMP="$(shell cygpath -m "$(TMP)")"
endif
endif

.PHONY: qsys_compile
qsys_compile: $(QSYS_STAMP)

ifeq ($(HAVE_QSYS),1)
ifneq ($(QSYS_FILE),)
$(QSYS_SOPCINFO) $(QSYS_QIP): $(QSYS_STAMP)
endif
endif

ifneq ($(QSYS_FILE),)
QSYS_CHECK_SCRIPT := qsys_check.sh
$(QSYS_STAMP): $(QSYS_DEPS) $(QSYS_CHECK_SCRIPT)
	@set -e; \
	tmp_script="$(QSYS_DIR)/.qsys_check_normalized.$$$$"; \
	tr -d '\015' < "$(QSYS_CHECK_SCRIPT)" > "$$tmp_script"; \
	chmod +x "$$tmp_script"; \
	bash "$$tmp_script" "$(QSYS_FILE)" "$(QSYS_DIR)" "$(GENERATED_DIR)" "$(QSYS_BASE)" "$(QSYS_STAMP)" "$(QSYS_SOPCINFO)" "$(QSYS_GENERATE_CMD)" "$(CURDIR)/ip/custom/calculator"; \
	rm -f "$$tmp_script"
else
# Dummy rule when QSYS_FILE doesn't exist (for clean targets or when QSys not needed)
$(QSYS_STAMP):
	@$(ECHO) "Skipping QSys generation (no QSys file found)"
	@$(ECHO) "Searched: $(QSYS_DIR)/"
	@$(MKDIR) $(dir $(QSYS_STAMP)) 2>/dev/null || true
	@touch $(QSYS_STAMP) 2>/dev/null || true
endif

HELP_TARGETS += qsys_edit

qsys_edit.HELP := Launch QSys GUI
ifneq ($(HAVE_QSYS),1)
qsys_edit.HELP := $(qsys_edit.HELP) (Install Quartus II Software to enable)
endif

.PHONY: qsys_edit
qsys_edit:
ifneq ($(QSYS_FILE),)
	$(QSYS_EDIT_CMD) $(QSYS_FILE) &
else
	@$(ECHO) "ERROR: No QSys file found"
	@$(ECHO) "Searched: $(QSYS_DIR)/"
	@exit 1
endif


# NOTE: .qsys files are SOURCE FILES and should NEVER be cleaned
# Only generated QSys files (QIP, SOPCINFO, generated directories) are cleaned
# Platform Designer generates files in both $(GENERATED_DIR)/$(QSYS_BASE) (command-line)
# and $(QSYS_DIR)/$(QSYS_BASE) (GUI), so clean handles both locations

#############
# Quartus II

# Only require QUARTUS_QPF for targets that need it (not for clean)
# Search for Quartus project files in quartus/ directory
# Note: Command-line QUARTUS_QPF overrides this, so use ?= to allow override
QUARTUS_QPF ?= $(firstword \
	$(wildcard $(QUARTUS_DIR)/*.qpf) \
)
# Fallback for environments where QUARTUS_DIR expansion is polluted (e.g., CRLF issues on WSL)
ifeq ($(strip $(QUARTUS_QPF)),)
QUARTUS_QPF := $(firstword $(wildcard quartus/*.qpf))
endif
ifneq ($(filter clean help,$(MAKECMDGOALS)),)
# For clean targets, allow QUARTUS_QPF to be empty
QUARTUS_QPF ?= 
else
# For other targets, require QUARTUS_QPF
ifeq ($(strip $(QUARTUS_QPF)),)
$(error ERROR: QUARTUS_QPF *.qpf file not set and could not be discovered in $(QUARTUS_DIR))
endif
endif

# Only define Quartus variables if QUARTUS_QPF exists
ifneq ($(strip $(QUARTUS_QPF)),)
QUARTUS_QSF := $(patsubst %.qpf,%.qsf,$(QUARTUS_QPF))
QUARTUS_BASE := $(basename $(notdir $(QUARTUS_QPF)))
else
# Dummy values for clean targets
QUARTUS_QSF := 
QUARTUS_BASE := 
endif
QUARTUS_HDL_SOURCE := $(wildcard $(HDL_DIR)/*.v $(HDL_DIR)/*.sv $(HDL_DIR)/*.vhd) $(wildcard ip/custom/*/*.v)
QUARTUS_MISC_SOURCE := $(wildcard $(QUARTUS_DIR)/*.stp $(QUARTUS_DIR)/*.sdc)

QUARTUS_PIN_ASSIGNMENTS_STAMP := $(call get_stamp_target,quartus_pin_assignments)
# Only add dependencies if QUARTUS_QPF exists
ifneq ($(strip $(QUARTUS_QPF)),)
QUARTUS_DEPS += $(QUARTUS_QPF) $(QUARTUS_QSF) $(QUARTUS_HDL_SOURCE) $(QUARTUS_MISC_SOURCE)
ifneq ($(QSYS_STAMP),)
QUARTUS_DEPS += $(QSYS_STAMP)
ifneq ($(QSYS_QIP),)
QUARTUS_DEPS += $(QSYS_QIP)
endif
endif
# Pin assignments are applied during/after compilation, not before
# QUARTUS_DEPS += $(QUARTUS_PIN_ASSIGNMENTS_STAMP)
else
QUARTUS_DEPS := 
endif

# Only define Quartus output files if QUARTUS_BASE exists
ifneq ($(QUARTUS_BASE),)
QUARTUS_SOF := $(BUILD_DIR)/output_files/$(QUARTUS_BASE).sof
else
QUARTUS_SOF := 
endif
QUARTUS_STAMP := $(call get_stamp_target,quartus)

.PHONY: quartus_compile
quartus_compile: $(QUARTUS_STAMP)

ifeq ($(HAVE_QUARTUS),1)
$(QUARTUS_SOF): $(QUARTUS_STAMP)
endif

$(QUARTUS_PIN_ASSIGNMENTS_STAMP): $(QSYS_STAMP)
	@$(ECHO) "Checking for pin assignment TCL files..."
	@if [ -f "$(GENERATED_DIR)/$(QSYS_BASE)/synthesis/submodules/hps_sdram_p0_pin_assignments.tcl" ] || \
	   [ -f "$(QSYS_DIR)/$(QSYS_BASE)/synthesis/submodules/hps_sdram_p0_pin_assignments.tcl" ] || \
	   [ -n "$$(ls $(GENERATED_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl 2>/dev/null)" ] || \
	   [ -n "$$(ls $(GENERATED_DIR)/$(QSYS_BASE)/synth/submodules/*_pin_assignments.tcl 2>/dev/null)" ] || \
	   [ -n "$$(ls $(QSYS_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl 2>/dev/null)" ] || \
	   [ -n "$$(ls $(QSYS_DIR)/$(QSYS_BASE)/synth/submodules/*_pin_assignments.tcl 2>/dev/null)" ]; then \
		$(ECHO) "Found pin assignment files."; \
		$(ECHO) "Note: Pin assignments will be applied during compilation (after map stage)."; \
		$(ECHO) "Skipping pre-compilation pin assignment step (requires timing netlist)."; \
	else \
		$(ECHO) "No pin assignment files found, skipping pin assignment step..."; \
	fi
	$(stamp_target)

#######
# we need to recursively call this makefile to 
# apply *_pin_assignments.tcl script because the
# pin_assignment.tcl files may not exist yet 
# when makefile was originally called

ifeq ($(QUARTUS_ENABLE_PIN_ASSIGNMENTS_APPLY),1)

QUARTUS_TCL_PIN_ASSIGNMENTS = $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl) $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/synth/submodules/*_pin_assignments.tcl) $(wildcard $(QSYS_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl) $(wildcard $(QSYS_DIR)/$(QSYS_BASE)/synth/submodules/*_pin_assignments.tcl)
QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS = $(patsubst %,quartus_apply_tcl-%,$(QUARTUS_TCL_PIN_ASSIGNMENTS))

.PHONY: quartus_apply_tcl_pin_assignments
quartus_apply_tcl_pin_assignments: $(QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS)

.PHONY: $(QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS)
$(QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS): quartus_apply_tcl-%: %
	@$(ECHO) "Applying $<... to $(QUARTUS_QPF)..."
	@# File path $< is relative to FPGA/ directory (where Makefile runs)
	@# QUARTUS_DIR is quartus/ (relative to FPGA/)
	@# From quartus/, to reach files in FPGA/:
	@#   - generated/ files: ../generated/... (one level up to FPGA/, then into generated/)
	@#   - qsys/ files: qsys/... (already under quartus/)
	@TCL_FILE=""; \
	if [ -f "$<" ]; then \
		if echo "$<" | grep -q "^generated/"; then \
			TCL_FILE="../$<"; \
		elif echo "$<" | grep -q "^quartus/qsys/"; then \
			TCL_FILE="$$(echo "$<" | sed 's|^quartus/||')"; \
		elif echo "$<" | grep -q "^qsys/"; then \
			TCL_FILE="$<"; \
		else \
			TCL_FILE="../$<"; \
		fi; \
		cd $(QUARTUS_DIR) && $(QUARTUS_STA_CMD) -t "$$TCL_FILE" $(notdir $(QUARTUS_QPF)); \
	elif [ -f "$(QUARTUS_DIR)/$<" ]; then \
		cd $(QUARTUS_DIR) && $(QUARTUS_STA_CMD) -t $< $(notdir $(QUARTUS_QPF)); \
	elif [ -f "../$<" ]; then \
		cd $(QUARTUS_DIR) && $(QUARTUS_STA_CMD) -t ../$< $(notdir $(QUARTUS_QPF)); \
	else \
		$(ECHO) "Error: Could not find TCL file: $<"; \
		$(ECHO) "  (Searched: $<, $(QUARTUS_DIR)/$<, ../$<)"; \
		exit 1; \
	fi

endif # QUARTUS_ENABLE_PIN_ASSIGNMENTS_APPLY == 1
######

ifneq ($(strip $(QUARTUS_QPF)),)
$(QUARTUS_STAMP): $(QUARTUS_DEPS)
	@$(MKDIR) $(BUILD_DIR)/output_files
	@$(ECHO) "Compiling Quartus project: $(notdir $(QUARTUS_QPF))"
	@$(ECHO) "Using Quartus: $(QUARTUS_SH_CMD)"
	@$(ECHO) "Parallel jobs: $(QUARTUS_PARALLEL_JOBS) (set QUARTUS_PARALLEL_JOBS to override)"
	@# quartus_sh does not accept -j; parallelism is controlled via Quartus settings/environment.
	@# We still export NUM_PARALLEL_PROCESSORS above for tools that honor it.
	cd $(QUARTUS_DIR) && $(QUARTUS_SH_CMD) --flow compile $(notdir $(QUARTUS_QPF))
	@$(ECHO) "Checking for pin assignment TCL files to apply after map..."
	@if [ -f "$(GENERATED_DIR)/$(QSYS_BASE)/synthesis/submodules/hps_sdram_p0_pin_assignments.tcl" ] || \
	   [ -f "$(QSYS_DIR)/$(QSYS_BASE)/synthesis/submodules/hps_sdram_p0_pin_assignments.tcl" ] || \
	   [ -n "$$(ls $(GENERATED_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl 2>/dev/null)" ] || \
	   [ -n "$$(ls $(QSYS_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl 2>/dev/null)" ]; then \
		$(ECHO) "Applying pin assignments after compilation..."; \
		$(MAKE) quartus_apply_tcl_pin_assignments QUARTUS_ENABLE_PIN_ASSIGNMENTS_APPLY=1 || $(ECHO) "Warning: Pin assignment application failed (may be non-critical)"; \
	fi
	$(stamp_target)
else
# Dummy target for clean when QUARTUS_QPF doesn't exist
$(QUARTUS_STAMP):
	@$(ECHO) "Skipping Quartus compilation (no Quartus project file found)"
endif

HELP_TARGETS += quartus_edit
quartus_edit.HELP := Launch Quartus II GUI

ifneq ($(HAVE_QUARTUS),1)
quartus_edit.HELP := $(quartus_edit.HELP) (Install Quartus II Software to enable)
endif


.PHONY: quartus_edit
quartus_edit:
	quartus $(QUARTUS_QPF) &

HELP_TARGETS += sof
sof.HELP := QSys generate & Quartus compile this design
ifneq ($(HAVE_QUARTUS),1)
sof.HELP := $(sof.HELP) (Install Quartus II Software to enable)
endif

BATCH_TARGETS += sof

.PHONY: sof
sof: $(QUARTUS_SOF)


QUARTUS_RBF := $(patsubst %.sof,%.rbf,$(QUARTUS_SOF))
#
# This converts the sof into compressed, unencrypted 
# raw binary format corresponding to MSEL value of 8 
# in the FPGAMGRREGS_STAT register. If you read the 
# the whole register, it should be 0x50.
#
# CVSoC DevBoard SW1 MSEL should be set to up,down,up,down,up,up
#

ifeq ($(HAVE_QUARTUS),1)
$(QUARTUS_RBF): $(QUARTUS_STAMP)
endif

QUARTUS_CPF_ENABLE_COMPRESSION ?= 1
ifeq ($(QUARTUS_CPF_ENABLE_COMPRESSION),1)
QUARTUS_CPF_ARGS += -o bitstream_compression=on
endif

$(QUARTUS_RBF): %.rbf: %.sof
	$(QUARTUS_CPF_CMD) -c $(QUARTUS_CPF_ARGS) $< $@

.PHONY: rbf
rbf: $(QUARTUS_RBF)

.PHONY: create_rbf
create_rbf:
	$(QUARTUS_CPF_CMD) -c $(QUARTUS_CPF_ARGS) $(QUARTUS_SOF) $(QUARTUS_RBF)


# Quartus output files are cleaned by the 'clean' target

################################################


################################################
# QSYS/Quartus Project Generation
#  - we don't run this generation step automatically because 
#    it will destroy any changes and/or customizations that 
#    you've made to your qsys or your quartus project
#
QSYS_QSYS_GEN := $(firstword $(wildcard create_*_qsys.tcl))
QUARTUS_TOP_GEN := $(firstword $(wildcard create_*_top.tcl))
QUARTUS_QSF_QPF_GEN := $(firstword $(wildcard create_*_quartus.tcl))

.PHONY: quartus_generate_qsf_qpf
ifneq ($(QUARTUS_QSF_QPF_GEN),)
quartus_generate_qsf_qpf: $(QUARTUS_QSF_QPF_GEN)
	$(RM) $(QUARTUS_QSF) $(QUARTUS_QPF)
	$(QUARTUS_SH_CMD) --script=$< $(QUARTUS_TCL_ARGS)
else
quartus_generate_qsf_qpf:
	@$(ECHO) "Make target '$@' is not supported for this design"
endif

.PHONY: quartus_generate_top
ifneq ($(QUARTUS_TOP_GEN),)
quartus_generate_top: $(QUARTUS_TOP_GEN)
	@$(RM) *_top.v
	$(QUARTUS_SH_CMD) --script=$< $(QUARTUS_TCL_ARGS)
else
quartus_generate_top:
	@$(ECHO) "Make target '$@' is not supported for this design"
endif

.PHONY: qsys_generate_qsys
ifneq ($(QSYS_QSYS_GEN),)

# Note that this target has a strange & known issue 
# that requires the Stratix V device family to be installed.
# If the stratix V device family is not installed then the target 
# will hang. This issue will hopefully be resolved in a future
# version of quartus/qsys.

qsys_generate_qsys: $(QSYS_QSYS_GEN)
	$(RM) $(QSYS_FILE)
	$(QSYS_SCRIPT_CMD) --script=$< $(QSYS_TCL_ARGS)
else
qsys_generate_qsys:
	@$(ECHO) "Make target '$@' is not supported for this design"
endif
################################################


################################################
# Quartus Programming
QUARTUS_PGM_STAMP := $(call get_stamp_target,quartus_pgm)

# set these for your board
# BOARD_CABLE =

# FPGA Board Device Index. Default to 2 since this is the most
#  common setting for dev board
# For SoCKIT board, this should be set to 1
BOARD_DEVICE_INDEX ?= 2

define quartus_pgm_sof
jtagconfig
$(QUARTUS_PGM_CMD) --mode=jtag $(if $(BOARD_CABLE),--cable="$(BOARD_CABLE)") --operation=p\;$1$(if $(BOARD_DEVICE_INDEX),"@$(BOARD_DEVICE_INDEX)")
jtagconfig $(if $(BOARD_CABLE),-c "$(BOARD_CABLE)") -n
endef

.PHONY: pgm
pgm: $(QUARTUS_PGM_STAMP)

$(QUARTUS_PGM_STAMP): $(QUARTUS_SOF)
	$(call quartus_pgm_sof,$<)
	$(stamp_target)

HELP_TARGETS += program_fpga
program_fpga.HELP := Quartus program sof to your attached dev board

.PHONY: program_fpga
program_fpga:
	$(call quartus_pgm_sof,$(QUARTUS_SOF))


# HPS Device Index. Default to 1 since this is the most
#  common setting for dev board
BOARD_HPS_DEVICE_INDEX ?= 1

define quartus_hps_pgm_qspi
jtagconfig
quartus_hps $(if $(BOARD_CABLE),--cable="$(BOARD_CABLE)") $(if $(BOARD_HPS_DEVICE_INDEX),--device=$(BOARD_HPS_DEVICE_INDEX)) --operation=PV $1
endef

HELP_TARGETS += program_qspi
program_qspi.HELP := Flash program preloader into QSPI Flash

.PHONY: program_qspi
program_qspi: $(PRELOADER_DIR)/preloader-mkpimage.bin
	$(call quartus_hps_pgm_qspi,$<)


# GHRD HPS Reset Targets
ifneq ($(wildcard ghrd_reset.tcl),)
# use the already programmed fpga to reset the hps
HPS_RESET_TARGETS := hps_cold_reset hps_warm_reset hps_debug_reset

.PHONY: $(HPS_RESET_TARGETS) 
$(HPS_RESET_TARGETS): hps_%_reset:
	$(QUARTUS_STP_CMD) --script=ghrd_reset.tcl $(if $(BOARD_CABLE),--cable-name "$(BOARD_CABLE)") $(if $(BOARD_DEVICE_INDEX),--device-index "$(BOARD_DEVICE_INDEX)") --$*-reset
endif

################################################


################################################

# Define final 'all' target with all collected dependencies
# This must be after all conditional dependencies are added to ALL_DEPS
.PHONY: all
all: $(ALL_DEPS)
	@$(ECHO) "==========================================="
	@$(ECHO) "Full build complete"
	@$(ECHO) ""
ifeq ($(HAVE_QUARTUS),1)
ifneq ($(QUARTUS_BASE),)
	@if [ -f "$(QUARTUS_SOF)" ]; then \
		$(ECHO) "[OK] FPGA bitstream built successfully"; \
		$(ECHO) "  SOF file: $(QUARTUS_SOF)"; \
		if [ -f "$(QUARTUS_RBF)" ]; then \
			$(ECHO) "  RBF file: $(QUARTUS_RBF)"; \
		fi; \
	else \
		$(ECHO) "[WARN] FPGA bitstream not found (may need to run 'make sof')"; \
	fi
else
	@$(ECHO) "[WARN] FPGA bitstream: Skipped (no Quartus project found)"
endif
else
	@$(ECHO) "[WARN] FPGA bitstream: Skipped (Quartus not in PATH)"
	@$(ECHO) "  To build FPGA bitstream, add Quartus to PATH:"
	@$(ECHO) "    export PATH=\$$PATH:/path/to/intelFPGA/20.1/quartus/bin"
	@$(ECHO) "  Or run: make sof  (if Quartus is installed)"
endif
	@$(ECHO) "==========================================="

################################################


################################################
# Clean-up and Archive

AR_FILES += $(filter-out $(AR_FILTER_OUT),$(wildcard $(AR_REGEX)))

CLEAN_FILES += $(filter-out $(AR_DIR) $(AR_FILES),$(wildcard *))

HELP_TARGETS += tgz
tgz.HELP := Create a tarball with the barebones source files that comprise this design

.PHONY: tarball tgz
tarball tgz: $(AR_FILE)

$(AR_FILE):
	@$(MKDIR) $(@D)
	@$(if $(wildcard $(@D)/*.tar.gz),$(MKDIR) $(@D)/.archive;$(MV) $(@D)/*.tar.gz $(@D)/.archive)
	@$(ECHO) "Generating $@..."
	@$(TAR) -czf $@ $(AR_FILES)

# CLEAN_FILES is used by tgz target only, not by clean target
# The 'clean' target explicitly removes all generated files

################################################


################################################
# Running Batch Jobs
ifneq ($(BATCH_TARGETS),)

BATCH_DIR := $(if $(TMP),$(TMP)/)batch/$(AR_TIMESTAMP)

.PHONY: $(patsubst %,batch-%,$(BATCH_TARGETS))
$(patsubst %,batch-%,$(BATCH_TARGETS)): batch-%: $(AR_FILE)
	@$(RM) $(BATCH_DIR)
	@$(MKDIR) $(BATCH_DIR)
	$(CP) $< $(BATCH_DIR) 
	$(CD) $(BATCH_DIR) && $(TAR) -xzf $(notdir $<) && $(CHMOD) -R 755 *
	$(MAKE) -C $(BATCH_DIR) $*

endif # BATCH_TARGETS != <empty>
################################################


################################################
# Help system

HELP_TARGETS += help
help.HELP := Displays this info (i.e. the available targets)

.PHONY: help
help: help-init help-targets help-fini

HELP_TARGETS_X := $(patsubst %,help-%,$(sort $(HELP_TARGETS)))
.PHONY: $(HELP_TARGETS_X)
help-targets: $(HELP_TARGETS_X)
$(HELP_TARGETS_X): help-%:
	@$(ECHO) "*********************"
	@$(ECHO) "* Target: $*"
	@$(ECHO) "*   $($*.HELP)"

.PHONY: help-init
help-init:
	@$(ECHO) "*****************************************"
	@$(ECHO) "*                                       *"
	@$(ECHO) "* Manage QuartusII/QSys design          *"
	@$(ECHO) "*                                       *"
	@$(ECHO) "*     Copyright (c) 2016                *"
	@$(ECHO) "*     All Rights Reserved               *"
	@$(ECHO) "*                                       *"
	@$(ECHO) "*****************************************"
	@$(ECHO) ""

.PHONY: help-fini
help-fini:
	@$(ECHO) "*********************"

################################################
