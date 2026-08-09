import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner  # <-- Import the runner API

#----------------------------------------------------------------------------------------------------------------------------------------
#       MODULE-LEVEL TESTING

@cocotb.test()
async def test_program_counter(dut):

    # Start a 10 ns clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Test reset
    dut.reset_n.value = 0
    dut.pc_next.value = 0x12345678
    await RisingEdge(dut.clk)
    assert dut.pc.value.to_unsigned() == 0

    # Release reset and load first value
    dut.reset_n.value = 1
    dut.pc_next.value = 0x12345678
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    assert dut.pc.value.to_unsigned() == 0x12345678

    # Load another value
    dut.pc_next.value = 0xDEADBEEF
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    assert dut.pc.value.to_unsigned() == 0xDEADBEEF

    # Ensure PC does not change between clock edges
    dut.pc_next.value = 0xCAFEBABE
    await Timer(5, unit="ns")  # Half a clock period
    assert dut.pc.value.to_unsigned() == 0xDEADBEEF

    # Next rising edge should update it
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    assert dut.pc.value.to_unsigned() == 0xCAFEBABE

@cocotb.test()
async def test_instruction_memory(dut):

    # Initialize memory contents
    dut.memory[0].value = 0x00A484B3
    dut.memory[1].value = 0x12345678
    dut.memory[2].value = 0xFFFFFFFF

    # Read word 0
    dut.address.value = 0x00000000
    await Timer(1, unit="ns")
    assert dut.instruction.value.to_unsigned() == 0x00A484B3
    assert dut.part1.value.to_unsigned() == ((0x00A484B3 >> 15) & 0x1F)
    assert dut.part2.value.to_unsigned() == ((0x00A484B3 >> 20) & 0x1F)
    assert dut.part3.value.to_unsigned() == ((0x00A484B3 >> 7) & 0x1F)

    # Address 4 should select memory[1]
    dut.address.value = 0x00000004
    await Timer(1, unit="ns")
    assert dut.instruction.value.to_unsigned() == 0x12345678
    assert dut.part1.value.to_unsigned() == ((0x12345678 >> 15) & 0x1F)
    assert dut.part2.value.to_unsigned() == ((0x12345678 >> 20) & 0x1F)
    assert dut.part3.value.to_unsigned() == ((0x12345678 >> 7) & 0x1F)

    # Address 8 should select memory[2]
    dut.address.value = 0x00000008
    await Timer(1, unit="ns")
    assert dut.instruction.value.to_unsigned() == 0xFFFFFFFF
    assert dut.part1.value.to_unsigned() == 31
    assert dut.part2.value.to_unsigned() == 31
    assert dut.part3.value.to_unsigned() == 31

    # Verify word alignment
    for addr in range(4):
        dut.address.value = addr
        await Timer(1, unit="ns")
        assert dut.instruction.value.to_unsigned() == 0x00A484B3
    for addr in range(4, 8):
        dut.address.value = addr
        await Timer(1, unit="ns")
        assert dut.instruction.value.to_unsigned() == 0x12345678

def make_instruction(opcode, funct3=0, funct7=0):
    return ((funct7 << 25) | (funct3 << 12) | opcode)

