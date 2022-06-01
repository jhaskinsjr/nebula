import sys
import argparse

import service
import riscv.constants
import riscv.decode

def remaining_buffer_availability():
    return state.get('config').get('buffer_capacity') - sum(map(lambda x: x.get('size'), state.get('pending_fetch')))
def hazard(p, c):
    return 'rd' in p.keys() and (('rs1' in c.keys() and p.get('rd') == c.get('rs1')) or ('rs2' in c.keys() and p.get('rd') == c.get('rs2')))
def do_tick(service, state, results, events):
    for _reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%pc' != _reg.get('name'): continue
        _pc = _reg.get('data')
        service.tx({'info': '_pc           : {}'.format(_pc)})
        service.tx({'info': 'state.get(pc) : {}'.format(state.get('%pc'))})
        if _pc != state.get('%pc'):
            state.get('pending_fetch').clear()
            state.get('buffer').clear()
            state.get('decoded').clear()
            state.update({'%pc': _pc})
            state.update({'last_flushed': state.get('cycle')})
    for _mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
        _data = _mem.pop('data')
        if _mem not in state.get('pending_fetch'): continue
        state.get('pending_fetch').remove(_mem)
        state.get('buffer').extend(_data)
        service.tx({'info': 'buffer : {}'.format(list(map(lambda x: hex(x), state.get('buffer'))))})
    for _flush in map(lambda y: y.get('flush'), filter(lambda x: x.get('flush'), results)):
        service.tx({'info': '_flush : {}'.format(_flush)})
        assert state.get('issued')[0].get('iid') == _flush.get('iid')
        state.get('issued').pop(0)
    for _retire in map(lambda y: y.get('retire'), filter(lambda x: x.get('retire'), results)):
        service.tx({'info': '_retire : {}'.format(_retire)})
        assert state.get('issued')[0].get('iid') == _retire.get('iid')
        state.get('issued').pop(0)
    for _dec in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
        if state.get('last_flushed') == state.get('cycle') and _dec.get('addr') != int.from_bytes(state.get('%pc'), 'little'): continue
        state.get('pending_fetch').append(_dec)
    service.tx({'info': 'max - len(decoded)  : {}'.format(state.get('max_instructions_to_decode') - len(state.get('decoded')))})
    for _insn in riscv.decode.do_decode(state.get('buffer'), state.get('max_instructions_to_decode') - len(state.get('decoded'))):
        state.get('decoded').append({
            **_insn,
            **{'iid': state.get('iid')},
            **{'%pc': state.get('%pc')},
        })
        state.update({'iid': 1 + state.get('iid')})
        state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_insn.get('size') + int.from_bytes(state.get('%pc'), 'little'), 64, 'little')})
    service.tx({'result': {
        'arrival': 1 + state.get('cycle'),
        'decode.buffer_available': remaining_buffer_availability(),
    }})
    service.tx({'info': 'state.decoded       : {}'.format(state.get('decoded'))})
    if not len(state.get('decoded')): return
    for _insn in state.get('decoded'):
        if any(map(lambda x: hazard(x, _insn), state.get('issued'))): break
        if _insn.get('rs1'): service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': _insn.get('rs1'),
            }
        }})
        if _insn.get('rs2'): service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'register': {
                'cmd': 'get',
                'name': _insn.get('rs2'),
            }
        }})
        service.tx({'event': {
            'arrival': 2 + state.get('cycle'),
            'alu': {
                'insn': _insn,
            },
        }})
        state.get('issued').append(_insn)
        for _ in range(_insn.get('size')): state.get('buffer').pop(0)
    service.tx({'info': 'state.decoded       : {}'.format(state.get('decoded'))})
    service.tx({'info': 'state.issued        : {}'.format(state.get('issued'))})
    for _insn in filter(lambda x: x in state.get('decoded'), state.get('issued')):
        state.get('decoded').remove(_insn)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Instruction Decode')
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
        'service': 'decode',
        'cycle': 0,
        'active': True,
        'running': False,
        '%pc': None,
        'ack': True,
        'buffer': [],
        'pending_fetch': [],
        'decoded': [],
        'issued': [],
        'last_flushed': None,
        'iid': 0,
        'max_instructions_to_decode': 1, # HACK: hard-coded max-instructions-to-decode of 1
        'config': {
            'buffer_capacity': 16,
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
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))