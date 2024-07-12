# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import subprocess

import service
import toolbox
import toolbox.stats
import riscv.constants


def do_tick(service, state, results, events):
    for reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%pc' != reg.get('name'): continue
        state.update({'%pc': reg.get('data')})
        service.tx({'info': 'state.%pc : {}'.format(state.get('%pc'))})
        if 0 == int.from_bytes(state.get('%pc'), 'little'):
            service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
            service.tx({'shutdown': {
                'coreid': state.get('coreid'),
            }})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'mem': {
                'cmd': 'peek',
                'addr': int.from_bytes(state.get('%pc'), 'little'),
                'size': 4,
            },
        }})
        state.update({'pending_fetch': int.from_bytes(state.get('%pc'), 'little')})
        state.update({'pending_pc': False})
#        toolbox.report_stats(service, state, 'flat', 'fetches')
        state.get('stats').refresh('flat', 'fetches')
    for mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
        if mem.get('addr') != state.get('pending_fetch'): continue
        state.update({'pending_fetch': None})
        state.update({'pending_decode': True})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'decode': {
                'bytes': mem.get('data'),
                '%pc': state.get('%pc'),
            },
        }})
    for insn in map(lambda y: y.get('insn'), filter(lambda x: x.get('insn'), results)):
        state.update({'pending_decode': False})
        _insn = {
            **insn,
            **{'iid': state.get('iid')},
            **({'function': next(filter(lambda x: int.from_bytes(insn.get('%pc'), 'little') >= x[0], sorted(state.get('objmap').items(), reverse=True)))[-1].get('name', '')} if state.get('objmap') else {}),
        }
        state.update({'pending_execute': _insn})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'execute': {
                'insn': _insn,
            }
        }})
        state.update({'iid': 1 + state.get('iid')})
    for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
        _cmd = _perf.get('cmd')
        if 'report_stats' == _cmd:
            _dict = state.get('stats').get(state.get('coreid')).get(state.get('service'))
            toolbox.report_stats_from_dict(service, state, _dict)
    for _shutdown in map(lambda y: y.get('shutdown'), filter(lambda x: x.get('shutdown'), events)):
        assert _shutdown
        service.tx({'shutdown': {
            'coreid': state.get('coreid'),
        }})
    for complete in map(lambda y: y.get('complete'), filter(lambda x: x.get('complete'), events)):
        _insn = complete.get('insn')
        assert _insn.get('iid') == state.get('pending_execute').get('iid'), '_insn : {} != state.pending_execute : {}'.format(_insn, state.get('pending_execute'))
        _jump = _insn.get('cmd') in riscv.constants.JUMPS
        _taken = _insn.get('taken')
        if not _jump and not _taken:
            _pc = int.from_bytes(_insn.get('%pc'), 'little')
            state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_pc + _insn.get('size'), 64, 'little')})
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'cmd': 'set',
                    'name': '%pc',
                    'data': state.get('%pc'),
                }
            }})
            state.update({'%pc': _pc})
        state.update({'pending_execute': None})
    for commit in map(lambda y: y.get('commit'), filter(lambda x: x.get('commit'), events)):
        _insn = commit.get('insn')
        if _insn.get('shutdown'):
            _insn.update({'operands': {int(k):v for k, v in _insn.get('operands').items()}})
            _x17 = _insn.get('operands').get(17)
            service.tx({'info': 'ECALL {}... graceful shutdown'.format(int.from_bytes(_x17, 'little'))})
#            service.tx({'shutdown': {
#                'coreid': state.get('coreid'),
#            }})
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'perf': {
                    'cmd': 'report_stats',
                },
            }})
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'shutdown': True,
            }})
        service.tx({'committed': 1})
        logging.info('retiring : {}'.format(_insn))
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
    service.tx({'info': 'state.pending_pc      : {}'.format(state.get('pending_pc'))})
    service.tx({'info': 'state.pending_fetch   : {}'.format(state.get('pending_fetch'))})
    service.tx({'info': 'state.pending_decode  : {}'.format(state.get('pending_decode'))})
    service.tx({'info': 'state.pending_execute : {}'.format(state.get('pending_execute'))})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Simple Core')
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
        'service': 'simplecore',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        'pending_pc': False,
        'pending_fetch': None,
        'pending_decode': False,
        'pending_execute': None,
        'stats': None,
        'iid': 0,
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
                state.update({'pending_pc': False})
                state.update({'pending_fetch': None})
                state.update({'pending_decode': False})
                state.update({'pending_execute': None})
                state.update({'stats': toolbox.stats.CounterBank(state.get('coreid'), state.get('service'))})
                state.update({'%pc': None})
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
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
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