@cocotb.test()
async def test_control_unit(dut):

    # ADD
    dut.zero.value = 0
    dut.alu_lsb.value = 0
    dut.instruction.value = make_instruction(
        0b0110011,
        funct3=0b000,
        funct7=0b0000000
    )
    await Timer(1, "ns")
    assert dut.reg_write.value == 1
    assert dut.ALU_ctrl.value == 0
    assert dut.ALU_src.value == 0
    assert dut.mem_write.value == 0

    # SUB
    dut.instruction.value = make_instruction(
        0b0110011,
        funct3=0b000,
        funct7=0b0100000
    )
    await Timer(1, "ns")
    assert dut.ALU_ctrl.value == 1
    assert dut.reg_write.value == 1

    # AND
    dut.instruction.value = make_instruction(
        0b0110011,
        funct3=0b111
    )
    await Timer(1, "ns")
    assert dut.ALU_ctrl.value == 2

    # OR
    dut.instruction.value = make_instruction(
        0b0110011,
        funct3=0b110
    )
    await Timer(1, "ns")
    assert dut.ALU_ctrl.value == 3

    # ADDI
    dut.instruction.value = make_instruction(
        0b0010011,
        funct3=0b000
    )
    await Timer(1, "ns")
    assert dut.reg_write.value == 1
    assert dut.ALU_src.value == 1
    assert dut.ALU_ctrl.value == 0

    dut.instruction.value = make_instruction(0b0000011)
    await Timer(1, "ns")
    assert dut.reg_write.value == 1
    assert dut.WB_src.value == 1
    assert dut.Imm_src.value == 2
    assert dut.ALU_src.value == 1

    dut.instruction.value = make_instruction(0b0100011)
    await Timer(1, "ns")
    assert dut.mem_write.value == 1
    assert dut.reg_write.value == 0
    assert dut.Imm_src.value == 1

    dut.zero.value = 1
    dut.instruction.value = make_instruction(
        0b1100011,
        funct3=0b000
    )
    await Timer(1, "ns")
    assert dut.PC_src.value == 1
    assert dut.ALU_ctrl.value == 1

    dut.zero.value = 0
    dut.instruction.value = make_instruction(
        0b1100011,
        funct3=0b001
    )
    await Timer(1, "ns")
    assert dut.PC_src.value == 1

    dut.alu_lsb.value = 1
    dut.instruction.value = make_instruction(
        0b1100011,
        funct3=0b100
    )
    await Timer(1, "ns")
    assert dut.PC_src.value == 1
    assert dut.ALU_ctrl.value == 8

    dut.instruction.value = make_instruction(0b1101111)
    await Timer(1, "ns")

    assert dut.reg_write.value == 1
    assert dut.PC_src.value == 1
    assert dut.WB_src.value == 2
    assert dut.Imm_src.value == 3

    dut.instruction.value = make_instruction(0b1100111)
    await Timer(1, "ns")
    assert dut.reg_write.value == 1
    assert dut.PC_src.value == 1
    assert dut.WB_src.value == 2
    assert dut.Sec_add_src.value == 2

    dut.instruction.value = make_instruction(0b0110111)
    await Timer(1, "ns")

    assert dut.reg_write.value == 1
    assert dut.WB_src.value == 3
    assert dut.Imm_src.value == 4
    assert dut.Sec_add_src.value == 1

    dut.instruction.value = make_instruction(0b0010111)
    await Timer(1, "ns")

    assert dut.reg_write.value == 1
    assert dut.WB_src.value == 3
    assert dut.Imm_src.value == 4
    assert dut.Sec_add_src.value == 0

@cocotb.test()
async def test_register_file(dut):

    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Verify all registers initialize to zero
    for i in range(32):
        dut.address1.value = i
        dut.address2.value = 0
        await Timer(1, unit="ns")
        assert dut.read1.value.to_unsigned() == 0

    # Write x5 = 0x12345678
    dut.write_enable.value = 1
    dut.address3.value = 5
    dut.register_data.value = 0x12345678
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.address1.value = 5
    await Timer(1, unit="ns")
    assert dut.read1.value.to_unsigned() == 0x12345678

    # Write x10 = 0xDEADBEEF
    dut.address3.value = 10
    dut.register_data.value = 0xDEADBEEF
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.address1.value = 10
    await Timer(1, unit="ns")
    assert dut.read1.value.to_unsigned() == 0xDEADBEEF

    # Verify simultaneous reads
    dut.address1.value = 5
    dut.address2.value = 10
    await Timer(1, unit="ns")
    assert dut.read1.value.to_unsigned() == 0x12345678
    assert dut.read2.value.to_unsigned() == 0xDEADBEEF

    # Verify writes only happen on clock edges
    dut.address3.value = 15
    dut.register_data.value = 0xCAFEBABE
    await Timer(5, unit="ns")      # Half a clock period
    dut.address1.value = 15
    await Timer(1, unit="ns")
    assert dut.read1.value.to_unsigned() == 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    await Timer(1, unit="ns")
    assert dut.read1.value.to_unsigned() == 0xCAFEBABE

    # Verify write_enable prevents writes
    dut.write_enable.value = 0
    dut.address3.value = 20
    dut.register_data.value = 0xAAAAAAAA
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.address1.value = 20
    await Timer(1, unit="ns")
    assert dut.read1.value.to_unsigned() == 0

    # Verify x0 is always zero
    dut.write_enable.value = 1
    dut.address3.value = 0
    dut.register_data.value = 0xFFFFFFFF
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.address1.value = 0
    await Timer(1, unit="ns")
    assert dut.read1.value.to_unsigned() == 0

