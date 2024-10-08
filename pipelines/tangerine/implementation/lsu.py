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
import components.simplemmu
import riscv.execute
import riscv.constants
import riscv.syscall.linux


def do_unimplemented(service, state, insn):
    logging.info(os.path.basename(__file__) + ': Unimplemented: {}'.format(state.get('insn')))
    service.tx({'undefined': insn})
def do_load(service, state, insn):
    if insn.get('peeked'):
        insn.update({'done': True})
        state.get('stats').refresh('flat', 'load_serviced_by_preceding_queued_store')
def do_store(service, state, insn):
    insn.update({'result': None})

def fetch_block(service, state, addr, physical):
    _blockaddr = state.get('l1dc').blockaddr(addr)
    _blocksize = state.get('l1dc').nbytesperblock
    logging.info(os.path.basename(__file__) + ': fetch_block(..., {} ({:08x}))'.format(addr, _blockaddr))
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
    state.get('stats').refresh('flat', 'l1dc_misses')
def do_l1dc(service, state):
    for _insn in filter(lambda x: not x.get('done'), state.get('executing')):
        _vaddr = _insn.get('operands').get('addr')
        _pagesize = state.get('config').get('pagesize')
        _frame = components.simplemmu.frame(_pagesize, _vaddr)
        if _frame not in state.get('tlb').keys(): continue
        _addr = state.get('tlb').get(_frame) | components.simplemmu.offset(_pagesize, _vaddr)
        _physical = True
        _size = _insn.get('nbytes')
        logging.info(os.path.basename(__file__) + ': _addr : {} ({})'.format(_addr, _vaddr))
        _ante = None
        _post = None
        if state.get('l1dc').fits(_addr, _size):
            _data = state.get('l1dc').peek(_addr, _size)
            if not _data:
                if len(state.get('pending_fetch')): continue # only 1 pending fetch at a time is primitive, but good enough for now
                fetch_block(service, state, _addr, _physical)
                continue
            logging.info(os.path.basename(__file__) + ': _data : @{} {}'.format(_addr, _data))
        else:
            _blockaddr = state.get('l1dc').blockaddr(_addr)
            _blocksize = state.get('l1dc').nbytesperblock
            _antesize = _blockaddr + _blocksize - _addr
            _ante = state.get('l1dc').peek(_addr, _antesize)
            if not _ante:
                if len(state.get('pending_fetch')): continue # only 1 pending fetch at a time is primitive, but good enough for now
                fetch_block(service, state, _addr, _physical)
                continue
            _post = state.get('l1dc').peek(_addr + len(_ante), _size - len(_ante))
            if not _post:
                if len(state.get('pending_fetch')): continue # only 1 pending fetch at a time is primitive, but good enough for now
                fetch_block(service, state, _addr + len(_ante), _physical)
                continue
            logging.info(os.path.basename(__file__) + ': _ante : @{} {}'.format(_addr, _ante))
            logging.info(os.path.basename(__file__) + ': _post : @{} {}'.format(_addr + len(_ante), _post))
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
                logging.info(os.path.basename(__file__) + ': _ante : @{} {}'.format(_addr, _ante))
                logging.info(os.path.basename(__file__) + ': _post : @{} {}'.format(_addr + len(_ante), _post))
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
                    'data': _insn.get('operands').get('data'),
                    'physical': _physical,
                }
            }})
        else:
            # LOAD
            _insn.update({'peeked': _data})
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'l1dc': {
                    'addr': _vaddr,
                    'size': _size,
                    'data': _data,
                },
            }})
        _insn.update({'done': True})
        if len(state.get('pending_fetch')): state.get('pending_fetch').pop(0)
        state.get('stats').refresh('flat', 'l1dc_accesses')
def do_execute(service, state):
    for _insn in state.get('pending_execute'):
        logging.info(os.path.basename(__file__) + ': _insn : {}'.format(_insn))
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

