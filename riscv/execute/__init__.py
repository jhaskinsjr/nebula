# Copyright (C) 2021, 2022 John Haskins Jr.

import functools
import riscv.constants

def lui(imm):
    # Description
    # Build 32-bit constants and uses the U-type format. LUI places the
    # U-immediate value in the top 20 bits of the destination register
    # rd, filling in the lowest 12 bits with zeros.
    # Implementation
    # x[rd] = sext(immediate[31:12] << 12)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#lui
    return riscv.constants.integer_to_list_of_bytes(imm, 64, 'little')
def auipc(pc, imm):
    # Description
    # Build pc-relative addresses and uses the U-type format. AUIPC forms
    # a 32-bit offset from the 20-bit U-immediate, filling in the lowest 12
    # bits with zeros, adds this offset to the pc, then places the result
    # in register rd.
    # Implementation
    # x[rd] = pc + sext(immediate[31:12] << 12)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#auipc
    return riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little')
def jal(pc, imm, sz):
    return (
        riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'),
        riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'),
    ) # next_pc, ret_pc
def jalr(pc, imm, rs1, sz):
    return (
        riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(rs1, 'little'), 64, 'little'),
        riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'),
    ) # next_pc, ret_pc
def addi(rs1, imm):
    # Description
    # Adds the sign-extended 12-bit immediate to register rs1. Arithmetic
    # overflow is ignored and the result is simply the low XLEN bits of the
    # result. ADDI rd, rs1, 0 is used to implement the MV rd, rs1 assembler
    # pseudo-instruction.
    # Implementation
    # x[rd] = x[rs1] + sext(immediate)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#addi
    return riscv.constants.integer_to_list_of_bytes(
        imm + int.from_bytes(rs1, 'little', signed=True),
        64,
        'little'
    )
def slti(rs1, imm):
    # Description
    # Place the value 1 in register rd if register rs1 is less than the
    # signextended immediate when both are treated as signed numbers, else
    # 0 is written to rd.
    # Implementation
    # x[rd] = x[rs1] <s sext(immediate)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#slti
    return riscv.constants.integer_to_list_of_bytes((1 if int.from_bytes(rs1, 'little', signed=True) < imm else 0), 64, 'little')
def sltiu(rs1, imm):
    # Description
    # Place the value 1 in register rd if register rs1 is less than the
    # immediate when both are treated as unsigned numbers, else 0 is
    # written to rd.
    # Implementation
    # x[rd] = x[rs1] <u sext(immediate)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#sltiu
    return riscv.constants.integer_to_list_of_bytes((1 if int.from_bytes(rs1, 'little') < imm else 0), 64, 'little')
def andi(rs1, imm):
    # Description
    # Performs bitwise AND on register rs1 and the sign-extended 12-bit
    # immediate and place the result in rd
    # Implementation
    # x[rd] = x[rs1] & sext(immediate)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#andi
    return list(map(
        lambda a, b: a & b,
        rs1,
        riscv.constants.integer_to_list_of_bytes(imm, 64, 'little')
    ))
def add(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1, 'little', signed=True) + int.from_bytes(rs2, 'little', signed=True),
        64,
        'little',
    )
def sub(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1, 'little', signed=True) - int.from_bytes(rs2, 'little', signed=True),
        64,
        'little',
    )
def xor(rs1, rs2):
    return list(map(
        lambda a, b: a ^ b,
        rs1,
        rs2,
    ))
def do_or(rs1, rs2):
    return list(map(
        lambda a, b: a | b,
        rs1,
        rs2,
    ))
def do_and(rs1, rs2):
    return list(map(
        lambda a, b: a & b,
        rs1,
        rs2,
    ))
def mul(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        (int.from_bytes(rs1, 'little', signed=True) * int.from_bytes(rs2, 'little', signed=True)) & ((2 ** 64) - 1),
        64,
        'little',
    )
def mulh(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        ((int.from_bytes(rs1, 'little', signed=True) * int.from_bytes(rs2, 'little', signed=True)) >> 64) & ((2 ** 64) - 1),
        64,
        'little',
    )
def mulhsu(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        ((int.from_bytes(rs1, 'little', signed=True) * int.from_bytes(rs2, 'little')) >> 64) & ((2 ** 64) - 1),
        64,
        'little',
    )
def mulhu(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        ((int.from_bytes(rs1, 'little') * int.from_bytes(rs2, 'little')) >> 64) & ((2 ** 64) - 1),
        64,
        'little',
    )
