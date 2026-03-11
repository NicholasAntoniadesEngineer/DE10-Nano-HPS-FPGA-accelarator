################################################
# QSys Generation and Compilation
################################################

# Search for QSys files in quartus/qsys/ directory
QSYS_FILE := $(firstword \
	$(wildcard $(QSYS_DIR)/*top*.qsys) \
	$(wildcard $(QSYS_DIR)/*main*.qsys) \
	$(wildcard $(QSYS_DIR)/*soc*.qsys) \
	$(wildcard $(QSYS_DIR)/*.qsys) \
)
QSYS_DEPS += $(wildcard $(QSYS_DIR)/*.qsys)

################################################
# Custom IP Auto-Discovery
################################################
# Automatically find all custom IP directories containing _hw.tcl files.
# The 'template' directory is excluded — it is a reference skeleton, not a real IP.
CUSTOM_IP_DIR := $(CURDIR)/ip/custom
CUSTOM_IP_ALL_DIRS := $(patsubst %/,%,$(dir $(wildcard $(CUSTOM_IP_DIR)/*/*_hw.tcl)))
CUSTOM_IP_DIRS := $(filter-out $(CUSTOM_IP_DIR)/template,$(CUSTOM_IP_ALL_DIRS))
# Also track custom IP source files as QSys dependencies
QSYS_DEPS += $(wildcard $(CUSTOM_IP_DIR)/*/*_hw.tcl) $(wildcard $(CUSTOM_IP_DIR)/*/*.v)

# Only define QSys variables if QSYS_FILE exists
ifneq ($(QSYS_FILE),)
QSYS_BASE := $(basename $(notdir $(QSYS_FILE)))
QSYS_QIP := $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/synthesis/$(QSYS_BASE).qip) $(wildcard $(GENERATED_DIR)/$(QSYS_BASE)/$(QSYS_BASE).qip) $(wildcard $(QSYS_DIR)/$(QSYS_BASE)/synthesis/$(QSYS_BASE).qip)
QSYS_SOPCINFO := $(GENERATED_DIR)/$(QSYS_BASE).sopcinfo
else
QSYS_BASE :=
QSYS_QIP :=
QSYS_SOPCINFO :=
endif
QSYS_STAMP := $(call get_stamp_target,qsys)

# Populate ALL_DEPS
ifneq ($(strip $(QSYS_FILE)),)
ALL_DEPS += qsys-generate
endif

# Under cygwin, ensure TMP env variable is not a cygwin style path
ifeq ($(IS_CYGWIN_HOST),1)
ifneq ($(shell $(WHICH) cygpath 2>/dev/null),)
SET_QSYS_GENERATE_ENV = TMP="$(shell cygpath -m "$(TMP)")"
endif
endif

################################################
# QSys Targets
################################################

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
	bash "$$tmp_script" "$(QSYS_FILE)" "$(QSYS_DIR)" "$(GENERATED_DIR)" "$(QSYS_BASE)" "$(QSYS_STAMP)" "$(QSYS_SOPCINFO)" "$(QSYS_GENERATE_CMD)" "$(CUSTOM_IP_DIRS)"; \
	rm -f "$$tmp_script"
else
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

################################################
# QSys/Quartus Project Generation
################################################

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
qsys_generate_qsys: $(QSYS_QSYS_GEN)
	$(RM) $(QSYS_FILE)
	$(QSYS_SCRIPT_CMD) --script=$< $(QSYS_TCL_ARGS)
else
qsys_generate_qsys:
	@$(ECHO) "Make target '$@' is not supported for this design"
endif
