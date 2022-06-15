import sys
import argparse
import functools
import struct

import service
import toolbox
import riscv.constants

def do_commit(service, state):
    service.tx({'info': 'pending_commit : [{}]'.format(', '.join(map(
        lambda x: '({}{}, {}, {})'.format(
            x.get('cmd'),
            (' @{}'.format(x.get('operands').get('addr')) if x.get('cmd') in riscv.constants.LOADS + riscv.constants.STORES else ''),
            x.get('%pc'),
            x.get('iid')
        ),
        state.get('pending_commit')
    )))})
    _retire = []
    service.tx({'info': 'pending_commit : {}'.format(state.get('pending_commit'))})
    for _insn in state.get('pending_commit'):
        service.tx({'info': '_insn : {}'.format(_insn)})
        if not any(map(lambda x: x in _insn.keys(), ['next_pc', 'ret_pc', 'result'])): break
        _retire.append(_insn)
        if state.get('flush_until') and state.get('flush_until') != _insn.get('%pc'):
            service.tx({'info': 'flushing {}'.format(_insn)})
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'flush': {
                    'iid': _insn.get('iid'),
                },
            }})
            toolbox.report_stats(service, state, 'flat', 'flushes')
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
        if _insn.get('result') and _insn.get('rd'):
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'register': {
                    'cmd': 'set',
                    'name': _insn.get('rd'),
                    'data': _insn.get('result'),
                },
            }})
        service.tx({'result': {
            'arrival': 1 + state.get('cycle'),
            'retire': {
                'iid': _insn.get('iid'),
            },
        }})
        toolbox.report_stats(service, state, 'flat', 'retires')
    for _insn in _retire: state.get('pending_commit').remove(_insn)

def do_tick(service, state, results, events):
    for _mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
        service.tx({'info': '_mem : {}'.format(_mem)})
        if 'data' in _mem.keys():
            for _insn in filter(lambda a: a.get('cmd') in riscv.constants.LOADS, state.get('pending_commit')):
                assert _insn.get('operands')
                if _insn.get('operands').get('addr') != _mem.get('addr'): continue
                service.tx({'info': '(LOAD)  _insn : {}'.format(_insn)})
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
                _index = state.get('pending_commit').index(_insn)
                state.get('pending_commit')[_index] = {
                    **_insn,
                    **{
                        'result': _result,
                    },
                }
        else:
            for _insn in filter(lambda a: a.get('cmd') in riscv.constants.STORES, state.get('pending_commit')):
                assert _insn.get('operands')
                if _insn.get('operands').get('addr') != _mem.get('addr'): continue
                service.tx({'info': '(STORE) _insn : {}'.format(_insn)})
                _index = state.get('pending_commit').index(_insn)
                state.get('pending_commit')[_index] = {
                    **_insn,
                    **{
                        'result': None,
                    },
                }
    for _commit in map(lambda y: y.get('commit'), filter(lambda x: x.get('commit'), events)):
        state.get('pending_commit').append(_commit.get('insn'))
    state.update({'pending_commit': sorted(state.get('pending_commit'), key=lambda x: x.get('iid'))})
    do_commit(service, state)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Commit')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    state = {
        'service': 'commit',
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'flush_until': None,
        'pending_commit': [],
    }
    _service = service.Service(state.get('service'), _launcher.get('host'), _launcher.get('port'))
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