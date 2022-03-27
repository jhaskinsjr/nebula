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
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})

def do_lui(service, state, insn):
    _result = riscv.execute.lui(insn.get('imm'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_auipc(service, state, insn):
    _result = riscv.execute.auipc(state.get('%pc'), insn.get('imm'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_jal(service, state, insn):
    _next_pc, _ret_pc = riscv.execute.jal(state.get('%pc'), insn.get('imm'), insn.get('size'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': '%pc',
            'data': _next_pc,
        }
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _ret_pc,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_jalr(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    _next_pc, _ret_pc = riscv.execute.jalr(state.get('%pc'), insn.get('imm'), state.get('operands').get('rs1'), insn.get('size'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': '%pc',
            'data': _next_pc,
        }
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _ret_pc,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_branch(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
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
    }.get(insn.get('cmd'))(state.get('%pc'), state.get('operands').get('rs1'), state.get('operands').get('rs2'), insn.get('imm'), insn.get('size'))
    insn.update({'taken': _taken})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': '%pc',
            'data': _next_pc,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_itype(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), list):
        return
    _result = {
        'ADDI': riscv.execute.addi(state.get('operands').get('rs1'), insn.get('imm')),
        'ADDIW': riscv.execute.addiw(state.get('operands').get('rs1'), insn.get('imm')),
        'ANDI': riscv.execute.andi(state.get('operands').get('rs1'), insn.get('imm')),
    }.get(insn.get('cmd'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_rtype(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
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
            'register': {
                'cmd': 'get',
                'name': insn.get('rs2'),
            }
        }})
    if not isinstance(state.get('operands').get('rs2'), list):
        return
    _result = {
        'ADD': riscv.execute.add(state.get('operands').get('rs1'), state.get('operands').get('rs2')),
        'SUB': riscv.execute.sub(state.get('operands').get('rs1'), state.get('operands').get('rs2')),
        'XOR': riscv.execute.xor(state.get('operands').get('rs1'), state.get('operands').get('rs2')),
        'OR': riscv.execute.do_or(state.get('operands').get('rs1'), state.get('operands').get('rs2')),
        'AND': riscv.execute.do_and(state.get('operands').get('rs1'), state.get('operands').get('rs2')),
        'ADDW': riscv.execute.addw(state.get('operands').get('rs1'), state.get('operands').get('rs2')),
        'SUBW': riscv.execute.subw(state.get('operands').get('rs1'), state.get('operands').get('rs2')),
    }.get(insn.get('cmd'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_load(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
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
#    print('do_load(): _fetched : {} ({})'.format(_fetched, len(_fetched)))
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
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _data,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_store(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
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
        'mem': {
            'cmd': 'poke',
            'addr': insn.get('imm') + int.from_bytes(state.get('operands').get('rs1'), 'little'),
            'size': _size,
            'data': _data
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_nop(service, state, insn):
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
def do_shift(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
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
        'SLLI': riscv.execute.slli(_rs1, _shamt),
        'SRLI': riscv.execute.srli(_rs1, _shamt),
        'SRAI': riscv.execute.srai(_rs1, _shamt),
        'SLLIW': riscv.execute.slliw(_rs1, _shamt),
        'SRLIW': riscv.execute.srliw(_rs1, _shamt),
        'SRAIW': riscv.execute.sraiw(_rs1, _shamt),
    }.get(insn.get('cmd'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': _result,
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
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
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})

def do_execute(service, state):
    for insn in state.get('pending_execute'):
        if 0x3 == insn.get('word') & 0x3:
            print('do_execute(): @{:8} {:08x} : {}'.format(state.get('cycle'), insn.get('word'), insn.get('cmd')))
        else:
            print('do_execute(): @{:8}     {:04x} : {}'.format(state.get('cycle'), insn.get('word'), insn.get('cmd')))
        {
            'LUI': do_lui,
            'AUIPC': do_auipc,
            'JAL': do_jal,
            'JALR': do_jalr,
            'ADDI': do_itype,
            'ADDIW': do_itype,
            'ANDI': do_itype,
#            'ADDI': do_addi,
#            'ADDIW': do_addiw,
#            'ANDI': do_andi,
            'ADD': do_rtype,
            'SUB': do_rtype,
            'XOR': do_rtype,
            'OR': do_rtype,
            'AND': do_rtype,
            'ADDW': do_rtype,
            'SUBW': do_rtype,
#            'ADD': do_add,
#            'SUB': do_sub,
#            'ADDW': do_addw,
#            'SUBW': do_subw,
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
        }.get(insn.get('cmd'), do_unimplemented)(service, state, insn)
def do_complete(service, state, insns): # finished the work of the instruction, but will not necessarily be committed
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'complete': {
            'insns': insns,
        },
    }})
def do_confirm(service, state, insns): # definitely will commit
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'confirm': {
            'insns': insns,
        },
    }})
def do_commit(service, state, insns):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'commit': {
            'insns': insns,
        },
    }})

def do_tick(service, state, results, events):
    for rs in filter(lambda x: x, map(lambda y: y.get('register'), results)):
        if '%pc' == rs.get('name'):
            state.update({'%pc': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('rs1'):
            state.get('operands').update({'rs1': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('rs2'):
            state.get('operands').update({'rs2': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('syscall_num'):
            state.get('operands').update({'syscall_num': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('syscall_a0'):
            state.get('operands').update({'syscall_a0': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('syscall_a1'):
            state.get('operands').update({'syscall_a1': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('syscall_a2'):
            state.get('operands').update({'syscall_a2': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('syscall_a3'):
            state.get('operands').update({'syscall_a3': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('syscall_a4'):
            state.get('operands').update({'syscall_a4': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('syscall_a5'):
            state.get('operands').update({'syscall_a5': rs.get('data')})
    for rs in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
        _mem = rs
        if _mem.get('addr') == state.get('operands').get('mem'):
            state.get('operands').update({'mem': _mem.get('data')})
    for ev in filter(lambda x: x, map(lambda y: y.get('execute'), events)):
        state.update({'pending_execute': ev.get('insns')})
    if state.get('pending_execute'): do_execute(service, state)

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
    _service = service.Service('execute', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': None,
        '%pc': None,
        'operands': {},
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