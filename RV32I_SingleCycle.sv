module ProgramCounter (
    input logic clk,
    input logic reset_n,
    input logic [31:0] pc_next,

    output logic [31:0] pc
);

always @(posedge clk) begin
    if (reset_n == 1'b0) begin
        pc <= 32'b0;
    end
    else begin
        pc <= pc_next;
    end
end

endmodule


module InstructionMemory #(parameter WORDS = 64) (
    input logic [31:0] address,

    output logic [31:0] instruction,
    output logic [4:0] part1,
    output logic [4:0] part2,
    output logic [4:0] part3

);

logic [31:0] memory [0:WORDS-1];

always_comb begin
    instruction = memory[address[7:2]];                         // Changed 31 to 7 due to compiler warning
    part1 = instruction[19:15];
    part2 = instruction[24:20];
    part3 = instruction[11:7];
end

endmodule


module ControlUnit (
    input logic [31:0] instruction,
    input logic zero,
    input logic alu_lsb,

    output logic PC_src,
    output logic [1:0] WB_src,
    output logic [3:0] ALU_ctrl,
    output logic ALU_src,
    output logic [1:0] Sec_add_src,
    output logic [2:0] Imm_src,
    output logic reg_write,
    output logic mem_write,
    output logic [2:0] funct3
);

logic [6:0] opcode;
assign opcode = instruction[6:0];
assign funct3 = instruction[14:12];
logic [6:0] funct7;
assign funct7 = instruction[31:25];


always_comb begin

    PC_src = 1'b0;
    WB_src = 2'b00;
    ALU_ctrl = 4'b0000;
    ALU_src = 1'b0;
    Sec_add_src = 2'b00;
    Imm_src = 3'b000;
    reg_write = 1'b0;
    mem_write = 1'b0;

    case (opcode)
        7'b0110011: begin
            case (funct3)
                3'b000 : begin
                    case (funct7)
                        7'b0 : begin // add
                            reg_write = 1'b1;
                        end
                        7'b0100000 : begin // subtract
                            ALU_ctrl = 4'b0001;
                            reg_write = 1'b1;
                        end
                        default : begin
                            // needed for compiler
                        end
                    endcase
                end
                3'b001 : begin // sll
                    ALU_ctrl = 4'b0101;
                    reg_write = 1'b1;
                end
                3'b010 : begin // slt
                    ALU_ctrl = 4'b1000;
                    reg_write = 1'b1;
                end
                3'b011 : begin // sltu
                    ALU_ctrl = 4'b1001;
                    reg_write = 1'b1;
                end
                3'b100 : begin // xor
                    ALU_ctrl = 4'b0100;
                    reg_write = 1'b1;
                end
                3'b101 : begin
                    case (funct7)
                        7'b0 : begin // srl
                            ALU_ctrl = 4'b0110;
                            reg_write = 1'b1;
                        end
                        7'b0100000 : begin // sra
                            ALU_ctrl = 4'b0111;
                            reg_write = 1'b1;
                        end
                        default : begin
                            // needed for compiler
                        end
                    endcase
                end
                3'b110 : begin // or
                    ALU_ctrl = 4'b0011;
                    reg_write = 1'b1;
                end
                3'b111 : begin // and
                    ALU_ctrl = 4'b0010;
                    reg_write = 1'b1;
                end
            endcase
        end
        7'b0010011: begin
            reg_write = 1'b1;
            ALU_src = 1'b1;
            case (funct3)
                3'b000 : begin // addi
                    // nothing to be done
                end
                3'b001 : begin // slli
                    ALU_ctrl = 4'b0101;
                end
                3'b010 : begin // slti
                    ALU_ctrl = 4'b1000;
                end
                3'b011 : begin // sltiu
                    ALU_ctrl = 4'b1001;
                end
                3'b100 : begin // xori
                    ALU_ctrl = 4'b0100;
                end
                3'b101 : begin
                    case (funct7)
                        7'b0 : begin // srli
                            ALU_ctrl = 4'b0110;
                        end
                        7'b0100000 : begin // srai
                            ALU_ctrl = 4'b0111;
                        end
                        default : begin
                            // needed for compiler
                        end
                    endcase
                end
                3'b110 : begin // ori
                    ALU_ctrl = 4'b0011;
                end
                3'b111 : begin // andi
                    ALU_ctrl = 4'b0010;
                end
            endcase
        end
        7'b0000011: begin
            reg_write = 1'b1;
            ALU_src = 1'b1;
            WB_src = 2'b01;
            Imm_src = 3'b000;
        end
        7'b0100011: begin
            mem_write = 1'b1;
            ALU_src = 1'b1;
            Imm_src = 3'b001;
        end
        7'b1100011: begin
            Imm_src = 3'b010;
            Sec_add_src = 2'b00;
            case (funct3)
                3'b000 : begin // beq
                    ALU_ctrl = 4'b0001;
                    PC_src = zero;
                end
                3'b001 : begin // bne
                    ALU_ctrl = 4'b0001;
                    PC_src = ~zero;
                end
                3'b100 : begin // blt
                    ALU_ctrl = 4'b1000;
                    PC_src = alu_lsb;
                end
                3'b101 : begin // bge
                    ALU_ctrl = 4'b1000;
                    PC_src = ~alu_lsb;
                end
                3'b110 : begin // bltu
                    ALU_ctrl = 4'b1001;
                    PC_src = alu_lsb;
                end
                3'b111 : begin // bgeu
                    ALU_ctrl = 4'b1001;
                    PC_src = ~alu_lsb;
                end
                default : begin
                    // needed for compiler
                end
            endcase
        end
        7'b1101111: begin // jal
            Imm_src = 3'b100;               //
            reg_write = 1'b1;
            WB_src = 2'b10;
            Sec_add_src = 2'b00;
            PC_src = 1'b1;
        end
        7'b1100111: begin // jalr
            Imm_src = 3'b000;
            reg_write = 1'b1;
            WB_src = 2'b10;
            Sec_add_src = 2'b10;
            PC_src = 1'b1;
        end
        7'b0110111: begin // lui
            Imm_src = 3'b011;               //
            reg_write = 1'b1;
            WB_src = 2'b11;
            Sec_add_src = 2'b01;
        end
        7'b0010111: begin // auipc
            Imm_src = 3'b011;               //
            reg_write = 1'b1;
            WB_src = 2'b11;
            Sec_add_src = 2'b00;
        end
        default : begin
            // needed for compiler
        end
    endcase
