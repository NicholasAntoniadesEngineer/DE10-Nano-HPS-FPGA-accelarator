## Work Flow
- Framework for Code
  - Generated using the DE10-Nano system builder from the CD.
  - Base your design on the GHRD (Generic Hardware Reference Design):
    - The GHRD provides a pre-configured hardware reference for the DE10-Nano.
    - Use it as your default example and foundation for further customization.

The qsys file has the actual low level ip blocks and the connections between them.
 - You can create your own ip blocks in the qsys file. From hdl files.

- Platform Designer (Qsys - inside of Quartus Prime Lite)
  - **Open and Modify the System in Platform Designer:**
    - Launch Qsys and load your design.
  - **Configure HPS-FPGA Interfaces:**
    - Set up the interface parameters between the HPS and FPGA.
  - **Add and Configure Required IP Cores:**
    - Incorporate all necessary IPs (e.g., GPIO, memory controllers, custom logic blocks).
  - **Connect the IP Cores ("Wiring"):**
    - Manually or automatically interconnect master and slave interfaces.
    - Validate interconnects and confirm that signals are correctly routed.
    - Use Qsys's built-in verification tools to check for connection errors.
  - **Generate HDL for the System:**
    - Once the connections are completed and verified, generate the HDL. This HDL now integrates your custom logic with the GHRD baseline.
  
- Development with Quartus Prime Lite
  - Customize the generated implementation (originating from the GHRD and Qsys configuration).
  - Compile and synthesize the design.
  - Run analysis and timing simulations to validate hardware performance.
  
- Program the FPGA:
  - Use the Quartus Programmer GUI.
  - Or utilize a command line/bash script from the default example.

## System Initialisation
- When the DE10-Nano boots from the HPS, the bootloader configures the FPGA using the soc_system.rbf file provided on the microSD card.
- The soc_system.rbf file is generated from a .sof file by running the batch file sof_to_rbf.bat.
- This batch file is supplied by Terasic and is located in the examples folder.
- The conversion utility quarthps_cpf.exe is used to convert the .sof into the .rbf format.
  

## Test Set Up Example
- Utilize 3 GPIOs on the FPGA side. When these GPIOs are triggered, they generate interrupts on the HPS side.
- These interrupts trigger different logic blocks in the code, potentially resulting in 3 different LED patterns.
