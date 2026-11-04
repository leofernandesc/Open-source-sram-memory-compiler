`timescale 1ns/1ps
`default_nettype none
// GLS-only substitute. The production physical flow uses the frozen 401-MOS
// fabric, never this storage array. No initialized state is introduced.
module leaf_fabric(
    inout VDD,VSS,
    input A0,A1,PCLK,PRECH,SCLK,WE,
    input DIN0,DIN1,DIN2,DIN3,DIN4,DIN5,DIN6,DIN7,
    input DIN_B0,DIN_B1,DIN_B2,DIN_B3,DIN_B4,DIN_B5,DIN_B6,DIN_B7,
    output DOUT0,DOUT1,DOUT2,DOUT3,DOUT4,DOUT5,DOUT6,DOUT7,
    input ROW0,ROW1,ROW2,ROW3,
    output DEC0,DEC1,DEC2,DEC3
);
    reg [7:0] word0,word1,word2,word3;
    reg [7:0] sensed_word;
    wire [7:0] input_word={DIN7,DIN6,DIN5,DIN4,DIN3,DIN2,DIN1,DIN0};
    assign DEC0=PCLK && {A1,A0}==2'b00;
    assign DEC1=PCLK && {A1,A0}==2'b01;
    assign DEC2=PCLK && {A1,A0}==2'b10;
    assign DEC3=PCLK && {A1,A0}==2'b11;
    // Transparent high-phase write is a functional completion model. It does
    // not characterize the 6T write margin or the physical bitline waveform.
    always @* if(WE && ROW0) word0 <= input_word;
    always @* if(WE && ROW1) word1 <= input_word;
    always @* if(WE && ROW2) word2 <= input_word;
    always @* if(WE && ROW3) word3 <= input_word;
    // The regenerative sense result survives WL release through output
    // capture. Only the transistor campaign proves its real setup/hold.
    always @(posedge SCLK) begin
        case ({ROW3,ROW2,ROW1,ROW0})
            4'b0001: sensed_word <= word0;
            4'b0010: sensed_word <= word1;
            4'b0100: sensed_word <= word2;
            4'b1000: sensed_word <= word3;
            default: sensed_word <= 8'bx;
        endcase
    end
    assign {DOUT7,DOUT6,DOUT5,DOUT4,DOUT3,DOUT2,DOUT1,DOUT0}=sensed_word;
endmodule
`default_nettype wire
