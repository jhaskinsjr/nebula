import os
import time
import socket
import json
import argparse
import threading
import subprocess

def tx(conns, msg):
    _message = {
        str: lambda : json.dumps({'text': msg}),
        dict: lambda : json.dumps(msg),
    }.get(type(msg), lambda : json.dumps({'error': 'Undeliverable object'}))().encode('ascii')
    assert 1024 >= len(_message), 'Message too big!'
    _message += (' ' * (1024 - len(_message))).encode('ascii')
    for c in conns: c.send(_message)
def handler(conn, addr):
    global state
    state.get('lock').acquire()
    state.get('connections').add(conn)
    state.get('lock').release()
    print('handler(): {}:{}'.format(*addr))
    tx([conn], {'ack': 'launcher'})
    while True:
        try:
            msg = conn.recv(1024)
            if not len(msg):
                time.sleep(1)
                continue
            msg = json.loads(msg.decode('ascii'))
#            print('{}: {}'.format(threading.current_thread().name, msg))
            k, v = (next(iter(msg.items())) if isinstance(msg, dict) else (None, None))
            if {k: v} == {'text': 'bye'}:
                conn.close()
                state.get('lock').acquire()
                state.get('connections').remove(conn)
                state.get('lock').release()
                break
            elif 'name' == k:
                threading.current_thread().name = v
            elif 'info' == k:
                print('{}.handler(): info : {}'.format(threading.current_thread().name, v))
            elif 'ack' == k:
                state.get('lock').acquire()
                state.get('ack').append((threading.current_thread().name, msg))
#                print('{}.handler(): ack: {} ({})'.format(threading.current_thread().name, state.get('ack'), len(state.get('ack'))))
                state.get('lock').release()
            elif 'result' == k:
                _arr = v.pop('arrival')
                _res = v
                state.get('lock').acquire()
                _res_evt = state.get('futures').get(_arr, {'results': [], 'events': []})
                _res_evt.get('results').append(_res)
                state.get('futures').update({_arr: _res_evt})
                state.get('lock').release()
            elif 'event' == k:
                _arr = v.pop('arrival')
                _evt = v
                state.get('lock').acquire()
                _res_evt = state.get('futures').get(_arr, {'results': [], 'events': []})
                _res_evt.get('events').append(_evt)
                state.get('futures').update({_arr: _res_evt})
                state.get('lock').release()
            else:
                state.get('lock').acquire()
                _running = state.get('running')
                state.get('lock').release()
#                print('{}.handler(): _running : {} ({})'.format(threading.current_thread().name, _running, msg))
                if _running:
                    state.get('lock').acquire()
                    state.get('events').append(msg)
                    state.get('lock').release()
                else:
                    state.get('lock').acquire()
                    tx(filter(lambda c: c != conn, state.get('connections')), msg)
                    state.get('lock').release()
        except Exception as ex:
            print('Oopsie! {} ({} ({}:{}))'.format(ex, str(msg), type(msg), len(msg)))
            conn.close()
def acceptor():
    while True:
        _conn, _addr = _s.accept()
        th = threading.Thread(target=handler, args=(_conn, _addr))
        th.start()
def integer(val):
    return {
        '0x': lambda x: int(x, 16),
        '0o': lambda x: int(x, 8),
        '0b': lambda x: int(x, 2),
    }.get(val[:2], lambda x: int(x))(val)
def register(connections, cmd, name, data=None):
    tx(connections, {'register': {**{
            'cmd': cmd,
            'name': name,
        },
        **({'data': integer(data)} if data else {}),
    }})
def mainmem(connections, cmd, addr, size, data=None):
    tx(connections, {'mainmem': {**{
            'cmd': cmd,
            'addr': integer(addr),
            'size': integer(size),
        },
        **({'data': integer(data)} if data else {}),
    }})
def loadbin(binary, addr):
    print('loadbin(): {} @{}'.format(binary, addr))
