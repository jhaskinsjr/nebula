# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time

import service
import toolbox
import toolbox.stats
import riscv.constants
import components.simplecore
import decode
import regfile
import execute
import watchdog


class Core(components.simplecore.SimpleCore):
    def __init__(self, name, coreid, launcher, s=None):
        super().__init__(name, coreid, launcher, s)
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.pending_pc = False
        self.pending_fetch = None
        self.pending_decode = False
        self.pending_execute = None
        self.iid = 0
        self.internal.update({'event_names': ['perf', 'shutdown', 'decode', 'register', 'execute', 'complete', 'confirm', 'commit']})
        self.internal.update({'result_names': ['register', 'insn']})
        self.components = {
            'decode': decode.Decode('decode', self.coreid, launcher, self.internal.get('service')),
            'regfile': regfile.SimpleRegisterFile('regfile', self.coreid, launcher, self.internal.get('service')),
            'execute': execute.Execute('execute', self.coreid, launcher, self.internal.get('service')),
            'watchdog': watchdog.Watchdog('watchdog', self.coreid, launcher, self.internal.get('service')),
        }
        logging.info('Core.components.decode.service  : {}'.format(self.components.get('decode').get('service')))
        logging.info('Core.components.regfile.service : {}'.format(self.components.get('regfile').get('service')))
        logging.info('Core.components.execute.service : {}'.format(self.components.get('execute').get('service')))
        logging.info('Core.components.watchdog.service : {}'.format(self.components.get('watchdog').get('service')))
    def __repr__(self):
        return '[{}] {}'.format(self.coreid, ', '.join(map(lambda x: '{}: {}'.format(x, self.get(x)), [
            'cycle',
            'pending_pc', 'pending_fetch', 'pending_decode', 'pending_execute',
            'active', 'running', 'ack',
        ])))
    def boot(self):
        for c in filter(lambda x: 'boot' in dir(x), self.components.values()): c.boot()
    def do_results(self, results):
        logging.debug('SimpleCore.do_results(self, {}): ...'.format(results))
        _service = self.internal.get('service')
        for reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
            if '%pc' != reg.get('name'): continue
            self.update({'%pc': reg.get('data')})
            if 0 == int.from_bytes(self.get('%pc'), 'little'):
                _service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
                _service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'shutdown': True,
                }})
            _service.tx({'event': {
                'arrival': 1 + self.get('cycle'),
                'coreid': self.get('coreid'),
                'mem': {
                    'cmd': 'peek',
                    'addr': int.from_bytes(self.get('%pc'), 'little'),
                    'size': 4,
                },
            }})
            self.update({'pending_fetch': int.from_bytes(self.get('%pc'), 'little')})
            self.update({'pending_pc': False})
            self.get('stats').refresh('flat', 'fetches')
        for mem in map(lambda y: y.get('mem'), filter(lambda x: x.get('mem'), results)):
            if mem.get('addr') != self.get('pending_fetch'): continue
            self.update({'pending_fetch': None})
            self.update({'pending_decode': True})
            _service.tx({'event': {
                'arrival': 1 + self.get('cycle'),
                'coreid': self.get('coreid'),
                'decode': {
                    'bytes': mem.get('data'),
                    '%pc': self.get('%pc'),
                },
            }})
        for insn in map(lambda y: y.get('insn'), filter(lambda x: x.get('insn'), results)):
            self.update({'pending_decode': False})
            _insn = {
                **insn,
                **{'iid': self.get('iid')},
            }
            self.update({'pending_execute': _insn})
            _service.tx({'event': {
                'arrival': 1 + self.get('cycle'),
                'coreid': self.get('coreid'),
                'execute': {
                    'insn': _insn,
                }
            }})
            self.update({'iid': 1 + self.get('iid')})
    def do_events(self, events):
        logging.debug('SimpleCore.do_events(self, {}): ...'.format(events))
        _service = self.internal.get('service')
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('service'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for _shutdown in map(lambda y: y.get('shutdown'), filter(lambda x: x.get('shutdown'), events)):
            assert _shutdown
            _service.tx({'shutdown': {
                'coreid': self.get('coreid'),
            }})
        for complete in map(lambda y: y.get('complete'), filter(lambda x: x.get('complete'), events)):
            _insn = complete.get('insn')
            assert _insn.get('iid') == self.get('pending_execute').get('iid'), '_insn : {} != state.pending_execute : {}'.format(_insn, self.get('pending_execute'))
            _jump = _insn.get('cmd') in riscv.constants.JUMPS
            _taken = _insn.get('taken')
            if not _jump and not _taken:
                _pc = int.from_bytes(_insn.get('%pc'), 'little')
                self.update({'%pc': riscv.constants.integer_to_list_of_bytes(_pc + _insn.get('size'), 64, 'little')})
                _service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'register': {
                        'cmd': 'set',
                        'name': '%pc',
                        'data': self.get('%pc'),
                    }
                }})
                self.update({'%pc': _pc})
            self.update({'pending_execute': None})
        for commit in map(lambda y: y.get('commit'), filter(lambda x: x.get('commit'), events)):
            _insn = commit.get('insn')
            if _insn.get('shutdown'):
                _insn.update({'operands': {int(k):v for k, v in _insn.get('operands').items()}})
                _x17 = _insn.get('operands').get(17)
                _service.tx({'info': 'ECALL {}... graceful shutdown'.format(int.from_bytes(_x17, 'little'))})
                _service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'perf': {
                        'cmd': 'report_stats',
                    },
                }})
                _service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'shutdown': True,
                }})
            _service.tx({'committed': 1})
            logging.debug('SimpleCore.do_events(): retiring : {}'.format(_insn))
    def do_tick(self, results, events):
        logging.debug('SimpleCore.do_tick(): {} {}'.format(results, events))
        _futures = self.futures.get(self.cycle, {'results': [], 'events': []})
        _futures.update({'results': _futures.get('results') + list(results)})
        _futures.update({'events': _futures.get('events') + list(events)})
        self.futures.update({self.cycle: _futures})
        _service = self.internal.get('service')
        while True:
            logging.debug('@{:15}'.format(self.cycle))
            logging.debug('SimpleCore.futures : {}'.format(self.futures))
            _res_evt = self.futures.pop(self.cycle, {'results': [], 'events': []})
            for c in self.components.values(): c.do_tick(_res_evt.get('results'), _res_evt.get('events'), cycle=self.cycle)
            self.do_results(_res_evt.get('results'))
            self.do_events(_res_evt.get('events'))
            logging.debug('SimpleCore.internal.service.fifo : {}'.format(self.internal.get('service').fifo))
            logging.debug('SimpleCore.futures : {}'.format(self.futures))
            logging.debug('SimpleCore.service.fifo [ante] : {}'.format(_service.fifo))
            if all(map(lambda x: not self.get(x), ['pending_pc', 'pending_fetch', 'pending_decode', 'pending_execute'])):
                _service.tx({'event': {
                    'arrival': 1 + self.cycle,
                    'coreid': self.coreid,
                    'register': {
                        'cmd': 'get',
                        'name': '%pc',
                    }
                }})
                self.update({'pending_pc': True})
            self.handle()
            logging.debug('SimpleCore.futures : {}'.format(self.futures))
            logging.debug('SimpleCore.service.fifo [post] : {}'.format(_service.fifo))
            while len(_service.fifo): self.service.tx(_service.fifo.pop(0))
            if 0 == len(self.futures.keys()): break
            self.cycle = min(self.futures.keys())
        self.service.tx({'info': 'state.pending_pc      : {} ({})'.format(self.pending_pc, self.get('pending_pc'))})
        self.service.tx({'info': 'state.pending_fetch   : {} ({})'.format(self.pending_fetch, self.get('pending_fetch'))})
        self.service.tx({'info': 'state.pending_decode  : {} ({})'.format(self.pending_decode, self.get('pending_decode'))})
        self.service.tx({'info': 'state.pending_execute : {} ({})'.format(self.pending_execute, self.get('pending_execute'))})
        _service.clear()
        

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Simple Core')
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
    state = Core('etrog', args.coreid, _launcher)
    _service = state.service
    logging.info('state : {}'.format(state))
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
                state.update({'pending_pc': False})
                state.update({'pending_fetch': None})
                state.update({'pending_decode': False})
                state.update({'pending_execute': None})
                state.update({'futures': {}})
                state.update({'stats': toolbox.stats.CounterBank(state.get('coreid'), state.get('service'))})
                state.update({'%pc': None})
                state.boot()
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'binary' == k:
                state.components.get('decode').update({'binary': v})
            elif 'config' == k:
                logging.info('config : {}'.format(v))
                _components = {
                    'regfile': state.components.get('regfile'),
                    'decode': state.components.get('decode'),
                    'execute': state.components.get('execute'),
                    'watchdog': state.components.get('watchdog'),
                    state.get('name'): state,
                }
                if v.get('service') not in _components.keys(): continue
                _target = _components.get(v.get('service'))
                _field = v.get('field')
                _val = v.get('val')
                assert _field in _target.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, v.get('service'))
                _target.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
                state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'register' == k:
                logging.info('register : {}'.format(v))
                if not state.get('coreid') == v.get('coreid'): continue
                _cmd = v.get('cmd')
                _name = v.get('name')
                _regfile = state.components.get('regfile')
                if 'set' == _cmd:
                   _regfile.update({'registers': _regfile.setregister(_regfile.get('registers'), _name, v.get('data'))})
                elif 'get' == _cmd:
                    _ret = _regfile.getregister(_regfile.get('registers'), _name)
                    state.service.tx({'result': {'register': _ret}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
