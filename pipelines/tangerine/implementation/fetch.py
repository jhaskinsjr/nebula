# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import toolbox.stats
import components.simplecache
import components.simplemmu
import riscv.constants


class Fetch:
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.l1ic = None
        self.pending_v2p = []
        self.pending_fetch = []
        self.fetch_buffer = []
        self.mispredict = None
        self.config = {
            'l1ic_nsets': 2**4,
            'l1ic_nways': 2**1,
            'l1ic_nbytesperblock': 2**4,
            'l1ic_evictionpolicy': 'lru',
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
        self.update({'mispredict': None})
        self.update({'fetch_buffer': []})
        self.update({'l1ic': components.simplecache.SimpleCache(
                    self.get('config').get('l1ic_nsets'),
                    self.get('config').get('l1ic_nways'),
                    self.get('config').get('l1ic_nbytesperblock'),
                    self.get('config').get('l1ic_evictionpolicy'),
                )})
    def fetch_block(self, jp, physical):
        _blockaddr = self.get('l1ic').blockaddr(jp)
        _blocksize = self.get('l1ic').nbytesperblock
        logging.info(os.path.basename(__file__) + ': fetch_block(..., {} ({:08x}))'.format(jp, _blockaddr))
        self.get('pending_fetch').append(_blockaddr)
        self.service.tx({'event': {
            'arrival': 1 + self.get('cycle'),
            'coreid': self.get('coreid'),
            'l2': {
                'cmd': 'peek',
                'addr': _blockaddr,
                'size': _blocksize,
                'physical': physical,
            },
        }})
        self.get('stats').refresh('flat', 'l1ic_misses')
    def do_l1ic(self):
        _req = self.get('fetch_buffer')[0]
        logging.debug('_req : {}'.format(_req))
        _vaddr = _req.get('addr')
        _pagesize = self.get('config').get('pagesize')
        _frame = components.simplemmu.frame(_pagesize, _vaddr)
        if _frame not in self.get('tlb').keys(): return
        _jp = self.get('tlb').get(_frame) | components.simplemmu.offset(_pagesize, _vaddr)
        _physical = True
        logging.info(os.path.basename(__file__) + ': _jp : {} ({})'.format(list(_jp.to_bytes(8, 'little')), _jp))
        _blockaddr = self.get('l1ic').blockaddr(_jp)
        _blocksize = self.get('l1ic').nbytesperblock
        _data = self.get('l1ic').peek(_blockaddr, _blocksize)
        logging.info(os.path.basename(__file__) + ': _data : {}'.format(_data))
        if not _data:
            if len(self.get('pending_fetch')): return # only 1 pending fetch at a time is primitive, but good enough for now
            self.fetch_block(_jp, _physical)
            return
        _data = _data[(_jp - _blockaddr):]
        self.service.tx({'result': {
            'arrival': 1 + self.get('cycle'),
            'coreid': self.get('coreid'),
            'l1ic': {
                'addr': _vaddr,
                'size': len(_data),
                'data': _data,
            },
        }})
        self.service.tx({'event': {
            'arrival': 1 + self.get('cycle'),
            'coreid': self.get('coreid'),
            'decode': {
                'addr': _vaddr,
                'data': _data,
            },
        }})
        self.get('fetch_buffer').pop(0)
        self.get('stats').refresh('flat', 'l1ic_accesses')
    def do_results(self, results):
        for _mispr in map(lambda y: y.get('mispredict'), filter(lambda x: x.get('mispredict'), results)):
            logging.info(os.path.basename(__file__) + ': _mispr : {}'.format(_mispr))
            self.get('pending_fetch').clear()
            self.get('fetch_buffer').clear()
            self.update({'mispredict': _mispr})
        for _l2 in map(lambda y: y.get('l2'), filter(lambda x: x.get('l2'), results)):
            _addr = _l2.get('addr')
            if _addr not in self.get('pending_fetch'): continue
            logging.info(os.path.basename(__file__) + ': _l2 : {}'.format(_l2))
            self.get('l1ic').poke(_addr, _l2.get('data'))
            self.get('pending_fetch').remove(_addr)
        for _mmu in map(lambda y: y.get('mmu'), filter(lambda x: x.get('mmu'), results)):
            _vaddr = _mmu.get('vaddr')
            _pagesize = self.get('config').get('pagesize')
            _frame = components.simplemmu.frame(_pagesize, _vaddr)
            if _frame not in self.get('pending_v2p'): continue
            self.update({'pending_v2p': list(filter(lambda x: _frame != x, self.get('pending_v2p')))})
            self.get('tlb').update({_frame: _mmu.get('frame')})
    def do_events(self, events):
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for _fetch in map(lambda y: y.get('fetch'), filter(lambda x: x.get('fetch'), events)):
            if 'cmd' in _fetch.keys():
                if 'purge' == _fetch.get('cmd'):
                    self.get('l1ic').purge()
                    self.get('pending_fetch').clear()
                elif 'get' == _fetch.get('cmd'):
                    if self.get('mispredict'): continue
                    _vaddr = _fetch.get('addr')
                    self.get('fetch_buffer').append({
                        'addr': _vaddr,
                    })
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
    def do_tick(self, results, events, **kwargs):
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        self.update({'mispredict': None})
        self.do_results(results)
        self.do_events(events)
        logging.info(os.path.basename(__file__) + ': state.fetch_buffer : {}'.format(self.get('fetch_buffer')))
        if not len(self.get('fetch_buffer')): return
        self.do_l1ic()
