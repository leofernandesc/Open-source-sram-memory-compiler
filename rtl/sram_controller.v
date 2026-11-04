`timescale 1ns/1ps
`default_nettype none

module sram_controller (
    input wire CLK,
    input wire [1:0] ADDR,
    input wire [7:0] DIN,
    input wire CSb, OEb, WEb,
    output reg [1:0] ADDR_Q,
    output reg [7:0] DIN_Q,
    output reg READ_Q, WRITE_Q
);
    always @(posedge CLK) begin
        ADDR_Q <= ADDR;
        READ_Q <= !CSb && !OEb && WEb;
        WRITE_Q <= !CSb && OEb && !WEb;
        if (!CSb && OEb && !WEb)
            DIN_Q <= DIN;
    end
endmodule
`default_nettype wire