@cocotb.test()
async def test_immediate_generator(dut):

    # I-type
    dut.Imm_src.value = 0b000
    dut.instruction.value = (0x123 << 20)
    await Timer(1, unit="ns")
    assert dut.immediate.value.to_unsigned() == 0x123

    # I-type (negative)
    dut.Imm_src.value = 0b000
    dut.instruction.value = (0xFFF << 20)
    await Timer(1, unit="ns")
    assert dut.immediate.value.to_unsigned() == 0xFFFFFFFF

    # S-type
    imm = 0x155
    instruction = ((imm >> 5) << 25) | ((imm & 0x1F) << 7)
    dut.Imm_src.value = 0b001
    dut.instruction.value = instruction
    await Timer(1, unit="ns")
    assert dut.immediate.value.to_unsigned() == imm

    # B-type
    imm = 16
    instruction = (
        ((imm >> 12) & 1) << 31 |
        ((imm >> 11) & 1) << 7 |
        ((imm >> 5) & 0x3F) << 25 |
        ((imm >> 1) & 0xF) << 8
    )
    dut.Imm_src.value = 0b010
    dut.instruction.value = instruction
    await Timer(1, unit="ns")
    assert dut.immediate.value.to_unsigned() == 16

    # U-type
    dut.Imm_src.value = 0b011
    dut.instruction.value = 0x12345000
    await Timer(1, unit="ns")
    assert dut.immediate.value.to_unsigned() == 0x12345000
    # J-type
    # immediate = 2048
    imm = 2048
    instruction = (
        ((imm >> 20) & 1) << 31 |
        ((imm >> 12) & 0xFF) << 12 |
        ((imm >> 11) & 1) << 20 |
        ((imm >> 1) & 0x3FF) << 21
    )
    dut.Imm_src.value = 0b100
    dut.instruction.value = instruction
    await Timer(1, unit="ns")
    assert dut.immediate.value.to_unsigned() == 2048

@cocotb.test()
async def test_alu_mux(dut):

    # Select read2
    dut.read2.value = 0x12345678
    dut.immediate.value = 0xDEADBEEF
    dut.ALU_src.value = 0
    await Timer(1, unit="ns")
    assert dut.operandb.value.to_unsigned() == 0x12345678

    # Select immediate
    dut.ALU_src.value = 1
    await Timer(1, unit="ns")
    assert dut.operandb.value.to_unsigned() == 0xDEADBEEF

    # Change read2 while selecting immediate
    dut.read2.value = 0xAAAAAAAA
    await Timer(1, unit="ns")
    assert dut.operandb.value.to_unsigned() == 0xDEADBEEF

    # Change immediate
    dut.immediate.value = 0xCAFEBABE
    await Timer(1, unit="ns")
    assert dut.operandb.value.to_unsigned() == 0xCAFEBABE

    # Switch back to read2
    dut.ALU_src.value = 0
    await Timer(1, unit="ns")
    assert dut.operandb.value.to_unsigned() == 0xAAAAAAAA

async def check_alu(dut, op1, op2, ctrl, expected):
    dut.operand1.value = op1
    dut.operand2.value = op2
    dut.ALU_ctrl.value = ctrl
    await Timer(1, unit="ns")
    result = dut.result.value.to_unsigned()
    assert result == expected & 0b11111111111111111111111111111111
    assert dut.zero.value == (expected == 0)
    assert dut.alu_lsb.value == ((expected & 1) != 0)


@cocotb.test()
async def test_alu(dut):

    # ADD
    await check_alu(dut, 10, 5, 0b0000, 15)
    # SUB
    await check_alu(dut, 10, 5, 0b0001, 5)
    # AND
    await check_alu(dut, 0b1100, 0b1010, 0b0010, 0b1000)
    # OR
    await check_alu(dut, 0b1100, 0b1010, 0b0011, 0b1110)
    # XOR
    await check_alu(dut, 0b1100, 0b1010, 0b0100, 0b0110)
    # SLL
    await check_alu(dut, 1, 4, 0b0101, 16)
    # SRL
    await check_alu(dut, 0b10000, 2, 0b0110, 0b100)
    # SRA
    await check_alu(dut, 0b11111111111111111111111111110000, 2, 0b0111, 0b11111111111111111111111111111100)
    # SLT signed
    await check_alu(dut, 5, 10, 0b1000, 1)
    await check_alu(dut, 10, 5, 0b1000, 0)
    # SLT signed negative
    await check_alu(dut, 0b11111111111111111111111111111111, 1, 0b1000, 1)
    # SLTU unsigned
    await check_alu(dut, 5, 10, 0b1001, 1)
    await check_alu(dut, 0b11111111111111111111111111111111, 1, 0b1001, 0)
    # Zero flag test
    await check_alu(dut, 5, 5, 0b0001, 0)

