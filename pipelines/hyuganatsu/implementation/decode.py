# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import itertools
import subprocess

import service
import toolbox
import toolbox.stats
import riscv.constants
import riscv.decode


class Decode:
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.buffer = []
        self.iid = 0
        self.objmap = None
        self.binary = ''
        self.config = {
            'buffer_capacity': 16,
            'max_bytes_to_decode': 16,
            'toolchain': '',
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
        self.update({'%jp': self.get('%pc')})
        self.update({'drop_until': None})
        self.update({'buffer': []})
        if not self.get('config').get('toolchain'): return
        if not self.get('binary'): return
        _toolchain = self.get('config').get('toolchain')
        _binary = self.get('binary')
        _files = next(iter(list(os.walk(_toolchain))))[-1]
        _objdump = next(filter(lambda x: 'objdump' in x, _files))
        _x = subprocess.run('{} -t {}'.format(os.path.join(_toolchain, _objdump), _binary).split(), capture_output=True)
        if len(_x.stderr): return
        _objdump = _x.stdout.decode('ascii').split('\n')
        _objdump = sorted(filter(lambda x: len(x), _objdump))
        _objdump = filter(lambda x: re.search('^0', x), _objdump)
        _objdump = map(lambda x: x.split(), _objdump)
        self.update({'objmap': {
            int(x[0], 16): {
                'flags': x[1:-1],
                'name': x[-1]
            } for x in _objdump
        }})
    def do_tick(self, results, events, **kwargs):
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        logging.debug('Decode.do_tick(): results : {}'.format(results))
        logging.debug('Decode.do_tick(): events  : {}'.format(events))
        for _mispr in map(lambda y: y.get('mispredict'), filter(lambda x: x.get('mispredict'), results)):
#            self.service.tx({'info': '_mispr : {}'.format(_mispr)})
            logging.info(os.path.basename(__file__) + ': _mispr : {}'.format(_mispr))
            _insn = _mispr.get('insn')
            if 'branch' == _insn.get('prediction').get('type'):
                self.get('buffer').clear()
                _next_pc = _insn.get('next_pc')
                self.update({'%pc': _next_pc})
                self.update({'%jp': _next_pc})
                self.update({'drop_until': _next_pc})
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for _dec in map(lambda y: y.get('decode'), filter(lambda x: x.get('decode'), events)):
            if self.get('drop_until') and int.from_bytes(self.get('drop_until'), 'little') != _dec.get('addr'): continue
            self.update({'drop_until': None})
            if _dec.get('addr') != int.from_bytes(self.get('%jp'), 'little'):
                self.get('buffer').clear()
                self.update({'%pc': riscv.constants.integer_to_list_of_bytes(_dec.get('addr'), 64, 'little')})
                self.update({'%jp': riscv.constants.integer_to_list_of_bytes(_dec.get('addr'), 64, 'little')})
#            self.service.tx({'info': '_dec : {}'.format(_dec)})
            logging.info(os.path.basename(__file__) + ': _dec : {}'.format(_dec))
            self.get('buffer').extend(_dec.get('data'))
            self.update({'%jp': riscv.constants.integer_to_list_of_bytes(_dec.get('addr') + len(_dec.get('data')), 64, 'little')})
        _decoded = []
        for _insn in riscv.decode.do_decode(self.get('buffer')[:self.get('config').get('max_bytes_to_decode')]):
            _pc = int.from_bytes(self.get('%pc'), 'little')
            _decoded.append({
                **_insn,
                **{'%pc': self.get('%pc')},
                **{'_pc': _pc},
                **({'function': next(filter(lambda x: _pc >= x[0], sorted(self.get('objmap').items(), reverse=True)))[-1].get('name', '')} if self.get('objmap') else {}),
            })
            logging.debug('Decode.do_tick(): {:8x} : {}'.format(_pc, _decoded[-1]))
#            toolbox.report_stats(service, state, 'histo', 'decoded.insn', _insn.get('cmd'))
            self.get('stats').refresh('histo', 'decoded_insn', _insn.get('cmd'))
            self.update({'%pc': riscv.constants.integer_to_list_of_bytes(_insn.get('size') + _pc, 64, 'little')})
        for _insn in _decoded:
           self.service.tx({'event': {
                'arrival': 1 + self.get('cycle'),
                'coreid': self.get('coreid'),
                'issue': {
                    'insn': _insn,
                },
            }})
        self.update({'buffer': self.get('buffer')[sum(map(lambda x: x.get('size'), _decoded)):]})
#        self.service.tx({'info': 'state.buffer           : {} ({})'.format(self.get('buffer'), len(self.get('buffer')))})
#        self.service.tx({'info': 'state.%pc              : {} ({})'.format(self.get('%pc'), ('' if not self.get('%pc') else int.from_bytes(self.get('%pc'), 'little')))})
#        self.service.tx({'info': 'state.%jp              : {} ({})'.format(self.get('%jp'), ('' if not self.get('%jp') else int.from_bytes(self.get('%jp'), 'little')))})
#        self.service.tx({'info': 'state.drop_until       : {} ({})'.format(self.get('drop_until'), ('' if not self.get('drop_until') else int.from_bytes(self.get('drop_until'), 'little')))})
        logging.info(os.path.basename(__file__) + ': state.buffer           : {} ({})'.format(self.get('buffer'), len(self.get('buffer'))))
        logging.info(os.path.basename(__file__) + ': state.%pc              : {} ({})'.format(self.get('%pc'), ('' if not self.get('%pc') else int.from_bytes(self.get('%pc'), 'little'))))
        logging.info(os.path.basename(__file__) + ': state.%jp              : {} ({})'.format(self.get('%jp'), ('' if not self.get('%jp') else int.from_bytes(self.get('%jp'), 'little'))))
        logging.info(os.path.basename(__file__) + ': state.drop_until       : {} ({})'.format(self.get('drop_until'), ('' if not self.get('drop_until') else int.from_bytes(self.get('drop_until'), 'little'))))

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
                state.update({'running': True})
                state.update({'ack': False})
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                state.boot()
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'binary' == k:
                state.update({'binary': v})
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
                state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
            elif 'register' == k:
                if not state.get('coreid') == v.get('coreid'): continue
                if not '%pc' == v.get('name'): continue
                if not 'set' == v.get('cmd'): continue
                _pc = v.get('data')
                state.update({'%pc': _pc})
                state.update({'%jp': _pc})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
