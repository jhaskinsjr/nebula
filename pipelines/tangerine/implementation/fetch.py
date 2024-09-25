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
#        self.update({'%jp': None})
        self.update({'l1ic': components.simplecache.SimpleCache(
                    self.get('config').get('l1ic_nsets'),
                    self.get('config').get('l1ic_nways'),
                    self.get('config').get('l1ic_nbytesperblock'),
                    self.get('config').get('l1ic_evictionpolicy'),
                )})
    def fetch_block(self, jp, physical):
        _blockaddr = self.get('l1ic').blockaddr(jp)
        _blocksize = self.get('l1ic').nbytesperblock
#        self.service.tx({'info': 'fetch_block(..., {} ({:08x}))'.format(jp, _blockaddr)})
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
#        toolbox.report_stats(service, state, 'flat', 'l1ic_misses')
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
#        self.service.tx({'info': '_jp : {} ({})'.format(list(_jp.to_bytes(8, 'little')), _jp)})
        logging.info(os.path.basename(__file__) + ': _jp : {} ({})'.format(list(_jp.to_bytes(8, 'little')), _jp))
        _blockaddr = self.get('l1ic').blockaddr(_jp)
        _blocksize = self.get('l1ic').nbytesperblock
        _data = self.get('l1ic').peek(_blockaddr, _blocksize)
#        self.service.tx({'info': '_data : {}'.format(_data)})
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
#        toolbox.report_stats(service, state, 'flat', 'l1ic_accesses')
        self.get('stats').refresh('flat', 'l1ic_accesses')
    def do_results(self, results):
        for _mispr in map(lambda y: y.get('mispredict'), filter(lambda x: x.get('mispredict'), results)):
#            self.service.tx({'info': '_mispr : {}'.format(_mispr)})
            logging.info(os.path.basename(__file__) + ': _mispr : {}'.format(_mispr))
            self.get('pending_fetch').clear()
            self.get('fetch_buffer').clear()
            self.update({'mispredict': _mispr})
        for _l2 in map(lambda y: y.get('l2'), filter(lambda x: x.get('l2'), results)):
            _addr = _l2.get('addr')
            if _addr not in self.get('pending_fetch'): continue
#            self.service.tx({'info': '_l2 : {}'.format(_l2)})
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
#        self.service.tx({'info': 'state.fetch_buffer : {}'.format(self.get('fetch_buffer'))})
        logging.info(os.path.basename(__file__) + ': state.fetch_buffer : {}'.format(self.get('fetch_buffer')))
        if not len(self.get('fetch_buffer')): return
        self.do_l1ic()
    

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
    state = Fetch('fetch', args.coreid, _launcher)
    _service = state.service
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
                state.boot()
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
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
                state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
#            elif 'register' == k:
#                logging.info('register : {}'.format(v))
#                if state.get('coreid') != v.get('coreid'): continue
#                if 'set' != v.get('cmd'): continue
#                if '%pc' != v.get('name'): continue
#                state.update({'%pc': v.get('data')})
#                logging.info('state : {}'.format(state))
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
    logging.info('state : {}'.format(state))
