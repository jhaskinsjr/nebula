# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import time
import socket
import argparse
import threading
import subprocess
import logging
import time
import json

import elftools.elf.elffile

import service
import riscv.constants

def tx(conns, msg):
    _msg = service.format(msg)
    for c in conns:
        service.tx(c, _msg, already_formatted=True)
        state.get('service.tx').update({'launcher.py': 1 + state.get('service.tx').get('launcher.py', 0)}) # NOTE: 1 at a time b/c conns might be an iterator
def handler(conn, addr):
    global state
    logging.debug('handler(): {}:{}'.format(*addr))
    _local = threading.local()
    _local.name = None
    _local.instructions_committed = 0
    _local.buffer = {
        'info': [],
        'futures': {},
    }
    tx([conn], {'ack': 'launcher'})
    while True: # FIXME: Break on {'shutdown': ...}, and send {'text': 'bye'} to conn
        try:
            msg = service.rx(conn)
            if _local.name:
                state.get('lock').acquire()
                state.get('service.rx').update({_local.name: 1 + state.get('service.rx').get(_local.name, 0)})
                state.get('lock').release()
            logging.debug('{}: {}'.format(threading.current_thread().name, msg))
            k, v = (next(iter(msg.items())) if isinstance(msg, dict) else (None, None))
            if {k: v} == {'text': 'bye'}:
                conn.close()
                state.get('lock').acquire()
                state.get('connections').update({_local.coreid: list(filter(lambda x: conn != x.get('conn'), state.get('connections').get(_local.coreid)))})
                state.get('lock').release()
                break
            elif 'shutdown' == k:
                state.get('lock').acquire()
                state.get('shutdown').update({v.get('coreid'): True})
                state.get('lock').release()
            elif 'undefined' == k:
                state.get('lock').acquire()
                state.update({'undefined': v})
                state.get('lock').release()
            elif 'committed' == k:
                _local.instructions_committed += v
            elif 'name' == k:
                threading.current_thread().name = v
            elif 'coreid' == k:
                _local.coreid = v
                _local.name = '[{:04}] {}'.format(_local.coreid, threading.current_thread().name) # NOTE: assumes {'name': ...} arrives before {'coreid': ...}
                state.get('lock').acquire()
                state.get('connections').update({_local.coreid: [{'conn': conn, 'name': _local.name}] + state.get('connections').get(_local.coreid, [])})
                state.get('lock').release()
            elif 'ack' == k:
                state.get('lock').acquire()
                state.get('ack').append({'name': _local.name, 'coreid': _local.coreid, 'msg': msg})
                logging.debug('{}.handler(): ack: {} ({})'.format(threading.current_thread().name, state.get('ack'), len(state.get('ack'))))
                state.get('info').extend(_local.buffer.get('info'))
                _local.buffer.get('info').clear()
                state.get('futures').update({
                    c: {
                        'results': state.get('futures').get(c, {'results': [], 'events': []}).get('results') + _local.buffer.get('futures').get(c).get('results'),
                        'events': state.get('futures').get(c, {'results': [], 'events': []}).get('events') + _local.buffer.get('futures').get(c).get('events'),
                    } for c in _local.buffer.get('futures').keys()
                })
                _local.buffer.get('futures').clear()
                state.update({'instructions_committed': _local.instructions_committed + state.get('instructions_committed')})
                _local.instructions_committed = 0
                state.get('lock').release()
            elif 'info' == k:
                _name = threading.current_thread().name
                _coreid = _local.coreid
                _local.buffer.get('info').append('[{:04}] {}.handler(): info : {}'.format(_coreid, _name, v))
            elif 'result' == k:
                _arr = v.pop('arrival')
                assert _arr > state.get('cycle'), '{}.handler(): Attempting to schedule result arrival in the past ({} vs. {})!'.format(threading.current_thread().name, _arr, state.get('cycle'))
                _res = v
                _res_evt = _local.buffer.get('futures').get(_arr, {'results': [], 'events': []})
                _res_evt.get('results').append(_res)
                _local.buffer.get('futures').update({_arr: _res_evt})
            elif 'event' == k:
                _arr = v.pop('arrival')
                assert _arr > state.get('cycle'), '{}.handler(): Attempting to schedule event arrival in the past ({} vs. {})!'.format(threading.current_thread().name, _arr, state.get('cycle'))
                _evt = v
                _res_evt = _local.buffer.get('futures').get(_arr, {'results': [], 'events': []})
                _res_evt.get('events').append(_evt)
                _local.buffer.get('futures').update({_arr: _res_evt})
            elif 'register' == k:
                _coreid = v.get('coreid')
                _cmd = v.get('cmd')
                _name = v.get('name')
                _data = v.get('data')
                register(filter(lambda y: conn != y, map(lambda x: x.get('conn'), sum(state.get('connections').values(), []))), _coreid, _cmd, _name, int.from_bytes(_data, 'little'))
            else:
                state.get('lock').acquire()
                state.get('unknown_message_key').append((threading.current_thread().name, msg))
                state.get('lock').release()
        except Exception as ex:
            logging.fatal('{}.handler(): Oopsie! {} (msg : {} ({}:{}), conn : {})'.format(threading.current_thread().name, ex, str(msg), type(msg), len(msg), conn))
            logging.fatal('{}.handler(): Initiating shutdown...'.format(threading.current_thread().name))
            state.get('lock').acquire()
            state.update({'running': False})
            tx(filter(lambda y: conn != y, map(lambda x: x.get('conn'), sum(state.get('connections').values(), []))), {'text': 'bye'})
            state.get('lock').release()
