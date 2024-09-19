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
import decode
import regfile
import execute
import watchdog


class InternalService:
    def __init__(self):
        self.fifo = []
    def tx(self, msg): self.fifo.append(msg)
    def rx(self): pass
    def reset(self): self.fifo = []
    def __iter__(self): return iter(self.fifo)
    def __len__(self): return len(self.fifo)
    def pop(self, x): return self.fifo.pop(x)
class Core(dict):
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if not s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.pending_pc = False
        self.pending_fetch = None
        self.pending_decode = False
        self.pending_execute = None
        self.iid = 0
        self.internal = {
            'service': InternalService(),
            'event_names': ['perf', 'shutdown', 'decode', 'register', 'execute', 'complete', 'confirm', 'commit'],
            'result_names': ['register', 'insn'],
        }
        logging.info('core.service  : {}'.format(self.service))
        logging.info('Core.internal : {}'.format(self.internal))
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
        self.futures = {}
        self.objmap = None
        self.config = {
            'toolchain': '',
            'binary': '',
        }
    def __repr__(self):
        return '[{}] {}'.format(self.coreid, ', '.join(map(lambda x: '{}: {}'.format(x, self.get(x)), [
            'cycle',
            'pending_pc', 'pending_fetch', 'pending_decode', 'pending_execute',
            'active', 'running', 'ack',
            'objmap', 'config',
        ])))
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
    def handle(self):
        _service = self.internal.get('service')
        _fifo = []
        while len(self.internal.get('service')):
            _msg = self.internal.get('service').pop(0)
            _channel, _payload = next(iter(_msg.items()))
            logging.debug('SimpleCore.handle(): {} {}'.format(_channel, _payload))
            if not isinstance(_payload, dict):
                _fifo.append(_msg)
                continue
            assert 'arrival' in _payload.keys(), '_channel : {}, _payload : {}'.format(_channel, _payload)
            _arr = _payload.pop('arrival')
            _coreid = _payload.pop('coreid')
            logging.debug('SimpleCore.handle(): {} {} {}'.format(_arr, _coreid, _payload))
            logging.debug('SimpleCore.handle(): {}'.format(next(iter(_payload.keys())) in self.internal.get('result_names')))
            logging.debug('SimpleCore.handle(): futures : {}'.format(self.futures))
            assert _arr > self.cycle, 'Attempting to schedule arrival in the past ({} vs. {})'.format(self.cycle, _arr)
            if 'result' == _channel and next(iter(_payload.keys())) in self.internal.get('result_names'):
                _res_evt = self.futures.get(_arr, {'results': [], 'events': []})
                _res_evt.get('results').append(_payload)
                self.futures.update({_arr: _res_evt})
            elif 'event' == _channel and next(iter(_payload.keys())) in self.internal.get('event_names'):
                _res_evt = self.futures.get(_arr, {'results': [], 'events': []})
                _res_evt.get('events').append(_payload)
                self.futures.update({_arr: _res_evt})
            else:
                _fifo.append({_channel: {**{'arrival': _arr, 'coreid': _coreid}, **_payload}})
            logging.debug('SimpleCore.handle(): futures : {}'.format(self.futures))
        _service.fifo = _fifo
    def do_results(self, results):
        logging.debug('SimpleCore.do_results(self, {}): ...'.format(results))
        _service = self.internal.get('service')
        for reg in map(lambda y: y.get('register'), filter(lambda x: x.get('register'), results)):
            if '%pc' != reg.get('name'): continue
            self.update({'%pc': reg.get('data')})
#            service.tx({'info': 'state.%pc : {}'.format(state.get('%pc'))})
            if 0 == int.from_bytes(self.get('%pc'), 'little'):
                self.service.tx({'info': 'Jump to @0x00000000... graceful shutdown'})
