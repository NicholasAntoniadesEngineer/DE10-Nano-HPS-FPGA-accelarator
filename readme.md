# low-latency-market-analysis

a low-latency market data processing system using the de10 nano (cyclone v soc) platform.

## project overview

this project implements a high-performance market data processing system using the de10 nano's dual-core arm cortex-a9 processor and cyclone v fpga. the system is designed to process market data streams, detect trading opportunities, and execute trades with minimal latency.

### key features

- real-time market data processing on fpga fabric
- hardware-accelerated technical indicator calculations
- low-latency order execution system
- integration with alpaca markets api
- websocket-based market data ingestion
- custom linux drivers for fpga communication
- integration of the RFS2 board for wireless communication and networking

## project structure

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
│       ├── build.sh
│       └── program.sh
│
└── docs/
    ├── hps/
    └── fpga/
```

### directory structure explanation

- `hps/`: hardware processing system (arm cores) code
  - `core0/`: primary core handling market data ingestion
  - `core1/`: secondary core for strategy execution
  - `common/`: shared libraries and headers
- `fpga/`: fpga fabric implementation
  - `src/hdl/`: verilog/vhdl source files
  - `src/constraints/`: timing and pin constraints
- `docs/`: documentation for both hps and fpga components

### build system

each component has its own build and execution scripts:

#### hps build system
- `core0/scripts/build.sh`: compiles market data handling components
- `core0/scripts/run.sh`: deploys and runs core0 processes
- `core1/scripts/build.sh`: compiles strategy execution components
- `core1/scripts/run.sh`: deploys and runs core1 processes

#### fpga build system
- `fpga/scripts/build.sh`: synthesizes and implements fpga design
- `fpga/scripts/program.sh`: programs the fpga with generated bitstream

## hardware requirements

- terasic de10 nano development board
- ethernet connection
- microsd card (16gb+ recommended)
- usb power supply

## software requirements

- quartus prime lite (free version)
- DE10-Nano System Builder  
- linux os (custom built or provided image)
- alpaca markets api account (free paper trading account)
- sdcard flashing tool (etcher)

## system architecture

### fpga components
- market data parser
- order book management
- moving average calculation engine
- momentum indicator processor
- pattern recognition module

### software components
- linux-based control system
- alpaca markets api interface
- configuration and monitoring interface
- trading strategy implementation
- data logging and analysis tools

## development roadmap

### phase 1: basic infrastructure
- linux system setup
- fpga-software communication
- basic market data ingestion

### phase 2: fpga development
- implement market data parser
- develop technical indicator modules
- create order book management system

### phase 3: trading system
- strategy implementation
- risk management
- performance optimization

### phase 4: Integrate the RFS2 board
- implement wireless communication
- add networking capabilities for remote monitoring and control

## testing

the system can be tested using:
- alpaca's paper trading environment
- historical market data replay
- simulated market data generation

## performance metrics

target performance metrics:
- market data processing latency: <1μs
- order execution latency: <10μs
- strategy calculation time: <5μs


## references

### OEM documentation
- [DE10-Nano System Builder](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=en-us&CategoryNo=167&No=1004)
- [Alpaca Markets API](https://alpaca.markets/learn/api-documentation/)
- [Terasic DE10-Nano](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=en-us&CategoryNo=167&No=1004)

### course material

- [ECE5760 - DE10-Nano Linux Image](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/DE1-SoC-UP-Linux/linux_sdcard_image.zip)
- [ECE5760 - FPGA Design](https://people.ece.cornell.edu/land/courses/ece5760/)
- [ECE5760 - HPS Peripherals](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/HPS_peripherials/linux_index.html)
- [ECE5760 - Lab 1](https://bpb-us-w2.wpmucdn.com/sites.coecis.cornell.edu/dist/4/81/files/2017/03/ece5760_lab1-18xgakl.pdf)

### youtube
- [Bruce Land - Cornell University](https://www.youtube.com/watch?v=fQAicY9a3DM&list=PLKcjQ_UFkrd7UcOVMm39A6VdMbWWq-e_c)
- [Hunter Adams - Cornell University](https://www.youtube.com/watch?v=F9IYUOXtlPo)



