# Copyright (C) 2021, 2022 John Haskins Jr.

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
    _blockaddr = state.get('l1dc').blockaddr(addr)
    _blocksize = state.get('l1dc').nbytesperblock
    state.get('pending_fetch').append(_blockaddr)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'l2': {
            'cmd': 'peek',
            'addr': _blockaddr,
            'size': _blocksize,
        },
    }})
    toolbox.report_stats(service, state, 'flat', 'l1dc_misses')
def do_l1dc(service, state, addr, size, data=None):
    service.tx({'info': 'addr : {}'.format(addr)})
    _ante = None
    _post = None
    if state.get('l1dc').fits(addr, size):
        _data = state.get('l1dc').peek(addr, size)
#        service.tx({'info': '_data : {}'.format(_data)})
        if not _data:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr)
            return
    else:
        _blockaddr = state.get('l1dc').blockaddr(addr)
        _blocksize = state.get('l1dc').nbytesperblock
        _size = _blockaddr + _blocksize - addr
        _ante = state.get('l1dc').peek(addr, _size)
        if not _ante:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, addr)
            return
        _post = state.get('l1dc').peek(addr + _size, size - _size)
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
        # STORE
        service.tx({'result': {
            'arrival': 2 + state.get('cycle'),
            'l1dc': {
                'addr': addr,
                'size': size,
            },
        }})
        if _ante:
            assert _post
            state.get('l1dc').poke(addr, _ante)
            state.get('l1dc').poke(addr + size, _post)
        else:
            state.get('l1dc').poke(addr, data)
        # writethrough
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'l2': {
                'cmd': 'poke',
                'addr': addr,
                'size': len(data),
                'data': data
            }
        }})
    else:
        # LOAD
        service.tx({'result': {
            'arrival': 2 + state.get('cycle'), # must not arrive in commit the same cycle as the LOAD instruction
            'l1dc': {
                'addr': addr,
                'size': size,
                'data': _data,
            },
        }})
    state.get('executing').pop(0)
    if len(state.get('pending_fetch')): state.get('pending_fetch').pop(0)
    toolbox.report_stats(service, state, 'flat', 'l1dc_accesses')

def do_unimplemented(service, state, insn):
    logging.info('Unimplemented: {}'.format(state.get('insn')))
    service.tx({'undefined': insn})

def do_load(service, state, insn):
    do_l1dc(service, state, insn.get('operands').get('addr'), insn.get('nbytes'))
def do_store(service, state, insn):
    _data = insn.get('operands').get('data')
    _data = {
        'SD': _data,
        'SW': _data[:4],
        'SH': _data[:2],
        'SB': _data[:1],
    }.get(insn.get('cmd'))
    do_l1dc(service, state, insn.get('operands').get('addr'), insn.get('nbytes'), _data)

def do_execute(service, state):
    # NOTE: simpliying to only one in-flight LOAD/STORE at a time
    _insn = (state.get('executing')[0] if len(state.get('executing')) else (state.get('pending_execute')[0] if len(state.get('pending_execute')) else None))
    if not _insn: return
    if not len(state.get('executing')): state.get('executing').append(state.get('pending_execute').pop(0))
    service.tx({'info': '_insn : {}'.format(_insn)})
    {
        'LD': do_load,
        'LW': do_load,
        'LH': do_load,
        'LB': do_load,
        'LWU': do_load,
        'LHU': do_load,
        'LBU': do_load,
        'SD': do_store,
        'SW': do_store,
        'SH': do_store,
        'SB': do_store,
    }.get(_insn.get('cmd'), do_unimplemented)(service, state, _insn)

def do_tick(service, state, results, events):
    for _l2 in filter(lambda x: x, map(lambda y: y.get('l2'), results)):
        _addr = _l2.get('addr')
        if _addr == state.get('operands').get('l2'):
            state.get('operands').update({'l2': _l2.get('data')})
        elif _addr in state.get('pending_fetch'):
            service.tx({'info': '_l2 : {}'.format(_l2)})
            state.get('l1dc').poke(_addr, _l2.get('data'))
    for _insn in map(lambda y: y.get('lsu'), filter(lambda x: x.get('lsu'), events)):
        state.get('pending_execute').append(_insn.get('insn'))
        # TODO: should this commit event be done in alu like everything else?
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'commit': {
                'insn': _insn.get('insn'),
            }
        }})
    do_execute(service, state)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Load-Store Unit')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
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
    logging.debug('args : {}'.format(args))
    _launcher = {x:y for x, y in zip(['host', 'port'], args.launcher.split(':'))}
    _launcher['port'] = int(_launcher['port'])
    logging.debug('_launcher : {}'.format(_launcher))
    state = {
        'service': 'lsu',
        'cycle': 0,
        'l1dc': None,
        'pending_fetch': [],
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': [],
        'executing': [],
        'operands': {},
        'config': {
            'l1dc_nsets': 2**4,
            'l1dc_nways': 2**1,
            'l1dc_nbytesperblock': 2**4,
            'l1dc_evictionpolicy': 'lru',
        },
    }
    _service = service.Service(state.get('service'), _launcher.get('host'), _launcher.get('port'))
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
                state.update({'l1dc': components.simplecache.SimpleCache(
                    state.get('config').get('l1dc_nsets'),
                    state.get('config').get('l1dc_nways'),
                    state.get('config').get('l1dc_nbytesperblock'),
                    state.get('config').get('l1dc_evictionpolicy'),
                )})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = v.get('results')
                _events = v.get('events')
                do_tick(_service, state, _results, _events)
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
