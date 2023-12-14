# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import sys
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
            'c.andi': self.c_andi,
            'c.addiw': self.c_addiw,
            'c.beqz': self.c_beqz,
            'c.bnez': self.c_bnez,
            'c.nop': self.c_nop,
            'c.lw': self.c_lw,
            'c.ld': self.c_ld,
            'c.lwsp': self.c_lwsp,
            'c.ldsp': self.c_ldsp,
            'c.sw': self.c_sw,
            'c.sd': self.c_sd,
            'c.swsp': self.c_swsp,
            'c.sdsp': self.c_sdsp,
            'sb': self.sb,
            'sh': self.sh,
            'sw': self.sw,
            'sd': self.sd,
            'lb': self.lb,
            'lh': self.lh,
            'lw': self.lw,
            'ld': self.ld,
            'lbu': self.lbu,
            'lhu': self.lhu,
            'lwu': self.lwu,
            'slli': self.slli,
            'slliw': self.slliw,
            'srli': self.srli,
            'srliw': self.srliw,
            'srai': self.srai,
            'sraiw': self.sraiw,
            'andi': self.andi,
            'ori': self.ori,
            'xori': self.xori,
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
            'beq': self.beq,
            'bne': self.bne,
            'blt': self.blt,
            'bge': self.bge,
            'bltu': self.bltu,
            'bgeu': self.bgeu,
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
        _const = random.randint(1, 2**7 - 1) << 2
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
    def c_andi(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(-2**4, 2**4 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['c.andi x15, {}'.format(_const_1)]
        _assembly += ['c.mv x31, x15']
#        _const_0 = int.from_bytes(struct.Struct('<q').pack(_const_0 << 12), 'little', signed=True)
#        _const_0 &= (2**64) - 1
#        _const_1 = int.from_bytes(struct.Struct('<q').pack(_const_1), 'little', signed=True)
#        _const_1 &= (2**64) - 1
        _const_0 = list(int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True).to_bytes(8, 'little', signed=True))
        _const_1 = list(int.from_bytes(struct.Struct('<i').pack(_const_1), 'little', signed=True).to_bytes(8, 'little', signed=True))
        print('_const_0        : {:016x}'.format(int.from_bytes(_const_0, 'little')))
        print('_const_1        : {:016x}'.format(int.from_bytes(_const_1, 'little')))
#        _correct_answer = _const_0 & _const_1
        _correct_answer = list(map(lambda a, b: a & b, _const_0, _const_1))
        print('_correct_answer : {:016x}'.format(int.from_bytes(_correct_answer, 'little')))
#        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_addiw(self):
        _const_0 = random.randint(0, 2**20 - 1)
        _const_1 = random.randint(-2**4, 2**4 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0)]
        _assembly += ['c.addiw x15, {}'.format(_const_1)]
        _assembly += ['c.mv x31, x15']
        _const_0 = int.from_bytes(struct.Struct('<I').pack(_const_0 << 12), 'little', signed=True)
        _correct_answer = ((_const_0 + _const_1) << 32) >> 32
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def c_beqz(self):
        _const = (0 if random.randint(0, 1) else random.randint(-2**11, 2**11 - 1))
        _assembly  = ['jal x0, do_test']
        _assembly += ['match:']
        _assembly += ['addi x31, x0, 1']
        _assembly += ['jal x0, done']
        _assembly += ['do_test:']
        _assembly += ['addi x15, x0, {}'.format(_const)]
        _assembly += ['c.beqz x15, match']
        _assembly += ['done:']
        _correct_answer = list((1 if 0 == _const else 0).to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def c_bnez(self):
        _const = (0 if random.randint(0, 1) else random.randint(-2**11, 2**11 - 1))
        _assembly  = ['jal x0, do_test']
        _assembly += ['match:']
        _assembly += ['addi x31, x0, 1']
        _assembly += ['jal x0, done']
        _assembly += ['do_test:']
        _assembly += ['addi x15, x0, {}'.format(_const)]
        _assembly += ['c.bnez x15, match']
        _assembly += ['done:']
        _correct_answer = list((1 if 0 != _const else 0).to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def c_nop(self):
        _assembly = ['c.nop']
        _correct_answer = list((0).to_bytes(8, 'little'))
        return _correct_answer, _assembly
    def c_lw(self):
        _nbytes = 4
        _mnemonic = 'c.lw'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**7 - 1) | 0b11) ^ 0b11
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x14, x0, 1']
        _assembly += ['slli x14, x14, 20']
        _assembly += ['sd x15, {}(x14)'.format(_offset)]
        _assembly += ['{} x15, {}(x14)'.format(_mnemonic, _offset)]
        _assembly += ['or x31, x15, x0']
        _sign = (_const[-1] >> 7) & 0b1 # HACK: little-endian specific
        _correct_answer = _const + [(0xff if _sign else 0)] * (8 - _nbytes)
        return _correct_answer, _assembly
    def c_ld(self):
        _nbytes = 8
        _mnemonic = 'c.ld'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**8 - 1) | 0b111) ^ 0b111
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x14, x0, 1']
        _assembly += ['slli x14, x14, 20']
        _assembly += ['sd x15, {}(x14)'.format(_offset)]
        _assembly += ['{} x15, {}(x14)'.format(_mnemonic, _offset)]
        _assembly += ['or x31, x15, x0']
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def c_lwsp(self):
        _nbytes = 4
        _mnemonic = 'c.lwsp'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**7 - 1) | 0b11) ^ 0b11
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['sd x15, {}(x2)'.format(_offset)]
        _assembly += ['{} x31, {}(x2)'.format(_mnemonic, _offset)]
        _sign = (_const[-1] >> 7) & 0b1 # HACK: little-endian specific
        _correct_answer = _const + [(0xff if _sign else 0)] * (8 - _nbytes)
        return _correct_answer, _assembly
    def c_ldsp(self):
        _nbytes = 8
        _mnemonic = 'c.ldsp'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**8 - 1) | 0b111) ^ 0b111
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['sd x15, {}(x2)'.format(_offset)]
        _assembly += ['{} x31, {}(x2)'.format(_mnemonic, _offset)]
        _sign = (_const[-1] >> 7) & 0b1 # HACK: little-endian specific
        _correct_answer = _const + [(0xff if _sign else 0)] * (8 - _nbytes)
        return _correct_answer, _assembly
    def c_sw(self):
        _nbytes = 4
        _mnemonic = 'c.sw'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**7 - 1) | 0b11) ^ 0b11
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x14, x0, 1']
        _assembly += ['slli x14, x14, 20']
        _assembly += ['sd x0, {}(x14)'.format(_offset)]
        _assembly += ['{} x15, {}(x14)'.format(_mnemonic, _offset)]
        _assembly += ['ld x15, {}(x14)'.format(_offset)]
        _assembly += ['or x31, x15, x0']
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def c_sd(self):
        _nbytes = 8
        _mnemonic = 'c.sd'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**8 - 1) | 0b111) ^ 0b111
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x14, x0, 1']
        _assembly += ['slli x14, x14, 20']
        _assembly += ['sd x0, {}(x14)'.format(_offset)]
        _assembly += ['{} x15, {}(x14)'.format(_mnemonic, _offset)]
        _assembly += ['ld x15, {}(x14)'.format(_offset)]
        _assembly += ['or x31, x15, x0']
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def c_swsp(self):
        _nbytes = 4
        _mnemonic = 'c.swsp'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**7 - 1) | 0b11) ^ 0b11
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['sd x0, {}(x2)'.format(_offset)]
        _assembly += ['{} x15, {}(x2)'.format(_mnemonic, _offset)]
        _assembly += ['ld x31, {}(x2)'.format(_offset)]
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def c_sdsp(self):
        _nbytes = 8
        _mnemonic = 'c.sdsp'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
        _offset = (random.randint(0, 2**8 - 1) | 0b111) ^ 0b111
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['sd x0, {}(x2)'.format(_offset)]
        _assembly += ['{} x15, {}(x2)'.format(_mnemonic, _offset)]
        _assembly += ['ld x31, {}(x2)'.format(_offset)]
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def sb(self):
        _nbytes = 1
        _mnemonic = 'sb'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
