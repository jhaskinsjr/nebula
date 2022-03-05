import os
import time
import socket
import json
import argparse
import threading
import subprocess
import itertools

import elftools.elf.elffile

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
    state.get('connections').append(conn)
    state.get('lock').release()
    print('handler(): {}:{}'.format(*addr))
    tx([conn], {'ack': 'launcher'})
    while True:
        try:
            msg = conn.recv(1024)
            if not len(msg):
                time.sleep(0.01)
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
            elif 'undefined' == k:
#                assert False
                state.get('lock').acquire()
                state.update({'undefined': v})
                state.get('lock').release()
            elif 'committed' == k:
                state.get('lock').acquire()
                state.update({'instructions_committed': 1 + state.get('instructions_committed')})
                state.get('lock').release()
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
    _name = name
    try:
        _name = int(_name)
    except:
        pass
    tx(connections, {'register': {**{
            'cmd': cmd,
            'name': _name,
        },
        **({'data': (integer(data) if isinstance(data, str) else data)} if data else {}),
    }})
def mainmem(connections, cmd, addr, size, data=None):
    tx(connections, {'mainmem': {**{
            'cmd': cmd,
            'addr': integer(addr),
            'size': integer(size),
        },
        **({'data': integer(data)} if data else {}),
    }})
def loadbin(connections, mainmem_rawfile, sp, pc, binary, *args):
    global state
    state.update({'mainmem_rawfile': mainmem_rawfile})
    fd = os.open(mainmem_rawfile, os.O_RDWR | os.O_CREAT)
    os.ftruncate(fd, 0)
    os.ftruncate(fd, 2**32) # HACK: hard-wired memory size is dumb, but I don't want to focus on that right now
    _start_pc = pc
    with open(binary, 'rb') as fp:
        elffile = elftools.elf.elffile.ELFFile(fp)
        _addr = pc
        for section in map(lambda n: elffile.get_section_by_name(n), ['.text', '.data', '.rodata', '.bss']):
            if not section: continue
            print('{} : 0x{:08x} ({})'.format(section.name, _addr, section.data_size))
            os.lseek(fd, _addr, os.SEEK_SET)
            os.write(fd, section.data())
            _addr += section.data_size
            _addr += 0x10000
            _addr |= 0xffff
            _addr ^= 0xffff
        _symbol_tables = [s for s in elffile.iter_sections() if isinstance(s, elftools.elf.elffile.SymbolTableSection)]
        _start = sum([list(filter(lambda s: '_start' == s.name, tab.iter_symbols())) for tab in _symbol_tables], [])
        assert 0 < len(_start), 'No _start symbol!'
        assert 2 > len(_start), 'More than one _start symbol?!?!?!?'
        _start = next(iter(_start))
        _start_pc += _start.entry.st_value - elffile.get_section_by_name('.text').header.sh_addr
    # The value of the argc argument is the number of command line
    # arguments. The argv argument is a vector of C strings; its elements
    # are the individual command line argument strings. The file name of
    # the program being run is also included in the vector as the first
    # element; the value of argc counts this element. A null pointer
    # always follows the last element: argv[argc] is this null pointer.
    #
    # For the command ‘cat foo bar’, argc is 3 and argv has three
    # elements, "cat", "foo" and "bar". 
    #
    # https://www.gnu.org/software/libc/manual/html_node/Program-Arguments.html
    _argc = 1 + len(args)   # add 1 since binary name is argv[0]
    _args = list(map(lambda a: '{}\0'.format(a), args))
    _fp  = sp
    _fp += 8           # 8 bytes for argc
    _fp += 8 * _argc   # 8 bytes for each argv * plus 1 NULL pointer
    _addr = list(itertools.accumulate([_fp] + list(map(lambda a: len(a), _args))))
    print('loadbin(): argc : {}'.format(_argc))
    print('loadbin(): len(_args) : {}'.format(sum(map(lambda a: len(a), _args))))
    for x, y in zip(_addr, _args):
        print('loadbin(): @{:08x} : {} ({})'.format(x, y, len(y)))
    os.lseek(fd, sp, os.SEEK_SET)
    os.write(fd, _argc.to_bytes(8, 'little'))       # argc
    os.lseek(fd, 8, os.SEEK_CUR)
    for a in _addr:                                 # argv pointers
        os.write(fd, a.to_bytes(8, 'little'))
        os.lseek(fd, 8, os.SEEK_CUR)
    os.lseek(fd, 8, os.SEEK_CUR)                    # NULL pointer
    os.write(fd, bytes(''.join(_args), 'ascii'))    # argv data
    os.close(fd)
    register(connections, 'set', 2, hex(sp))
    register(connections, 'set', '%pc', hex(_start_pc))
def config(args, field, val):
    _output = 'args.{} : {}'.format(field, args.__getattribute__(field))
    if val:
        _val = val
        try:
            _val = int(val)
        except:
            pass
        args.__setattr__(field, _val)
        _output += ' -> {}'.format(args.__getattribute__(field))
    print(_output)
