# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import subprocess

import service
import toolbox
import toolbox.stats
import riscv.constants

import components.simplecore
import brpred
import fetch
import decode
import issue
import regfile
import alu
import lsu
import commit
import watchdog


class Core(components.simplecore.SimpleCore):
    def __init__(self, name, coreid, launcher, s=None):
        super().__init__(name, coreid, launcher, s)
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.internal.update({'result_names': ['recovery_iid', 'flush', 'retire', 'forward', 'register', 'mispredict', 'prediction', 'l1ic', 'l1dc']})
        self.internal.update({'event_names': ['perf', 'shutdown', 'fetch', 'decode', 'issue', 'register', 'alu', 'lsu', 'commit']})
        self.components = {
            k:v(k, self.coreid, launcher, self.internal.get('service'))
            for k, v in [
                ('watchdog', watchdog.Watchdog),
                ('brpred', brpred.BranchPredictor),
                ('fetch', fetch.Fetch),
                ('decode', decode.Decode),
                ('issue', issue.Issue),
                ('regfile', regfile.SimpleRegisterFile),
                ('alu', alu.ALU),
                ('lsu', lsu.LSU),
                ('commit', commit.Commit),
            ]
        }
        self.config = {}
    def __repr__(self):
        return '[{}] {}'.format(self.coreid, ', '.join(map(lambda x: '{}: {}'.format(x, self.get(x)), [
            'cycle',
            'active', 'running', 'ack',
            'config',
        ])))
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)
    def boot(self):
        for c in filter(lambda x: 'boot' in dir(x), self.components.values()): c.boot()
    def do_results(self, results):
        logging.debug('Core.do_results(self, {}): ...'.format(results))
        _service = self.internal.get('service')
    def do_events(self, events):
        logging.debug('Core.do_events(self, {}): ...'.format(events))
        _service = self.internal.get('service')
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for _shutdown in map(lambda y: y.get('shutdown'), filter(lambda x: x.get('shutdown'), events)):
            assert _shutdown
            _service.tx({'shutdown': {
                'coreid': self.get('coreid'),
            }})
    def do_tick(self, results, events):
        logging.debug('Core.do_tick(): {} {}'.format(results, events))
        _futures = self.futures.get(self.cycle, {'results': [], 'events': []})
        _futures.update({'results': _futures.get('results') + list(results)})
        _futures.update({'events': _futures.get('events') + list(events)})
        self.futures.update({self.cycle: _futures})
        _service = self.internal.get('service')
        while True:
            logging.info('@{:15}'.format(self.cycle))
            logging.info('Core.futures : {}'.format(self.futures))
            _res_evt = self.futures.pop(self.cycle, {'results': [], 'events': []})
            for c in self.components.values(): c.do_tick(_res_evt.get('results'), _res_evt.get('events'), cycle=self.cycle)
            self.do_results(_res_evt.get('results'))
            self.do_events(_res_evt.get('events'))
            logging.debug('Core.internal.service.fifo : {}'.format(self.internal.get('service').fifo))
            logging.debug('Core.futures : {}'.format(self.futures))
            logging.debug('Core.service.fifo [ante] : {}'.format(_service.fifo))
            self.handle()
            logging.debug('Core.futures : {}'.format(self.futures))
            logging.debug('Core.service.fifo [post] : {}'.format(_service.fifo))
            if len(_service.fifo):
                while len(_service.fifo): self.service.tx(_service.fifo.pop(0))
                if len(self.futures.keys()): self.service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'ping': True,
                }})
                break
            if 0 == len(self.futures.keys()): break
            self.cycle = min(self.futures.keys())
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
    state = Core('hyuganatsu', args.coreid, _launcher)
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
                state.update({'futures': {}})
                state.update({'stats': toolbox.stats.CounterBank(state.get('coreid'), state.get('name'))})
#                for c in filter(lambda x: 'boot' in dir(x), state.components.values()): c.boot()
#                state.components.get('brpred').boot()
#                if not state.get('config').get('toolchain'): continue
#                _toolchain = state.get('config').get('toolchain')
#                _binary = state.get('binary')
#                _files = next(iter(list(os.walk(_toolchain))))[-1]
#                _objdump = next(filter(lambda x: 'objdump' in x, _files))
#                _x = subprocess.run('{} -t {}'.format(os.path.join(_toolchain, _objdump), _binary).split(), capture_output=True)
#                if len(_x.stderr): continue
#                _objdump = _x.stdout.decode('ascii').split('\n')
#                _objdump = sorted(filter(lambda x: len(x), _objdump))
#                _objdump = filter(lambda x: re.search('^0', x), _objdump)
#                _objdump = map(lambda x: x.split(), _objdump)
#                state.update({'objmap': {
#                    int(x[0], 16): {
#                        'flags': x[1:-1],
#                        'name': x[-1]
#                    } for x in _objdump
#                }})
                state.boot()
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'binary' == k:
                state.update({'binary': v})
            elif 'config' == k:
                logging.info('config : {}'.format(v))
#                _components = {
#                    'watchdog': state.components.get('watchdog'),
#                    'brpred': state.components.get('brpred'),
#                    'fetch': state.components.get('fetch'),
#                    'regfile': state.components.get('regfile'),
#                    state.get('name'): state,
#                }
                _components = {**state.components, **{state.get('name'): state}}
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
                _brpred = state.components.get('brpred')
                _decode = state.components.get('decode')
                if 'set' == _cmd:
                   _regfile.update({'registers': _regfile.setregister(_regfile.get('registers'), _name, v.get('data'))})
                   if '%pc' == _name:
                       _brpred.update({_name: v.get('data')})
                       _decode.update({_name: v.get('data')})
                elif 'get' == _cmd:
                    _ret = _regfile.getregister(_regfile.get('registers'), _name)
                    state.service.tx({'result': {'register': _ret}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
