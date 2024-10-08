# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import itertools
import logging
import time

import service
import toolbox
import toolbox.stats
import riscv.constants

class SaturatingCounter:
    def __init__(self, nbit = 2):
        self.nbit = nbit
        self.count = 0
    def add(self, n):
        self.count += n
        self.count = (self.count if self.count < (1 << self.nbit) else ((1 << self.nbit) - 1))
        self.count = (self.count if self.count >= 0 else 0)
    def __repr__(self):
        return ('{' + ':0{}b'.format(self.nbit) + '}').format(self.count)
class CounterTablePredictor:
    def __init__(self, kind, ncounter, nbit = 2):
        assert kind in ['gshare', 'bimodal'], 'kind must be either "gshare" or "bimodal"'
        assert 0 == (ncounter & (ncounter - 1)), 'ncounter must be a power of 2'
        self.kind = kind
        self.ncounter = ncounter
        self.nbit = nbit
        self.countertable = [SaturatingCounter(self.nbit) for _ in range(self.ncounter)]
        self.history = 0
    def index(self, addr): return (self.history ^ (addr >> 1)) & (self.ncounter - 1)
    def istaken(self, addr): return 1 == (self.countertable[self.index(addr)].count >> (self.nbit - 1))
    def update(self, addr, taken):
        logging.debug('update({:8x}, {})'.format(addr, taken))
        logging.debug('self.history         : {:b}'.format(self.history))
        logging.debug('self.countertable[{}] : {}'.format(self.index(addr), self.countertable[self.index(addr)]))
        self.countertable[self.index(addr)].add(1 if taken else -1)
        logging.debug('self.countertable[{}] : {}'.format(self.index(addr), self.countertable[self.index(addr)]))
        self.history <<= 1
        self.history |= (0 if not taken or 'bimodal' == self.kind else 1)
        self.history &= ((1 << self.nbit) - 1)
    def __repr__(self):
        return '[' + ','.join(['{:4}: {}'.format(x, y) for x, y in enumerate(self.countertable)]) + ']'
class BranchTargetAddressCache:
    def __init__(self, nentry):
        assert 0 == (nentry & (nentry - 1)), 'nentry must be power of 2'
        self.nentry = nentry
        self.cache = {}
        self.lru = []
    def get(self, k, default=None): return self.cache.get(k, default)
    def keys(self): return self.cache.keys()
    def pop(self, k, default=None):
        _retval = self.cache.pop(k, None)
        if _retval: self.lru.remove(k)
        return (default if not _retval else _retval)
    def update(self, d):
        _k, _ = next(iter(d.items()))
        if _k in self.cache.keys():
            self.cache.pop(_k)
            self.lru.remove(_k)
        self.cache.update(d)
        self.lru.insert(0, _k)
        if len(self.keys()) > self.nentry: self.cache.pop(self.lru.pop(-1))
    def items(self): return self.cache.items()
    def __len__(self): return len(self.lru)
    def __repr__(self):
        return '[' + ','.join([str({x: self.cache.get(x)}) for x in self.lru]) + ']' + ' ({})'.format(len(self.lru))

