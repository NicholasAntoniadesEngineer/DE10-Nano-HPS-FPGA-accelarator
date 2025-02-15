CC = gcc
CFLAGS = -Wall -Wextra -O2
LDFLAGS = 

TARGET = hps_fpga_led_control
SRCS = main.c fpga_uio.c led_controller.c
OBJS = $(SRCS:.c=.o)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) -o $(TARGET) $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(TARGET) $(OBJS)

dtbo: fpga-leds.dts
	dtc -I dts -O dtb -o fpga-leds.dtbo fpga-leds.dts

install: dtbo
	sudo cp fpga-leds.dtbo /boot/overlays/
	sudo modprobe uio
	sudo modprobe uio_pdrv_genirq 