# Copyright (C) 2021, 2022 John Haskins Jr.

import functools
import struct

def compressed_unimplemented_instruction(word, **kwargs):
    return {
        'cmd': 'Undefined',
        'word': word,
        'size': 2,
    }
def uncompressed_unimplemented_instruction(word, **kwargs):
    return {
        'cmd': 'Undefined',
        'word': word,
        'size': 4,
    }

def c_j(word, **kwargs):
    # C.J performs an unconditional control transfer. The offset is
    # sign-extended and added to the pc to form the jump target address.
    # C.J can therefore target a ±2 KiB range. C.J expands to jal x0,
    # offset[11:1].
    return {
        'cmd': 'JAL',
        'imm': kwargs.get('imm'),
        'rd': 0,
        'word': word,
        'size': 2,
    }
def c_jr(word):
    return {
        'cmd': 'JALR',
        'imm': 0,
        'rs1': compressed_rs1_or_rd(word),
        'rd': 0,
        'word': word,
        'size': 2,
    }
def c_jalr(word):
    # C.JALR (jump and link register) performs the same operation as
    # C.JR, but additionally writes the address of the instruction
    # following the jump (pc+2) to the link register, x1. C.JALR expands
    # to jalr x1, 0(rs1). C.JALR is only valid when rs1̸=x0; the code
    # point with rs1=x0 corresponds to the C.EBREAK instruction.
    return {
        'cmd': 'JALR',
        'imm': 0,
        'rs1': compressed_rs1_or_rd(word),
        'rd': 1,
        'word': word,
        'size': 2,
    }
def c_beqz(word, **kwargs):
    # BEQZ performs conditional control transfers. The offset is
    # sign-extended and added to the pc to form the branch target address.
    # It can therefore target a ±256 B range. C.BEQZ takes the branch if
    # the value in register rs1' is zero. It expands to
    # beq rs1', x0, offset[8:1].
    return {
        'cmd': 'BEQ',
        'imm': kwargs.get('imm'),
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': 0,
        'taken': None,
        'word': word,
        'size': 2,
    }
def c_bnez(word, **kwargs):
    # BEQZ performs conditional control transfers. The offset is
    # sign-extended and added to the pc to form the branch target address.
    # It can therefore target a ±256 B range. C.BEQZ takes the branch if
    # the value in register rs1' is zero. It expands to
    # beq rs1', x0, offset[8:1].
    return {
        'cmd': 'BNE',
        'imm': kwargs.get('imm'),
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': 0,
        'taken': None,
        'word': word,
        'size': 2,
    }
def c_mv(word):
    # C.MV copies the value in register rs2 into register rd. C.MV expands into add rd, x0, rs2;
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.106)
    return {
        'cmd': 'ADD',
        'rs1': 0,
        'rs2': compressed_rs2(word),
        'rd': compressed_rs1_or_rd(word),
        'word': word,
        'size': 2,
    }
def c_lui(word, **kwargs):
    # C.LUI loads the non-zero 6-bit immediate field into bits 17–12 of the
    # destination register, clears the bottom 12 bits, and sign-extends bit
    # 17 into all higher bits of the destination. C.LUI expands into
    # lui rd, nzimm[17:12]. C.LUI is only valid when rd̸={x0, x2}, and when
    # the immediate is not equal to zero.
    #
    # C.LUI nzimm[17] dest̸={0, 2} nzimm[16:12] C1
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.104)
    return {
        'cmd': 'LUI',
        'rd': compressed_rs1_or_rd(word),
        'imm': kwargs.get('imm'),
        'word': word,
        'size': 2,
    }
def c_ldsp(word):
    # C.LDSP is an RV64C/RV128C-only instruction that loads a 64-bit value from memory
    # into register rd. It computes its effective address by adding the zero-extended
    # offset, scaled by 8, to the stack pointer, x2. It expands to ld rd, offset[8:3](x2);
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.99)
    #
    # 011 uimm[5] rd̸=0 uimm[4:3|8:6] 10 C.LDSP (RV64/128; RES, rd=0);
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.111)
    _b080706 = (word >> 2) & 0b111
    _b0403   = (word >> 5) & 0b11
    _b05     = (word >> 12) & 0b1
    _imm = (_b080706 << 6) | (_b05 << 5) | (_b0403 << 3)
    return {
        'cmd': 'LD',
        'rs1': 2,
        'imm': _imm,
        'rd': compressed_rs1_or_rd(word),
        'nbytes': 8,
        'word': word,
        'size': 2,
    }
def c_lw(word, **kwargs):
    # C.LW loads a 32-bit value from memory into register rd ′. It computes
    # an effective address by adding the zero-extended offset, scaled by 4,
    # to the base address in register rs1 ′. It expands to
    # lw rd', offset[6:2](rs1').
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.101)
    return {
        'cmd': 'LW',
        'rs1': compressed_quadrant_00_rs1_prime(word),
        'imm': kwargs.get('imm'),
        'rd': compressed_quadrant_00_rs2_prime_or_rd_prime(word),
        'nbytes': 4,
        'word': word,
        'size': 2,
    }
def c_ld(word, **kwargs):
    # C.LD is an RV64C/RV128C-only instruction that loads a 64-bit value from memory
    # into register rd'. It computes an effective address by adding the zero-extended
    # offset, scaled by 8, to the base address in register rs1'. It expands to ld rd',
    # offset[7:3](rs1').
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.101)
    return {
        'cmd': 'LD',
        'rs1': compressed_quadrant_00_rs1_prime(word),
        'imm': kwargs.get('imm'),
        'rd': compressed_quadrant_00_rs2_prime_or_rd_prime(word),
        'nbytes': 8,
        'word': word,
        'size': 2,
    }
def c_sd(word, **kwargs):
    # C.SD is an RV64C/RV128C-only instruction that stores a 64-bit value in
    # register rs2' to memory. It computes an effective address by adding the
    # zero-extended offset, scaled by 8, to the base address in register rs1'.
    # It expands to sd rs2', offset[7:3](rs1')
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.102)
    return {
        'cmd': 'SD',
        'rs1': compressed_quadrant_00_rs1_prime(word),
        'rs2': compressed_quadrant_00_rs2_prime_or_rd_prime(word),
        'imm': kwargs.get('imm'),
        'nbytes': 8,
        'word': word,
        'size': 2,
    }
def c_sw(word, **kwargs):
    # C.SW stores a 32-bit value in register rs2' to memory. It computes an
    # effective address by adding the zero-extended offset, scaled by 4, to
    # the base address in register rs1'. It expands to sw rs2', offset[6:2](rs1')
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.102)
    return {
        'cmd': 'SW',
        'rs1': compressed_quadrant_00_rs1_prime(word),
        'rs2': compressed_quadrant_00_rs2_prime_or_rd_prime(word),
        'imm': kwargs.get('imm'),
        'nbytes': 4,
        'word': word,
        'size': 2,
    }
