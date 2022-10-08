# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import sys
import argparse
import logging

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
        _insn = _dec.get('insn')
        _pc = _dec.get('%pc')
        _hazards = sum(map(lambda x: hazard(x, _insn), state.get('issued')), [])
        service.tx({'info': '_hazards : {}'.format(_hazards)})
        if not all(map(lambda y: y in state.get('forward').keys(), _hazards)): break
        state.get('remove_from_decoded').append(_dec)
        if 'rs1' in _insn.keys():
            if _insn.get('rs1') in _hazards and _insn.get('rs1') in state.get('forward').keys():
                if not 'operands' in _insn.keys(): _insn.update({'operands': {}})
                _insn.get('operands').update({'rs1': state.get('forward').get(_insn.get('rs1'))})
                service.tx({'info': 'forward operand {}'.format(_insn.get('rs1'))})
            else:
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'register': {
                        'cmd': 'get',
                        'name': _insn.get('rs1'),
                    },
                }})
        if 'rs2' in _insn.keys():
            if _insn.get('rs2') in _hazards and _insn.get('rs2') in state.get('forward').keys():
                if not 'operands' in _insn.keys(): _insn.update({'operands': {}})
                _insn.get('operands').update({'rs2': state.get('forward').get(_insn.get('rs2'))})
                service.tx({'info': 'forward operand {}'.format(_insn.get('rs2'))})
            else:
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'register': {
                        'cmd': 'get',
                        'name': _insn.get('rs2'),
                    },
                }})
        _btb_entry = (state.get('btb').peek(int.from_bytes(_pc, 'little')) if state.get('btb') else None)
        _insn = {
            **_insn,
            **{'iid': state.get('iid')},
            **{'%pc': _pc},
            **({'speculative_next_pc': riscv.constants.integer_to_list_of_bytes(_btb_entry.next_pc, 64, 'little')} if _btb_entry else {}),
        }
        state.update({'iid': 1 + state.get('iid')})
        service.tx({'event': {
            'arrival': 2 + state.get('cycle'),
            'alu': {
                'insn': _insn,
            },
        }})
        state.get('issued').append(_insn)
        toolbox.report_stats(service, state, 'histo', 'issued.insn', _insn.get('cmd'))
        if _btb_entry:
            service.tx({'info': '_btb_entry : {}'.format(_btb_entry)})
            state.get('buffer').clear()
            state.get('buffer').extend(_btb_entry.data)
            state.get('next_%pc').clear()
            state.get('next_%pc').append(riscv.constants.integer_to_list_of_bytes(_btb_entry.next_pc + len(_btb_entry.data), 64, 'little'))
            state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_btb_entry.next_pc, 64, 'little')})
            state.update({'drop_until': state.get('next_%pc')[0]})
            break
    service.tx({'info': 'state.remove_from_decoded       : {}'.format(state.get('remove_from_decoded'))})
    for _dec in state.get('remove_from_decoded'): state.get('decoded').remove(_dec)
    state.get('remove_from_decoded').clear()
