
## Work FLow
- Framework for code
    - Generated using the DE10-Nano system builder from the cd.
    - Use another default example.   
- Development with Quartus prime lite.
    - Customise the generated implementation.
    - Compile the code.
    - Analysis and synthesis.
- Program the FPGA:
    - Using the Quartus programmer GUI.
    - Using a command line/ bash script from the default example.

## System Initialisation
- When the DE10-Nano boots from HPS, the bootloader configures the FPGA using the soc_system.rbf file provided on the microSD card.
- The soc_system.rbf file can be generated from a .sof file by running the batch file sof_to_rbf.bat.
- This batch file is supplied by Terasic and is located in the examples folder.
- The batch call utility quarthps_cpf.exe is used to convert the .sof into .rbf.

## Test set up
3 GPIOS on the FPGA side and if they are triggerered, they trigger intterupts on the HPS side which in term trigger different blocks of logic in the code. Potentially 3 different led patterns.
