# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import time
import socket
import json
import argparse
import threading
import subprocess
import logging
import time

import elftools.elf.elffile

import service
import riscv.constants

def tx(conns, msg):
    _message = {
        str: lambda : json.dumps({'text': msg}),
        dict: lambda : json.dumps(msg),
    }.get(type(msg), lambda : json.dumps({'error': 'Undeliverable object'}))().encode('ascii')
    assert service.Service.MESSAGE_SIZE >= len(_message), 'Message too big! ({} bytes) -> {}'.format(len(_message), _message)
    _message += (' ' * (service.Service.MESSAGE_SIZE - len(_message))).encode('ascii')
    for c in conns: c.send(_message)
def handler(conn, addr):
    global state
    state.get('lock').acquire()
    state.get('connections').append(conn)
    state.get('lock').release()
    logging.debug('handler(): {}:{}'.format(*addr))
    tx([conn], {'ack': 'launcher'})
    while True: # FIXME: Break on {'shutdown': ...}, and send {'text': 'bye'} to conn
        try:
            msg = conn.recv(service.Service.MESSAGE_SIZE, socket.MSG_WAITALL)
            if not len(msg.strip()):
                time.sleep(0.01)
                continue
            msg = json.loads(msg.decode('ascii'))
            logging.debug('{}: {}'.format(threading.current_thread().name, msg))
            k, v = (next(iter(msg.items())) if isinstance(msg, dict) else (None, None))
            if {k: v} == {'text': 'bye'}:
                conn.close()
                state.get('lock').acquire()
                state.get('connections').remove(conn)
                state.get('lock').release()
                break
            elif 'shutdown' == k:
                state.get('lock').acquire()
                state.get('shutdown').update({v.get('coreid'): True})
                if all(state.get('shutdown').values()): state.update({'running': False})
                state.get('lock').release()
            elif 'undefined' == k:
                state.get('lock').acquire()
                state.update({'undefined': v})
                state.get('lock').release()
            elif 'committed' == k:
                state.get('lock').acquire()
                state.update({'instructions_committed': v + state.get('instructions_committed')})
                state.get('lock').release()
            elif 'name' == k:
                threading.current_thread().name = v
            elif 'info' == k:
                state.get('lock').acquire()
                state.get('info').append('{}.handler(): info : {}'.format(threading.current_thread().name, v))
                state.get('lock').release()
            elif 'ack' == k:
                state.get('lock').acquire()
                state.get('ack').append((threading.current_thread().name, msg))
                logging.debug('{}.handler(): ack: {} ({})'.format(threading.current_thread().name, state.get('ack'), len(state.get('ack'))))
                state.get('lock').release()
            elif 'result' == k:
                _arr = v.pop('arrival')
                assert _arr > state.get('cycle'), '{}.handler(): Attempting to schedule result arrival in the past ({} vs. {})!'.format(threading.current_thread().name, _arr, state.get('cycle'))
                _res = v
                state.get('lock').acquire()
                _res_evt = state.get('futures').get(_arr, {'results': [], 'events': []})
                _res_evt.get('results').append(_res)
                state.get('futures').update({_arr: _res_evt})
                state.get('lock').release()
            elif 'event' == k:
                _arr = v.pop('arrival')
                assert _arr > state.get('cycle'), '{}.handler(): Attempting to schedule event arrival in the past ({} vs. {})!'.format(threading.current_thread().name, _arr, state.get('cycle'))
                _evt = v
                state.get('lock').acquire()
                _res_evt = state.get('futures').get(_arr, {'results': [], 'events': []})
                _res_evt.get('events').append(_evt)
                state.get('futures').update({_arr: _res_evt})
                state.get('lock').release()
            elif 'register' == k:
                logging.debug('{}.handler(): register : {}'.format(threading.current_thread().name, v))
                state.get('lock').acquire()
                tx(filter(lambda c: c != conn, state.get('connections')), msg)
                state.get('lock').release()
            else:
                state.get('lock').acquire()
                _running = state.get('running')
                state.get('lock').release()
                logging.debug('{}.handler(): _running : {} ({})'.format(threading.current_thread().name, _running, msg))
                if _running:
                    state.get('lock').acquire()
