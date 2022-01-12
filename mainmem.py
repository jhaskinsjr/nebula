import sys
import argparse

import service

import os

def do_tick(service, state, cycle, results, events):
    for ev in filter(lambda x: x, map(lambda y: y.get('mem'), events)):
#        service.tx({'info': ev})
        _cmd = ev.get('cmd')
        _addr = ev.get('addr')
        _size = ev.get('size')
        _data = ev.get('data')
        if 'poke' == _cmd:
            poke(state, _addr, _size, _data)
        elif 'peek' == _cmd:
            service.tx({'result': {
                'arrival': 5 + cycle,
                'mem': {
                    'addr': _addr,
                    'size': _size,
                    'data': peek(state, _addr, _size),
                }
            }})
        else:
            print('ev : {}'.format(ev))
            assert False
    return cycle

def poke(state, addr, data):
    # data : list of unsigned char, e.g., to make an integer, X, into a list
    # of N little-endian-formatted bytes -> list(X.to_bytes(N, 'little'))
    _fd = state.get('fd')
    os.lseek(_fd, addr, os.SEEK_SET)
    os.write(_fd, bytes(data))
def peek(state, addr, size):
    # return : list of unsigned char, e.g., to make an 8-byte quadword from
    # a list, X, of N bytes -> int.from_bytes(X, 'little')
    _fd = state.get('fd')
    os.lseek(_fd, addr, os.SEEK_SET)
    return list(os.read(_fd, size))

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Main Memory')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    _service = service.Service('mainmem', _launcher.get('host'), _launcher.get('port'))
    state = {
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'fd': os.open('/tmp/mainmem.raw', os.O_RDWR|os.O_CREAT)
    }
    os.ftruncate(state.get('fd'), 2**32) # HACK: hard-wired memory is dumb, but I don't want to focus on that right now
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
    os.close(state.get('fd'))