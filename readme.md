# low-latency-market-analysis

The goal of this project is to implement a high-speed market data processing system using Altera's Cyclone V FPGA for hardware acceleration. 

The system will be designed to process market data streams, detect trading opportunities, and execute trades.

### Key features

- Real-time market data processing on fpga fabric
- Hardware-accelerated technical indicator calculations
- Low-latency order execution system
- Integration with alpaca markets api
- Websocket-based market data ingestion
- Custom linux drivers for fpga communication
- Integration of the RFS2 board for wireless communication and networking

## Project structure

```
low-latency-market-analysis/
├── hps/
│   └── linux_image/
│   │   └── scripts/
│   │       ├── build.sh
│   │       └── program.sh
│   └── market_analysis_application/
│  
├── fpga/
│   ├── src/
│   │   ├── hdl/
│   │   │   ├── market_data_parser/
│   │   │   ├── technical_indicators/
│   │   │   └── order_book/
│   └── scripts/
│   │   ├── build.sh
│   │   └── program.sh
│   └── tools/
│       └──DE10_Nano_SystemBuilder.exe
│ 
├── examples/
│   ├── fpga_examples/
│   ├── hps_examples/
│   └── hps_fpga_examples/
│
└── docs/
    ├── hps/
    └── fpga/
```

### Directory structure explanation

- `hps/`: hardware processing system (arm cores) code
  - `core0/`: primary core handling market data ingestion
  - `core1/`: secondary core for strategy execution
  - `common/`: shared libraries and headers
- `fpga/`: fpga fabric implementation
  - `src/hdl/`: verilog/vhdl source files
  - `src/constraints/`: timing and pin constraints
- `docs/`: documentation for both hps and fpga components

### Build system

Each component has its own build and execution scripts:

#### HPS build system
- `core0/scripts/build.sh`: compiles market data handling components
- `core0/scripts/run.sh`: deploys and runs core0 processes
- `core1/scripts/build.sh`: compiles strategy execution components
- `core1/scripts/run.sh`: deploys and runs core1 processes

#### FPGA build system
- `fpga/scripts/build.sh`: synthesizes and implements fpga design
- `fpga/scripts/program.sh`: programs the fpga with generated bitstream

## Hardware requirements

- Terasic de10 nano development board
- Ethernet connection
- Microsd card (16gb+ recommended)
- USB power supply

## Software requirements

- Quartus Prime lite (free version)
  - compile the fpga design and and programme fpga
- DE10-Nano System Builder  
- Linux os (custom built or provided image)
- Alpaca markets api account (free paper trading account)
- Sdcard flashing tool (etcher)

## System architecture

### FPGA components
- Market data parser
- Order book management
- Moving average calculation engine
- Momentum indicator processor
- Pattern recognition module

### Software components
- Linux-based control system
- Alpaca markets api interface
- Configuration and monitoring interface
- Trading strategy implementation
- Data logging and analysis tools

## Development roadmap

### Phase 1: basic infrastructure
- Linux system setup
- FPGA-software communication
- Basic market data ingestion

### Phase 2: fpga development
- Implement market data parser
- Develop technical indicator modules
- Create order book management system

### Phase 3: trading system
- Strategy implementation
- Risk management
- Performance optimization

### Phase 4: Integrate the RFS2 board
- Implement wireless communication
- Add networking capabilities for remote monitoring and control

## References

### OEM documentation
- [De10-nano CD download](https://download.terasic.com/downloads/cd-rom/de10-nano/ ) 
- [Terasic DE10-Nano](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046#contents)
- [Cyclone V HPS Register Address Map and Definitions](https://www.intel.com/content/www/us/en/programmable/hps/cyclone-v/hps.html#sfo1418687413697.html)

### Websites and Repositories
- [Building embedded linux for the terasic de10-nano](https://bitlog.it/20170820_building_embedded_linux_for_the_terasic_de10-nano.html)
- [zangman/de10-nano](https://github.com/zangman/de10-nano?tab=readme-ov-file)

### Cornell University ECE5760 course material
- [Linux Image](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/DE1-SoC-UP-Linux/linux_sdcard_image.zip)
- [FPGA Design](https://people.ece.cornell.edu/land/courses/ece5760/)
- [HPS Peripherals](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/HPS_peripherials/linux_index.html)
- [Lab 1](https://bpb-us-w2.wpmucdn.com/sites.coecis.cornell.edu/dist/4/81/files/2017/03/ece5760_lab1-18xgakl.pdf)

### Youtube
- [Bruce Land - Cornell University](https://www.youtube.com/watch?v=fQAicY9a3DM&list=PLKcjQ_UFkrd7UcOVMm39A6VdMbWWq-e_c)
- [Hunter Adams - Cornell University](https://www.youtube.com/watch?v=F9IYUOXtlPo)

