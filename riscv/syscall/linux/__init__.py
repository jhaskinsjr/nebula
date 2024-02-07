# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

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

class System:
    PAGESIZE = 2**12    # HACK: pages need not necessarily always be 4096 B
    SIZEOF_VOID_P = 8   # HACK: this is highly (!) 64-bit-specific
    SIZEOF_SIZE_T = 8   # HACK: this is highly (!) 64-bit specific
    def __init__(self):
        self.state = {}
    def do_syscall(self, syscall_num, a0, a1, a2, a3, a4, a5, **kwargs):
        f = {
    #         17: self.do_getcwd,
    #         34: self.do_mkdirat,
    #         35: self.do_unlinkat,
    #         37: self.do_linkat,
    #         38: self.do_renameat,
    #         48: self.do_faccessat,
    #         49: self.do_chdir,
             56: self.do_openat,
             57: self.do_close,
             62: self.do_lseek,
             63: self.do_read,
             64: self.do_write,
             66: self.do_writev,
             78: self.do_readlinkat,
    #         79: self.do_fstatat,
             80: self.do_fstat,
             93: self.do_exit,
             98: self.do_futex,
            160: self.do_uname,
    #        169: self.do_gettimeofday,
            172: self.do_getpid,
            174: self.do_getuid,
            175: self.do_geteuid,
            176: self.do_getgid,
            177: self.do_getegid,
            214: self.do_brk,
            215: self.do_munmap,
            222: self.do_mmap,
           1024: self.do_open, 
        }.get(int.from_bytes(syscall_num, 'little'), self.null)
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
    def null(self, a0, a1, a2, a3, a4, a5, **kwargs):
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
    def do_openat(self, a0, a1, a2, a3, a4, a5, **kwargs):
        if 'arg' in kwargs.keys():
            _dir_fd = int.from_bytes(a0[:4], 'little', signed=True)
            kwargs.get('arg')[0] += bytes([0])
            _pathname = kwargs.get('arg')[0][:kwargs.get('arg')[0].index(0)].decode('ascii')
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
    def do_close(self, a0, a1, a2, a3, a4, a5, **kwargs):
        logging.info('do_close(): a0     : {}'.format(a0))
        try:
            _fd = int.from_bytes(a0, 'little')
            os.close(_fd)
            _retval = 0
        except:
            _retval = -1
        logging.info('close() -> {}'.format(_retval))
        return {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': list(_retval.to_bytes(8, 'little', signed=True))
                },
            },
        }
    def do_lseek(self, a0, a1, a2, a3, a4, a5, **kwargs):
        logging.info('do_lseek(): a0     : {}'.format(a0))
        logging.info('do_lseek(): a1     : {}'.format(a1))
        logging.info('do_lseek(): a2     : {}'.format(a2))
        logging.info('do_lseek(): kwargs : {}'.format(kwargs))
        try:
            _fd = int.from_bytes(a0, 'little')
            _off = int.from_bytes(a1, 'little')
            _whence = {
                0: os.SEEK_SET,
                1: os.SEEK_CUR,
                2: os.SEEK_END,
            }.get(int.from_bytes(a2, 'little'))
            _retval = os.lseek(_fd, _off, _whence)
        except:
            _retval = -1
        logging.info('lseek() -> {}'.format(_retval))
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
    def do_read(self, a0, a1, a2, a3, a4, a5, **kwargs):
        logging.info('do_read(): a0     : {}'.format(a0))
        logging.info('do_read(): a1     : {}'.format(a1))
        logging.info('do_read(): a2     : {}'.format(a2))
        logging.info('do_read(): kwargs : {}'.format(kwargs))
        try:
            _fd = int.from_bytes(a0, 'little')
            _buf = int.from_bytes(a1, 'little')
            _count = int.from_bytes(a2, 'little')
            _data = os.read(_fd, _count)
            _retval = len(_data)
        except:
            _retval = -1
        logging.info('read({}, {}, {}) -> {}'.format(_fd, _buf, _count, _retval))
        return {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': list(_retval.to_bytes(8, 'little', signed=True)),
                },
            },
            'poke': {
                'addr': a1, # FIXME: convert this (i.e.: int.from_bytes(a3, 'little')) here
                'data': list(_data),
            },
        }
    def do_write(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _len = int.from_bytes(a2, 'little')
        if 'arg' in kwargs.keys():
            _fd = int.from_bytes(a0[:4], 'little', signed=True)
            _buf = kwargs.get('arg')[0]
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
    def do_writev(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _sys_ret = 0
        if 'arg' not in kwargs.keys():
            _len = 256
            return {
                'done': False,
                'peek': {
                    'addr': int.from_bytes(a1, 'little'),
                    'size': _len,
                }
            }
        else:
            _iovcnt = int.from_bytes(a2, 'little')
            if len(kwargs.get('arg')) <= _iovcnt:
                _iov_so_far = len(kwargs.get('arg')) - 1
                _p = _iov_so_far * (self.SIZEOF_VOID_P + self.SIZEOF_SIZE_T)
                _addr = int.from_bytes(kwargs.get('arg')[0][_p:(self.SIZEOF_VOID_P + _p)], 'little')
                _p += self.SIZEOF_VOID_P
                _size = int.from_bytes(kwargs.get('arg')[0][_p:(self.SIZEOF_SIZE_T + _p)], 'little')
                return {
                    'done': False,
                    'peek': {
                        'addr': _addr,
                        'size': _size,
                    }
                }
            else:
                for x in range(1, 1 + _iovcnt):
                    _fd = int.from_bytes(a0, 'little')
                    _buf = kwargs.get('arg')[x]
                    os.write(_fd, _buf)
                    _sys_ret += len(_buf)
                logging.info('writev({}, {}, {}) -> {}'.format(_fd, int.from_bytes(a1, 'little'), _iovcnt, _sys_ret))
        return {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': list(_sys_ret.to_bytes(8, 'little', signed=True)),
                },
            },
        }
    def do_readlinkat(self, a0, a1, a2, a3, a4, a5, **kwargs):
        # ssize_t readlinkat(int dirfd, const char *restrict pathname, char *restrict buf, size_t bufsiz);
        #
        # see: https://man7.org/linux/man-pages/man2/readlinkat.2.html
        if 'arg' in kwargs.keys():
            _dir_fd = int.from_bytes(a0, 'little', signed=True)
            kwargs.get('arg')[0] += bytes([0])
            _pathname = kwargs.get('arg')[0][:kwargs.get('arg')[0].index(0)].decode('ascii')
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
    def do_exit(self, a0, a1, a2, a3, a4, a5, **kwargs):
        logging.info('do_exit(): a0     : {}'.format(a0))
        logging.info('do_exit(): kwargs : {}'.format(kwargs))
        return {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': a0,
                },
            },
            'shutdown': None,
        }
    def do_fstat(self, a0, a1, a2, a3, a4, a5, **kwargs):
        logging.info('do_fstat(): a0     : {}'.format(a0))
        logging.info('do_fstat(): a1     : {}'.format(a1))
        logging.info('do_fstat(): kwargs : {}'.format(kwargs))
        try:
            _os_fstat = os.fstat(int.from_bytes(a0, 'little'))
            _success = 0
        except:
            _success = -1
        logging.info('fstat() -> {}'.format(_success))
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
                'addr': a1,
                'data': list(b''.join([
                    _os_fstat.st_dev.to_bytes(4, 'little', signed=True),
                    _os_fstat.st_ino.to_bytes(4, 'little', signed=True),
                    _os_fstat.st_mode.to_bytes(4, 'little', signed=True),
                    _os_fstat.st_nlink.to_bytes(2, 'little'),
                    _os_fstat.st_uid.to_bytes(4, 'little', signed=True),
                    _os_fstat.st_gid.to_bytes(4, 'little', signed=True),
                    (0).to_bytes(4, 'little', signed=True),
                    _os_fstat.st_size.to_bytes(8, 'little', signed=True)
                ])),
            },
        }
    def do_futex(self, a0, a1, a2, a3, a4, a5, **kwargs):
        # int futex(int *uaddr, int op, int val, const struct timespec *timeout, int *uaddr2, int val3)
        #
        # see: https://linux.die.net/man/2/futex
        FUTEX_PRIVATE_FLAG = 128
        ERESTARTSYS = 512 # see: https://elixir.bootlin.com/linux/latest/source/include/linux/errno.h#L14
        EAGAIN = 11 # see: https://elixir.bootlin.com/linux/latest/source/include/uapi/asm-generic/errno-base.h#L15
        EINVAL = 22 # see: https://elixir.bootlin.com/linux/latest/source/include/uapi/asm-generic/errno-base.h#L26
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
            if 'arg' in kwargs.keys():
                _u = int.from_bytes(kwargs.get('arg')[0], 'little', signed=True)
                # NOTE: Since this code is supposed to mimick an underlying
                # kernel, it will behave here as if the FUTEX_WAIT has already
                # happened and we are resuming execution following a FUTEX_WAKE
                # see: https://elixir.bootlin.com/linux/latest/source/kernel/futex/waitwake.c#L632
                # see: https://www.man7.org/linux/man-pages/man2/futex.2.html#RETURN_VALUE
                _retval = 0
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
                    'poke': {   # HACK: this needs more study; I don't know why it seems to work
                        'addr': a0,
                        'data': list((0).to_bytes(8, 'little')),
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
        elif 'FUTEX_WAKE' in _op:
            _retval = 1
            logging.info('futex({}, {}, {}, {}, {}, {}) -> {}'.format(
                _uaddr, _op, _val, _timeout_p, a4, a5,
                _retval
            ))
            return self.null(a0, a1, a2, a3, a4, a5, **{
                **kwargs,
                **{'retval': _retval}, # NOTE: return that 1 thread was woken up; see: https://www.man7.org/linux/man-pages/man2/futex.2.html#RETURN_VALUE
            })
        return self.null(a0, a1, a2, a3, a4, a5, **kwargs)
    def do_uname(self, a0, a1, a2, a3, a4, a5, **kwargs):
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
    def do_getpid(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _sys_ret = 5
        return self.null(a0, a1, a2, a3, a4, a5, **{
            **kwargs,
            **{
                'retval': _sys_ret,
                'log': 'getpid() -> {}'.format(_sys_ret),
            },
        })
    def do_getuid(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _sys_ret = 0
        return self.null(a0, a1, a2, a3, a4, a5, **{
            **kwargs,
            **{
                'retval': _sys_ret,
                'log': 'getuid() -> {}'.format(_sys_ret),
            },
        })
    def do_geteuid(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _sys_ret = 0
        return self.null(a0, a1, a2, a3, a4, a5, **{
            **kwargs,
            **{
                'retval': _sys_ret,
                'log': 'geteuid() -> {}'.format(_sys_ret),
            },
        })
    def do_getgid(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _sys_ret = 0
        return self.null(a0, a1, a2, a3, a4, a5, **{
            **kwargs,
            **{
                'retval': _sys_ret,
                'log': 'getgid() -> {}'.format(_sys_ret),
            },
        })
    def do_getegid(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _sys_ret = 0
        return self.null(a0, a1, a2, a3, a4, a5, **{
            **kwargs,
            **{
                'retval': _sys_ret,
                'log': 'getegid() -> {}'.format(_sys_ret),
            },
        })
    def do_brk(self, a0, a1, a2, a3, a4, a5, **kwargs):
        # [T]he actual Linux system call returns the new program break on success.
        # On failure, the system call returns the current break. The glibc wrapper
        # function does some work (i.e., checks whether the new break is less than
        # addr) to provide the 0 and -1 return values described above.
        #
        # see: https://www.man7.org/linux/man-pages/man2/brk.2.html ("C library/kernel differences")
        #      https://gist.github.com/nikAizuddin/f4132721126257ec4345
        _endds = int.from_bytes(a0, 'little')
        _sys_ret = _endds
        logging.info('brk({:08x}) -> {:08x}'.format(_endds, _sys_ret))
        return {
            'done': True,
            'output': {
                'register': {
                    'cmd': 'set',
                    'name': 10,
                    'data': list(_sys_ret.to_bytes(8, 'little')),
                },
            },
        }
    def do_munmap(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _sys_ret = 0
        return self.null(a0, a1, a2, a3, a4, a5, **{
            **kwargs,
            **{
                'retval': _sys_ret,
                'log': 'munmap({:08x}, {:08x}) -> {}'.format(int.from_bytes(a0, 'little'), int.from_bytes(a1, 'little'), _sys_ret),
            },
        })
    def do_mmap(self, a0, a1, a2, a3, a4, a5, **kwargs):
        _addr = int.from_bytes(a0, 'little')
        _length = int.from_bytes(a1, 'little')
        _prot = int.from_bytes(a2, 'little')
        _flags = int.from_bytes(a3, 'little')
        _fd = int.from_bytes(a4, 'little', signed=True)
        _offset = int.from_bytes(a5, 'little')
        if -1 == _fd:
            _sys_ret = self.state.get('mmap', 0x20000000)
            _mmap  = _sys_ret + _length
            _mmap += (self.PAGESIZE if (_mmap & (self.PAGESIZE - 1)) else 0)
            _mmap |= (self.PAGESIZE - 1)
            _mmap ^= (self.PAGESIZE - 1)
            self.state.update({'mmap': _mmap})
            logging.info('mmap({:08x}, {:08x}, {}, {}, {}, {}) -> {:08x}'.format(_addr, _length, _prot, _flags, _fd, _offset, _sys_ret))
            return {
                'done': True,
                'output': {
                    'register': {
                        'cmd': 'set',
                        'name': 10,
                        'data': list(_sys_ret.to_bytes(8, 'little', signed=True)),
                    },
                },
            }
        logging.info('mmap({:08x}, {:08x}, {}, {}, {}, {})'.format(_addr, _length, _prot, _flags, _fd, _offset))
        return self.null(a0, a1, a2, a3, a4, a5, **kwargs)
    def do_open(self, a0, a1, a2, a3, a4, a5, **kwargs):
        if 'arg' in kwargs.keys():
            kwargs.get('arg')[0] += bytes([0])
            _pathname = kwargs.get('arg')[0][:kwargs.get('arg')[0].index(0)].decode('ascii')
            _flags = int.from_bytes(a1, 'little')
            try:
                _fd = os.open(_pathname, _flags)
            except:
                logging.info('do_open(): a0        : {}'.format(a0))
                logging.info('do_open(): a1        : {}'.format(a1))
                logging.info('do_open(): _pathname : {} ({})'.format(_pathname, len(_pathname)))
                _fd = -1
            logging.info('open({}, {}) -> {}'.format(_pathname, _flags, _fd))
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
            _len = 256 # HACK: This is the pathname of SYS_open, which has
                    # function prototype open(const char * pathname, int flags);
                    # see: https://man7.org/linux/man-pages/man2/open.2.html. How long is
                    # the pathname? Who knows? It could, in theory, be much more than 256
                    # bytes, but I can't be bothered with making this general-purpose right now.
            _retval = {
                'done': False,
                'peek': {
                    'addr': int.from_bytes(a0, 'little'),
                    'size': _len,
                },
            }
        return _retval