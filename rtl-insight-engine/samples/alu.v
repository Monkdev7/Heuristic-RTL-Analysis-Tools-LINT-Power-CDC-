module alu (
    input clk,
    input rst,
    input [15:0] a,
    input [15:0] b,
    input [2:0]  opcode,
    output reg [15:0] result,
    output reg zero
);

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            result <= 0;
            zero   <= 0;
        end else begin
            case (opcode)
                3'b000: result <= a + b;
                3'b001: result <= a - b;
                3'b010: result <= a & b;
                3'b011: result <= a | b;
                3'b100: result <= a ^ b;
                3'b101: result <= a >> 1;
                3'b110: result <= a << 1;
                default: result <= 16'b0;
            endcase
            zero <= (result == 0) ? 1 : 0;
        end
    end

endmodule