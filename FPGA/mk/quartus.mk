################################################
# Quartus II Compilation
################################################

# Search for Quartus project files in quartus/ directory
QUARTUS_QPF ?= $(firstword \
	$(wildcard $(QUARTUS_DIR)/*.qpf) \
)
# Fallback for environments where QUARTUS_DIR expansion is polluted (e.g., CRLF issues on WSL)
ifeq ($(strip $(QUARTUS_QPF)),)
QUARTUS_QPF := $(firstword $(wildcard quartus/*.qpf))
endif
ifneq ($(filter clean help,$(MAKECMDGOALS)),)
QUARTUS_QPF ?=
else
ifeq ($(strip $(QUARTUS_QPF)),)
$(error ERROR: QUARTUS_QPF *.qpf file not set and could not be discovered in $(QUARTUS_DIR))
endif
endif

# Only define Quartus variables if QUARTUS_QPF exists
ifneq ($(strip $(QUARTUS_QPF)),)
QUARTUS_QSF := $(patsubst %.qpf,%.qsf,$(QUARTUS_QPF))
QUARTUS_BASE := $(basename $(notdir $(QUARTUS_QPF)))
else
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

# Build FPGA bitstream (if Quartus available)
ifeq ($(HAVE_QUARTUS),1)
ALL_DEPS += sof rbf
endif

################################################
# Quartus Compile Targets
################################################

.PHONY: quartus-compile
quartus-compile: quartus_compile

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

################################################
# Pin Assignment Application (recursive)
################################################

ifeq ($(QUARTUS_ENABLE_PIN_ASSIGNMENTS_APPLY),1)

QUARTUS_TCL_PIN_ASSIGNMENTS = $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl) $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/synth/submodules/*_pin_assignments.tcl) $(wildcard $(QSYS_DIR)/$(QSYS_BASE)/synthesis/submodules/*_pin_assignments.tcl) $(wildcard $(QSYS_DIR)/$(QSYS_BASE)/synth/submodules/*_pin_assignments.tcl)
QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS = $(patsubst %,quartus_apply_tcl-%,$(QUARTUS_TCL_PIN_ASSIGNMENTS))

.PHONY: quartus_apply_tcl_pin_assignments
quartus_apply_tcl_pin_assignments: $(QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS)

.PHONY: $(QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS)
$(QUARTUS_TCL_PIN_ASSIGNMENTS_APPLY_TARGETS): quartus_apply_tcl-%: %
	@$(ECHO) "Applying $<... to $(QUARTUS_QPF)..."
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

################################################
# Quartus Compilation Rule
################################################

ifneq ($(strip $(QUARTUS_QPF)),)
$(QUARTUS_STAMP): $(QUARTUS_DEPS)
	@$(MKDIR) $(BUILD_DIR)/output_files
	@$(ECHO) "Compiling Quartus project: $(notdir $(QUARTUS_QPF))"
	@$(ECHO) "Using Quartus: $(QUARTUS_SH_CMD)"
	@$(ECHO) "Parallel jobs: $(QUARTUS_PARALLEL_JOBS) (set QUARTUS_PARALLEL_JOBS to override)"
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
$(QUARTUS_STAMP):
	@$(ECHO) "Skipping Quartus compilation (no Quartus project file found)"
endif

################################################
# SOF / RBF Generation
################################################

HELP_TARGETS += sof
sof.HELP := QSys generate & Quartus compile this design
ifneq ($(HAVE_QUARTUS),1)
sof.HELP := $(sof.HELP) (Install Quartus II Software to enable)
endif

BATCH_TARGETS += sof

.PHONY: sof
sof: $(QUARTUS_SOF)

QUARTUS_RBF := $(patsubst %.sof,%.rbf,$(QUARTUS_SOF))

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

################################################
# Quartus Editor
################################################

HELP_TARGETS += quartus_edit
quartus_edit.HELP := Launch Quartus II GUI
ifneq ($(HAVE_QUARTUS),1)
quartus_edit.HELP := $(quartus_edit.HELP) (Install Quartus II Software to enable)
endif

.PHONY: quartus_edit
quartus_edit:
	quartus $(QUARTUS_QPF) &
