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
    _retire = []
    _commit = []
    for x in range(len(state.get('pending_commit'))):
        _insn = state.get('pending_commit')[x]
        if not all(map(lambda x: x.get('retired'), state.get('pending_commit')[:x])): continue
        if not any(map(lambda x: x in _insn.keys(), ['next_pc', 'ret_pc', 'result'])): break
        _commit.append(_insn)
        _retire.append(_insn)
        _key = None
        if _insn.get('cmd') in riscv.constants.STORES: _key = 'cycles_per_STORE'
        if _insn.get('cmd') in riscv.constants.LOADS: _key = 'cycles_per_LOAD'
        if _key: toolbox.report_stats(service, state, 'histo', _key, state.get('cycle') - _insn.get('issued'))
        service.tx({'info': 'retiring {}'.format(_insn)})
        if _insn.get('next_pc'):
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'name': '%pc',
                    'data': _insn.get('next_pc'),
                },
            }})
        if _insn.get('ret_pc'):
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'name': _insn.get('rd'),
                    'data': _insn.get('ret_pc'),
                },
            }})
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
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'name': _insn.get('rd'),
                    'data': _insn.get('result'),
                },
            }})
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
                'cmd': _insn.get('cmd'),
                'iid': _insn.get('iid'),
                '%pc': _insn.get('%pc'),
                'word': _insn.get('word'),
                'size': _insn.get('size'),
                'issued': _insn.get('issued'),
#                'retired': state.get('cycle'),
                **({'next_pc': _insn.get('next_pc')} if 'next_pc' in _insn.keys() else {}),
                **({'ret_pc': _insn.get('ret_pc')} if 'ret_pc' in _insn.keys() else {}),
                **({'taken': _insn.get('taken')} if 'taken' in _insn.keys() else {}),
                **({'result': _insn.get('result')} if 'result' in _insn.keys() else {}),
                **({'prediction': _insn.get('prediction')} if 'prediction' in _insn.keys() else {}),
            },
        }})
        _insn.update({'retired': True})
        toolbox.report_stats(service, state, 'flat', 'retires')
        state.update({'ncommits': 1 + state.get('ncommits')})
        _pc = _insn.get('_pc')
        _word = ('{:08x}'.format(_insn.get('word')) if 4 == _insn.get('size') else '    {:04x}'.format(_insn.get('word')))
        logging.info('do_commit(): {:8x}: {} : {:10} ({:12}, {})'.format(_pc, _word, _insn.get('cmd'), state.get('cycle'), _insn.get('function', '')))
    service.tx({'committed': len(_retire)})
    if len(_commit):
        toolbox.report_stats(service, state, 'histo', 'retired_per_cycle', len(_retire))
    for _insn in _commit: state.get('pending_commit').remove(_insn)

def do_tick(service, state, results, events):
    for _l1dc in map(lambda y: y.get('l1dc'), filter(lambda x: x.get('l1dc'), results)):
        service.tx({'info': '_l1dc : {}'.format(_l1dc)})
        for _insn in filter(lambda a: a.get('cmd') in riscv.constants.LOADS, state.get('pending_commit')):
            if _insn.get('operands').get('addr') != _l1dc.get('addr'): continue
            assert 'data' in _l1dc.keys()
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
                'LR.D': _peeked,
                'LR.W': _peeked[:4] + [(0xff if ((_peeked[3] >> 7) & 0b1) else 0)] * 4,
            }.get(_insn.get('cmd'))
            _index = state.get('pending_commit').index(_insn)
            state.get('pending_commit')[_index] = {
                **_insn,
                **{
                    'result': _result,
                },
            }
    for _commit in map(lambda y: y.get('commit'), filter(lambda x: x.get('commit'), events)):
        _insn = _commit.get('insn')
        state.get('pending_commit').append(_insn)
    state.update({'pending_commit': sorted(state.get('pending_commit'), key=lambda x: x.get('iid'))})
    if len(state.get('pending_commit')): do_commit(service, state)
    service.tx({'info': 'pending_commit : [{}]'.format(', '.join(map(
        lambda x: '({}{}, {}, {})'.format(
            x.get('cmd'),
            (' @{}'.format(x.get('operands').get('addr')) if x.get('cmd') in riscv.constants.LOADS + riscv.constants.STORES else ''),
            x.get('%pc'),
            x.get('iid')
        ),
        state.get('pending_commit')
    )))})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Commit')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
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
        'ncommits': 0,
        'active': True,
        'running': False,
        'ack': True,
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