#                self.service.tx({'shutdown': {
#                    'coreid': self.get('coreid'),
#                }})
                _service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'shutdown': True,
                }})
            self.service.tx({'event': { # FIXME: _service.tx() even though 'mem' is handled OUTSIDE of SimpleCore
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
#            toolbox.report_stats(service, state, 'flat', 'fetches')
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
                **({'function': next(filter(lambda x: int.from_bytes(insn.get('%pc'), 'little') >= x[0], sorted(self.get('objmap').items(), reverse=True)))[-1].get('name', '')} if state.get('objmap') else {}),
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
            self.service.tx({'shutdown': {
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
#            self.service.tx({'committed': 1}) # FIXME: _service.tx()
            logging.info('SimpleCore.do_events(): retiring : {}'.format(_insn))
    def do_tick(self, results, events):
        logging.info('SimpleCore.do_tick(): {} {}'.format(results, events))
        _futures = self.futures.get(self.cycle, {'results': [], 'events': []})
        _futures.update({'results': _futures.get('results') + list(results)})
        _futures.update({'events': _futures.get('events') + list(events)})
        self.futures.update({self.cycle: _futures})
        _service = self.internal.get('service')
        while True:
            logging.info('@{:15}'.format(self.cycle))
            logging.info('SimpleCore.futures : {}'.format(self.futures))
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
            if len(_service):
                # FIXME: properly handle remaining _service.fifo items (e.g., {'info': XXX})
                for x in _service.fifo: self.service.tx(x)
                break
            if 0 == len(self.futures.keys()): break
            self.cycle = min(self.futures.keys())
        self.service.tx({'info': 'state.pending_pc      : {} ({})'.format(self.pending_pc, self.get('pending_pc'))})
        self.service.tx({'info': 'state.pending_fetch   : {} ({})'.format(self.pending_fetch, self.get('pending_fetch'))})
        self.service.tx({'info': 'state.pending_decode  : {} ({})'.format(self.pending_decode, self.get('pending_decode'))})
        self.service.tx({'info': 'state.pending_execute : {} ({})'.format(self.pending_execute, self.get('pending_execute'))})
        self.internal.get('service').reset()

        

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
#    state = {
#        'service': 'simplecore',
#        'cycle': 0,
#        'coreid': args.coreid,
#        'active': True,
#        'running': False,
#        'pending_pc': False,
#        'pending_fetch': None,
#        'pending_decode': False,
#        'pending_execute': None,
#        'stats': None,
#        'iid': 0,
#        '%pc': None,
#        'ack': True,
#        'objmap': None,
#        'core': Core('simplecore', args.coreid, _launcher),
#        'config': {
#            'toolchain': '',
#            'binary': '',
#        },
#    }
#    _service = service.Service(state.get('service'), state.get('coreid'), _launcher.get('host'), _launcher.get('port'))
#    state.update({'core': Core('simplecore', args.coreid, _launcher)})
    state = Core('simplecore', args.coreid, _launcher)
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
                if not state.get('config').get('toolchain'): continue
                _toolchain = state.get('config').get('toolchain')
                _binary = state.get('binary')
                _files = next(iter(list(os.walk(_toolchain))))[-1]
                _objdump = next(filter(lambda x: 'objdump' in x, _files))
                _x = subprocess.run('{} -t {}'.format(os.path.join(_toolchain, _objdump), _binary).split(), capture_output=True)
                if len(_x.stderr): continue
                _objdump = _x.stdout.decode('ascii').split('\n')
                _objdump = sorted(filter(lambda x: len(x), _objdump))
                _objdump = filter(lambda x: re.search('^0', x), _objdump)
                _objdump = map(lambda x: x.split(), _objdump)
                state.update({'objmap': {
                    int(x[0], 16): {
                        'flags': x[1:-1],
                        'name': x[-1]
                    } for x in _objdump
                }})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'binary' == k:
                state.update({'binary': v})
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
#                if state.get('service') != v.get('service'): continue
#                _field = v.get('field')
#                _val = v.get('val')
#                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
#                state.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
                state.do_tick(_results, _events)
#                do_tick(_service, state, _results, _events)
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
