// Explicit technology mapping. E is active high; TE_B is active low.
module \$_TBUF_ (input A, E, output Y);
    sky130_fd_sc_hd__ebufn_1 buffer_cell (.A(A), .TE_B(~E), .Z(Y));
endmodule
