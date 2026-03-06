module mips_pipeline (
    input clk,
    input rst,
    input [31:0] instruction,
    input [31:0] mem_data,
    output reg [31:0] alu_result,
    output reg [31:0] write_data,
    output reg mem_write,
    output reg mem_read,
    output reg reg_write,
    output reg zero_flag,
    output reg overflow_flag
);

    // Pipeline registers
    reg [31:0] IF_ID_instr;
    reg [31:0] ID_EX_reg1;
    reg [31:0] ID_EX_reg2;
    reg [5:0]  ID_EX_opcode;
    reg [31:0] EX_MEM_result;
    reg [31:0] MEM_WB_data;

    // Hazard signals (CDC risk area)
    reg        stall;
    reg        flush;
    reg [31:0] forwarded_a;
    reg [31:0] forwarded_b;

    // IF Stage
    always @(posedge clk or posedge rst) begin
        if (rst)
            IF_ID_instr <= 32'b0;
        else if (!stall)
            IF_ID_instr <= instruction;
    end

    // ID Stage
    always @(posedge clk) begin
        ID_EX_opcode <= IF_ID_instr[31:26];
        ID_EX_reg1   <= IF_ID_instr[25:21];
        ID_EX_reg2   <= IF_ID_instr[20:16];
    end

    // EX Stage - ALU
    always @(posedge clk) begin
        case (ID_EX_opcode)
            6'b000000: EX_MEM_result <= forwarded_a + forwarded_b;
            6'b000010: EX_MEM_result <= forwarded_a - forwarded_b;
            6'b000100: EX_MEM_result <= forwarded_a & forwarded_b;
            6'b000110: EX_MEM_result <= forwarded_a | forwarded_b;
            6'b001000: EX_MEM_result <= forwarded_a ^ forwarded_b;
            6'b001010: EX_MEM_result <= forwarded_a << 1;
            6'b001100: EX_MEM_result <= forwarded_a >> 1;
            6'b001110: EX_MEM_result <= forwarded_a * forwarded_b;
            default:   EX_MEM_result <= 32'b0;
        endcase
        zero_flag     <= (EX_MEM_result == 0);
        overflow_flag <= (EX_MEM_result > 32'hFFFF);
    end

    // MEM Stage
    always @(posedge clk) begin
        if (mem_write)
            write_data <= EX_MEM_result;
        if (mem_read)
            MEM_WB_data <= mem_data;
    end

    // WB Stage
    always @(posedge clk) begin
        if (reg_write)
            alu_result <= MEM_WB_data;
        else
            alu_result <= EX_MEM_result;
    end

    // Hazard Detection (high CDC risk)
    always @(posedge clk) begin
        if (flush) begin
            stall <= 0;
            forwarded_a <= 32'b0;
            forwarded_b <= 32'b0;
        end else begin
            forwarded_a <= ID_EX_reg1;
            forwarded_b <= ID_EX_reg2;
            stall <= (mem_read && (ID_EX_reg2 == IF_ID_instr[25:21]));
        end
    end

endmodule