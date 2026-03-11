################################################
# Tool Detection with Caching
#
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

# Check for QSys tools
QSYS_GENERATE := $(shell $(WHICH) qsys-generate 2>/dev/null)
ifneq ($(QSYS_GENERATE),)
HAVE_QSYS_GENERATE := 1
else
QSYS_GENERATE := $(shell $(WHICH) qsys-generate.exe 2>/dev/null)
ifneq ($(QSYS_GENERATE),)
HAVE_QSYS_GENERATE := 1
else
# Try common Windows QSys installation paths (for WSL)
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

# Save detected tool paths to cache
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

################################################
# Quartus Tool Commands
################################################

ifeq ($(HAVE_QUARTUS),1)
ifneq ($(QUARTUS_SH),)
QUARTUS_SH_CMD := $(QUARTUS_SH)
QUARTUS_STP_CMD := $(subst quartus_sh.exe,quartus_stp.exe,$(subst quartus_sh,quartus_stp,$(QUARTUS_SH)))
QUARTUS_CPF_CMD := $(subst quartus_sh.exe,quartus_cpf.exe,$(subst quartus_sh,quartus_cpf,$(QUARTUS_SH)))
QUARTUS_STA_CMD := $(subst quartus_sh.exe,quartus_sta.exe,$(subst quartus_sh,quartus_sta,$(QUARTUS_SH)))
QUARTUS_PGM_CMD := $(subst quartus_sh.exe,quartus_pgm.exe,$(subst quartus_sh,quartus_pgm,$(QUARTUS_SH)))
QUARTUS_MAP_CMD := $(subst quartus_sh.exe,quartus_map.exe,$(subst quartus_sh,quartus_map,$(QUARTUS_SH)))
QUARTUS_CDB_CMD := $(subst quartus_sh.exe,quartus_cdb.exe,$(subst quartus_sh,quartus_cdb,$(QUARTUS_SH)))
else
QUARTUS_SH_CMD := quartus_sh
QUARTUS_STP_CMD := quartus_stp
QUARTUS_CPF_CMD := quartus_cpf
QUARTUS_STA_CMD := quartus_sta
QUARTUS_PGM_CMD := quartus_pgm
QUARTUS_MAP_CMD := quartus_map
QUARTUS_CDB_CMD := quartus_cdb
endif
else
QUARTUS_SH_CMD := quartus_sh
QUARTUS_STP_CMD := quartus_stp
QUARTUS_CPF_CMD := quartus_cpf
QUARTUS_STA_CMD := quartus_sta
QUARTUS_PGM_CMD := quartus_pgm
QUARTUS_MAP_CMD := quartus_map
QUARTUS_CDB_CMD := quartus_cdb
endif

################################################
# QSys Tool Commands
################################################

ifeq ($(HAVE_QSYS_GENERATE),1)
ifneq ($(QSYS_GENERATE),)
QSYS_GENERATE_CMD := $(QSYS_GENERATE)
QSYS_EDIT_CMD := $(patsubst %qsys-generate%,%qsys-edit%,$(QSYS_GENERATE))
QSYS_SCRIPT_CMD := $(patsubst %qsys-generate%,%qsys-script%,$(QSYS_GENERATE))
else
QSYS_GENERATE_CMD := qsys-generate
QSYS_EDIT_CMD := qsys-edit
QSYS_SCRIPT_CMD := qsys-script
endif
else
QSYS_GENERATE_CMD := qsys-generate
QSYS_EDIT_CMD := qsys-edit
QSYS_SCRIPT_CMD := qsys-script
endif

endif # SKIP_TOOL_DETECTION

################################################
# Tool Check Targets
################################################

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
