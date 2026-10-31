`timescale 1ns/1ps
`default_nettype none

module sram_4x8_wrapper (
    input wire CLK,
    input wire [1:0] ADDR,
    inout wire [7:0] DATA,
    input wire CSb, OEb, WEb,
    inout wire VDD, VSS
);
    wire [1:0] address_q;
    wire [7:0] write_data_q, raw_read_data;
    wire read_q, write_q;
    reg [7:0] read_data_q;
    wire live_read = !CSb && !OEb && WEb;

    sram_controller control (
        .CLK(CLK), .ADDR(ADDR), .DIN(DATA),
        .CSb(CSb), .OEb(OEb), .WEb(WEb),
        .ADDR_Q(address_q), .DIN_Q(write_data_q),
        .READ_Q(read_q), .WRITE_Q(write_q)
    );
    sram_4x8_macro macro_core (
        .CLK(CLK), .ADDR_Q(address_q), .DIN_Q(write_data_q),
        .READ_Q(read_q), .WRITE_Q(write_q), .DOUT_RAW(raw_read_data),
        .VDD(VDD), .VSS(VSS)
    );
    always @(negedge CLK) begin
        if (read_q)
            read_data_q <= raw_read_data;
    end
    assign DATA = (read_q && live_read) ? read_data_q : 8'bz;
endmodule
`default_nettype wire
