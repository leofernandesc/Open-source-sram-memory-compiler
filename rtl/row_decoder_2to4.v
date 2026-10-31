`timescale 1ns/1ps
`default_nettype none

// Logical verification view, not a replacement for the 33-MOS dynamic cell.
module row_decoder_2to4 (
    input wire [1:0] ADDR_Q,
    input wire EVAL_EN,
    output wire [3:0] DEC
);
    assign DEC = EVAL_EN ? (4'b0001 << ADDR_Q) : 4'b0000;
endmodule
`default_nettype wire
