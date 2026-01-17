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

# HAVE_QSYS is set if we have either quartus or qsys-generate
ifeq ($(HAVE_QUARTUS),1)
HAVE_QSYS := 1
endif
ifeq ($(HAVE_QSYS_GENERATE),1)
HAVE_QSYS := 1
endif

#<unused>
#ifneq ($(shell $(WHICH) quartus_pgm 2>/dev/null),)
#HAVE_QUARTUS_PGM := 1
#endif

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

################################################

################################################
# Directory structure
FPGA_DIR := fpga
HDL_DIR := $(FPGA_DIR)/hdl
QUARTUS_DIR := $(FPGA_DIR)/quartus
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
		$(ECHO) "  ✓ Found: $(QUARTUS_SH)"; \
		$(ECHO) "  HAVE_QUARTUS: $(HAVE_QUARTUS)"; \
	else \
		$(ECHO) "  ✗ Not found in PATH or standard locations"; \
	fi
	@$(ECHO) ""
	@$(ECHO) "QSys detection:"
	@if [ -n "$(QSYS_GENERATE)" ]; then \
		$(ECHO) "  ✓ Found: $(QSYS_GENERATE)"; \
		$(ECHO) "  HAVE_QSYS_GENERATE: $(HAVE_QSYS_GENERATE)"; \
	else \
		$(ECHO) "  ✗ Not found in PATH or standard locations"; \
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
	@$(ECHO) "Building Everything"
	@$(ECHO) "==========================================="
	@$(ECHO) ""
	@$(ECHO) "Step 1: QSys Generation"
	@$(ECHO) "-------------------------------------------"
ifneq ($(QSYS_FILE),)
	@$(ECHO) "QSys file found: $(QSYS_FILE)"
	@$(ECHO) "  (Searched: $(QSYS_DIR)/)"
	@$(MAKE) qsys-generate
else
	@$(ECHO) "WARNING: No QSys file found"
	@$(ECHO) "  Searched location: $(QSYS_DIR)/"
	@$(ECHO) "  Patterns: *top*.qsys, *main*.qsys, *soc*.qsys, *.qsys"
	@$(ECHO) "Skipping QSys generation"
endif
	@$(ECHO) ""
	@$(ECHO) "Step 2: FPGA Bitstream Generation"
	@$(ECHO) "-------------------------------------------"
ifeq ($(HAVE_QUARTUS),1)
ifneq ($(QUARTUS_BASE),)
	@$(ECHO) "Quartus project found: $(QUARTUS_BASE)"
	@$(ECHO) "  Project file: $(QUARTUS_QPF)"
	@$(ECHO) "  (Searched: $(QUARTUS_DIR)/)"
	@$(MAKE) sof rbf
	@$(ECHO) "FPGA bitstream generation complete"
else
	@$(ECHO) "WARNING: No Quartus project file found"
	@$(ECHO) "  Searched location: $(QUARTUS_DIR)/"
	@$(ECHO) "  Pattern: *.qpf"
	@$(ECHO) "Skipping FPGA bitstream generation"
endif
else
	@$(ECHO) "WARNING: Quartus not found in PATH"
	@$(ECHO) "Skipping FPGA bitstream generation"
endif
	@$(ECHO) ""
	@$(ECHO) "Step 3: HPS Software (Preloader, U-Boot, Device Tree)"
	@$(ECHO) "-------------------------------------------"
ifneq ($(SBT.CREATE_SETTINGS),)
	@$(ECHO) "SoC EDS tools found: $(SBT.CREATE_SETTINGS)"
	@$(ECHO) "  (Searched: PATH, SOCEDS_DEST_ROOT/host_tools/bin, SOCEDS_DEST_ROOT/bin)"
	@$(ECHO) "Building preloader, U-Boot, device tree, and SD card image..."
	@$(MAKE) preloader uboot dts dtb sd-fat
	@$(ECHO) "HPS software build complete"
