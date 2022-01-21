def auipc(pc, imm): return imm + pc
def jal(pc, imm): return (imm + pc, 4 + pc) # next_pc, ret_pc
def addi(rs1, imm): return imm + rs1