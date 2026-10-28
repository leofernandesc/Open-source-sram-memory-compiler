// sch_path: /work/cells/control/row_address_capture.sch
module row_address_capture
(
  output wire A0_Q,
  output wire A1_Q,
  inout wire VDD,
  inout wire VSS,
  input wire CLK,
  input wire A0,
  input wire A1
);
sky130_fd_sc_hd__dfxtp_1
XA0_FF (
 .CLK( CLK ),
 .D( A0 ),
 .Q( A0_Q )
);


sky130_fd_sc_hd__dfxtp_1
XA1_FF (
 .CLK( CLK ),
 .D( A1 ),
 .Q( A1_Q )
);

endmodule