@cocotb.test()
async def test_mux_branch_adder(dut):

    # Test branch/jump target:
    dut.current_pc.value = 0x1000
    dut.read1.value = 0x5000
    dut.immediate_extended.value = 0x20
    dut.sec_add_src.value = 0b00
    await Timer(1, unit="ns")
    assert dut.pc_target.value.to_unsigned() == 0x1020

    # Test LUI:
    dut.current_pc.value = 0x1000
    dut.immediate_extended.value = 0x12345000
    dut.sec_add_src.value = 0b01
    await Timer(1, unit="ns")
    assert dut.pc_target.value.to_unsigned() == 0x12345000

    # Test JALR:
    # read1 + immediate
    dut.read1.value = 0x2000
    dut.immediate_extended.value = 0x100
    dut.sec_add_src.value = 0b10
    await Timer(1, unit="ns")
    assert dut.pc_target.value.to_unsigned() == 0x2100

    # Verify input independence
    dut.current_pc.value = 0xFFFFFFFF
    dut.immediate_extended.value = 0x10
    dut.read1.value = 0x3000
    dut.sec_add_src.value = 0b10
    await Timer(1, unit="ns")
    assert dut.pc_target.value.to_unsigned() == 0x3010

@cocotb.test()
async def test_data_memory(dut):

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize inputs
    dut.write_enable.value = 0
    dut.byte_enables.value = 0
    dut.byte_address.value = 0
    dut.write_data.value = 0

    # Test full word write
    dut.byte_address.value = 0
    dut.write_data.value = 0x12345678
    dut.byte_enables.value = 0b1111
    dut.write_enable.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.write_enable.value = 0
    await Timer(1, unit="ns")
    assert dut.read_data.value.to_unsigned() == 0x12345678

    # Test second word
    dut.byte_address.value = 4
    dut.write_data.value = 0xDEADBEEF
    dut.byte_enables.value = 0b1111
    dut.write_enable.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.write_enable.value = 0
    await Timer(1, unit="ns")
    assert dut.read_data.value.to_unsigned() == 0xDEADBEEF

    # Test individual byte writes
    dut.byte_address.value = 8
    # Write only lowest byte
    dut.write_data.value = 0xAAAAAAAA
    dut.byte_enables.value = 0b0001
    dut.write_enable.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.write_enable.value = 0
    await Timer(1, unit="ns")
    assert dut.read_data.value.to_unsigned() == 0x000000AA

    # Write second byte
    dut.write_data.value = 0xBBBBBBBB
    dut.byte_enables.value = 0b0010
    dut.write_enable.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.write_enable.value = 0
    await Timer(1, unit="ns")
    assert dut.read_data.value.to_unsigned() == 0x0000BBAA


    # Write third byte
    dut.write_data.value = 0xCCCCCCCC
    dut.byte_enables.value = 0b0100
    dut.write_enable.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.write_enable.value = 0
    await Timer(1, unit="ns")
    assert dut.read_data.value.to_unsigned() == 0x00CCBBAA

    # Write fourth byte
    dut.write_data.value = 0xDDDDDDDD
    dut.byte_enables.value = 0b1000
    dut.write_enable.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.write_enable.value = 0
    await Timer(1, unit="ns")
    assert dut.read_data.value.to_unsigned() == 0xDDCCBBAA

    # Test write disabled
    old_value = dut.read_data.value.to_unsigned()
    dut.write_data.value = 0xFFFFFFFF
    dut.byte_enables.value = 0b1111
    dut.write_enable.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    assert dut.read_data.value.to_unsigned() == old_value

@cocotb.test()
async def test_decoder(dut):

    dut.funct3.value = 0b000
    dut.reg_read.value = 0x000000AA

    # Store byte at offset 0
    dut.alu_res.value = 0x00000000
    await Timer(1, unit="ns")
    assert dut.alu_offset.value.to_unsigned() == 0
    assert dut.mask.value.to_unsigned() == 0x000000AA
    assert dut.BE_bits.value.to_unsigned() == 0b0001

    # Store byte at offset 1
    dut.alu_res.value = 0x00000001
    await Timer(1, unit="ns")
    assert dut.mask.value.to_unsigned() == 0x0000AA00
    assert dut.BE_bits.value.to_unsigned() == 0b0010

    # Store byte at offset 2
    dut.alu_res.value = 0x00000002
    await Timer(1, unit="ns")
    assert dut.mask.value.to_unsigned() == 0x00AA0000
    assert dut.BE_bits.value.to_unsigned() == 0b0100

    # Store byte at offset 3
    dut.alu_res.value = 0x00000003
    await Timer(1, unit="ns")
    assert dut.mask.value.to_unsigned() == 0xAA000000
    assert dut.BE_bits.value.to_unsigned() == 0b1000

    dut.funct3.value = 0b001
    dut.reg_read.value = 0x0000BEEF

    # Halfword at lower half
    dut.alu_res.value = 0x00000000
    await Timer(1, unit="ns")
    assert dut.mask.value.to_unsigned() == 0x0000BEEF
    assert dut.BE_bits.value.to_unsigned() == 0b0011

    # Halfword at upper half
    dut.alu_res.value = 0x00000002
    await Timer(1, unit="ns")
    assert dut.mask.value.to_unsigned() == 0xBEEF0000
    assert dut.BE_bits.value.to_unsigned() == 0b1100

    # Invalid halfword alignment
    dut.alu_res.value = 0x00000001
    await Timer(1, unit="ns")
    assert dut.BE_bits.value.to_unsigned() == 0

    dut.funct3.value = 0b010
    dut.reg_read.value = 0x12345678
    dut.alu_res.value = 0x00000003
    await Timer(1, unit="ns")
    assert dut.mask.value.to_unsigned() == 0x12345678
    assert dut.BE_bits.value.to_unsigned() == 0b1111

    # Invalid funct3
    dut.funct3.value = 0b111
    await Timer(1, unit="ns")
    assert dut.mask.value.to_unsigned() == 0
    assert dut.BE_bits.value.to_unsigned() == 0

