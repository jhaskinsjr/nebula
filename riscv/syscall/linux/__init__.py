# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import logging

# The syscall numbers were learned from
# https://www.robalni.org/riscv/linux-syscalls-64.html
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
    f = {
#         17: do_getcwd,
#         34: do_mkdirat,
#         35: do_unlinkat,
#         37: do_linkat,
#         38: do_renameat,
#         48: do_faccessat,
#         49: do_chdir,
         56: do_openat,
#         57: do_close,
#         62: do_lseek,
#         63: do_read,
         64: do_write,
         78: do_readlinkat,
#         79: do_fstatat,
#         80: do_fstat,
#         93: do_exit,
         98: do_futex,
        160: do_uname,
#        169: do_gettimeofday,
        172: do_getpid,
        174: do_getuid,
        175: do_geteuid,
        176: do_getgid,
        177: do_getegid,
        214: do_brk,
    }.get(int.from_bytes(syscall_num, 'little'), null)
    if 'null' == f.__name__: kwargs.update({
        'log': '*** Syscall ({}) not implemented! ***'.format(int.from_bytes(syscall_num, 'little')),
        'retval': -1,
    })
    return f(a0, a1, a2, a3, a4, a5, **{
        **kwargs,
        **{
            'syscall_num': int.from_bytes(syscall_num, 'little'),
        }
    })
def null(a0, a1, a2, a3, a4, a5, **kwargs):
    if 'log' in kwargs.keys(): logging.info(kwargs.get('log'))
    return {
        'done': True,
        'output': {
            'register': {
                'cmd': 'set',
                'name': 10,
                'data': list((-1 if 'retval' not in kwargs.keys() else kwargs.get('retval')).to_bytes(8, 'little', signed=True)),
            },
        },
    }
def do_openat(a0, a1, a2, a3, a4, a5, **kwargs):
    if '0' in kwargs.keys():
        _dir_fd = int.from_bytes(a0[:4], 'little', signed=True)
        kwargs.update({'0': kwargs.get('0') + bytes([0])})
        _pathname = kwargs.get('0')[:kwargs.get('0').index(0)].decode('ascii')
        _flags = int.from_bytes(a2, 'little')
        try:
            _fd = os.open(_pathname, _flags, dir_fd=_dir_fd)
        except:
            logging.info('do_openat(): a0        : {}'.format(a0))
            logging.info('do_openat(): a1        : {}'.format(a1))
            logging.info('do_openat(): a2        : {}'.format(a2))
            logging.info('do_openat(): _dir_fd   : {}'.format(_dir_fd))
            logging.info('do_openat(): _pathname : {} ({})'.format(_pathname, len(_pathname)))
            _fd = -1
        logging.info('openat({}, {}, {}) -> {}'.format(_dir_fd, _pathname, _flags, _fd))
        _retval = {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': list(_fd.to_bytes(8, 'little', signed=True)),
                },
            },
        }
    else:
        _len = 256 # HACK: This is the pathname of SYS_openat, which has
                   # function prototype openat(int dirfd, const char * pathname, int flags);
                   # see: https://man7.org/linux/man-pages/man2/open.2.html. How long is
                   # the pathname? Who knows? It could, in theory, be much more than 256
                   # bytes, but I can't be bothered with making this general-purpose right now.
        _retval = {
            'done': False,
            'peek': {
                'addr': int.from_bytes(a1, 'little'),
                'size': _len,
            },
        }
    return _retval
