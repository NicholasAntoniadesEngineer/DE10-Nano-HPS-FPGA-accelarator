# ============================================================================
# Calculator Demo - Makefile
# ============================================================================
# Cross-compilation Makefile for ARM (HPS on DE10-Nano)
# ============================================================================

TARGET       = calculator_demo

CROSS_COMPILE ?= arm-linux-gnueabihf-
CC            = $(CROSS_COMPILE)gcc
STRIP         = $(CROSS_COMPILE)strip

LOGGER_DIR    = ../../libs/logger
DRIVER_DIR    = ../../drivers/calculator

CFLAGS  = -Wall -Wextra -O2 -std=gnu99 -D_GNU_SOURCE
CFLAGS += -I$(LOGGER_DIR) -I$(DRIVER_DIR)

LDFLAGS = -lm

SRCS = calculator_demo.c \
       $(DRIVER_DIR)/calculator_driver.c \
       $(LOGGER_DIR)/logger.c

OBJS = calculator_demo.o calculator_driver.o logger.o

DEPS = $(DRIVER_DIR)/calculator_driver.h $(LOGGER_DIR)/logger.h

.PHONY: all clean strip help

all: $(TARGET)

$(TARGET): $(OBJS)
	@echo "Linking $@..."
	$(CC) $(LDFLAGS) $^ -o $@
	@echo "Build complete: $(TARGET)"

calculator_demo.o: calculator_demo.c $(DEPS)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

calculator_driver.o: $(DRIVER_DIR)/calculator_driver.c $(DRIVER_DIR)/calculator_driver.h
	@echo "Compiling calculator driver..."
	$(CC) $(CFLAGS) -c $(DRIVER_DIR)/calculator_driver.c -o $@

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
	@echo "Calculator Demo Makefile"
	@echo "  make          - Build ARM binary"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make strip    - Strip debug symbols"
	@echo "  make CROSS_COMPILE=  - Native build on DE10-Nano"