def div(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        (int.from_bytes(rs1, 'little', signed=True) // int.from_bytes(rs2, 'little', signed=True)) & ((2 ** 64) - 1),
        64,
        'little',
    )
def divu(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        (int.from_bytes(rs1, 'little') // int.from_bytes(rs2, 'little')) & ((2 ** 64) - 1),
        64,
        'little',
    )
def rem(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        (int.from_bytes(rs1, 'little', signed=True) % int.from_bytes(rs2, 'little', signed=True)) & ((2 ** 64) - 1),
        64,
        'little',
    )
def remu(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        (int.from_bytes(rs1, 'little') % int.from_bytes(rs2, 'little')) & ((2 ** 64) - 1),
        64,
        'little',
    )
def slli(rs1, shamt):
    # Description
    # Performs logical left shift on the value in register rs1 by the shift
    # amount held in the lower 5 bits of the immediate
    # In RV64, bit-25 is used to shamt[5].
    # Implementation
    # x[rd] = x[rs1] << shamt
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#slli
    return riscv.constants.integer_to_list_of_bytes(
        (int.from_bytes(rs1, 'little') << shamt) & ((2**64) - 1),
        64,
        'little',
    )
def srli(rs1, shamt):
    # Description
    # Performs logical right shift on the value in register rs1 by the shift
    # amount held in the lower 5 bits of the immediate
    # In RV64, bit-25 is used to shamt[5].
    # Implementation
    # x[rd] = x[rs1] >>u shamt
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#srli
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1, 'little') >> shamt,
        64,
        'little',
    )
def srai(rs1, shamt):
    # Description
    # Performs arithmetic right shift on the value in register rs1 by the
    # shift amount held in the lower 5 bits of the immediate
    # In RV64, bit-25 is used to shamt[5].
    # Implementation
    # x[rd] = x[rs1] >>s shamt
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#srai
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1, 'little', signed=True) >> shamt,
        64,
        'little',
    )
def addiw(rs1, imm):
    # Description
    # Adds the sign-extended 12-bit immediate to register rs1 and produces
    # the proper sign-extension of a 32-bit result in rd. Overflows are
    # ignored and the result is the low 32 bits of the result sign-extended
    # to 64 bits. Note, ADDIW rd, rs1, 0 writes the sign-extension of the
    # lower 32 bits of register rs1 into register rd (assembler
    # pseudoinstruction SEXT.W).
    # Implementation
    # x[rd] = sext((x[rs1] + sext(immediate))[31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64i.html#addiw
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(((imm + int.from_bytes(rs1, 'little')) & ((2**32) - 1)).to_bytes(4, 'little'), 'little', signed=True),
        64,
        'little'
    )
def slliw(rs1, shamt):
    # Description
    # Performs logical left shift on the 32-bit of value in register rs1
    # by the shift amount held in the lower 5 bits of the immediate.
    # Encodings with $imm[5] neq 0$ are reserved.
    # Implementation
    # x[rd] = sext((x[rs1] << shamt)[31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64i.html#slliw
    return riscv.constants.integer_to_list_of_bytes(
        (int.from_bytes(rs1, 'little') << shamt) & ((2**32) - 1),
        64,
        'little',
    )
def srliw(rs1, shamt):
    # Description
    # Performs logical right shift on the 32-bit of value in register rs1
    # by the shift amount held in the lower 5 bits of the immediate.
    # Encodings with $imm[5] neq 0$ are reserved.
    # Implementation
    # x[rd] = sext(x[rs1][31:0] >>u shamt)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64i.html#srliw
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1[:4], 'little') >> shamt,
        64,
        'little',
    )
def sraiw(rs1, shamt):
    # Description
    # Performs arithmetic right shift on the 32-bit of value in register
    # rs1 by the shift amount held in the lower 5 bits of the immediate.
    # Encodings with $imm[5] neq 0$ are reserved.
    # Implementation
    # x[rd] = sext(x[rs1][31:0] >>s shamt)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64i.html#sraiw
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1[:4], 'little', signed=True) >> shamt,
        64,
        'little',
    )
def addw(rs1, rs2):
    # Description
    # Adds the 32-bit of registers rs1 and 32-bit of register rs2 and
    # stores the result in rd. Arithmetic overflow is ignored and the low
    # 32-bits of the result is sign-extended to 64-bits and written to the
    # destination register.
    # Implementation
    # x[rd] = sext((x[rs1] + x[rs2])[31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64i.html#addw
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(((int.from_bytes(rs1, 'little', signed=True) + int.from_bytes(rs2, 'little', signed=True)) & ((2**64) - 1)).to_bytes(8, 'little')[:4], 'little', signed=True),
        64,
        'little',
    )