#        print('_const : {}'.format(_const))
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x18, x0, 1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x0, 0(x18)']
        _assembly += ['{} x15, 0(x18)'.format(_mnemonic)]
        _assembly += ['ld x31, 0(x18)']
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def sh(self):
        _nbytes = 2
        _mnemonic = 'sh'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
#        print('_const : {}'.format(_const))
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x18, x0, 1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x0, 0(x18)']
        _assembly += ['{} x15, 0(x18)'.format(_mnemonic)]
        _assembly += ['ld x31, 0(x18)']
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def sw(self):
        _nbytes = 4
        _mnemonic = 'sw'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
#        print('_const : {}'.format(_const))
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x18, x0, 1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x0, 0(x18)']
        _assembly += ['{} x15, 0(x18)'.format(_mnemonic)]
        _assembly += ['ld x31, 0(x18)']
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def sd(self):
        _nbytes = 8
        _mnemonic = 'sd'
        _const = [random.randint(0, 255) for _ in range(_nbytes)]
#        print('_const : {}'.format(_const))
        _assembly  = sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const)], [])
        _assembly += ['ori x18, x0, 1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x0, 0(x18)']
        _assembly += ['{} x15, 0(x18)'.format(_mnemonic)]
        _assembly += ['ld x31, 0(x18)']
        _correct_answer = _const + [0] * (8 - _nbytes)
        return _correct_answer, _assembly
    def lb(self):
        _nbytes = 1
        _nbits = _nbytes * 8
        _const_0u = random.randint(0, 2**20 - 1)
        _const_0l = random.randint(-2**11, 2**11 - 1)
        _const_1u = random.randint(0, 2**20 - 1)
        _const_1l = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0u)]
        _assembly += ['slli x15, x15, 32']
        _assembly += ['srli x15, x15, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_0l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x15, x15, x17']
        _assembly += ['slli x15, x15, 32']
        _assembly += ['lui x16, {}'.format(_const_1u)]
        _assembly += ['slli x16, x16, 32']
        _assembly += ['srli x16, x16, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_1l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x16, x16, x17']
        _assembly += ['or x15, x15, x16']
        _assembly += ['ori x18, x0, 0x1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x15, 0(x18)']
        _assembly += ['lb x31, 0(x18)']
        _correct_answer  = (_const_0u << 12)
        _correct_answer |= (_const_0l & ((2**12) - 1))
        _correct_answer <<= 32
        _correct_answer |= (_const_1u << 12)
        _correct_answer |= (_const_1l & ((2**12) - 1))
        _correct_answer &= (2 ** 64) - 1