def c_addi4spn(word, **kwargs):
    # C.ADDI4SPN is a CIW-format instruction that adds a zero-extended non-zero
    # immediate, scaledby 4, to the stack pointer, x2, and writes the result to rd'.
    # This instruction is used to generate pointers to stack-allocated variables,
    # and expands to addi rd', x2, nzuimm[9:2].
    return {
        'cmd': 'ADDI',
        'imm': kwargs.get('imm'),
        'rs1': 2,
        'rd': compressed_quadrant_00_rs2_prime_or_rd_prime(word),
        'word': word,
        'size': 2,
    }
def c_addi16sp(word, **kwargs):
    # C.ADDI16SP is used to adjust the stack pointer in procedure prologues and
    # epilogues. It expands into addi x2, x2, nzimm[9:4]. C.ADDI16SP is only
    # valid when nzimm̸=0; the code point with nzimm=0 is reserved.
    return {
        'cmd': 'ADDI',
        'imm': kwargs.get('imm'),
        'rs1': 2,
        'rd': 2,
        'word': word,
        'size': 2,
    }
def c_sdsp(word, **kwargs):
    # C.SDSP is an RV64C/RV128C-only instruction that stores a 64-bit value in
    # register rs2 to memory. It computes an effective address by adding the
    # zero-extended offset, scaled by 8, to the stack pointer, x2. It expands to
    # sd rs2, offset[8:3](x2).
    return {
        'cmd': 'SD',
        'imm': kwargs.get('imm'),
        'rs1': 2,
        'rs2': compressed_rs2(word),
        'nbytes': 8,
        'word': word,
        'size': 2,
    }
def c_addi(word, **kwargs):
    # C.ADDI adds the non-zero sign-extended 6-bit immediate to the value in
    # register rd then writes the result to rd. C.ADDI expands into
    # addi rd, rd, nzimm[5:0]. C.ADDI is only valid when rd̸=x0. The code point
    # with both rd=x0 and nzimm=0 encodes the C.NOP instruction; the remaining
    # code points with either rd=x0 or nzimm=0 encode HINTs.
    return {
        'cmd': 'ADDI',
        'imm': kwargs.get('imm'),
        'rs1': compressed_rs1_or_rd(word),
        'rd': compressed_rs1_or_rd(word),
        'word': word,
        'size': 2,
    }
def c_addiw(word, **kwargs):
    # C.ADDIW is an RV64C/RV128C-only instruction that performs the same
    # computation but produces a 32-bit result, then sign-extends result to 64
    # bits. C.ADDIW expands into addiw rd, rd, imm[5:0]. The immediate can be
    # zero for C.ADDIW, where this corresponds to sext.w rd. C.ADDIW is only
    # valid when rd̸=x0; the code points with rd=x0 are reserved.
    return {
        'cmd': 'ADDIW',
        'imm': kwargs.get('imm'),
        'rs1': compressed_rs1_or_rd(word),
        'rd': compressed_rs1_or_rd(word),
        'word': word,
        'size': 2,
    }
def c_nop(word):
    return {
        'cmd': 'NOP',
        'word': word,
        'size': 2,
    }
def c_add(word):
    # C.ADD adds the values in registers rd and rs2 and writes the result to
    # register rd. C.ADD expands into add rd, rd, rs2. C.ADD is only valid when
    # rs2̸=x0; the code points with rs2=x0 correspond to the C.JALR and C.EBREAK
    # instructions. The code points with rs2̸=x0 and rd=x0 are HINTs.
    return {
        'cmd': 'ADD',
        'rs1': compressed_rs1_or_rd(word),
        'rs2': compressed_rs2(word),
        'rd': compressed_rs1_or_rd(word),
        'word': word,
        'size': 2,
    }
def c_sub(word):
    # C.SUB subtracts the value in register rs2 ′ from the value in register rd',
    # then writes the result to register rd ′. C.SUB expands into
    # sub rd', rd', rs2'.
    return {
        'cmd': 'SUB',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': compressed_quadrant_01_rs2_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'word': word,
        'size': 2,
    }
def c_xor(word):
    # C.XOR computes the bitwise XOR of the values in registers rd'
    # and rs2', then writes the result to register rd'. C.XOR expands
    # into xor rd', rd', rs2'.
    return {
        'cmd': 'XOR',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': compressed_quadrant_01_rs2_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'word': word,
        'size': 2,
    }
def c_or(word):
    # C.OR computes the bitwise OR of the values in registers rd'
    # and rs2', then writes the result to register rd'. C.OR expands
    # into or rd', rd', rs2'.
    return {
        'cmd': 'OR',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': compressed_quadrant_01_rs2_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'word': word,
        'size': 2,
    }
def c_and(word):
    # C.AND computes the bitwise AND of the values in registers rd'
    # and rs2', then writes the result to register rd'. C.AND expands
    # into and rd', rd', rs2'.
    return {
        'cmd': 'AND',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': compressed_quadrant_01_rs2_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'word': word,
        'size': 2,
    }
def c_subw(word):
    # C.SUBW is an RV64C/RV128C-only instruction that subtracts the value
    # in register rs2' from the value in register rd', then sign-extends
    # the lower 32 bits of the difference before writing the result to
    # register rd'. C.SUBW expands into subw rd', rd', rs2 ′.
    return {
        'cmd': 'SUBW',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': compressed_quadrant_01_rs2_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'word': word,
        'size': 2,
    }
def c_addw(word):
    # C.ADDW is an RV64C/RV128C-only instruction that adds the values
    # in registers rd' and rs2', then sign-extends the lower 32 bits of
    # the sum before writing the result to register rd'. C.ADDW
    # expands into addw rd', rd', rs2'
    return {
        'cmd': 'ADDW',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rs2': compressed_quadrant_01_rs2_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'word': word,
        'size': 2,
    }
def c_li(word, **kwargs):
    # C.LI loads the sign-extended 6-bit immediate, imm, into register rd. C.LI
    # expands into addi rd, x0, imm[5:0]. C.LI is only valid when rd̸=x0; the code
    # points with rd=x0 encode HINTs.
    return {
        'cmd': 'ADDI',
        'rs1': 0,
        'rd': compressed_rs1_or_rd(word),
        'imm': kwargs.get('imm'),
        'word': word,
        'size': 2,
    }
def c_slli(word, **kwargs):
    # C.SLLI is a CI-format instruction that performs a logical left shift
    # of the value in register rd then writes the result to rd. The shift
    # amount is encoded in the shamt field. For RV128C, a shift amount of
    # zero is used to encode a shift of 64. C.SLLI expands into
    # slli rd, rd, shamt[5:0], except for RV128C with shamt=0, which expands
    # to slli rd, rd, 64.
    return {
        'cmd': 'SLLI',
        'rs1': compressed_rs1_or_rd(word),
        'rd': compressed_rs1_or_rd(word),
        'shamt': kwargs.get('imm'),
        'word': word,
        'size': 2,
    }
def c_srli(word, **kwargs):
    # C.SRLI is a CB-format instruction that performs a logical right shift
    # of the value in register rd' then writes the result to rd'. The shift
    # amount is encoded in the shamt field. For RV128C, a shift amount of
    # zero is used to encode a shift of 64. Furthermore, the shift amount
    # is sign-extended for RV128C, and so the legal shift amounts are 1–31,
    # 64, and 96–127. C.SRLI expands into srli rd', rd', shamt[5:0], except
    # for RV128C with shamt=0, which expands to srli rd ′, rd ′, 64
    return {
        'cmd': 'SRLI',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'shamt': kwargs.get('imm'),
        'word': word,
        'size': 2,
    }