def do_write(a0, a1, a2, a3, a4, a5, **kwargs):
    _len = int.from_bytes(a2, 'little')
    if '0' in kwargs.keys():
        _fd = int.from_bytes(a0[:4], 'little', signed=True)
        _buf = kwargs.get('0')
        try:
            _nbytes = os.write(_fd, _buf[:_len])
        except:
            logging.info('do_write(): a0   : {}'.format(a0))
            logging.info('do_write(): a1   : {}'.format(a1))
            logging.info('do_write(): a2   : {}'.format(a2))
            logging.info('do_write(): _fd  : {}'.format(_fd))
            logging.info('do_write(): _buf : {} ({})'.format(_buf, len(_buf)))
            _nbytes = -1
        logging.info('write({}, {}, {}) -> {}'.format(_fd, _buf[:_len], _len, _nbytes))
        _retval = {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': list(_nbytes.to_bytes(8, 'little', signed=True)),
                },
            },
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
def do_readlinkat(a0, a1, a2, a3, a4, a5, **kwargs):
    # ssize_t readlinkat(int dirfd, const char *restrict pathname, char *restrict buf, size_t bufsiz);
    #
    # see: https://man7.org/linux/man-pages/man2/readlinkat.2.html
    if '0' in kwargs.keys():
        _dir_fd = int.from_bytes(a0, 'little', signed=True)
        kwargs.update({'0': kwargs.get('0') + bytes([0])})
        _pathname = kwargs.get('0')[:kwargs.get('0').index(0)].decode('ascii')
        _buf_p = int.from_bytes(a2, 'little')
        _bufsize = int.from_bytes(a3, 'little')
        try:
            _linkpath = os.readlink(_pathname, dir_fd=_dir_fd)
            _syscall_ret = 0
        except:
            logging.info('do_readlinkat(): a0        : {}'.format(a0))
            logging.info('do_readlinkat(): a1        : {}'.format(a1))
            logging.info('do_readlinkat(): a2        : {}'.format(a2))
            logging.info('do_readlinkat(): a3        : {}'.format(a3))
            logging.info('do_readlinkat(): _dir_fd   : {}'.format(_dir_fd))
            logging.info('do_readlinkat(): _pathname : {} ({})'.format(_pathname, len(_pathname)))
            _syscall_ret = -1
        logging.info('readlinkat({}, {}, {}, {}) -> {}'.format(_dir_fd, _pathname, _buf_p, _bufsize, _linkpath))
        _retval = {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': list(_syscall_ret.to_bytes(8, 'little', signed=True)),
                },
            },
            'poke': {
                'addr': a3, # FIXME: convert this (i.e.: int.from_bytes(a3, 'little')) here
                'data': list(bytes(_linkpath[:_bufsize], encoding='ascii')),
            },
        }
    else:
        _len = 256 # HACK: This is the pathname of SYS_readlinkat. How long is
                   # the pathname? Who knows? It could, in theory, be much more than 256
                   # bytes, but I can't be bothered with making this general-purpose right now.
        _retval = {
            'done': False,
            'peek': {
                'addr': int.from_bytes(a1, 'little'),
                'size': _len,
            },
        }
    return _retval
def do_futex(a0, a1, a2, a3, a4, a5, **kwargs):
    # int futex(int *uaddr, int op, int val, const struct timespec *timeout, int *uaddr2, int val3)
    #
    # see: https://linux.die.net/man/2/futex
    FUTEX_PRIVATE_FLAG = 128
    _uaddr = int.from_bytes(a0, 'little')
    _op = int.from_bytes(a1, 'little', signed=True)
    _private = (_op & FUTEX_PRIVATE_FLAG == FUTEX_PRIVATE_FLAG)
    _op = {
        0: 'FUTEX_WAIT',
        1: 'FUTEX_WAKE',
        2: 'FUTEX_FD',
        3: 'FUTEX_REQUEUE',
        4: 'FUTEX_CMP_REQUEUE',
    }.get((_op | FUTEX_PRIVATE_FLAG) ^ FUTEX_PRIVATE_FLAG, _op)
    _op += ('|FUTEX_PRIVATE_FLAG' if _private else '')
    _val = int.from_bytes(a2, 'little', signed=True)
    _timeout_p = int.from_bytes(a3, 'little')
    _timeout_p = ('NULL' if 0 == _timeout_p else _timeout_p)
