# Copyright (C) 2021, 2022 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import riscv.constants


def do_tick(service, state, results, events):
    for _reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
        if '%pc' != _reg.get('name'): continue
        _pc = _reg.get('data')
        if 0 == int.from_bytes(_pc, 'little'):
            service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
            service.tx({'shutdown': None})
        service.tx({'info': '_pc           : {}'.format(_pc)})
        service.tx({'info': 'state.get(jp) : {}'.format(state.get('%jp'))})
        _jp_old = state.get('%jp')
        state.update({'%jp': _pc})
        service.tx({'info': '_jp : {} -> {} (%pc update)'.format(_jp_old, state.get('%jp'))})
    for _decode_buffer_available in map(lambda y: y.get('decode.buffer_available'), filter(lambda x: x.get('decode.buffer_available'), results)):
        state.update({'decode.buffer_available': _decode_buffer_available})
    service.tx({'info': 'decode.buffer_available : {}'.format(state.get('decode.buffer_available'))})
    service.tx({'info': 'fetch_size              : {}'.format(state.get('fetch_size'))})
    if state.get('decode.buffer_available') <= state.get('fetch_size'): return
    if state.get('stall_until') > state.get('cycle'): return
    if not state.get('%jp'): return
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'mem': {
            'cmd': 'peek',
            'addr': int.from_bytes(state.get('%jp'), 'little'),
            'size': state.get('fetch_size'),
        },
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'decode': {
            'addr': int.from_bytes(state.get('%jp'), 'little'),
            'size': state.get('fetch_size'),
        },
    }})
    _jp_old = state.get('%jp')
    state.update({'%jp': riscv.constants.integer_to_list_of_bytes(4 + int.from_bytes(state.get('%jp'), 'little'), 64, 'little')})
    service.tx({'info': '_jp : {} -> {} (%pc + 4)'.format(_jp_old, state.get('%jp'))})
    toolbox.report_stats(service, state, 'flat', 'number_of_fetches')

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Simple Core')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
    args = parser.parse_args()
    assert not os.path.isfile(args.log), '--log must point to directory, not file'
    while not os.path.isdir(args.log):
        try:
            os.makedirs(args.log, exist_ok=True)
        except:
            time.sleep(0.1)
    logging.basicConfig(
        filename=os.path.join(args.log, '{:04}_{}.log'.format(args.coreid, os.path.basename(__file__))),
        format='%(message)s',
        level=(logging.DEBUG if args.debug else logging.INFO),
    )
    logging.debug('args : {}'.format(args))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = {
        'service': 'fetch',
        'cycle': 0,
        'coreid': args.coreid,
        'stall_until': 0,
        'active': True,
        'running': False,
        'decode.buffer_available': 4,
        'fetch_size': 4, # HACK: hard-coded number of bytes to fetch
        '%jp': None, # This is the fetch pointer. Why %jp? Who knows?
        'ack': True,
    }
    _service = service.Service(state.get('service'), state.get('coreid'), _launcher.get('host'), _launcher.get('port'))
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
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
                do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'register' == k:
                if not '%pc' == v.get('name'): continue
                if not 'set' == v.get('cmd'): continue
                _pc = v.get('data')
                state.update({'%jp': _pc})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
