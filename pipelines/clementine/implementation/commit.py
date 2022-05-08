import sys
import argparse
import functools
import struct

import service
import riscv.constants

def do_commit(service, state):
    service.tx({'info': 'pending_commit : [{}]'.format(', '.join(map(
        lambda x: '({}, {}, {})'.format(x.get('cmd'), x.get('%pc'), x.get('iid')),
        state.get('pending_commit')
    )))})
    _retire = []
    for _insn in state.get('pending_commit'):
        if not any(map(lambda x: x in _insn.keys(), ['next_pc', 'ret_pc', 'result'])): break
        _retire.append(_insn)
        if state.get('flush_until') and state.get('flush_until') != _insn.get('%pc'):
            service.tx({'info': 'flushing {}'.format(_insn)})
            continue
        state.update({'flush_until': None})
        service.tx({'info': 'retiring {}'.format(_insn)})
        if _insn.get('next_pc') and _insn.get('taken'):
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'register': {
                    'name': '%pc',
                    'data': _insn.get('next_pc'),
                },
            }})
            state.update({'flush_until': _insn.get('next_pc')})
        if _insn.get('ret_pc'):
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'register': {
                    'cmd': 'set',
                    'name': _insn.get('rd'),
                    'data': _insn.get('ret_pc'),
                },
            }})
        if _insn.get('result'):
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'register': {
                    'cmd': 'set',
                    'name': _insn.get('rd'),
                    'data': _insn.get('result'),
                },
            }})
    for _insn in _retire: state.get('pending_commit').remove(_insn)

def do_tick(service, state, results, events):
    for _mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
        service.tx({'info': '_mem : {}'.format(_mem)})
        _new_insn = None
        _old_insn = None
        for _insn in state.get('pending_commit'):
            if not _insn.get('cmd') in riscv.constants.LOADS: continue
            if _insn.get('operands') and _insn.get('operands').get('addr') != _mem.get('addr'): continue
            service.tx({'info': '_insn : {}'.format(_insn)})
            _peeked  = _mem.get('data')
            _peeked += [-1] * (8 - len(_peeked))
            _result = { # HACK: This is 100% little-endian-specific
                'LD': _peeked,
                'LW': _peeked[:4] + [(0xff if ((_peeked[3] >> 7) & 0b1) else 0)] * 4,
                'LH': _peeked[:2] + [(0xff if ((_peeked[1] >> 7) & 0b1) else 0)] * 6,
                'LB': _peeked[:1] + [(0xff if ((_peeked[0] >> 7) & 0b1) else 0)] * 7,
                'LWU': _peeked[:4] + [0] * 4,
                'LHU': _peeked[:2] + [0] * 6,
                'LBU': _peeked[:1] + [0] * 7,
            }.get(_insn.get('cmd'))
            _old_insn = _insn
            _new_insn = {
                **_insn,
                **{
                    'result': _result,
                },
            }
        if _new_insn and _old_insn:
            state.get('pending_commit').remove(_old_insn)
            state.get('pending_commit').append(_new_insn)
    for _commit in map(lambda y: y.get('commit'), filter(lambda x: x.get('commit'), events)):
        state.get('pending_commit').append(_commit.get('insn'))
    state.update({'pending_commit': sorted(state.get('pending_commit'), key=lambda x: x.get('iid'))})
    do_commit(service, state)

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
    _service = service.Service('commit', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        '%pc': None,
        'flush_until': None,
        'pending_commit': [],
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