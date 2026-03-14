# Research References

Curated references from research into Cyclone V SoC applications spanning ML inference, mechatronics, GPS-free geolocation, and underwater navigation.

---

## 1. FPGA ML Inference

### Binary Neural Networks on FPGA
- [FINN framework (BNN on FPGA)](https://github.com/Xilinx/finn) -- Xilinx/AMD
- [FINN-R paper (Blott et al., 2018)](https://arxiv.org/abs/1809.04570)
- [hls4ml (ML-to-FPGA compiler)](https://github.com/fastmachinelearning/hls4ml) -- CERN
- [XNOR-Net (Rastegari et al., 2016)](https://arxiv.org/abs/1603.05279)
- [BinaryConnect (Courbariaux et al., 2015)](https://arxiv.org/abs/1511.00363)
- [Ternary Weight Networks](https://arxiv.org/abs/1605.04711)
- [Vitis AI (Xilinx DPU)](https://github.com/Xilinx/Vitis-AI)
- [Intel OpenVINO](https://docs.openvino.ai/)
- [PipeCNN (OpenCL CNN on FPGA)](https://github.com/doonny/PipeCNN)

### Cyclone V / DE10-Nano
- [Intel Cyclone V device overview](https://www.intel.com/content/www/us/en/docs/programmable/683694/current/)
- [DE10-Nano resources (Terasic)](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&CategoryNo=165&No=1046)
- [Intel SoC FPGA Embedded Development Suite](https://www.intel.com/content/www/us/en/software-kit/661147/)
- [Platform Designer (QSys) user guide](https://www.intel.com/content/www/us/en/docs/programmable/683364/)
- [Avalon Interface Specifications](https://www.intel.com/content/www/us/en/docs/programmable/683091/)
- [Intel FPGA design examples](https://www.intel.com/content/www/us/en/support/programmable/support-resources/design-examples.html)
- [Linux SoCFPGA kernel](https://github.com/altera-opensource/linux-socfpga)

### Apple M4 / Apple Silicon (Comparison Baseline)
- [Apple M4 Pro and M4 Max announcement](https://www.apple.com/newsroom/2024/10/apple-introduces-m4-pro-and-m4-max/)
- [Core ML framework](https://developer.apple.com/documentation/coreml)
- [Apple Neural Engine / Core ML](https://developer.apple.com/machine-learning/core-ml/)
- [Metal Performance Shaders](https://developer.apple.com/documentation/metalperformanceshaders)
- [MLX (Apple ML framework)](https://github.com/ml-explore/mlx)

---

## 2. Mechatronic Applications

### Motor Control / Field-Oriented Control (FOC)
- [Intel Drive-on-a-Chip (Cyclone V reference)](https://www.intel.com/content/www/us/en/developer/articles/technical/drive-on-chip-design-example.html)
- [SimpleFOC (open-source FOC library)](https://github.com/simplefoc/Arduino-FOC)
- [ODrive (open-source motor controller)](https://github.com/odriverobotics/ODrive)
- [VESC (open-source ESC with FOC)](https://github.com/vedderb/bldc)
- [TI InstaSPIN-FOC / MotorWare](https://www.ti.com/tool/MOTORWARE)
- [Beckhoff AX8000 (FPGA-based servo)](https://www.beckhoff.com/en-en/products/motion/servo-drives/ax8000/)
- [Beckhoff XFC (eXtreme Fast Control)](https://www.beckhoff.com/en-en/products/motion/xfc-technology/)
- [B&R ACOPOS servo drives](https://www.br-automation.com/en/products/motion-control/acopos-servo-drives/)
- [Yaskawa Sigma-7 servo](https://www.yaskawa.com/products/motion/sigma-7-servo-products)
- [Microchip dsPIC motor control](https://www.microchip.com/en-us/solutions/motor-control-and-drive)
- [AMD/Xilinx motor control](https://www.amd.com/en/applications/industrial/motor-control.html)
- [FPGA-FOC (open-source FPGA FOC)](https://github.com/WangXuan95/FPGA-FOC)
- [HostMot2 (LinuxCNC FPGA firmware)](https://github.com/LinuxCNC/hostmot2-firmware)
- [STMBL (servo drive project)](https://github.com/rene-dev/stmbl)

### GaN / SiC Power Electronics
- [GaN Systems application notes](https://gansystems.com/design-center/application-notes/)
- [EPC (Efficient Power Conversion) dev kits](https://epc-co.com/epc/products/evaluation-boards)
- [OPAL-RT FPGA power electronics simulation](https://www.opal-rt.com/)
- [Texas Instruments GaN FET drivers](https://www.ti.com/power-management/gan/overview.html)
- [Infineon CoolGaN](https://www.infineon.com/cms/en/product/power/gan-hemt-gallium-nitride/)
- [Wolfspeed SiC MOSFETs](https://www.wolfspeed.com/products/power/sic-mosfets/)

### Haptics & Surgical Robotics
- [Intuitive Surgical da Vinci patent -- US 7,155,315](https://patents.google.com/patent/US7155315)
- [Raven II open-source surgical robot](https://github.com/uw-biorobotics/raven2)
- Keio University bilateral control on FPGA -- IEEE (search "FPGA bilateral control haptic")
- [Touch Surgery (Medtronic)](https://www.medtronic.com/covidien/en-us/robotic-assisted-surgery/hugo-ras-system.html)

### Collaborative Robots & Safety
- [ISO 15066:2016 (collaborative robot safety)](https://www.iso.org/standard/62996.html)
- [Universal Robots safety documentation](https://www.universal-robots.com/articles/ur/safety/)
- [IEC 61508 (functional safety)](https://www.iec.ch/functionalsafety)

### HD-EMG / Prosthetics
- [Myo armband sEMG dataset](https://github.com/UlysseCoteAllworx/sEMG-myo)
- [BioPatRec (open-source prosthetics)](https://github.com/biopatrec/biopatrec)
- [NinaPro EMG dataset](http://ninapro.hevs.ch/)

### EtherCAT & Industrial Protocols
- [EtherCAT Technology Group](https://www.ethercat.org/)
- [IgH EtherCAT Master (Linux)](https://etherlab.org/en/ethercat/)
- [SOEM (Simple Open EtherCAT Master)](https://github.com/OpenEtherCATsociety/SOEM)
- [SOES (Simple Open EtherCAT Slave)](https://github.com/OpenEtherCATsociety/SOES)

### CNC & Motion Control
- [LinuxCNC](https://linuxcnc.org/)
- [Mesa Electronics (FPGA motion cards)](http://www.mesanet.com/)
- [Machinekit](https://github.com/machinekit/machinekit)

### Real-Time Linux
- [Xenomai (real-time framework)](https://xenomai.org/)
- [PREEMPT_RT patch](https://wiki.linuxfoundation.org/realtime/start)

---

## 3. GPS-Free Geolocation

### Star Trackers & Celestial Navigation
- [Tetra star identification algorithm](https://github.com/brownj4/Tetra)
- [Astrometry.net (plate solving)](https://github.com/dstndstn/astrometry.net)
- [OpenStarTracker](https://github.com/UBNanosatLab/openstartracker)
- [ESA Hipparcos/Tycho catalogs](https://www.cosmos.esa.int/web/hipparcos/catalogues)
- [CelNav (celestial navigation library)](https://github.com/lukasmwerner/CelNav)
- [USNO Astronomical Almanac](https://aa.usno.navy.mil/)
- Liebe (1995) -- "Star Trackers for Attitude Determination" -- IEEE AES Magazine
- [ST-16 star tracker datasheet (Sinclair Interplanetary)](https://www.rfriedberg.com/wp-content/uploads/2021/03/SinclairST-16datasheet.pdf)

### Terrain Matching (TERCOM / DSMAC)
- [NASA SRTM DEM data (30m global)](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1)
- [Copernicus DEM (ESA, 30m global)](https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model)
- [OpenDEM](https://www.opendem.info/)
- Werrell -- "The Evolution of the Cruise Missile" (USAF Historical Studies)

### Visual Place Recognition
- [NetVLAD (Arandjelovic et al., 2016)](https://arxiv.org/abs/1511.07247)
- [SuperGlue (Sarlin et al., 2020)](https://github.com/magicleap/SuperGluePretrainedNetwork)
- [Patch-NetVLAD](https://github.com/QVPR/Patch-NetVLAD)
- [OpenCV feature matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html)
- [GeoEstimation (image geolocation from CNN)](https://github.com/TIBHannover/GeoEstimation)

### Sun / Shadow Methods
- [Solar position algorithm (NREL SPA)](https://midcdmz.nrel.gov/spa/)
- [PyEphem (astronomical computations)](https://github.com/brandon-rhodes/pyephem)
- [Skyfield (high-precision astronomy)](https://github.com/skyfielders/python-skyfield)

### Magnetic Navigation
- [NOAA World Magnetic Model (WMM)](https://www.ncei.noaa.gov/products/world-magnetic-model)
- [IGRF-13 (International Geomagnetic Reference Field)](https://www.ngdc.noaa.gov/IAGA/vmod/igrf.html)
- [MagNav.jl (MIT Lincoln Lab)](https://github.com/MIT-AI-Accelerator/MagNav.jl)

### IMU / Inertial Navigation
- [Madgwick AHRS filter (Fusion)](https://github.com/xioTechnologies/Fusion)
- [maplab (INS/GPS fusion)](https://github.com/ethz-asl/maplab)
- [RIDI (Robust IMU Double Integration)](https://github.com/AaltoML/RIDI)

### GPS-Denied Military Programs
- [DARPA ASPN (All Source Positioning and Navigation)](https://www.darpa.mil/program/all-source-positioning-and-navigation)
- DARPA STOIC (Spatial, Temporal, and Orientation Information in Contested Environments)

---

## 4. Underwater Navigation

### DVL (Doppler Velocity Log)
- [Nortek DVL](https://www.nortekgroup.com/products/dvl)
- [WaterLinked DVL A50](https://waterlinked.com/dvl/dvl-a50)
- [Teledyne RDI Explorer DVL](https://www.teledynemarine.com/brands/rdi/explorer-dvl)
- [LinkQuest NavQuest DVL](https://www.link-quest.com/html/navquest_600d.htm)

### AUV Platforms & Navigation
- [BlueROV2 (Blue Robotics)](https://bluerobotics.com/store/rov/bluerov2/)
- [OpenROV](https://github.com/OpenROV)
- [MOOS-IvP (AUV mission planning)](https://oceanai.mit.edu/moos-ivp/pmwiki/pmwiki.php)
- [LCM (Lightweight Communications and Marshalling)](https://github.com/lcm-proj/lcm)
- [UUV Simulator (ROS)](https://github.com/uuvsimulator/uuv_simulator)

### Acoustic Communications & Positioning
- [EvoLogics underwater modems](https://evologics.de/)
- [Sonardyne (USBL/LBL systems)](https://www.sonardyne.com/)
- [WHOI Micro-Modem](https://acomms.whoi.edu/micro-modem/)
- [Desert Star Systems (acoustic tracking)](https://desertstar.com/)

### Sonar & Bathymetry
- [OpenSidescan](https://github.com/CIDCO-dev/OpenSidescan)
- [MB-System (multibeam processing)](https://www.mbari.org/technology/mb-system/)
- [Ping sonar (Blue Robotics)](https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/)

### FPGA Sonar / Acoustic Processing
- [Analog Devices AD9361 (SDR frontend)](https://www.analog.com/en/products/ad9361.html)
- [Intel FPGA DSP design guide](https://www.intel.com/content/www/us/en/docs/programmable/683461/)
- PMUT research -- IEEE Ultrasonics Symposium proceedings

### Underwater Sensor Fusion
- [robot_localization (ROS EKF/UKF)](https://github.com/cra-ros-pkg/robot_localization)
- [GTSAM (factor graph optimization)](https://github.com/borglab/gtsam)
- Kaess et al. -- iSAM2 (incremental SLAM) -- IJRR 2012

---

## 5. FPGA Development Resources

### Intel / Altera Tools
- [Quartus Prime Lite (free)](https://www.intel.com/content/www/us/en/software-kit/795187/)
- [Intel FPGA design examples](https://www.intel.com/content/www/us/en/support/programmable/support-resources/design-examples.html)
- [Avalon Interface Specifications](https://www.intel.com/content/www/us/en/docs/programmable/683091/)

### Open-Source FPGA Tools & HDL
- [LiteX (SoC builder)](https://github.com/enjoy-digital/litex)
- [Amaranth HDL (Python)](https://github.com/amaranth-lang/amaranth)
- [SpinalHDL](https://github.com/SpinalHDL/SpinalHDL)
- [Chisel (Scala HDL)](https://github.com/chipsalliance/chisel)
- [Yosys (synthesis)](https://github.com/YosysHQ/yosys)
- [nextpnr (place-and-route)](https://github.com/YosysHQ/nextpnr)

### Tutorials & Courses
- [Nandland FPGA tutorials](https://nandland.com/)
- [FPGA4Fun](https://www.fpga4fun.com/)
- [Phil's Lab (YouTube -- FPGA + PCB design)](https://www.youtube.com/@PhilsLab)
- [Robert Feranec (YouTube -- hardware design)](https://www.youtube.com/@RobertFeranec)
- Intel FPGA DE10-Nano workshop -- search YouTube

---

## 6. Additional Mechatronics Deep Dive

### Medical Devices
- [OCRA (open-source MRI console on Red Pitaya/Zynq)](https://github.com/OpenMRI/ocra)
- [OpenEPHYS (open-source electrophysiology)](https://open-ephys.org/)

### Aerospace & Defense
- [NASA F Prime (flight software framework)](https://github.com/nasa/fprime)
- [PolarFire SoC (rad-tolerant FPGA)](https://www.microchip.com/en-us/products/fpgas-and-plds/fpgas/polarfire-fpgas)
- [Xilinx Radiation-Tolerant FPGAs](https://www.amd.com/en/products/adaptive-socs-and-fpgas/fpga/kintex-ultrascale.html)

### Digital Twin / HIL Simulation
- [OPAL-RT (real-time simulation)](https://www.opal-rt.com/)
- [dSPACE (HIL testing)](https://www.dspace.com/)
- [Typhoon HIL](https://www.typhoon-hil.com/)

### Humanoid Robotics
- [MuJoCo (physics engine)](https://github.com/google-deepmind/mujoco)
- [Isaac Gym (NVIDIA)](https://developer.nvidia.com/isaac-gym)
- [Pinocchio (rigid body dynamics)](https://github.com/stack-of-tasks/pinocchio)

### Brain-Computer Interfaces
- [OpenBCI](https://openbci.com/)
- [BCI2000](https://www.bci2000.org/)
- [MNE-Python (MEG/EEG analysis)](https://github.com/mne-tools/mne-python)

### Agricultural Robotics
- [ROS Agriculture](https://github.com/ros-agriculture)
- [OpenWeedLocator](https://github.com/geezacoleman/OpenWeedLocator)
- [FarmHack](https://farmhack.org/)

### Fusion Energy / Plasma Control
- [ITER (international fusion project)](https://www.iter.org/)
- [MARTe2 (real-time control framework)](https://github.com/aneto0/MARTe2)

---

## Papers (arXiv)

| ID | Topic |
|----|-------|
| [1603.05279](https://arxiv.org/abs/1603.05279) | XNOR-Net (binary neural networks) |
| [1511.00363](https://arxiv.org/abs/1511.00363) | BinaryConnect |
| [1605.04711](https://arxiv.org/abs/1605.04711) | Ternary Weight Networks |
| [1809.04570](https://arxiv.org/abs/1809.04570) | FINN-R (BNN on FPGA) |
| [1511.07247](https://arxiv.org/abs/1511.07247) | NetVLAD (visual place recognition) |
