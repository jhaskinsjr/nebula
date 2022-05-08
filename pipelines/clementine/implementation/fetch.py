import sys
import argparse

import service
import riscv.constants


def do_tick(service, state, results, events):
    for _reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%pc' != _reg.get('name'): continue
        _pc = _reg.get('data')
        if 0 == int.from_bytes(_pc, 'little'):
            service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
            service.tx({'shutdown': None})
        state.update({'%jp': _pc})
    for _decode_buffer_available in map(lambda y: y.get('decode.buffer_available'), filter(lambda x: x.get('decode.buffer_available'), results)):
        state.update({'decode.buffer_available': _decode_buffer_available})
    service.tx({'info': 'decode.buffer_available : {}'.format(state.get('decode.buffer_available'))})
    service.tx({'info': 'fetch_size              : {}'.format(state.get('fetch_size'))})
    if state.get('decode.buffer_available') <= state.get('fetch_size'): return
    if state.get('stall_until') > state.get('cycle'): return
    if not state.get('%jp'): return
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'mem': {
            'cmd': 'peek',
            'addr': int.from_bytes(state.get('%jp'), 'little'),
            'size': state.get('fetch_size'),
        },
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'decode': {
            'addr': int.from_bytes(state.get('%jp'), 'little'),
            'size': state.get('fetch_size'),
        },
    }})
    state.update({'%jp': riscv.constants.integer_to_list_of_bytes(4 + int.from_bytes(state.get('%jp'), 'little'), 64, 'little')})
    

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Simple Core')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    _service = service.Service('fetch', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'stall_until': 0,
        'active': True,
        'running': False,
        'decode.buffer_available': 4,
        'fetch_size': 4, # HACK: hard-coded number of bytes to fetch
        '%jp': None, # This is the fetch pointer. Why %jp? Who knows?
        'ack': True,
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
                state.update({'%jp': _pc})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))