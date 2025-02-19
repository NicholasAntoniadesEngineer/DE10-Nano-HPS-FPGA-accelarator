# HPS Development Guide

This guide outlines the workflow for developing and deploying custom Linux images for the DE10-Nano's HPS (Hard Processor System).

## Overview

The DE10-Nano's HPS (Hard Processor System) allows you to run a full Linux operating system alongside the FPGA fabric. This enables powerful combinations of software and hardware acceleration.

## Linux HPS image.

We support two main development paths for the HPS:
1. Full Custom Debian Build - For maximum flexibility and control
2. Yocto-Based Build - For streamlined, production-focused development

For detailed instructions on both approaches, including build processes, SD card creation, development workflows, and troubleshooting, see [Linux HPS images](linux_hps_image.md).

## HPS and FPGA communication.

## Resources

- [DE10-Nano Documentation](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046)
- [Linux Kernel Documentation](https://www.kernel.org/doc/html/latest/)
- [Yocto Project Documentation](https://docs.yoctoproject.org/)