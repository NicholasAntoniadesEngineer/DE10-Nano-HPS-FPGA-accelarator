# ============================================================================
# HPS Application Binary Auto-Discovery
# ============================================================================
# Included by rootfs and linux_image Makefiles to track app binaries as
# dependencies. When any binary is recompiled, rootfs and SD image rebuild.
#
# Convention: each app directory contains a Makefile and produces a binary
# with the same name as the directory (e.g., boot_led/boot_led).
# Adding a new app requires NO changes here — just follow the convention.
# ============================================================================

_HPS_APPS_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
_APP_DIRS := $(dir $(wildcard $(_HPS_APPS_DIR)/*/Makefile))
APP_BINARIES := $(foreach d,$(_APP_DIRS),$(wildcard $(d)$(notdir $(patsubst %/,%,$(d)))))
