# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import toolbox.stats
import riscv.constants
import riscv.decode

class Decode:
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        logging.debug('=== s : {}'.format(s))
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.buffer = []
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
    def do_tick(self, results, events, **kwargs):
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        logging.debug('Decode.do_tick(): {} {}'.format(results, events))
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for decode in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
            self.update({'buffer': decode.get('bytes')})
            self.service.tx({'info': 'state.buffer : {}'.format(self.get('buffer'))})
            for _insn in riscv.decode.do_decode(self.get('buffer'), 1): # HACK: hard-coded max-instructions-to-decode of 1
#                toolbox.report_stats(service, state, 'histo', 'decoded.insn', _insn.get('cmd'))
                self.get('stats').refresh('histo', 'decoded_insn', _insn.get('cmd'))
                self.service.tx({'result': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'insn': {**_insn, **{'%pc': decode.get('%pc')}},
                }})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Instruction Decode')
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
    state = Decode('decode', args.coreid, _launcher)
    while state.get('active'):
        state.update({'ack': True})
        msg = state.service.rx()
#        _service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif {'text': 'run'} == {k: v}:
                state.update({'running': True})
                state.update({'ack': False})
                state.update({'stats': toolbox.stats.CounterBank(state.get('coreid'), state.get('service'))})
                state.update({'buffer': []})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
                state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                state.service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): state.service.tx({'ack': {'cycle': state.get('cycle')}})
