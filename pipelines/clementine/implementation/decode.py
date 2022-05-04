import sys
import argparse

import service
import riscv.constants
import riscv.decode

def remaining_buffer_availability():
    return state.get('buffer_capacity') - sum(map(lambda x: x.get('size'), state.get('pending_fetch')))
def do_tick(service, state, results, events):
    for _reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%pc' != _reg.get('name'): continue
        _pc = _reg.get('data')
        service.tx({'info': '_pc           : {}'.format(_pc)})
        service.tx({'info': 'state.get(pc) : {}'.format(state.get('%pc'))})
        if _pc != state.get('%pc'):
            state.get('buffer').clear()
        state.update({'%pc': _pc})
    for _dec in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
        state.get('pending_fetch').append(_dec)
    for _mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
        _data = _mem.pop('data')
        if _mem not in state.get('pending_fetch'): continue
        state.get('pending_fetch').remove(_mem)
        state.get('buffer').extend(_data)
        service.tx({'info': 'buffer : {}'.format(list(map(lambda x: hex(x), state.get('buffer'))))})
        _decoded = riscv.decode.do_decode(state.get('buffer'), state.get('max_instructions_to_decode')) 
        service.tx({'info': '_decoded : {}'.format(_decoded)})
        for _insn in _decoded:
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
                    'insn': {
                        **_insn,
                        **{'iid': state.get('iid')},
                        **{'%pc': state.get('%pc')},
                    },
                },
            }})
            state.update({'iid': 1 + state.get('iid')})
        _bytes_decoded = sum(map(lambda x: x.get('size'), _decoded))
        state.update({'%pc': riscv.constants.integer_to_list_of_bytes(_bytes_decoded + int.from_bytes(state.get('%pc'), 'little'), 64, 'little')})
        for _ in range(_bytes_decoded): state.get('buffer').pop(0)
    service.tx({'result': {
        'arrival': 1 + state.get('cycle'),
        'decode.buffer_available': remaining_buffer_availability(),
    }})

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
    _service = service.Service('decode', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        '%pc': None,
        'ack': True,
        'buffer': [],
        'buffer_capacity': 16, # HACK: it's dumb to hard code the buffer length, but can't be bothered with that now
        'pending_fetch': [],
        'iid': 0,
        'max_instructions_to_decode': 1, # HACK: hard-coded max-instructions-to-decode of 1
    }
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