def c_srai(word, **kwargs):
    # C.SRAI is defined analogously to C.SRLI, but instead performs an
    # arithmetic right shift. C.SRAI expands to srai rd', rd', shamt[5:0].
    return {
        'cmd': 'SRAI',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'shamt': kwargs.get('imm'),
        'word': word,
        'size': 2,
    }
def c_andi(word, **kwargs):
    # C.ANDI is a CB-format instruction that computes the bitwise AND
    # of the value in register rd' and the sign-extended 6-bit immediate,
    # then writes the result to rd'. C.ANDI expands to andi rd', rd', imm[5:0].
    return {
        'cmd': 'ANDI',
        'rs1': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'rd': compressed_quadrant_01_rs1_prime_or_rd_prime(word),
        'imm': kwargs.get('imm'),
        'word': word,
        'size': 2,
    }
def c_ebreak(word, **kwargs):
    # Debuggers can use the C.EBREAK instruction, which expands to ebreak,
    # to cause control to be transferred back to the debugging environment.
    # C.EBREAK shares the opcode with the C.ADD instruction, but with rd
    # and rs2 both zero, thus can also use the CR format.
    return {
        'cmd': 'EBREAK',
        'word': word,
        'size': 2,
    }

def lui(word):
    # LUI (load upper immediate) is used to build 32-bit constants and
    # uses the U-type format. LUI places the U-immediate value in the top
    # 20 bits of the destination register rd, filling in the lowest 12
    # bits with zeros. ... The 32-bit result is sign-extended to 64 bits.
    _imm = uncompressed_imm32(word)
    _imm <<= 12
    _b31 = (_imm >> 31) & 0b1
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _imm)
    _imm = int.from_bytes(struct.Struct('<Q').pack(_imm), 'little', signed=True)
    return {
        'cmd': 'LUI',
        'imm': _imm,
        'rd': uncompressed_rd(word),
        'word': word,
        'size': 4,
    }
def auipc(word):
    # AUIPC (add upper immediate to pc) is used to build pc-relative
    # addresses and uses the U-type format. AUIPC forms a 32-bit offset
    # from the 20-bit U-immediate, filling in the lowest 12 bits with
    # zeros, adds this offset to the address of the AUIPC instruction,
    # then places the result in register rd.
    _imm = uncompressed_imm32(word)
    _imm <<= 12
    _b31 = (_imm >> 31) & 0b1
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _imm)
    _imm = int.from_bytes(struct.Struct('<Q').pack(_imm), 'little', signed=True)
    return {
        'cmd': 'AUIPC',
        'imm': _imm,
        'rd': uncompressed_rd(word),
        'word': word,
        'size': 4,
    }
def jal(word):
    return {
        'cmd': 'JAL',
        'imm': uncompressed_imm21(word, signed=True),
        'rd': uncompressed_rd(word),
        'word': word,
        'size': 4,
    }
def jalr(word):
    # The indirect jump instruction JALR (jump and link register) uses
    # the I-type encoding. The target address is obtained by adding the
    # sign-extended 12-bit I-immediate to the register rs1, then setting
    # the least-significant bit of the result to zero. The address of
    # the instruction following the jump (pc+4) is written to register
    # rd. Register x0 can be used as the destination if the result is
    # not required.
    # see: https://riscv.org/wp-content/uploads/2019/12/riscv-spec-20191213.pdf (p. 21)
    return {
        'cmd': 'JALR',
        'imm': uncompressed_i_type_imm12(word, signed=True),
        'rs1': uncompressed_rs1(word),
        'rd': uncompressed_rd(word),
        'word': word,
        'size': 4,
    }
def i_type(word):
    # imm[11:0]     rs1 000 rd 0010011 ADDI
    # imm[11:0]     rs1 010 rd 0010011 SLTI
    # imm[11:0]     rs1 011 rd 0010011 SLTIU
    # imm[11:0]     rs1 100 rd 0010011 XORI
    # imm[11:0]     rs1 110 rd 0010011 ORI
    # imm[11:0]     rs1 111 rd 0010011 ANDI
    # 0000000 shamt rs1 001 rd 0010011 SLLI
    # 0000000 shamt rs1 101 rd 0010011 SRLI
    # 0100000 shamt rs1 101 rd 0010011 SRAI
    # imm[11:0]     rs1 000 rd 0011011 ADDIW
    # 0000000 shamt rs1 001 rd 0011011 SLLIW
    # 0000000 shamt rs1 101 rd 0011011 SRLIW
    # 0100000 shamt rs1 101 rd 0011011 SRAIW
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.130)

    _cmds = {
        0b001_0011: {
            0b000: {'cmd': 'ADDI', 'imm': uncompressed_i_type_imm12(word, signed=True)},
            0b010: {'cmd': 'SLTI', 'imm': uncompressed_i_type_imm12(word, signed=True)},
            0b011: {'cmd': 'SLTIU', 'imm': int.from_bytes((uncompressed_i_type_imm12(word, signed=True) & ((2**64) - 1)).to_bytes(8, 'little'), 'little')},
            0b001: {'cmd': 'SLLI', 'shamt': uncompressed_i_type_shamt(word)},
            0b100: {'cmd': 'XORI', 'imm': uncompressed_i_type_imm12(word, signed=True)},
            0b110: {'cmd': 'ORI', 'imm': uncompressed_i_type_imm12(word, signed=True)},
            0b111: {'cmd': 'ANDI', 'imm': uncompressed_i_type_imm12(word, signed=True)},
            0b101: {'cmd': ('SRLI' if 0 == uncompressed_funct7(word) else 'SRAI'), 'shamt': uncompressed_i_type_shamt(word)},
            0b111: {'cmd': 'ANDI', 'imm': uncompressed_i_type_imm12(word, signed=True)},
        },
        0b001_1011: {
            0b000: {'cmd': 'ADDIW', 'imm': uncompressed_i_type_imm12(word, signed=True)},
            0b001: {'cmd': 'SLLIW', 'shamt': uncompressed_i_type_shamt(word)},
            0b101: {'cmd': ('SRLIW' if 0 == uncompressed_funct7(word) else 'SRAIW'), 'shamt': uncompressed_i_type_shamt(word)},
        }
    }.get(uncompressed_opcode(word), {})
    if not uncompressed_funct3(word) in _cmds.keys():
        return uncompressed_unimplemented_instruction(word)
    _retval = {
        **_cmds.get(uncompressed_funct3(word)),
        **{
            'rs1': uncompressed_rs1(word),
            'rd': uncompressed_rd(word),
            'word': word,
            'size': 4,
        },
    }
    return _retval
