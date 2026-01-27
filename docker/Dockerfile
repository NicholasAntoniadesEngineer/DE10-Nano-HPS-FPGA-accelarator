# DE10-Nano FPGA + HPS Development Environment
# Supports: Quartus Prime Lite (headless), ARM cross-compilation, Device Tree
#
# Usage on Apple Silicon:
#   docker build --platform linux/amd64 -t de10-nano-dev ./docker
#   docker run --platform linux/amd64 -it -v $(pwd):/workspace de10-nano-dev
#
# Note: Runs via x86 emulation on ARM Macs (~4x slower than native x86)

FROM raetro/quartus:18.1

LABEL maintainer="DE10-Nano Development"
LABEL description="Complete build environment for DE10-Nano FPGA and HPS development"

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Fix apt sources for Debian Stretch (EOL - moved to archive)
RUN echo "deb http://archive.debian.org/debian stretch main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security stretch/updates main contrib non-free" >> /etc/apt/sources.list && \
    echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until

# Install ARM cross-compiler and essential build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ARM Cross-compilation toolchain
    gcc-arm-linux-gnueabihf \
    g++-arm-linux-gnueabihf \
    binutils-arm-linux-gnueabihf \
    # Device Tree tools
    device-tree-compiler \
    # Build essentials
    build-essential \
    cmake \
    git \
    wget \
    curl \
    # Text editors and utilities
    vim \
    nano \
    tree \
    # Python (for scripts)
    python3 \
    python3-pip \
    # U-Boot tools
    u-boot-tools \
    # File utilities
    file \
    bc \
    bison \
    flex \
    libssl-dev \
    # Root filesystem creation tools
    debootstrap \
    qemu-user-static \
    binfmt-support \
    # SD card image creation tools
    parted \
    dosfstools \
    mtools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install GNU Make 4.3 from source (Debian Stretch has old 3.81, we need 4.0+ for --output-sync)
# Also replace Quartus's bundled old make to ensure our new version is used everywhere
RUN cd /tmp && \
    wget -q https://ftp.gnu.org/gnu/make/make-4.3.tar.gz && \
    tar xzf make-4.3.tar.gz && \
    cd make-4.3 && \
    ./configure --prefix=/usr/local && \
    make -j$(nproc) && \
    make install && \
    cd / && rm -rf /tmp/make-4.3 /tmp/make-4.3.tar.gz && \
    ln -sf /usr/local/bin/make /usr/bin/make && \
    mv /opt/intelFPGA/quartus/linux64/gnu/make /opt/intelFPGA/quartus/linux64/gnu/make.old 2>/dev/null || true && \
    ln -sf /usr/local/bin/make /opt/intelFPGA/quartus/linux64/gnu/make

# Update Debian archive keyring (Stretch's keyring is outdated for debootstrap)
RUN cd /tmp && \
    wget -q http://ftp.debian.org/debian/pool/main/d/debian-archive-keyring/debian-archive-keyring_2023.3+deb12u2_all.deb && \
    dpkg -i debian-archive-keyring_2023.3+deb12u2_all.deb && \
    rm -f debian-archive-keyring_2023.3+deb12u2_all.deb

# Set up environment variables
ENV CROSS_COMPILE=arm-linux-gnueabihf-
ENV ARCH=arm

# Quartus is already in PATH from base image, verify installation
# The base image includes: quartus_sh, quartus_pgm, quartus_cpf, etc.

# Create workspace directory
WORKDIR /workspace

# Add helper scripts
COPY scripts/ /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh 2>/dev/null || true

# Default command - show available tools
CMD ["/bin/bash", "-c", "echo '=== DE10-Nano Development Environment ===' && \
    echo '' && \
    echo 'Available tools:' && \
    echo '  Quartus:     quartus_sh, quartus_cpf, quartus_pgm' && \
    echo '  ARM GCC:     arm-linux-gnueabihf-gcc' && \
    echo '  Device Tree: dtc' && \
    echo '' && \
    echo 'Quick commands:' && \
    echo '  build-fpga.sh <project.qpf>  - Compile FPGA project' && \
    echo '  build-hps.sh <directory>     - Cross-compile HPS code' && \
    echo '' && \
    echo 'Starting bash...' && \
    exec /bin/bash"]
