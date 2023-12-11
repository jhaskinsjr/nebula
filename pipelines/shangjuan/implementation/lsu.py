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
    toolbox.report_stats(service, state, 'flat', 'l1dc_misses')
def do_l1dc(service, state):
    for _insn in filter(lambda x: not x.get('done'), state.get('executing')):
        _addr = _insn.get('operands').get('addr')
        _size = _insn.get('nbytes')
        service.tx({'info': '_addr : {}'.format(_addr)})
        _ante = None
        _post = None
        if state.get('l1dc').fits(_addr, _size):
            _data = state.get('l1dc').peek(_addr, _size)
            if not _data:
                if len(state.get('pending_fetch')): continue # only 1 pending fetch at a time is primitive, but good enough for now
                fetch_block(service, state, _addr)
                continue
            service.tx({'info': '_data : @{} {}'.format(_addr, _data)})
        else:
            _blockaddr = state.get('l1dc').blockaddr(_addr)
            _blocksize = state.get('l1dc').nbytesperblock
            _antesize = _blockaddr + _blocksize - _addr
            _ante = state.get('l1dc').peek(_addr, _antesize)
            if not _ante:
                if len(state.get('pending_fetch')): continue # only 1 pending fetch at a time is primitive, but good enough for now
                fetch_block(service, state, _addr)
                continue
            _post = state.get('l1dc').peek(_addr + len(_ante), _size - len(_ante))
            if not _post:
                if len(state.get('pending_fetch')): continue # only 1 pending fetch at a time is primitive, but good enough for now
                fetch_block(service, state, _addr + len(_ante))
                continue
            service.tx({'info': '_ante : @{} {}'.format(_addr, _ante)})
            service.tx({'info': '_post : @{} {}'.format(_addr + len(_ante), _post)})
            # NOTE: In an L1DC with only a single block, an incoming _post would
            #       always displace _ante, and an incoming _ante would always displace
            #       _post... but an L1DC with only a single block would not be very
            #       useful in practice, so no effort will be made to handle that scenario.
            #       Like: No effort AT ALL.
            _data = _ante + _post
            assert len(_data) == _size
        if _insn.get('operands').get('data'):
            # STORE
            if _ante:
                assert _post
                service.tx({'info': '_ante : @{} {}'.format(_addr, _ante)})
                service.tx({'info': '_post : @{} {}'.format(_addr + len(_ante), _post)})
                state.get('l1dc').poke(_addr, _ante)
                state.get('l1dc').poke(_addr + len(_ante), _post)
            else:
                state.get('l1dc').poke(_addr, _insn.get('operands').get('data'))
            # writethrough
            service.tx({'event': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'l2': {
                    'cmd': 'poke',
                    'addr': _addr,
                    'size': len(_insn.get('operands').get('data')),
                    'data': _insn.get('operands').get('data')
                }
            }})
        else:
            # LOAD
            _insn.update({'peeked': _data})
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'l1dc': {
                    'addr': _addr,
                    'size': _size,
                    'data': _data,
                },
            }})
        _insn.update({'done': True})
        if len(state.get('pending_fetch')): state.get('pending_fetch').pop(0)
        toolbox.report_stats(service, state, 'flat', 'l1dc_accesses')

def do_unimplemented(service, state, insn):
    logging.info('Unimplemented: {}'.format(state.get('insn')))
    service.tx({'undefined': insn})
def do_load(service, state, insn):
    if insn.get('peeked'):
        insn.update({'done': True})
        toolbox.report_stats(service, state, 'flat', 'load_serviced_by_preceding_queued_store')
def do_store(service, state, insn):
    insn.update({'result': None})

def do_execute(service, state):
    for _insn in state.get('pending_execute'):
        service.tx({'info': '_insn : {}'.format(_insn)})
        state.get('executing').append(_insn)
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
    do_l1dc(service, state)
    for _insn in filter(lambda x: x.get('done'), state.get('executing')):
        if _insn.get('peeked'):
            _peeked = _insn.get('peeked')
            _peeked += [-1] * (8 - len(_peeked))
            _result = { # HACK: This is 100% little-endian-specific
                'LD': _peeked,
                'LW': _peeked[:4] + [(0xff if ((_peeked[3] >> 7) & 0b1) else 0)] * 4,
                'LH': _peeked[:2] + [(0xff if ((_peeked[1] >> 7) & 0b1) else 0)] * 6,
                'LB': _peeked[:1] + [(0xff if ((_peeked[0] >> 7) & 0b1) else 0)] * 7,
                'LWU': _peeked[:4] + [0] * 4,
                'LHU': _peeked[:2] + [0] * 6,
                'LBU': _peeked[:1] + [0] * 7,
                'LR.D': _peeked,
                'LR.W': _peeked[:4] + [(0xff if ((_peeked[3] >> 7) & 0b1) else 0)] * 4,
            }.get(_insn.get('cmd'))
            _insn.update({'result': _result})
    for _insn in state.get('pending_execute'):
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'commit': {
                'insn': next(filter(lambda x: x.get('iid') == _insn.get('iid'), state.get('executing')), _insn),
            }
        }})
    state.update({'executing': list(filter(lambda x: not x.get('done'), state.get('executing')))})
