def auipc(pc, imm): return imm + pc
def jal(pc, imm): return (imm + pc, 4 + pc) # next_pc, ret_pc
def jalr(pc, imm, rs1): return (imm + rs1, 4 + pc) # next_pc, ret_pc
def addi(rs1, imm): return imm + rs1
def add(rs1, rs2): return rs1 + rs2
def andi(rs1, imm): return imm & rs1
def slli(rs1, shamt): return rs1 << shamt
def beq(pc, rs1, rs2, imm): return (imm + pc if rs1 == rs2 else 4 + pc)
def bne(pc, rs1, rs2, imm): return (imm + pc if rs1 != rs2 else 4 + pc)