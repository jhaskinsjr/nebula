# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import toolbox.stats
import riscv.execute
import riscv.syscall.linux

def do_unimplemented(service, state, insn):
    logging.info('Unimplemented: {}'.format(insn))
    service.tx({'undefined': insn})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})

def do_lui(service, state, insn):
    _result = riscv.execute.lui(insn.get('imm'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_auipc(service, state, insn):
    _result = riscv.execute.auipc(insn.get('%pc'), insn.get('imm'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_jal(service, state, insn):
    _next_pc, _ret_pc = riscv.execute.jal(insn.get('%pc'), insn.get('imm'), insn.get('size'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': '%pc',
            'data': _next_pc,
        }
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _ret_pc,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_jalr(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    _next_pc, _ret_pc = riscv.execute.jalr(insn.get('%pc'), state.get('operands').get('rs1'), insn.get('imm'), insn.get('size'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': '%pc',
            'data': _next_pc,
        }
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _ret_pc,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_branch(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    if not 'rs2' in state.get('operands'):
        state.get('operands').update({'rs2': '%{}'.format(insn.get('rs2'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs2'),
            }
        }})
    if not isinstance(state.get('operands').get('rs2'), list):
        return
    _next_pc, _taken = {
        'BEQ': riscv.execute.beq,
        'BNE': riscv.execute.bne,
        'BLT': riscv.execute.blt,
        'BGE': riscv.execute.bge,
        'BLTU': riscv.execute.bltu,
        'BGEU': riscv.execute.bgeu,
    }.get(insn.get('cmd'))(insn.get('%pc'), state.get('operands').get('rs1'), state.get('operands').get('rs2'), insn.get('imm'), insn.get('size'))
    insn.update({'taken': _taken})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': '%pc',
            'data': _next_pc,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_itype(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    _result = {
        'ADDI': riscv.execute.addi,
        'SLTI': riscv.execute.slti,
        'SLTIU': riscv.execute.sltiu,
        'ADDIW': riscv.execute.addiw,
        'XORI': riscv.execute.xori,
        'ORI': riscv.execute.ori,
        'ANDI': riscv.execute.andi,
    }.get(insn.get('cmd'))(state.get('operands').get('rs1'), insn.get('imm'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_rtype(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    if not 'rs2' in state.get('operands'):
        state.get('operands').update({'rs2': '%{}'.format(insn.get('rs2'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs2'),
            }
        }})
    if not isinstance(state.get('operands').get('rs2'), list):
        return
    _result = {
        'ADD': riscv.execute.add,
        'SUB': riscv.execute.sub,
        'XOR': riscv.execute.xor,
        'SLT': riscv.execute.slt,
        'SLTU': riscv.execute.sltu,
        'SLL': riscv.execute.sll,
        'SRL': riscv.execute.srl,
        'SRA': riscv.execute.sra,
        'OR': riscv.execute.do_or,
        'AND': riscv.execute.do_and,
        'ADDW': riscv.execute.addw,
        'SUBW': riscv.execute.subw,
        'SLLW': riscv.execute.sllw,
        'SRLW': riscv.execute.srlw,
        'SRAW': riscv.execute.sraw,
        'MUL': riscv.execute.mul,
        'MULH': riscv.execute.mulh,
        'MULHSU': riscv.execute.mulhsu,
        'MULHU': riscv.execute.mulhu,
        'DIV': riscv.execute.div,
        'DIVU': riscv.execute.divu,
        'REM': riscv.execute.rem,
        'REMU': riscv.execute.remu,
        'MULW': riscv.execute.mulw,
        'DIVW': riscv.execute.divw,
        'DIVUW': riscv.execute.divuw,
        'REMW': riscv.execute.remw,
        'REMUW': riscv.execute.remuw,
    }.get(insn.get('cmd'))(state.get('operands').get('rs1'), state.get('operands').get('rs2'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_load(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    if not 'mem' in state.get('operands'):
        state.get('operands').update({'mem': insn.get('imm') + int.from_bytes(state.get('operands').get('rs1'), 'little')})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'mem': {
                'cmd': 'peek',
                'addr': state.get('operands').get('mem'),
                'size': insn.get('nbytes'),
            }
        }})
    if not isinstance(state.get('operands').get('mem'), list):
        return
    _fetched  = state.get('operands').get('mem')
    _fetched += [-1] * (8 - len(_fetched))
    logging.debug('do_load(): _fetched : {} ({})'.format(_fetched, len(_fetched)))
    _data = { # HACK: This is 100% little-endian-specific
        'LD': _fetched,
        'LW': _fetched[:4] + [(0xff if ((_fetched[3] >> 7) & 0b1) else 0)] * 4,
        'LH': _fetched[:2] + [(0xff if ((_fetched[1] >> 7) & 0b1) else 0)] * 6,
        'LB': _fetched[:1] + [(0xff if ((_fetched[0] >> 7) & 0b1) else 0)] * 7,
        'LWU': _fetched[:4] + [0] * 4,
        'LHU': _fetched[:2] + [0] * 6,
        'LBU': _fetched[:1] + [0] * 7,
    }.get(insn.get('cmd'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _data,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_store(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    if not 'rs2' in state.get('operands'):
        state.get('operands').update({'rs2': '%{}'.format(insn.get('rs2'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs2'),
            }
        }})
    if not isinstance(state.get('operands').get('rs2'), list):
        return
    _size = insn.get('nbytes')
    _data = state.get('operands').get('rs2')
    _data = {
        'SD': _data,
        'SW': _data[:4],
        'SH': _data[:2],
        'SB': _data[:1],
    }.get(insn.get('cmd'))
#    _data = state.get('operands').get('rs2') & {
#        8: 0xffffffffffffffff,
#        4: 0xffffffff,
#        2: 0xffff,
#        1: 0xff,
#    }.get(_size)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'mem': {
            'cmd': 'poke',
            'addr': insn.get('imm') + int.from_bytes(state.get('operands').get('rs1'), 'little'),
            'size': _size,
            'data': _data
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_nop(service, state, insn):
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_shift(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    _rs1 = state.get('operands').get('rs1')
    _shamt = insn.get('shamt')
    _result = {
        'SLLI': riscv.execute.slli,
        'SRLI': riscv.execute.srli,
        'SRAI': riscv.execute.srai,
        'SLLIW': riscv.execute.slliw,
        'SRLIW': riscv.execute.srliw,
        'SRAIW': riscv.execute.sraiw,
    }.get(insn.get('cmd'))(_rs1, _shamt)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_ecall(service, state, insn):
    # The syscall calling protocol was learned from
    # https://git.kernel.org/pub/scm/docs/man-pages/man-pages.git/tree/man2/syscall.2?h=man-pages-5.04#n332
    # specficially:
    #
    #   riscv	ecall	a7	a0	a1
    #
    # meaning that the syscall number is in register x17 (i.e., a7) and
    # parameters to the syscall are in registers x10 (i.e., a0) through
    # x15 (i.e., a5), respectively
    _a7 = 17
    _a0 = 10
    _a1 = 11
    _a2 = 12
    _a3 = 13
    _a4 = 14
    _a5 = 15
    if not 'syscall_num' in state.get('operands'):
        state.get('operands').update({'syscall_num': '%{}'.format(_a7)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': _a7,
            }
        }})
    if not isinstance(state.get('operands').get('syscall_num'), list):
        return
    if not 'syscall_a0' in state.get('operands'):
        state.get('operands').update({'syscall_a0': '%{}'.format(_a0)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': _a0,
            }
        }})
    if not isinstance(state.get('operands').get('syscall_a0'), list):
        return
    if not 'syscall_a1' in state.get('operands'):
        state.get('operands').update({'syscall_a1': '%{}'.format(_a1)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': _a1,
            }
        }})
    if not isinstance(state.get('operands').get('syscall_a1'), list):
        return
    if not 'syscall_a2' in state.get('operands'):
        state.get('operands').update({'syscall_a2': '%{}'.format(_a2)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': _a2,
            }
        }})
    if not isinstance(state.get('operands').get('syscall_a2'), list):
        return
    if not 'syscall_a3' in state.get('operands'):
        state.get('operands').update({'syscall_a3': '%{}'.format(_a3)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': _a3,
            }
        }})
    if not isinstance(state.get('operands').get('syscall_a3'), list):
        return
    if not 'syscall_a4' in state.get('operands'):
        state.get('operands').update({'syscall_a4': '%{}'.format(_a4)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': _a4,
            }
        }})
    if not isinstance(state.get('operands').get('syscall_a4'), list):
        return
    if not 'syscall_a5' in state.get('operands'):
        state.get('operands').update({'syscall_a5': '%{}'.format(_a5)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': _a5,
            }
        }})
    if not isinstance(state.get('operands').get('syscall_a5'), list):
        return
    _syscall_num = state.get('operands').get('syscall_num')
    _syscall_a0 = state.get('operands').get('syscall_a0')
    _syscall_a1 = state.get('operands').get('syscall_a1')
    _syscall_a2 = state.get('operands').get('syscall_a2')
    _syscall_a3 = state.get('operands').get('syscall_a3')
    _syscall_a4 = state.get('operands').get('syscall_a4')
    _syscall_a5 = state.get('operands').get('syscall_a5')
    if 'mem' in state.get('operands').keys() and isinstance(state.get('operands').get('mem'), list):
        if 'arg' not in state.get('syscall_kwargs').keys(): state.get('syscall_kwargs').update({'arg': []})
        state.get('syscall_kwargs').get('arg').append(bytes(state.get('operands').get('mem')))
        state.get('operands').pop('mem')
    _side_effect = state.get('system').do_syscall(
        _syscall_num,
        _syscall_a0, _syscall_a1, _syscall_a2, _syscall_a3, _syscall_a4, _syscall_a5, **{
            **state.get('syscall_kwargs'),
            **{'cycle': state.get('cycle')},
    })
    _done = _side_effect.get('done')
    if 'poke' in _side_effect.keys():
        _addr = int.from_bytes(_side_effect.get('poke').get('addr'), 'little')
        _data = _side_effect.get('poke').get('data')
        service.tx({'info': '_data : {} ({})'.format(_data, type(_data))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'mem': {
                'cmd': 'poke',
                'addr': _addr,
                'size': len(_data),
                'data': _data,
            }
        }})
    if 'peek' in _side_effect.keys():
        if not 'mem' in state.get('operands').keys():
            _addr = _side_effect.get('peek').get('addr')
            _size = _side_effect.get('peek').get('size')
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'mem': {
                    'cmd': 'peek',
                    'addr': _addr,
                    'size': _size,
                }
            }})
            state.get('operands').update({'mem': _addr})
    if 'shutdown' in _side_effect.keys():
        insn = {
            **insn,
            **{'operands': {
                17: state.get('operands').get('syscall_num'),
                10: state.get('operands').get('syscall_a0'),
                11: state.get('operands').get('syscall_a1'),
                12: state.get('operands').get('syscall_a2'),
                13: state.get('operands').get('syscall_a3'),
                14: state.get('operands').get('syscall_a4'),
                15: state.get('operands').get('syscall_a5'),
            }},
            **{'shutdown': True},
        }
    if not _done: return
    if 'output' in _side_effect.keys():
        service.tx({'event': {
            **{'arrival': 1 + state.get('cycle')},
            **{'coreid': state.get('coreid')},
            **_side_effect.get('output'),
        }})
    state.update({'syscall_kwargs': {}})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_fence(service, state, insn):
    # HACK: in a complex pipeline, this needs to be more than a NOP
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
    do_commit(service, state, insn)
    state.update({'operands': {}})
    state.update({'pending_execute': None})