@cocotb.test()
async def test_read_data_alignment(dut):

    # Test word load (lw)
    dut.word.value = 0x12345678
    dut.funct3.value = 0b010
    dut.alu_res_offset.value = 0
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x12345678

    # Test LB (sign extended byte)
    dut.funct3.value = 0b000
    # byte 0 = 0x78 (positive)
    dut.alu_res_offset.value = 0
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x00000078

    # byte 1 = 0x56 (positive)
    dut.alu_res_offset.value = 1
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x00000056

    # byte 2 = 0x34
    dut.alu_res_offset.value = 2
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x00000034

    # byte 3 = 0x12
    dut.alu_res_offset.value = 3
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x00000012

    # Test LB sign extension
    dut.word.value = 0x00000080
    dut.funct3.value = 0b000
    dut.alu_res_offset.value = 0
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0xFFFFFF80

    # Test LBU (zero extended byte)
    dut.funct3.value = 0b100
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x00000080

    # Test LH (sign extended halfword)
    dut.word.value = 0x80001234
    dut.funct3.value = 0b001
    dut.alu_res_offset.value = 0
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x00001234
    dut.alu_res_offset.value = 2
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0xFFFF8000

    # Test LHU (zero extended halfword)
    dut.funct3.value = 0b101
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0x00008000

    # Test invalid halfword alignment
    dut.funct3.value = 0b001
    dut.alu_res_offset.value = 1
    await Timer(1, unit="ns")
    assert dut.load_data.value.to_unsigned() == 0

#----------------------------------------------------------------------------------------------------------------------------------------
#       INSTRUCTION AND INTEGRATION TESTBENCHES


async def reset_cpu(dut):
    dut.reset_n.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.reset_n.value = 1
    await Timer(1, unit="ns")

async def clock_cycles(dut, count):
    for i in range(count):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

def set_reg(dut, register, value):
    dut.moduleF.registers[register].value = value & 0b11111111111111111111111111111111

def get_reg(dut, register):
    return dut.moduleF.registers[register].value.to_unsigned()

def set_instruction(dut, index, instruction):
    dut.moduleC.memory[index].value = instruction & 0b11111111111111111111111111111111

def set_data_word(dut, index, value):
    dut.moduleL.memory[index].value = value & 0b11111111111111111111111111111111

def get_pc(dut):
    return dut.moduleB.pc.value.to_unsigned()

async def setup_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