def r_type(word):
    # 0000000 rs2 rs1 000 rd 0110011 ADD
    # 0100000 rs2 rs1 000 rd 0110011 SUB
    # 0000000 rs2 rs1 001 rd 0110011 SLL
    # 0000000 rs2 rs1 010 rd 0110011 SLT
    # 0000000 rs2 rs1 011 rd 0110011 SLTU
    # 0000000 rs2 rs1 100 rd 0110011 XOR
    # 0000000 rs2 rs1 101 rd 0110011 SRL
    # 0100000 rs2 rs1 101 rd 0110011 SRA
    # 0000000 rs2 rs1 110 rd 0110011 OR
    # 0000000 rs2 rs1 111 rd 0110011 AND
    # 0000000 rs2 rs1 000 rd 0111011 ADDW
    # 0100000 rs2 rs1 000 rd 0111011 SUBW
    # 0000000 rs2 rs1 001 rd 0111011 SLLW
    # 0000000 rs2 rs1 101 rd 0111011 SRLW
    # 0100000 rs2 rs1 101 rd 0111011 SRAW
    # see: 
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.130, 131)
    _cmds = {
        (0b000_0000, 0b000, 0b011_0011): 'ADD',
        (0b010_0000, 0b000, 0b011_0011): 'SUB',
        (0b000_0000, 0b001, 0b011_0011): 'SLL',
        (0b000_0000, 0b010, 0b011_0011): 'SLT',
        (0b000_0000, 0b011, 0b011_0011): 'SLTU',
        (0b000_0000, 0b100, 0b011_0011): 'XOR',
        (0b000_0000, 0b101, 0b011_0011): 'SRL',
        (0b010_0000, 0b101, 0b011_0011): 'SRA',
        (0b000_0000, 0b110, 0b011_0011): 'OR',
        (0b000_0000, 0b111, 0b011_0011): 'AND',
        (0b000_0000, 0b000, 0b011_1011): 'ADDW',
        (0b010_0000, 0b000, 0b011_1011): 'SUBW',
        (0b000_0001, 0b000, 0b011_0011): 'MUL',
        (0b000_0001, 0b001, 0b011_0011): 'MULH',
        (0b000_0001, 0b010, 0b011_0011): 'MULHSU',
        (0b000_0001, 0b011, 0b011_0011): 'MULHU',
        (0b000_0001, 0b100, 0b011_0011): 'DIV',
        (0b000_0001, 0b101, 0b011_0011): 'DIVU',
        (0b000_0001, 0b110, 0b011_0011): 'REM',
        (0b000_0001, 0b111, 0b011_0011): 'REMU',
        (0b000_0001, 0b000, 0b011_1011): 'MULW',
        (0b000_0001, 0b100, 0b011_1011): 'DIVW',
        (0b000_0001, 0b101, 0b011_1011): 'DIVUW',
        (0b000_0001, 0b110, 0b011_1011): 'REMW',
        (0b000_0001, 0b111, 0b011_1011): 'REMUW',
    }
    _cmd = _cmds.get((uncompressed_funct7(word), uncompressed_funct3(word), uncompressed_opcode(word)), 'Undefined')
    return {
        'cmd': _cmd,
        'rs1': uncompressed_rs1(word),
        'rs2': uncompressed_rs2(word),
        'rd': uncompressed_rd(word),
        'word': word,
        'size': 4,
    }
def b_type(word):
    _cmds = {
        0b000: 'BEQ',
        0b001: 'BNE',
        0b100: 'BLT',
        0b101: 'BGE',
        0b110: 'BLTU',
        0b111: 'BGEU',
    }
    if not uncompressed_funct3(word) in _cmds.keys(): uncompressed_illegal_instruction(word)
    _cmd = _cmds.get(uncompressed_funct3(word))
    return {
        'cmd': _cmd,
        'rs1': uncompressed_rs1(word),
        'rs2': uncompressed_rs2(word),
        'imm': uncomprssed_b_type_imm13(word, signed=True),
        'taken': None,
        'word': word,
        'size': 4,
    }
def system(word):
    _cmds = {
        0b0000_0000_0000: 'ECALL',
        0b0000_0000_0001: 'EBREAK',
    }
    if not uncompressed_i_type_imm12(word) in _cmds.keys(): uncompressed_illegal_instruction(word)
    _cmd = _cmds.get(uncompressed_i_type_imm12(word))
    return {
        'cmd': _cmd,
        'word': word,
        'size': 4,
    }
def load(word):
    # imm[11:0] rs1 000 rd 0000011 LB
    # imm[11:0] rs1 001 rd 0000011 LH
    # imm[11:0] rs1 010 rd 0000011 LW
    # imm[11:0] rs1 011 rd 0000011 LD
    # imm[11:0] rs1 100 rd 0000011 LBU
    # imm[11:0] rs1 101 rd 0000011 LHU
    # imm[11:0] rs1 110 rd 0000011 LWU
    _variety = {
        0b000: {'cmd': 'LB', 'nbytes': 1},
        0b001: {'cmd': 'LH', 'nbytes': 2},
        0b010: {'cmd': 'LW', 'nbytes': 4},
        0b011: {'cmd': 'LD', 'nbytes': 8},
        0b100: {'cmd': 'LBU', 'nbytes': 1},
        0b101: {'cmd': 'LHU', 'nbytes': 2},
        0b110: {'cmd': 'LWU', 'nbytes': 4},
    }.get((word >> 12) & 0b111)
    return {
        **_variety,
        **{
            'imm': uncompressed_load_imm12(word, signed=True),
            'rs1': uncompressed_rs1(word),
            'rd': uncompressed_rd(word),
            'word': word,
            'size': 4,
        },
    }
def store(word):
    # imm[11:5] rs2 rs1 000 imm[4:0] 0100011 SB
    # imm[11:5] rs2 rs1 001 imm[4:0] 0100011 SH
    # imm[11:5] rs2 rs1 010 imm[4:0] 0100011 SW
    # imm[11:5] rs2 rs1 011 imm[4:0] 0100011 SD
    # see: https://riscv.org/wp-content/uploads/2019/12/riscv-spec-20191213.pdf (p. 130, 131)
    _variety = {
        0b000: {'cmd': 'SB', 'nbytes': 1},
        0b001: {'cmd': 'SH', 'nbytes': 2},
        0b010: {'cmd': 'SW', 'nbytes': 4},
        0b011: {'cmd': 'SD', 'nbytes': 8},
    }.get(uncompressed_funct3(word))
    return {
        **_variety,
        **{
            'imm': uncompressed_store_imm12(word, signed=True), 
            'rs1': uncompressed_rs1(word),
            'rs2': uncompressed_rs2(word),
            'word': word,
            'size': 4,
        },
    }
