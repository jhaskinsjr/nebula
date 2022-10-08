# Copyright (C) 2021, 2022 John Haskins Jr.

import os

# The syscall numbers were learned from
# https://github.com/westerndigitalcorporation/RISC-V-Linux/blob/master/riscv-pk/pk/syscall.h
#
# The syscall calling protocol was learned from
# https://git.kernel.org/pub/scm/docs/man-pages/man-pages.git/tree/man2/syscall.2?h=man-pages-5.04#n332
# specficially:
#
#   riscv	ecall	a7	a0	a1
#
# meaning that the syscall number is in register x17 (i.e., a7) and,
# optionally, the first and second parameters to the syscall are in
# registers x10 (i.e., a0) and x11 (i.e., a1), respectively

def do_syscall(syscall_num, a0, a1, a2, a3, a4, a5):
    return {
        160: do_uname,
        214: do_brk,
    }.get(int.from_bytes(syscall_num, 'little'))(a0, a1, a2, a3, a4, a5)

def do_uname(a0, a1, a2, a3, a4, a5):
    # TODO: actually fill in a uname struct, pointed to by a0
    print('do_uname(): a0       : {}'.format(a0))
    print('do_uname(): a1       : {}'.format(a1))
    print('do_uname(): a2       : {}'.format(a2))
    print('do_uname(): a3       : {}'.format(a3))
    print('do_uname(): a4       : {}'.format(a4))
    print('do_uname(): a5       : {}'.format(a5))
    print('do_uname(): os.uname : {}'.format(os.uname()))
    return a0
def do_brk(a0, a1, a2, a3, a4, a5):
    return a5