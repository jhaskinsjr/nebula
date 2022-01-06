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
    connections.add(conn)
    print('handler for {}:{}'.format(*addr))
    print('len(connections) : {}'.format(len(connections)))
    conn.setblocking(True)
    tx(conn, {'ack': 'launcher'})
    while True:
        try:
            msg = conn.recv(1024)
            if not len(msg):
                time.sleep(1)
                continue
            msg = json.loads(msg.decode('ascii'))
            print('{}: {}'.format(threading.current_thread().name, msg))
            k, v = (next(iter(msg.items())) if isinstance(msg, dict) else (None, None))
            if {k: v} == {'text': 'bye'}:
                conn.close()
                connections.remove(conn)
                break
            elif 'name' == k:
                threading.current_thread().name = v
#            else:
#                broadcast(set(filter(lambda c: c != conn, connections)), msg)
        except Exception as e:
            print('Oopsie! {} ({} ({}:{}))'.format(e, str(msg), type(msg), len(msg)))
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
def tick(connections, increment):
    broadcast(connections, {'tick': increment})
def run(connections, cycle, max_cycles):
    while (cycle < max_cycles if max_cycles else True):
        cycle_inc = 1
        tick(connections, cycle_inc)
        cycle += cycle_inc
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
    _cycle = 0
    while len(_services) > len(connections): time.sleep(1)
    with open(args.script) as fp:
        for raw in map(lambda x: x.strip(), fp.readlines()):
            raw = (raw[:raw.index('#')] if '#' in raw else raw)
            if '' == raw: continue
            cmd, params = ((raw.split()[0], raw.split()[1:]) if 1 < len(raw.split()) else (raw, []))
            if 'shutdown' == cmd:
                break
            elif 'tick' == cmd:
                _cycle += sum(map(lambda x: integer(x), params))
                broadcast(connections, {'cycle': _cycle})
            elif 'run' == cmd:
                _cycle = run(connections, _cycle, args.max_cycles)
            else:
                {
                    'register': lambda x, y, z=None: register(connections, x, y, z),
                    'mainmem': lambda w, x, y, z=None: mainmem(connections, w, x, y, z),
                    'loadbin': lambda x, y: loadbin(x, y),
                    'run': lambda x: run(x),
                    'cycle': lambda: print(_cycle),
                    'connections': lambda: print(connections),
                    'push': lambda x: push(x),
                }.get(cmd, lambda : print('Unknown command!'))(*params)
    broadcast(connections, 'bye')
    [th.join() for th in _services]