def atomic(word):
    # 00010 aq rl 00000 rs1 010 rd 0101111 LR.W
    # 00010 aq rl 00000 rs1 011 rd 0101111 LR.D
    # 00011 aq rl rs2   rs1 010 rd 0101111 SC.W
    # 00011 aq rl rs2   rs1 011 rd 0101111 SC.D
    # 00001 aq rl rs2   rs1 010 rd 0101111 AMOSWAP.W
    # 00000 aq rl rs2   rs1 010 rd 0101111 AMOADD.W
    # 00100 aq rl rs2   rs1 010 rd 0101111 AMOXOR.W
    # 01100 aq rl rs2   rs1 010 rd 0101111 AMOAND.W
    # 01000 aq rl rs2   rs1 010 rd 0101111 AMOOR.W
    # 10000 aq rl rs2   rs1 010 rd 0101111 AMOMIN.W
    # 10100 aq rl rs2   rs1 010 rd 0101111 AMOMAX.W
    # 11000 aq rl rs2   rs1 010 rd 0101111 AMOMINU.W
    # 11100 aq rl rs2   rs1 010 rd 0101111 AMOMAXU.W
    # 00001 aq rl rs2   rs1 011 rd 0101111 AMOSWAP.D
    # 00000 aq rl rs2   rs1 011 rd 0101111 AMOADD.D
    # 00100 aq rl rs2   rs1 011 rd 0101111 AMOXOR.D
    # 01100 aq rl rs2   rs1 011 rd 0101111 AMOAND.D
    # 01000 aq rl rs2   rs1 011 rd 0101111 AMOOR.D
    # 10000 aq rl rs2   rs1 011 rd 0101111 AMOMIN.D
    # 10100 aq rl rs2   rs1 011 rd 0101111 AMOMAX.D
    # 11000 aq rl rs2   rs1 011 rd 0101111 AMOMINU.D
    # 11100 aq rl rs2   rs1 011 rd 0101111 AMOMAXU.D
    # see: https://riscv.org/wp-content/uploads/2019/12/riscv-spec-20191213.pdf (p. 132)
    _variety = {
        (0b0_0010, 0b010): {'cmd': 'LR.W', 'nbytes': 4},
        (0b0_0010, 0b011): {'cmd': 'LR.D', 'nbytes': 8},
        (0b0_0011, 0b010): {'cmd': 'SC.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_0011, 0b011): {'cmd': 'SC.D', 'nbytes': 8, 'rs2': uncompressed_rs2(word)},
        (0b0_0001, 0b010): {'cmd': 'AMOSWAP.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_0000, 0b010): {'cmd': 'AMOADD.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_0100, 0b010): {'cmd': 'AMOXOR.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_1100, 0b010): {'cmd': 'AMOAND.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_1000, 0b010): {'cmd': 'AMOOR.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_0000, 0b010): {'cmd': 'AMOMIN.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_0100, 0b010): {'cmd': 'AMOMAX.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_1000, 0b010): {'cmd': 'AMOMINU.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_1100, 0b010): {'cmd': 'AMOMAXU.W', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_0001, 0b011): {'cmd': 'AMOSWAP.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_0000, 0b011): {'cmd': 'AMOADD.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_0100, 0b011): {'cmd': 'AMOXOR.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_1100, 0b011): {'cmd': 'AMOAND.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b0_1000, 0b011): {'cmd': 'AMOOR.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_0000, 0b011): {'cmd': 'AMOMIN.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_0100, 0b011): {'cmd': 'AMOMAX.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_1000, 0b011): {'cmd': 'AMOMINU.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
        (0b1_1100, 0b011): {'cmd': 'AMOMAXU.D', 'nbytes': 4, 'rs2': uncompressed_rs2(word)},
    }.get((uncompressed_funct5(word), uncompressed_funct3(word)))
    return {
        **_variety,
        **{
            'imm': 0,
            'rd': uncompressed_rd(word),
            'rs1': uncompressed_rs1(word),
            'aq': (1 == (word >> 26) & 0b1),
            'rl': (1 == (word >> 25) & 0b1),
            'word': word,
            'size': 4,
        },
    }
def fence(word):
    return {
        'cmd': 'FENCE',
        'word': word,
        'size': 4,
    }





def compressed_illegal_instruction(word, **kwargs):
    assert False, 'Illegal instruction ({:04x})!'.format(word)
def decode_compressed(word):
#    print('decode_compressed({:04x})'.format(word))
    return {
        0b00: compressed_quadrant_00,
        0b01: compressed_quadrant_01,
        0b10: compressed_quadrant_10,
    }.get(compressed_quadrant(word), compressed_unimplemented_instruction)(word)
def compressed_quadrant(word):
#    print('compressed_quadrant({:04x})'.format(word))
    return word & 0b11

def compressed_quadrant_00(word):
    return {
        0b000: compressed_quadrant_00_opcode_000,
        0b010: compressed_quadrant_00_opcode_010,
        0b011: compressed_quadrant_00_opcode_011,
        0b110: compressed_quadrant_00_opcode_110,
        0b111: compressed_quadrant_00_opcode_111,
    }.get(compressed_opcode(word), compressed_unimplemented_instruction)(word)
def compressed_quadrant_00_opcode_000(word):
    # 00 nzuimm[5:4|9:6|2|3] rd' 00 ; C.ADDI4SPN (RES, nzuimm=0)
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.110)
    _impl = compressed_unimplemented_instruction
    _b03       = (word >> 5) & 0b1
    _b02       = (word >> 6) & 0b1
    _b09080706 = (word >> 7) & 0b1111
    _b0504     = (word >> 11) & 0b11
    _imm = (_b09080706 << 6) | (_b0504 << 4) | (_b03 << 3) | (_b02 << 2)
    if 0 == _imm:
        _impl = compressed_illegal_instruction
    else:
        _impl = c_addi4spn
    return _impl(word, imm=_imm)
def compressed_quadrant_00_opcode_010(word):
    # 010 uimm[5:3] rs1' uimm[2|6] rd' 00 C.LW
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.110)
    _impl = c_lw
    _b06     = (word >> 5) & 0b1
    _b02     = (word >> 6) & 0b1
    _b050403 = (word >> 9) & 0b111
    _imm = (_b06 << 6) | (_b050403 << 3) | (_b02 << 2)
    return _impl(word, imm=_imm)
def compressed_quadrant_00_opcode_011(word):
    # 011 uimm[5:3] rs1 ′ uimm[7:6] rd ′ 00 C.LD (RV64/128)
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.110)
    _impl = c_ld
    _b0706   = (word >> 5) & 0b11
    _b050403 = (word >> 10) & 0b111
    _imm = (_b0706 << 6) | (_b050403 << 3)
    return _impl(word, imm=_imm)
def compressed_quadrant_00_opcode_110(word):
    # 110 uimm[5:3] rs1' uimm[2|6] rs2' 00 C.SW
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.110)
    _impl = c_sw
    _b06 = (word >> 5) & 0b1
    _b02 = (word >> 6) & 0b1
    _b050403 = (word >> 10) & 0b111
    _imm = (_b06 << 6) | (_b050403 << 3) | (_b02 << 2)
    return _impl(word, imm=_imm)
def compressed_quadrant_00_opcode_111(word):
    # 111 uimm[5:3] rs1' uimm[7:6] rs2' 00 C.SD (RV64/128)
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.110)
    _impl = c_sd
    _b0706 = (word >> 5) & 0b11
    _b050403 = (word >> 10) & 0b111
    _imm = (_b0706 << 6) | (_b050403 << 3)
    return _impl(word, imm=_imm)
