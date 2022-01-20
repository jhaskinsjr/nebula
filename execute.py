import sys
import argparse

import service

def do_unimplemented(service, state, insn):
    print('Unimplemented: {}'.format(state.get('pending_execute')))
    do_complete(service, state)
def do_auipc(service, state, insn):
#    service.tx({'info': state.get('%pc')})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': insn.get('imm') + state.get('%pc'),
        }
    }})
    do_complete(service, state)
def do_jal(service, state, insn):
    # should always have %pc
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': '%pc',
            'data': insn.get('imm') + state.get('%pc'),
        }
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': 4 + state.get('%pc'),
        }
    }})
    do_complete(service, state)
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
#    service.tx({'info': 'insn : {}'.format(insn)})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': insn.get('imm') + state.get('operands').get('rs1'),
        }
    }})
    state.update({'operands': {}})
    do_complete(service, state)

def do_execute(service, state):
    for insn in state.get('pending_execute'):
        if 0x3 == insn.get('word') & 0x3:
            print('do_execute(): {:08x} : {}'.format(insn.get('word'), insn.get('cmd')))
        else:
            print('do_execute():     {:04x} : {}'.format(insn.get('word'), insn.get('cmd')))
        # TODO: actually *do* the insn; just print and NOP for now
        {
            'AUIPC': do_auipc,
            'JAL': do_jal,
            'ADDI': do_addi,
        }.get(insn.get('cmd'), do_unimplemented)(service, state, insn)
def do_complete(service, state):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'complete': {
            'insns': state.get('pending_execute'),
        },
    }})
    state.update({'pending_execute': None})

def do_tick(service, state, results, events):
    for rs in filter(lambda x: x, map(lambda y: y.get('register'), results)):
        if '%pc' == rs.get('name'):
            state.update({'%pc': rs.get('data')})
        elif '%{}'.format(rs.get('name')) == state.get('operands').get('rs1'):
            state.get('operands').update({'rs1': rs.get('data')})
    for ev in filter(lambda x: x, map(lambda y: y.get('execute'), events)):
#        service.tx({'info': ev})
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
        '%rs1': None,
        '%rs2': None,
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