# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import sys
import argparse
import logging
import time
import functools
import struct

import service
import toolbox
import riscv.execute
import riscv.constants
import riscv.syscall.linux

def do_unimplemented(service, state, insn):
    logging.info('Unimplemented: {}'.format(state.get('pending_execute')))
    insn = {
        **insn,
        **{
            'result': None,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    service.tx({'undefined': insn})
    return insn, True

def do_lui(service, state, insn):
    _result = riscv.execute.lui(insn.get('imm'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': _result,
                },
            },
        }
    }})
    return insn, True
def do_auipc(service, state, insn):
    _result = riscv.execute.auipc(insn.get('%pc'), insn.get('imm'))
    insn = {
        **insn,
        **{
            'result': _result,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_jal(service, state, insn):
    _next_pc, _ret_pc = riscv.execute.jal(insn.get('%pc'), insn.get('imm'), insn.get('size'))
    _taken = (int.from_bytes(insn.get('%pc'), 'little') + insn.get('size')) != int.from_bytes(_next_pc, 'little') 
    # _taken rather than using the return value since,
    # in a pathological case, it's possible to jump
    # to the next instruction which is indistinguishable
    # from not-taken
    insn = {
        **insn,
        **{
            'taken': _taken,
            'next_pc': _next_pc,
            'ret_pc': _ret_pc,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_jalr(service, state, insn):
    _rs1 = insn.get('operands').get('rs1')
    _next_pc, _ret_pc = riscv.execute.jalr(insn.get('%pc'), insn.get('imm'), _rs1, insn.get('size'))
    _taken = (int.from_bytes(insn.get('%pc'), 'little') + insn.get('size')) != int.from_bytes(_next_pc, 'little') 
    # _taken rather than using the return value since,
    # in a pathological case, it's possible to jump
    # to the next instruction which is indistinguishable
    # from not-taken
    insn = {
        **insn,
        **{
            'taken': _taken,
            'next_pc': _next_pc,
            'ret_pc': _ret_pc,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_branch(service, state, insn):
    _rs1 = insn.get('operands').get('rs1')
    _rs2 = insn.get('operands').get('rs2')
    _next_pc, _taken = {
        'BEQ': riscv.execute.beq,
        'BNE': riscv.execute.bne,
        'BLT': riscv.execute.blt,
        'BGE': riscv.execute.bge,
        'BLTU': riscv.execute.bltu,
        'BGEU': riscv.execute.bgeu,
    }.get(insn.get('cmd'))(insn.get('%pc'), _rs1, _rs2, insn.get('imm'), insn.get('size'))
    _taken = (int.from_bytes(insn.get('%pc'), 'little') + insn.get('size')) != int.from_bytes(_next_pc, 'little') 
    # _taken rather than using the return value since,
    # in a pathological case, it's possible to branch
    # to the next instruction which is indistinguishable
    # from not-taken
    insn = {
        **insn,
        **{
            'taken': _taken,
            'next_pc': _next_pc,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_itype(service, state, insn):
    _rs1 = insn.get('operands').get('rs1')
    _result = {
        'ADDI': riscv.execute.addi,
        'SLTI': riscv.execute.slti,
        'SLTIU': riscv.execute.sltiu,
        'ADDIW': riscv.execute.addiw,
        'XORI': riscv.execute.xori,
        'ORI': riscv.execute.ori,
        'ANDI': riscv.execute.andi,
    }.get(insn.get('cmd'))(_rs1, insn.get('imm'))
    insn = {
        **insn,
        **{
            'result': _result,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_rtype(service, state, insn):
    _rs1 = insn.get('operands').get('rs1')
    _rs2 = insn.get('operands').get('rs2')
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
    }.get(insn.get('cmd'))(_rs1, _rs2)
    insn = {
        **insn,
        **{
            'result': _result,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_load(service, state, insn):
    _rs1 = insn.get('operands').get('rs1')
    insn = {
        **insn,
    }
    insn.get('operands').update({'addr': insn.get('imm') + int.from_bytes(_rs1, 'little')})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'lsu': {
            'insn': {
                **insn,
                **{'confirmed': False},
#                **{'result': None},
            },
        }
    }})
    return insn, True
def do_store(service, state, insn):
    _rs1 = insn.get('operands').get('rs1')
    _rs2 = insn.get('operands').get('rs2')
    insn = {
        **insn,
        **{'confirmed': False},
    }
    insn.get('operands').update({'data': _rs2})
    insn.get('operands').update({'addr': insn.get('imm') + int.from_bytes(_rs1, 'little')})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'lsu': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_atomic(service, state, insn):
    service.tx({'info': 'state.operands.mem : {} ({})'.format(state.get('operands').get('mem'), insn.get('cmd'))})
    if insn.get('cmd') in ['LR.W', 'LR.D', 'SC.W', 'SC.D']:
        insn = {
            **insn,
            **{
                'reservation': True, # TODO: add code to "do" reservations in lsu, l2, mainmem
            },
        }
        return {
            'LR.W': do_load,
            'LR.D': do_load,
            'SC.W': do_store,
            'SC.D': do_store,
        }.get(insn.get('cmd'), do_unimplemented)(service, state, insn)
    _done = False
    _rs1 = insn.get('operands').get('rs1')
    _rs2 = insn.get('operands').get('rs2')
    if not state.get('operands').get('mem'):
        _addr = int.from_bytes(_rs1, 'little')
        _size = (8 if insn.get('cmd').endswith('.D') else 4)
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
    else:
        # These AMO instructions atomically load a data value from the
        # address in rs1, place the value into register rd, apply a binary
        # operator to the loaded value and the original value in rs2, then
        # store the result back to the address in rs1.
        # (see: https://riscv.org/wp-content/uploads/2019/06/riscv-spec.pdf, p.51)
        #
        # In other words...
        # 1. rd <- value from @rs1
        # 2. binop(value from @rs1, rs2) -> @rs1
        if isinstance(state.get('operands').get('mem'), list):
            _size = (8 if insn.get('cmd').endswith('.D') else 4)
            _data  = state.get('operands').get('mem')
            _data += (([0xff] * (8 - _size)) if 0 > int.from_bytes(_data, 'little', signed=True) else ([0] * (8 - _size)))
            _result = {
                'AMOSWAP.W': riscv.execute.swap,
                'AMOADD.W': riscv.execute.add,
                'AMOAND.W': riscv.execute.do_and,
                'AMOOR.W': riscv.execute.do_or,
                'AMOXOR.W': riscv.execute.xor,
                'AMOAMIN.W': riscv.execute.min,
                'AMOAMAX.W': riscv.execute.max,
                'AMOAMINU.W': riscv.execute.minu,
                'AMOAMAXU.W': riscv.execute.maxu,
                'AMOSWAP.D': riscv.execute.swap,
                'AMOADD.D': riscv.execute.add,
                'AMOAND.D': riscv.execute.do_and,
                'AMOOR.D': riscv.execute.do_or,
                'AMOXOR.D': riscv.execute.xor,
                'AMOAMIN.D': riscv.execute.min,
                'AMOAMAX.D': riscv.execute.max,
                'AMOAMINU.D': riscv.execute.minu,
                'AMOAMAXU.D': riscv.execute.maxu,
            }.get(insn.get('cmd'))(_data, _rs2)
            insn = {
                **insn,
                **{
                    'result': _data,
                },
            }
            _addr = int.from_bytes(_rs1, 'little')
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'mem': {
                    'cmd': 'poke',
                    'addr': _addr,
                    'size': _size,
                    'data': _result[:_size],
                }
            }})
            service.tx({'event': {
                'arrival': 2 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'commit': {
                    'insn': {
                        **insn,
                    },
                }
            }})
            _done = True
            state.get('operands').pop('mem')
    return insn, _done
def do_nop(service, state, insn):
    insn = {
        **insn,
        **{
            'result': None,
        }
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_shift(service, state, insn):
    _rs1 = insn.get('operands').get('rs1')
    _shamt = insn.get('shamt')
    _result = {
        'SLLI': riscv.execute.slli,
        'SRLI': riscv.execute.srli,
        'SRAI': riscv.execute.srai,
        'SLLIW': riscv.execute.slliw,
        'SRLIW': riscv.execute.srliw,
        'SRAIW': riscv.execute.sraiw,
    }.get(insn.get('cmd'))(_rs1, _shamt)
    insn = {
        **insn,
        **{
            'result': _result,
        },
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_ecall(service, stats, insn):
    _x17 = insn.get('operands').get(17)
    _x10 = insn.get('operands').get(10)
    _x11 = insn.get('operands').get(11)
    _x12 = insn.get('operands').get(12)
    _x13 = insn.get('operands').get(13)
    _x14 = insn.get('operands').get(14)
    _x15 = insn.get('operands').get(15)
    insn = {
        **insn,
        **{
            'result': None,
        }
    }
    if 'mem' in state.get('operands').keys() and isinstance(state.get('operands').get('mem'), list):
        if 'arg' not in state.get('syscall_kwargs').keys(): state.get('syscall_kwargs').update({'arg': []})
        state.get('syscall_kwargs').get('arg').append(bytes(state.get('operands').get('mem')))
        state.get('operands').pop('mem')
    service.tx({'info': 'state.syscall_kwargs : {}'.format(state.get('syscall_kwargs'))})
    _side_effect = state.get('system').do_syscall(_x17, _x10, _x11, _x12, _x13, _x14, _x15, **{
        **state.get('syscall_kwargs'),
        **{'cycle': state.get('cycle')},
    })
    service.tx({'info': '_side_effect         : {}'.format(_side_effect)})
    _done = _side_effect.get('done')
    if 'poke' in _side_effect.keys():
        _addr = int.from_bytes(_side_effect.get('poke').get('addr'), 'little')
        _data = _side_effect.get('poke').get('data')
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
        insn = {
            **insn,
            **{
                'poke': True,
            }
        }
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
        insn = {
            **insn,
            **{
                'peek': True,
            }
        }
    if 'shutdown' in _side_effect.keys():
        service.tx({'info': 'ECALL {}... graceful shutdown'.format(int.from_bytes(_x17, 'little'))})
        service.tx({'shutdown': {
            'coreid': state.get('coreid'),
        }})
    if _done:
        if 'output' in _side_effect.keys():
            service.tx({'event': {
                **{'arrival': 1 + state.get('cycle')},
                **{'coreid': state.get('coreid')},
                **_side_effect.get('output'),
            }})
        service.tx({'event': {
            'arrival': 2 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'commit': {
                'insn': {
                    **insn,
                },
            }
        }})
        if 'poke' in insn.keys() or 'peek' in insn.keys():
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'fetch': {
                    'cmd': 'purge',
                }
            }})
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'lsu': {
                    'cmd': 'purge',
                }
            }})
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'l2': {
                    'cmd': 'purge',
                }
            }})
        state.update({'syscall_kwargs': {}})
    return insn, _done
