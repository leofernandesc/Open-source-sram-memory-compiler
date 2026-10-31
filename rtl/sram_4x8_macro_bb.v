`timescale 1ns/1ps
`default_nettype none

// Future synthesis boundary; the transistor-level implementation is not bound yet.
(* blackbox *)
module sram_4x8_macro (
    input wire CLK,
    input wire [1:0] ADDR_Q,
    input wire [7:0] DIN_Q,
    input wire READ_Q, WRITE_Q,
    output wire [7:0] DOUT_RAW,
    inout wire VDD, VSS
);
endmodule
`default_nettype wire
