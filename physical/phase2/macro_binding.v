`default_nettype none
// Experimental physical binding. Fixed-delay phase logic must pass transistor
// simulation and routed checks; zero-delay GLS cannot qualify this sequence.
module sram_4x8_macro (
    input CLK,
    input [1:0] ADDR_Q,
    input [7:0] DIN_Q,
    input READ_Q, WRITE_Q,
    output [7:0] DOUT_RAW,
    inout VDD, VSS
);
    wire [80:0] delay_clk;
    wire valid_access, clk_released, precharge_set;
    wire pclk, prech, sclk, write_enable;
    wire [3:0] dec, row;
    wire [7:0] din_b;
    assign delay_clk[0] = CLK;
    genvar i;
    generate for (i=0; i<80; i=i+1) begin: phase_delay
        // Preserve physical delay cells: algebraic cancellation would destroy
        // the intended phase circuit even though Boolean behavior is equal.
        (* keep = 1, dont_touch = 1 *)
        sky130_fd_sc_hd__inv_1 delay_cell (.A(delay_clk[i]), .Y(delay_clk[i+1]));
    end endgenerate
    sky130_fd_sc_hd__or2_1 access_valid (.A(READ_Q), .B(WRITE_Q), .X(valid_access));
    sky130_fd_sc_hd__and2_1 release_phase (.A(CLK), .B(delay_clk[24]), .X(clk_released));
    sky130_fd_sc_hd__or2_1 precharge_phase (.A(clk_released), .B(delay_clk[80]), .X(precharge_set));
    sky130_fd_sc_hd__and3_2 evaluation (.A(valid_access), .B(CLK), .C(delay_clk[60]), .X(pclk));
    sky130_fd_sc_hd__and2_4 precharge_drive (.A(valid_access), .B(precharge_set), .X(prech));
    sky130_fd_sc_hd__and2_4 sense_drive (.A(READ_Q), .B(delay_clk[80]), .X(sclk));
    // The first pilot measured WE rising before PRECH had released. Tap 40
    // leaves a guard after tap-24 release and still leads tap-60 evaluation.
    sky130_fd_sc_hd__and3_4 write_drive (.A(WRITE_Q), .B(CLK), .C(delay_clk[40]), .X(write_enable));
    generate for (i=0; i<4; i=i+1) begin: qualify_row
        sky130_fd_sc_hd__and2_1 qualify (.A(dec[i]), .B(pclk), .X(row[i]));
    end endgenerate
    generate for (i=0; i<8; i=i+1) begin: data_complement
        sky130_fd_sc_hd__inv_1 complement (.A(DIN_Q[i]), .Y(din_b[i]));
    end endgenerate
    leaf_fabric array_and_peripherals (
        .VDD(VDD), .VSS(VSS), .A0(ADDR_Q[0]), .A1(ADDR_Q[1]),
        .PCLK(pclk), .PRECH(prech), .SCLK(sclk), .WE(write_enable),
        .DIN0(DIN_Q[0]), .DIN1(DIN_Q[1]), .DIN2(DIN_Q[2]), .DIN3(DIN_Q[3]),
        .DIN4(DIN_Q[4]), .DIN5(DIN_Q[5]), .DIN6(DIN_Q[6]), .DIN7(DIN_Q[7]),
        .DIN_B0(din_b[0]), .DIN_B1(din_b[1]), .DIN_B2(din_b[2]), .DIN_B3(din_b[3]),
        .DIN_B4(din_b[4]), .DIN_B5(din_b[5]), .DIN_B6(din_b[6]), .DIN_B7(din_b[7]),
        .DOUT0(DOUT_RAW[0]), .DOUT1(DOUT_RAW[1]), .DOUT2(DOUT_RAW[2]), .DOUT3(DOUT_RAW[3]),
        .DOUT4(DOUT_RAW[4]), .DOUT5(DOUT_RAW[5]), .DOUT6(DOUT_RAW[6]), .DOUT7(DOUT_RAW[7]),
        .ROW0(row[0]), .ROW1(row[1]), .ROW2(row[2]), .ROW3(row[3]),
        .DEC0(dec[0]), .DEC1(dec[1]), .DEC2(dec[2]), .DEC3(dec[3])
    );
endmodule

(* blackbox *)
module leaf_fabric (
    inout VDD, VSS,
    input A0, A1, PCLK, PRECH, SCLK, WE,
    input DIN0, DIN1, DIN2, DIN3, DIN4, DIN5, DIN6, DIN7,
    input DIN_B0, DIN_B1, DIN_B2, DIN_B3, DIN_B4, DIN_B5, DIN_B6, DIN_B7,
    output DOUT0, DOUT1, DOUT2, DOUT3, DOUT4, DOUT5, DOUT6, DOUT7,
    input ROW0, ROW1, ROW2, ROW3,
    output DEC0, DEC1, DEC2, DEC3
);
endmodule
`default_nettype wire
