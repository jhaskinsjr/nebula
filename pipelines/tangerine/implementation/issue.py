# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import re
import sys
import argparse
import logging
import time
import itertools

import service
import toolbox
import toolbox.stats
import riscv.constants
import riscv.decode


class Issue:
    def __init__(self, name, coreid, launcher, s=None):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid'), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.cycle = 0
        self.active = True
        self.running = False
        self.ack = True
        self.stats = toolbox.stats.CounterBank(coreid, name)
        self.iid = 0
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
        self.update({'buffer': []})
        self.update({'decoded': []})
        self.update({'issued': []})
        self.update({'drop_until': None})
        self.update({'forward': {}})
        self.update({'predictions': {}})
    def do_issue(self):
        def hazard(p, c):
            if not 'rd' in p.keys(): return []
            _conflict  = ([c.get('rs1')] if ('rs1' in c.keys() and p.get('rd') == c.get('rs1')) else  [])
            _conflict += ([c.get('rs2')] if ('rs2' in c.keys() and p.get('rd') == c.get('rs2')) else  [])
            return _conflict
        if not len(self.get('decoded')): return
        self.get('stats').refresh('flat', 'decode_not_empty')
        _remove_from_decoded = []
        for _insn in self.get('decoded'):
            # ECALL/FENCE must execute alone, i.e., all issued instructions
            # must retire before an ECALL/FENCE instruction will issue and no
            # further instructions will issue so long as an ECALL/FENCE has
            # yet to flush/retire
            if len(self.get('issued')) and self.get('issued')[-1].get('cmd') in ['ECALL', 'FENCE']: break
            _hazards = sum(map(lambda x: hazard(x, _insn), self.get('issued')), [])
            _hazards = list(filter(lambda x: x not in self.get('forward').keys(), _hazards)) + [x for x in self.get('forward').keys() if _hazards.count(x) > 1]
            logging.info(os.path.basename(__file__) + ': _hazards : {} ({})'.format(_hazards, len(_hazards)))
            if len(_hazards): break
            if _insn.get('cmd') in ['ECALL', 'FENCE']:
                if len(self.get('issued')): break
                # FIXME: This is not super-realistic because it
                # requests all seven of the registers used by a
                # RISC-V Linux syscall all at once (see: https://git.kernel.org/pub/scm/docs/man-pages/man-pages.git/tree/man2/syscall.2?h=man-pages-5.04#n332;
                # basically, the syscall number is in x17, and
                # as many as six parameters are in x10 through
                # x15). But I just now I prefer to focus on
                # syscall proxying, rather than realism.
                for _reg in [10, 11, 12, 13, 14, 15, 17]:
                    self.service.tx({'event': {
                        'arrival': 1 + self.get('cycle'),
                        'coreid': self.get('coreid'),
                        'register': {
                            'cmd': 'get',
                            'name': _reg,
                        }
                    }})
            else:
                if any(map(lambda x: x in _insn.keys(), ['rs1', 'rs2'])): _insn.update({'operands': {}})
                if 'rs1' in _insn.keys():
                    if _insn.get('rs1') in self.get('forward').keys():
                        _insn.get('operands').update({'rs1': self.get('forward').get(_insn.get('rs1'))})
                    else:
                        self.service.tx({'event': {
                            'arrival': 1 + self.get('cycle'),
                            'coreid': self.get('coreid'),
                            'register': {
                                'cmd': 'get',
                                'name': _insn.get('rs1'),
                            },
                        }})
                if 'rs2' in _insn.keys():
                    if _insn.get('rs2') in self.get('forward').keys():
                        _insn.get('operands').update({'rs2': self.get('forward').get(_insn.get('rs2'))})
                    else:
                        self.service.tx({'event': {
                            'arrival': 1 + self.get('cycle'),
                            'coreid': self.get('coreid'),
                            'register': {
                                'cmd': 'get',
                                'name': _insn.get('rs2'),
                            }, 
                        }})
                if 0 != _insn.get('rd'): self.get('forward').pop(_insn.get('rd'), None)
            _remove_from_decoded.append(_insn)
            _insn = {
                **_insn,
                **{'iid': self.get('iid')},
                **{'issued': self.get('cycle')},
            }
            logging.info('do_issue(): {:8x} : {}'.format(_insn.get('_pc'), {'cmd': _insn.get('cmd'), 'iid': _insn.get('iid')}))
            self.update({'iid': 1 + self.get('iid')})
            self.service.tx({'event': {
                'arrival': 2 + self.get('cycle'),
                'coreid': self.get('coreid'),
                'alu': {
                    'insn': _insn,
                },
            }})
            self.get('issued').append(_insn)
            self.get('stats').refresh('histo', 'issued_insn', _insn.get('cmd'))
            if _insn.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS and 'prediction' in _insn.keys():
                _prediction = _insn.get('prediction')
                if 'branch' == _prediction.get('type') and _prediction.get('targetpc') != _insn.get('_pc') + _insn.get('size'): break
        for _insn in _remove_from_decoded: self.get('decoded').remove(_insn)
    def do_tick(self, results, events, **kwargs):
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        logging.debug('do_tick(): results : {}'.format(results))
        for _flush, _retire in map(lambda y: (y.get('flush'), y.get('retire')), filter(lambda x: x.get('flush') or x.get('retire'), results)):
            if _flush:
                logging.info(os.path.basename(__file__) + ': flushing : {}'.format(_flush))
                self.update({'issued': list(filter(lambda x: x.get('iid') != _flush.get('iid'), self.get('issued')))})
            if _retire:
                logging.info(os.path.basename(__file__) + ': retiring : {}'.format(_retire))
                assert _retire.get('iid') == self.get('issued')[0].get('iid'), '[@{}] _retire : {} (vs {})'.format(self.get('cycle'), _retire, self.get('issued')[0])
                self.get('issued').pop(0)
        if next(filter(lambda x: x.get('mispredict'), results), None):
            for _mispr in map(lambda y: y.get('mispredict'), filter(lambda x: x.get('mispredict'), results)):
                logging.info(os.path.basename(__file__) + ': _mispr : {}'.format(_mispr))
                _insn = _mispr.get('insn')
                self.get('decoded').clear()
                self.get('predictions').clear()
                self.update({'drop_until': _insn.get('next_pc')})
                self.service.tx({'result': {
                    'arrival': 1 + self.get('cycle'),
                    'coreid': self.get('coreid'),
                    'recovery_iid': {
                        'iid': self.get('iid'),
                    },
                }})
                self.update({'issued': list(filter(lambda x: x.get('iid') <= _insn.get('iid'), self.get('issued')))})
        else:
            for _fwd in map(lambda x: x.get('forward'), filter(lambda y: y.get('forward'), results)):
                self.get('forward').update({_fwd.get('rd'): _fwd.get('result')})
            self.get('forward').update({0: riscv.constants.integer_to_list_of_bytes(0, 64, 'little')})
            for _pr in map(lambda x: x.get('prediction'), filter(lambda y: y.get('prediction'), results)):
                if 'branch' != _pr.get('type'): continue
                logging.info(os.path.basename(__file__) + ': _pr : {}'.format(_pr))
                self.get('predictions').update({_pr.get('branchpc'): _pr})
            logging.info(os.path.basename(__file__) + ': state.predictions           : {} ({})'.format(self.get('predictions'), len(self.get('predictions').keys())))
            for _iss in map(lambda y: y.get('issue'), filter(lambda x: x.get('issue'), events)):
                if self.get('drop_until') and _iss.get('insn').get('%pc') != self.get('drop_until'): continue
                self.update({'drop_until': None})
                _insn = _iss.get('insn')
                if _insn.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS:
                    _pr = self.get('predictions').pop(_insn.get('_pc'), None)
                    _insn.update({
                        'prediction': {
                            'type': 'branch',
                            'branchpc': _insn.get('_pc'),
                            'size': _insn.get('size'),
                            'targetpc': (_pr.get('targetpc') if _pr else _insn.get('_pc') + _insn.get('size')),
                        },
                    })
                    self.update({'drop_until': riscv.constants.integer_to_list_of_bytes(_insn.get('prediction').get('targetpc'), 64, 'little')})
                _insn.update({'cycle': self.get('cycle')})
                self.get('decoded').append(_insn)
                logging.debug('{:8x}: {}'.format(_insn.get('_pc'), _insn))
            self.do_issue()
        for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
            _cmd = _perf.get('cmd')
            if 'report_stats' == _cmd:
                _dict = self.get('stats').get(self.get('coreid')).get(self.get('name'))
                toolbox.report_stats_from_dict(self.service, self.state(), _dict)
        logging.info(os.path.basename(__file__) + ': state.issued           : {} ({})'.format(self.get('issued'), len(self.get('issued'))))
        logging.info(os.path.basename(__file__) + ': state.decoded          : {} ({})'.format(self.get('decoded')[:20], len(self.get('decoded'))))
        logging.info(os.path.basename(__file__) + ': state.drop_until       : {}'.format(self.get('drop_until')))
        logging.info(os.path.basename(__file__) + ': state.forward          : {} ({})'.format(self.get('forward'), len(self.get('forward'))))
        self.get('forward').clear()
