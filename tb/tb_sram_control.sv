`timescale 1ns/1ps
`default_nettype none
module tb_sram_control;
    reg CLK = 0;
    reg [1:0] ADDR = 0;
    reg [7:0] DIN = 0;
    reg CSb = 1, OEb = 1, WEb = 1;
    wire [1:0] ADDR_Q;
    wire [7:0] DIN_Q;
    wire READ_Q, WRITE_Q;
    wire [3:0] DEC;
    wire EVAL_EN = CLK && (READ_Q || WRITE_Q);
    reg [3:0] expected;
    reg [7:0] previous_din = 8'bx;
    integer op, a, checks = 0;
    sram_controller dut (.*);
    row_decoder_2to4 decoder (.*);
    task automatic check_state(input bit high_phase);
        expected = 0;
        if (high_phase && (op == 1 || op == 2)) expected[a] = 1;
        checks = checks + 1;
        if (ADDR_Q !== a[1:0] || READ_Q !== (op == 1) ||
            WRITE_Q !== (op == 2) || DIN_Q !== previous_din || DEC !== expected)
            $fatal(1, "Control/one-hot mismatch operation=%0d address=%0d DEC=%b", op, a, DEC);
    endtask
    initial begin
        for (op = 0; op < 8; op = op + 1)
            for (a = 0; a < 4; a = a + 1) begin
                {CSb, OEb, WEb} = op;
                ADDR = a;
                DIN = 8'h96 ^ a;
                #1;
                CLK = 1;
                if (op == 2) previous_din = DIN;
                #1; check_state(1);
                ADDR = ~ADDR;
                DIN = ~DIN;
                {CSb, OEb, WEb} = ~op;
                #1; check_state(1);
                CLK = 0;
                #1; check_state(0);
            end
        $display("CONTROL_RESULT {\"checks\":%0d,\"controls\":8,\"addresses\":4}", checks);
        $display("PASS controller and logical one-hot decoder");
        $finish;
    end
endmodule
`default_nettype wire
