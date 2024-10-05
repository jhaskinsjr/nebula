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
            if next(filter(lambda x: x.get('mispredict'), results), None): continue
            if self.get('drop_until') and int.from_bytes(self.get('drop_until'), 'little') != _dec.get('addr'): continue
            self.update({'drop_until': None})
            if _dec.get('addr') != int.from_bytes(self.get('%jp'), 'little'):
                self.get('buffer').clear()
                self.update({'%pc': riscv.constants.integer_to_list_of_bytes(_dec.get('addr'), 64, 'little')})
                self.update({'%jp': riscv.constants.integer_to_list_of_bytes(_dec.get('addr'), 64, 'little')})
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
        logging.info(os.path.basename(__file__) + ': state.buffer           : {} ({})'.format(self.get('buffer'), len(self.get('buffer'))))
        logging.info(os.path.basename(__file__) + ': state.%pc              : {} ({})'.format(self.get('%pc'), ('' if not self.get('%pc') else int.from_bytes(self.get('%pc'), 'little'))))
        logging.info(os.path.basename(__file__) + ': state.%jp              : {} ({})'.format(self.get('%jp'), ('' if not self.get('%jp') else int.from_bytes(self.get('%jp'), 'little'))))
        logging.info(os.path.basename(__file__) + ': state.drop_until       : {} ({})'.format(self.get('drop_until'), ('' if not self.get('drop_until') else int.from_bytes(self.get('drop_until'), 'little'))))
