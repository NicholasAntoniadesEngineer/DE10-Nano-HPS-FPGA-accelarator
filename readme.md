# Low-Latency Market Analysis

High-speed market data processing system using Altera's Cyclone V FPGA for hardware acceleration on the DE10-Nano SoC board.

## Project Overview

This project implements a hardware-accelerated trading system that processes market data streams, detects trading opportunities, and executes trades with minimal latency. The system leverages the DE10-Nano's FPGA fabric for real-time calculations and the HPS (Hard Processor System) for control and communication.

### Key Features

- Real-time market data processing on FPGA fabric
- Hardware-accelerated technical indicator calculations
- Low-latency order execution system
- Integration with Alpaca Markets API
- Websocket-based market data ingestion
- Custom Linux drivers for FPGA communication
- Integration of the RFS2 board for wireless communication and networking

## Repository Structure

```
low-latency-market-analysis/
├── README.md                    # This file
├── FPGA/                        # FPGA design and build system
│   ├── Makefile                 # FPGA build system
│   ├── README.md                # FPGA documentation
│   ├── hdl/                     # Top-level HDL files
│   ├── ip/                      # IP cores (custom and vendor)
│   ├── quartus/                 # Quartus project files
│   ├── generated/               # Generated QSys files
│   └── build/                   # Build outputs (SOF, RBF)
├── HPS/                         # HPS software (ARM applications)
│   ├── Makefile                 # HPS build system
│   ├── README.md                # HPS documentation
│   ├── calculator_test/         # Calculator IP test suite
│   ├── integration/             # Linux kernel integration tools
│   └── led_examples/            # LED control examples
├── Docs/                        # Documentation
│   ├── setup/                   # Setup and installation guides
│   ├── development/             # Development workflows
│   ├── fpga/                    # FPGA-specific documentation
│   ├── hps/                     # HPS-specific documentation
│   └── reference/               # Reference materials (PDFs)
└── examples/                    # Example projects
    ├── fpga_examples/
    ├── hps_examples/
    └── hps_fpga_examples/
```

## Quick Start

### Building FPGA Design

```bash
# Navigate to FPGA directory
cd FPGA

# Build FPGA bitstream
make sof

# Generate RBF file for SD card boot
make rbf
```

### Building HPS Software

```bash
# Navigate to HPS directory
cd HPS

# Build all HPS components
make

# Or build specific components
make calculator_test
make led_examples
```

### Using Prebuilt Linux Image

1. **Write prebuilt image to SD card**
2. **Boot DE10-Nano and pull repository**
3. **Build HPS software:** `cd HPS && make`
4. **Update FPGA bitstream on SD card:** Copy RBF file to FAT partition
5. **Run tests:** `./calculator_test`

See [HPS/README.md](HPS/README.md) for detailed instructions.

## Hardware Requirements

- Terasic DE10-Nano development board
- Ethernet connection
- MicroSD card (16GB+ recommended)
- USB power supply
- USB-to-UART cable (optional, for console)

## Software Requirements

- **Quartus Prime Lite** (free version) - For FPGA design compilation
- **DE10-Nano System Builder** - For initial system setup
- **Linux OS** - Custom built or provided image
- **Alpaca Markets API account** - Free paper trading account available
- **SD card flashing tool** - Etcher or similar

## System Architecture

### FPGA Components

- Market data parser
- Order book management
- Moving average calculation engine
- Momentum indicator processor
- Pattern recognition module
- Calculator IP (current implementation)

### Software Components

- Linux-based control system
- Alpaca Markets API interface
- Configuration and monitoring interface
- Trading strategy implementation
- Data logging and analysis tools

## Documentation

- **[FPGA/README.md](FPGA/README.md)** - FPGA design documentation
- **[HPS/README.md](HPS/README.md)** - HPS software documentation
- **[Docs/setup/](Docs/setup/)** - Setup and installation guides
- **[Docs/development/](Docs/development/)** - Development workflows
- **[Docs/fpga/](Docs/fpga/)** - FPGA-specific documentation
- **[Docs/hps/](Docs/hps/)** - HPS-specific documentation

## Development Roadmap

### Phase 1: Basic Infrastructure ✓
- Linux system setup
- FPGA-software communication
- Basic market data ingestion
- Calculator IP implementation

### Phase 2: FPGA Development
- Implement market data parser
- Develop technical indicator modules
- Create order book management system

### Phase 3: Trading System
- Strategy implementation
- Risk management
- Performance optimization

### Phase 4: RFS2 Integration
- Implement wireless communication
- Add networking capabilities for remote monitoring and control

## Build System

Each component has its own Makefile:

- **FPGA:** `cd FPGA && make` - Builds FPGA bitstream
- **HPS:** `cd HPS && make` - Builds all HPS software components

## References

### OEM Documentation

- [DE10-Nano CD Download](https://download.terasic.com/downloads/cd-rom/de10-nano/)
- [Terasic DE10-Nano](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046#contents)
- [Cyclone V HPS Register Address Map](https://www.intel.com/content/www/us/en/programmable/hps/cyclone-v/hps.html#sfo1418687413697.html)

### Community Resources

- [Building Embedded Linux for DE10-Nano](https://bitlog.it/20170820_building_embedded_linux_for_the_terasic_de10-nano.html)
- [zangman/de10-nano](https://github.com/zangman/de10-nano)

### Cornell University ECE5760

- [Linux Image](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/DE1-SoC-UP-Linux/linux_sdcard_image.zip)
- [FPGA Design](https://people.ece.cornell.edu/land/courses/ece5760/)
- [HPS Peripherals](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/HPS_peripherials/linux_index.html)

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