#        print('_correct_answer : {:016x}'.format(_correct_answer))
        _correct_answer &= 2**_nbits - 1
        _sign = _correct_answer & (1 << (_nbits - 1))
#        print('_correct_answer : {}'.format(_correct_answer))
        _correct_answer = list(_correct_answer.to_bytes(_nbytes, 'little'))
        _correct_answer += ([0xff] * (8 - _nbytes) if _sign else [0] * (8 - _nbytes))
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('_const_0u       : {:05x}'.format(_const_0u))
#        print('_const_0l       : {:03x}'.format(_const_0l & ((2**32) - 1)))
#        print('_const_1u       : {:05x}'.format(_const_1u))
#        print('_const_1l       : {:03x}'.format(_const_1l & ((2**32) - 1)))
        return _correct_answer, _assembly
    def lh(self):
        _nbytes = 2
        _nbits = _nbytes * 8
        _const_0u = random.randint(0, 2**20 - 1)
        _const_0l = random.randint(-2**11, 2**11 - 1)
        _const_1u = random.randint(0, 2**20 - 1)
        _const_1l = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0u)]
        _assembly += ['slli x15, x15, 32']
        _assembly += ['srli x15, x15, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_0l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x15, x15, x17']
        _assembly += ['slli x15, x15, 32']
        _assembly += ['lui x16, {}'.format(_const_1u)]
        _assembly += ['slli x16, x16, 32']
        _assembly += ['srli x16, x16, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_1l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x16, x16, x17']
        _assembly += ['or x15, x15, x16']
        _assembly += ['ori x18, x0, 0x1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x15, 0(x18)']
        _assembly += ['lh x31, 0(x18)']
        _correct_answer  = (_const_0u << 12)
        _correct_answer |= (_const_0l & ((2**12) - 1))
        _correct_answer <<= 32
        _correct_answer |= (_const_1u << 12)
        _correct_answer |= (_const_1l & ((2**12) - 1))
        _correct_answer &= (2 ** 64) - 1
