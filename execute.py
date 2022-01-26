import sys
import argparse

import service
import riscv.execute

def do_unimplemented(service, state, insn):
#    print('Unimplemented: {}'.format(state.get('pending_execute')))
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})

def do_lui(service, state, insn):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': insn.get('imm'),
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
    _next_pc, _ret_pc = riscv.execute.jal(state.get('%pc'), insn.get('imm'))
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
    if not isinstance(state.get('operands').get('rs1'), int):
        return
    _next_pc, _ret_pc = riscv.execute.jalr(state.get('%pc'), insn.get('imm'), state.get('operands').get('rs1'))
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
    if not isinstance(state.get('operands').get('rs1'), int):
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
    if not isinstance(state.get('operands').get('rs2'), int):
        return
    _next_pc = {
        'BEQ': riscv.execute.beq,
        'BNE': riscv.execute.bne,
    }.get(insn.get('cmd'))(state.get('%pc'), state.get('operands').get('rs1'), state.get('operands').get('rs2'), insn.get('imm'))
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
def do_addi(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), int):
        return
    _result = riscv.execute.addi(state.get('operands').get('rs1'), insn.get('imm'))
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
def do_add(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not 'rs2' in state.get('operands'):
        state.get('operands').update({'rs2': '%{}'.format(insn.get('rs2'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs2'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), int) or not isinstance(state.get('operands').get('rs2'), int):
        return
    _result = riscv.execute.add(state.get('operands').get('rs1'), state.get('operands').get('rs2'))
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
def do_ld(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), int):
        return
    if not 'mem' in state.get('operands'):
        state.get('operands').update({'mem': insn.get('imm') + state.get('operands').get('rs1')})
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
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': int.from_bytes(state.get('operands').get('mem'), 'little'),
        }
    }})
    do_complete(service, state, state.get('pending_execute'))
    do_confirm(service, state, state.get('pending_execute'))
    do_commit(service, state, state.get('pending_execute'))
    state.update({'operands': {}})
    state.update({'pending_execute': None})
def do_andi(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), int):
        return
    _result = riscv.execute.andi(state.get('operands').get('rs1'), insn.get('imm'))
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
def do_sd(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), int):
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
    if not isinstance(state.get('operands').get('rs2'), int):
        return
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'mem': {
            'cmd': 'poke',
            'addr': insn.get('imm') + state.get('operands').get('rs1'),
            'size': insn.get('nbytes'),
            'data': state.get('operands').get('rs2')
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
def do_slli(service, state, insn):
    if not 'rs1' in state.get('operands'):
        state.get('operands').update({'rs1': '%{}'.format(insn.get('rs1'))})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': insn.get('rs1'),
            }
        }})
    if not isinstance(state.get('operands').get('rs1'), int):
        return
    _result = riscv.execute.slli(state.get('operands').get('rs1'), insn.get('shamt'))
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
            'ADDI': do_addi,
            'ADD': do_add,
            'LD': do_ld,
            'ANDI': do_andi,
            'SD': do_sd,
            'NOP': do_nop,
            'SLLI': do_slli,
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