def contains_load_data(ld, st):
    retval  = ld.get('operands').get('addr') >= st.get('operands').get('addr')
    retval &= ld.get('operands').get('addr') + ld.get('nbytes') <= st.get('operands').get('addr') + len(st.get('operands').get('data'))
    return retval

def do_tick(service, state, results, events):
    state.get('pending_execute').clear()
    for _retire in map(lambda y: y.get('retire'), filter(lambda x: x.get('retire'), results)):
        if _retire:
            _ndx = next(filter(lambda x: _retire.get('iid') == state.get('pending_execute')[x].get('iid'), range(len(state.get('pending_execute')))), None)
            if not isinstance(_ndx, int): continue
            logging.info('_retire : {}'.format(_retire))
            service.tx({'info': 'retiring : {}'.format(_retire)})
            state.get('pending_execute')[_ndx].update({'retired': True})
    for _l2 in filter(lambda x: x, map(lambda y: y.get('l2'), results)):
        _addr = _l2.get('addr')
        if _addr == state.get('operands').get('l2'):
            state.get('operands').update({'l2': _l2.get('data')})
        elif _addr in state.get('pending_fetch') and 'data' in _l2.keys():
            service.tx({'info': '_l2 : {}'.format(_l2)})
            state.get('l1dc').poke(_addr, _l2.get('data'))
            state.get('pending_fetch').remove(_addr)
    for _lsu in map(lambda y: y.get('lsu'), filter(lambda x: x.get('lsu'), events)):
        if 'insn' in _lsu.keys():
            _insn = _lsu.get('insn')
            if _insn.get('cmd') in riscv.constants.STORES:
                _data = _insn.get('operands').get('data')
                _data = {
                    'SD': _data,
                    'SW': _data[:4],
                    'SH': _data[:2],
                    'SB': _data[:1],
                    'SC.D': _data,
                    'SC.W': _data[:4],
                }.get(_insn.get('cmd'))
                _insn.get('operands').update({'data': _data})
                _insn.update({'result': None})
            else:
                _pending_stores = list(filter(lambda y: y.get('cmd') in riscv.constants.STORES, state.get('pending_execute')))
                _store = next(filter(lambda s: contains_load_data(_insn, s), reversed(_pending_stores)), None)
                logging.info('{} ?<- _pending_stores : {} ({}){}'.format(
                    [_insn.get('cmd'), _insn.get('iid'), _insn.get('operands').get('addr')],
                    list(map(lambda x: [x.get('cmd'), x.get('iid'), x.get('operands').get('addr')], _pending_stores)), len(_pending_stores),
                    (' -> {}'.format([_store.get('cmd'), _store.get('iid'), _store.get('operands').get('addr')]) if _store else '')
                ))
                if _store:
                    logging.debug('_store : {}'.format(_store))
                    _ld_addr = _insn.get('operands').get('addr')
                    _st_addr = _store.get('operands').get('addr')
                    _offset = _ld_addr - _st_addr
                    _peeked = _store.get('operands').get('data')[_offset:_offset+_insn.get('nbytes')]
                    _insn.update({'peeked': _peeked})
                    logging.debug('_insn : {}'.format(_insn))
            state.get('pending_execute').append(_insn)
        elif 'cmd' in _lsu.keys() and 'purge' == _lsu.get('cmd'):
            state.get('l1dc').purge()
    service.tx({'info': 'state.executing       : {} ({})'.format(list(map(lambda x: [x.get('cmd'), x.get('iid'), x.get('operands').get('addr')], state.get('executing'))), len(state.get('executing')))})
    service.tx({'info': 'state.pending_execute : {} ({})'.format(list(map(lambda x: [x.get('cmd'), x.get('iid'), x.get('operands').get('addr')], state.get('pending_execute'))), len(state.get('pending_execute')))})
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                state.update({'l1dc': components.simplecache.SimpleCache(
                    state.get('config').get('l1dc_nsets'),
                    state.get('config').get('l1dc_nways'),
                    state.get('config').get('l1dc_nbytesperblock'),
                    state.get('config').get('l1dc_evictionpolicy'),
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