#        print('_correct_answer : {:016x} ({})'.format(_correct_answer, list(_correct_answer.to_bytes(8, 'little'))))
        _correct_answer &= 2**_nbits - 1
        _sign = _correct_answer & (1 << (_nbits - 1))
#        print('_correct_answer : {}'.format(_correct_answer))
        _correct_answer = list(_correct_answer.to_bytes(_nbytes, 'little'))
        _correct_answer += ([0xff] * (8 - _nbytes) if _sign else [0] * (8 - _nbytes))
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('_const_0u       : {:05x}'.format(_const_0u))
#        print('_const_0l       : {:03x}'.format(_const_0l & ((2**32) - 1)))
#        print('_const_1u       : {:05x}'.format(_const_1u))
#        print('_const_1l       : {:03x}'.format(_const_1l & ((2**32) - 1)))
        return _correct_answer, _assembly
    def lw(self):
        _nbytes = 4
        _nbits = _nbytes * 8
        _const_0u = random.randint(0, 2**20 - 1)
        _const_0l = random.randint(-2**11, 2**11 - 1)
        _const_1u = random.randint(0, 2**20 - 1)
        _const_1l = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0u)]
        _assembly += ['slli x15, x15, 32']
        _assembly += ['srli x15, x15, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_0l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x15, x15, x17']
        _assembly += ['slli x15, x15, 32']
        _assembly += ['lui x16, {}'.format(_const_1u)]
        _assembly += ['slli x16, x16, 32']
        _assembly += ['srli x16, x16, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_1l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x16, x16, x17']
        _assembly += ['or x15, x15, x16']
        _assembly += ['ori x18, x0, 0x1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x15, 0(x18)']
        _assembly += ['lw x31, 0(x18)']
        _correct_answer  = (_const_0u << 12)
        _correct_answer |= (_const_0l & ((2**12) - 1))
        _correct_answer <<= 32
        _correct_answer |= (_const_1u << 12)
        _correct_answer |= (_const_1l & ((2**12) - 1))
        _correct_answer &= (2 ** 64) - 1
#        print('_correct_answer : {:016x} ({})'.format(_correct_answer, list(_correct_answer.to_bytes(8, 'little'))))
        _correct_answer &= 2**_nbits - 1
        _sign = _correct_answer & (1 << (_nbits - 1))
#        print('_correct_answer : {}'.format(_correct_answer))
        _correct_answer = list(_correct_answer.to_bytes(_nbytes, 'little'))
        _correct_answer += ([0xff] * (8 - _nbytes) if _sign else [0] * (8 - _nbytes))
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('_const_0u       : {:05x}'.format(_const_0u))
#        print('_const_0l       : {:03x}'.format(_const_0l & ((2**32) - 1)))
#        print('_const_1u       : {:05x}'.format(_const_1u))
#        print('_const_1l       : {:03x}'.format(_const_1l & ((2**32) - 1)))
        return _correct_answer, _assembly
    def ld(self):
        _nbytes = 8
        _nbits = _nbytes * 8
        _const_0u = random.randint(0, 2**20 - 1)
        _const_0l = random.randint(-2**11, 2**11 - 1)
        _const_1u = random.randint(0, 2**20 - 1)
        _const_1l = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0u)]
        _assembly += ['slli x15, x15, 32']
        _assembly += ['srli x15, x15, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_0l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x15, x15, x17']
        _assembly += ['slli x15, x15, 32']
        _assembly += ['lui x16, {}'.format(_const_1u)]
        _assembly += ['slli x16, x16, 32']
        _assembly += ['srli x16, x16, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_1l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x16, x16, x17']
        _assembly += ['or x15, x15, x16']
        _assembly += ['ori x18, x0, 0x1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x15, 0(x18)']
        _assembly += ['ld x31, 0(x18)']
        _correct_answer  = (_const_0u << 12)
        _correct_answer |= (_const_0l & ((2**12) - 1))
        _correct_answer <<= 32
        _correct_answer |= (_const_1u << 12)
        _correct_answer |= (_const_1l & ((2**12) - 1))
        _correct_answer &= (2 ** 64) - 1
