def auipc(pc, imm): return imm + pc
def jal(pc, imm): return (imm + pc, 4 + pc) # next_pc, ret_pc
def jalr(pc, imm, rs1): return (imm + rs1, 4 + pc) # next_pc, ret_pc
def addi(rs1, imm): return imm + rs1
def add(rs1, rs2): return rs1 + rs2
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
def beq(pc, rs1, rs2, imm): return (imm + pc if rs1 == rs2 else 4 + pc)
def bne(pc, rs1, rs2, imm): return (imm + pc if rs1 != rs2 else 4 + pc)