else
	@$(ECHO) "WARNING: SoC EDS tools not found"
	@$(ECHO) "  Searched locations:"
	@$(ECHO) "    - PATH (bsp-create-settings, bsp-create-settings.exe)"
	@if [ -n "$$SOCEDS_DEST_ROOT" ]; then \
		$(ECHO) "    - $$SOCEDS_DEST_ROOT/host_tools/bin/"; \
		$(ECHO) "    - $$SOCEDS_DEST_ROOT/bin/"; \
		$(ECHO) "    - Recursive search in $$SOCEDS_DEST_ROOT"; \
	else \
		$(ECHO) "    - SOCEDS_DEST_ROOT not set"; \
	fi
	@$(ECHO) "Skipping HPS software components (preloader, uboot, dts, dtb, sd-fat)"
	@$(ECHO) "To build HPS software, install SoC EDS and set SOCEDS_DEST_ROOT"
endif
	@$(ECHO) ""
	@$(ECHO) "Step 4: HPS Test Suite"
	@$(ECHO) "-------------------------------------------"
	@TEST_MAKEFILE=""; \
	if [ -f "$(HPS_DIR)/calculator_test/Makefile" ]; then \
		TEST_MAKEFILE="$(HPS_DIR)/calculator_test/Makefile"; \
	elif [ -f "hps/calculator_test/Makefile" ]; then \
		TEST_MAKEFILE="hps/calculator_test/Makefile"; \
	else \
		TEST_MAKEFILE=$$($(FIND) . -maxdepth 4 -path "*/calculator_test/Makefile" 2>/dev/null | $(HEAD) -n1); \
	fi; \
	if [ -n "$$TEST_MAKEFILE" ] && [ -f "$$TEST_MAKEFILE" ]; then \
		TEST_DIR=$$(dirname "$$TEST_MAKEFILE"); \
		$(ECHO) "Test suite Makefile found: $$TEST_MAKEFILE"; \
		$(ECHO) "Building HPS calculator test suite..."; \
		$(MAKE) -C "$$TEST_DIR" || $(ECHO) "WARNING: Failed to build test suite (may need cross-compiler)"; \
	else \
		$(ECHO) "WARNING: Test suite Makefile not found"; \
		$(ECHO) "Searched: $(HPS_DIR)/calculator_test/Makefile, hps/calculator_test/Makefile, and recursively"; \
		$(ECHO) "Skipping test suite build"; \
	fi
	@$(ECHO) ""
	@$(ECHO) "==========================================="
	@$(ECHO) "Build Summary"
	@$(ECHO) "==========================================="
	@$(ECHO) ""
ifneq ($(QSYS_FILE),)
	@$(ECHO) "✓ QSys generation: Complete"
	@if [ -f "$(QSYS_SOPCINFO)" ]; then \
		$(ECHO) "  - SOPCINFO: $(QSYS_SOPCINFO)"; \
	fi
else
	@$(ECHO) "✗ QSys generation: Skipped (no QSys file)"
endif
	@$(ECHO) ""
ifeq ($(HAVE_QUARTUS),1)
ifneq ($(QUARTUS_BASE),)
	@$(ECHO) "✓ FPGA bitstream: Complete"
	@if [ -f "$(QUARTUS_SOF)" ]; then \
		$(ECHO) "  - SOF file: $(QUARTUS_SOF)"; \
	fi
	@if [ -f "$(QUARTUS_RBF)" ]; then \
		$(ECHO) "  - RBF file: $(QUARTUS_RBF)"; \
	fi
else
	@$(ECHO) "✗ FPGA bitstream: Skipped (no Quartus project)"
endif
else
	@$(ECHO) "✗ FPGA bitstream: Skipped (Quartus not available)"
endif
	@$(ECHO) ""
ifneq ($(SBT.CREATE_SETTINGS),)
	@$(ECHO) "✓ HPS software: Complete"
	@if [ -f "$(DEVICE_TREE_BLOB)" ]; then \
		$(ECHO) "  - Device tree: $(DEVICE_TREE_BLOB)"; \
	fi
	@if [ -f "$(SD_FAT_TGZ)" ]; then \
		$(ECHO) "  - SD card image: $(SD_FAT_TGZ)"; \
	fi
