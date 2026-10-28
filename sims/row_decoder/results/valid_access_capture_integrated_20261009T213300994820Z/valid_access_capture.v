// sch_path: /work/cells/control/valid_access_capture.sch
module valid_access_capture
(
  output wire VALID_ACCESS_Q,
  inout wire VDD,
  inout wire VSS,
  input wire CSb,
  input wire OEb,
  input wire WEb,
  input wire CLK
);
wire net1 ;
wire net2 ;
wire net3 ;

sky130_fd_sc_hd__inv_1
XCSB_INV (
 .A( CSb ),
 .Y( net1 )
);


sky130_fd_sc_hd__xor2_1
XOE_WE_XOR (
 .A( OEb ),
 .B( WEb ),
 .X( net2 )
);


sky130_fd_sc_hd__and2_1
XVALID_AND (
 .A( net1 ),
 .B( net2 ),
 .X( net3 )
);


sky130_fd_sc_hd__dfxtp_1
XVALID_FF (
 .CLK( CLK ),
 .D( net3 ),
 .Q( VALID_ACCESS_Q )
);

endmodule