#                    state.get('events').append(msg)
                    state.get('lock').release()
                else:
                    state.get('lock').acquire()
                    tx(filter(lambda c: c != conn, state.get('connections')), msg)
                    state.get('lock').release()
        except Exception as ex:
            logging.fatal('{}.handler(): Oopsie! {} (msg : {} ({}:{}), conn : {})'.format(threading.current_thread().name, ex, str(msg), type(msg), len(msg), conn))
            logging.fatal('{}.handler(): Initiating shutdown...'.format(threading.current_thread().name))
            state.get('lock').acquire()
            state.update({'running': False})
            tx(filter(lambda c: c != conn, state.get('connections')), {'text': 'bye'})
            state.get('lock').release()
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
def register(connections, coreid, cmd, name, data=None):
    _name = name
    try:
        _name = int(_name)
    except:
        pass
    tx(connections, {'register': {**{
            'coreid': coreid,
            'cmd': cmd,
            'name': _name,
        },
        **({'data': (riscv.constants.integer_to_list_of_bytes(integer(data), 64, 'little') if isinstance(data, str) else riscv.constants.integer_to_list_of_bytes(data, 64, 'little'))} if data else {}),
    }})
def config(connections, service, field, val):
    _val = val
    try:
        _val = integer(val)
    except:
        pass
    tx(connections, {'config': {
        'service': service,
        'field': field,
        'val': _val,
    }})
def restore(state, snapshot_filename):
    logging.info('restore(): snapshot_filename            : {}'.format(snapshot_filename))
    _cycle = 0
    tx(state.get('connections'), {
        'restore': {
            'cycle': _cycle,
            'snapshot_filename': snapshot_filename,
        }
    })
    waitforack(state)
    return _cycle
def waitforack(state):
    _ack = False
    while not _ack:
        time.sleep(0.01)
        logging.debug('state.ack : {} ({})'.format(state.get('ack'), len(state.get('ack'))))
        assert len(state.get('ack')) <= len(state.get('connections')), 'Something ACK\'d more than once!!!'
        _ack = len(state.get('ack')) == len(state.get('connections'))
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
    snapshot_at = state.get('instructions_committed') + snapshot_frequency
    while (cycle < max_cycles if max_cycles else True) and \
          (state.get('instructions_committed') < max_instructions if max_instructions else True) and \
          (state.get('running')) and \
          (None == state.get('undefined') if break_on_undefined else True):
        state.get('lock').acquire()
        _snapshot = {}
        if snapshot_frequency and snapshot_at and state.get('instructions_committed') >= snapshot_at:
            state.update({'cycle': cycle})
            _snapshot = {
                'snapshot': {
                    'addr': state.get('snapshot').get('addr'),
                    'data': {
                        'cycle': state.get('cycle'),
                        'instructions_committed': state.get('instructions_committed'),
                        'cmdline': state.get('cmdline'),
                    },
                }
            }
            snapshot_at += snapshot_frequency
        logging.debug('snapshot_frequency : {}'.format(snapshot_frequency))
        logging.debug('snapshot_at        : {}'.format(snapshot_at))
        logging.debug('state.instructions_committed : {}'.format(state.get('instructions_committed')))
        logging.info('run(): @{:8}'.format(cycle))
        logging.info('\tinfo :\n\t\t{}'.format('\n\t\t'.join(state.get('info'))))
        state.get('info').clear()
        logging.info('\tfutures :\n\t\t{}'.format(
            '\t\t'.join(map(lambda a: '{:8}: {}\n'.format(
                a,
                state.get('futures').get(a)
            ), sorted(state.get('futures').keys())))
        ))
        cycle = (min(state.get('futures').keys()) if len(state.get('futures').keys()) else 1 + cycle)
        tx(state.get('connections'), {'tick': {
            **{'cycle': cycle},
            **_snapshot,
            **dict(state.get('futures').get(cycle, {'results': [], 'events': []})),
        }})
        if cycle in state.get('futures'): state.get('futures').pop(cycle)
        state.get('ack').clear()
        state.get('lock').release()
        waitforack(state)
    if state.get('undefined'): logging.info('*** Encountered undefined instruction! ***')
    return cycle
