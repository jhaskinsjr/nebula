# Copyright (C) 2021, 2022 John Haskins Jr.

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
import riscv.syscall.linux

def do_unimplemented(service, state, insn):
    logging.info('Unimplemented: {}'.format(state.get('pending_execute')))
    service.tx({'undefined': insn})
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})
    return True

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
    return True
def do_auipc(service, state, insn):
    _result = riscv.execute.auipc(insn.get('%pc'), insn.get('imm'))
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
    return True
def do_jal(service, state, insn):
    _next_pc, _ret_pc = riscv.execute.jal(insn.get('%pc'), insn.get('imm'), insn.get('size'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'taken': True,
                    'next_pc': _next_pc,
                    'ret_pc': _ret_pc,
                },
            },
        }
    }})
    return True
def do_jalr(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _next_pc, _ret_pc = riscv.execute.jalr(insn.get('%pc'), insn.get('imm'), _rs1, insn.get('size'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'taken': True,
                    'next_pc': _next_pc,
                    'ret_pc': _ret_pc,
                    'operands': {
                        'rs1': _rs1,
                    },
                },
            },
        }
    }})
    return True
def do_branch(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _rs2 = state.get('operands').get(insn.get('rs2'))
    _next_pc, _taken = {
        'BEQ': riscv.execute.beq,
        'BNE': riscv.execute.bne,
        'BLT': riscv.execute.blt,
        'BGE': riscv.execute.bge,
        'BLTU': riscv.execute.bltu,
        'BGEU': riscv.execute.bgeu,
    }.get(insn.get('cmd'))(insn.get('%pc'), _rs1, _rs2, insn.get('imm'), insn.get('size'))
    insn.update({'taken': _taken})
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'taken': _taken,
                    'next_pc': _next_pc,
                    'operands': {
                        'rs1': _rs1,
                        'rs2': _rs2,
                    },
                },
            },
        }
    }})
    return True
def do_itype(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _result = {
        'ADDI': riscv.execute.addi,
        'SLTI': riscv.execute.slti,
        'SLTIU': riscv.execute.sltiu,
        'ADDIW': riscv.execute.addiw,
        'XORI': riscv.execute.xori,
        'ORI': riscv.execute.ori,
        'ANDI': riscv.execute.andi,
    }.get(insn.get('cmd'))(_rs1, insn.get('imm'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': _result,
                    'operands': {
                        'rs1': _rs1,
                    },
                },
            },
        }
    }})
    return True
def do_rtype(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _rs2 = state.get('operands').get(insn.get('rs2'))
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
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': _result,
                    'operands': {
                        'rs1': _rs1,
                        'rs2': _rs2,
                    },
                },
            },
        }
    }})
    return True
def do_load(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'lsu': {
            'insn': {
                **insn,
                **{
                    'operands': {
                        'rs1': _rs1,
                        'addr': insn.get('imm') + int.from_bytes(_rs1, 'little'),
                    },
                },
            },
        }
    }})
    return True
def do_store(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _rs2 = state.get('operands').get(insn.get('rs2'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'lsu': {
            'insn': {
                **insn,
                **{
                    'operands': {
                        'rs1': _rs1,
                        'data': _rs2,
                        'addr': insn.get('imm') + int.from_bytes(_rs1, 'little'),
                    },
                },
            },
        }
    }})
    return True
def do_nop(service, state, insn):
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})
    return True
def do_shift(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
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
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': _result,
                    'operands': {
                        'rs1': _rs1,
                    },
                },
            },
        }
    }})
    return True
def do_ecall(service, stats, insn):
    _x17 = state.get('operands').get(17)
    _x10 = state.get('operands').get(10)
    _x11 = state.get('operands').get(11)
    _x12 = state.get('operands').get(12)
    _x13 = state.get('operands').get(13)
    _x14 = state.get('operands').get(14)
    _x15 = state.get('operands').get(15)
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
        service.tx({'shutdown': None})
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
        state.update({'syscall_kwargs': {}})
    return _done
def do_fence(service, state, insn):
    # HACK: in a complex pipeline, this needs to be more than a NOP
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})
    return True

def do_execute(service, state):
    if not len(state.get('pending_execute')): return
    _remove_from_pending_execute = []
    for _insn in map(lambda x: x.get('insn'), state.get('pending_execute')):
#        state.get('pending_execute').pop(0)
        service.tx({'info': '_insn : {}'.format(_insn)})
        if 0x3 == _insn.get('word') & 0x3:
            logging.info('do_execute(): @{:8} {:08x} : {}'.format(state.get('cycle'), _insn.get('word'), _insn.get('cmd')))
        else:
            logging.info('do_execute(): @{:8}     {:04x} : {}'.format(state.get('cycle'), _insn.get('word'), _insn.get('cmd')))
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
        if True == _f(service, state, _insn): _remove_from_pending_execute.append(_insn)
        toolbox.report_stats(service, state, 'histo', 'category', _f.__name__)
    for _ in range(len(_remove_from_pending_execute)): state.get('pending_execute').pop(0)

def do_tick(service, state, results, events):
    for _mem in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
        _addr = _mem.get('addr')
        if _addr == state.get('operands').get('mem'):
            state.get('operands').update({'mem': _mem.get('data')})
    for _reg in filter(lambda x: x, map(lambda y: y.get('register'), results)):
        _name = _reg.get('name')
        _data = _reg.get('data')
        state.get('operands').update({_name: _data})
    for _insn in map(lambda y: y.get('alu'), filter(lambda x: x.get('alu'), events)):
        state.get('pending_execute').append(_insn)
    do_execute(service, state)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Execute')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
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
