CROSS_COMPILE ?= arm-linux-gnueabihf-
CC = $(CROSS_COMPILE)gcc
AR = $(CROSS_COMPILE)ar

DRIVER_DIR   := $(CURDIR)
FPGA_UIO_DIR  = $(DRIVER_DIR)/../fpga_uio
FPGA_UIO_LIB  = $(FPGA_UIO_DIR)/libfpga_uio.a

TARGET = libtemplate.a
SRCS   = template_driver.c
OBJS   = $(SRCS:.c=.o)
DEPS   = template_driver.h $(FPGA_UIO_DIR)/fpga_uio.h

CFLAGS  = -Wall -Wextra -O2 -std=gnu99 -D_GNU_SOURCE
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
