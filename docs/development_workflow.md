# Development Workflow and Troubleshooting

This guide covers the general development workflow and troubleshooting tips for HPS development on the DE10-Nano.

## Development Workflow

1. **Environment Setup**
   - Install required development tools and cross-compiler
   - Set up network connectivity for the DE10-Nano
   - Configure SSH access (optional but recommended)

2. **Initial System Setup**
   - Build or download base Linux image (see [Linux HPS Images](linux_hps_image.md))
   - Flash SD card with the image
   - Boot DE10-Nano and verify:
     - Network connectivity
     - Access to required tools/compilers
     - Basic system functionality

3. **Development Cycle**

   a. **Application Development**
      - Set up cross-compilation environment
      - Write and compile applications
      - Deploy to target:
      ```bash
      scp myapp root@de10-nano:/usr/local/bin/
      ```
      - Test and debug on the device

   b. **Kernel Module Development**
      - Write module code
      - Set up module build environment
      - Cross-compile against target kernel
      - Deploy and test:
      ```bash
      scp mymodule.ko root@de10-nano:/lib/modules/$(uname -r)/
      ssh de10-nano "insmod /lib/modules/$(uname -r)/mymodule.ko"
      ssh de10-nano "dmesg | tail"
      ```

4. **Testing and Validation**
   - Connect via UART for low-level debugging (115200 baud)
   - Default login: root/terasic
   - Verify functionality:
     - Check system logs: `dmesg`, `journalctl`
     - Monitor resource usage: `top`, `htop`
     - Test specific functionality
   - Run automated tests if available

5. **Deployment**
   - Back up working configurations
   - Document any system requirements
   - Create deployment package if needed
   - Update system image for production