def do_execute(service, state):
    _insn = state.get('pending_execute')
    _pc = int.from_bytes(_insn.get('%pc'), 'little')
    _word = ('{:08x}'.format(_insn.get('word')) if 4 == _insn.get('size') else '    {:04x}'.format(_insn.get('word')))
    logging.info('do_execute(): {:8x}: {} : {:10} ({:12}, {})'.format(_pc, _word, _insn.get('cmd'), state.get('cycle'), _insn.get('function', '')))
    _f = {
        'LUI': do_lui,
        'AUIPC': do_auipc,
        'JAL': do_jal,
        'JALR': do_jalr,
        'ADDI': do_itype,
        'ADDIW': do_itype,
        'XORI': do_itype,
        'ORI': do_itype,
        'ANDI': do_itype,
        'SLTI': do_itype,
        'SLTIU': do_itype,
        'ADD': do_rtype,
        'SUB': do_rtype,
        'XOR': do_rtype,
        'SLL': do_rtype,
        'SRL': do_rtype,
        'SRA': do_rtype,
        'SLT': do_rtype,
        'SLTU': do_rtype,
        'OR': do_rtype,
        'AND': do_rtype,
        'ADDW': do_rtype,
        'SUBW': do_rtype,
        'SLLW': do_rtype,
        'SRLW': do_rtype,
        'SRAW': do_rtype,
        'MUL': do_rtype,
        'MULH': do_rtype,
        'MULHSU': do_rtype,
        'MULHU': do_rtype,
        'DIV': do_rtype,
        'DIVU': do_rtype,
        'REM': do_rtype,
        'REMU': do_rtype,
        'MULW': do_rtype,
        'DIVW': do_rtype,
        'DIVUW': do_rtype,
        'REMW': do_rtype,
        'REMUW': do_rtype,
        'LD': do_load,
        'LW': do_load,
        'LH': do_load,
        'LB': do_load,
        'LWU': do_load,
        'LHU': do_load,
        'LBU': do_load,
        'SD': do_store,
        'SW': do_store,
        'SH': do_store,
        'SB': do_store,
        'NOP': do_nop,
        'SLLI': do_shift,
        'SRLI': do_shift,
        'SRAI': do_shift,
        'SLLIW': do_shift,
        'SRLIW': do_shift,
        'SRAIW': do_shift,
        'BEQ': do_branch,
        'BNE': do_branch,
        'BLT': do_branch,
        'BGE': do_branch,
        'BLTU': do_branch,
        'BGEU': do_branch,
        'ECALL': do_ecall,
        'FENCE': do_fence,
    }.get(_insn.get('cmd'), do_unimplemented)
    _f(service, state, _insn)
