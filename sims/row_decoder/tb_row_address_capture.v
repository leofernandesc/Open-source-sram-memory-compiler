`timescale 1ns/1ps

module tb_row_address_capture;
    reg CLK;
    reg A0;
    reg A1;
    supply1 VDD;
    supply0 VSS;
    wire A0_Q;
    wire A1_Q;

    integer address;
    integer failures;
    reg sampled_a0;
    reg sampled_a1;

    row_address_capture dut (
        .CLK(CLK),
        .A0(A0),
        .A1(A1),
        .VDD(VDD),
        .VSS(VSS),
        .A0_Q(A0_Q),
        .A1_Q(A1_Q)
    );

    initial begin
        $dumpfile("row_address_capture.vcd");
        $dumpvars(0, tb_row_address_capture);
        CLK = 1'b0;
        A0 = 1'b0;
        A1 = 1'b0;
        failures = 0;
        #1;

        // Cover every 2-bit row address at a rising edge, then disturb the
        // live address to verify the registered outputs hold their values.
        for (address = 0; address < 4; address = address + 1) begin
            CLK = 1'b0;
            A1 = address[1];
            A0 = address[0];
            #1;
            CLK = 1'b1;
            #1;
            sampled_a0 = A0_Q;
            sampled_a1 = A1_Q;
            if ({A1_Q, A0_Q} !== address[1:0]) begin
                $display("FAIL address %02b: Q=%02b", address[1:0],
                         {A1_Q, A0_Q});
                failures = failures + 1;
            end

            {A1, A0} = ~address[1:0];
            #1;
            if ({A1_Q, A0_Q} !== {sampled_a1, sampled_a0}) begin
                $display("FAIL address %02b: outputs followed live inputs while CLK high",
                         address[1:0]);
                failures = failures + 1;
            end

            CLK = 1'b0;
            #1;
            if ({A1_Q, A0_Q} !== {sampled_a1, sampled_a0}) begin
                $display("FAIL address %02b: outputs changed on falling edge",
                         address[1:0]);
                failures = failures + 1;
            end
        end

        if (failures == 0) begin
            $display("PASS: 4/4 row-address captures and 8/8 hold checks");
            $finish;
        end
        $display("FAIL: %0d checks failed", failures);
        $fatal(1);
    end
endmodule
