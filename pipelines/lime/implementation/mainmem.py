import os
import sys
import argparse
import logging

import service
import toolbox

def do_tick(service, state, results, events):
    for ev in filter(lambda x: x, map(lambda y: y.get('mem'), events)):
        _cmd = ev.get('cmd')
        _addr = ev.get('addr')
        _size = ev.get('size')
        _data = ev.get('data')
        if 'poke' == _cmd:
            poke(state, _addr, _size, _data)
            toolbox.report_stats(service, state, 'histo', 'poke.size', _size)
        elif 'peek' == _cmd:
            service.tx({'result': {
                'arrival': state.get('config').get('peek_latency_in_cycles') + state.get('cycle'),
                'mem': {
                    'addr': _addr,
                    'size': _size,
                    'data': peek(state, _addr, _size),
                }
            }})
            toolbox.report_stats(service, state, 'histo', 'peek.size', _size)
        else:
            logging.fatal('ev : {}'.format(ev))
            assert False

def poke(state, addr, size, data):
    # data : list of unsigned char, e.g., to make an integer, X, into a list
    # of N little-endian-formatted bytes -> list(X.to_bytes(N, 'little'))
    _fd = state.get('fd')
    os.lseek(_fd, addr, os.SEEK_SET)
    os.write(_fd, bytes(data))
#    os.write(_fd, data.to_bytes(size, 'little'))
def peek(state, addr, size):
    # return : list of unsigned char, e.g., to make an 8-byte quadword from
    # a list, X, of N bytes -> int.from_bytes(X, 'little')
    _fd = state.get('fd')
    os.lseek(_fd, addr, os.SEEK_SET)
    return list(os.read(_fd, size))

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Main Memory')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--quiet', '-Q', dest='quiet', action='store_true', help='suppress status messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    logging.basicConfig(
        filename=os.path.join(args.log, '{}.log'.format(os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    if not args.quiet: print('Starting {}...'.format(sys.argv[0]))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = {
        'service': 'mainmem',
        'cycle': 0,
        'active': True,
        'running': False,
        'ack': True,
        'fd': None,
        'config': {
            'main_memory_filename': '/tmp/mainmem.raw',
            'main_memory_capacity': 2**32,
            'peek_latency_in_cycles': 500,
        },
    }
    _service = service.Service(state.get('service_name'), _launcher.get('host'), _launcher.get('port'))
#    state.update({'fd': os.open(state.get('config').get('main_memory_filename'), os.O_RDWR|os.O_CREAT)})
#    os.ftruncate(state.get('fd'), state.get('config').get('main_memory_capacity'))
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
                state.update({'fd': os.open(state.get('config').get('main_memory_filename'), os.O_RDWR|os.O_CREAT)})
                os.ftruncate(state.get('fd'), state.get('config').get('main_memory_capacity'))
                state.update({'running': True})
                state.update({'ack': False})
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
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    if not args.quiet: print('Shutting down {}...'.format(sys.argv[0]))
    os.close(state.get('fd'))