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
    for _insn in state.get('pending_commit'):
        if not any(map(lambda x: x in _insn.keys(), ['next_pc', 'ret_pc', 'result'])): break
        _retire.append(_insn)
        if state.get('flush_until') and state.get('flush_until') != _insn.get('%pc'):
            service.tx({'info': 'flushing {}'.format(_insn)})
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
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
                'coreid': state.get('coreid'),
                'register': {
                    'name': '%pc',
                    'data': _insn.get('next_pc'),
                },
            }})
            state.update({'flush_until': _insn.get('next_pc')})
        if _insn.get('ret_pc'):
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'cmd': 'set',
                    'name': _insn.get('rd'),
                    'data': _insn.get('ret_pc'),
                },
            }})
        if _insn.get('result') and _insn.get('rd'):
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'cmd': 'set',
                    'name': _insn.get('rd'),
                    'data': _insn.get('result'),
                },
            }})
        service.tx({'result': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'retire': {
                'iid': _insn.get('iid'),
            },
        }})
        toolbox.report_stats(service, state, 'flat', 'retires')
    for _insn in _retire: state.get('pending_commit').remove(_insn)

def do_tick(service, state, results, events):
    for _l1dc in map(lambda y: y.get('l1dc'), filter(lambda x: x.get('l1dc'), results)):
        service.tx({'info': '_l1dc : {}'.format(_l1dc)})
        if 'data' in _l1dc.keys():
            for _insn in filter(lambda a: a.get('cmd') in riscv.constants.LOADS, state.get('pending_commit')):
                assert _insn.get('operands')
                if _insn.get('operands').get('addr') != _l1dc.get('addr'): continue
                service.tx({'info': '_insn : {}'.format(_insn)})
                _peeked  = _l1dc.get('data')
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
                if _insn.get('operands').get('addr') != _l1dc.get('addr'): continue
                service.tx({'info': '_insn : {}'.format(_insn)})
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
        'service': 'commit',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        'ack': True,
        'flush_until': None,
        'pending_commit': [],
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
