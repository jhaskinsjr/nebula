import sys
import argparse

import service

def do_decode(state, max_insns):
    _retval = []
    while max_insns > len(_retval) and len(state.get('buffer')):
        _word = int.from_bytes(state.get('buffer')[:4], 'little')
        if 0x3 == _word & 0x3:
            if 4 > len(state.get('buffer')): break
            _retval.append(_word)
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
        else:
            _retval.append(_word & 0xffff)
            state.get('buffer').pop(0)
            state.get('buffer').pop(0)
    return _retval

def do_tick(service, state, cycle, results, events):
    for ev in filter(lambda x: x, map(lambda y: y.get('decode'), events)):
        _bytes = ev.get('bytes')
        state.get('buffer').extend(_bytes)
        service.tx({'result': {
            'arrival': 1 + cycle,
            'insns': {
                'data': do_decode(state, 1), # HACK: hard-coded max-instructions-to-decode of 1
            },
        }})
    return cycle

def setregister(registers, reg, val):
    return {x: y for x, y in tuple(registers.items()) + ((reg, val),)}
def getregister(registers, reg):
    return registers.get(reg, None)

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
        'ack': True,
        'buffer': [],
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
                _cycle = v.get('cycle')
                _results = v.get('results')
                _events = v.get('events')
                state.update({'cycle': do_tick(_service, state, _cycle, _results, _events)})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))