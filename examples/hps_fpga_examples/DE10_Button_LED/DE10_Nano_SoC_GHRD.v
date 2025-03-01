module DE10_Nano_SoC_GHRD (
    input CLOCK_50,          // PIN_V11
    input [1:0] KEY,         // KEY0: PIN_AH17, KEY1: PIN_AH16 (active low)
    output [3:0] LED         // LED0: PIN_AG17, LED1-3: PIN_AF17, AE17, AD17
);

    wire button_in;
    wire led_out;
    wire hps_reset;
    wire pio_button_rst;
    wire pio_led_rst;

    de10_nano_system u0 (
        .clk_clk(CLOCK_50),
        .reset_reset_n(1'b1),                   // Tie high for simplicity
        .pio_button_external_connection_export(button_in),
        .pio_led_external_connection_export(led_out),
        .hps_0_h2f_reset(hps_reset),
        .pio_button_reset(pio_button_rst),
        .pio_led_reset(pio_led_rst)
        // Other HPS ports omitted for simplicity
    );

    assign button_in = ~KEY[0];  // Invert KEY0 (active low) for logic 1 when pressed
    assign LED[0] = led_out;
    assign LED[3:1] = 3'b000;    // Keep other LEDs off

endmodule