else
	@$(ECHO) "✗ HPS software: Skipped (SoC EDS not available)"
endif
	@$(ECHO) ""
	@TEST_EXE=""; \
	if [ -f "$(HPS_DIR)/calculator_test/calculator_test" ]; then \
		TEST_EXE="$(HPS_DIR)/calculator_test/calculator_test"; \
	elif [ -f "hps/calculator_test/calculator_test" ]; then \
		TEST_EXE="hps/calculator_test/calculator_test"; \
	else \
		TEST_EXE=$$($(FIND) . -maxdepth 4 -path "*/calculator_test/calculator_test" 2>/dev/null | $(HEAD) -n1); \
	fi; \
	if [ -n "$$TEST_EXE" ] && [ -f "$$TEST_EXE" ]; then \
		$(ECHO) "✓ Test suite: Complete"; \
		$(ECHO) "  - Executable: $$TEST_EXE"; \
	else \
		$(ECHO) "✗ Test suite: Skipped or failed"; \
	fi
	@$(ECHO) ""
	@$(ECHO) "==========================================="
	@$(ECHO) "Everything build complete!"
	@$(ECHO) "==========================================="

HELP_TARGETS += everything
everything.HELP := Build all components (QSys, FPGA bitstream, HPS software, test suite)

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
		@$(ECHO) "Please create a QSys file in fpga/quartus/qsys/ directory"
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
	@$(ECHO) "  - HPS software build artifacts..."
	@$(RM) $(wildcard $(HPS_DIR)/calculator_test/*.o $(HPS_DIR)/calculator_test/*.d)
	@$(RM) $(wildcard $(HPS_DIR)/calculator_test/calculator_test $(HPS_DIR)/calculator_test/*.log)
	@$(RM) $(wildcard $(HPS_DIR)/preloader)
	@$(ECHO) "  - Device tree files..."
	@$(RM) $(wildcard $(GENERATED_DIR)/*.dts $(GENERATED_DIR)/*.dtb)
	@$(ECHO) "  - Boot scripts and SD card images..."
	@$(RM) $(wildcard boot.script u-boot.scr sd_fat.tar.gz)
	@$(ECHO) "Build artifacts and generated files cleaned successfully"
	@$(ECHO) "  Run 'make all' to rebuild everything"
################################################


################################################
# Archiving & Cleaning your QuartusII/QSys Project

AR_TIMESTAMP := $(if $(SOCEDS_VERSION),$(subst .,_,$(SOCEDS_VERSION))_)$(subst $(SPACE),,$(shell $(DATE) +%m%d%Y_%k%M%S))

AR_DIR := tgz
AR_FILE := $(AR_DIR)/$(basename $(firstword $(wildcard *.qpf)))_$(AR_TIMESTAMP).tar.gz

HPS_DIR := hps
PRELOADER_DIR := $(HPS_DIR)/preloader

AR_REGEX += \
	Makefile ip readme.txt ds5 \
	altera_avalon* *.qpf *.qsf *.sdc *.v *.sv *.vhd *.qsys *.tcl *.terp *.stp \
	*.sed quartus.ini *.sof *.rbf *.sopcinfo *.jdi output_files \
	hps_isw_handoff */*.svd */synthesis/*.svd */synth/*.svd *.dts *.dtb *.xml \
	$(HPS_DIR)

AR_FILTER_OUT += %_tb.qsys
################################################



################################################
# Build QuartusII/QSys Project
#

#############
# QSys
# Only require QSYS_FILE for targets that need it (not for clean/scrub/help)
# Allow QSYS_FILE to be empty - targets will handle it gracefully
# Search for QSys files in fpga/quartus/qsys/ directory
QSYS_FILE := $(firstword \
	$(wildcard $(QSYS_DIR)/*top*.qsys) \
	$(wildcard $(QSYS_DIR)/*main*.qsys) \
	$(wildcard $(QSYS_DIR)/*soc*.qsys) \
	$(wildcard $(QSYS_DIR)/*.qsys) \
)
QSYS_DEPS += $(wildcard $(QSYS_DIR)/*.qsys)
# Only define QSys variables if QSYS_FILE exists
ifneq ($(QSYS_FILE),)
QSYS_BASE := $(basename $(notdir $(QSYS_FILE)))
QSYS_QIP := $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/synthesis/$(QSYS_BASE).qip) $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/$(QSYS_BASE).qip)
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
	@bash $(QSYS_CHECK_SCRIPT) "$(QSYS_FILE)" "$(QSYS_DIR)" "$(GENERATED_DIR)" "$(QSYS_BASE)" "$(QSYS_STAMP)" "$(QSYS_SOPCINFO)" "$(QSYS_GENERATE_CMD)"
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
# Search for Quartus project files in fpga/quartus/ directory
QUARTUS_QPF := $(firstword \
	$(wildcard $(QUARTUS_DIR)/*.qpf) \
)
ifneq ($(filter clean help,$(MAKECMDGOALS)),)
# For clean targets, allow QUARTUS_QPF to be empty
QUARTUS_QPF ?= 
else
# For other targets, require QUARTUS_QPF
ifeq ($(QUARTUS_QPF),)
$(error ERROR: QUARTUS_QPF *.qpf file not set and could not be discovered in $(QUARTUS_DIR))
endif
endif

# Only define Quartus variables if QUARTUS_QPF exists
ifneq ($(QUARTUS_QPF),)
QUARTUS_QSF := $(patsubst %.qpf,%.qsf,$(QUARTUS_QPF))
QUARTUS_BASE := $(basename $(notdir $(QUARTUS_QPF)))
else
# Dummy values for clean targets
QUARTUS_QSF := 
QUARTUS_BASE := 
endif
QUARTUS_HDL_SOURCE := $(wildcard $(HDL_DIR)/*.v $(HDL_DIR)/*.sv $(HDL_DIR)/*.vhd) $(wildcard $(FPGA_DIR)/ip/custom/*/*.v)
QUARTUS_MISC_SOURCE := $(wildcard $(QUARTUS_DIR)/*.stp $(QUARTUS_DIR)/*.sdc)

QUARTUS_PIN_ASSIGNMENTS_STAMP := $(call get_stamp_target,quartus_pin_assignments)
# Only add dependencies if QUARTUS_QPF exists
ifneq ($(QUARTUS_QPF),)
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
	@if [ -f "$<" ]; then \
		cd $(QUARTUS_DIR) && $(QUARTUS_STA_CMD) -t ../$< $(notdir $(QUARTUS_QPF)); \
	elif [ -f "$(QUARTUS_DIR)/$<" ]; then \
		cd $(QUARTUS_DIR) && $(QUARTUS_STA_CMD) -t $< $(notdir $(QUARTUS_QPF)); \
	elif [ -f "../../$<" ]; then \
		cd $(QUARTUS_DIR) && $(QUARTUS_STA_CMD) -t ../../$< $(notdir $(QUARTUS_QPF)); \
	else \
		$(ECHO) "Error: Could not find TCL file: $<"; \
		$(ECHO) "  (Searched: $<, $(QUARTUS_DIR)/$<, ../../$<)"; \
		exit 1; \
	fi

endif # QUARTUS_ENABLE_PIN_ASSIGNMENTS_APPLY == 1
######

ifneq ($(QUARTUS_QPF),)
$(QUARTUS_STAMP): $(QUARTUS_DEPS)
	@$(MKDIR) $(BUILD_DIR)/output_files
	@$(ECHO) "Compiling Quartus project: $(notdir $(QUARTUS_QPF))"
	@$(ECHO) "Using Quartus: $(QUARTUS_SH_CMD)"
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
# Preloader

QSYS_HPS_INST_NAME ?= hps_0

# Define targets that require SoC EDS
HPS_TARGETS := preloader uboot dts dtb sd-fat

# Check for SoC EDS environment (only for targets that need it)
# Fast targets and 'all' don't require SoC EDS (all will conditionally build HPS)
ifneq ($(filter-out $(FAST_TARGETS) all help clean,$(MAKECMDGOALS)),)
ifneq ($(filter $(HPS_TARGETS),$(MAKECMDGOALS)),)
ifndef SOCEDS_DEST_ROOT
$(warning WARNING: SOCEDS_DEST_ROOT is not set. SoC EDS tools may not be found.)
$(warning Set SOCEDS_DEST_ROOT to your SoC EDS installation directory, e.g.,)
$(warning export SOCEDS_DEST_ROOT=/path/to/intelFPGA/20.1/embedded)
$(warning Note: Fast build targets (fast, fast-flash, fast-rbf) do not require SoC EDS.)
endif
endif
endif

# Always try to find bsp-create-settings (for conditional use in 'all' target)
# First try to find it in PATH
SBT.CREATE_SETTINGS := $(shell $(WHICH) bsp-create-settings 2>/dev/null)
ifeq ($(SBT.CREATE_SETTINGS),)
SBT.CREATE_SETTINGS := $(shell $(WHICH) bsp-create-settings.exe 2>/dev/null)
endif

# If not in PATH, try to find it in SoC EDS installation
ifeq ($(SBT.CREATE_SETTINGS),)
ifdef SOCEDS_DEST_ROOT
# Try common locations (handle both Unix and Windows paths)
SBT.CREATE_SETTINGS := $(wildcard $(SOCEDS_DEST_ROOT)/host_tools/bin/bsp-create-settings)
ifeq ($(SBT.CREATE_SETTINGS),)
SBT.CREATE_SETTINGS := $(wildcard $(SOCEDS_DEST_ROOT)/host_tools/bin/bsp-create-settings.exe)
endif
ifeq ($(SBT.CREATE_SETTINGS),)
SBT.CREATE_SETTINGS := $(wildcard $(SOCEDS_DEST_ROOT)/bin/bsp-create-settings)
endif
ifeq ($(SBT.CREATE_SETTINGS),)
SBT.CREATE_SETTINGS := $(wildcard $(SOCEDS_DEST_ROOT)/bin/bsp-create-settings.exe)
endif
# Try Windows-style paths if on Windows
ifeq ($(IS_WINDOWS_HOST),1)
ifeq ($(SBT.CREATE_SETTINGS),)
SBT.CREATE_SETTINGS := $(shell find "$(SOCEDS_DEST_ROOT)" -name "bsp-create-settings*" 2>/dev/null | $(HEAD) -n1)
endif
endif
endif
endif

# Final check - if still not found, provide helpful error (only for HPS-specific targets)
# Fast targets, clean targets, and 'all' don't require SoC EDS (all will conditionally build HPS)
ifeq ($(SBT.CREATE_SETTINGS),)
ifneq ($(filter-out $(FAST_TARGETS) all help clean,$(MAKECMDGOALS)),)
ifneq ($(filter $(HPS_TARGETS),$(MAKECMDGOALS)),)
$(error ERROR: bsp-create-settings not found. Please ensure SoC EDS is installed and either:)
$(error   1. Set SOCEDS_DEST_ROOT and add $(if $(SOCEDS_DEST_ROOT),$(SOCEDS_DEST_ROOT)/host_tools/bin,<SOCEDS_PATH>/host_tools/bin) to PATH, or)
$(error   2. Source embedded_command_shell.sh from your SoC EDS installation, or)
$(error   3. Run './scripts/find_soceds.sh' to locate your SoC EDS installation)
endif
endif
endif

# Always try to find bsp-generate-files (for conditional use)
SBT.GENERATE := $(shell $(WHICH) bsp-generate-files 2>/dev/null)
ifeq ($(SBT.GENERATE),)
SBT.GENERATE := $(shell $(WHICH) bsp-generate-files.exe 2>/dev/null)
endif
ifeq ($(SBT.GENERATE),)
ifdef SOCEDS_DEST_ROOT
SBT.GENERATE := $(wildcard $(SOCEDS_DEST_ROOT)/host_tools/bin/bsp-generate-files)
ifeq ($(SBT.GENERATE),)
SBT.GENERATE := $(wildcard $(SOCEDS_DEST_ROOT)/host_tools/bin/bsp-generate-files.exe)
endif
ifeq ($(SBT.GENERATE),)
SBT.GENERATE := $(wildcard $(SOCEDS_DEST_ROOT)/bin/bsp-generate-files)
endif
ifeq ($(SBT.GENERATE),)
SBT.GENERATE := $(wildcard $(SOCEDS_DEST_ROOT)/bin/bsp-generate-files.exe)
endif
endif
ifeq ($(SBT.GENERATE),)
SBT.GENERATE := bsp-generate-files
endif
endif

# Add HPS software components to 'all' target if SoC EDS is available
# This must be after the SoC EDS check above
ifneq ($(SBT.CREATE_SETTINGS),)
ALL_DEPS += preloader uboot dts dtb sd-fat
endif

HELP_TARGETS += preloader
preloader.HELP := Build Preloader BSP for this design into $(PRELOADER_DIR) directory

PRELOADER_ID := hps_isw_handoff/$(QSYS_BASE)_$(QSYS_HPS_INST_NAME)/id
PRELOADER_DEPS += $(PRELOADER_ID)

ifeq ($(HAVE_QUARTUS),1)
PRELOADER_DEPS += $(QUARTUS_STAMP)

$(PRELOADER_ID): $(QUARTUS_STAMP) 
endif

PRELOADER_STAMP := $(call get_stamp_target,preloader)

PRELOADER_DISABLE_WATCHDOG ?= 1
ifeq ($(PRELOADER_DISABLE_WATCHDOG),1)
PRELOADER_EXTRA_ARGS += --set spl.boot.WATCHDOG_ENABLE false
endif

PRELOADER_ENABLE_ECC_SCRUBBING ?= 1
ifeq ($(PRELOADER_ENABLE_ECC_SCRUBBING),1)
# If enabled, we should scrub all 1GB of DDR. This may be overkill
PRELOADER_EXTRA_ARGS += \
	--set spl.boot.SDRAM_SCRUBBING true
endif


.PHONY: preloader
preloader: $(PRELOADER_STAMP)

# Create and build preloader with watchdog disabled.
# This is useful for board bring up and troubleshooting.
$(PRELOADER_STAMP): $(PRELOADER_DEPS)

	@$(MKDIR) $(PRELOADER_DIR)

	$(SBT.CREATE_SETTINGS) \
		--type spl \
		--bsp-dir $(PRELOADER_DIR) \
		--preloader-settings-dir "hps_isw_handoff/$(QSYS_BASE)_$(QSYS_HPS_INST_NAME)" \
		--settings $(PRELOADER_DIR)/settings.bsp \
		$(PRELOADER_EXTRA_ARGS)

	$(MAKE) -C $(PRELOADER_DIR)

	$(stamp_target)


UBOOT_STAMP := $(call get_stamp_target,uboot)

$(UBOOT_STAMP): $(PRELOADER_STAMP)
	$(MAKE) -C $(PRELOADER_DIR) uboot
	$(stamp_target)


ifeq ($(IS_WINDOWS_HOST),1)
EXE_EXT := .exe
endif
UBOOT_MKIMAGE := $(PRELOADER_DIR)/uboot-socfpga/tools/mkimage$(EXE_EXT)
AR_REGEX += $(UBOOT_MKIMAGE)


HELP_TARGETS += uboot
uboot.HELP := Build U-Boot into $(PRELOADER_DIR) directory

.PHONY: uboot
uboot: $(UBOOT_STAMP)


# Preloader directory is cleaned by the 'clean' target

################################################


################################################
# Preloader/Uboot SD Card Programming

# Update the A2 Partition on your sd card with
# the preloader and uboot that build with this design

# These targets assume you have a pre-imaged sd card
# or an sd card *.img file 
# An example sd image for the Altera SoC Development
# Board can be found here:
# <soceds_install>/embeddedsw/socfpga/prebuilt_images

ALT_BOOT_DISK_UTIL := alt-boot-disk-util

ifeq ($(IS_WINDOWS_HOST),1)

ifeq ($(SDCARD),)
ifeq ($(SD_DRIVE_LETTER),)
GUESS_DRIVE_LETTER = $(firstword $(foreach drive_letter,d e f g h i j k l m n o p q r s t u v w x y z,$(if $(wildcard $(drive_letter):/zImage),$(drive_letter))))
SD_DRIVE_LETTER = $(GUESS_DRIVE_LETTER)
endif # SD_DRIVE_LETTER == <empty>
SDCARD ?= $(if $(SD_DRIVE_LETTER),-d $(SD_DRIVE_LETTER),$(error ERROR: SD_DRIVE_LETTER not specified. Try "make $(MAKECMDGOALS) SD_DRIVE_LETTER=[sd_card_windows_drive_letter]"))
endif # SDCARD == <empty>

else # if not a Windows Host

SDCARD ?= $(error ERROR: SD Card not specified. Try "make $(MAKECMDGOALS) SDCARD=/dev/sdX", where X represents your target SD Card device)

endif

PRELOADER_BIN ?= $(PRELOADER_DIR)/preloader-mkpimage.bin

.PHONY: sd-update-preloader
sd-update-preloader: $(PRELOADER_BIN)
	$(ALT_BOOT_DISK_UTIL) -p $< -a write $(SDCARD)

NEXTSTAGE_BIN ?= $(PRELOADER_DIR)/uboot-socfpga/u-boot.img

.PHONY: sd-update-uboot
sd-update-uboot: $(NEXTSTAGE_BIN)
	$(ALT_BOOT_DISK_UTIL) -b $< -a write $(SDCARD)

sd-update-preloader-uboot: sd-update-preloader sd-update-uboot

################################################


################################################
# Device Tree

DTS.SOPC2DTS := sopc2dts
DTS.DTC := dtc

DTS.BOARDINFO ?= $(QSYS_BASE)_board_info.xml
DTS.COMMON ?= hps_common_board_info.xml

DTS.EXTRA_DEPS += $(DTS.BOARDINFO) $(DTS.COMMON)

DTS.SOPC2DTS_ARGS += $(if $(DTS.BOARDINFO),--board $(DTS.BOARDINFO))
DTS.SOPC2DTS_ARGS += $(if $(DTS.COMMON),--board $(DTS.COMMON))
DTS.SOPC2DTS_ARGS += --bridge-removal all
DTS.SOPC2DTS_ARGS += --clocks

define dts.sopc2dts
$(if $(DTS.BOARDINFO),,$(warning WARNING: DTS BoardInfo file was not specified or found))
$(DTS.SOPC2DTS) --input $1 --output $2 $3 $(DTS.SOPC2DTS_ARGS)
endef


# Device Tree Source (dts)
# Only define if QSYS_SOPCINFO exists
ifneq ($(QSYS_SOPCINFO),)
DEVICE_TREE_SOURCE := $(patsubst %.sopcinfo,%.dts,$(QSYS_SOPCINFO))
else
DEVICE_TREE_SOURCE := 
endif

HELP_TARGETS += dts
dts.HELP := Generate a device tree for this qsys design

.PHONY: dts
dts: $(DEVICE_TREE_SOURCE)

ifeq ($(HAVE_QSYS),1)
ifneq ($(DEVICE_TREE_SOURCE),)
$(DEVICE_TREE_SOURCE): $(QSYS_STAMP)
endif
endif

ifneq ($(DEVICE_TREE_SOURCE),)
$(DEVICE_TREE_SOURCE): %.dts: %.sopcinfo $(DTS.EXTRA_DEPS)
	$(call dts.sopc2dts,$<,$@)
endif


# Device Tree Blob (dtb)
# Only define if QSYS_SOPCINFO exists
ifneq ($(QSYS_SOPCINFO),)
DEVICE_TREE_BLOB := $(patsubst %.sopcinfo,%.dtb,$(QSYS_SOPCINFO))
else
DEVICE_TREE_BLOB := 
endif

HELP_TARGETS += dtb
dtb.HELP := Generate a device tree blob for this qsys design

.PHONY: dtb
dtb: $(DEVICE_TREE_BLOB)

ifeq ($(HAVE_QSYS),1)
ifneq ($(DEVICE_TREE_BLOB),)
$(DEVICE_TREE_BLOB): $(QSYS_STAMP)
endif
endif

ifneq ($(DEVICE_TREE_BLOB),)
$(DEVICE_TREE_BLOB): %.dtb: %.dts
	$(DTS.DTC) -I dts -O dtb -o $@ $<
endif

# Device tree files are cleaned by the 'clean' target

################################################


################################################
boot.script: Makefile
	@$(RM) $@
	@$(ECHO) "Generating $@"
	@$(ECHO) "fatload mmc 0:1 \$$fpgadata $(QUARTUS_RBF);" >>$@
	@$(ECHO) "fpga load 0 \$$fpgadata \$$filesize;" >>$@
	@$(ECHO) "setenv fdtimage $(DEVICE_TREE_BLOB);" >>$@
	@$(ECHO) "run bridge_enable_handoff;" >>$@
	@$(ECHO) "run mmcload;" >>$@
	@$(ECHO) "run mmcboot;" >>$@

ifeq ($(wildcard $(UBOOT_MKIMAGE)),)
$(UBOOT_MKIMAGE): $(PRELOADER_STAMP)
endif

u-boot.scr: boot.script $(UBOOT_MKIMAGE)
	$(UBOOT_MKIMAGE) -A arm -O linux -T script -C none -a 0 -e 0 -n "bootscript" -d $< $@

SD_FAT_TGZ ?= sd_fat.tar.gz
SD_FAT_TGZ_DEPS += u-boot.scr boot.script $(QUARTUS_RBF) $(DEVICE_TREE_BLOB)

$(SD_FAT_TGZ): $(SD_FAT_TGZ_DEPS)
	@$(RM) $@
	@$(MKDIR) $(@D)
	$(TAR) -czf $@ $^

.PHONY: sd-fat
sd-fat: $(SD_FAT_TGZ)

AR_FILES += $(wildcard $(SD_FAT_TGZ))

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
		$(ECHO) "✓ FPGA bitstream built successfully"; \
		$(ECHO) "  SOF file: $(QUARTUS_SOF)"; \
		if [ -f "$(QUARTUS_RBF)" ]; then \
			$(ECHO) "  RBF file: $(QUARTUS_RBF)"; \
		fi; \
	else \
		$(ECHO) "⚠ FPGA bitstream not found (may need to run 'make sof')"; \
	fi
else
	@$(ECHO) "⚠ FPGA bitstream: Skipped (no Quartus project found)"
endif
else
	@$(ECHO) "⚠ FPGA bitstream: Skipped (Quartus not in PATH)"
	@$(ECHO) "  To build FPGA bitstream, add Quartus to PATH:"
	@$(ECHO) "    export PATH=\$$PATH:/path/to/intelFPGA/20.1/quartus/bin"
	@$(ECHO) "  Or run: make sof  (if Quartus is installed)"
endif
ifneq ($(SBT.CREATE_SETTINGS),)
	@$(ECHO) "Device tree: $(DEVICE_TREE_BLOB)"
	@$(ECHO) "SD card image: $(SD_FAT_TGZ)"
endif
	@$(ECHO) "==========================================="

# SD card image is cleaned by the 'clean' target

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