def acceptor():
    global state
    while True:
        _conn, _addr = state.get('socket').accept()
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
    if 'FALSE' == val.upper(): _val = False
    if 'TRUE' == val.upper(): _val = True
    tx(connections, {'config': {
        'service': service,
        'field': field,
        'val': _val,
    }})
def restore(state, snapshot_filename):
    logging.info('restore(): snapshot_filename            : {}'.format(snapshot_filename))
    _cycle = 0
    tx(map(lambda x: x.get('conn'), sum(state.get('connections').values(), [])), {
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
        time.sleep(0.001)
        logging.debug('state.ack : {} ({})'.format(state.get('ack'), len(state.get('ack'))))
        assert len(state.get('ack')) <= len(sum(state.get('connections').values(), [])), 'Something ACK\'d more than once!!! state.ack : ({}) {}'.format(len(state.get('ack')), state.get('ack'))
        _ack = len(state.get('ack')) == len(sum(state.get('connections').values(), []))
def run(cycle, max_cycles, max_instructions, break_on_undefined, snapshot_frequency):
    global state
    # {
    #   'tick': {
    #       'cycle': XXX,
    #       'results': [],
    #       'events': [],
    #   }
    # }
    _cmdline = (list(filter(lambda x: len(x), ' '.join(args.cmdline).strip().split(','))) if args.cmdline else [])
    if args.restore:
        _coreid = 0 # snapshot restore for now assumes a single core
        state.get('shutdown').update({_coreid: False})
        for c in (args.config if args.config else []): config(map(
            lambda x: x.get('conn'),
            sum(state.get('connections').values(), [])
        ), *c.split(':'))
        cycle = restore(state, args.restore)
        _futures = state.get('futures').pop(1 + cycle, {'results': [], 'events': []})
        _futures.get('events').extend([{'coreid': _coreid, 'init': True}])
        state.get('futures').update({1 + cycle: _futures})
        tx(map(lambda x: x.get('conn'), state.get('connections').get(_coreid)), 'run')
    if args.snapshots:
        tx(map(lambda x: x.get('conn'), sum(state.get('connections').values(), [])), {
            'snapshots': {
                'checkpoints': args.snapshots,
                'cmdline': state.get('cmdline'),
            }
        })
    state.get('lock').acquire()
    for c in (args.config if args.config else []): config(map(lambda x: x.get('conn'), state.get('connections').get(-1)), *c.split(':'))
    tx(map(lambda x: x.get('conn'), state.get('connections').get(-1)), 'run')
    state.get('lock').release()
    while (cycle < max_cycles if max_cycles else True) and \
          (state.get('instructions_committed') < max_instructions if max_instructions else True) and \
          (state.get('running')) and \
          (None == state.get('undefined') if break_on_undefined else True):
        logging.info('run(): @{:8}'.format(cycle))
        state.get('lock').acquire()
        if any(state.get('shutdown').values()) and len(_cmdline):
            _coreid = next(filter(lambda x: state.get('shutdown').get(x), state.get('shutdown').keys()))
            # NOTE: drain results and events from any prior binary executed on this core
#            state.update({'futures': {
#                c: {
#                    'results': list(filter(lambda x: _coreid != x.get('coreid'), state.get('futures').get(c).get('results'))),
#                    'events': list(filter(lambda x: _coreid != x.get('coreid'), state.get('futures').get(c).get('events'))),
#                }
#                for c in state.get('futures').keys()
#            }})
            state.update({'futures': {
                c: {
                    'results': list(filter(lambda x: coreid != x.get('coreid'), state.get('futures').get(c).get('results'))),
                    'events': list(filter(lambda x: coreid != x.get('coreid'), state.get('futures').get(c).get('events'))),
                }
                for c in state.get('futures').keys()
                for coreid in filter(lambda x: state.get('shutdown').get(x), state.get('shutdown').keys())
            }})
            _conn = list(map(lambda x: x.get('conn'), state.get('connections').get(_coreid)))
            tx(_conn, 'pause')
            for c in (args.config if args.config else []): config(_conn, *c.split(':'))
            _cmd = _cmdline.pop(0).strip().split(' ')
            _binary = os.path.join(os.getcwd(), _cmd[0])
            _args = tuple(_cmd[1:])
            tx(_conn, {'binary': os.path.join(os.getcwd(), _binary)})
            _sp = integer(args.loadbin[0])
            _pc = integer(args.loadbin[1])
            _start_symbol = args.loadbin[2]
            tx(map(lambda x: x.get('conn'), state.get('connections').get(-1, [])), 'pause')
            tx(_conn + list(map(lambda x: x.get('conn'), state.get('connections').get(-1, []))), {
                'loadbin': {
                    'coreid': _coreid,
                    'start_symbol': _start_symbol,
                    'sp': _sp,
                    'pc': _pc,
                    'binary': _binary,
                    'args': ((_binary,) + _args),
                }
            })
            tx(map(lambda x: x.get('conn'), state.get('connections').get(-1, [])), {'reset': {'coreid': _coreid}})
            tx(map(lambda x: x.get('conn'), state.get('connections').get(-1, [])), 'run')
            register(_conn, _coreid, 'set', 1, hex(0))
            register(_conn, _coreid, 'set', 2, hex(_sp))
            register(_conn, _coreid, 'set', 4, '0xffff0000') # FIXME: is this necessary???
            register(_conn, _coreid, 'set', 10, hex(1 + len(_args)))
            register(_conn, _coreid, 'set', 11, hex(8 + _sp))
            register(_conn, _coreid, 'set', '%pc', hex(_pc + get_startsymbol(_binary, _start_symbol)))
            logging.info('implied loadbin')
            logging.info('\tstate.shutdown : {}'.format(state.get('shutdown')))
            logging.info('\t_coreid        : {}'.format(_coreid))
            logging.info('\t_cmd           : {}'.format(_cmd))
            logging.info('\t_binary        : {}'.format(_binary))
            logging.info('\t_args          : {}'.format(_args))
            logging.info('\t_pc            : {}'.format(_pc + get_startsymbol(_binary, _start_symbol)))
            state.get('shutdown').update({_coreid: False})
            _futures = state.get('futures').pop(1 + cycle, {'results': [], 'events': []})
            _futures.get('events').extend([{'coreid': _coreid, 'init': True}])
            state.get('futures').update({1 + cycle: _futures})
            tx(_conn, 'run')
        state.update({'futures': {
            c: state.get('futures').get(c)
            for c in filter(
                lambda x: len(state.get('futures').get(x).get('results')) or len(state.get('futures').get(x).get('events')),
                state.get('futures').keys()
            )
        }})
        if all(state.get('shutdown').values()): state.update({'running': False})
        logging.debug('state.instructions_committed : {}'.format(state.get('instructions_committed')))
        logging.info('\tinfo :\n\t\t{}'.format('\n\t\t'.join(state.get('info'))))
        state.get('info').clear()
        logging.info('\tfutures :\n\t\t{}'.format(
            '\t\t'.join(map(lambda a: '{:8}: {}\n'.format(
                a,
                state.get('futures').get(a)
            ), sorted(state.get('futures').keys())))
        ))
        cycle = (min(state.get('futures').keys()) if len(state.get('futures').keys()) else 1 + cycle)
        _futures = state.get('futures').pop(cycle, {'results': [], 'events': []})
#        _futures.update({'results': list(filter(lambda x: not state.get('shutdown').get(x.get('coreid')), _futures.get('results')))})
#        _futures.update({'events': list(filter(lambda x: not state.get('shutdown').get(x.get('coreid')), _futures.get('events')))})
        state.update({'ack': sum(map(lambda x: [{'coreid': x}] * len(state.get('connections').get(x)), state.get('connections').keys()), [])})
#        for c in state.get('connections').keys():
        for c in filter(lambda x: not state.get('shutdown').get(x), state.get('connections').keys()):
            _res_evt = {
                'results': (_futures.get('results') if -1 == c else list(filter(lambda x: x.get('coreid') == c, _futures.get('results')))),
                'events': (_futures.get('events') if -1 == c else list(filter(lambda x: x.get('coreid') == c, _futures.get('events')))),
            }
            if 0 == len(sum(_res_evt.values(), [])): continue
            tx(map(lambda x: x.get('conn'), state.get('connections').get(c)), {'tick': {
                **{'cycle': cycle},
                **_res_evt,
            }})
            state.update({'ack': list(filter(lambda x: x.get('coreid') != c, state.get('ack')))})
        state.get('lock').release()
        waitforack(state)
    if state.get('undefined'): logging.info('*** Encountered undefined instruction! ***')
    return cycle
def add_service(services, arguments, s):
    c, h, p, coreid_init, coreid_fini, params = (s + ('' if 5 == s.count(':') else ':')).split(':')
    params = (params.replace('"', '').strip() if len(params) else None)
    _init = int(coreid_init)
    _fini = (-1 if -1 == _init else int(coreid_fini))
    for coreid in range(_init, 1 + _fini):
        services.append(
            threading.Thread(
                target=subprocess.run,
                args=([
                    'ssh',
                    '-p',
                    '{}'.format(p),
                    h,
                    'python3 {} {} {} {} {} {}'.format(
                        os.path.join(os.getcwd(), c),
                        ('-D' if arguments.debug else ''),
                        '{}:{}'.format(socket.gethostbyaddr(socket.gethostname())[0], arguments.port),
                        ('--log {}'.format(arguments.log) if arguments.log else ''),
                        ('--coreid {}'.format(coreid) if -1 != int(coreid) else ''),
                        ('{}'.format(params) if params else '')
                    )
                ],),
                daemon=True,
            )
        )
        if -1 < coreid: state.get('shutdown').update({coreid: True})
def spawn(services, args):
    if args.services:
        for s in args.services: add_service(services, args, s)
    for th in services:
        th.start()
        time.sleep(0.1)
    while len(services) > len(sum(state.get('connections').values(), [])): time.sleep(1)
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
    parser = argparse.ArgumentParser(description='Nebula')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--break_on_undefined', '-B', dest='break_on_undefined', action='store_true', help='cease execution on undefined instruction')
    parser.add_argument('--services', dest='services', nargs='+', help='code:host')
    parser.add_argument('--config', dest='config', nargs='+', help='service:field:val')
    parser.add_argument('--loadbin', dest='loadbin', nargs=3, default=['0x80000000', '0x00000000', '_start'], help='initial_sp initial_pc start_symbol')
    parser.add_argument('--restore', dest='restore', type=str, help='snapshot filename to be restored')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory')
    parser.add_argument('--max_cycles', type=int, dest='max_cycles', default=None, help='maximum number of cycles to run for')
    parser.add_argument('--max_instructions', type=int, dest='max_instructions', default=None, help='maximum number of instructions to execute')
    parser.add_argument('--snapshots', type=int, dest='snapshots', nargs='+', help='list of snapshot locations (in instructions)')
    parser.add_argument('port', type=int, help='port for accepting connections')
    parser.add_argument('script', type=str, help='script to be executed by Nebula')
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
        'connections': {},
        'ack': [],
        'futures': {},
        'info': [],
        'running': False,
        'cycle': 0,
        'socket': None,
        'instructions_committed': 0,
        'shutdown': {},
        'service.tx': {},
        'service.rx': {},
        'undefined': None,
        'unknown_message_key': [],
        'cmdline': None,
        'config': {
        },
    }
    state.update({'socket': socket.socket(socket.AF_INET, socket.SOCK_STREAM)})
    state.get('socket').setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    state.get('socket').bind(('0.0.0.0', args.port))
    state.get('socket').listen(5)
    threading.Thread(target=acceptor, daemon=True).start()
    _services = []
    with open(args.script) as fp:
        for raw in map(lambda x: x.strip(), fp.readlines()):
            raw = (raw[:raw.index('#')] if '#' in raw else raw)
            if '' == raw: continue
            cmd, params = ((raw.split()[0], raw.split()[1:]) if 1 < len(raw.split()) else (raw, []))
            if 2 == len(list(filter(lambda x: '"' in x, params))) and params[-1].endswith('"'): params = [' '.join(params)]
            if 'shutdown' == cmd:
                break
            elif 'tick' == cmd:
                state.update({'cycle': state.get('cycle') + sum(map(lambda x: integer(x), params))})
                tx(map(lambda x: x.get('conn'), sum(state.get('connections').values(), [])), {
                    'tick': {
                        'cycle': state.get('cycle'),
                        'results': [],
                        'events': [],
                    }
                })
            elif 'spawn' == cmd:
                spawn(_services, args)
            elif 'run' == cmd:
                assert not (len(args.cmdline) and args.restore), 'Both command line and --restore given!'
                state.update({'running': True})
                state.update({'cycle': run(state.get('cycle'), args.max_cycles, args.max_instructions, args.break_on_undefined, args.snapshots)})
                state.update({'running': False})
            else:
                {
                    'service': lambda x: add_service(_services, args, x),
                    'register': lambda w, x, y, z=None: register(map(lambda x: x.get('conn'), sum(state.get('connections').values(), [])), w, x, y, z),
                    'cycle': lambda: logging.info(state.get('cycle')),
                    'state': lambda: logging.info(state),
                    'config': lambda x, y: config(map(lambda x: x.get('conn'), sum(state.get('connections').values(), [])), *x.split(':'), y),
                    'connections': lambda: logging.info(state.get('connections')),
                }.get(cmd, lambda : logging.fatal('Unknown command!'))(*params)
    tx(map(lambda x: x.get('conn'), sum(state.get('connections').values(), [])), 'bye')
    [th.join() for th in _services]
    logging.info('state : {}'.format(json.dumps({k:v for k, v in state.items() if k not in ['lock', 'socket', 'connections']}, indent=4)))