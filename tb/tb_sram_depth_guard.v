`timescale 1ns/1ps
module tb_sram_depth_guard;
    parameter integer DEPTH = 5;
    wire [7:0] DATA;
    wire VDD, VSS;
    wire [$clog2(DEPTH)-1:0] ADDR = 0;
    sram_model #(.DEPTH(DEPTH)) dut (
        .CLK(1'b0), .ADDR(ADDR), .DATA(DATA),
        .CSb(1'b1), .OEb(1'b1), .WEb(1'b1), .VDD(VDD), .VSS(VSS)
    );
    initial begin
        #1;
        $fatal(1, "Unsupported depth was not rejected");
    end
endmodule