def compressed_quadrant_00_rs1_prime(word):
    # RVC     Register Number          000 001 010 011 100 101 110 111
    # Integer Register Number           x8  x9 x10 x11 x12 x13 x14 x15
    # Integer Register ABI Name         s0  s1  a0  a1  a2  a3  a4  a5
    # Floating-Point Register Number    f8  f9 f10 f11 f12 f13 f14 f15
    # Floating-Point Register ABI Name fs0 fs1 fa0 fa1 fa2 fa3 fa4 fa5
    # Table 16.2: Registers specified by the three-bit rs1 ′, rs2 ′, and rd ′ fields of the CIW, CL, CS, CA,
    # and CB formats; see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.98)
    #
    # see also: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return 8 + ((word >> 7) & 0b111)
def compressed_quadrant_00_rs2_prime_or_rd_prime(word):
    return 8 + ((word >> 2) & 0b111)

def compressed_quadrant_01(word):
    return {
        0b000: compressed_quadrant_01_opcode_000,
        0b001: compressed_quadrant_01_opcode_001,
        0b010: compressed_quadrant_01_opcode_010,
        0b011: compressed_quadrant_01_opcode_011,
        0b100: compressed_quadrant_01_opcode_100,
        0b101: compressed_quadrant_01_opcode_101,
        0b110: compressed_quadrant_01_opcode_110,
        0b111: compressed_quadrant_01_opcode_111,
    }.get(compressed_opcode(word), compressed_unimplemented_instruction)(word)
def compressed_quadrant_01_opcode_000(word):
    # 000 nzimm[5] rs1/rd̸=0 nzimm[4:0] 01 C.ADDI (HINT, nzimm=0) (p.111)
    _impl = compressed_unimplemented_instruction
    _b05         = (word >> 12) & 0b1
    _b0403020100 = (word >> 2) & 0b1_1111
    _imm = (_b05 << 5) | (_b0403020100)
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b05 << x, range(6, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    if 0 != compressed_rs1_or_rd(word):
        _impl = c_addi
    else:
        _impl = c_nop
    return _impl(word, imm=_imm)
def compressed_quadrant_01_opcode_001(word):
    # 001 imm[5] rs1/rd̸ =0 imm[4:0] 01 C.ADDIW (RV64/128; RES, rd=0)
    _impl = compressed_unimplemented_instruction
    if 0 != compressed_rs1_or_rd(word):
        _impl = c_addiw
        _b05         = (word >> 12) & 0b1
        _b0403020100 = (word >> 2) & 0b1_1111
        _imm = (_b05 << 5) | (_b0403020100)
        _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b05 << x, range(6, 16)), _imm)
        _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    else:
        _imm = None
    return _impl(word, imm=_imm)
def compressed_quadrant_01_opcode_010(word):
    # 010 imm[5] rd̸=0 imm[4:0] 01 C.LI (HINT, rd=0)
    _impl = compressed_unimplemented_instruction
    _b0403020100 = (word >> 2) & 0b1_1111
    _b05         = (word >> 12) & 0b1
    _imm = (_b05 << 5) | _b0403020100
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b05 << x, range(6, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    if 0 == compressed_rs1_or_rd(word):
        _impl = compressed_illegal_instruction
    else:
        _impl = c_li
    return _impl(word, imm=_imm)
def compressed_quadrant_01_opcode_011(word):
    # 011 nzimm[9] 2 nzimm[4|6|8:7|5] 01 C.ADDI16SP (RES, nzimm=0) (p.111)
    # 011 nzimm[17] rd̸={0, 2} nzimm[16:12] 01 C.LUI (RES, nzimm=0; HINT, rd=0)
    _impl = compressed_unimplemented_instruction
    if 2 == compressed_rs1_or_rd(word):
        _b05 = (word >> 2) & 0b1
        _b0807 = (word >> 3) & 0b11
        _b06 = (word >> 5) & 0b1
        _b04 = (word >> 6) & 0b1
        _b09 = (word >> 12) & 0b1
        _imm = (_b09 << 9) | (_b0807 << 7) | (_b06 << 6) | (_b05 << 5) | (_b04 << 4)
        _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b09 << x, range(10, 16)), _imm)
        _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
        if 0 == _imm:
            _impl = compressed_illegal_instruction
        else:
            _impl = c_addi16sp
    else:
        _b17         = (word >> 12) & 0b1
        _b1615141312 = (word >> 2) & 0b1_1111
        _imm = (_b17 << 17) | (_b1615141312 << 12)
        if 0 == _imm:
            _impl = compressed_illegal_instruction
        else:
            _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b17 << x, range(18, 32)), _imm)
            _imm = int.from_bytes(struct.Struct('<I').pack(_imm), 'little', signed=True)
            _impl = c_lui
    return _impl(word, imm=_imm)
def compressed_quadrant_01_opcode_100(word):
    # 100 nzuimm[5] 00 rs1 ′/rd ′ nzuimm[4:0] 01 C.SRLI (RV32 NSE, nzuimm[5]=1)
    # 100 0 00 rs1 ′/rd ′ 0 01 C.SRLI64 (RV128; RV32/64 HINT)
    # 100 nzuimm[5] 01 rs1 ′/rd ′ nzuimm[4:0] 01 C.SRAI (RV32 NSE, nzuimm[5]=1)
    # 100 0 01 rs1 ′/rd ′ 0 01 C.SRAI64 (RV128; RV32/64 HINT)
    # 100 imm[5] 10 rs1 ′/rd ′ imm[4:0] 01 C.ANDI
    # 100 0 11 rs1 ′/rd ′ 00 rs2 ′ 01 C.SUB
    # 100 0 11 rs1 ′/rd ′ 01 rs2 ′ 01 C.XOR
    # 100 0 11 rs1 ′/rd ′ 10 rs2 ′ 01 C.OR
    # 100 0 11 rs1 ′/rd ′ 11 rs2 ′ 01 C.AND
    # 100 1 11 rs1 ′/rd ′ 00 rs2 ′ 01 C.SUBW (RV64/128; RV32 RES)
    # 100 1 11 rs1 ′/rd ′ 01 rs2 ′ 01 C.ADDW (RV64/128; RV32 RES)
    # 100 1 11 — 10 — 01 Reserved
    # 100 1 11 — 11 — 01 Reserved
    _impl = compressed_unimplemented_instruction
    _imm = None
    _b12   = (word >> 12) & 0b1
    _b1110 = (word >> 10) & 0b11
    _b0605 = (word >> 5) & 0b11
    if 0b00 == _b1110:
        _impl = c_srli
        _imm = (_b12 << 5) | (word >> 2) & 0b1_1111
    elif 0b01 == _b1110:
        _impl = c_srai
        _imm = (_b12 << 5) | (word >> 2) & 0b1_1111
    elif 0b10 == _b1110:
        _impl = c_andi
        _imm = int.from_bytes([(_b12 << 7) | (_b12 << 6) | (_b12 << 5) | (word >> 2) & 0b1_1111], 'little', signed=True)
    elif 0b11 == _b1110:
        if 0b0 == _b12:
            _impl = {
                0b00: c_sub,
                0b01: c_xor,
                0b10: c_or,
                0b11: c_and,
            }.get(_b0605)
        else:
            _impl = {
                0b00: c_subw,
                0b01: c_addw,
            }.get(_b0605)
    return (_impl(word, imm=_imm) if _imm else _impl(word))

