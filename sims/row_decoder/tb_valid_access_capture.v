`timescale 1ns/1ps

module tb_valid_access_capture;
    reg CLK;
    reg CSb;
    reg OEb;
    reg WEb;
    supply1 VDD;
    supply0 VSS;
    wire VALID_ACCESS_Q;

    integer i;
    integer failures;
    integer vector_file;
    reg expected_valid;
    reg q_after_capture;
    reg q_while_high;
    reg q_after_fall;
    reg [2:0] controls;

    valid_access_capture dut (
        .CLK(CLK),
        .CSb(CSb),
        .OEb(OEb),
        .WEb(WEb),
        .VDD(VDD),
        .VSS(VSS),
        .VALID_ACCESS_Q(VALID_ACCESS_Q)
    );

    initial begin
        $dumpfile("capture.vcd");
        $dumpvars(0, tb_valid_access_capture);
        vector_file = $fopen("vectors.csv", "w");
        $fdisplay(vector_file,
            "control_vector,CSb,OEb,WEb,expected_valid_from_controls,VALID_ACCESS_Q_after_rise,VALID_ACCESS_Q_after_input_change,VALID_ACCESS_Q_after_fall");

        CLK = 1'b0;
        CSb = 1'b1;
        OEb = 1'b1;
        WEb = 1'b1;
        failures = 0;
        #1;

        // Cover all eight combinations. The Q state before the first rising
        // edge is intentionally not checked because the project has no reset.
        for (i = 0; i < 8; i = i + 1) begin
            CLK = 1'b0;
            controls = i[2:0];
            {CSb, OEb, WEb} = controls;
            #1;
            expected_valid = (~CSb) & (OEb ^ WEb);
            CLK = 1'b1;
            #1;
            q_after_capture = VALID_ACCESS_Q;
            if (q_after_capture !== expected_valid) begin
                $display("FAIL vector %03b: Q after rising edge=%b expected=%b",
                         controls, q_after_capture, expected_valid);
                failures = failures + 1;
            end

            // Change live controls while CLK remains high. The registered
            // qualifier must retain the value captured at the rising edge.
            {CSb, OEb, WEb} = ~controls;
            #1;
            q_while_high = VALID_ACCESS_Q;
            if (q_while_high !== q_after_capture) begin
                $display("FAIL vector %03b: Q followed live controls while CLK high",
                         controls);
                failures = failures + 1;
            end

            CLK = 1'b0;
            #1;
            q_after_fall = VALID_ACCESS_Q;
            if (q_after_fall !== q_after_capture) begin
                $display("FAIL vector %03b: Q changed on falling edge", controls);
                failures = failures + 1;
            end

            $fdisplay(vector_file, "%03b,%0b,%0b,%0b,%0b,%0b,%0b,%0b",
                      controls, controls[2], controls[1], controls[0],
                      expected_valid, q_after_capture, q_while_high,
                      q_after_fall);
        end

        $fclose(vector_file);
        if (failures == 0) begin
            $display("PASS: 8/8 control-vector captures and 16/16 hold checks");
            $finish;
        end
        $display("FAIL: %0d checks failed", failures);
        $fatal(1);
    end
endmodule
