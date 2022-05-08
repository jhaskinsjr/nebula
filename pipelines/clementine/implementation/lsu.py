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
        'arrival': 1 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})

def do_load(service, state, insn):
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'mem': {
            'cmd': 'peek',
            'addr': insn.get('operands').get('addr'),
            'size': insn.get('nbytes'),
        }
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
            },
        }
    }})
def do_store(service, state, insn):
    _data = insn.get('operands').get('data')
    _data = {
        'SD': _data,
        'SW': _data[:4],
        'SH': _data[:2],
        'SB': _data[:1],
    }.get(insn.get('cmd'))
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'mem': {
            'cmd': 'poke',
            'addr': insn.get('operands').get('addr'),
            'size': insn.get('nbytes'),
            'data': _data
        }
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'commit': {
            'insn': {
                **insn,
                **{
                    'result': None,
                },
            },
        }
    }})

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
        }.get(_insn.get('cmd'), do_unimplemented)(service, state, _insn)

def do_tick(service, state, results, events):
    for _insn in map(lambda y: y.get('lsu'), filter(lambda x: x.get('lsu'), events)):
        state.get('pending_execute').append(_insn)
    for _mem in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
        if _mem.get('addr') == state.get('operands').get('mem'):
            state.get('operands').update({'mem': _mem.get('data')})
    do_execute(service, state)

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
    _service = service.Service('lsu', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': [],
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