#    _uaddr2 = int.from_bytes(a4, 'little')
#    _val3 = int.from_bytes(a5, 'little', signed=True)
    logging.info('futex({}, {}, {}, {}, {}, {})...'.format(
        _uaddr, _op, _val, _timeout_p, a4, a5,
    ))
    if 'FUTEX_WAIT' in _op:
        if '0' in kwargs.keys():
            _u = int.from_bytes(kwargs.get('0'), 'little', signed=True)
            _retval = (0 if _u == _val else -1)
            logging.info('futex({}, {}, {}, {}, {}, {}) -> {}'.format(
                _uaddr, _op, _val, _timeout_p, a4, a5,
                _retval
            ))
            return {
                'done': True,
                'output': {
                    'register': {
                        'cmd': 'set',
                        'name': 10,
                        'data': list(_retval.to_bytes(8, 'little', signed=True)),
                    },
                },
            }
        else:
            return {
                'done': False,
                'peek': {
                    'addr': _uaddr,
                    'size': 4, # sizeof(int)
                },
            }
    return null(a0, a1, a2, a3, a4, a5, **kwargs)
def do_uname(a0, a1, a2, a3, a4, a5, **kwargs):
    # NOTE: The fields in a struct utsname are padded to 65 bytes;
    # see: _UTSNAME_LENGTH in /opt/riscv/sysroot/usr/include/bits/utsname.h
    try:
        _os_uname = os.uname()
        _success = 0
    except:
        _success = -1
    logging.info('uname() -> {}'.format(_success))
    return {
        'done': True,
        'output': {
            'register': {
                'cmd': 'set',
                'name': 10,
                'data': list(_success.to_bytes(8, 'little', signed=True)),
            },
        },
        'poke': {
            'addr': a0, # FIXME: convert this (i.e.: int.from_bytes(a3, 'little')) here
            'data': list(bytes(''.join(map(lambda x: x + ('\0' * (65 - len(x))), _os_uname)), encoding='ascii')),
        },
    }
def do_getpid(a0, a1, a2, a3, a4, a5, **kwargs): return null(a0, a1, a2, a3, a4, a5, **{**kwargs, **{'retval': 5}})
def do_getuid(a0, a1, a2, a3, a4, a5, **kwargs): return null(a0, a1, a2, a3, a4, a5, **{**kwargs, **{'retval': 0}})
def do_geteuid(a0, a1, a2, a3, a4, a5, **kwargs): return null(a0, a1, a2, a3, a4, a5, **{**kwargs, **{'retval': 0}})
def do_getgid(a0, a1, a2, a3, a4, a5, **kwargs): return null(a0, a1, a2, a3, a4, a5, **{**kwargs, **{'retval': 0}})
def do_getegid(a0, a1, a2, a3, a4, a5, **kwargs): return null(a0, a1, a2, a3, a4, a5, **{**kwargs, **{'retval': 0}})
def do_brk(a0, a1, a2, a3, a4, a5, **kwargs):
    # Prototype
    # int brk(void *endds);
    #
    # Argument
    # endds 	pointer to the end of the data segment
    #
    # Return Value
    #
    # Returns ‘0’ if successful; otherwise, returns ‘-1’.
    #
    # If the argument endds is zero, the function sets the global variable
    # __curbrk to the address of the start of the heap and returns zero.
    #
    # If the argument endds is non-zero and has a value less than the address
    # of the end of the heap, the function sets the global variable __curbrk
    # to the value of endds and returns zero.
    #
    # Otherwise, the global variable __curbrk is unchanged and the function
    # returns -1.
    #
    # see: https://onlinedocs.microchip.com/pr/GUID-70ACD6B0-A33F-4653-B192-8465EAD1FD98-en-US-5/index.html?GUID-1DF544E2-138D-489F-803B-36427E9FBA54
    _endds = int.from_bytes(a0, 'little')
    _retval = (list((0x10000000).to_bytes(8, 'little')) if 0 == _endds else a0)
    logging.info('brk({}) -> {}'.format(_endds, _retval))
    return {
        'done': True,
        'output': {
            'register': {
                'cmd': 'set',
                'name': 10,
                'data': _retval,
            },
        },
    }