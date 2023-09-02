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
import components.simplebtb
import riscv.constants
import riscv.decode

def hazard(p, c):
    if not 'rd' in p.keys(): return []
    _conflict  = ([c.get('rs1')] if ('rs1' in c.keys() and p.get('rd') == c.get('rs1')) else  [])
    _conflict += ([c.get('rs2')] if ('rs2' in c.keys() and p.get('rd') == c.get('rs2')) else  [])
    return _conflict
def do_issue(service, state):
    for _dec in state.get('decoded'):
        # ECALL/FENCE must execute alone, i.e., all issued instructions
        # must retire before an ECALL/FENCE instruction will issue and no
        # further instructions will issue so long as an ECALL/FENCE has
        # yet to flush/retire
        if len(state.get('issued')) and state.get('issued')[-1].get('cmd') in ['ECALL', 'FENCE']: break
        _insn = _dec.get('insn')
        _pc = _dec.get('%pc')
        _hazards = sum(map(lambda x: hazard(x, _insn), state.get('issued')), [])
        service.tx({'info': '_hazards : {}'.format(_hazards)})
        if len(_hazards): break
#        if _insn.get('cmd') in riscv.constants.LOADS + riscv.constants.STORES and any(map(lambda x: x.get('cmd') in riscv.constants.LOADS + riscv.constants.STORES, state.get('issued'))): break
        if _insn.get('cmd') not in ['ECALL', 'FENCE']:
            if 'rs1' in _insn.keys():
                if 'operands' not in _insn.keys(): _insn.update({'operands': {}})
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': state.get('coreid'),
                    'register': {
                        'cmd': 'get',
                        'name': _insn.get('rs1'),
                    },
                }})
            if 'rs2' in _insn.keys():
                if 'operands' not in _insn.keys(): _insn.update({'operands': {}})
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': state.get('coreid'),
                    'register': {
                        'cmd': 'get',
                        'name': _insn.get('rs2'),
                    },
                }})
        else:
            if len(state.get('issued')): break
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
        state.get('remove_from_decoded').append(_dec)
        _insn = {
            **_insn,
            **{'iid': state.get('iid')},
            **{'%pc': _pc},
            **{'_pc': int.from_bytes(_pc, 'little')},
            **({'function': next(filter(lambda x: int.from_bytes(_pc, 'little') >= x[0], sorted(state.get('objmap').items(), reverse=True)))[-1].get('name', '')} if state.get('objmap') else {}),
        }
        state.update({'iid': 1 + state.get('iid')})
        service.tx({'event': {
            'arrival': 2 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'alu': {
                'insn': _insn,
            },
        }})
        state.get('issued').append(_insn)
        toolbox.report_stats(service, state, 'histo', 'issued.insn', _insn.get('cmd'))
    service.tx({'info': 'state.remove_from_decoded       : {}'.format(state.get('remove_from_decoded'))})
    for _dec in state.get('remove_from_decoded'): state.get('decoded').remove(_dec)
    state.get('remove_from_decoded').clear()
def do_tick(service, state, results, events):
    logging.debug('do_tick(): results : {}'.format(results))
    state.get('forward').clear()
    for _fwd in map(lambda y: y.get('forward'), filter(lambda x: x.get('forward'), results)):
        state.get('forward').update({_fwd.get('rd'): _fwd.get('result')})
    service.tx({'info': 'forward                : {}'.format(state.get('forward'))})
    for _flush, _retire in map(lambda y: (y.get('flush'), y.get('retire')), filter(lambda x: x.get('flush') or x.get('retire'), results)):
        if _flush: service.tx({'info': 'flushing : {}'.format(_flush)})
        if _retire:
            service.tx({'info': 'retiring : {}'.format(_retire)})
            if 'next_pc' in _retire.keys() and _retire.get('taken'):
                state.get('decoded').clear()
                state.get('buffer').clear()
                _next_pc = _retire.get('next_pc')
                if len(state.get('issued')): _next_pc = (
                    _retire.get('next_pc')
                    if not any(map(lambda x: _retire.get('next_pc') == x.get('%pc'), state.get('issued')))
                    else riscv.constants.integer_to_list_of_bytes(state.get('issued')[-1].get('_pc') + state.get('issued')[-1].get('size'), 64, 'little')
                )
                state.update({'%pc': _next_pc})
                state.update({'%jp': _next_pc})
                state.update({'pending_fetch': {
                    'fetch': {
                        'cmd': 'get',
                        'addr': int.from_bytes(state.get('%jp'), 'little'),
                    }
                }})
                _service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': state.get('coreid'),
                    **state.get('pending_fetch'),
                }})
        _commit = (_flush if _flush else _retire)
        assert _commit.get('iid') == state.get('issued')[0].get('iid')
        state.get('issued').pop(0)
    for _dec in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
        if state.get('pending_fetch') and _dec.get('addr') != state.get('pending_fetch').get('fetch').get('addr'): continue
        service.tx({'info': '_dec : {}'.format(_dec)})
        state.get('buffer').extend(_dec.get('data'))
        state.update({'%jp': riscv.constants.integer_to_list_of_bytes(_dec.get('addr') + len(_dec.get('data')), 64, 'little')})
        state.update({'pending_fetch': {
            'fetch': {
                'cmd': 'get',
                'addr': int.from_bytes(state.get('%jp'), 'little'),
            }
        }})
        _service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            **state.get('pending_fetch'),
        }})
    if state.get('config').get('max_instructions_to_decode') > len(state.get('decoded')):
        _insns_to_pop_from_buffer = []
        logging.info('buffer : {} ({})'.format(state.get('buffer'), len(state.get('buffer'))))
        for _insn in riscv.decode.do_decode(state.get('buffer'), state.get('config').get('max_instructions_to_decode') - len(state.get('decoded'))):
            state.get('decoded').append({
                'insn': _insn,
                '%pc': state.get('%pc'),
            })
            toolbox.report_stats(service, state, 'histo', 'decoded.insn', _insn.get('cmd'))
            _insns_to_pop_from_buffer.append(_insn)
            state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_insn.get('size') + int.from_bytes(state.get('%pc'), 'little'), 64, 'little')})
            logging.info('_insns_to_pop_from_buffer : {} ({})'.format(_insns_to_pop_from_buffer, len(_insns_to_pop_from_buffer)))
        for _ in range(sum(map(lambda x: x.get('size'), _insns_to_pop_from_buffer))): state.get('buffer').pop(0)
    do_issue(service, state)
    service.tx({'info': 'state.issued           : {} ({})'.format(state.get('issued'), len(state.get('issued')))})
    service.tx({'info': 'state.buffer           : {} ({})'.format(state.get('buffer'), len(state.get('buffer')))})
    service.tx({'info': 'state.%pc              : {}'.format(state.get('%pc'))})
    service.tx({'info': 'state.%jp              : {}'.format(state.get('%jp'))})
    service.tx({'info': 'state.decoded          : {}'.format(state.get('decoded'))})

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
        'btb': None,
        'active': True,
        'running': False,
        '%pc': None,
        '%jp': None, # address of the first byte beyond the end of state.buffer
        'ack': True,
        'buffer': [],
        'decoded': [],
        'remove_from_decoded': [],
        'issued': [],
        'forward': {},
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
