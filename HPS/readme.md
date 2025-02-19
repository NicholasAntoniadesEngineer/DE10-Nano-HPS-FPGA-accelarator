# HPS Development Guide

This guide outlines the workflow for developing and deploying custom Linux images for the DE10-Nano's HPS (Hard Processor System).

## Overview

The DE10-Nano's HPS (Hard Processor System) allows you to run a full Linux operating system alongside the FPGA fabric. This enables powerful combinations of software and hardware acceleration.

## Getting Started

1. **Linux HPS Image**
   - For building and deploying Linux images, see [Linux HPS Images](linux_hps_image.md)
   - Includes both Debian and Yocto-based approaches

2. **Development Workflow**
   - For day-to-day development and troubleshooting, see [Development Workflow](development_workflow.md)
   - Covers kernel modules, application development, and common issues

3. **HPS and FPGA Communication**
   - For setting up communication between HPS and FPGA, see [HPS-FPGA Communication](hps_fpga_communication.md)
   - Covers bridge setup, device drivers, and example implementations

## Resources

- [DE10-Nano Documentation](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046)
- [Linux Kernel Documentation](https://www.kernel.org/doc/html/latest/)
- [Yocto Project Documentation](https://docs.yoctoproject.org/)