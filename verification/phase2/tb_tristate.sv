`timescale 1ns/1ps
module tb_tristate;
    reg A = 0, EN = 0, host_en = 0, host_data = 0;
    tri DATA;
    supply1 VDD;
    supply0 VSS;
    assign DATA = host_en ? host_data : 1'bz;
    tristate_pilot dut(.*);
    integer checks = 0;
    task check(input logic expected);
        #1;
        checks++;
        if (DATA !== expected) $fatal(1, "tri-state DATA=%b expected=%b", DATA, expected);
    endtask
    initial begin
        check(1'bz);
        EN = 1; check(0);
        A = 1; check(1);
        EN = 0; check(1'bz);
        host_en = 1; host_data = 0; check(0);
        host_data = 1; check(1);
        host_en = 0; check(1'bz);
        A = 0; check(1'bz);
        $display("TRISTATE_RESULT checks=%0d", checks);
        $finish;
    end
    initial begin #100; $fatal(1, "tri-state watchdog"); end
endmodule
