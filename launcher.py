import os
import time
import socket
import json
import argparse
import threading
import subprocess

def tx(conn, msg):
    _message = {
        str: lambda : json.dumps({'text': msg}),
        dict: lambda : json.dumps(msg),
    }.get(type(msg), lambda : json.dumps({'error': 'Undeliverable object'}))().encode('ascii')
    assert 1024 >= len(_message), 'Message too big!'
    _message += (' ' * (1024 - len(_message))).encode('ascii')
    conn.send(_message)
def broadcast(connections, msg):
    return [tx(c, msg) for c in connections]
def handler(connections, conn, addr):
    global state
    state.get('lock').acquire()
    state.get('connections').add(conn)
    state.get('lock').release()
    connections.add(conn)
#    print('handler for {}:{}'.format(*addr))
#    print('len(connections) : {}'.format(len(connections)))
#    conn.setblocking(True)
    tx(conn, {'ack': 'launcher'})
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
                connections.remove(conn)
                break
            elif 'name' == k:
                threading.current_thread().name = v
            elif 'info' == k:
                print('{}.handler(): info : {}'.format(threading.current_thread().name, v))
            elif 'ack' == k:
                state.get('lock').acquire()
                state.get('ack').append((threading.current_thread().name, msg))
                print('{}.handler(): ack: {} ({})'.format(threading.current_thread().name, state.get('ack'), len(state.get('ack'))))
                state.get('lock').release()
            elif 'result' == k:
                state.get('lock').acquire()
                state.get('results').append(v) # e.g., v = {'pc': 0x40000000}
                state.get('lock').release()
            else:
                state.get('lock').acquire()
                _running = state.get('running')
                state.get('lock').release()
                print('{}.handler(): _running : {} ({})'.format(threading.current_thread().name, _running, msg))
                if _running:
                    state.get('lock').acquire()
                    state.get('events').append((filter(lambda c: c != conn, state.get('connections')), msg))
                    state.get('lock').release()
                else:
                    state.get('lock').acquire()
                    broadcast(filter(lambda c: c != conn, state.get('connections')), msg)
                    state.get('lock').release()
        except Exception as ex:
            print('Oopsie! {} ({} ({}:{}))'.format(ex, str(msg), type(msg), len(msg)))
            connections.remove(conn)
            conn.close()
def acceptor(connections):
    while True:
        _conn, _addr = _s.accept()
        th = threading.Thread(target=handler, args=(connections, _conn, _addr))
        th.start()
def integer(val):
    return {
        '0x': lambda x: int(x, 16),
        '0o': lambda x: int(x, 8),
        '0b': lambda x: int(x, 2),
    }.get(val[:2], lambda x: int(x))(val)
def register(connections, cmd, name, data=None):
    broadcast(connections, {'register': {**{
            'cmd': cmd,
            'name': name,
        },
        **({'data': integer(data)} if data else {}),
    }})
def mainmem(connections, cmd, addr, size, data=None):
    broadcast(connections, {'mainmem': {**{
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
    broadcast(state.get('connections'), 'run')
    state.get('lock').release()
    while (cycle < max_cycles if max_cycles else True):
        state.get('lock').acquire()
        broadcast(state.get('connections'), {
            'tick': {
                'cycle': cycle,
                'results': state.get('results').copy(),
                'events': state.get('events').copy(),
            }
        })
        state.get('lock').release()
        _ack = False
        while not _ack:
            state.get('lock').acquire()
            print('run(): ack     : {} ({})'.format(state.get('ack'), len(state.get('ack'))))
            _ack = len(state.get('ack')) == len(state.get('connections'))
            state.get('lock').release()
#            time.sleep(10)
        state.get('lock').acquire()
        print('run(): results : {} ({})'.format(state.get('results'), len(state.get('results'))))
        print('run(): events  : {} ({})'.format(state.get('events'), len(state.get('events'))))
        state.get('ack').clear()
        state.get('results').clear()
        state.get('events').clear()
        state.get('lock').release()
        cycle_inc = 1
        cycle += cycle_inc
#        time.sleep(1)
    return cycle

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='μService-SIMulator')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--services', dest='services', nargs='+', help='service:code:host:port')
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
        'results': [],
        'events': [],
        'running': False,
        'cycle': 0,
    }
    connections = set()
    threading.Thread(target=acceptor, args=(connections,), daemon=True).start()
    _services = [
        threading.Thread(
            target=subprocess.run,
            args=(['ssh', h, 'python3 {} {} {} {}'.format(c, ('-D' if args.debug else ''), '{}:{}'.format(socket.gethostname(), args.port), p)],),
            daemon=True,
        ) for _, c, h, p in map(lambda x: x.split(':'), args.services)
    ]
    [th.start() for th in _services]
#    while len(_services) > len(connections): time.sleep(1)
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
                broadcast(connections, {
                    'tick': {
                        'cycle': state.get('cycle'),
                        'results': [],
                        'events': [],
                    }
                })
            elif 'run' == cmd:
                state.update({'running': True})
                state.update({'cycle': run(connections, state.get('cycle'), args.max_cycles)})
                state.update({'running': False})
            else:
                {
                    'register': lambda x, y, z=None: register(connections, x, y, z),
                    'mainmem': lambda w, x, y, z=None: mainmem(connections, w, x, y, z),
                    'loadbin': lambda x, y: loadbin(x, y),
                    'run': lambda x: run(x),
                    'cycle': lambda: print(state.get('cycle')),
                    'state': lambda: print(state),
                    'connections': lambda: print(connections),
                    'push': lambda x: push(x),
                }.get(cmd, lambda : print('Unknown command!'))(*params)
    broadcast(connections, 'bye')
    [th.join() for th in _services]
#    [th.join() for th in filter(lambda x: x != threading.main_thread(), threading.enumerate())]