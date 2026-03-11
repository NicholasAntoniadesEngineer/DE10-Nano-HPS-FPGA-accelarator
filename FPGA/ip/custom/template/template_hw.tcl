# ============================================================================
# Custom IP - Platform Designer Component Definition (TEMPLATE)
# ============================================================================
# Rename this file to <yourip>_hw.tcl and update all references from
# "template_ip" to your IP name.
# The file MUST be named *_hw.tcl for QSys auto-discovery.
# ============================================================================

package require -exact qsys 16.0

# ============================================================================
# Module Properties
# ============================================================================
set_module_property DESCRIPTION "Custom IP template — replace with your description"
set_module_property NAME template_ip
set_module_property VERSION 1.0
set_module_property INTERNAL false
set_module_property OPAQUE_ADDRESS_MAP true
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
set_module_property EDITABLE true
set_module_property REPORT_TO_TALKBACK false
set_module_property ALLOW_GREYBOX_GENERATION false
set_module_property REPORT_HIERARCHY false

# ============================================================================
# File Sets — list ALL Verilog files; mark top-level
# ============================================================================
add_fileset QUARTUS_SYNTH QUARTUS_SYNTH "" ""
set_fileset_property QUARTUS_SYNTH TOP_LEVEL template_ip
set_fileset_property QUARTUS_SYNTH ENABLE_RELATIVE_INCLUDE_PATHS false
set_fileset_property QUARTUS_SYNTH ENABLE_FILE_OVERWRITE_MODE false

add_fileset_file template_ip.v              VERILOG PATH template_ip.v TOP_LEVEL_FILE
add_fileset_file template_avalon_mm.v       VERILOG PATH template_avalon_mm.v
add_fileset_file template_registers.v       VERILOG PATH template_registers.v
add_fileset_file template_core.v            VERILOG PATH template_core.v

# ============================================================================
# Clock Interface
# ============================================================================
add_interface clock clock end
set_interface_property clock clockRate 0
set_interface_property clock ENABLED true
set_interface_property clock EXPORT_OF ""
set_interface_property clock PORT_NAME_MAP ""
set_interface_property clock CMSIS_SVD_VARIABLES ""
set_interface_property clock SVD_ADDRESS_GROUP ""

add_interface_port clock clk clk Input 1

# ============================================================================
# Reset Interface
# ============================================================================
add_interface reset reset end
set_interface_property reset associatedClock clock
set_interface_property reset synchronousEdges DEASSERT
set_interface_property reset ENABLED true
set_interface_property reset EXPORT_OF ""
set_interface_property reset PORT_NAME_MAP ""
set_interface_property reset CMSIS_SVD_VARIABLES ""
set_interface_property reset SVD_ADDRESS_GROUP ""

add_interface_port reset reset_n reset_n Input 1

# ============================================================================
# Avalon-MM Slave Interface
# ============================================================================
add_interface s0 avalon end
set_interface_property s0 addressUnits WORDS
set_interface_property s0 associatedClock clock
set_interface_property s0 associatedReset reset
set_interface_property s0 bitsPerSymbol 8
set_interface_property s0 burstOnBurstBoundariesOnly false
set_interface_property s0 burstcountUnits WORDS
set_interface_property s0 explicitAddressSpan 0
set_interface_property s0 holdTime 0
set_interface_property s0 linewrapBursts false
set_interface_property s0 maximumPendingReadTransactions 0
set_interface_property s0 maximumPendingWriteTransactions 0
set_interface_property s0 readLatency 1
set_interface_property s0 readWaitTime 0
set_interface_property s0 setupTime 0
set_interface_property s0 timingUnits Cycles
set_interface_property s0 writeWaitTime 0
set_interface_property s0 ENABLED true
set_interface_property s0 EXPORT_OF ""
set_interface_property s0 PORT_NAME_MAP ""
set_interface_property s0 CMSIS_SVD_VARIABLES ""
set_interface_property s0 SVD_ADDRESS_GROUP ""

# Address width = 4 bits = 16 word registers = 64 bytes
add_interface_port s0 avs_s0_address address Input 4
add_interface_port s0 avs_s0_read read Input 1
add_interface_port s0 avs_s0_write write Input 1
add_interface_port s0 avs_s0_writedata writedata Input 32
add_interface_port s0 avs_s0_readdata readdata Output 32
add_interface_port s0 avs_s0_waitrequest waitrequest Output 1

set_interface_assignment s0 embeddedsw.configuration.isFlash 0
set_interface_assignment s0 embeddedsw.configuration.isMemoryDevice 0
set_interface_assignment s0 embeddedsw.configuration.isNonVolatileStorage 0
set_interface_assignment s0 embeddedsw.configuration.isPrintableDevice 0

# Memory map — update offsets and size to match your register file
set_module_assignment embeddedsw.CMacro.SIZE 64
set_module_assignment embeddedsw.CMacro.CONTROL 0x00
set_module_assignment embeddedsw.CMacro.INPUT_A 0x04
set_module_assignment embeddedsw.CMacro.INPUT_B 0x08
set_module_assignment embeddedsw.CMacro.RESULT 0x0C
set_module_assignment embeddedsw.CMacro.STATUS 0x10
set_module_assignment embeddedsw.CMacro.INT_ENABLE 0x14
set_module_assignment embeddedsw.CMacro.VERSION 0x3C

# ============================================================================
# Interrupt Sender Interface
# ============================================================================
add_interface irq interrupt end
set_interface_property irq associatedAddressablePoint s0
set_interface_property irq associatedClock clock
set_interface_property irq associatedReset reset
set_interface_property irq bridgedReceiverOffset ""
set_interface_property irq bridgesToReceiver ""
set_interface_property irq ENABLED true
set_interface_property irq EXPORT_OF ""
set_interface_property irq PORT_NAME_MAP ""
set_interface_property irq CMSIS_SVD_VARIABLES ""
set_interface_property irq SVD_ADDRESS_GROUP ""

add_interface_port irq ins_irq_irq irq Output 1

# ============================================================================
# Conduit Export (OPTIONAL — uncomment and rename for GPIO/LED/etc.)
# If you enable a conduit, you MUST also wire it in hdl/DE10_NANO_SoC_GHRD.v.
# After QSys generation, check generated/soc_system/synthesis/soc_system.v
# for the exact port name. See ip/custom/README.md Step 4 for details.
# ============================================================================
# add_interface output_conduit conduit end
# set_interface_property output_conduit associatedClock clock
# set_interface_property output_conduit associatedReset reset
# set_interface_property output_conduit ENABLED true
# set_interface_property output_conduit EXPORT_OF ""
# set_interface_property output_conduit PORT_NAME_MAP ""
# set_interface_property output_conduit CMSIS_SVD_VARIABLES ""
# set_interface_property output_conduit SVD_ADDRESS_GROUP ""
#
# add_interface_port output_conduit coe_output_export export Output 8