def subw(rs1, rs2):
    # Description
    # Subtract the 32-bit of registers rs1 and 32-bit of register rs2 and
    # stores the result in rd. Arithmetic overflow is ignored and the low
    # 32-bits of the result is sign-extended to 64-bits and written to the
    # destination register.
    # Implementation
    # x[rd] = sext((x[rs1] - x[rs2])[31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64i.html#subw
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(((int.from_bytes(rs1, 'little', signed=True) - int.from_bytes(rs2, 'little', signed=True)) & ((2**64) - 1)).to_bytes(8, 'little')[:4], 'little', signed=True),
        64,
        'little',
    )
def mulw(rs1, rs2):
    # Implementation
    # x[rd] = sext((x[rs1] × x[rs2])[31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64m.html#mulw
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(((int.from_bytes(rs1, 'little', signed=True) * int.from_bytes(rs2, 'little', signed=True)) & ((2**64) - 1)).to_bytes(8, 'little')[:4], 'little', signed=True),
        64,
        'little',
    )
def divw(rs1, rs2):
    # Implementation
    # x[rd] = sext(x[rs1][31:0] /s x[rs2][31:0]
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64m.html#divw
    return riscv.constants.integer_to_list_of_bytes(
        int(int.from_bytes(rs1[:4], 'little', signed=True) / int.from_bytes(rs2[:4], 'little', signed=True)),
        64,
        'little',
    )
def divuw(rs1, rs2):
    # Implementation
    # x[rd] = sext(x[rs1][31:0] /u x[rs2][31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64m.html#divuw
    return riscv.constants.integer_to_list_of_bytes(
        int(int.from_bytes(rs1[:4], 'little') / int.from_bytes(rs2[:4], 'little')),
        64,
        'little',
    )
def remw(rs1, rs2):
    # Implementation
    # x[rd] = sext(x[rs1][31:0] %s x[rs2][31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64m.html#remw
    return riscv.constants.integer_to_list_of_bytes(
        int(int.from_bytes(rs1[:4], 'little', signed=True) % int.from_bytes(rs2[:4], 'little', signed=True)),
        64,
        'little',
    )
def remuw(rs1, rs2):
    # Implementation
    # x[rd] = sext(x[rs1][31:0] %u x[rs2][31:0])
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rv64m.html#remuw
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(
            int(int.from_bytes(rs1[:4], 'little') % int.from_bytes(rs2[:4], 'little')).to_bytes(4, 'little'),
            'little',
            signed=True,
        ),
        64,
        'little',
    )
def beq(pc, rs1, rs2, imm, sz):
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if all(map(lambda a, b: a == b, rs1, rs2)) else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )
def bne(pc, rs1, rs2, imm, sz):
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if not all(map(lambda a, b: a == b, rs1, rs2)) else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )
def blt(pc, rs1, rs2, imm, sz):
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if int.from_bytes(rs1, 'little', signed=True) < int.from_bytes(rs2, 'little', signed=True) else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )
def bge(pc, rs1, rs2, imm, sz):
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if int.from_bytes(rs1, 'little', signed=True) >= int.from_bytes(rs2, 'little', signed=True) else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )
def bltu(pc, rs1, rs2, imm, sz):
    # Description
    # Take the branch if registers rs1 is less than rs2, using unsigned
    # comparison.
    # Implementation
    # if (rs1 >u rs2) pc += sext(offset)
    # XXX: Umm... The above is a typo, right?!?!?!?!?!?!?
    #      I copied it verbatim from the Web address below, but it doesn't
    #      make any sense to do rs1 unsigned-greater-than rs2 if the
    #      instruction is branch-if-less-than-unsigned. Right?!?!?!?!?!?!?
    #      I'm going to act as though it said the implementation were
    #      if (rs1 <u rs2) pc += sext(offset)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#bltu
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if int.from_bytes(rs1, 'little') < int.from_bytes(rs2, 'little') else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )
def bgeu(pc, rs1, rs2, imm, sz):
    # Description
    # Take the branch if registers rs1 is greater than rs2, using unsigned
    # comparison.
    # Implementation
    # if (rs1 >=u rs2) pc += sext(offset)
    # see: https://msyksphinz-self.github.io/riscv-isadoc/html/rvi.html#bgeu
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if int.from_bytes(rs1, 'little') >= int.from_bytes(rs2, 'little') else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )