import sys
import argparse

import service
import riscv.decode

JUMPS = ['JALR', 'JAL'] # needs to be incorporated into riscv module
BRANCHES = [] # needs to ben incorporated into riscv module

def do_tick(service, state, results, events):
    for completed in filter(lambda x: x, map(lambda y: y.get('complete'), events)):
        service.tx({'info': 'completed : {}'.format(completed)})
        _insns = completed.get('insns')
        _jumps = any(map(lambda a: a.get('cmd') in JUMPS, _insns))
        _branches = any(map(lambda a: a.get('cmd') in BRANCHES, _insns))
        service.tx({'info': '_jumps    : {}'.format(_jumps)})
        service.tx({'info': '_branches : {}'.format(_branches)})
        if _jumps or _branches: state.get('buffer').clear()
    for ev in filter(lambda x: x, map(lambda y: y.get('decode'), events)):
        _bytes = ev.get('bytes')
        state.get('buffer').extend(_bytes)
        _decoded = riscv.decode.do_decode(state.get('buffer'), 1) # HACK: hard-coded max-instructions-to-decode of 1
        for _size, _ in _decoded:
            for x in range(_size): state.get('buffer').pop(0)
        _decoded = [y for _, y in map(lambda x: x, _decoded)]
        service.tx({'result': {
            'arrival': 1 + state.get('cycle'),
            'insns': {
                'data': _decoded,
            },
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
                state.update({'cycle': v.get('cycle')})
                _results = v.get('results')
                _events = v.get('events')
                do_tick(_service, state, _results, _events)
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))