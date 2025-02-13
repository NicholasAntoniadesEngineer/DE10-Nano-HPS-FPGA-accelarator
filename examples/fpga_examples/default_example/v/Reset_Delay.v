// Reset_Delay module generates a delayed reset signal
// Used to ensure system is stable before starting normal operation
module	Reset_Delay(iCLK,oRESET);
input		iCLK;          // Input clock signal
output reg	oRESET;        // Output reset signal (active high)
reg	[19:0]	Cont;          // 20-bit counter for delay generation

// This always block triggers on the rising edge of the input clock
always@(posedge iCLK)
begin
	// Check if counter hasn't reached maximum value (0xFFFFF)
	if(Cont!=20'hFFFFF)
	// The 'begin' and 'end' keywords are used here to group multiple sequential statements.
	// Without them, only the first statement would be conditionally executed.
	begin
		Cont	<=	Cont + 1;      // Increment counter
		oRESET	<=	1'b0;         // Keep reset active (low) while counting
	end
	else
		oRESET	<=	1'b1;        // Release reset when counter is done
	                            // With 50MHz clock, this creates ~21ms delay
end

endmodule