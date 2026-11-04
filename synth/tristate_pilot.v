`default_nettype none
module tristate_pilot(input A, EN, inout DATA, VDD, VSS);
    assign DATA = EN ? A : 1'bz;
endmodule
`default_nettype wire
