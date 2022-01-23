import functools
import struct

from psutil import CONN_LISTEN

def compressed_unimplemented_instruction(word):
    return {
        'cmd': 'Undefined',
        'word': word,
        'size': 2,
    }
def uncompressed_unimplemented_instruction(word):
    return {
        'cmd': 'Undefined',
        'word': word,
        'size': 4,
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
def c_beqz(word, **kwargs):
    # BEQZ performs conditional control transfers. The offset is
    # sign-extended and added to the pc to form the branch target address.
    # It can therefore target a ±256 B range. C.BEQZ takes the branch if
    # the value in register rs1' is zero. It expands to
    # beq rs1', x0, offset[8:1].
    return {
        'cmd': 'BEQ',
        'imm': kwargs.get('imm'),
        'rs1': compressed_rs1_prime_or_rd_prime(word),
        'rs2': 0,
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
        'cmd': 'BEQ',
        'imm': kwargs.get('imm'),
        'rs1': compressed_rs1_prime_or_rd_prime(word),
        'rs2': 0,
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
def c_ldsp(word):
    # C.LDSP is an RV64C/RV128C-only instruction that loads a 64-bit value from memory
    # into register rd. It computes its effective address by adding the zero-extended
    # offset, scaled by 8, to the stack pointer, x2. It expands to ld rd, offset[8:3](x2);
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.99)
    #
    # 011 uimm[5] rd̸=0 uimm[4:3|8:6] 10 C.LDSP (RV64/128; RES, rd=0);
    # see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.111)
    _b0403   = (word >> 5) & 0b11
    _b080706 = (word >> 2) & 0b111
    _imm = ((_b080706 << 3) | _b0403) << 3
    return {
        'cmd': 'LD',
        'rs1': 2,
        'imm': _imm,
        'rd': compressed_rs1_or_rd(word),
        'nbytes': 8,
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
        'rs1': compressed_rs1_prime_or_rd_prime(word),
        'imm': kwargs.get('imm'),
        'rd': compressed_rs1_prime_or_rd_prime(word),
        'nbytes': 8,
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
        'rd': compressed_rs1_prime_or_rd_prime(word),
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

def lui(word):
    return {
        'cmd': 'LUI',
        'imm': uncompressed_imm32(word, signed=True),
        'rd': uncompressed_rd(word),
        'word': word,
        'size': 4,
    }
def auipc(word):
    return {
        'cmd': 'AUIPC',
        'imm': uncompressed_imm32(word, signed=True),
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
def i_type(word):
    _cmds = {
        0b000: 'ADDI',
        0b001: 'SLLI',
        0b111: 'ANDI',
    }
    if not uncompressed_funct3(word) in _cmds.keys():
        return uncompressed_unimplemented_instruction(word)
    elif 0b001 == uncompressed_funct3(word):
        return {
            'cmd': _cmds.get(uncompressed_funct3(word)),
            'shamt': uncompressed_i_type_shamt(word),
            'rs1': uncompressed_rs1(word),
            'rd': uncompressed_rd(word),
            'word': word,
            'size': 4,
        }
    else:
        return {
            'cmd': _cmds.get(uncompressed_funct3(word)),
            'imm': uncompressed_i_type_imm12(word, signed=True),
            'rs1': uncompressed_rs1(word),
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
        'imm': uncomprssed_b_type_imm13(word, signed=(False if _cmd.endswith('U') else True)),
        'word': word,
        'size': 4,
    }
def store(word):
    return {
        'cmd': 'SD',
        'imm': uncompressed_store_imm12(word, signed=True), 
        'rs1': uncompressed_rs1(word),
        'rs2': uncompressed_rs2(word),
        'nbytes': 8,
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
        0b011: compressed_quadrant_00_opcode_011,
    }.get(compressed_opcode(word), compressed_unimplemented_instruction)(word)
def compressed_quadrant_00_opcode_000(word):
    # 00 nzuimm[5:4|9:6|2|3] rd ′ 00 ; C.ADDI4SPN (RES, nzuimm=0)
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.110)
    _impl = compressed_unimplemented_instruction
    _b03       = (word >> 5) * 0b1
    _b02       = (word >> 6) & 0b1
    _b09080706 = (word >> 7) & 0b1111
    _b0504     = (word >> 11) & 0b11
    _imm = (_b09080706 << 6) | (_b0504 << 4) | (_b03 << 3) | (_b02 << 2)
    if 0 == _imm:
        _impl = compressed_illegal_instruction
    else:
        _impl = c_addi4spn
    return _impl(word, imm=_imm)
def compressed_quadrant_00_opcode_011(word):
    # 011 uimm[5:3] rs1 ′ uimm[7:6] rd ′ 00 C.LD (RV64/128)
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p.110)
    _impl = c_ld
    _b0706   = (word >> 5) & 0b11
    _b050403 = (word >> 8) & 0b111
    _imm = (_b0706 << 6) | (_b050403 << 3)
    return _impl(word, imm=_imm)

def compressed_quadrant_01(word):
    return {
        0b000: compressed_quadrant_01_opcode_000,
        0b010: compressed_quadrant_01_opcode_010,
        0b011: compressed_quadrant_01_opcode_011,
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
def compressed_quadrant_01_opcode_011(word):
    # 011 nzimm[9] 2 nzimm[4|6|8:7|5] 01 C.ADDI16SP (RES, nzimm=0) (p.111)
    _impl = compressed_unimplemented_instruction
    _b05 = (word >> 2) & 0b1
    _b0807 = (word >> 3) & 0b11
    _b06 = (word >> 5) & 0b1
    _b04 = (word >> 6) & 0b1
    _b09 = (word >> 11) & 0b1
    _imm = (_b09 << 9) | (_b0807 << 7) | (_b06 << 6) | (_b05 << 4) | (_b04 << 4)
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b09 << x, range(10, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    if 2 == compressed_rs1_or_rd(word):
        if 0 == _imm:
            _impl = compressed_illegal_instruction
        else:
            _impl = c_addi16sp
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
def compressed_quadrant_01_opcode_110(word):
    # 110 imm[8|4:3] rs1 ′ imm[7:6|2:1|5] 01 C.BEQZ
    _impl = c_beqz
    _b05   = (word >> 2) & 0b1
    _b0201 = (word >> 4) & 0b11
    _b0706 = (word >> 6) & 0b11
    _b0403 = (word >> 9) & 0b11
    _b08   = (word >> 11) & 0b1
    _imm = (_b08 << 8) | (_b0706 << 6) | (_b05 << 5) | (_b0403 << 3) | (_b0201 << 1)
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b08 << x, range(9, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    return _impl(word, imm=_imm)
def compressed_quadrant_01_opcode_111(word):
    # 111 imm[8|4:3] rs1 ′ imm[7:6|2:1|5] 01 C.BNEZ
    _impl = c_bnez
    _b05   = (word >> 2) & 0b1
    _b0201 = (word >> 4) & 0b11
    _b0706 = (word >> 6) & 0b11
    _b0403 = (word >> 9) & 0b11
    _b08   = (word >> 11) & 0b1
    _imm = (_b08 << 8) | (_b0706 << 6) | (_b05 << 5) | (_b0403 << 3) | (_b0201 << 1)
    _imm = functools.reduce(lambda a, b: a | b, map(lambda x: _b08 << x, range(9, 16)), _imm)
    _imm = int.from_bytes(struct.Struct('<H').pack(_imm), 'little', signed=True)
    return _impl(word, imm=_imm)
def compressed_quadrant_10(word):
#    print('compressed_quadrant_10({:04x})'.format(word))
    return {
        0b011: compressed_quadrant_10_opcode_011,
        0b100: compressed_quadrant_10_opcode_100,
        0b111: compressed_quadrant_10_opcode_111,
    }.get(compressed_opcode(word), compressed_unimplemented_instruction)(word)
def compressed_quadrant_10_opcode_011(word):
    _impl = compressed_unimplemented_instruction
    if 0 == compressed_rs1_or_rd:
        pass
    else:
        _impl = c_ldsp
    return _impl(word)
def compressed_quadrant_10_opcode_100(word):
#    print('compressed_quadrant_10_opcode_100()')
    _impl = compressed_unimplemented_instruction
    _b12 = (word >> 12) & 0b1
    if 0 == _b12:
        if 0 == compressed_rs2(word):
            _impl = c_jr
        else:
            _impl = c_mv
    else:
        # 100 1 rs1/rd̸=0 rs2̸=0 10 C.ADD (HINT, rd=0)
        if 0 != compressed_rs1_or_rd(word) and 0 != compressed_rs2(word):
            _impl = c_add
        else:
            pass
    return _impl(word)
def compressed_quadrant_10_opcode_111(word):
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
def compressed_rs1_prime_or_rd_prime(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return (word >> 7) & 0b111
def compressed_rs2(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return (word >> 2) & 0b1_1111
def compressed_rs2_prime(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 111)
    return (word >> 2) & 0b111

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
        0b011_0111: lui,
        0b001_0111: auipc,
        0b110_1111: jal,
        0b010_0011: store,
        0b001_0011: i_type,
        0b110_0011: b_type,
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
    # imm[11:0]
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _tmp = (word >> 20) & 0b1111_1111_1111
    _b11 = (_tmp & 0b1000_0000_0000) >> 11
    _retval = _tmp
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b11 << x, range(12, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncompressed_imm21(word, **kwargs):
    # imm[20|10:1|11|19:12] rrrrr ooooooo
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _tmp = (word >> 12) & 0b1111_1111_1111_1111_1111
    _b1918171615141312     = (_tmp & 0b1111_1111) >> 0
    _b11                   = (_tmp & 0b1_0000_0000) >> 8
    _b10090807060504030201 = (_tmp & 0b111_1111_1110_0000_0000) >> 9
    _b20                   = (_tmp & 0b1000_0000_0000_0000_0000) >> 19
    _retval  = _b20 << 20
    _retval |= _b1918171615141312 << 12
    _retval |= _b11 << 11
    _retval |= _b10090807060504030201 << 1
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b20 << x, range(21, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncompressed_imm32(word, **kwargs):
    # imm[31:12] rrrrr ooooooo
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _retval = word & 0b1111_1111_1111_1111_1111_0000_0000_0000
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)
def uncompressed_funct3(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    return (word >> 12) & 0b111
def uncompressed_i_type_shamt(word):
    return (word >> 20) & 0b1_1111
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
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    _b12           = (word >> 31) & 0b1
    _b100908070605 = (word >> 25) & 0b11_1111
    _b04030201     = (word >> 9) & 0b1111
    _b11           = (word >> 7) & 0b1
    _retval  = _b12 << 12
    _retval |= _b11 << 11
    _retval |= _b100908070605 << 5
    _retval |= _b04030201 << 1
    _retval = functools.reduce(lambda a, b: a | b, map(lambda x: _b12 << x, range(13, 32)), _retval)
    return int.from_bytes(struct.Struct('<I').pack(_retval), 'little', **kwargs)





def do_decode(buffer, max_insns):
    _retval = []
    while max_insns > len(_retval) and len(buffer):
        _word = int.from_bytes(buffer[:4], 'little')
        if 0x3 == _word & 0x3:
            if 4 > len(buffer): break
            _retval.append(decode_uncompressed(_word))
        else:
            _word &= 0xffff
            _retval.append(decode_compressed(_word))
    return _retval