def do_ebreak(service, state, insn):
    # HACK: in a complex pipeline, this needs to be more than a NOP
    insn = {
        **insn,
        **{
            'result': None,
        }
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True
def do_fence(service, state, insn):
    # HACK: in a complex pipeline, this needs to be more than a NOP
    insn = {
        **insn,
        **{
            'result': None,
        }
    }
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
    return insn, True

def do_execute(service, state):
    if not len(state.get('pending_execute')): return
    toolbox.report_stats(service, state, 'flat', 'pending_execute_not_empty')
    _remove_from_pending_execute = []
    service.tx({'info': 'state.pending_execute : {}'.format(state.get('pending_execute'))})
    for _insn in state.get('pending_execute'):
        service.tx({'info': '_insn : {}'.format(_insn)})
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
            'LR.W': do_atomic,
            'LR.D': do_atomic,
            'SC.W': do_atomic,
            'SC.D': do_atomic,
            'AMOSWAP.W': do_atomic,
            'AMOADD.W': do_atomic,
            'AMOAND.W': do_atomic,
            'AMOOR.W': do_atomic,
            'AMOXOR.W': do_atomic,
            'AMOAMIN.W': do_atomic,
            'AMOAMAX.W': do_atomic,
            'AMOAMINU.W': do_atomic,
            'AMOAMAXU.W': do_atomic,
            'AMOSWAP.D': do_atomic,
            'AMOADD.D': do_atomic,
            'AMOAND.D': do_atomic,
            'AMOOR.D': do_atomic,
            'AMOXOR.D': do_atomic,
            'AMOAMIN.D': do_atomic,
            'AMOAMAX.D': do_atomic,
            'AMOAMINU.D': do_atomic,
            'AMOAMAXU.D': do_atomic,
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
            'EBREAK': do_ebreak,
            'FENCE': do_fence,
        }.get(_insn.get('cmd'), do_unimplemented)
        _insn_prime, _done = _f(service, state, _insn)
        toolbox.report_stats(service, state, 'histo', 'category', _f.__name__)
        if _done:
            _remove_from_pending_execute.append(_insn)
        else:
            break
    for _insn in _remove_from_pending_execute: state.get('pending_execute').remove(_insn)