end

endmodule

module RegisterFile (
    input logic clk,
    input logic write_enable,
    input logic [4:0] address1,
    input logic [4:0] address2,
    input logic [4:0] address3,
    input logic [31:0] register_data,

    output logic [31:0] read1,
    output logic [31:0] read2
);

logic [31:0] registers [0:31];

initial begin
    for (int i = 0; i < 32; i++) begin
        registers[i] = 32'b0;
    end
end

always_comb begin
    if (address1 == 5'b0)
        read1 = 32'b0;
    else
        read1 = registers[address1];
    if (address2 == 5'b0)
        read2 = 32'b0;
    else
        read2 = registers[address2];
end

always @(posedge clk) begin
    if (write_enable && address3 != 5'b0) begin
        registers[address3] <= register_data;
    end
end

endmodule 


module ImmediateGenerator (
    input logic [31:0] instruction,
    input logic [2:0] Imm_src,

    output logic [31:0] immediate
);

always_comb begin
    case (Imm_src)
        3'b000 : begin // I
            immediate = {{20{instruction[31]}}, instruction[31:20]};
        end
        3'b001 : begin // S
            immediate = {{20{instruction[31]}}, instruction[31:25], instruction[11:7]};
        end
        3'b010 : begin // B
            immediate = {{19{instruction[31]}}, instruction[31], instruction[7], instruction[30:25], instruction[11:8], 1'b0};
        end
        3'b011 : begin // U
            immediate = {instruction[31:12], 12'b0};
        end
        3'b100 : begin // J
            immediate = {{11{instruction[31]}}, instruction[31], instruction[19:12], instruction[20], instruction[30:21], 1'b0};
        end
        default:
            immediate = 32'b0;
    endcase
end

endmodule


module ALUMUX (
    input logic [31:0] read2,
    input logic [31:0] immediate,
    input logic ALU_src,

    output logic [31:0] operandb
);

always_comb begin
    if (ALU_src == 1'b0) begin
        operandb = read2;
    end
    else begin
        operandb = immediate;
    end
end

endmodule


module ALU (
    input logic [31:0] operand1,
    input logic [31:0] operand2,
    input logic [3:0] ALU_ctrl, 

    output logic [31:0] result,
    output logic zero,
    output logic alu_lsb
);

always_comb begin
    case (ALU_ctrl)
        4'b0000 : begin // Add
            result = operand1 + operand2;
        end
        4'b0001 : begin // Subtract
            result = operand1 - operand2;
        end
        4'b0010 : begin // And
            result = operand1 & operand2;
        end
        4'b0011 : begin // Or
            result = operand1 | operand2;
        end
        4'b0100 : begin // Xor
            result = operand1 ^ operand2;
        end
        4'b0101 : begin // Sll
            result = operand1 << operand2[4:0];
        end
        4'b0110 : begin // Srl
            result = operand1 >> operand2[4:0];
        end
        4'b0111 : begin // Sra
            result = $signed(operand1) >>> operand2[4:0];
        end
        4'b1000 : begin // Slt
            result = {31'b0, ($signed(operand1) < $signed(operand2))};
        end
        4'b1001 : begin /// Sltu
            result = {31'b0, (operand1 < operand2)};
        end
        default:
            result = 32'b0;
    endcase
    if (result == 32'b0) begin
        zero = 1'b1;
    end
    else begin
        zero = 1'b0;
    end
    alu_lsb = result[0];
end

endmodule


module PC4Adder (
    input logic [31:0] pc,

    output logic [31:0] pc_plus4
);

always_comb begin
    pc_plus4 = pc + 32'd4;
end

endmodule


module MUXBranchAdder (
    input logic [31:0] current_pc,
    input logic [31:0] read1,
    input logic [31:0] immediate_extended,
    input logic [1:0] sec_add_src,

    output logic [31:0] pc_target
);

logic [31:0] adder_input;

always_comb begin
    case (sec_add_src)
        2'b00 : begin
            adder_input = current_pc;
        end
        2'b01 : begin
            adder_input = 32'b0;
        end
        2'b10 : begin
            adder_input =  read1;
        end
        default : begin
            // needed for compiler
        end
    endcase
    pc_target = adder_input + immediate_extended;
end

endmodule


module DataMemory #(parameter WORDS = 64) (
    input logic clk,
    input logic [31:0] byte_address,
    input logic [31:0] write_data,
    input logic [3:0] byte_enables,
    input logic write_enable,

    output logic [31:0] read_data
);

logic [31:0] memory [0:WORDS-1];
logic [31:0] word_address;
assign word_address = {2'b0, byte_address[31:2]};

always_comb begin
    read_data = memory[word_address];
end

always @(posedge clk) begin
    if (write_enable == 1'b1) begin
        if (byte_enables[0] == 1'b1) begin
            memory[word_address][7:0] <= write_data[7:0];
        end
        if (byte_enables[1] == 1'b1) begin
            memory[word_address][15:8] <= write_data[15:8];
        end
        if (byte_enables[2] == 1'b1) begin
            memory[word_address][23:16] <= write_data[23:16];
        end
        if (byte_enables[3] == 1'b1) begin
            memory[word_address][31:24] <= write_data[31:24];
        end
    end
end

endmodule

module Decoder (
    input logic [2:0] funct3,
    input logic [31:0] alu_res,
    input logic [31:0] reg_read,

    output logic [31:0] mask,
    output logic [3:0] BE_bits,
    output logic [1:0] alu_offset

);

assign alu_offset = alu_res[1:0];

always_comb begin
    mask = 32'b0;
    BE_bits = 4'b0000;
    case (funct3)
        3'b000: begin // sb
            case (alu_offset)
                2'b00: begin
                    mask = {24'b0, reg_read[7:0]};
                    BE_bits = 4'b0001;
                end
                2'b01: begin
                    mask = {16'b0, reg_read[7:0], 8'b0};
                    BE_bits = 4'b0010;
                end
                2'b10: begin
                    mask = {8'b0, reg_read[7:0], 16'b0};
                    BE_bits = 4'b0100;
                end
                2'b11: begin
                    mask = {reg_read[7:0], 24'b0};
                    BE_bits = 4'b1000;
                end
            endcase
        end
        3'b001: begin // sh
            case (alu_offset)
                2'b00: begin
                    mask = {16'b0, reg_read[15:0]};
                    BE_bits = 4'b0011;
                end
                2'b10: begin
                    mask = {reg_read[15:0], 16'b0};
                    BE_bits = 4'b1100;
                end
                default : begin
                    // needed for compiler
                end
            endcase
        end
        3'b010: begin // sw
            mask = reg_read;
            BE_bits = 4'b1111;
        end
        default : begin
            // needed for compiler
        end
    endcase
end

endmodule


module ReadDataAlignment (
    input logic [31:0] word,
    input logic [2:0] funct3,
    input logic [1:0] alu_res_offset,

    output logic [31:0] load_data
);

logic [7:0] extracted_byte;
logic [15:0] extracted_halfword;

always_comb begin
    load_data = 32'b0;
    case (funct3)
        3'b000 : begin // lb
            case (alu_res_offset)
                2'b00 : begin
                    extracted_byte = word[7:0];
                    load_data = {{24{extracted_byte[7]}}, extracted_byte};
                end
                2'b01 : begin
                    extracted_byte = word[15:8];
                    load_data = {{24{extracted_byte[7]}}, extracted_byte};
                end
                2'b10 : begin
                    extracted_byte = word[23:16];
                    load_data = {{24{extracted_byte[7]}}, extracted_byte};
                end
                2'b11 : begin
                    extracted_byte = word[31:24];
                    load_data = {{24{extracted_byte[7]}}, extracted_byte};
                end
                default : begin
                    // needed for compiler
                end
            endcase
        end
        3'b001 : begin // lh
            case (alu_res_offset)
                2'b00 : begin
                    extracted_halfword = word[15:0];
                    load_data = {{16{extracted_halfword[15]}}, extracted_halfword};
                end
                2'b10 : begin
                    extracted_halfword = word[31:16];
                    load_data = {{16{extracted_halfword[15]}}, extracted_halfword};
                end
                default : begin
                    // needed for compiler
                end
            endcase
        end
        3'b100 : begin // lbu
            case (alu_res_offset)
                2'b00 : begin
                    extracted_byte = word[7:0];
                    load_data = {24'b0, extracted_byte};
                end
                2'b01 : begin
                    extracted_byte = word[15:8];
                    load_data = {24'b0, extracted_byte};
                end
                2'b10 : begin
                    extracted_byte = word[23:16];
                    load_data = {24'b0, extracted_byte};
                end
                2'b11 : begin
                    extracted_byte = word[31:24];
                    load_data = {24'b0, extracted_byte};
                end
                default : begin
                    // needed for compiler
                end
            endcase
        end
        3'b101 : begin // lhu
            case (alu_res_offset)
                2'b00 : begin
                    extracted_halfword = word[15:0];
                    load_data = {16'b0, extracted_halfword};
                end
                2'b10 : begin
                    extracted_halfword = word[31:16];
                    load_data = {16'b0, extracted_halfword};
                end
                default : begin
                    // needed for compiler
                end
            endcase
        end
        3'b010 : begin
            load_data = word;
        end
        default : begin
            // needed for compiler
        end
    endcase
end

endmodule


module WriteBackMUX (
    input logic [31:0] alu_result,
    input logic [31:0] loaded_data,
    input logic [31:0] pc_plus4,
    input logic [31:0] immediate_extended,
    input logic [1:0] WB_src,

    output logic [31:0] write_data
);

always_comb begin
    if (WB_src == 2'b00) begin
        write_data = alu_result;
    end
    else if (WB_src == 2'b01) begin
        write_data = loaded_data;
    end
    else if (WB_src == 2'b10) begin
        write_data = pc_plus4;
    end
    else if (WB_src == 2'b11) begin
        write_data = immediate_extended;
    end
    else begin
        write_data = 32'b0;
    end
end

endmodule


module PCSourceMUX (
    input logic [31:0] pc_plus4,
    input logic [31:0] pc_target,
    input logic PC_src,

    output logic [31:0] pc_next
);

always_comb begin
    if (PC_src) begin
        pc_next = pc_target;
    end
    else begin
        pc_next = pc_plus4;
    end
end

endmodule

module SingleCycleProcessorCore (
    input logic clk,
    input logic reset_n,

    output logic [31:0] output_data
);

    logic [31:0] wireA;
    PCSourceMUX moduleA (
        .pc_plus4(wireD),
        .pc_target(wireQ),
        .PC_src(wireE),

        .pc_next(wireA)
    );

    logic [31:0] wireB;
    ProgramCounter moduleB (
        .clk(clk),
        .reset_n(reset_n),
        .pc_next(wireA),

        .pc(wireB)
    );

    logic [31:0] wireC;
    logic [4:0] wireAB;
    logic [4:0] wireAC;
    logic [4:0] wireAD;
    InstructionMemory moduleC (
        .address(wireB),

        .instruction(wireC),
        .part1(wireAB),
        .part2(wireAC),
        .part3(wireAD)
    );

    logic [31:0] wireD;
    PC4Adder moduleD (
        .pc(wireB),

        .pc_plus4(wireD)
    );

    logic wireE;
    logic [1:0] wireF;
    logic [3:0] wireG;
    logic wireH;
    logic [1:0] wireI;
    logic [2:0] wireJ;
    logic wireK;
    logic wireL;
    logic [2:0] wireZ;
    ControlUnit moduleE (
        .instruction(wireC),
        .zero(wireS),
        .alu_lsb(wireT),

        .PC_src(wireE),
        .WB_src(wireF),
        .ALU_ctrl(wireG),
        .ALU_src(wireH),
        .Sec_add_src(wireI),
        .Imm_src(wireJ),
        .reg_write(wireK),
        .mem_write(wireL),
        .funct3(wireZ)
    );

    logic [31:0] wireM;
    logic [31:0] wireN;
    RegisterFile moduleF (
        .clk(clk),
        .write_enable(wireK),
        .address1(wireAB),
        .address2(wireAC),
        .address3(wireAD),
        .register_data(wireY),

        .read1(wireM),
        .read2(wireN)
    );

    logic [31:0] wireO;
    ImmediateGenerator moduleG (
        .instruction(wireC),
        .Imm_src(wireJ),

        .immediate(wireO)
    );

    logic [31:0] wireP;
    ALUMUX moduleH (
        .read2(wireN),
        .immediate(wireO),
        .ALU_src(wireH),

        .operandb(wireP)
    );

    logic [31:0] wireQ;
    MUXBranchAdder moduleI (
        .current_pc(wireB),
        .read1(wireM),
        .immediate_extended(wireO),
        .sec_add_src(wireI),

        .pc_target(wireQ)
    );

    logic [31:0] wireR;
    logic wireS;
    logic wireT;
    ALU moduleJ (
        .operand1(wireM),
        .operand2(wireP),
        .ALU_ctrl(wireG), 

        .result(wireR),
        .zero(wireS),
        .alu_lsb(wireT)
    );

    logic [31:0] wireU;
    logic [3:0] wireV;
    logic [1:0] wireAA;
    Decoder moduleK (
        .funct3(wireZ),
        .alu_res(wireR),
        .reg_read(wireN),

        .mask(wireU),
        .BE_bits(wireV),
        .alu_offset(wireAA)
    );

    logic [31:0] wireW;
    DataMemory moduleL (
        .clk(clk),
        .byte_address(wireR),
        .write_data(wireU),
        .byte_enables(wireV),
        .write_enable(wireL),

        .read_data(wireW)
    );

    logic [31:0] wireX;
    ReadDataAlignment moduleM (
        .word(wireW),
        .funct3(wireZ),
        .alu_res_offset(wireAA),

        .load_data(wireX)
    );

    logic [31:0] wireY;
    WriteBackMUX moduleN (
        .alu_result(wireR),
        .loaded_data(wireX),
        .pc_plus4(wireD),
        .immediate_extended(wireQ),
        .WB_src(wireF),

        .write_data(wireY)
    );
    assign output_data = wireY;

endmodule