def snapshot(mainmem_rawfile, snapshot_rawfile, cycle):
    global state
    subprocess.run('cp {} {}'.format(mainmem_rawfile, snapshot_rawfile).split())
    fd = os.open(snapshot_rawfile, os.O_RDWR)
    os.lseek(fd, 0x10000000, os.SEEK_SET) # HACK: hard-coding snapshot metadata to 0x10000000 is dumb, but I don't want to be bothered with that now
    os.write(fd, (1 + cycle).to_bytes(8, 'little'))
    os.lseek(fd, 8, os.SEEK_CUR)
    os.fsync(fd)
    os.close(fd)
    _res_evt = state.get('futures').get(1 + cycle, {'results': [], 'events': []})
    _res_evt.get('events').append({
        'register': {
            'cmd': 'snapshot',
            'name': '{}'.format(snapshot_rawfile),
            'data': 0x20000000, # HACK: hard-coding snapshot metadata to 0x20000000 is dumb, but I don't want to be bothere with that now
        }
    })
    state.get('futures').update({1 + cycle: _res_evt})
def restore(mainmem_rawfile, snapshot_rawfile):
    global state
    state.update({'mainmem_rawfile': mainmem_rawfile})
    subprocess.run('cp {} {}'.format(snapshot_rawfile, mainmem_rawfile).split())
    fd = os.open(mainmem_rawfile, os.O_RDWR)
    os.lseek(fd, 0x10000000, os.SEEK_SET)
    cycle = int.from_bytes(os.read(fd, 8), 'little')
#    os.write(fd, (0).to_bytes(4096, 'little'))
    os.lseek(fd, 0x20000000, os.SEEK_SET)
    pc = int.from_bytes(os.read(fd, 8), 'little')
#    os.write(fd, (0).to_bytes(4096, 'little'))
    os.close(fd)
    _res_evt = state.get('futures').get(cycle, {'results': [], 'events': []})
    _res_evt.get('events').append({
        'register': {
            'cmd': 'restore',
            'name': '{}'.format(snapshot_rawfile),
            'data': 0x20000000, # HACK: hard-coding snapshot metadata to 0x20000000 is dumb, but I don't want to be bothere with that now
        }
    })
    state.get('futures').update({cycle: _res_evt})
    register(state.get('connections'), 'set', '%pc', hex(pc))
    return cycle - 1
def run(cycle, max_cycles, max_instructions, break_on_undefined, snapshot_frequency):
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
    snapshot_at = cycle + snapshot_frequency
    while (cycle < max_cycles if max_cycles else True) and \
          (state.get('instructions_committed') < max_instructions if max_instructions else True) and \
          (None == state.get('undefined') if break_on_undefined else True):
        state.get('lock').acquire()
        if snapshot_at and cycle >= snapshot_at:
            snapshot(state.get('mainmem_rawfile'), '{}.snapshot'.format(state.get('mainmem_rawfile')), cycle)
            snapshot_at += snapshot_frequency
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
            time.sleep(0.01)
            state.get('lock').acquire()
            _ack = len(state.get('ack')) == len(state.get('connections'))
            state.get('lock').release()
    return cycle

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='μService-SIMulator')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='print debug messages')
    parser.add_argument('--break_on_undefined', '-B', dest='break_on_undefined', action='store_true', help='cease execution on undefined instruction')
    parser.add_argument('--services', dest='services', nargs='+', help='code:host')
    parser.add_argument('--max_cycles', type=int, dest='max_cycles', default=None, help='maximum number of cycles to run for')
    parser.add_argument('--max_instructions', type=int, dest='max_instructions', default=None, help='maximum number of instructions to execute')
    parser.add_argument('--snapshots', type=int, dest='snapshots', default=0, help='number of cycles per snapshot')
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
        'connections': [],
        'mainmem_rawfile': None,
        'ack': [],
        'futures': {},
        'running': False,
        'cycle': 0,
        'instructions_committed': 0,
        'undefined': None,
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
                state.update({'cycle': run(state.get('cycle'), args.max_cycles, args.max_instructions, args.break_on_undefined, args.snapshots)})
                state.update({'running': False})
            else:
                {
                    'register': lambda x, y, z=None: register(state.get('connections'), x, y, z),
                    'mainmem': lambda w, x, y, z=None: mainmem(state.get('connections'), w, x, y, z),
                    'loadbin': lambda w, x, y, z, *args: loadbin(state.get('connections'), w, integer(x), integer(y), z, *args),
                    'restore': lambda x, y: state.update({'cycle': restore(x, y)}),
                    'cycle': lambda: print(state.get('cycle')),
                    'state': lambda: print(state),
                    'config': lambda x, y=None: config(args, x, y),
                    'connections': lambda: print(state.get('connections')),
                }.get(cmd, lambda : print('Unknown command!'))(*params)
    tx(state.get('connections'), 'bye')
    [th.join() for th in _services]