def compressed_quadrant_01_opcode_101(word):
    # 101 imm[11|4|9:8|10|6|7|3:1|5] 01 C.J
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.111)
    _impl = c_j
    _b05     = (word >> 2) & 0b1
    _b030201 = (word >> 3) & 0b111
    _b07     = (word >> 6) & 0b1
    _b06     = (word >> 7) & 0b1
    _b10     = (word >> 8) & 0b1
    _b0908   = (word >> 9) & 0b11
    _b04     = (word >> 11) & 0b1
    _b11     = (word >> 12) & 0b1
    _imm = (_b11 << 11) | (_b10 << 10) | (_b0908 << 8) | (_b07 << 7) | (_b06 << 6) | (_b05 << 5) | (_b04 << 4) | (_b030201 << 1)
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b11 << x, range(12, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    return _impl(word, imm=_imm)
def compressed_quadrant_01_opcode_110(word):
    # 110 imm[8|4:3] rs1 ′ imm[7:6|2:1|5] 01 C.BEQZ
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.111)
    _impl = c_beqz
    _b05   = (word >> 2) & 0b1
    _b0201 = (word >> 3) & 0b11
    _b0706 = (word >> 5) & 0b11
    _b0403 = (word >> 10) & 0b11
    _b08   = (word >> 12) & 0b1
    _imm = (_b08 << 8) | (_b0706 << 6) | (_b05 << 5) | (_b0403 << 3) | (_b0201 << 1)
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b08 << x, range(9, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    return _impl(word, imm=_imm)
def compressed_quadrant_01_opcode_111(word):
    # 111 imm[8|4:3] rs1 ′ imm[7:6|2:1|5] 01 C.BNEZ
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.111)
    _impl = c_bnez
    _b05   = (word >> 2) & 0b1
    _b0201 = (word >> 3) & 0b11
    _b0706 = (word >> 5) & 0b11
    _b0403 = (word >> 10) & 0b11
    _b08   = (word >> 12) & 0b1
    _imm = (_b08 << 8) | (_b0706 << 6) | (_b05 << 5) | (_b0403 << 3) | (_b0201 << 1)
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b08 << x, range(9, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    return _impl(word, imm=_imm)
def compressed_quadrant_01_rs1_prime_or_rd_prime(word):
    # RVC     Register Number          000 001 010 011 100 101 110 111
    # Integer Register Number           x8  x9 x10 x11 x12 x13 x14 x15
    # Integer Register ABI Name         s0  s1  a0  a1  a2  a3  a4  a5
    # Floating-Point Register Number    f8  f9 f10 f11 f12 f13 f14 f15
    # Floating-Point Register ABI Name fs0 fs1 fa0 fa1 fa2 fa3 fa4 fa5
    # Table 16.2: Registers specified by the three-bit rs1 ′, rs2 ′, and rd ′ fields of the CIW, CL, CS, CA,
    # and CB formats; see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.98)
    #
    # see also: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return 8 + ((word >> 7) & 0b111)
def compressed_quadrant_01_rs2_prime(word):
    return 8 + ((word >> 2) & 0b111)

def compressed_quadrant_10(word):
#    print('compressed_quadrant_10({:04x})'.format(word))
    return {
        0b000: compressed_quadrant_10_opcode_000,
        0b011: compressed_quadrant_10_opcode_011,
        0b100: compressed_quadrant_10_opcode_100,
        0b111: compressed_quadrant_10_opcode_111,
    }.get(compressed_opcode(word), compressed_unimplemented_instruction)(word)
def compressed_quadrant_10_opcode_000(word):
    # 000 nzuimm[5] rs1/rd̸=0 nzuimm[4:0] 10 C.SLLI (HINT, rd=0; RV32 NSE, nzuimm[5]=1)
    _impl = compressed_unimplemented_instruction
    if 0 == compressed_rs1_or_rd(word):
        pass
        _imm = None
    else:
        _b05         = (word >> 12) & 0b1
        _b0403020100 = (word >> 2) & 0b1_1111
        _imm = (_b05 << 5) | _b0403020100
        _impl = c_slli
    return _impl(word, imm=_imm)
def compressed_quadrant_10_opcode_011(word):
    _impl = compressed_unimplemented_instruction
    if 0 == compressed_rs1_or_rd(word):
        pass
    else:
        _impl = c_ldsp
    return _impl(word)
def compressed_quadrant_10_opcode_100(word):
#    print('compressed_quadrant_10_opcode_100()')
    # 100 0 rs1̸=0    0       10 C.JR (RES, rs1=0)
    # 100 0 rd̸=0     rs2̸=0  10 C.MV (HINT, rd=0)
    # 100 1 0         0       10 C.EBREAK
    # 100 1 rs1̸=0    0       10 C.JALR
    # 100 1 rs1/rd̸=0 rs2̸=0  10 C.ADD (HINT, rd=0)
    #
    # See: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    _impl = compressed_unimplemented_instruction
    _b12 = (word >> 12) & 0b1
    if 0 == _b12:
        if 0 != compressed_rs1_or_rd(word):
            if 0 == compressed_rs2(word):
                _impl = c_jr
            else:
                _impl = c_mv
    else:
        if 0 == compressed_rs1_or_rd(word):
            _impl = c_ebreak
        else:
            if 0 != compressed_rs2(word):
                _impl = c_add
            else:
                _impl = c_jalr
    return _impl(word)
def compressed_quadrant_10_opcode_111(word):
    # 111 uimm[5:3|8:6] rs2 10 C.SDSP (RV64/128
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.111)
    _impl = c_sdsp
    _b080706 = (word >> 7) & 0b111
    _b050403 = (word >> 10) & 0b111
    _imm = (_b080706 << 6) | (_b050403 << 3)
    return _impl(word, imm=_imm)


def compressed_opcode(word):
#    print('compressed_opcode({:04x}): -> {}'.format(word, (word & 0b1110_0000_0000_0000) >> 13))
    return (word & 0b1110_0000_0000_0000) >> 13
def compressed_rs1_or_rd(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return (word >> 7) & 0b1_1111
def compressed_rs2(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return (word >> 2) & 0b1_1111
#def compressed_rs1_prime_or_rd_prime(word):
#    # RVC     Register Number          000 001 010 011 100 101 110 111
#    # Integer Register Number           x8  x9 x10 x11 x12 x13 x14 x15
#    # Integer Register ABI Name         s0  s1  a0  a1  a2  a3  a4  a5
#    # Floating-Point Register Number    f8  f9 f10 f11 f12 f13 f14 f15
#    # Floating-Point Register ABI Name fs0 fs1 fa0 fa1 fa2 fa3 fa4 fa5
#    # Table 16.2: Registers specified by the three-bit rs1 ′, rs2 ′, and rd ′ fields of the CIW, CL, CS, CA,
#    # and CB formats; see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.98)
#    # see also: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
#    return (word >> 7) & 0b111
#def compressed_rs2_prime(word):
#    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
#    return (word >> 2) & 0b111

def compressed_imm6(word, **kwargs):
    # nzimm[5] 00000 nzimm[4:0]
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    _b05         = (word & 0b1_0000_0000_0000) >> 12
    _b0403020100 = (word & 0b111_1100) >> 2
    _retval  = _b05 << 5
    _retval |= _b0403020100
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b05 << x, range(6, 8)), _retval)
    return int.from_bytes(struct.Struct('<B').pack(_retval), 'little', **kwargs)