class LSU:
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.config = {
            'l1dc_nsets': 2**4,
            'l1dc_nways': 2**1,
            'l1dc_nbytesperblock': 2**4,
            'l1dc_evictionpolicy': 'lru',
            'pagesize': 2**16,
        }
    def state(self):
        return {
            'service': self.get('name'),
            'cycle': self.get('cycle'),
            'coreid': self.get('coreid'),
        }
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)
    def boot(self):
        self.update({'tlb': {}})
        self.update({'pending_v2p': []})
        self.update({'pending_fetch': []})
        self.update({'pending_execute': []})
        self.update({'executing': []})
        self.update({'l1dc': components.simplecache.SimpleCache(
            self.get('config').get('l1dc_nsets'),
            self.get('config').get('l1dc_nways'),
            self.get('config').get('l1dc_nbytesperblock'),
            self.get('config').get('l1dc_evictionpolicy'),
        )})
    def do_tick(self, results, events, **kwargs):
        def contains_load_data(ld, st):
            retval  = ld.get('operands').get('addr') >= st.get('operands').get('addr')
            retval &= ld.get('operands').get('addr') + ld.get('nbytes') <= st.get('operands').get('addr') + len(st.get('operands').get('data'))
            return retval
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        self.get('pending_execute').clear()
        for _retire in map(lambda y: y.get('retire'), filter(lambda x: x.get('retire'), results)):
            if _retire:
                _ndx = next(filter(lambda x: _retire.get('iid') == self.get('pending_execute')[x].get('iid'), range(len(self.get('pending_execute')))), None)
                if not isinstance(_ndx, int): continue
                logging.info(os.path.basename(__file__) + ': _retire : {}'.format(_retire))
                self.get('pending_execute')[_ndx].update({'retired': True})
        for _l2 in filter(lambda x: x, map(lambda y: y.get('l2'), results)):
            _addr = _l2.get('addr')
            if _addr not in self.get('pending_fetch'): continue
            if not 'data' in _l2.keys(): continue # b/c lower levels in the cache hierarchy report POKE oeprations
            logging.info(os.path.basename(__file__) + ': _l2 : {}'.format(_l2))
            self.get('l1dc').poke(_addr, _l2.get('data'))
            self.get('pending_fetch').remove(_addr)
        for _mmu in map(lambda y: y.get('mmu'), filter(lambda x: x.get('mmu'), results)):
            _vaddr = _mmu.get('vaddr')
            _pagesize = self.get('config').get('pagesize')
            _frame = components.simplemmu.frame(_pagesize, _vaddr)
            if _frame not in self.get('pending_v2p'): continue
            self.update({'pending_v2p': list(filter(lambda x: _frame != x, self.get('pending_v2p')))})
            self.get('tlb').update({_frame: _mmu.get('frame')})
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for _lsu in map(lambda y: y.get('lsu'), filter(lambda x: x.get('lsu'), events)):
            if 'insn' in _lsu.keys():
                _insn = _lsu.get('insn')
                _vaddr = _insn.get('operands').get('addr')
                _pagesize = self.get('config').get('pagesize')
                _frame = components.simplemmu.frame(_pagesize, _vaddr)
                if _frame not in self.get('tlb').keys():
                    self.get('pending_v2p').append(_frame)
                    self.service.tx({'event': {
                        'arrival': 1 + self.get('cycle'),
                        'coreid': self.get('coreid'),
                        'mmu': {
                            'cmd': 'v2p',
                            'vaddr': _vaddr,
                        }
                    }})
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
                    _pending_stores = list(filter(lambda y: y.get('cmd') in riscv.constants.STORES, self.get('pending_execute')))
                    _store = next(filter(lambda s: contains_load_data(_insn, s), reversed(_pending_stores)), None)
                    logging.info('LSU.do_tick(): {} ?<- _pending_stores : {} ({}){}'.format(
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
                self.get('pending_execute').append(_insn)
            elif 'cmd' in _lsu.keys() and 'purge' == _lsu.get('cmd'):
                self.get('l1dc').purge()
        logging.info(os.path.basename(__file__) + ': state.executing       : {} ({})'.format(list(map(lambda x: [x.get('cmd'), x.get('iid'), x.get('operands').get('addr')], self.get('executing'))), len(self.get('executing'))))
        logging.info(os.path.basename(__file__) + ': state.pending_execute : {} ({})'.format(list(map(lambda x: [x.get('cmd'), x.get('iid'), x.get('operands').get('addr')], self.get('pending_execute'))), len(self.get('pending_execute'))))
        do_execute(self.service, self)
