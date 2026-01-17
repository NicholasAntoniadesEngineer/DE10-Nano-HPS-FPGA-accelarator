/*
 * HPS-FPGA LED Control Demo
 * 
 * This program demonstrates communication between the Hard Processor System (HPS)
 * and FPGA fabric through the Lightweight AXI Bridge on the DE10-Nano SoC.
 * 
 * The program controls LEDs connected to the FPGA fabric by writing to memory-mapped
 * registers. This demonstrates the basic principle of HPS-FPGA communication where
 * the HPS can control FPGA resources through memory-mapped I/O.
 *
 * Prerequisites:
 * - FPGA must be programmed with the GHRD (Golden Hardware Reference Design)
 * - Requires root access to access /dev/mem for memory mapping
 */

#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include "hwlib.h"               // Hardware abstraction library for Cyclone V SoC
#include "socal/socal.h"         // SoC abstraction layer
#include "socal/hps.h"           // HPS peripheral definitions
#include "socal/alt_gpio.h"      // GPIO definitions
#include "hps_0.h"               // Generated header containing peripheral base addresses

// Define the physical memory region we want to access
// These addresses are specific to the Cyclone V SoC architecture
#define HW_REGS_BASE ( ALT_STM_OFST )     // Base address of lightweight bridge
#define HW_REGS_SPAN ( 0x04000000 )       // Span of memory region (64MB)
#define HW_REGS_MASK ( HW_REGS_SPAN - 1 ) // Mask for address calculations

int main() {

	// Pointers and variables for memory mapping
	void *virtual_base;          // Base address of mapped memory
	int fd;                      // File descriptor for /dev/mem
	int loop_count;              // Counter for LED animation loops
	int led_direction;           // Direction of LED movement (0: left, 1: right)
	int led_mask;               // Bit mask for current LED position
	void *h2p_lw_led_addr;      // Address of LED control register

	// Open /dev/mem to get access to physical addresses
	// This requires root privileges
	if( ( fd = open( "/dev/mem", ( O_RDWR | O_SYNC ) ) ) == -1 ) {
		printf( "ERROR: could not open \"/dev/mem\"...\n" );
		return( 1 );
	}

	// Map physical memory into virtual address space
	// This creates a user-space mapping to the physical memory addresses
	virtual_base = mmap( NULL, HW_REGS_SPAN, ( PROT_READ | PROT_WRITE ), MAP_SHARED, fd, HW_REGS_BASE );

	if( virtual_base == MAP_FAILED ) {
		printf( "ERROR: mmap() failed...\n" );
		close( fd );
		return( 1 );
	}
	
	// Calculate the virtual address of the LED PIO (Parallel I/O) controller
	// This translates the physical address of the LED controller to a virtual address
	h2p_lw_led_addr=virtual_base + ( ( unsigned long  )( ALT_LWFPGASLVS_OFST + LED_PIO_BASE ) & ( unsigned long)( HW_REGS_MASK ) );

	// LED animation loop
	loop_count = 0;
	led_mask = 0x01;            // Start with rightmost LED
	led_direction = 0;          // Start moving left to right

	// Run the animation for 60 cycles
	while( loop_count < 60 ) {
		
		// Write to the LED controller
		// The ~ operator inverts the mask because the LEDs are active-low
		*(uint32_t *)h2p_lw_led_addr = ~led_mask; 

		// Delay for visual effect
		usleep( 100*1000 );  // 100ms delay
		
		// Update LED position based on direction
		if (led_direction == 0){
			led_mask <<= 1;  // Shift left (move right)
			// Change direction when reaching leftmost LED
			if (led_mask == (0x01 << (LED_PIO_DATA_WIDTH-1)))
				 led_direction = 1;
		}else{
			led_mask >>= 1;  // Shift right (move left)
			// Change direction and increment counter when reaching rightmost LED
			if (led_mask == 0x01){ 
				led_direction = 0;
				loop_count++;
			}
		}
	}

	// Cleanup: Unmap memory and close file descriptor
	if( munmap( virtual_base, HW_REGS_SPAN ) != 0 ) {
		printf( "ERROR: munmap() failed...\n" );
		close( fd );
		return( 1 );
	}

	close( fd );
	return( 0 );
}
