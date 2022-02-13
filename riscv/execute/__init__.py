import functools

def auipc(pc, imm): return imm + pc
def jal(pc, imm, sz): return (imm + pc, sz + pc) # next_pc, ret_pc
def jalr(pc, imm, rs1, sz): return (imm + rs1, sz + pc) # next_pc, ret_pc
def addi(rs1, imm): return imm + rs1
def add(rs1, rs2): return rs1 + rs2
def sub(rs1, rs2): return rs1 - rs2
#def andi(rs1, imm): return imm & rs1
def andi(rs1, imm):
#    print('andi(): rs1 : {}'.format(list(map(lambda x: '{:08b}'.format(x), rs1.to_bytes(8, 'little', signed=True)))))
#    print('andi(): imm : {}'.format(list(map(lambda x: '{:08b}'.format(x), imm.to_bytes(8, 'little', signed=True)))))
    return int.from_bytes(map(
        lambda a, b: a & b,
        rs1.to_bytes(8, 'little', signed=True),
        imm.to_bytes(8, 'little', signed=True),
    ), 'little', signed=True)
#def slli(rs1, shamt): return (rs1 << shamt)
def slli(rs1, shamt):
    _retval  = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little') << shamt
    _retval &= 2**64 - 1
    _retval  = int.from_bytes(_retval.to_bytes(8, 'little'), 'little')
    return _retval
def srli(rs1, shamt):
    _mask = ((2 ** shamt) - 1) << (64 - shamt)
    _retval  = srai(rs1, shamt)
    _retval |= _mask
    _retval ^= _mask
    return _retval
def srai(rs1, shamt):
    _retval  = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little') >> shamt
    _msbs = (((2 ** shamt) - 1) << (64 - shamt) if ((rs1 >> 63) & 0b1) else 0)
    _retval |= _msbs
#    _retval  = int.from_bytes(_retval.to_bytes(8, 'little'), 'little')
    return _retval
def beq(pc, rs1, rs2, imm, sz): return (imm + pc if rs1 == rs2 else sz + pc)
def bne(pc, rs1, rs2, imm, sz):
    print('bne(): pc  : {}'.format(pc))
    print('bne(): rs1 : {}'.format(rs1))
    print('bne(): rs2 : {}'.format(rs2))
    _retval = (imm + pc if rs1 != rs2 else sz + pc)
    print('bne(): _retval : {}'.format(_retval))
    return _retval
def blt(pc, rs1, rs2, imm, sz): return (imm + pc if rs1 <  rs2 else sz + pc)
def bge(pc, rs1, rs2, imm, sz): return (imm + pc if rs1 >= rs2 else sz + pc)
def bltu(pc, rs1, rs2, imm, sz):
    _rs1 = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little')
    _rs2 = int.from_bytes(rs2.to_bytes(8, 'little', signed=True), 'little')
    return (imm + pc if _rs1 < _rs2 else sz + pc)
def bgeu(pc, rs1, rs2, imm, sz):
    _rs1 = int.from_bytes(rs1.to_bytes(8, 'little', signed=True), 'little')
    _rs2 = int.from_bytes(rs2.to_bytes(8, 'little', signed=True), 'little')
    return (imm + pc if _rs1 >= _rs2 else sz + pc)