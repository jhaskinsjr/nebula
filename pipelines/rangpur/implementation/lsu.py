# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging
import time
import functools
import struct

import service
import toolbox
import toolbox.stats
import components.simplecache
import riscv.execute
import riscv.constants
import riscv.syscall.linux

def fetch_block(service, state, addr):
    _blockaddr = state.get('l1dc').blockaddr(addr)
    _blocksize = state.get('l1dc').nbytesperblock
    service.tx({'info': 'fetch_block(..., {})'.format(addr)})
    state.get('pending_fetch').append(_blockaddr)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'l2': {
            'cmd': 'peek',
            'addr': _blockaddr,
            'size': _blocksize,
        },
    }})
#    toolbox.report_stats(service, state, 'flat', 'l1dc_misses')
    state.get('stats').refresh('flat', 'l1dc_misses')
def do_l1dc(service, state, insn, data=None):
    _addr = insn.get('operands').get('addr')
    _size = insn.get('nbytes')
    service.tx({'info': '_addr : {}'.format(_addr)})
    _ante = None
    _post = None
    if state.get('l1dc').fits(_addr, _size):
        _data = state.get('l1dc').peek(_addr, _size)
        if not _data:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, _addr)
            return
        service.tx({'info': '_data : @{} {}'.format(_addr, _data)})
    else:
        _blockaddr = state.get('l1dc').blockaddr(_addr)
        _blocksize = state.get('l1dc').nbytesperblock
        _antesize = _blockaddr + _blocksize - _addr
        _ante = state.get('l1dc').peek(_addr, _antesize)
        if not _ante:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, _addr)
            return
        _post = state.get('l1dc').peek(_addr + len(_ante), _size - len(_ante))
        if not _post:
            if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            fetch_block(service, state, _addr + len(_ante))
            return
        service.tx({'info': '_ante : @{} {}'.format(_addr, _ante)})
        service.tx({'info': '_post : @{} {}'.format(_addr + len(_ante), _post)})
        # NOTE: In an L1DC with only a single block, an incoming _post would
        #       always displace _ante, and an incoming _ante would always displace
        #       _post... but an L1DC with only a single block would not be very
        #       useful in practice, so no effort will be made to handle that scenario.
        #       Like: No effort AT ALL.
        _data = _ante + _post
        assert len(_data) == _size
    if data:
        # STORE
        service.tx({'result': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'l1dc': {
                'addr': _addr,
                'size': _size,
            },
        }})
        if _ante:
            assert _post
            service.tx({'info': '_ante : @{} {}'.format(_addr, _ante)})
            service.tx({'info': '_post : @{} {}'.format(_addr + len(_ante), _post)})
            state.get('l1dc').poke(_addr, _ante)
            state.get('l1dc').poke(_addr + len(_ante), _post)
        else:
            state.get('l1dc').poke(_addr, data)
        # writethrough
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'l2': {
                'cmd': 'poke',
                'addr': _addr,
                'size': len(data),
                'data': data
            }
        }})
    else:
       # LOAD
        service.tx({'result': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'l1dc': {
                'addr': _addr,
                'size': _size,
                'data': _data,
            },
        }})
    state.get('executing').pop(0)
    if len(state.get('pending_fetch')): state.get('pending_fetch').pop(0)
#    toolbox.report_stats(service, state, 'flat', 'l1dc_accesses')
    state.get('stats').refresh('flat', 'l1dc_accesses')

def do_unimplemented(service, state, insn):
    logging.info('Unimplemented: {}'.format(state.get('insn')))
    service.tx({'undefined': insn})

def do_load(service, state, insn):
    do_l1dc(service, state, insn)
def do_store(service, state, insn):
    _data = insn.get('operands').get('data')
    _data = {
        'SD': _data,
        'SW': _data[:4],
        'SH': _data[:2],
        'SB': _data[:1],
        'SC.D': _data,
        'SC.W': _data[:4],
    }.get(insn.get('cmd'))
    do_l1dc(service, state, insn, _data)

