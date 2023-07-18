# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import sys
import argparse
import logging
import time
import functools
import struct

import service
import toolbox
import components.simplecache
import riscv.execute
import riscv.syscall.linux

def fetch_block(service, state, addr):
    _blockaddr = state.get('l2').blockaddr(addr)
    _blocksize = state.get('l2').nbytesperblock
    state.get('pending_fetch').append(_blockaddr)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'mem': {
            'cmd': 'peek',
            'addr': _blockaddr,
            'size': _blocksize,
        },
    }})
    toolbox.report_stats(service, state, 'flat', 'l2_misses')
def do_l2(service, state, addr, size, data=None):
    service.tx({'info': 'addr : {}'.format(addr)})
    _ante = None
    _post = None
    if state.get('l2').fits(addr, size):
        _data = state.get('l2').peek(addr, size)
#        service.tx({'info': '_data : {}'.format(_data)})
        if not _data:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr)
            return
    else:
        _blockaddr = state.get('l2').blockaddr(addr)
        _blocksize = state.get('l2').nbytesperblock
        _size = _blockaddr + _blocksize - addr
        _ante = state.get('l2').peek(addr, _size)
        if not _ante:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr)
            return
        _post = state.get('l2').peek(addr + _size, size - _size)
        if not _post:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr + _size)
            return
        # NOTE: In an L1DC with only a single block, an incoming _post would
        #       always displace _ante, and an incoming _ante would always displace
        #       _post... but an L1DC with only a single block would not be very
        #       useful in practice, so no effort will be made to handle that scenario.
        #       Like: No effort AT ALL.
        _data = _ante + _post
        assert len(_data) == size
    if data:
        # POKE
        service.tx({'result': {
            'arrival': state.get('config').get('l2_hitlatency') + state.get('cycle'),
            'coreid': state.get('coreid'),
            'l2': {
                'addr': addr,
                'size': size,
            },
        }})
        if _ante:
            assert _post
            state.get('l2').poke(addr, _ante)
            state.get('l2').poke(addr + size, _post)
        else:
            state.get('l2').poke(addr, data)
        # writethrough
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'mem': {
                'cmd': 'poke',
                'addr': addr,
                'size': len(data),
                'data': data
            }
        }})
    else:
        # PEEK
        service.tx({'result': {
            'arrival': state.get('config').get('l2_hitlatency') + state.get('cycle'), # must not arrive in commit the same cycle as the LOAD instruction
            'coreid': state.get('coreid'),
            'l2': {
                'addr': addr,
                'size': size,
                'data': _data,
            },
        }})
    state.get('executing').pop(0)
    if len(state.get('pending_fetch')): state.get('pending_fetch').pop(0)
    toolbox.report_stats(service, state, 'flat', 'l2_accesses')

def do_tick(service, state, results, events):
    for _mem in filter(lambda x: x, map(lambda y: y.get('mem'), results)):
        _addr = _mem.get('addr')
        if _addr == state.get('operands').get('mem'):
            state.get('operands').update({'mem': _mem.get('data')})
        elif _addr in state.get('pending_fetch'):
            service.tx({'info': '_mem : {}'.format(_mem)})
            state.get('l2').poke(_addr, _mem.get('data'))
            state.get('pending_fetch').remove(_addr)
    for ev in map(lambda y: y.get('l2'), filter(lambda x: x.get('l2'), events)):
        if 'cmd' in ev.keys() and 'purge' == ev.get('cmd'):
            state.get('l2').purge()
            continue
        state.get('executing').append(ev)
    if len(state.get('executing')):
        _op = state.get('executing')[0] # forcing single outstanding operation for now
        # NOTE: _op.get('cmd') assumed to be 'poke' if message contains a payload (i.e., _op.get('data') != None)
        _addr = _op.get('addr')
        _size = _op.get('size')
        _data = _op.get('data')
        do_l2(service, state, _addr, _size, _data)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Load-Store Unit')
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
        'service': 'l2',
        'cycle': 0,
        'coreid': args.coreid,
        'l2': None,
        'pending_fetch': [],
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': [],
        'executing': [],
        'operands': {},
        'config': {
            'l2_nsets': 2**5,
            'l2_nways': 2**4,
            'l2_nbytesperblock': 2**4,
            'l2_evictionpolicy': 'lru',
            'l2_hitlatency': 5,
        },
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                state.update({'l2': components.simplecache.SimpleCache(
                    state.get('config').get('l2_nsets'),
                    state.get('config').get('l2_nways'),
                    state.get('config').get('l2_nbytesperblock'),
                    state.get('config').get('l2_evictionpolicy'),
                )})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                if state.get('service') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
                do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