# Test Cases (One per RISC V Instruction Implemented):
# R Type: *requires addi to insert values in registers 2 and 3
#     Add: InputInstruction - 0000000/00011/00010/000/00100/0110011, ExpectedOutput - register 4 has value = register 2 + register 3
@cocotb.test()
async def test_add(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 15)
    set_reg(dut, 3, 27)
    set_instruction(dut, 0, 0b00000000001100010000001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 42
#     Sub: InputInstruction - 0100000/00011/00010/000/00100/0110011, ExpectedOutput - register 4 has value = register 3 - register 2
@cocotb.test()
async def test_sub(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 30)
    set_reg(dut, 3, 12)
    set_instruction(dut, 0, 0b01000000001100010000001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 18
#     Xor: InputInstruction - 0000000/00011/00010/100/00100/0110011, ExpectedOutput - register 4 has value = register 2 ^ register 3
@cocotb.test()
async def test_xor(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b10101010010101011010101001010101)
    set_reg(dut, 3, 0b11111111111111110000000000000000)
    set_instruction(dut, 0, 0b00000000001100010100001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == (0b10101010010101011010101001010101 ^ 0b11111111111111110000000000000000)
#     Or: InputInstruction - 0000000/00011/00010/110/00100/0110011, ExpectedOutput - register 4 has value = register 2 OR register 3
@cocotb.test()
async def test_or(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b10101010000000000000000000000000)
    set_reg(dut, 3, 0b00000000000000000101010101010101)
    set_instruction(dut, 0, 0b00000000001100010110001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 0b10101010000000000101010101010101
#     And: InputInstruction - 0000000/00011/00010/111/00100/0110011, ExpectedOutput - register 4 has value = register 2 AND register 3
@cocotb.test()
async def test_and(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b11111111111111110000000011111111)
    set_reg(dut, 3, 0b00001111000011110000111100001111)
    set_instruction(dut, 0, 0b00000000001100010111001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 0b00001111000011110000000000001111
#     Sll: InputInstruction - 0000000/00011/00010/001/00100/0110011, ExpectedOutput - register 4 has value = register 2 shifted left by value in register 3, inserting zeroes
@cocotb.test()
async def test_sll(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b00000000000000000000000000000011)
    set_reg(dut, 3, 4)
    set_instruction(dut, 0, 0b00000000001100010001001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 0b110000
#     Srl: InputInstruction - 0000000/00011/00010/101/00100/0110011, ExpectedOutput - register 4 has value = register 2 shifted right by value in register 3, inserting zeroes
@cocotb.test()
async def test_srl(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b00000000000000000000000011110000)
    set_reg(dut, 3, 4)
    set_instruction(dut, 0, 0b00000000001100010101001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 0b1111
#     Sra: InputInstruction - 0100000/00011/00010/101/00100/0110011, ExpectedOutput - register 4 has value = register 2 shifted right by value in register 3, inserting sign bit
@cocotb.test()
async def test_sra(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b11110000000000000000000000000000)
    set_reg(dut, 3, 4)
    set_instruction(dut, 0, 0b01000000001100010101001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 0b11111111000000000000000000000000
#     Slt: InputInstruction - 0000000/00011/00010/010/00100/0110011, ExpectedOutput - register 4 has value 1 if register 2 is less than register 3, else has value 0
@cocotb.test()
async def test_slt(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 5)
    set_reg(dut, 3, 10)
    set_instruction(dut, 0, 0b00000000001100010010001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 1
#     Sltu: InputInstruction - 0000000/00011/00010/011/00100/0110011, ExpectedOutput - register 4 has value of unsigned register 2 is less than unsigned register 3, else has value 0
@cocotb.test()
async def test_sltu(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 5)
    set_reg(dut, 3, 10)
    set_instruction(dut, 0, 0b00000000001100010011001000110011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 4) == 1

# I Type:
#     Addi: InputInstruction - 000000011100/00000/000/00010/0010011, ExpectedOutput - register 00010 in regfile has value 000000011100 (immediate)
@cocotb.test()
async def test_addi(dut):
    await setup_clock(dut)
    set_instruction(dut, 0, 0b00000001110000000000000100010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 2) == 28
#     Xori: InputInstruction - 000000011100/00010/100/00011/0010011, ExpectedOutput - register 3 has value = register 2 ^ immediate
@cocotb.test()
async def test_xori(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b1010101)
    set_instruction(dut, 0, 0b00000001110000010100000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == (0b1010101 ^ 28)
#     Ori: InputInstruction - 000000011100/00010/110/00011/0010011, ExpectedOutput - register 3 has value = register 2 OR immediate
@cocotb.test()
async def test_ori(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b1010101)
    set_instruction(dut, 0, 0b00000001110000010110000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == (0b1010101 | 28)
#     Andi: InputInstruction - 000000011100/00010/111/00011/0010011, ExpectedOutput - register 3 has value = register 2 AND immediate
@cocotb.test()
async def test_andi(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b11111111)
    set_instruction(dut, 0, 0b00000001110000010111000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == (0b11111111 & 28)
#     Slli: InputInstruction - 000000000011/00010/001/00011/0010011, ExpectedOutput - register 3 has value = register 2 shifted left by immediate value
@cocotb.test()
async def test_slli(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 3)
    set_instruction(dut, 0, 0b00000000001100010001000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 24
#     Srli: InputInstruction - 000000000011/00010/101/00011/0010011, ExpectedOutput - register 3 has value = register 2 shifted right by immediate value 
@cocotb.test()
async def test_srli(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b11110000)
    set_instruction(dut, 0, 0b00000000001100010101000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 0b00011110
#     Srai: InputInstruction - 010000000011/00010/101/00011/0010011, ExpectedOutput - register 3 has value = register 2 shifted right by immediate value, filling with sign bits
@cocotb.test()
async def test_srai(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b11110000000000000000000000000000)
    set_instruction(dut, 0, 0b01000000001100010101000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 0b11111110000000000000000000000000
#     Slti: InputInstruction - 000000011100/00010/010/00011/0010011, ExpectedOutput - register 3 has value 1 if register 2 has value less then immediate (sign extended)
@cocotb.test()
async def test_slti(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_instruction(dut, 0, 0b00000001110000010010000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 1
#     Sltiu: InputInstruction - 000000011100/00010/011/00011/0010011, ExpectedOutput - register 3 has value 1 if register 2 has value less than immediate (sign extended, unsigned comparison)
@cocotb.test()
async def test_sltiu(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_instruction(dut, 0, 0b00000001110000010011000110010011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 1
#     Lb: InputInstruction - 000000000110/00010/000/00011/0000011, ExpectedOutput - adds immediate value (offset) to register 2 value, obtains byte at calculated address in data memory, sign extends, then stores in register 3
@cocotb.test()
async def test_lb(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0)
    set_data_word(dut, 1, 0b00000000100000000000000000000000)
    set_instruction(dut, 0, 0b00000000011000010000000110000011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 0b11111111111111111111111110000000
#     Lh: InputInstruction - 000000000110/00010/001/00011/0000011, ExpectedOutput - adds immediate value (offset) to register 2 value, obtains halfword at calculated address in data memory, sign extends, then stores in register 3
@cocotb.test()
async def test_lh(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0)
    set_data_word(dut, 1, 0b10000000000000000000000000000000)
    set_instruction(dut, 0, 0b00000000011000010001000110000011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 0b11111111111111111000000000000000
#     Lw: InputInstruction - 000000000110/00010/010/00011/0000011, ExpectedOutput - adds immediate value (offset) to register 2 value, obtains word at calcualted address, stores in register 3
@cocotb.test()
async def test_lw(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0)
    set_data_word(dut, 1, 0b00010010001101000101011001111000)
    set_instruction(dut, 0, 0b00000000011000010010000110000011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 0b00010010001101000101011001111000
#     Lbu: InputInstruction - 000000000110/00010/100/00011/0000011, ExpectedOutput - same as lb but extends using zeroes
@cocotb.test()
async def test_lbu(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0)
    set_data_word(dut, 1, 0b00000000100000000000000000000000)
    set_instruction(dut, 0, 0b00000000011000010100000110000011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 0b00000000000000000000000010000000
#     Lhu: InputInstruction - 000000000110/00010/101/00011/0000011, ExpectedOutput - same as lh but extends using zeroes
@cocotb.test()
async def test_lhu(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0)
    set_data_word(dut, 1, 0b10000000000000000000000000000000)
    set_instruction(dut, 0, 0b00000000011000010101000110000011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 3) == 0b00000000000000001000000000000000
#     Jalr: InputInstruction - 000000000100/00010/000/00011/1100111, ExpectedOutput - calculates immediate + value of register 2, forces lsb = 0, stores pc+4 in register 3, jumps to calculated address
@cocotb.test()
async def test_jalr(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b100000)
    set_instruction(dut, 0, 0b00000000010000010000000111100111)
    set_instruction(dut, 9, 0b10011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_pc(dut) == 0b100100
    assert get_reg(dut, 3) == 4

# S Type:
#     Sb: InputInstruction - 0000000/00010/00011/000/00010/0100011, ExpectedOutput - stores 1st byte in register 2 in memory address = immediate offset by register 3
@cocotb.test()
async def test_sb(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b00000000000000000000000010101010)
    set_reg(dut, 3, 4)
    set_data_word(dut, 1, 0b10010001101000101011001111000)
    set_instruction(dut, 0, 0b00000000001000011000000100100011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert dut.moduleL.memory[1].value.to_unsigned() == 0b10010101010100101011001111000
#     Sh: InputInstruction - 0000000/00010/00011/001/00010/0100011, ExpectedOutput - same but for halfword in register 2
@cocotb.test()
async def test_sh(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b1011111011101111)
    set_reg(dut, 3, 4)
    set_data_word(dut, 1, 0b10010001101000101011001111000)
    set_instruction(dut, 0, 0b00000000001000011001000100100011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert dut.moduleL.memory[1].value.to_unsigned() == 0b10111110111011110101011001111000
#     Sw: InputInstruction - 0000000/00010/00011/010/00010/0100011, ExpectedOutput - same but for word in register 2
@cocotb.test()
async def test_sw(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 0b11011110101011011011111011101111)
    set_reg(dut, 3, 0)
    set_data_word(dut, 1, 0b10010001101000101011001111000)
    set_instruction(dut, 0, 0b00000000001000011010000100100011)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert dut.moduleL.memory[0].value.to_unsigned() == 0b11011110101011011011111011101111

# B Type:
async def run_branch_test(dut, instruction, should_branch):
    set_instruction(dut, 0, instruction)
    set_instruction(dut, 1, 0b00000000000000000000000000011101)
    set_instruction(dut, 2, 0b00000000000000000000000000011101)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    pc = get_pc(dut)
    if should_branch:
        assert pc == 8
    else:
        assert pc == 4
#     Beq: InputInstruction - 0000000/00010/00011/000/01000/1100011, ExpectedOutput - goes to instruction at pc + immediate if register 2 = register 3
@cocotb.test()
async def test_beq(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_reg(dut, 3, 10)
    instruction = 0b00000000001000011000010001100011
    await run_branch_test(dut, instruction, True)
#     Bne: InputInstruction - 0000000/00010/00011/001/01000/1100011, ExpectedOutput - goes to instruction at pc + immediate if register 2 != register 3
@cocotb.test()
async def test_bne(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_reg(dut, 3, 10)
    instruction = 0b00000000001000011001010001100011
    await run_branch_test(dut, instruction, False)
#     Blt: InputInstruction - 0000000/00010/00011/100/01000/1100011, ExpectedOutput - goes to instruction at pc + immediate if register 3 < register 2
@cocotb.test()
async def test_blt(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_reg(dut, 3, 10)
    instruction = 0b00000000001000011100010001100011
    await run_branch_test(dut, instruction, False)
#     Bge: InputInstruction - 0000000/00010/00011/101/01000/1100011, ExpectedOutput - goes to instruction at pc + immediate if register 3 >= register 2
@cocotb.test()
async def test_bge(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_reg(dut, 3, 10)
    instruction = 0b00000000001000011101010001100011
    await run_branch_test(dut, instruction, True)
#     Bltu: InputInstruction - 0000000/00010/00011/110/01000/1100011, ExpectedOutput - goes to instruction at pc + immediate if register 3 < register 2 (zero extended)
@cocotb.test()
async def test_bltu(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_reg(dut, 3, 10)
    instruction = 0b00000000001000011110010001100011
    await run_branch_test(dut, instruction, False)
#     Bgeu: InputInstruction - 0000000/00010/00011/111/01000/1100011, ExpectedOutput - goes to instruction at pc + immediate if register 3 >= register 2 (zero extended)
@cocotb.test()
async def test_bgeu(dut):
    await setup_clock(dut)
    set_reg(dut, 2, 10)
    set_reg(dut, 3, 10)
    instruction = 0b00000000001000011111010001100011
    await run_branch_test(dut, instruction, True)

# U Type:
#     Lui: InputInstruction - 01101001010101010010/01100/0110111, ExpectedOutput - takes immediate value and stores in register 12, with lower 12 being zeroes
@cocotb.test()
async def test_lui(dut):
    await setup_clock(dut)
    instruction = 0b01101001010101010010011000110111
    set_instruction(dut, 0, instruction)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 12) == 0b1101001010101010010000000000000
#     Auipc: InputInstruction - 01101001010101010010/01100/0010111, ExpectedOutput - takes immediate value (shifted left by 12) + current pc and stores address in register 12
@cocotb.test()
async def test_auipc(dut):
    await setup_clock(dut)
    instruction = 0b01101001010101010010011000010111
    set_instruction(dut, 0, instruction)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_reg(dut, 12) == 0b1101001010101010010000000000000

# J Type:
#     Jal: InputInstruction - 00000000100000000000/01100/1101111, ExpectedOutput - takes immediate value + current PC to jump to new instruction, saving pc + 4 in register 12
@cocotb.test()
async def test_jal(dut):
    await setup_clock(dut)
    set_instruction(dut, 0, 0b00000000100000000000011001101111)
    await reset_cpu(dut)
    await clock_cycles(dut, 1)
    assert get_pc(dut) == 8
    assert get_reg(dut, 12) == 4

#----------------------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    runner = get_runner("verilator")
    
    runner.build(
        sources=[os.path.abspath("RV32I_SingleCycle.sv")],
        hdl_toplevel="SingleCycleProcessorCore",   # Changes to whichever module I'm testing
        # build_args = ["--public-flat-rw"]
    )

    runner.test(
        hdl_toplevel="SingleCycleProcessorCore",   # Changes to whichever module I'm testing
        test_module="Test_Benches"
    )