#    toolbox.report_stats(service, state, 'histo', 'category', _f.__name__)
    state.get('stats').refresh('histo', 'category', _f.__name__)
def do_complete(service, state, insn): # finished the work of the instruction, but will not necessarily be committed
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'complete': {
            'insn': insn,
        },
    }})
#    toolbox.report_stats(service, state, 'flat', 'number_of_completes')
    state.get('stats').refresh('flat', 'number_of_completes')
def do_confirm(service, state, insn): # definitely will commit
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'confirm': {
            'insn': insn,
        },
    }})
#    toolbox.report_stats(service, state, 'flat', 'number_of_confirms')
    state.get('stats').refresh('flat', 'number_of_confirms')
def do_commit(service, state, insn):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': insn,
        },
    }})
#    toolbox.report_stats(service, state, 'flat', 'number_of_commits')
    state.get('stats').refresh('flat', 'number_of_commits')

def do_tick(service, state, results, events):
    for reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%{}'.format(reg.get('name')) == state.get('operands').get('rs1'):
            state.get('operands').update({'rs1': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('rs2'):
            state.get('operands').update({'rs2': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('syscall_num'):
            state.get('operands').update({'syscall_num': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('syscall_a0'):
            state.get('operands').update({'syscall_a0': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('syscall_a1'):
            state.get('operands').update({'syscall_a1': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('syscall_a2'):
            state.get('operands').update({'syscall_a2': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('syscall_a3'):
            state.get('operands').update({'syscall_a3': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('syscall_a4'):
            state.get('operands').update({'syscall_a4': reg.get('data')})
        elif '%{}'.format(reg.get('name')) == state.get('operands').get('syscall_a5'):
            state.get('operands').update({'syscall_a5': reg.get('data')})
    for mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
        if mem.get('addr') != state.get('operands').get('mem'): continue
        state.get('operands').update({'mem': mem.get('data')})
    for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
        _cmd = _perf.get('cmd')
        if 'report_stats' == _cmd:
            _dict = state.get('stats').get(state.get('coreid')).get(state.get('service'))
            toolbox.report_stats_from_dict(service, state, _dict)
    for execute in map(lambda y: y.get('execute'), filter(lambda x: x.get('execute'), events)):
        state.update({'pending_execute': execute.get('insn')})
    if state.get('pending_execute'): do_execute(service, state)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Execute')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
    args = parser.parse_args()
    assert not os.path.isfile(args.log), '--log must point to directory, not file'
    while not os.path.isdir(args.log):
        try:
            os.makedirs(args.log, exist_ok=True)
        except:
            time.sleep(0.1)
    logging.basicConfig(
        filename=os.path.join(args.log, '{:04}_{}.log'.format(args.coreid, os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = {
        'service': 'execute',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': None,
        'syscall_kwargs': {},
        'system': riscv.syscall.linux.System(),
        'stats': None,
        'operands': {},
    }
    _service = service.Service(state.get('service'), state.get('coreid'), _launcher.get('host'), _launcher.get('port'))
    while state.get('active'):
        state.update({'ack': True})
        msg = _service.rx()
#        _service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif {'text': 'run'} == {k: v}:
                state.update({'running': True})
                state.update({'ack': False})
                state.update({'pending_execute': None})
                state.update({'syscall_kwargs': {}})
                state.update({'stats': toolbox.stats.CounterBank(state.get('coreid'), state.get('service'))})
                state.update({'operands': {}})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
                do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