def compressed_imm10(word, **kwargs):
    # nzimm[9] 00010 nzimm[4|6|8:7|5]
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    _tmp = (word >> 2) & 0b111_1111_1111
    _b05   = (_tmp & 0b1) >> 0
    _b0807 = (_tmp & 0b110) >> 1
    _b06   = (_tmp & 0b1000) >> 3
    _b04   = (_tmp & 0b1_0000) >> 4
    _b09   = (_tmp & 0b100_0000_0000) >> 10
    _retval  = _b09 << 9
    _retval |= _b0807 << 7
    _retval |= _b06 << 6
    _retval |= _b05 << 5
    _retval |= _b04 << 4
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b09 << x, range(10, 16)), _retval)
    return int.from_bytes(struct.Struct('<H').pack(_retval), 'little', **kwargs)
def compressed_imm12(word, **kwargs):
    # imm[11|4|9:8|10|6|7|3:1|5]
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf, (p. 111)
    _tmp = (word & 0b0001_1111_1111_1100) >> 2
    _b05     = (_tmp & 0b1) >> 0
    _b030201 = (_tmp & 0b1110) >> 1
    _b07     = (_tmp & 0b1_0000) >> 4
    _b06     = (_tmp & 0b10_0000) >> 5
    _b10     = (_tmp & 0b100_0000) >> 6
    _b0908   = (_tmp & 0b1_1000_0000) >> 7
    _b04     = (_tmp & 0b10_0000_0000) >> 9
    _b11     = (_tmp & 0b100_0000_0000) >> 10
    _retval  = _b11 << 11
    _retval |= _b10 << 10
    _retval |= _b0908 << 8
    _retval |= _b07 << 7
    _retval |= _b06 << 6
    _retval |= _b05 << 5
    _retval |= _b04 << 4
    _retval |= _b030201 << 3
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b11 << x, range(12, 16)), _retval)
    return int.from_bytes(struct.Struct('<H').pack(_retval), 'little', **kwargs)





def uncompressed_illegal_instruction(word, **kwargs):
    assert False, 'Illegal instruction ({:08x})!'.format(word)
def decode_uncompressed(word):
    return {
        0b000_0011: load,
        0b000_1111: fence,
        0b011_0111: lui,
        0b001_0111: auipc,
        0b110_1111: jal,
        0b110_0111: jalr,
        0b010_0011: store,
        0b010_1111: atomic,
        0b001_0011: i_type,
        0b001_1011: i_type,
        0b011_1011: r_type,
        0b011_0011: r_type,
        0b110_0011: b_type,
        0b111_0011: system,
    }.get(uncompressed_opcode(word), uncompressed_unimplemented_instruction)(word)

def uncompressed_opcode(word):
    return (word & 0b111_1111)
def uncompressed_rs1(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    return (word >> 15) & 0b1_1111
def uncompressed_rs2(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    return (word >> 20) & 0b1_1111
def uncompressed_rd(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    return (word >> 7) & 0b1_1111

def uncompressed_i_type_imm12(word, **kwargs):
    # imm[11:0] rs1 funct3 rd opcode I-type
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _tmp = (word >> 20) & 0b1111_1111_1111
    _b11 = (_tmp & 0b1000_0000_0000) >> 11
    _retval = _tmp
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b11 << x, range(12, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncompressed_imm21(word, **kwargs):
    # imm[20|10:1|11|19:12] rrrrr ooooooo
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _b1918171615141312     = (word >> 12) & 0b1111_1111
    _b11                   = (word >> 20) & 0b1
    _b10090807060504030201 = (word >> 21) & 0b11_1111_1111
    _b20                   = (word >> 31) & 0b1
    _retval  = _b20 << 20
    _retval |= _b1918171615141312 << 12
    _retval |= _b11 << 11
    _retval |= _b10090807060504030201 << 1
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b20 << x, range(21, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncompressed_imm32(word, **kwargs):
    # imm[31:12] rrrrr ooooooo
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
#    _retval = word & 0b1111_1111_1111_1111_1111_0000_0000_0000
#    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
#    return int.from_bytes(_retval.to_bytes(4, 'little'), 'little', **kwargs)
    return (word >> 12) & 0b1111_1111_1111_1111_1111
def uncompressed_funct7(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 16)
    return (word >> 25) & 0b111_1111
def uncompressed_funct5(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 48)
    return (word >> 27) & 0b1_1111
def uncompressed_funct3(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 16)
    return (word >> 12) & 0b111
def uncompressed_i_type_shamt(word):
    return (word >> 20) & 0b11_1111
def uncompressed_load_imm12(word, **kwargs):
    # imm[11:0] rs1 011 rd 0000011 LD
    _b11 = (word >> 31) & 0b1
    _retval = (word >> 20) & 0b1111_1111_1111
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b11 << x, range(12, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncompressed_store_imm12(word, **kwargs):
    # imm[11:5] rs2 rs1 011 imm[4:0] 0100011 SD
    _b0403020100   = (word >> 7) & 0b1_1111
    _b100908070605 = (word >> 25) & 0b111_1111
    _b11           = (word >> 31) & 0b1
    _retval  = _b11 << 11
    _retval |= _b100908070605 << 5
    _retval |= _b0403020100
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b11 << x, range(12, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncomprssed_b_type_imm13(word, **kwargs):
    # imm[12|10:5] rs2 rs1 000 imm[4:1|11] 1100011 BEQ
    # imm[12|10:5] rs2 rs1 001 imm[4:1|11] 1100011 BNE
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _b11           = (word >> 7) & 0b1
    _b04030201     = (word >> 8) & 0b1111
    _b100908070605 = (word >> 25) & 0b11_1111
    _b12           = (word >> 31) & 0b1
    _retval  = _b12 << 12
    _retval |= _b11 << 11
    _retval |= _b100908070605 << 5
    _retval |= _b04030201 << 1
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b12 << x, range(13, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)





def do_decode(buffer, max_insns):
    if len(buffer) and 0 == int.from_bytes(buffer[:2], 'little'):
        # FIXME: popping these two here feels... inelegant, somehow
        # I would rather this happen in the decoder logic, but this
        # works for now
        buffer.pop(0)
        buffer.pop(0)
        return []
    _retval = []
    x = 0
    while max_insns > len(_retval) and len(buffer[x:4 + x]):
        _word = int.from_bytes(buffer[x:4 + x], 'little')
        if 0x3 == _word & 0x3:
            if 4 > len(buffer): break
            _retval.append(decode_uncompressed(_word))
            x += 4
        else:
            _word &= 0xffff
            _retval.append(decode_compressed(_word))
            x += 2
    return _retval
