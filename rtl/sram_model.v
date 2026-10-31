`timescale 1ns/1ps
`default_nettype none

// Functional SRAM view. Supply pins do not model analog power behavior.
module sram_model #(parameter integer DEPTH = 4) (
    input wire CLK,
    input wire [$clog2(DEPTH)-1:0] ADDR,
    inout wire [7:0] DATA,
    input wire CSb, OEb, WEb,
    inout wire VDD, VSS
);
    reg [7:0] mem [0:DEPTH-1];
    reg [$clog2(DEPTH)-1:0] address_q;
    reg [7:0] write_data_q, read_data_q;
    reg read_q, write_q;
    wire live_read = !CSb && !OEb && WEb;

    generate
        if (DEPTH != 4 && DEPTH != 8 && DEPTH != 16 && DEPTH != 32) begin : invalid_depth
            initial $fatal(1, "Unsupported SRAM depth: %0d", DEPTH);
        end
    endgenerate

    always @(posedge CLK) begin
        address_q <= ADDR;
        read_q <= !CSb && !OEb && WEb;
        write_q <= !CSb && OEb && !WEb;
        if (!CSb && OEb && !WEb)
            write_data_q <= DATA;
    end

    // This edge represents completion of the high-phase array access.
    always @(negedge CLK) begin
        if (write_q)
            mem[address_q] <= write_data_q;
        if (read_q)
            read_data_q <= mem[address_q];
    end

    assign DATA = (read_q && live_read) ? read_data_q : 8'bz;
endmodule
`default_nettype wire
