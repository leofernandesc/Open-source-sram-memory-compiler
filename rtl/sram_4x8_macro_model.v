`timescale 1ns/1ps
`default_nettype none

// Simulation substitute for the custom array/peripherals. Not synthesizable IP.
module sram_4x8_macro (
    input wire CLK,
    input wire [1:0] ADDR_Q,
    input wire [7:0] DIN_Q,
    input wire READ_Q, WRITE_Q,
    output wire [7:0] DOUT_RAW,
    inout wire VDD, VSS
);
    reg [7:0] storage [0:3];
    assign DOUT_RAW = storage[ADDR_Q];
    always @(negedge CLK) begin
        if (WRITE_Q)
            storage[ADDR_Q] <= DIN_Q;
    end
endmodule
`default_nettype wire
