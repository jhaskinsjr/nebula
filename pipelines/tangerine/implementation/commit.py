# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging
import time
import functools
import struct

import service
import toolbox
import toolbox.stats
import riscv.constants


class Commit:
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.ncommits = 0
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
        self.update({'pending_commit': []})
    def do_commit(self):
        _retire = []
        _commit = []
        for x in range(len(self.get('pending_commit'))):
            _insn = self.get('pending_commit')[x]
            if not all(map(lambda x: x.get('retired'), self.get('pending_commit')[:x])): continue
            if not any(map(lambda x: x in _insn.keys(), ['next_pc', 'ret_pc', 'result'])): break
            _commit.append(_insn)
            _retire.append(_insn)
            _key = None
            if _insn.get('cmd') in riscv.constants.STORES: _key = 'cycles_per_STORE'
            if _insn.get('cmd') in riscv.constants.LOADS: _key = 'cycles_per_LOAD'
            if _key: self.get('stats').refresh('histo', _key, self.get('cycle') - _insn.get('issued'))
            logging.info(os.path.basename(__file__) + ': retiring {}'.format(_insn))
            if _insn.get('ret_pc'):
                self.service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'register': {
                        'cmd': 'set',
                        'name': _insn.get('rd'),
                        'data': _insn.get('ret_pc'),
                    },
                }})
            if _insn.get('result') and _insn.get('rd'):
                self.service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'register': {
                        'cmd': 'set',
                        'name': _insn.get('rd'),
                        'data': _insn.get('result'),
                    },
                }})
            if _insn.get('shutdown'):
                _insn.update({'operands': {int(k):v for k, v in _insn.get('operands').items()}})
                _x17 = _insn.get('operands').get(17)
                logging.info(os.path.basename(__file__) + ': ECALL {}... graceful shutdown'.format(int.from_bytes(_x17, 'little')))
                self.service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'perf': {
                        'cmd': 'report_stats',
                    },
                }})
                self.service.tx({'event': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'shutdown': True,
                }})
            self.service.tx({'result': {
                'arrival': 1 + self.get('cycle'),
                'coreid': self.get('coreid'),
                'retire': {
                    'cmd': _insn.get('cmd'),
                    'iid': _insn.get('iid'),
                    '%pc': _insn.get('%pc'),
                    'word': _insn.get('word'),
                    'size': _insn.get('size'),
                    'issued': _insn.get('issued'),
                    **({'next_pc': _insn.get('next_pc')} if 'next_pc' in _insn.keys() else {}),
                    **({'ret_pc': _insn.get('ret_pc')} if 'ret_pc' in _insn.keys() else {}),
                    **({'taken': _insn.get('taken')} if 'taken' in _insn.keys() else {}),
                    **({'result': _insn.get('result')} if 'result' in _insn.keys() else {}),
                    **({'prediction': _insn.get('prediction')} if 'prediction' in _insn.keys() else {}),
                },
            }})
            _insn.update({'retired': True})
            self.get('stats').refresh('flat', 'retires')
            self.update({'ncommits': 1 + self.get('ncommits')})
            _pc = _insn.get('_pc')
            _word = ('{:08x}'.format(_insn.get('word')) if 4 == _insn.get('size') else '    {:04x}'.format(_insn.get('word')))
            logging.info('do_commit(): {:8x}: {} : {:10} (iid : {}, {:12}, {})'.format(_pc, _word, _insn.get('cmd'), _insn.get('iid'), self.get('cycle'), _insn.get('function', '')))
        self.service.tx({'committed': len(_retire)})
        if len(_commit):
            self.get('stats').refresh('histo', 'retired_per_cycle', len(_retire))
        for _insn in _commit: self.get('pending_commit').remove(_insn)
    def do_tick(self, results, events, **kwargs):
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        for _l1dc in map(lambda y: y.get('l1dc'), filter(lambda x: x.get('l1dc'), results)):
            logging.info(os.path.basename(__file__) + ': _l1dc : {}'.format(_l1dc))
            for _insn in filter(lambda a: a.get('cmd') in riscv.constants.LOADS, self.get('pending_commit')):
                if _insn.get('operands').get('addr') != _l1dc.get('addr'): continue
                assert 'data' in _l1dc.keys()
                logging.info(os.path.basename(__file__) + ': _insn : {}'.format(_insn))
                _peeked  = _l1dc.get('data')
                _peeked += [-1] * (8 - len(_peeked))
                _result = { # HACK: This is 100% little-endian-specific
                    'LD': _peeked,
                    'LW': _peeked[:4] + [(0xff if ((_peeked[3] >> 7) & 0b1) else 0)] * 4,
                    'LH': _peeked[:2] + [(0xff if ((_peeked[1] >> 7) & 0b1) else 0)] * 6,
                    'LB': _peeked[:1] + [(0xff if ((_peeked[0] >> 7) & 0b1) else 0)] * 7,
                    'LWU': _peeked[:4] + [0] * 4,
                    'LHU': _peeked[:2] + [0] * 6,
                    'LBU': _peeked[:1] + [0] * 7,
                    'LR.D': _peeked,
                    'LR.W': _peeked[:4] + [(0xff if ((_peeked[3] >> 7) & 0b1) else 0)] * 4,
                }.get(_insn.get('cmd'))
                _index = self.get('pending_commit').index(_insn)
                self.get('pending_commit')[_index] = {
                    **_insn,
                    **{
                        'result': _result,
                    },
                }
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        for _shutdown in map(lambda y: y.get('shutdown'), filter(lambda x: x.get('shutdown'), events)):
            assert _shutdown
            self.service.tx({'shutdown': {
                'coreid': self.get('coreid'),
            }})
        for _commit in map(lambda y: y.get('commit'), filter(lambda x: x.get('commit'), events)):
            _insn = _commit.get('insn')
            self.get('pending_commit').append(_insn)
        self.update({'pending_commit': sorted(self.get('pending_commit'), key=lambda x: x.get('iid'))})
        if len(self.get('pending_commit')): self.do_commit()
        self.service.tx({'info': 'jhjr'}) # FIXME: something goes awry when NO self.service.tx({'info': ...}) are performed; don't know why yet
        logging.info(os.path.basename(__file__) + ': pending_commit : [{}]'.format(', '.join(map(
            lambda x: '({}{}, {}, {})'.format(
                x.get('cmd'),
                (' @{}'.format(x.get('operands').get('addr')) if x.get('cmd') in riscv.constants.LOADS + riscv.constants.STORES else ''),
                x.get('%pc'),
                x.get('iid')
            ),
            self.get('pending_commit')
        ))))
