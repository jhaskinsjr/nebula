import sys
import argparse

import service

def do_unimplemented(service, state, insn):
    print('Unimplemented: {}'.format(state.get('pending_execute')))
    state.update({'pending_execute': None})
def do_auipc(service, state, insn):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': insn.get('imm') + state.get('%pc'),
        }
    }})
    state.update({'pending_execute': None})
def do_jal(service, state, insn):
#    state.update({'%pc': insn.get('imm') + state.get('%pc')})
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
    state.update({'pending_execute': None})
def do_addi(service, state, insn):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'register': {
            'cmd': 'set',
            'name': insn.get('rd'),
            'data': insn.get('imm') + insn.get('rs1'),
        }
    }})
    state.update({'pending_execute': None})

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
#    state.update({'pending_execute': None})

def do_tick(service, state, results, events):
    if state.get('pending_execute'): do_execute(service, state)
    for pc in map(lambda w: w.get('data'), filter(lambda x: x and '%pc' == x.get('name'), map(lambda y: y.get('register'), results))):
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'mem': {
                'cmd': 'peek',
                'addr': pc,
                'size': 4,
            },
        }})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'set',
                'name': '%pc',
                'data': 4 + pc,
            }
        }})
        state.update({'%pc': pc})
        if pc not in state.get('requested_pc'): state.get('requested_pc').append(pc)
    for mem in filter(lambda x: x and x.get('addr') in state.get('requested_pc'), map(lambda y: y.get('mem'), results)):
        state.get('requested_pc').remove(mem.get('addr'))
        state.update({'pending_fetch': False})
        state.update({'pending_decode': True})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'decode': {
                'bytes': mem.get('data'),
            },
        }})
    if not state.get('pending_fetch') and not state.get('pending_decode') and not state.get('pending_execute'):
        state.update({'pending_fetch': True})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': '%pc',
            },
        }})
    for insns in filter(lambda x: x, map(lambda y: y.get('insns'), results)):
        state.update({'pending_decode': False})
        state.update({'pending_execute': insns.get('data')})
        do_execute(service, state)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Simple Core')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    _service = service.Service('simplecore', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        'requested_pc': [], # to allow more than one outstanding PC req at a time
        'pending_fetch': False,
        'pending_decode': False,
        'pending_execute': None,
        '%pc': None,
        'ack': True,
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