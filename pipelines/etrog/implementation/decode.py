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
        self.binary = None
        self.objmap = None
        self.config = {
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
                self.get('stats').refresh('histo', 'decoded_insn', _insn.get('cmd'))
                self.service.tx({'result': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'insn': {
                        **_insn,
                        **{'%pc': decode.get('%pc')},
                        **({'function': next(filter(lambda x: int.from_bytes(decode.get('%pc'), 'little') >= x[0], sorted(self.get('objmap').items(), reverse=True)))[-1].get('name', '')} if self.get('objmap') else {}),
                    },
                }})