def do_tick(service, state, results, events):
    for k in filter(lambda x: isinstance(x, int), list(state.get('operands').keys())): state.get('operands').pop(k)
    for _mem in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
        _addr = _mem.get('addr')
        if _addr == state.get('operands').get('mem'):
            state.get('operands').update({'mem': _mem.get('data')})
    for _reg in filter(lambda x: x, map(lambda y: y.get('register'), results)):
        _name = _reg.get('name')
        _data = _reg.get('data')
        state.get('operands').update({_name: _data})
    for _alu in map(lambda y: y.get('alu'), filter(lambda x: x.get('alu'), events)):
        _insn = _alu.get('insn')
        logging.debug('_insn : {}'.format(_insn))
        assert _insn.get('cmd') not in riscv.constants.BRANCHES + riscv.constants.JUMPS or _insn.get('prediction'), '{} without prediction field!'.format(_insn)
        if 'ECALL' == _insn.get('cmd'):
            _patch = {'operands': {
                17: state.get('operands').get(17),
                10: state.get('operands').get(10),
                11: state.get('operands').get(11),
                12: state.get('operands').get(12),
                13: state.get('operands').get(13),
                14: state.get('operands').get(14),
                15: state.get('operands').get(15),
            }}
        else:
            _patch = ({'operands': {k:v for k, v in _insn.get('operands').items()}} if 'operands' in _insn.keys() else {})
            if len(_patch.keys()) and 'rs1' in _insn.keys() and 'rs1' not in _insn.get('operands').keys(): _patch.get('operands').update({'rs1': state.get('operands').get(_insn.get('rs1'))})
            if len(_patch.keys()) and 'rs2' in _insn.keys() and 'rs2' not in _insn.get('operands').keys(): _patch.get('operands').update({'rs2': state.get('operands').get(_insn.get('rs2'))})
        logging.debug('_insn : {}'.format({**_insn, **_patch}))
        state.get('pending_execute').append({
            **_insn,
            **_patch,
        })
    do_execute(service, state)

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
        'service': 'alu',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': [],
        'syscall_kwargs': {},
        'system': riscv.syscall.linux.System(),
        'operands': {
            **{x: riscv.constants.integer_to_list_of_bytes(0, 64, 'little') for x in range(32)},
        },
        'config': {
        },
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if state.get('service') != v.get('service'): continue
                _field = v.get('field')
                _val = eval(v.get('val'))
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
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
