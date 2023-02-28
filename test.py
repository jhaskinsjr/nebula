# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import re
import random
import argparse
import struct
import subprocess
import functools
import pdb

class Harness:
    def __init__(self):
        self.tests = {
            'c.lui': self.c_lui,
            'c.add': self.c_add,
            'c.sub': self.c_sub,
            'c.xor': self.c_xor,
            'c.or': self.c_or,
            'c.and': self.c_and,
            'c.addw': self.c_addw,
            'c.subw': self.c_subw,
            'c.addi16sp': self.c_addi16sp,
            'c.addi4spn': self.c_addi4spn,
            'c.mv': self.c_mv,
            'c.li': self.c_li,
            'c.addi': self.c_addi,
            'c.slli': self.c_slli,
            'c.srli': self.c_srli,
            'c.srai': self.c_srai,
            'slli': self.slli,
            'slliw': self.slliw,
            'srli': self.srli,
            'srliw': self.srliw,
            'srai': self.srai,
            'sraiw': self.sraiw,
            'andi': self.andi,
            'addi': self.addi,
            'addiw': self.addiw,
            'add': self.add,
            'sub': self.sub,
            'addw': self.addw,
            'subw': self.subw,
            'mulw': self.mulw,
            'divw': self.divw,
            'divuw': self.divuw,
            'remw': self.remw,
            'remuw': self.remuw,
            'sll': self.sll,
            'sllw': self.sllw,
            'srl': self.srl,
            'srlw': self.srlw,
            'sra': self.sra,
            'sraw': self.sraw,
            'and': self.test_and,
            'or': self.test_or,
            'xor': self.test_xor,
            'slt': self.slt,
            'sltu': self.sltu,
            'slti': self.slti,
            'sltiu': self.sltiu,
            'lui': self.lui,
#            'auipc': self.auipc, # FIXME: self._start_pc is not 0x00000000
        }
        self._start_pc = 0x00000000
        self._sp = 0x80000000
    def c_lui(self):
        _const = random.randint(1, 2**5 - 1)
        _assembly  = ['c.lui x15, {}'.format(_const)]
        _assembly += ['c.mv x31, x15']
        _const <<= 12
        _b17 = (_const >> 17) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b17 << x, range(18, 32)), _const)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_add(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['c.add x15, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = _const_0 + _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_sub(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['c.sub x15, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = _const_0 - _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_xor(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['c.xor x15, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = _const_0 ^ _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_or(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**20 - 1
#        _const_1 = 8
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['c.or x15, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = _const_0 | _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_and(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**20 - 1
#        _const_1 = 8
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['c.and x15, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = _const_0 & _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_addw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**20 - 1
#        _const_1 = 8
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['c.addw x15, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = (_const_0 + _const_1) & ((2 ** 32) - 1)
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def c_subw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**20 - 1
#        _const_1 = 8
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['c.subw x15, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = (_const_0 - _const_1) & ((2 ** 32) - 1)
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def c_addi16sp(self):
        _const = random.choice([
            random.randint(-2**5, -1) << 4,
            random.randint(1, 2**5 - 1) << 4,
        ])
#        _const = -32
        _assembly  = ['c.addi16sp x2, {}'.format(_const)]
        _assembly += ['c.mv x31, x2']
        _correct_answer = _const + self._sp
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_addi4spn(self):
        _const = (random.randint(1, 2**9 - 1) | 0b11) ^ 0b11
#        _const = 4
        _assembly  = ['c.addi4spn x15, x2, {}'.format(_const)]
        _assembly += ['c.mv x31, x15']
        _correct_answer  = _const
        _correct_answer += self._sp
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_mv(self):
        _const = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x30, {}'.format(_const)]
        _assembly += ['c.mv x31, x30']
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_li(self):
        _const = random.randint(0, 2**5 - 1)
        _assembly = ['c.li x31, {}'.format(_const)]
        _b05 = (_const >> 5) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b05 << x, range(6, 16)), _const)
        _correct_answer = int.from_bytes(struct.Struct('<H').pack(_correct_answer), 'little', signed=True)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_addi(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.choice([random.randint(0, 2**5 - 1), random.randint(-2**5, -1)])
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['c.addi x15, {}'.format(_const_1)]
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _correct_answer = _const_0 + _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_slli(self):
        _const = random.randint(0, 2**20 - 1)
        _shamt = random.randint(1, 2**6 - 1)
        _assembly  = ['lui x31, {}'.format(_const)]
        _assembly += ['c.slli x31, {}'.format(_shamt)]
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_const << 12), 'little', signed=True)
        _correct_answer <<= _shamt
        _correct_answer &= 2 ** 64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def c_srli(self):
        _const = random.randint(0, 2**20 - 1)
        _shamt = random.randint(1, 2**6 - 1)
        _mask = ((2 ** _shamt) - 1) << (64 - _shamt)
        _assembly  = ['lui x15, {}'.format(_const)]
        _assembly += ['c.srli x15, {}'.format(_shamt)]
        _assembly += ['c.mv x31, x15']
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_const << 12), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer |= _mask
        _correct_answer ^= _mask
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def c_srai(self):
        _const = random.randint(0, 2**20 - 1)
        _shamt = random.randint(1, 2**6 - 1)
        _assembly  = ['lui x15, {}'.format(_const)]
        _assembly += ['c.srai x15, {}'.format(_shamt)]
        _assembly += ['c.mv x31, x15']
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_const << 12), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def slli(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = 17
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 0x20
        _assembly  = ['lui x30, {}'.format(_const)]
        _assembly += ['slli x31, x30, {}'.format(_shamt)]
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer <<= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def slliw(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = 178273
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 5
        _assembly  = ['lui x30, {}'.format(_const)]
        _assembly += ['slliw x31, x30, {}'.format(_shamt)]
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer <<= _shamt
        _correct_answer &= 2**32 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def srli(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _mask = ((2 ** _shamt) - 1) << (64 - _shamt)
        _assembly  = ['lui x30, {}'.format(_const)]
        _assembly += ['srli x31, x30, {}'.format(_shamt)]
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer |= _mask
        _correct_answer ^= _mask
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def srliw(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _mask = ((2 ** _shamt) - 1) << (64 - _shamt)
        _assembly  = ['lui x30, {}'.format(_const)]
        _assembly += ['srliw x31, x30, {}'.format(_shamt)]
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer &= (2**32 - 1)
        _correct_answer >>= _shamt
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def srai(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _assembly  = ['lui x30, {}'.format(_const)]
        _assembly += ['srai x31, x30, {}'.format(_shamt)]
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def sraiw(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _assembly  = ['lui x30, {}'.format(_const)]
        _assembly += ['sraiw x31, x30, {}'.format(_shamt)]
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**32 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def andi(self):
        _const_0 = random.randint(0, 2**20 - 1)
#        _const_0 = 3614366011 >> 12
#        _const_0 = 3614361915 >> 12
#        _const_0 = 1614361915 >> 12
        _assembly  = ['lui x30, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little', signed=True)
        _const_1 = random.randint(-2**11, 2**11 - 1)
#        _const_1 = -1733
        _assembly += ['addi x30, x30, {}'.format(_const_1)]
        _const_0 += _const_1
        _const_2 = random.randint(-2**11, 2**11 - 1)
#        _const_2 = -2013
        _assembly += ['andi x31, x30, {}'.format(_const_2)]
#        print('_const_0 : {:15} {}'.format(_const_0, list(map(lambda x: '{:08b}'.format(x), _const_0.to_bytes(8, 'little', signed=True)))))
#        print('_const_1 : {:15} {}'.format(_const_1, list(map(lambda x: '{:08b}'.format(x), _const_1.to_bytes(8, 'little', signed=True)))))
#        print('_const_2 : {:15} {}'.format(_const_2, list(map(lambda x: '{:08b}'.format(x), _const_2.to_bytes(8, 'little', signed=True)))))
        _correct_answer = int.from_bytes(map(
            lambda a, b: a & b,
            _const_0.to_bytes(8, 'little', signed=True),
            _const_2.to_bytes(8, 'little', signed=True),
        ), 'little', signed=True)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def addi(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.choice([random.randint(0, 2**5 - 1), random.randint(-2**5, -1)])
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['addi x15, x15, {}'.format(_const_1)]
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _correct_answer = _const_0 + _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def addiw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['addiw x15, x15, {}'.format(_const_1)]
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _correct_answer = ((_const_0 + _const_1) << 32) >> 32
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def add(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x29, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little', signed=True)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly += ['lui x30, {}'.format(_const_1)]
        _const_1 <<= 12
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1), 'little', signed=True)
        _assembly += ['add x31, x29, x30']
        _correct_answer = _const_0 + _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def sub(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x29, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little', signed=True)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly += ['lui x30, {}'.format(_const_1)]
        _const_1 <<= 12
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1), 'little', signed=True)
        _assembly += ['sub x31, x29, x30']
        _correct_answer = _const_0 - _const_1
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def addw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**20 - 1
#        _const_1 = 8
        _assembly  = ['lui x13, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['addw x15, x13, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = (_const_0 + _const_1) & ((2 ** 32) - 1)
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def subw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**20 - 1
#        _const_1 = 8
        _assembly  = ['lui x13, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['subw x15, x13, x14']
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = (_const_0 - _const_1) & ((2 ** 32) - 1)
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def mulw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**20 - 1
#        _const_1 = 8
#        _const_0 = 2**16
#        _const_1 = 1
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['mulw x31, x15, x14']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer = (_const_0 * _const_1) & ((2**32) - 1)
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def divw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**15 - 1
#        _const_1 = 2**4 - 1
#        _const_0 = 2**16
#        _const_1 = 1
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['divw x31, x15, x14']
        _correct_answer  = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _correct_answer /= int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer  = int(_correct_answer)
#        _b31 = (1 if 0 > _correct_answer else 0)
#        _correct_answer &= ((2**32) - 1)
#        _correct_answer  = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer  = list(_correct_answer.to_bytes(8, 'little', signed=True))
#        pdb.set_trace()
        return _correct_answer, _assembly
    def divuw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**15 - 1
#        _const_1 = 2**4 - 1
#        _const_0 = 2**20 - 1
#        _const_1 = 1
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['divuw x31, x15, x14']
        _correct_answer  = _const_0 << 12
        _correct_answer /= _const_1 << 12
        _correct_answer  = int(_correct_answer)
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer  = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer  = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def remw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**15 - 1
#        _const_1 = 2**4 - 1
#        _const_0 = 2**16
#        _const_1 = 1
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['remw x31, x15, x14']
        _correct_answer  = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _correct_answer %= int.from_bytes(struct.Struct('<I').pack(_const_1 << 12), 'little', signed=True)
        _correct_answer  = list(_correct_answer.to_bytes(8, 'little', signed=True))
#        pdb.set_trace()
        return _correct_answer, _assembly
    def remuw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**20 - 1)
#        _const_0 = 2**15 - 1
#        _const_1 = 2**4 - 1
#        _const_0 = 2**20 - 1
#        _const_1 = 1
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['lui x14, {}'.format(_const_1)]
        _assembly += ['remuw x31, x15, x14']
        _correct_answer  = _const_0 << 12
        _correct_answer %= _const_1 << 12
        _correct_answer  = list(int.from_bytes(_correct_answer.to_bytes(4, 'little'), 'little', signed=True).to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def sll(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = 17
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 0x20
        _assembly  = ['c.li x15, {}'.format(_shamt)]
        _assembly += ['lui x30, {}'.format(_const)]
        _assembly += ['sll x31, x30, x15']
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer <<= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def sllw(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = 178273
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 5
        _assembly  = ['c.li x15, {}'.format(_shamt)]
        _assembly += ['lui x30, {}'.format(_const)]
        _assembly += ['sllw x31, x30, x15']
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer <<= _shamt
        _correct_answer &= 2**32 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def srl(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _mask = ((2 ** _shamt) - 1) << (64 - _shamt)
        _assembly  = ['c.li x15, {}'.format(_shamt)]
        _assembly += ['lui x30, {}'.format(_const)]
        _assembly += ['srl x31, x30, x15']
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer |= _mask
        _correct_answer ^= _mask
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def srlw(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _mask = ((2 ** _shamt) - 1) << (64 - _shamt)
        _assembly  = ['c.li x15, {}'.format(_shamt)]
        _assembly += ['lui x30, {}'.format(_const)]
        _assembly += ['srlw x31, x30, x15']
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer &= (2**32 - 1)
        _correct_answer >>= _shamt
#        _b31 = (_correct_answer >> 31) & 0b1
#        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def sra(sra):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _assembly  = ['c.li x15, {}'.format(_shamt)]
        _assembly += ['lui x30, {}'.format(_const)]
        _assembly += ['sra x31, x30, x15']
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**64 - 1
        _correct_answer = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little')
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def sraw(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 7
        _assembly  = ['c.li x15, {}'.format(_shamt)]
        _assembly += ['lui x30, {}'.format(_const)]
        _assembly += ['sraw x31, x30, x15']
        _correct_answer = _const << 12
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_correct_answer), 'little', signed=True)
        _correct_answer >>= _shamt
        _correct_answer &= 2**32 - 1
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def test_and(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x29, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little', signed=True)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly += ['lui x30, {}'.format(_const_1)]
        _const_1 <<= 12
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1), 'little', signed=True)
        _assembly += ['and x31, x29, x30']
        _correct_answer = int.from_bytes(map(
            lambda a, b: a & b,
            _const_0.to_bytes(8, 'little', signed=True),
            _const_1.to_bytes(8, 'little', signed=True),
        ), 'little', signed=True)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def test_or(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x29, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little', signed=True)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly += ['lui x30, {}'.format(_const_1)]
        _const_1 <<= 12
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1), 'little', signed=True)
        _assembly += ['or x31, x29, x30']
        _correct_answer = int.from_bytes(map(
            lambda a, b: a | b,
            _const_0.to_bytes(8, 'little', signed=True),
            _const_1.to_bytes(8, 'little', signed=True),
        ), 'little', signed=True)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def test_xor(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x29, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little', signed=True)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly += ['lui x30, {}'.format(_const_1)]
        _const_1 <<= 12
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1), 'little', signed=True)
        _assembly += ['xor x31, x29, x30']
        _correct_answer = int.from_bytes(map(
            lambda a, b: a ^ b,
            _const_0.to_bytes(8, 'little', signed=True),
            _const_1.to_bytes(8, 'little', signed=True),
        ), 'little', signed=True)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def slt(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x29, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little', signed=True)
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly += ['lui x30, {}'.format(_const_1)]
        _assembly += ['slt x31, x29, x30']
        _const_1 <<= 12
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1), 'little', signed=True)
        _correct_answer = list((1 if _const_0 < _const_1 else 0).to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def sltu(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _assembly  = ['lui x29, {}'.format(_const_0)]
        _const_0 <<= 12
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0), 'little')
        _const_1 = random.randint(0, 2**20 - 1)
        _assembly += ['lui x30, {}'.format(_const_1)]
        _assembly += ['sltu x31, x29, x30']
        _const_1 <<= 12
        _const_1 = int.from_bytes(struct.Struct('<I').pack(_const_1), 'little')
        _correct_answer = list((1 if _const_0 < _const_1 else 0).to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def slti(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.choice([random.randint(0, 2**5 - 1), random.randint(-2**5, -1)])
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['slti x31, x15, {}'.format(_const_1)]
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _correct_answer = (1 if _const_0 < _const_1 else 0)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def sltiu(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(0, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['sltiu x31, x15, {}'.format(_const_1)]
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little')
        _correct_answer = (1 if _const_0 < _const_1 else 0)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def lui(self):
        _const = random.randint(0, 2**20 - 1)
#        _const = 2**20 - 1
        _assembly = ['lui x31, {}'.format(_const)]
        _correct_answer = int.from_bytes(struct.Struct('<I').pack(_const << 12), 'little', signed=True)
        _correct_answer = list(struct.Struct('<q').pack(_correct_answer))
        return _correct_answer, _assembly
    def auipc(self):
        _const = random.randint(0, 2**20 - 1)
#        print('_const : {}'.format(_const))
        _assembly = ['auipc x31, {}'.format(_const)]
        _correct_answer  = _const << 12
#        print('_correct_answer : {:016x}'.format(_correct_answer))
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer  = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
#        print('_correct_answer : {:016x}'.format(_correct_answer))
        _correct_answer  = int.from_bytes(struct.Struct('<Q').pack(_correct_answer), 'little', signed=True)
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('self._start_pc : {}'.format(self._start_pc))
        _correct_answer += self._start_pc
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
#        print('_correct_answer : {}'.format(_correct_answer))
        return _correct_answer, _assembly
    def generate(self, args, test):
        _correct_answer, _assembly = self.tests.get(test)()
        _n_instruction = len(_assembly)
        _program  = '\n'.join(list(map(lambda x: '\t{}'.format(x), ['.text', '.globl\t_start', '.type\t_start, @function'])) + [''])
        _program += '\n'.join(['_exit: '] + list(map(lambda x: '\t{}'.format(x), ['add x17, x0, 93', 'ecall'])) + [''])
        _program += '\n'.join(['_start:'] + list(map(lambda x: '\t{}'.format(x), _assembly + ['jal x1, _exit'])))
        _program += '\n'
        with open(os.path.join(args.dir, 'src', '{}.s'.format(test)), 'w+') as fp: fp.write(_program)
        subprocess.run('{} -o {} -march=rv64gc {} -nostartfiles'.format(
            args.compiler,
            os.path.join(args.dir, 'bin', '{}'.format(test)),
            os.path.join(args.dir, 'src', '{}.s'.format(test))
        ).split())
        _script  = ['# μService-SIMulator test harness script']
#        _script += ['port 10000']
        _script += ['service pipelines/bergamot/implementation/{}:localhost'.format(s) for s in ('simplecore.py', 'regfile.py', 'mainmem.py', 'decode.py', 'execute.py')]
        _script += ['spawn']
        _script += ['config mainmem:peek_latency_in_cycles 1']
        _script += ['loadbin 0x{:08x} 0x{:08x} _start'.format(self._sp, self._start_pc)]
#        _script += ['config max_instructions {}'.format(_n_instruction)]
        _script += ['run']
        _script += ['shutdown']
        with open(os.path.join(args.dir, 'test.ussim'), 'w+') as fp: fp.write('\n'.join(_script))
        _cmd = 'python3 launcher.py --log {} --max_instructions {} -- {} {} {}'.format(
            args.dir,
            _n_instruction,
            args.port,
            os.path.join(args.dir, 'test.ussim'),
            os.path.join(args.dir, 'bin', '{}'.format(test))
        )
        if args.debug: print('_cmd : {}'.format(_cmd))
        _result = subprocess.run(
            _cmd.split(),
            capture_output=True,
        )
        _stdout = _result.stdout.decode('utf-8').split('\n')
        if args.debug: print('\n'.join(_stdout))
        _regfile_py_log = None
        with open(os.path.join(args.dir, 'regfile.py.log'), 'r') as fp: _regfile_py_log = fp.readlines()
        _x31 = list(filter(lambda x: re.search('register 31 : ', x), _regfile_py_log))[-1].split(':')[1]
        _x31 = eval(_x31)
        print('do_test(..., {}): {} (_correct_answer) ?= {} (_x31) -> {}'.format(
            test,
            _correct_answer,
            _x31,
            _correct_answer ==_x31
        ))
        if _x31 != _correct_answer:
            print('\n'.join(_stdout))
            assert False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='μService-SIMulator')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('port', type=int, help='port for accepting connections')
    parser.add_argument('compiler', type=str, help='RISC-V cross-compiler')
    parser.add_argument('dir', type=str, help='directory to put tests')
    args = parser.parse_args()
    assert os.path.exists(args.dir), 'Cannot open dir, {}!'.format(args.dir)
    if not os.path.exists(os.path.join(args.dir, 'src')): os.mkdir(os.path.join(args.dir, 'src'))
    if not os.path.exists(os.path.join(args.dir, 'bin')): os.mkdir(os.path.join(args.dir, 'bin'))
    if args.debug: print('args : {}'.format(args))
    _harness = Harness()
#    [_harness.generate(args, n) for n in _harness.tests.keys()]
#    _harness.generate(args, 'c.lui')
#    _harness.generate(args, 'c.add')
#    _harness.generate(args, 'c.sub')
#    _harness.generate(args, 'c.xor')
#    _harness.generate(args, 'c.or')
#    _harness.generate(args, 'c.and')
#    _harness.generate(args, 'c.addw')
#    _harness.generate(args, 'c.subw')
#    _harness.generate(args, 'c.addi16sp')
#    _harness.generate(args, 'c.addi4spn')
#    _harness.generate(args, 'c.mv')
#    _harness.generate(args, 'c.li')
#    _harness.generate(args, 'c.addi')
#    _harness.generate(args, 'c.slli')
#    _harness.generate(args, 'c.srli')
#    _harness.generate(args, 'c.srai')
#    _harness.generate(args, 'slli')
#    _harness.generate(args, 'slliw')
#    _harness.generate(args, 'srli')
#    _harness.generate(args, 'srliw')
#    _harness.generate(args, 'srai')
#    _harness.generate(args, 'sraiw')
#    _harness.generate(args, 'andi')
#    _harness.generate(args, 'addi')
#    _harness.generate(args, 'addiw')
#    _harness.generate(args, 'add')
#    _harness.generate(args, 'sub')
#    _harness.generate(args, 'addw')
#    _harness.generate(args, 'subw')
#    _harness.generate(args, 'mulw')
#    _harness.generate(args, 'divw')
#    _harness.generate(args, 'divuw')
#    _harness.generate(args, 'remw')
#    _harness.generate(args, 'remuw')
#    _harness.generate(args, 'sll')
#    _harness.generate(args, 'sllw')
#    _harness.generate(args, 'srl')
#    _harness.generate(args, 'srlw')
#    _harness.generate(args, 'sra')
#    _harness.generate(args, 'sraw')
#    _harness.generate(args, 'slt')
    _harness.generate(args, 'sltu')
#    _harness.generate(args, 'and')
#    _harness.generate(args, 'or')
#    _harness.generate(args, 'xor')
#    _harness.generate(args, 'slti')
#    _harness.generate(args, 'sltiu')
#    _harness.generate(args, 'lui')
#    _harness.generate(args, 'auipc')