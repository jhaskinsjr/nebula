# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import subprocess

import service
import toolbox
import riscv.constants


def do_tick(service, state, results, events):
    for pc in map(lambda w: w.get('data'), filter(lambda x: x and '%pc' == x.get('name'), map(lambda y: y.get('register'), results))):
        if 0 == int.from_bytes(pc, 'little'):
            service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
            service.tx({'shutdown': None})
        if not state.get('%jp'): state.update({'%jp': pc})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'mem': {
                'cmd': 'peek',
                'addr': int.from_bytes(state.get('%jp'), 'little'),
                'size': 4,
            },
        }})
        state.update({'pending_fetch': int.from_bytes(state.get('%jp'), 'little')})
        state.update({'%jp': riscv.constants.integer_to_list_of_bytes(4 + int.from_bytes(state.get('%jp'), 'little'), 64, 'little')})
        state.update({'%pc': pc})
        state.update({'pending_pc': False})
        toolbox.report_stats(service, state, 'flat', 'fetches')
    for mem in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
#        service.tx({'info': 'mem.addr      : {}'.format(mem.get('addr'))})
#        service.tx({'info': 'pending_fetch : {}'.format(state.get('pending_fetch'))})
        if mem.get('addr') != state.get('pending_fetch'):
            continue
        state.update({'pending_fetch': None})
        state.update({'pending_decode': True})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'decode': {
                'bytes': mem.get('data'),
            },
        }})
    for insns in filter(lambda x: x, map(lambda y: y.get('insns'), results)):
        state.update({'pending_decode': False})
        _pending = [{
            **x,
            **{
                '%pc': state.get('%pc'),
                '_pc': int.from_bytes(state.get('%pc'), 'little'),
            },
            **({'function': next(filter(lambda x: int.from_bytes(state.get('%pc'), 'little') >= x[0], sorted(state.get('objmap').items(), reverse=True)))[-1].get('name', '')} if state.get('objmap') else {}),
        } for x in insns.get('data')]
        state.update({'pending_execute': _pending})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'execute': {
                'insns': _pending,
            }
        }})
    for completed in filter(lambda x: x, map(lambda y: y.get('complete'), events)):
        _completed = {'insns': [{x: y for x, y in filter(lambda z: 'taken' not in z, a.items())} for a in completed.get('insns')]}
        _pending = {'insns': [{x: y for x, y in filter(lambda z: 'taken' not in z, a.items())} for a in state.get('pending_execute')]}
#        service.tx({'info': 'completed  : {}'.format(completed)})
#        service.tx({'info': '_completed : {}'.format(_completed)})
#        service.tx({'info': 'state.get(pending_execute) : {}'.format(state.get('pending_execute'))})
#        service.tx({'info': '_pending   : {}'.format(_pending)})
        assert _completed.get('insns') == _pending.get('insns'), '{} != {}'.format(completed.get('insns'), state.get('pending_execute'))
        _insns = completed.get('insns')
        _jumps = any(map(lambda a: a.get('cmd') in riscv.constants.JUMPS, _insns))
        _taken_branches = any(map(lambda a: a.get('cmd') in riscv.constants.BRANCHES and a.get('taken'), _insns))
#        service.tx({'info': '%jp : {}'.format(state.get('%jp'))})
#        service.tx({'info': '%pc : {}'.format(state.get('%pc'))})
        if not _jumps and not _taken_branches:
            _pc = sum(map(lambda x: x.get('size'), completed.get('insns'))) + int.from_bytes(state.get('%pc'), 'little')
            _pc = riscv.constants.integer_to_list_of_bytes(_pc, 64, 'little')
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'cmd': 'set',
                    'name': '%pc',
                    'data': _pc,
                }
            }})
            state.update({'%pc': _pc})
        else:
            state.update({'%jp': None})
#        service.tx({'info': '%jp : {}'.format(state.get('%jp'))})
#        service.tx({'info': '%pc : {}'.format(state.get('%pc'))})
        state.update({'pending_execute': None})
    _n_committed = len(list(filter(lambda x: x, map(lambda y: y.get('commit'), events))))
    if _n_committed: service.tx({'committed': _n_committed})
    for committed in filter(lambda x: x, map(lambda y: y.get('commit'), events)):
        service.tx({'info': 'retiring : {}'.format(committed)})
#        _n_committed += 1
    if not state.get('pending_pc') and not state.get('pending_fetch') and not state.get('pending_decode') and not state.get('pending_execute'):
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'register': {
                'cmd': 'get',
                'name': '%pc',
            },
        }})
        state.update({'pending_pc': True})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Simple Core')
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
        'service': 'simplecore',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        'pending_pc': False,
        'pending_fetch': None,
        'pending_decode': False,
        'pending_execute': None,
        '%jp': None, # This is the fetch pointer. Why %jp? Who knows?
        '%pc': None,
        'ack': True,
        'objmap': None,
        'config': {
            'toolchain': '',
            'binary': '',
        },
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
                if not state.get('config').get('toolchain'): continue
                _toolchain = state.get('config').get('toolchain')
                _binary = state.get('binary')
                _files = next(iter(list(os.walk(_toolchain))))[-1]
                _objdump = next(filter(lambda x: 'objdump' in x, _files))
                _x = subprocess.run('{} -t {}'.format(os.path.join(_toolchain, _objdump), _binary).split(), capture_output=True)
                if len(_x.stderr): continue
                _objdump = _x.stdout.decode('ascii').split('\n')
                _objdump = sorted(filter(lambda x: len(x), _objdump))
                _objdump = filter(lambda x: re.search('^0', x), _objdump)
                _objdump = map(lambda x: x.split(), _objdump)
                state.update({'objmap': {
                    int(x[0], 16): {
                        'flags': x[1:-1],
                        'name': x[-1]
                    } for x in _objdump
                }})
            elif 'binary' == k:
                state.update({'binary': v})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if state.get('service') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
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
