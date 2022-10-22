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

def do_syscall(syscall_num, a0, a1, a2, a3, a4, a5, **kwargs):
    return {
#         17: do_getcwd,
#         34: do_mkdirat,
#         35: do_unlinkat,
#         37: do_linkat,
#         38: do_renameat,
#         48: do_faccessat,
#         49: do_chdir,
#         56: do_openat,
#         57: do_close,
#         62: do_lseek,
#         63: do_read,
         64: do_write,
#         79: do_fstatat,
#         80: do_fstat,
#         93: do_exit,
        160: do_uname,
#        169: do_gettimeofday,
#        172: do_getpid,
#        174: do_getuid,
#        175: do_geteuid,
#        176: do_getgid,
#        177: do_getegid,
        214: do_brk,
    }.get(int.from_bytes(syscall_num, 'little'), null)(a0, a1, a2, a3, a4, a5, **{**kwargs, **{'syscall_num': int.from_bytes(syscall_num, 'little')}})

def null(a0, a1, a2, a3, a4, a5, **kwargs):
    print('syscall ({}) not implemented'.format(kwargs.get('syscall_num')))
    return {
        'done': True,
    }
def do_write(a0, a1, a2, a3, a4, a5, **kwargs):
    _len = int.from_bytes(a2, 'little')
    if 'buf' in kwargs.keys():
        _fd = int.from_bytes(a0, 'little')
        _buf = kwargs.get('buf')
        try:
            os.write(_fd, _buf[:_len])
        except:
            print('do_write(): a0   : {}'.format(a0))
            print('do_write(): a1   : {}'.format(a1))
            print('do_write(): a2   : {}'.format(a2))
            print('do_write(): _fd  : {}'.format(_fd))
            print('do_write(): _buf : {} ({})'.format(_buf, len(_buf)))
        _retval = {
            'done': True,
        }
    else:
        _retval = {
            'done': False,
            'peek': {
                'addr': int.from_bytes(a1, 'little'),
                'size': _len,
            },
        }
    return _retval
def do_uname(a0, a1, a2, a3, a4, a5, **kwargs):
    # NOTE: The fields in a struct utsname are padded to 65 bytes;
    # see: _UTSNAME_LENGTH in /opt/riscv/sysroot/usr/include/bits/utsname.h
    return {
        'done': True,
        'poke': {
            'addr': a0,
            'data': list(bytes(''.join(map(lambda x: x + ('\0' * (65 - len(x))), os.uname())), encoding='ascii')),
        },
    }
def do_brk(a0, a1, a2, a3, a4, a5, **kwargs): return {
    'done': True,
}