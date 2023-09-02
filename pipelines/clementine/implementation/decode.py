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
import riscv.decode

def remaining_buffer_availability():
    return state.get('config').get('buffer_capacity') - len(state.get('buffer')) - sum(map(lambda x: x.get('size'), state.get('pending_fetch')))
def hazard(p, c):
    return 'rd' in p.keys() and (('rs1' in c.keys() and p.get('rd') == c.get('rs1')) or ('rs2' in c.keys() and p.get('rd') == c.get('rs2')))

def do_issue(service, state):
    for _insn in state.get('decoded'):
        toolbox.report_stats(service, state, 'histo', 'decoded.insn', _insn.get('cmd'))
        if any(map(lambda x: hazard(x, _insn), state.get('issued'))): break
        if _insn.get('cmd') not in ['ECALL', 'FENCE']:
            if _insn.get('rs1'): service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'cmd': 'get',
                    'name': _insn.get('rs1'),
                }
            }})
            if _insn.get('rs2'): service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'register': {
                    'cmd': 'get',
                    'name': _insn.get('rs2'),
                }
            }})
        else:
            # FIXME: This is not super-realistic because it
            # requests all seven of the registers used by a
            # RISC-V Linux syscall all at once (see: https://git.kernel.org/pub/scm/docs/man-pages/man-pages.git/tree/man2/syscall.2?h=man-pages-5.04#n332;
            # basically, the syscall number is in x17, and
            # as many as six parameters are in x10 through
            # x15). But I just now I prefer to focus on
            # syscall proxying, rather than realism.
            for _reg in [10, 11, 12, 13, 14, 15, 17]:
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': state.get('coreid'),
                    'register': {
                        'cmd': 'get',
                        'name': _reg,
                    }
                }})
        service.tx({'event': {
            'arrival': 2 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'alu': {
                'insn': _insn,
            },
        }})
        state.get('issued').append(_insn)
        for _ in range(_insn.get('size')): state.get('buffer').pop(0)
        toolbox.report_stats(service, state, 'histo', 'issued.insn', _insn.get('cmd'))
def do_tick(service, state, results, events):
    for _reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%pc' != _reg.get('name'): continue
        _pc = _reg.get('data')
        service.tx({'info': '_pc           : {}'.format(_pc)})
        service.tx({'info': 'state.get(pc) : {}'.format(state.get('%pc'))})
        state.update({'drop_until': int.from_bytes(_pc, 'little')})
        state.update({'purge_pending_fetch': True})
        state.get('buffer').clear()
        state.get('decoded').clear()
    for _mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
        if state.get('drop_until'):
            if _mem.get('addr') != state.get('drop_until'): continue
            state.update({'drop_until': None})
            state.update({'%pc': list(_mem.get('addr').to_bytes(8, 'little'))})
        _data = _mem.pop('data')
        if _mem not in state.get('pending_fetch'): continue
        state.get('pending_fetch').remove(_mem)
        service.tx({'info': '_mem : {}'.format(_mem)})
        state.get('buffer').extend(_data)
        service.tx({'info': 'buffer : {}'.format(list(map(lambda x: hex(x), state.get('buffer'))))})
    for _flush, _retire in map(lambda y: (y.get('flush'), y.get('retire')), filter(lambda x: x.get('flush') or x.get('retire'), results)):
        if _flush: service.tx({'info': '_flush : {}'.format(_flush)})
        if _retire: service.tx({'info': '_retire : {}'.format(_retire)})
        _commit = (_flush if _flush else _retire)
        assert state.get('issued')[0].get('iid') == _commit.get('iid')
        state.get('issued').pop(0)
    for _dec in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
        state.get('pending_fetch').append(_dec)
    if state.get('purge_pending_fetch'):
        state.get('pending_fetch').clear()
        state.update({'purge_pending_fetch': False})
    service.tx({'info': 'pending_fetch : {}'.format(state.get('pending_fetch'))})
    service.tx({'info': 'max - len(decoded)  : {}'.format(state.get('max_instructions_to_decode') - len(state.get('decoded')))})
    for _insn in riscv.decode.do_decode(state.get('buffer'), state.get('max_instructions_to_decode') - len(state.get('decoded'))):
        # ECALL/FENCE must execute alone, i.e., all issued instructions
        # must retire before an ECALL/FENCE instruction will issue and no
        # further instructions will issue so long as an ECALL/FENCE has
        # yet to flush/retire
        if _insn.get('cmd') in ['ECALL', 'FENCE'] and len(state.get('issued')): break
        if len(state.get('issued')) and state.get('issued')[0].get('cmd') in ['ECALL', 'FENCE']: break
        state.get('decoded').append({
            **_insn,
            **{'iid': state.get('iid')},
            **{'%pc': state.get('%pc')},
            **{'_pc': int.from_bytes(state.get('%pc'), 'little')},
            **({'function': next(filter(lambda x: int.from_bytes(state.get('%pc'), 'little') >= x[0], sorted(state.get('objmap').items(), reverse=True)))[-1].get('name', '')} if state.get('objmap') else {}),
        })
        state.update({'iid': 1 + state.get('iid')})
        state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_insn.get('size') + int.from_bytes(state.get('%pc'), 'little'), 64, 'little')})
    service.tx({'result': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'decode.buffer_available': remaining_buffer_availability(),
    }})
    service.tx({'info': 'state.decoded       : {}'.format(state.get('decoded'))})
    if not len(state.get('decoded')): return
    do_issue(service, state)
    service.tx({'info': 'state.decoded       : {}'.format(state.get('decoded'))})
    service.tx({'info': 'state.issued        : {}'.format(state.get('issued'))})
    for _insn in filter(lambda x: x in state.get('decoded'), state.get('issued')):
        state.get('decoded').remove(_insn)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Instruction Decode')
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
        'service': 'decode',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        '%pc': None,
        'ack': True,
        'buffer': [],
        'drop_until': None,
        'pending_fetch': [],
        'purge_pending_fetch': False,
        'decoded': [],
        'issued': [],
        'iid': 0,
        'max_instructions_to_decode': 1, # HACK: hard-coded max-instructions-to-decode of 1
        'objmap': None,
        'binary': '',
        'config': {
            'buffer_capacity': 16,
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
            elif 'register' == k:
                logging.info('register : {}'.format(v))
                if not state.get('coreid') == v.get('coreid'): continue
                if not '%pc' == v.get('name'): continue
                if not 'set' == v.get('cmd'): continue
                _pc = v.get('data')
                state.update({'%pc': _pc})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
