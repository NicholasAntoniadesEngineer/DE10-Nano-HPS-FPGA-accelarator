#!/bin/bash

# Make UIO modules load at boot
echo "Setting up UIO modules to load at boot..."
if ! grep -q "uio" /etc/modules; then
    sudo sh -c 'echo "uio" >> /etc/modules'
fi
if ! grep -q "uio_pdrv_genirq" /etc/modules; then
    sudo sh -c 'echo "uio_pdrv_genirq" >> /etc/modules'
fi

# Compile and install device tree overlay
echo "Installing device tree overlay..."
make dtbo
sudo mkdir -p /boot/overlays
sudo cp fpga-leds.dtbo /boot/overlays/

# Add overlay to boot configuration
echo "Adding overlay to boot configuration..."
if ! grep -q "fpga-leds" /boot/config.txt; then
    sudo sh -c 'echo "dtoverlay=fpga-leds" >> /boot/config.txt'
fi

echo "Setup complete. Please reboot your system for changes to take effect." 