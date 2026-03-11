################################################
# Clean Targets
################################################

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
