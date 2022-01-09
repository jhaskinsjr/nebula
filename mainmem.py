import sys
import argparse

import service

import os
import struct

def do_tick(service, state, cycle, results, events):
    [rs for rs in results]
    [ev for ev in events]
    for ev in filter(lambda x: x, map(lambda y: y.get('mem'), events)):
#        service.tx({'info': ev})
        _cmd = ev.get('cmd')
        _addr = ev.get('addr')
        _size = ev.get('size')
        _data = ev.get('data')
        if 'poke' == _cmd:
            poke(state, _addr, _size, _data)
        elif 'peek' == _cmd:
            service.tx({
                'result': {
                    'mem': {
                        'addr': _addr,
                        'size': _size,
                        'data': peek(state, _addr, _size),
                    }
                }
            })
        else:
            print('ev : {}'.format(ev))
            assert False
    return cycle

def poke(state, addr, data):
    _fd = state.get('fd')
    _size = len(data)
    os.lseek(_fd, addr, os.SEEK_SET)
    os.write(_fd, struct.pack('B' * _size, *(os.read(_fd, _size))), _size)
def peek(state, addr, size):
    _fd = state.get('fd')
    os.lseek(_fd, addr, os.SEEK_SET)
    _data = struct.unpack('B' * size, os.read(_fd, size))
    return _data
#    return 23456789

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