def push(val):
    print('push(): @(%sp) <= {}'.format(val))
def run(connections, cycle, max_cycles):
    global state
    # {
    #   'tick': {
    #       'cycle': XXX,
    #       'results': [],
    #       'events': [],
    #   }
    # }
    state.get('lock').acquire()
    tx(state.get('connections'), 'run')
    state.get('lock').release()
    while (cycle < max_cycles if max_cycles else True):
        state.get('lock').acquire()
        print('run(): @{:8} futures  : {}'.format(cycle, state.get('futures')))
        cycle = (min(state.get('futures').keys()) if len(state.get('futures').keys()) else 1 + cycle)
        tx(state.get('connections'), {'tick': {
            **{'cycle': cycle},
            **dict(state.get('futures').get(cycle, {'results': [], 'events': []})),
        }})
        if cycle in state.get('futures'): state.get('futures').pop(cycle)
        state.get('ack').clear()
        state.get('lock').release()
        _ack = False
        while not _ack:
            state.get('lock').acquire()
            _ack = len(state.get('ack')) == len(state.get('connections'))
            state.get('lock').release()
    return cycle

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='μService-SIMulator')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--services', dest='services', nargs='+', help='code:host')
    parser.add_argument('--max_cycles', type=int, dest='max_cycles', default=None, help='maximum number of cycles to run for')
    parser.add_argument('port', type=int, help='port to connect to on host')
    parser.add_argument('script', type=str, help='script to be executed by μService-SIMulator')
    args = parser.parse_args()
    assert os.path.exists(args.script), 'Cannot open script file, {}!'.format(args.script)
    if args.debug: print('args : {}'.format(args))
    _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _s.bind(('0.0.0.0', args.port))
    _s.listen(5)
    state = {
        'lock': threading.Lock(),
        'connections': set(),
        'ack': [],
        'futures': {},
        'running': False,
        'cycle': 0,
    }
    threading.Thread(target=acceptor, daemon=True).start()
    _services = [
        threading.Thread(
            target=subprocess.run,
            args=(['ssh', h, 'python3 {} {} {}'.format(c, ('-D' if args.debug else ''), '{}:{}'.format(socket.gethostname(), args.port))],),
            daemon=True,
        ) for c, h in map(lambda x: x.split(':'), args.services)
    ]
    [th.start() for th in _services]
    while len(_services) > len(state.get('connections')): time.sleep(1)
    with open(args.script) as fp:
        for raw in map(lambda x: x.strip(), fp.readlines()):
            raw = (raw[:raw.index('#')] if '#' in raw else raw)
            if '' == raw: continue
            cmd, params = ((raw.split()[0], raw.split()[1:]) if 1 < len(raw.split()) else (raw, []))
            if 'shutdown' == cmd:
                break
            elif 'tick' == cmd:
                state.update({'cycle': state.get('cycle') + sum(map(lambda x: integer(x), params))})
                tx(state.get('connections'), {
                    'tick': {
                        'cycle': state.get('cycle'),
                        'results': [],
                        'events': [],
                    }
                })
            elif 'run' == cmd:
                state.update({'running': True})
                state.update({'cycle': run(state.get('connections'), state.get('cycle'), args.max_cycles)})
                state.update({'running': False})
            else:
                {
                    'register': lambda x, y, z=None: register(state.get('connections'), x, y, z),
                    'mainmem': lambda w, x, y, z=None: mainmem(state.get('connections'), w, x, y, z),
                    'loadbin': lambda x, y: loadbin(x, y),
                    'run': lambda x: run(x),
                    'cycle': lambda: print(state.get('cycle')),
                    'state': lambda: print(state),
                    'connections': lambda: print(state.get('connections')),
                    'push': lambda x: push(x),
                }.get(cmd, lambda : print('Unknown command!'))(*params)
    tx(state.get('connections'), 'bye')
    [th.join() for th in _services]