import sys
import argparse

import service

def setregister(registers, reg, val):
    return {x: y for x, y in tuple(registers.items()) + ((reg, val),)}
def getregister(registers, reg):
    return registers.get(reg, None)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Register File')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    parser.add_argument('port', type=int, help='port to connect to on host')
    args = parser.parse_args()
    if args.debug: print('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    if args.debug: print('_launcher : {}'.format(_launcher))
    _service = service.Service('regfile', _launcher.get('host'), _launcher.get('port'))
    _cycle = 0
    _active = True
    _registers = {x: 0 for x in ['%pc', '%sp']}
    while _active:
        msg = _service.rx()
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                _active = False
            elif 'cycle' == k:
                _cycle = msg.get('cycle')
#                _service.tx({'cycle': _cycle})
            elif 'register' == k:
                _cmd = v.get('cmd')
                _name = v.get('name')
                if 'set' == _cmd:
                    _registers = setregister(_registers, _name, v.get('data'))
                elif 'get' == _cmd:
                    _ret = getregister(_registers, _name)
                    _service.tx({'result': {'register': _ret}})
        _service.tx({'ack': {'cycle': _cycle}})
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))