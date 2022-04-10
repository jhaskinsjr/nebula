JUMPS = ['JALR', 'JAL']
BRANCHES = ['BEQ', 'BNE', 'BLT', 'BGE', 'BLTU', 'BGEU']

def register_mask(wbits):
    return {
        64: (2 ** 64) - 1,
        32: (2 ** 32) - 1,
        16: (2 ** 16) - 1,
         8: (2 ** 8) - 1,
    }.get(wbits, None)
def integer_to_list_of_bytes(v, wbits, byte_order):
    return list((v & register_mask(wbits)).to_bytes((wbits // 8), byte_order))