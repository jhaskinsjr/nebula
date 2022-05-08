import sys
import argparse
import functools
import struct

import service
import riscv.execute
import riscv.syscall.linux

def do_unimplemented(service, state, insn):
#    print('Unimplemented: {}'.format(state.get('pending_execute')))
    service.tx({'undefined': insn})
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)

def do_lui(service, state, insn):
    _result = riscv.execute.lui(insn.get('imm'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': _result,
                },
            },
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
def do_auipc(service, state, insn):
    _result = riscv.execute.auipc(insn.get('%pc'), insn.get('imm'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': _result,
                },
            },
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
def do_jal(service, state, insn):
    _next_pc, _ret_pc = riscv.execute.jal(insn.get('%pc'), insn.get('imm'), insn.get('size'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
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
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
def do_jalr(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _next_pc, _ret_pc = riscv.execute.jalr(insn.get('%pc'), insn.get('imm'), _rs1, insn.get('size'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
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
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
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
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
def do_itype(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _result = {
        'ADDI': riscv.execute.addi,
        'SLTI': riscv.execute.slti,
        'SLTIU': riscv.execute.sltiu,
        'ADDIW': riscv.execute.addiw,
        'ANDI': riscv.execute.andi,
    }.get(insn.get('cmd'))(_rs1, insn.get('imm'))
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
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
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
def do_rtype(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _rs2 = state.get('operands').get(insn.get('rs2'))
    _result = {
        'ADD': riscv.execute.add,
        'SUB': riscv.execute.sub,
        'XOR': riscv.execute.xor,
        'OR': riscv.execute.do_or,
        'AND': riscv.execute.do_and,
        'ADDW': riscv.execute.addw,
        'SUBW': riscv.execute.subw,
        'MUL': riscv.execute.mul,
        'MULH': riscv.execute.mulh,
        'MULHSU': riscv.execute.mulhsu,
        'MULHU': riscv.execute.mulhu,
        'DIV': riscv.execute.div,
        'DIVU': riscv.execute.divu,
        'REM': riscv.execute.rem,
        'REMU': riscv.execute.remu,
    }.get(insn.get('cmd'))(_rs1, _rs2)
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
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
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
def do_load(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
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
def do_store(service, state, insn):
    _rs1 = state.get('operands').get(insn.get('rs1'))
    _rs2 = state.get('operands').get(insn.get('rs2'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
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
def do_nop(service, state, insn):
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
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
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
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
    _result = riscv.syscall.linux.do_syscall(_syscall_num, _syscall_a0, _syscall_a1, _syscall_a2, _syscall_a3, _syscall_a4, _syscall_a5)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': _a0,
            'data': _result,
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)
def do_fence(service, state, insn):
    # HACK: in a complex pipeline, this needs to be more than a NOP
    service.tx({'event': {
        'arrival': 2 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})
    do_complete(service, state, insn)
    do_confirm(service, state, insn)

def do_execute(service, state):
    if not len(state.get('pending_execute')): return
    for _insn in map(lambda x: x.get('insn'), state.get('pending_execute')):
        state.get('pending_execute').pop(0)
        service.tx({'info': '_insn : {}'.format(_insn)})
        if 0x3 == _insn.get('word') & 0x3:
            print('do_execute(): @{:8} {:08x} : {}'.format(state.get('cycle'), _insn.get('word'), _insn.get('cmd')))
        else:
            print('do_execute(): @{:8}     {:04x} : {}'.format(state.get('cycle'), _insn.get('word'), _insn.get('cmd')))
        {
            'LUI': do_lui,
            'AUIPC': do_auipc,
            'JAL': do_jal,
            'JALR': do_jalr,
            'ADDI': do_itype,
            'ADDIW': do_itype,
            'ANDI': do_itype,
            'SLTI': do_itype,
            'SLTIU': do_itype,
            'ADD': do_rtype,
            'SUB': do_rtype,
            'XOR': do_rtype,
            'OR': do_rtype,
            'AND': do_rtype,
            'ADDW': do_rtype,
            'SUBW': do_rtype,
            'MUL': do_rtype,
            'MULH': do_rtype,
            'MULHSU': do_rtype,
            'MULHU': do_rtype,
            'DIV': do_rtype,
            'DIVU': do_rtype,
            'REM': do_rtype,
            'REMU': do_rtype,
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
        }.get(_insn.get('cmd'), do_unimplemented)(service, state, _insn)
def do_complete(service, state, insn): # finished the work of the instruction, but will not necessarily be committed
    pass
#    service.tx({'event': {
#        'arrival': 1 + state.get('cycle'),
#        'complete': {
#            'insn': insn,
#        },
#    }})
def do_confirm(service, state, insn): # definitely will commit
    pass
#    service.tx({'event': {
#        'arrival': 1 + state.get('cycle'),
#        'confirm': {
#            'insn': insn,
#        },
#    }})

def do_tick(service, state, results, events):
    for _reg in filter(lambda x: x, map(lambda y: y.get('register'), results)):
        _name = _reg.get('name')
        _data = _reg.get('data')
        state.get('operands').update({_name: _data})
    for _insn in map(lambda y: y.get('alu'), filter(lambda x: x.get('alu'), events)):
        state.get('pending_execute').append(_insn)
    do_execute(service, state)
    # TODO: properly handle ECALL instruction, which requires a LOT (!) of registers

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Execute')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    _service = service.Service('alu', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': [],
        'operands': {
            **{x: riscv.constants.integer_to_list_of_bytes(0, 64, 'little') for x in range(32)},
        },
    }
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
                _results = v.get('results')
                _events = v.get('events')
                do_tick(_service, state, _results, _events)
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))