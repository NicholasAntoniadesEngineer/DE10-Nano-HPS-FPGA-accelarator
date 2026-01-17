# ============================================================================
# Hardware Calculator IP - Platform Designer Component Definition
# ============================================================================
# TCL script for Platform Designer (QSys) component integration
# Defines interfaces, parameters, and files for calculator IP
# ============================================================================

package require -exact qsys 16.0

# ============================================================================
# Module Properties
# ============================================================================
set_module_property DESCRIPTION "Hardware-accelerated floating-point calculator with HFT operations and LED display"
set_module_property NAME calculator
set_module_property VERSION 1.1
set_module_property INTERNAL false
set_module_property OPAQUE_ADDRESS_MAP true
set_module_property AUTHOR "Claude Code"
set_module_property DISPLAY_NAME "Hardware Calculator"
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
set_module_property EDITABLE true
set_module_property REPORT_TO_TALKBACK false
set_module_property ALLOW_GREYBOX_GENERATION false
set_module_property REPORT_HIERARCHY false

# ============================================================================
# File Sets
# ============================================================================
add_fileset QUARTUS_SYNTH QUARTUS_SYNTH "" ""
set_fileset_property QUARTUS_SYNTH TOP_LEVEL calculator
set_fileset_property QUARTUS_SYNTH ENABLE_RELATIVE_INCLUDE_PATHS false
set_fileset_property QUARTUS_SYNTH ENABLE_FILE_OVERWRITE_MODE false

add_fileset_file calculator.v                VERILOG PATH calculator.v TOP_LEVEL_FILE
add_fileset_file calculator_avalon_mm.v      VERILOG PATH calculator_avalon_mm.v
add_fileset_file calculator_registers.v      VERILOG PATH calculator_registers.v
add_fileset_file calculator_core.v           VERILOG PATH calculator_core.v
add_fileset_file calculator_float_ops.v      VERILOG PATH calculator_float_ops.v
add_fileset_file calculator_led_display.v    VERILOG PATH calculator_led_display.v
add_fileset_file calculator_price_buffer.v   VERILOG PATH calculator_price_buffer.v
add_fileset_file calculator_hft_ops.v        VERILOG PATH calculator_hft_ops.v

# ============================================================================
# Parameters
# ============================================================================
# Currently no user-configurable parameters
# Future: Add parameters for pipeline depth, precision, etc.

# ============================================================================
# Clock and Reset Interface
# ============================================================================
add_interface clock clock end
set_interface_property clock clockRate 0
set_interface_property clock ENABLED true
set_interface_property clock EXPORT_OF ""
set_interface_property clock PORT_NAME_MAP ""
set_interface_property clock CMSIS_SVD_VARIABLES ""
set_interface_property clock SVD_ADDRESS_GROUP ""

add_interface_port clock clk clk Input 1

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
set_interface_property s0 readLatency 0
set_interface_property s0 readWaitTime 1
set_interface_property s0 setupTime 0
set_interface_property s0 timingUnits Cycles
set_interface_property s0 writeWaitTime 0
set_interface_property s0 ENABLED true
set_interface_property s0 EXPORT_OF ""
set_interface_property s0 PORT_NAME_MAP ""
set_interface_property s0 CMSIS_SVD_VARIABLES ""
set_interface_property s0 SVD_ADDRESS_GROUP ""

add_interface_port s0 avs_s0_address address Input 6
add_interface_port s0 avs_s0_read read Input 1
add_interface_port s0 avs_s0_write write Input 1
add_interface_port s0 avs_s0_writedata writedata Input 32
add_interface_port s0 avs_s0_readdata readdata Output 32
add_interface_port s0 avs_s0_waitrequest waitrequest Output 1

set_interface_assignment s0 embeddedsw.configuration.isFlash 0
set_interface_assignment s0 embeddedsw.configuration.isMemoryDevice 0
set_interface_assignment s0 embeddedsw.configuration.isNonVolatileStorage 0
set_interface_assignment s0 embeddedsw.configuration.isPrintableDevice 0

# Memory map - 16 registers x 4 bytes = 64 bytes total (extended for HFT)
set_module_assignment embeddedsw.CMacro.SIZE 64
set_module_assignment embeddedsw.CMacro.CONTROL 0x00
set_module_assignment embeddedsw.CMacro.OPERAND_A 0x04
set_module_assignment embeddedsw.CMacro.OPERAND_B 0x08
set_module_assignment embeddedsw.CMacro.RESULT 0x0C
set_module_assignment embeddedsw.CMacro.STATUS 0x10
set_module_assignment embeddedsw.CMacro.INT_ENABLE 0x14
set_module_assignment embeddedsw.CMacro.BUFFER_CONTROL 0x18
set_module_assignment embeddedsw.CMacro.BUFFER_WRITE 0x1C
set_module_assignment embeddedsw.CMacro.BUFFER_COUNT 0x20
set_module_assignment embeddedsw.CMacro.EMA_ALPHA 0x24
set_module_assignment embeddedsw.CMacro.CONFIG_FLAGS 0x28
set_module_assignment embeddedsw.CMacro.ERROR_CODE 0x2C
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
# LED Output Conduit Interface
# ============================================================================
add_interface led_output conduit end
set_interface_property led_output associatedClock clock
set_interface_property led_output associatedReset reset
set_interface_property led_output ENABLED true
set_interface_property led_output EXPORT_OF ""
set_interface_property led_output PORT_NAME_MAP ""
set_interface_property led_output CMSIS_SVD_VARIABLES ""
set_interface_property led_output SVD_ADDRESS_GROUP ""

add_interface_port led_output coe_led_output_export export Output 8
