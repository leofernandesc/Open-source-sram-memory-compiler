`timescale 1ns/1ps
`default_nettype none

module tb_sram_4x8;
    parameter integer DEPTH = 4;
    localparam integer AW = $clog2(DEPTH);
    reg CLK = 0;
    reg [AW-1:0] ADDR = 0;
    reg CSb = 1, OEb = 1, WEb = 1;
    reg host_drive = 0;
    reg [7:0] host_data = 0;
    tri [7:0] DATA;
    supply1 VDD;
    supply0 VSS;
    assign DATA = host_drive ? host_data : 8'bz;

`ifdef TEST_WRAPPER
    sram_4x8_wrapper dut (.*);
`else
    sram_model #(.DEPTH(DEPTH)) dut (.*);
`endif
    sram_ref_model #(.DEPTH(DEPTH)) reference_model ();

    integer checks = 0, transactions = 0, random_ops = 2048;
    integer control_hits [0:7];
    integer read_hits [0:DEPTH-1];
    integer write_hits [0:DEPTH-1];
    integer transition_hits [0:7][0:7];
    integer previous_operation = 7;
    reg previous_read = 1'bx;
    reg [7:0] last_read = 8'bx;
    reg [31:0] seed = 32'h5a17, rng_state, random_word;
    reg sampled_read;
    reg [7:0] sampled_result;
    integer a, b, op, next_op, p, i, hit_transitions;
    reg [7:0] pattern;
    string vcd_path;

    task automatic expect_bus(input reg [7:0] expected, input string stage);
        checks = checks + 1;
        if (DATA !== expected)
            $fatal(1, "%s transaction=%0d controls=%b address=%0d DATA=%h expected=%h",
                   stage, transactions, {CSb, OEb, WEb}, ADDR, DATA, expected);
    endtask

    task automatic expect_current(input reg captured_read, input string stage);
        if (host_drive) expect_bus(host_data, stage);
        else if ({CSb, OEb, WEb} == 3'b001) begin
            case (captured_read)
                1'b1: expect_bus(last_read, stage);
                1'b0: expect_bus(8'bz, stage);
                default: expect_bus(8'bx, stage);
            endcase
        end
        else expect_bus(8'bz, stage);
    endtask

    function automatic [31:0] next_random;
        rng_state = rng_state * 32'd1664525 + 32'd1013904223;
        next_random = rng_state;
    endfunction

    // Manual edges avoid sampling races. Delays are TB scheduling only.
    task automatic transaction(
        input reg [2:0] operation,
        input integer address,
        input reg [7:0] payload,
        input integer disturbance
    );
        host_drive = 0;
        {CSb, OEb, WEb} = operation;
        ADDR = address;
        #1;
        expect_current(previous_read, "low/setup/bus-release");
        host_data = payload;
        host_drive = (operation == 3'b010);
        #1;
        expect_current(previous_read, "write-data-setup");
        CLK = 1;
        #1;
        expect_current(operation == 3'b001, "rising/old-result");

        case (disturbance)
            1: begin
                ADDR = (address + 1) % DEPTH;
                host_data = ~payload;
            end
            2: begin
                {CSb, OEb, WEb} = 3'b111;
                host_drive = 0;
            end
            3: begin
                // A live request must not replace the captured request.
                host_drive = 0;
                {CSb, OEb, WEb} = (operation == 3'b010) ? 3'b001 : 3'b010;
                #1;
                expect_current(operation == 3'b001, "live-control-release");
                if (operation != 3'b010) begin
                    host_data = ~payload;
                    host_drive = 1;
                end
            end
            default: begin end
        endcase
        #1;
        expect_current(operation == 3'b001, "high/inputs-changed");
        reference_model.complete_transaction(operation, address, payload,
                                             sampled_read, sampled_result);
        if (sampled_read) last_read = sampled_result;
        CLK = 0;
        #1;
        expect_current(operation == 3'b001, "falling/result");
        host_drive = 0;
        {CSb, OEb, WEb} = operation;
        #1;
        expect_current(operation == 3'b001, "restored-controls/result");
        previous_read = sampled_read;
        control_hits[operation] = control_hits[operation] + 1;
        transition_hits[previous_operation][operation] =
            transition_hits[previous_operation][operation] + 1;
        previous_operation = operation;
        if (operation == 3'b001) read_hits[address] = read_hits[address] + 1;
        if (operation == 3'b010) write_hits[address] = write_hits[address] + 1;
        transactions = transactions + 1;
    endtask

    initial begin
        if ($value$plusargs("seed=%d", seed)) begin end
        if ($value$plusargs("random_ops=%d", random_ops)) begin end
        rng_state = seed;
        for (a = 0; a < 8; a = a + 1) begin
            control_hits[a] = 0;
            for (b = 0; b < 8; b = b + 1) transition_hits[a][b] = 0;
        end
        for (a = 0; a < DEPTH; a = a + 1) begin
            read_hits[a] = 0;
            write_hits[a] = 0;
        end
        if ($value$plusargs("vcd=%s", vcd_path)) begin
            $dumpfile(vcd_path);
            $dumpvars(0, tb_sram_4x8);
        end
        #1;
        expect_bus(8'bz, "startup/disabled");
        // Every location is read before any write. Unknown is intentional.
        for (a = 0; a < DEPTH; a = a + 1) transaction(3'b001, a, 0, 0);
        // Write all unique words before reading: detect address aliasing.
        for (a = 0; a < DEPTH; a = a + 1)
            transaction(3'b010, a, 8'ha7 ^ (a * 13), 1);
        for (a = 0; a < DEPTH; a = a + 1) transaction(3'b001, a, 0, 1);
        for (p = 0; p < 20; p = p + 1) begin
            case (p)
                0: pattern = 8'h00;
                1: pattern = 8'hff;
                2: pattern = 8'haa;
                3: pattern = 8'h55;
                default: if (p < 12) pattern = 8'b1 << (p - 4);
                         else pattern = ~(8'b1 << (p - 12));
            endcase
            for (a = 0; a < DEPTH; a = a + 1) transaction(3'b010, a, pattern, p % 4);
            for (a = 0; a < DEPTH; a = a + 1) transaction(3'b001, a, 0, p % 4);
        end
        // Attempt inactive/invalid writes, then audit the entire memory.
        for (op = 0; op < 8; op = op + 1)
            if (op != 1 && op != 2)
                for (a = 0; a < DEPTH; a = a + 1) begin
                    transaction(op, a, 8'h3c, 3);
                    for (b = 0; b < DEPTH; b = b + 1) transaction(3'b001, b, 0, 0);
                end
        // Explicitly cover all 64 ordered control transitions.
        for (op = 0; op < 8; op = op + 1)
            for (next_op = 0; next_op < 8; next_op = next_op + 1) begin
                transaction(op, op % DEPTH, 8'h96, 0);
                transaction(next_op, next_op % DEPTH, 8'h69, 0);
            end
        // Read-to-read selection across every ordered pair of addresses.
        for (a = 0; a < DEPTH; a = a + 1)
            for (b = 0; b < DEPTH; b = b + 1) begin
                transaction(3'b001, a, 0, 0);
                transaction(3'b001, b, 0, 0);
            end
        for (i = 0; i < random_ops; i = i + 1) begin
            random_word = next_random();
            transaction((random_word >> 25) & 7, (random_word >> 8) % DEPTH,
                        random_word >> 16, (random_word >> 29) % 4);
        end
        // Final full readback detects corruption in the last random operations.
        for (a = 0; a < DEPTH; a = a + 1) transaction(3'b001, a, 0, 0);
        hit_transitions = 0;
        for (a = 0; a < 8; a = a + 1) begin
            if (control_hits[a] == 0) $fatal(1, "Missing control coverage %0d", a);
            for (b = 0; b < 8; b = b + 1)
                if (transition_hits[a][b] > 0) hit_transitions = hit_transitions + 1;
        end
        if (hit_transitions != 64) $fatal(1, "Incomplete transition coverage");
        for (a = 0; a < DEPTH; a = a + 1)
            if (read_hits[a] == 0 || write_hits[a] == 0)
                $fatal(1, "Missing address coverage %0d", a);
        $write("RESULT {\"depth\":%0d,\"seed\":%0d,\"random_ops\":%0d,\"transactions\":%0d,\"checks\":%0d,\"control_transitions\":%0d,\"controls\":[",
               DEPTH, seed, random_ops, transactions, checks, hit_transitions);
        for (a = 0; a < 8; a = a + 1) $write("%s%0d", a ? "," : "", control_hits[a]);
        $write("],\"read_addresses\":[");
        for (a = 0; a < DEPTH; a = a + 1) $write("%s%0d", a ? "," : "", read_hits[a]);
        $write("],\"write_addresses\":[");
        for (a = 0; a < DEPTH; a = a + 1) $write("%s%0d", a ? "," : "", write_hits[a]);
        $display("]}");
        $display("PASS SRAM transaction regression");
        $finish;
    end

    initial begin
        #1000000;
        $fatal(1, "Testbench watchdog");
    end
endmodule
`default_nettype wire