def do_tick(service, state, results, events):
    state.get('forward').clear()
    for _reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%pc' != _reg.get('name'): continue
        _pc = _reg.get('data')
        if 0 == int.from_bytes(_pc, 'little'):
            service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
            service.tx({'shutdown': None})
    for _fwd in map(lambda y: y.get('forward'), filter(lambda x: x.get('forward'), results)):
        state.get('forward').update({_fwd.get('rd'): _fwd.get('result')})
    for _flush, _retire in map(lambda y: (y.get('flush'), y.get('retire')), filter(lambda x: x.get('flush') or x.get('retire'), results)):
        if _flush: service.tx({'info': '_flush : {}'.format(_flush)})
        if _retire: service.tx({'info': '_retire : {}'.format(_retire)})
        _commit = (_flush if _flush else _retire)
        assert state.get('issued')[0].get('iid') == _commit.get('iid')
        state.get('issued').pop(0)
        if _retire and 'taken' in _retire.keys() and state.get('btb'):
            _pc = int.from_bytes(_retire.get('%pc'), 'little')
            _next_pc = int.from_bytes(_retire.get('next_pc'), 'little')
            if _retire.get('taken'):
                state.get('btb').poke(_pc, _next_pc)
                toolbox.report_stats(service, state, 'flat', 'btb_pokes')
                _btb_entry = state.get('btb').peek(_pc)
                _btb_entry.inc()
            else:
                _btb_entry = state.get('btb').peek(_pc)
                toolbox.report_stats(service, state, 'flat', 'btb_peeks')
                if not _btb_entry:
                    toolbox.report_stats(service, state, 'flat', 'btb_peek_misses')
                    continue
                _btb_entry.dec()
                if not _btb_entry.counter:
                    state.get('btb').evict(_pc) # if strongly not-taken, why keep it around?
                    toolbox.report_stats(service, state, 'flat', 'btb_strongly_not_taken')
        if _retire and _retire.get('next_pc'):
            if _retire.get('speculative_next_pc') == _retire.get('next_pc'): continue
            if len(state.get('issued')) and state.get('issued')[0].get('%pc') == _retire.get('next_pc'): continue
            if state.get('decode.request') and state.get('decode.request').get('addr') == _retire.get('next_pc'):
                state.get('buffer').clear()
                state.get('decoded').clear()
                state.update({'%pc': state.get('decode.request').get('addr')})
                continue
            if len(state.get('next_%pc')) and state.get('next_%pc') == _retire.get('next_pc'): continue
            if state.get('%pc') and state.get('%pc') == _retire.get('next_pc'): continue
            state.get('buffer').clear()
            state.get('decoded').clear()
            state.get('next_%pc').clear()
            state.get('next_%pc').append(_retire.get('next_pc'))
            state.update({'drop_until': state.get('next_%pc')[0]})
    for _dec in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
        _addr = int.from_bytes(_dec.get('addr'), 'little')
        if state.get('btb'): state.get('btb').update(_addr, _dec.get('data'))
        state.get('decode.request').update({'nbytes_received_so_far': state.get('decode.request').get('nbytes_received_so_far') + len(_dec.get('data'))})
        if state.get('decode.request').get('nbytes_received_so_far') == state.get('decode.request').get('nbytes_requested'):
            state.update({'decode.request': None})
        service.tx({'info': '_dec                  : {}'.format(_dec)})
        if state.get('drop_until'):
            if _dec.get('addr') != state.get('drop_until'): continue
            state.update({'drop_until': None})
            if not len(state.get('buffer')): state.update({'%pc': _dec.get('addr')})
        state.get('buffer').extend(_dec.get('data'))
    if len(state.get('next_%pc')) < 2: # NOTE: try to keep 2 next_%pc at a time
        _next_pc  = int.from_bytes(state.get('next_%pc')[-1], 'little')
        _next_pc += state.get('fetch_size')
        _next_pc  = riscv.constants.integer_to_list_of_bytes(_next_pc, 64, 'little')
        state.get('next_%pc').append(_next_pc)
    if not state.get('decode.request') and len(state.get('buffer')) < state.get('config').get('buffer_capacity') >> 1:
        state.update({'decode.request': {
            'addr': state.get('next_%pc').pop(0),
            'nbytes_requested': state.get('fetch_size'),
            'nbytes_received_so_far': 0,
        }})
        _service.tx({'event': {
            **{'arrival': 1 + state.get('cycle')},
            **{'decode.request': {k:v for k, v in state.get('decode.request').items() if 'nbytes_received_so_far' != k}},
        }})
    if state.get('max_instructions_to_decode') > len(state.get('decoded')):
        for _insn in riscv.decode.do_decode(state.get('buffer'), state.get('max_instructions_to_decode') - len(state.get('decoded'))):
            state.get('decoded').append({
                'insn': _insn,
                '%pc': state.get('%pc'),
            })
            toolbox.report_stats(service, state, 'histo', 'decoded.insn', _insn.get('cmd'))
            for _ in range(_insn.get('size')): state.get('buffer').pop(0)
            state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_insn.get('size') + int.from_bytes(state.get('%pc'), 'little'), 64, 'little')})
    do_issue(service, state)
    service.tx({'info': 'state.issued           : {}'.format(state.get('issued'))})
    service.tx({'info': 'state.buffer           : {} ({})'.format(state.get('buffer'), len(state.get('buffer')))})
    service.tx({'info': 'state.%pc              : {}'.format(state.get('%pc'))})
    service.tx({'info': 'state.next_%pc         : {}'.format(state.get('next_%pc'))})
    service.tx({'info': 'state.decoded          : {}'.format(state.get('decoded'))})
    service.tx({'info': 'state.decode.request   : {}'.format(state.get('decode.request'))})
    service.tx({'info': 'state.drop_until       : {}'.format(state.get('drop_until'))})
    service.tx({'info': 'forward                : {}'.format(state.get('forward'))})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Instruction Decode')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    logging.basicConfig(
        filename=os.path.join(args.log, '{}.log'.format(os.path.basename(__file__))),
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
        'btb': None,
        'active': True,
        'running': False,
        '%pc': None,
        'next_%pc': [],
        'ack': True,
        'buffer': [],
        'decode.request': None,
        'drop_until': None,
        'decoded': [],
        'remove_from_decoded': [],
        'fetch_size': 4, # HACK: hard-coded number of bytes to fetch
        'issued': [],
        'forward': {},
        'iid': 0,
        'max_instructions_to_decode': 1, # HACK: hard-coded max-instructions-to-decode of 1
        'config': {
            'buffer_capacity': 16,
            'btb_nentries': 32,
            'btb_nbytesperentry': 16,
            'btb_evictionpolicy': 'lru',
        },
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                if state.get('config').get('btb_nentries'): state.update({'btb': components.simplebtb.SimpleBTB(
                    state.get('config').get('btb_nentries'),
                    state.get('config').get('btb_nbytesperentry'),
                    state.get('config').get('btb_evictionpolicy'),
                )})
                state.update({'decode.request': {
                    'addr': state.get('%pc'),
                    'nbytes_requested': state.get('fetch_size'),
                    'nbytes_received_so_far': 0,
                }})
                _next_pc  = int.from_bytes(state.get('decode.request').get('addr'), 'little')
                _next_pc += state.get('decode.request').get('nbytes_requested')
                _next_pc  = riscv.constants.integer_to_list_of_bytes(_next_pc, 64, 'little')
                state.get('next_%pc').append(_next_pc)
                _service.tx({'event': {
                    **{'arrival': 2 + state.get('cycle')},
                    **{'decode.request': {k:v for k, v in state.get('decode.request').items() if 'nbytes_received_so_far' != k}},
                }})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if state.get('service') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = v.get('results')
                _events = v.get('events')
                do_tick(_service, state, _results, _events)
            elif 'register' == k:
                if not '%pc' == v.get('name'): continue
                if not 'set' == v.get('cmd'): continue
                _pc = v.get('data')
                state.update({'%pc': _pc})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