def add_service(services, arguments, s):
    c, h, coreid = s.split(':')
    services.append(
        threading.Thread(
            target=subprocess.run,
            args=([
                'ssh',
                h,
                'python3 {} {} {} {} {}'.format(
                    os.path.join(os.getcwd(), c),
                    ('-D' if arguments.debug else ''),
                    '{}:{}'.format(socket.gethostbyaddr(socket.gethostname())[0], arguments.port),
                    ('--log {}'.format(arguments.log) if arguments.log else ''),
                    ('--coreid {}'.format(coreid) if -1 != int(coreid) else ''),
                )
            ],),
            daemon=True,
        )
    )
def spawn(services, args):
    if args.services:
        for s in args.services: add_service(services, args, s)
#    [th.start() for th in services]
    for th in services:
        th.start()
        time.sleep(1)
    while len(services) > len(state.get('connections')): time.sleep(1)
def get_startsymbol(binary, start_symbol):
    with open(binary, 'rb') as fp:
        elffile = elftools.elf.elffile.ELFFile(fp)
        _symbol_tables = [s for s in elffile.iter_sections() if isinstance(s, elftools.elf.elffile.SymbolTableSection)]
        _start = sum([list(filter(lambda s: start_symbol == s.name, tab.iter_symbols())) for tab in _symbol_tables], [])
        assert 0 < len(_start), 'No {} symbol!'.format(start_symbol)
        assert 2 > len(_start), 'More than one {} symbol?!?!?!?'.format(start_symbol)
        _start = next(iter(_start))
        return _start.entry.st_value

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='μService-SIMulator')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--break_on_undefined', '-B', dest='break_on_undefined', action='store_true', help='cease execution on undefined instruction')
    parser.add_argument('--services', dest='services', nargs='+', help='code:host')
    parser.add_argument('--config', dest='config', nargs='+', help='service:field:val')
    parser.add_argument('--loadbin', dest='loadbin', nargs=3, default=['0x80000000', '0x00000000', '_start'], help='initial_sp initial_pc start_symbol')
    parser.add_argument('--restore', dest='restore', type=str, help='snapshot filename to be restored')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory')
    parser.add_argument('--max_cycles', type=int, dest='max_cycles', default=None, help='maximum number of cycles to run for')
    parser.add_argument('--max_instructions', type=int, dest='max_instructions', default=None, help='maximum number of instructions to execute')
    parser.add_argument('--snapshots', type=int, dest='snapshots', default=0, help='number of instructions per snapshot')
    parser.add_argument('port', type=int, help='port for accepting connections')
    parser.add_argument('script', type=str, help='script to be executed by μService-SIMulator')
    parser.add_argument('cmdline', nargs='*', help='binary to be executed and parameters')
    args = parser.parse_args()
    assert not os.path.isfile(args.log), '--log must point to directory, not file'
    while not os.path.isdir(args.log):
        try:
            os.makedirs(args.log, exist_ok=True)
        except:
            time.sleep(0.1)
    logging.basicConfig(
        filename=os.path.join(args.log, '{}.log'.format(os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    assert os.path.exists(args.script), 'Cannot open script file, {}!'.format(args.script)
    logging.debug('args : {}'.format(args))
    state = {
        'lock': threading.Lock(),
        'connections': [],
        'ack': [],
        'futures': {},
        'info': [],
        'running': False,
        'cycle': 0,
        'instructions_committed': 0,
        'shutdown': {},
        'undefined': None,
        'cmdline': None,
        'snapshot': {
            'addr': {
                'padding': 0x0000,
                'cycle': 0x1000,
                'instructions_committed': 0x2000,
                'cmdline_length': 0x3000,
                'cmdline': 0x4000,
                'registers_length': 0x5000,
                'registers': 0x6000,
                'mmu_length': 0x7000,
                'mmu': 0x8000,
            },
        },
        'config': {
            'mainmem_filename': None,
            'mainmem_capacity': None,
            'toolchain': '',
        },
    }
    _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _s.bind(('0.0.0.0', args.port))
    _s.listen(5)
    threading.Thread(target=acceptor, daemon=True).start()
    _services = []
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
                assert not (len(args.cmdline) and args.restore), 'Both command line and --restore given!'
                if len(args.cmdline): tx(state.get('connections'), {
                    'binary': os.path.join(os.getcwd(), args.cmdline[0]),
                })
                for c in (args.config if args.config else []): config(state.get('connections'), *c.split(':'))
                if len(args.cmdline):
                    state.update({'cmdline': ' '.join(args.cmdline)})
                    _sp = integer(args.loadbin[0])
                    _pc = integer(args.loadbin[1])
                    _start_symbol = args.loadbin[2]
                    for _coreid, _cmdline in enumerate(' '.join(args.cmdline).split(',')):
                        _cmdline = _cmdline.split()
                        _binary = os.path.join(os.getcwd(), _cmdline[0])
                        _args = tuple(_cmdline[1:])
                        tx(state.get('connections'), {
                            'loadbin': {
                                'coreid': _coreid,
                                'start_symbol': _start_symbol,
                                'sp': _sp,
                                'pc': _pc,
                                'binary': _binary,
                                'args': ((_binary,) + _args),
                            }
                        })
                        register(state.get('connections'), _coreid, 'set', 2, hex(_sp))
                        register(state.get('connections'), _coreid, 'set', 4, '0xffff0000') # FIXME: is this necessary???
                        register(state.get('connections'), _coreid, 'set', 10, hex(1 + len(_args)))
                        register(state.get('connections'), _coreid, 'set', 11, hex(8 + _sp))
                        register(state.get('connections'), _coreid, 'set', '%pc', hex(_pc + get_startsymbol(_binary, _start_symbol)))
                        logging.info('implied loadbin')
                        logging.info('\t_coreid  : {}'.format(_coreid))
                        logging.info('\t_cmdline : {}'.format(_cmdline))
                        logging.info('\t_binary  : {}'.format(_binary))
                        logging.info('\t_args    : {}'.format(_args))
                        state.get('shutdown').update({len(state.get('shutdown').keys()): False})
                elif args.restore:
                    restore(state, args.restore)
                    state.get('shutdown').update({len(state.get('shutdown').keys()): False})
                else:
                    assert False, 'Neither command line nor --restore!'
                state.update({'running': True})
                state.update({'cycle': run(state.get('cycle'), args.max_cycles, args.max_instructions, args.break_on_undefined, args.snapshots)})
                state.update({'running': False})
            elif 'spawn' == cmd:
                spawn(_services, args)
            else:
                {
                    'service': lambda x: add_service(_services, args, x),
                    'register': lambda w, x, y, z=None: register(state.get('connections'), w, x, y, z),
                    'cycle': lambda: logging.info(state.get('cycle')),
                    'state': lambda: logging.info(state),
                    'config': lambda x, y: config(state.get('connections'), *x.split(':'), y),
                    'connections': lambda: logging.info(state.get('connections')),
                }.get(cmd, lambda : logging.fatal('Unknown command!'))(*params)
    tx(state.get('connections'), 'bye')
    [th.join() for th in _services]