#        print('_correct_answer : {:016x} ({})'.format(_correct_answer, list(_correct_answer.to_bytes(8, 'little'))))
        _correct_answer &= 2**_nbits - 1
        _sign = _correct_answer & (1 << (_nbits - 1))
#        print('_correct_answer : {}'.format(_correct_answer))
        _correct_answer = list(_correct_answer.to_bytes(_nbytes, 'little'))
        _correct_answer += ([0xff] * (8 - _nbytes) if _sign else [0] * (8 - _nbytes))
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('_const_0u       : {:05x}'.format(_const_0u))
#        print('_const_0l       : {:03x}'.format(_const_0l & ((2**32) - 1)))
#        print('_const_1u       : {:05x}'.format(_const_1u))
#        print('_const_1l       : {:03x}'.format(_const_1l & ((2**32) - 1)))
        return _correct_answer, _assembly
    def lbu(self):
        _nbytes = 1
        _nbits = _nbytes * 8
        _const_0u = random.randint(0, 2**20 - 1)
        _const_0l = random.randint(-2**11, 2**11 - 1)
        _const_1u = random.randint(0, 2**20 - 1)
        _const_1l = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0u)]
        _assembly += ['slli x15, x15, 32']
        _assembly += ['srli x15, x15, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_0l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x15, x15, x17']
        _assembly += ['slli x15, x15, 32']
        _assembly += ['lui x16, {}'.format(_const_1u)]
        _assembly += ['slli x16, x16, 32']
        _assembly += ['srli x16, x16, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_1l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x16, x16, x17']
        _assembly += ['or x15, x15, x16']
        _assembly += ['ori x18, x0, 0x1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x15, 0(x18)']
        _assembly += ['lbu x31, 0(x18)']
        _correct_answer  = (_const_0u << 12)
        _correct_answer |= (_const_0l & ((2**12) - 1))
        _correct_answer <<= 32
        _correct_answer |= (_const_1u << 12)
        _correct_answer |= (_const_1l & ((2**12) - 1))
        _correct_answer &= (2 ** 64) - 1
#        print('_correct_answer : {:016x}'.format(_correct_answer))
        _correct_answer &= 2**_nbits - 1
        _sign = _correct_answer & (1 << (_nbits - 1))
#        print('_correct_answer : {}'.format(_correct_answer))
        _correct_answer = list(_correct_answer.to_bytes(_nbytes, 'little'))
        _correct_answer += [0] * (8 - _nbytes)
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('_const_0u       : {:05x}'.format(_const_0u))
#        print('_const_0l       : {:03x}'.format(_const_0l & ((2**32) - 1)))
#        print('_const_1u       : {:05x}'.format(_const_1u))
#        print('_const_1l       : {:03x}'.format(_const_1l & ((2**32) - 1)))
        return _correct_answer, _assembly
    def lhu(self):
        _nbytes = 2
        _nbits = _nbytes * 8
        _const_0u = random.randint(0, 2**20 - 1)
        _const_0l = random.randint(-2**11, 2**11 - 1)
        _const_1u = random.randint(0, 2**20 - 1)
        _const_1l = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0u)]
        _assembly += ['slli x15, x15, 32']
        _assembly += ['srli x15, x15, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_0l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x15, x15, x17']
        _assembly += ['slli x15, x15, 32']
        _assembly += ['lui x16, {}'.format(_const_1u)]
        _assembly += ['slli x16, x16, 32']
        _assembly += ['srli x16, x16, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_1l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x16, x16, x17']
        _assembly += ['or x15, x15, x16']
        _assembly += ['ori x18, x0, 0x1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x15, 0(x18)']
        _assembly += ['lhu x31, 0(x18)']
        _correct_answer  = (_const_0u << 12)
        _correct_answer |= (_const_0l & ((2**12) - 1))
        _correct_answer <<= 32
        _correct_answer |= (_const_1u << 12)
        _correct_answer |= (_const_1l & ((2**12) - 1))
        _correct_answer &= (2 ** 64) - 1
#        print('_correct_answer : {:016x} ({})'.format(_correct_answer, list(_correct_answer.to_bytes(8, 'little'))))
        _correct_answer &= 2**_nbits - 1
        _sign = _correct_answer & (1 << (_nbits - 1))
