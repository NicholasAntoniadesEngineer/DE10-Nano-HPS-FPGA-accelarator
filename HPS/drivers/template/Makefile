# ============================================================================
# Custom IP Driver Build (TEMPLATE)
# ============================================================================
# Rename "template" references to match your IP name.
# This builds a static library (.a) for linking into HPS applications.
# ============================================================================

CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar
CFLAGS = -Wall -Wextra -O2 -I.

# Add paths to shared libraries (e.g., logger) if needed:
# CFLAGS += -I../../applications/shared/logger

TARGET = libtemplate.a
SRCS = template_driver.c
OBJS = $(SRCS:.c=.o)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(AR) rcs $@ $^

%.o: %.c template_driver.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
