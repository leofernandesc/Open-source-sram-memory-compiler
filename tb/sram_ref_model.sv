`timescale 1ns/1ps
`default_nettype none

// Transaction-level scoreboard: no DUT hierarchy or RTL helper is reused.
module sram_ref_model #(parameter integer DEPTH = 4);
    reg [7:0] expected [0:DEPTH-1];
    bit written [0:DEPTH-1];

    task automatic complete_transaction(
        input reg [2:0] operation,
        input integer address,
        input reg [7:0] payload,
        output reg is_read,
        output reg [7:0] result
    );
        is_read = 0;
        result = 8'bx;
        case (operation)
            3'b001: begin
                is_read = 1;
                if (written[address]) result = expected[address];
            end
            3'b010: begin
                expected[address] = payload;
                written[address] = 1;
            end
            default: begin end
        endcase
    endtask
endmodule
`default_nettype wire