#        print('_correct_answer : {}'.format(_correct_answer))
        _correct_answer = list(_correct_answer.to_bytes(_nbytes, 'little'))
        _correct_answer += [0] * (8 - _nbytes)
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('_const_0u       : {:05x}'.format(_const_0u))
#        print('_const_0l       : {:03x}'.format(_const_0l & ((2**32) - 1)))
#        print('_const_1u       : {:05x}'.format(_const_1u))
#        print('_const_1l       : {:03x}'.format(_const_1l & ((2**32) - 1)))
        return _correct_answer, _assembly
    def lwu(self):
        _nbytes = 4
        _nbits = _nbytes * 8
        _const_0u = random.randint(0, 2**20 - 1)
        _const_0l = random.randint(-2**11, 2**11 - 1)
        _const_1u = random.randint(0, 2**20 - 1)
        _const_1l = random.randint(-2**11, 2**11 - 1)
        _assembly  = ['lui x15, {}'.format(_const_0u)]
        _assembly += ['slli x15, x15, 32']
        _assembly += ['srli x15, x15, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_0l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x15, x15, x17']
        _assembly += ['slli x15, x15, 32']
        _assembly += ['lui x16, {}'.format(_const_1u)]
        _assembly += ['slli x16, x16, 32']
        _assembly += ['srli x16, x16, 32']
        _assembly += ['ori x17, x0, {}'.format(_const_1l)]
        _assembly += ['slli x17, x17, {}'.format(64 - 12)]
        _assembly += ['srli x17, x17, {}'.format(64 - 12)]
        _assembly += ['or x16, x16, x17']
        _assembly += ['or x15, x15, x16']
        _assembly += ['ori x18, x0, 0x1']
        _assembly += ['slli x18, x18, 20']
        _assembly += ['sd x15, 0(x18)']
        _assembly += ['lwu x31, 0(x18)']
        _correct_answer  = (_const_0u << 12)
        _correct_answer |= (_const_0l & ((2**12) - 1))
        _correct_answer <<= 32
        _correct_answer |= (_const_1u << 12)
        _correct_answer |= (_const_1l & ((2**12) - 1))
        _correct_answer &= (2 ** 64) - 1
#        print('_correct_answer : {:016x} ({})'.format(_correct_answer, list(_correct_answer.to_bytes(8, 'little'))))
        _correct_answer &= 2**_nbits - 1
        _sign = _correct_answer & (1 << (_nbits - 1))
#        print('_correct_answer : {}'.format(_correct_answer))
        _correct_answer = list(_correct_answer.to_bytes(_nbytes, 'little'))
        _correct_answer += [0] * (8 - _nbytes)
#        print('_correct_answer : {}'.format(_correct_answer))
#        print('_const_0u       : {:05x}'.format(_const_0u))
#        print('_const_0l       : {:03x}'.format(_const_0l & ((2**32) - 1)))
#        print('_const_1u       : {:05x}'.format(_const_1u))
#        print('_const_1l       : {:03x}'.format(_const_1l & ((2**32) - 1)))
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
#        _const = 381056
#        _const = int.from_bytes((-789958656 // (2**12) & 0xffff_ffff).to_bytes(8, 'little'), 'little') >> 12
#        print('_const : {:08x} ({})'.format(_const, _const))
        _shamt = random.randint(0, 2**5 - 1)
#        _shamt = 21
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
    def ori(self):
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
        _assembly += ['ori x31, x30, {}'.format(_const_2)]
#        print('_const_0 : {:15} {}'.format(_const_0, list(map(lambda x: '{:08b}'.format(x), _const_0.to_bytes(8, 'little', signed=True)))))
#        print('_const_1 : {:15} {}'.format(_const_1, list(map(lambda x: '{:08b}'.format(x), _const_1.to_bytes(8, 'little', signed=True)))))
#        print('_const_2 : {:15} {}'.format(_const_2, list(map(lambda x: '{:08b}'.format(x), _const_2.to_bytes(8, 'little', signed=True)))))
        _correct_answer = int.from_bytes(map(
            lambda a, b: a | b,
            _const_0.to_bytes(8, 'little', signed=True),
            _const_2.to_bytes(8, 'little', signed=True),
        ), 'little', signed=True)
        _correct_answer = list(_correct_answer.to_bytes(8, 'little', signed=True))
        return _correct_answer, _assembly
    def xori(self):
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
        _assembly += ['xori x31, x30, {}'.format(_const_2)]
