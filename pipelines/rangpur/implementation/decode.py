# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import itertools
import subprocess

import service
import toolbox
import components.simplebtb
import riscv.constants
import riscv.decode

def do_tick(service, state, results, events):
    logging.debug('do_tick(): results : {}'.format(results))
    for _retire in map(lambda y: y.get('retire'), filter(lambda x: x.get('retire'), results)):
        service.tx({'info': 'retiring : {}'.format(_retire)})
        if not _retire.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS: continue
        if _retire.get('taken'):
            state.get('buffer').clear()
            _next_pc = _retire.get('next_pc')
            state.update({'%pc': _next_pc})
            state.update({'%jp': _next_pc})
    for _pr in map(lambda x: x.get('prediction'), filter(lambda y: y.get('prediction'), results)):
        if 'branch' != _pr.get('type'): continue
        service.tx({'info': '_pr : {}'.format(_pr)})
    for _dec in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
        if state.get('%jp') and _dec.get('addr') != int.from_bytes(state.get('%jp'), 'little'): continue
        service.tx({'info': '_dec : {}'.format(_dec)})
        state.get('buffer').extend(_dec.get('data'))
        state.update({'%jp': riscv.constants.integer_to_list_of_bytes(_dec.get('addr') + len(_dec.get('data')), 64, 'little')})
    _decoded = []
    for _insn in riscv.decode.do_decode(state.get('buffer'), state.get('config').get('max_instructions_to_decode')):
        _pc = int.from_bytes(state.get('%pc'), 'little')
        _decoded.append({
            **_insn,
            **{'%pc': state.get('%pc')},
            **{'_pc': _pc},
            **({'function': next(filter(lambda x: _pc >= x[0], sorted(state.get('objmap').items(), reverse=True)))[-1].get('name', '')} if state.get('objmap') else {}),
        })
        toolbox.report_stats(service, state, 'histo', 'decoded.insn', _insn.get('cmd'))
        state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_insn.get('size') + int.from_bytes(state.get('%pc'), 'little'), 64, 'little')})
    for _insn in _decoded:
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'issue': {
                'insn': _insn,
            },
        }})
    for _ in range(sum(map(lambda x: x.get('size'), _decoded))): state.get('buffer').pop(0)
    service.tx({'info': 'state.buffer           : {} ({})'.format(state.get('buffer'), len(state.get('buffer')))})
    service.tx({'info': 'state.%pc              : {} ({})'.format(state.get('%pc'), ('' if not state.get('%pc') else int.from_bytes(state.get('%pc'), 'little')))})
    service.tx({'info': 'state.%jp              : {} ({})'.format(state.get('%jp'), ('' if not state.get('%jp') else int.from_bytes(state.get('%jp'), 'little')))})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Instruction Decode')
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
        'service': 'decode',
        'cycle': 0,
        'coreid': args.coreid,
        'btb': None,
        'active': True,
        'running': False,
        '%pc': None,
        '%jp': None, # address of the first byte beyond the end of state.buffer
        'ack': True,
        'buffer': [],
        'iid': 0,
        'objmap': None,
        'binary': '',
        'config': {
            'buffer_capacity': 16,
            'btb_nentries': 32,
            'btb_nbytesperentry': 16,
            'btb_evictionpolicy': 'lru',
            'max_instructions_to_decode': 2,
            'toolchain': '',
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                if state.get('config').get('btb_nentries'): state.update({'btb': components.simplebtb.SimpleBTB(
                    state.get('config').get('btb_nentries'),
                    state.get('config').get('btb_nbytesperentry'),
                    state.get('config').get('btb_evictionpolicy'),
                )})
                if not state.get('config').get('toolchain'): continue
                if not state.get('binary'): continue
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
            elif 'register' == k:
                if not state.get('coreid') == v.get('coreid'): continue
                if not '%pc' == v.get('name'): continue
                if not 'set' == v.get('cmd'): continue
                _pc = v.get('data')
                state.update({'%pc': _pc})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
