CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

DRIVER_DIR   := $(CURDIR)
HPS_DIR      := $(abspath $(DRIVER_DIR)/../..)
LIBS_DIR     := $(HPS_DIR)/libs
FPGA_UIO_DIR  = $(DRIVER_DIR)/../fpga_uio
FPGA_UIO_LIB  = $(FPGA_UIO_DIR)/libfpga_uio.a

TARGET = libcalculator.a
SRCS   = calculator_driver.c
OBJS   = $(SRCS:.c=.o)
DEPS   = calculator_driver.h $(FPGA_UIO_DIR)/fpga_uio.h $(LIBS_DIR)/logger/logger.h

CFLAGS  = -Wall -Wextra -O2 -g -std=gnu99 -D_GNU_SOURCE
CFLAGS += -I$(LIBS_DIR)/logger
CFLAGS += -I$(FPGA_UIO_DIR)

.PHONY: all clean fpga_uio

all: fpga_uio $(TARGET)

fpga_uio:
	$(MAKE) -C $(FPGA_UIO_DIR)

$(TARGET): $(OBJS)
	$(AR) rcs $@ $^ $(FPGA_UIO_LIB)

%.o: %.c $(DEPS)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
	$(MAKE) -C $(FPGA_UIO_DIR) clean
