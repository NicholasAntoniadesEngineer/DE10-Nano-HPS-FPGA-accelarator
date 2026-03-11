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
# Common Tools

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

################################################
# Platform Detection

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

CLEAN_TARGETS := clean clean-all clear-tool-cache show-tool-cache

ifneq ($(filter $(CLEAN_TARGETS),$(MAKECMDGOALS)),)
ifeq ($(filter-out $(CLEAN_TARGETS),$(MAKECMDGOALS)),)
SKIP_TOOL_DETECTION := 1
endif
endif

################################################
# Quartus Parallel Compilation
################################################

NPROC := $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
QUARTUS_PARALLEL_JOBS ?= $(NPROC)
export NUM_PARALLEL_PROCESSORS := $(QUARTUS_PARALLEL_JOBS)

################################################
# Directory Structure

HDL_DIR := hdl
QUARTUS_DIR := quartus
QSYS_DIR := $(QUARTUS_DIR)/qsys
BUILD_DIR := build
GENERATED_DIR := generated
DOCS_DIR := docs

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

################################################
# Shared Variables (populated by included files)

ALL_DEPS :=
HELP_TARGETS :=
BATCH_TARGETS :=

# Fast build targets that don't require SoC EDS
FAST_TARGETS := fast fast-flash fast-rbf qsys-generate quartus-compile qsys_compile quartus_compile qsys_edit quartus_edit sof rbf

################################################
# Include Sub-Makefiles

include mk/tools.mk
include mk/qsys.mk
include mk/quartus.mk
include mk/program.mk
include mk/clean.mk
include mk/archive.mk
include mk/help.mk

################################################
# Default Target

.PHONY: default
default: help

################################################
# Build Everything Target

HELP_TARGETS += everything
everything.HELP := Build FPGA components: QSys generation + Quartus compile + RBF

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
	@$(ECHO) ""
	@$(ECHO) "==========================================="
	@$(ECHO) "Everything build complete!"
	@$(ECHO) "==========================================="

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

################################################
# All Target

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