def do_execute(service, state):
    # NOTE: simpliying to only one in-flight LOAD/STORE at a time
    if not len(state.get('executing')) and not len(state.get('pending_execute')): return
    if not len(state.get('executing')) and state.get('pending_execute')[0].get('confirmed'): state.get('executing').append(state.get('pending_execute').pop(0))
    if not len(state.get('executing')): return
    _insn = state.get('executing')[0]
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
        'LR.W': do_load,
        'LR.D': do_load,
        'SC.W': do_store,
        'SC.D': do_store,
    }.get(_insn.get('cmd'), do_unimplemented)(service, state, _insn)

def do_tick(service, state, results, events):
    for _flush, _retire, _confirm in map(lambda y: (y.get('flush'), y.get('retire'), y.get('confirm')), filter(lambda x: x.get('flush') or x.get('retire') or x.get('confirm'), results)):
        if _flush:
            _ndx = next(filter(lambda x: _flush.get('iid') == state.get('pending_execute')[x].get('iid'), range(len(state.get('pending_execute')))), None)
            if not isinstance(_ndx, int): continue
            logging.info('_flush : {}'.format(_flush))
            service.tx({'info': 'flushing : {}'.format(_flush)})
            state.get('pending_execute').pop(_ndx)
        if _retire:
            _ndx = next(filter(lambda x: _retire.get('iid') == state.get('pending_execute')[x].get('iid'), range(len(state.get('pending_execute')))), None)
            if not isinstance(_ndx, int): continue
            logging.info('_retire : {}'.format(_retire))
            service.tx({'info': 'retiring : {}'.format(_retire)})
            state.get('pending_execute')[_ndx].update({'retired': True})
        if _confirm:
            _ndx = next(filter(lambda x: _confirm.get('iid') == state.get('pending_execute')[x].get('iid'), range(len(state.get('pending_execute')))), None)
            if not isinstance(_ndx, int): continue
            logging.info('_confirm : {}'.format(_confirm))
            service.tx({'info': 'confirming : {}'.format(_confirm)})
            state.get('pending_execute')[_ndx].update({'confirmed': True})
    for _l2 in filter(lambda x: x, map(lambda y: y.get('l2'), results)):
        _addr = _l2.get('addr')
        if _addr == state.get('operands').get('l2'):
            state.get('operands').update({'l2': _l2.get('data')})
        elif _addr in state.get('pending_fetch') and 'data' in _l2.keys():
            service.tx({'info': '_l2 : {}'.format(_l2)})
            state.get('l1dc').poke(_addr, _l2.get('data'))
            state.get('pending_fetch').remove(_addr)
    for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
        _cmd = _perf.get('cmd')
        if 'report_stats' == _cmd:
            _dict = state.get('stats').get(state.get('coreid')).get(state.get('service'))
            toolbox.report_stats_from_dict(service, state, _dict)
    for _lsu in map(lambda y: y.get('lsu'), filter(lambda x: x.get('lsu'), events)):
        if 'insn' in _lsu.keys():
            _insn = _lsu.get('insn')
            state.get('pending_execute').append(_insn)
            # TODO: should this commit event be done in alu like everything else?
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'commit': {
                    'insn': _insn,
                }
            }})
        elif 'cmd' in _lsu.keys() and 'purge' == _lsu.get('cmd'):
            state.get('l1dc').purge()
    service.tx({'info': 'state.pending_execute : {}'.format(state.get('pending_execute'))})
    do_execute(service, state)

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Load-Store Unit')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
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
        'service': 'lsu',
        'cycle': 0,
        'coreid': args.coreid,
        'l1dc': None,
        'pending_fetch': [],
        'active': True,
        'running': False,
        'ack': True,
        'pending_execute': [],
        'executing': [],
        'operands': {},
        'stats': None,
        'config': {
            'l1dc_nsets': 2**4,
            'l1dc_nways': 2**1,
            'l1dc_nbytesperblock': 2**4,
            'l1dc_evictionpolicy': 'lru',
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
                state.update({'pending_fetch': []})
                state.update({'pending_execute': []})
                state.update({'executing': []})
                state.update({'operands': {}})
                state.update({'stats': toolbox.stats.CounterBank(state.get('coreid'), state.get('service'))})
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                state.update({'l1dc': components.simplecache.SimpleCache(
                    state.get('config').get('l1dc_nsets'),
                    state.get('config').get('l1dc_nways'),
                    state.get('config').get('l1dc_nbytesperblock'),
                    state.get('config').get('l1dc_evictionpolicy'),
                )})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
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