#        print('_const_0 : {:15} {}'.format(_const_0, list(map(lambda x: '{:08b}'.format(x), _const_0.to_bytes(8, 'little', signed=True)))))
#        print('_const_1 : {:15} {}'.format(_const_1, list(map(lambda x: '{:08b}'.format(x), _const_1.to_bytes(8, 'little', signed=True)))))
#        print('_const_2 : {:15} {}'.format(_const_2, list(map(lambda x: '{:08b}'.format(x), _const_2.to_bytes(8, 'little', signed=True)))))
        _correct_answer = int.from_bytes(map(
            lambda a, b: a ^ b,
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
        _b31 = (_correct_answer >> 31) & 0b1
        _correct_answer = functools.reduce(lambda a, b: a | b, map(lambda x: _b31 << x, range(32, 64)), _correct_answer)
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
    def branch(self, mnemonic, nbytes, c1, correct_answer):
        _const_0 = [random.randint(0, 255) for _ in range(nbytes)]
        _const_1 = c1(_const_0)
        _assembly  = ['jal x0, do_test']
        _assembly += ['match:']
        _assembly += ['addi x31, x0, 1']
        _assembly += ['jal x0, done']
        _assembly += ['do_test:']
        _assembly += sum([['slli x15, x15, 8', 'ori x15, x15, {}'.format(c)] for c in reversed(_const_0)], [])
        _assembly += sum([['slli x16, x16, 8', 'ori x16, x16, {}'.format(c)] for c in reversed(_const_1)], [])
        _assembly += ['{} x15, x16, match'.format(mnemonic)]
        _assembly += ['done:']
        _correct_answer = correct_answer(_const_0, _const_1)
        return _correct_answer, _assembly
    def beq(self):
        return self.branch(
            'beq',
            8,
            lambda a: (a if random.randint(0, 1) else [random.randint(0, 255) for _ in range(8)]),
            lambda a, b: list((1 if a == b else 0).to_bytes(8, 'little')),
        )
    def bne(self):
        return self.branch(
            'bne',
            8,
            lambda a: (a if random.randint(0, 1) else [random.randint(0, 255) for _ in range(8)]),
            lambda a, b: list((1 if a != b else 0).to_bytes(8, 'little')),
        )
    def blt(self):
        return self.branch(
            'blt',
            8,
            lambda a: (list((int.from_bytes(a, 'little', signed=True) - 1).to_bytes(8, 'little', signed=True)) if random.randint(0, 1) else [random.randint(0, 255) for _ in range(8)]),
            lambda a, b: list((1 if int.from_bytes(a, 'little', signed=True) < int.from_bytes(b, 'little', signed=True) else 0).to_bytes(8, 'little')),
        )
    def bge(self):
        return self.branch(
            'bge',
            8,
            lambda a: (list((int.from_bytes(a, 'little', signed=True) + random.randint(0, 1)).to_bytes(8, 'little', signed=True)) if random.randint(0, 1) else [random.randint(0, 255) for _ in range(8)]),
            lambda a, b: list((1 if int.from_bytes(a, 'little', signed=True) >= int.from_bytes(b, 'little', signed=True) else 0).to_bytes(8, 'little')),
        )
    def bltu(self):
        return self.branch(
            'bltu',
            8,
            lambda a: (list((int.from_bytes(a, 'little') - 1).to_bytes(8, 'little')) if random.randint(0, 1) else [random.randint(0, 255) for _ in range(8)]),
            lambda a, b: list((1 if int.from_bytes(a, 'little') < int.from_bytes(b, 'little') else 0).to_bytes(8, 'little')),
        )
    def bgeu(self):
        return self.branch(
            'bgeu',
            8,
            lambda a: (list((int.from_bytes(a, 'little') + random.randint(0, 1)).to_bytes(8, 'little')) if random.randint(0, 1) else [random.randint(0, 255) for _ in range(8)]),
            lambda a, b: list((1 if int.from_bytes(a, 'little') >= int.from_bytes(b, 'little') else 0).to_bytes(8, 'little')),
        )
    def generate(self, args, test):
        _correct_answer, _assembly = self.tests.get(test)()
        _n_instruction = len(list(filter(lambda a: not a.endswith(':'), _assembly))) + 3
        _program  = '\n'.join(list(map(lambda x: '\t{}'.format(x), ['.text', '.globl\t_start', '.type\t_start, @function'])) + [''])
        _program += '\n'.join(['_exit: '] + list(map(lambda x: '\t{}'.format(x), ['add x17, x0, 93', 'ecall'])) + [''])
        _program += '\n'.join(['_start:'] + list(map(lambda x: (x if x.endswith(':') else '\t{}'.format(x)), _assembly + ['jal x1, _exit'])))
        _program += '\n'
        with open(os.path.join(args.dir, 'src', '{}.s'.format(test)), 'w+') as fp: fp.write(_program)
        subprocess.run('{} -o {} -march=rv64gc {} -nostartfiles'.format(
            args.compiler,
            os.path.join(args.dir, 'bin', '{}'.format(test)),
            os.path.join(args.dir, 'src', '{}.s'.format(test))
        ).split())
        _script  = ['# Nebula test harness script']
#        _script += ['port 10000']
        _script += ['service pipelines/bergamot/implementation/{}:localhost:22:0'.format(s) for s in ('simplecore.py', 'regfile.py', 'decode.py', 'execute.py')]
        _script += ['spawn']
        _script += ['config mainmem:peek_latency_in_cycles 1']
        _script += ['config mainmem:filename {}'.format(os.path.join(args.dir, 'mainmem.raw'))]
        _script += ['config mainmem:capacity {}'.format(2**32)]
#        _script += ['loadbin 0x{:08x} 0x{:08x} _start'.format(self._sp, self._start_pc)]
#        _script += ['config max_instructions {}'.format(_n_instruction)]
        _script += ['run']
        _script += ['shutdown']
        with open(os.path.join(args.dir, 'test.nebula'), 'w+') as fp: fp.write('\n'.join(_script))
        _cmd = 'python3 launcher.py --log {} --service {} --max_instructions {} -- {} {} {}'.format(
            os.path.join(os.getcwd(), args.dir),
            'pipelines/bergamot/implementation/mainmem.py:localhost:22:-1',
            _n_instruction,
            args.port,
            os.path.join(args.dir, 'test.nebula'),
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
        os.sync()
        with open(os.path.join(args.dir, '0000_regfile.py.log'), 'r') as fp: _regfile_py_log = fp.readlines()
        _x31 = list(filter(lambda x: re.search('register 31 : ', x), _regfile_py_log))[-1].split(':')[1]
        _x31 = eval(_x31)
        print('do_test(..., {}): {} (_correct_answer) ?= {} (_x31) -> {}'.format(
            test,
            _correct_answer,
            _x31,
            _correct_answer ==_x31
        ))
        if _x31 != _correct_answer:
            print(_program)
            print('---')
            print('\n'.join(_stdout))
            assert False


if __name__ == '__main__':
    _harness = Harness()
    if '--list' in sys.argv:
        for x in _harness.tests.keys(): print(x)
        sys.exit(0)
    parser = argparse.ArgumentParser(description='Nebula')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--loop', dest='loop', type=int, default=1, help='number of times to repeat tests')
    parser.add_argument('--insns', dest='insns', type=str, nargs='+', help='specific instruction(s) to test')
    parser.add_argument('port', type=int, help='port for accepting connections')
    parser.add_argument('compiler', type=str, help='RISC-V cross-compiler')
    parser.add_argument('dir', type=str, help='directory to put tests')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    args.dir = os.path.join(os.getcwd(), args.dir)
    assert os.path.exists(args.dir), 'Cannot open dir, {}!'.format(args.dir)
    if not os.path.exists(os.path.join(args.dir, 'src')): os.mkdir(os.path.join(args.dir, 'src'))
    if not os.path.exists(os.path.join(args.dir, 'bin')): os.mkdir(os.path.join(args.dir, 'bin'))
    for _ in range(args.loop): [
        _harness.generate(args, n)
        for n in filter(lambda a: a in (map(lambda b: b.lower(), args.insns) if args.insns else _harness.tests.keys()), _harness.tests.keys())
    ]