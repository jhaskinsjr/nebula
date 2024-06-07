# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import components.simplecache
import components.simplemmu
import riscv.constants

def fetch_block(service, state, jp, physical):
    _blockaddr = state.get('l1ic').blockaddr(jp)
    _blocksize = state.get('l1ic').nbytesperblock
    service.tx({'info': 'fetch_block(..., {} ({:08x}))'.format(jp, _blockaddr)})
    state.get('pending_fetch').append(_blockaddr)
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'l2': {
            'cmd': 'peek',
            'addr': _blockaddr,
            'size': _blocksize,
            'physical': physical,
        },
    }})
    toolbox.report_stats(service, state, 'flat', 'l1ic_misses')
def do_l1ic(service, state):
    _req = state.get('fetch_buffer')[0]
    logging.debug('_req : {}'.format(_req))
    _vaddr = _req.get('addr')
    _pagesize = state.get('config').get('pagesize')
    _frame = components.simplemmu.frame(_pagesize, _vaddr)
    if _frame not in state.get('tlb').keys(): return
    _jp = state.get('tlb').get(_frame) | components.simplemmu.offset(_pagesize, _vaddr)
    _physical = True
    service.tx({'info': '_jp : {} ({})'.format(list(_jp.to_bytes(8, 'little')), _jp)})
    _blockaddr = state.get('l1ic').blockaddr(_jp)
    _blocksize = state.get('l1ic').nbytesperblock
    _data = state.get('l1ic').peek(_blockaddr, _blocksize)
    service.tx({'info': '_data : {}'.format(_data)})
    if not _data:
        if len(state.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
        fetch_block(service, state, _jp, _physical)
        return
    _data = _data[(_jp - _blockaddr):]
    service.tx({'result': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'l1ic': {
            'addr': _vaddr,
            'size': len(_data),
            'data': _data,
        },
    }})
    service.tx({'event': {
        'arrival': 1 + state.get('cycle'),
        'coreid': state.get('coreid'),
        'decode': {
            'addr': _vaddr,
            'data': _data,
        },
    }})
    state.get('fetch_buffer').pop(0)
    toolbox.report_stats(service, state, 'flat', 'l1ic_accesses')
def do_tick(service, state, results, events):
    for _l2 in map(lambda y: y.get('l2'), filter(lambda x: x.get('l2'), results)):
        _addr = _l2.get('addr')
        if _addr not in state.get('pending_fetch'): continue
        service.tx({'info': '_l2 : {}'.format(_l2)})
        state.get('l1ic').poke(_addr, _l2.get('data'))
        state.get('pending_fetch').remove(_addr)
    for _mmu in map(lambda y: y.get('mmu'), filter(lambda x: x.get('mmu'), results)):
        _vaddr = _mmu.get('vaddr')
        _pagesize = state.get('config').get('pagesize')
        _frame = components.simplemmu.frame(_pagesize, _vaddr)
        if _frame not in state.get('pending_v2p'): continue
        state.update({'pending_v2p': list(filter(lambda x: _frame != x, state.get('pending_v2p')))})
        state.get('tlb').update({_frame: _mmu.get('frame')})
    for _fetch in map(lambda y: y.get('fetch'), filter(lambda x: x.get('fetch'), events)):
        if 'cmd' in _fetch.keys():
            if 'purge' == _fetch.get('cmd'):
                state.get('l1ic').purge()
            elif 'get' == _fetch.get('cmd'):
                _vaddr = _fetch.get('addr')
                state.get('fetch_buffer').append({
                    'addr': _vaddr,
                })
                _pagesize = state.get('config').get('pagesize')
                _frame = components.simplemmu.frame(_pagesize, _vaddr)
                if _frame not in state.get('tlb').keys():
                    state.get('pending_v2p').append(_frame)
                    service.tx({'event': {
                        'arrival': 1 + state.get('cycle'),
                        'coreid': state.get('coreid'),
                        'mmu': {
                            'cmd': 'v2p',
                            'vaddr': _vaddr,
                        }
                    }})
    if not len(state.get('fetch_buffer')): return
    service.tx({'info': 'fetch_buffer : {}'.format(state.get('fetch_buffer'))})
    do_l1ic(service, state)
    

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Instruction Fetch')
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
        'service': 'fetch',
        'cycle': 0,
        'coreid': args.coreid,
        'l1ic': None,
        'tlb': {},
        'pending_v2p': [],
        'pending_fetch': [],
        'active': True,
        'running': False,
        'fetch_buffer': [],
        '%jp': None, # This is the fetch pointer. Why %jp? Who knows?
        '%pc': None,
        'ack': True,
        'config': {
            'l1ic_nsets': 2**4,
            'l1ic_nways': 2**1,
            'l1ic_nbytesperblock': 2**4,
            'l1ic_evictionpolicy': 'lru',
            'pagesize': 2**16,
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
                logging.info('state.config : {}'.format(state.get('config')))
                state.update({'running': True})
                state.update({'ack': False})
                state.update({'tlb': {}})
                state.update({'pending_v2p': []})
                state.update({'pending_fetch': []})
                state.update({'active': True})
                state.update({'fetch_buffer': []})
                state.update({'%jp': None})
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                state.update({'l1ic': components.simplecache.SimpleCache(
                    state.get('config').get('l1ic_nsets'),
                    state.get('config').get('l1ic_nways'),
                    state.get('config').get('l1ic_nbytesperblock'),
                    state.get('config').get('l1ic_evictionpolicy'),
                )})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'config' == k:
                logging.debug('config : {}'.format(v))
                logging.debug('config : {}'.format(v))
                if v.get('service') not in [state.get('name'), 'all']: continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys() or 'all' == v.get('service'), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
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
            elif 'register' == k:
                logging.info('register : {}'.format(v))
                if state.get('coreid') != v.get('coreid'): continue
                if 'set' != v.get('cmd'): continue
                if '%pc' != v.get('name'): continue
                state.update({'%pc': v.get('data')})
                logging.info('state : {}'.format(state))
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    logging.info('state : {}'.format(state))
