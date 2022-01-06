import sys
import argparse

import service

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Main Memory')
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
    _service = service.Service('mainmem', _launcher.get('host'), _launcher.get('port'))
#    _service.tx('bye')
    while True:
        msg = _service.rx()
        print(msg)
        if {'text': 'bye'} == msg: break
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))