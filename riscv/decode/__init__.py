import functools
import struct

def unimplemented_instruction(word):
    return {
        'cmd': 'Undefined',
        'word': word,
    }

def c_jr(word):
    return {
        'cmd': 'JALR',
        'imm': 0,
        'rs1': compressed_rs1_or_rd(word),
        'rd': 0,
        'word': word,
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
        'size': 8,
        'word': word,
    }

def auipc(word):
    return {
        'cmd': 'AUIPC',
        'imm': uncompressed_imm32(word, signed=True),
        'rd': uncompressed_rd(word),
        'word': word,
    }
def jal(word):
    return {
        'cmd': 'JAL',
        'imm': uncompressed_imm21(word, signed=True),
        'rd': uncompressed_rd(word),
        'word': word,
    }
def i_type(word):
    return {
        0b000: {
            'cmd': 'ADDI',
            'imm': uncompressed_i_type_imm12(word, signed=True),
            'rs1': uncompressed_rs1(word),
            'rd': uncompressed_rd(word),
            'word': word,
        }
    }.get(uncompressed_i_type_funct3(word), unimplemented_instruction(word))





def decode_compressed(word):
#    print('decode_compressed({:04x})'.format(word))
    return {
        0b10: compressed_quadrant_10,
    }.get(compressed_quadrant(word), unimplemented_instruction)(word)
def compressed_quadrant(word):
#    print('compressed_quadrant({:04x})'.format(word))
    return word & 0b11

def compressed_quadrant_10(word):
#    print('compressed_quadrant_10({:04x})'.format(word))
    return {
        0b011: compressed_quadrant_10_opcode_011,
        0b100: compressed_quadrant_10_opcode_100,
    }.get(compressed_opcode(word), unimplemented_instruction)(word)
def compressed_quadrant_10_opcode_100(word):
#    print('compressed_quadrant_10_opcode_100()')
    _impl = unimplemented_instruction
    _b12 = (word >> 12) & 0b1
    if 0 == _b12:
        if 0 == compressed_rs2(word):
            _impl = c_jr
        else:
            _impl = c_mv
    else:
        pass
    return _impl(word)
def compressed_quadrant_10_opcode_011(word):
    _impl = unimplemented_instruction
    if 0 == compressed_rs1_or_rd:
        pass
    else:
        _impl = c_ldsp
    return _impl(word)


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





def uncompressed_illegal_instruction(word):
    assert False, 'Illegal instruction ({:08x})!'.format(word)
def decode_uncompressed(word):
    return {
        0b001_0111: auipc,
        0b110_1111: jal,
        0b001_0011: i_type,
    }.get(uncompressed_opcode(word), unimplemented_instruction)(word)

def uncompressed_opcode(word):
    return (word & 0b111_1111)
def uncompressed_rs1(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    return (word >> 15) & 0b1_1111
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
def uncompressed_i_type_funct3(word):
    # https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf (p. 130)
    return (word >> 12) & 0b111





def do_decode(buffer, max_insns):
    _retval = []
    while max_insns > len(_retval) and len(buffer):
        _word = int.from_bytes(buffer[:4], 'little')
        if 0x3 == _word & 0x3:
            if 4 > len(buffer): break
            _retval.append((4, decode_uncompressed(_word)))
        else:
            _word &= 0xffff
            _retval.append((2, decode_compressed(_word)))
    return _retval