class BranchPredictor:
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.fetch_address = []
        self.pending_fetch = None
        self.predictor = None
        self.btac = None
        self.drop_until = None
        self.config = {
            'btac_entries': None,
            'predictor_type': None, # 'bimodal', 'gshare'
            'predictor_entries': None,
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
        self.update({'pending_fetch': None})
        self.update({'fetch_address': [{'fetch': {
            'cmd': 'get',
            'addr': int.from_bytes(self.get('%pc'), 'little'),
        }}]})
        self.update({'drop_until': None})
        self.update({'%jp': None})
        if self.get('config').get('btac_entries'): self.update({'btac': BranchTargetAddressCache(self.get('config').get('btac_entries'))})
        if self.get('config').get('predictor_type') and self.get('config').get('predictor_entries'): self.update({'predictor': CounterTablePredictor(
            self.get('config').get('predictor_type'),
            self.get('config').get('predictor_entries'),
        )})
    def do_tick(self, results, events, **kwargs):
        def contains(a0, s0, a1, s1):
            return (False if not isinstance(a1, int) else all(map(lambda x: x in range(*itertools.accumulate((a0, s0))), [a1, a1+s1-1])))
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        logging.debug('@{:15}'.format(self.cycle))
        logging.debug('BranchPredictor.do_tick({}, {}, {})'.format(results, events, kwargs))
        logging.debug('BranchPredictor.do_tick(): self.pending_fetch : {}'.format(self.pending_fetch))
        logging.debug('BranchPredictor.do_tick(): self.fetch_address : {}'.format(self.fetch_address))
        _btac = self.get('btac')
        for _flush, _retire in map(lambda y: (y.get('flush'), y.get('retire')), filter(lambda x: x.get('flush') or x.get('retire'), results)):
            if _retire:
                if not _retire.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS: continue
                logging.info(os.path.basename(__file__) + ': retiring : {}'.format(_retire))
                _pc = int.from_bytes(_retire.get('%pc'), 'little')
                if isinstance(_btac, BranchTargetAddressCache):
                    if not _pc in _btac.keys(): _btac.update({_pc: {'size': _retire.get('size'), 'targetpc': _pc + _retire.get('size')}})
                    if _retire.get('taken'): _btac.update({_pc: {**_btac.get(_pc), **{'targetpc': int.from_bytes(_retire.get('next_pc'), 'little')}}})
                if self.get('predictor'): self.get('predictor').update(_pc, _retire.get('taken'))
            if _flush:
                if not _flush.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS: continue
                logging.info(os.path.basename(__file__) + ': flushing : {}'.format(_flush))
                if _btac: _btac.pop(int.from_bytes(_flush.get('%pc'), 'little'), None)
        if next(filter(lambda x: x.get('mispredict'), results), None):
            for _mispr in map(lambda y: y.get('mispredict'), filter(lambda x: x.get('mispredict'), results)):
                logging.debug('BranchPredictor.do_tick(): _mispr : {}'.format(_mispr))
                logging.info(os.path.basename(__file__) + ': _mispr : {}'.format(_mispr))
                _insn = _mispr.get('insn')
                if 'branch' == _insn.get('prediction').get('type'):
                    self.get('fetch_address').clear()
                    self.get('fetch_address').append({
                        'fetch': {
                            'cmd': 'get',
                            'addr': int.from_bytes(_insn.get('next_pc'), 'little')
                        }
                    })
                    self.update({'drop_until': int.from_bytes(_insn.get('next_pc'), 'little')})
                    self.get('stats').refresh('flat', 'mispredictions')
                self.update({'pending_fetch': None})
        else:
            for _l1ic in map(lambda y: y.get('l1ic'), filter(lambda x: x.get('l1ic'), results)):
                logging.debug('BranchPredictor.do_tick(): _l1ic : {}'.format(_l1ic))
                assert _l1ic.get('addr') == self.get('pending_fetch').get('fetch').get('addr'), '_l1ic : {} ; self.pending_fetch : {}'.format(_l1ic, self.get('pending_fetch'))
                self.update({'pending_fetch': None})
                if self.get('drop_until') and _l1ic.get('addr') != self.get('drop_until'): continue
                self.update({'drop_until': None})
                _br = (next(filter(lambda x: contains(_l1ic.get('addr'), _l1ic.get('size'), x[0], x[1].get('size')), _btac.items()), None) if _btac else None)
                _br = (dict([_br]) if _br else None)
                _brpc, _pr = (next(iter(_br.items())) if _br else (None, None))
                if _br and (self.get('predictor').istaken(_brpc) if self.get('predictor') else True):
                    logging.info(os.path.basename(__file__) + ': _br : {}'.format(_br))
                    self.service.tx({'result': {
                        'arrival': 1 + self.get('cycle'),
                        'coreid': self.get('coreid'),
                        'prediction': {
                            'type': 'branch',
                            'branchpc': _brpc,
                            **_pr,
                        }
                    }})
                    if _pr.get('targetpc') != _brpc + _pr.get('size') and not contains(_l1ic.get('addr'), _l1ic.get('size'), _pr.get('targetpc'), 0): # i.e., if the branch is predicted taken and no portion of _br \in _l1ic
                        self.get('fetch_address').append({
                            'fetch': {
                                'cmd': 'get',
                                'addr': _pr.get('targetpc'),
                            }
                        })
                        self.get('stats').refresh('flat', 'predict_taken')
                self.get('stats').refresh('flat', 'predictions')
                if not len(self.get('fetch_address')):
                    self.get('fetch_address').append({
                        'fetch': {
                            'cmd': 'get',
                            'addr': _l1ic.get('addr') + _l1ic.get('size'),
                        }
                    })
        logging.debug('BranchPredictor.do_tick(): self.pending_fetch : {}'.format(self.pending_fetch))
        logging.debug('BranchPredictor.do_tick(): self.fetch_address : {}'.format(self.fetch_address))
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        if not self.get('pending_fetch') and len(self.get('fetch_address')):
            self.update({'pending_fetch': self.get('fetch_address').pop(0)})
            self.service.tx({'event': {
                'arrival': 1 + self.get('cycle'),
                'coreid': self.get('coreid'),
                **self.get('pending_fetch'),
            }})
        logging.info(os.path.basename(__file__) + ': state.pending_fetch       : {}'.format(self.get('pending_fetch')))
        logging.info(os.path.basename(__file__) + ': state.fetch_address         : {} ({})'.format(self.get('fetch_address'), len(self.get('fetch_address'))))
        logging.info(os.path.basename(__file__) + ': state.predictor             : {}'.format(self.get('predictor')))
        logging.info(os.path.basename(__file__) + ': state.btac                  : {}'.format(self.get('btac')))
        logging.info(os.path.basename(__file__) + ': state.drop_until            : {}'.format('' if not self.get('drop_until') else list(self.get('drop_until').to_bytes(8, 'little')), self.get('drop_until')))
        logging.info(os.path.basename(__file__) + ':  filter(mispredict, results) : {}'.format(len(list(filter(lambda x: x.get('mispredict'), results)))))
