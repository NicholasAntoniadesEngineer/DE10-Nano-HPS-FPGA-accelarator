# ============================================================================
# template - Makefile
# ============================================================================
# Cross-compilation Makefile for ARM (HPS on DE10-Nano)
# ============================================================================

TARGET       = template

CROSS_COMPILE ?= arm-linux-gnueabihf-
CC            = $(CROSS_COMPILE)gcc
STRIP         = $(CROSS_COMPILE)strip

LOGGER_DIR    = ../../libs/logger

CFLAGS  = -Wall -Wextra -O2 -std=gnu99 -D_GNU_SOURCE
CFLAGS += -I$(LOGGER_DIR)

SRCS = template.c \
       $(LOGGER_DIR)/logger.c

OBJS = template.o logger.o

DEPS = $(LOGGER_DIR)/logger.h

.PHONY: all clean strip help

all: $(TARGET)

$(TARGET): $(OBJS)
	@echo "Linking $@..."
	$(CC) $^ -o $@
	@echo "Build complete: $(TARGET)"

template.o: template.c $(DEPS)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

logger.o: $(LOGGER_DIR)/logger.c $(LOGGER_DIR)/logger.h
	@echo "Compiling logger..."
	$(CC) $(CFLAGS) -c $(LOGGER_DIR)/logger.c -o $@

clean:
	rm -f $(TARGET) $(OBJS) *~
	@echo "Clean complete"

strip: $(TARGET)
	$(STRIP) $(TARGET)
	@echo "Stripped size:"; ls -lh $(TARGET)

help:
	@echo "template Makefile"
	@echo "  make          - Build ARM binary"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make strip    - Strip debug symbols"
	@echo "  make CROSS_COMPILE=  - Native build on DE10-Nano"
