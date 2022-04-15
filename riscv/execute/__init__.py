import functools
import riscv.constants

def lui(imm):
    return riscv.constants.integer_to_list_of_bytes(imm, 64, 'little')
def auipc(pc, imm):
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
    return riscv.constants.integer_to_list_of_bytes(
        imm + int.from_bytes(rs1, 'little', signed=True),
        64,
        'little'
    )
def slti(rs1, imm):
    return (
        riscv.constants.integer_to_list_of_bytes(1, 64, 'little')
        if int.from_bytes(rs1, 'little', signed=True) < imm else
        riscv.constants.integer_to_list_of_bytes(0, 64, 'little')
    )
def sltiu(rs1, imm):
    return (
        riscv.constants.integer_to_list_of_bytes(1, 64, 'little')
        if int.from_bytes(rs1, 'little') < imm else
        riscv.constants.integer_to_list_of_bytes(0, 64, 'little')
    )
def addiw(rs1, imm):
    return riscv.constants.integer_to_list_of_bytes(
        ((imm + int.from_bytes(rs1, 'little', signed=True)) << 32) >> 32,
        64,
        'little'
    )
def andi(rs1, imm):
    return list(map(
        lambda a, b: a & b,
        rs1,
        riscv.constants.integer_to_list_of_bytes(imm, 64, 'little')
    ))
#def addiw(rs1, imm):return (addi(rs1, imm) << 32) >> 32
#def andi(rs1, imm): return imm & rs1
#def andi(rs1, imm):
#    print('andi(): rs1 : {}'.format(list(map(lambda x: '{:08b}'.format(x), rs1.to_bytes(8, 'little', signed=True)))))
#    print('andi(): imm : {}'.format(list(map(lambda x: '{:08b}'.format(x), imm.to_bytes(8, 'little', signed=True)))))
#    return int.from_bytes(map(
#        lambda a, b: a & b,
#        rs1.to_bytes(8, 'little', signed=True),
#        imm.to_bytes(8, 'little', signed=True),
#    ), 'little', signed=True)
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
def addw(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        ((int.from_bytes(rs1, 'little', signed=True) + int.from_bytes(rs2, 'little', signed=True)) << 32) >> 32,
        64,
        'little',
    )
def subw(rs1, rs2):
    return riscv.constants.integer_to_list_of_bytes(
        ((int.from_bytes(rs1, 'little', signed=True) - int.from_bytes(rs2, 'little', signed=True)) << 32) >> 32,
        64,
        'little',
    )
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
#def add(rs1, rs2): return rs1 + rs2
#def sub(rs1, rs2): return rs1 - rs2
#def addw(rs1, rs2): return (add(rs1, rs2) << 32) >> 32
#def subw(rs1, rs2): return (sub(rs1, rs2) << 32) >> 32
def slli(rs1, shamt):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1, 'little') << shamt,
        64,
        'little',
    )
def srli(rs1, shamt):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1, 'little') >> shamt,
        64,
        'little',
    )
def srai(rs1, shamt):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(rs1, 'little', signed=True) >> shamt,
        64,
        'little',
    )
def slliw(rs1, shamt):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(((int.from_bytes(rs1, 'little') << shamt) & ((2 ** 32) - 1)).to_bytes(4, 'little'), 'little', signed=True),
        64,
        'little',
    )
def srliw(rs1, shamt):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(((int.from_bytes(rs1, 'little') >> shamt) & ((2 ** 32) - 1)).to_bytes(4, 'little'), 'little', signed=True),
        64,
        'little',
    )
def sraiw(rs1, shamt):
    return riscv.constants.integer_to_list_of_bytes(
        int.from_bytes(((int.from_bytes(rs1, 'little', signed=True) >> shamt) & ((2 ** 32) - 1)).to_bytes(4, 'little'), 'little', signed=True),
        64,
        'little',
    )
#def slli(rs1, shamt): return (rs1 << shamt)
#def slli(rs1, shamt):
#    _retval  = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little') << shamt
#    _retval &= 2**64 - 1
#    _retval  = int.from_bytes(_retval.to_bytes(8, 'little'), 'little')
#    return _retval
#def srli(rs1, shamt):
#    _mask = ((2 ** shamt) - 1) << (64 - shamt)
#    _retval  = srai(rs1, shamt)
#    _retval |= _mask
#    _retval ^= _mask
#    return _retval
#def srai(rs1, shamt):
#    _retval  = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little') >> shamt
#    _msbs = (((2 ** shamt) - 1) << (64 - shamt) if ((rs1 >> 63) & 0b1) else 0)
#    _retval |= _msbs
#    return _retval
#def slliw(rs1, shamt): return (slli(rs1, shamt) << 32) >> 32
#def srliw(rs1, shamt): return (srli(rs1, shamt) << 32) >> 32
#def sraiw(rs1, shamt): return (srai(rs1, shamt) << 32) >> 32
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
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if int.from_bytes(rs1, 'little') < int.from_bytes(rs2, 'little') else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )
def bgeu(pc, rs1, rs2, imm, sz):
    return (
        (riscv.constants.integer_to_list_of_bytes(imm + int.from_bytes(pc, 'little'), 64, 'little'), True)
        if int.from_bytes(rs1, 'little') >= int.from_bytes(rs2, 'little') else
        (riscv.constants.integer_to_list_of_bytes(sz + int.from_bytes(pc, 'little'), 64, 'little'), False)
    )
#def beq(pc, rs1, rs2, imm, sz): return (imm + pc if rs1 == rs2 else sz + pc)
#def bne(pc, rs1, rs2, imm, sz):
#    print('bne(): pc  : {}'.format(pc))
#    print('bne(): rs1 : {}'.format(rs1))
#    print('bne(): rs2 : {}'.format(rs2))
#    _retval = (imm + pc if rs1 != rs2 else sz + pc)
#    print('bne(): _retval : {}'.format(_retval))
#    return _retval
#def blt(pc, rs1, rs2, imm, sz): return (imm + pc if rs1 <  rs2 else sz + pc)
#def bge(pc, rs1, rs2, imm, sz): return (imm + pc if rs1 >= rs2 else sz + pc)
#def bltu(pc, rs1, rs2, imm, sz):
#    _rs1 = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little')
#    _rs2 = int.from_bytes(rs2.to_bytes(8, 'little', signed=True), 'little')
#    return (imm + pc if _rs1 < _rs2 else sz + pc)
#def bgeu(pc, rs1, rs2, imm, sz):
#    _rs1 = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little')
#    _rs2 = int.from_bytes(rs2.to_bytes(8, 'little', signed=True), 'little')
#    return (imm + pc if _rs1 >= _rs2 else sz + pc)