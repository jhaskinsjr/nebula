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

def hazard(p, c):
    if not 'rd' in p.keys(): return []
    _conflict  = ([c.get('rs1')] if ('rs1' in c.keys() and p.get('rd') == c.get('rs1')) else  [])
    _conflict += ([c.get('rs2')] if ('rs2' in c.keys() and p.get('rd') == c.get('rs2')) else  [])
    return _conflict
def do_issue(service, state):
    if not len(state.get('decoded')): return
#    toolbox.report_stats(service, state, 'flat', 'decoded_not_empty')
    state.get('stats').refresh('flat', 'decoded_not_empty')
    _remove_from_decoded = []
    for _insn in state.get('decoded'):
        # ECALL/FENCE must execute alone, i.e., all issued instructions
        # must retire before an ECALL/FENCE instruction will issue and no
        # further instructions will issue so long as an ECALL/FENCE has
        # yet to flush/retire
        if len(state.get('issued')) and state.get('issued')[-1].get('cmd') in ['ECALL', 'FENCE']: break
        _hazards = sum(map(lambda x: hazard(x, _insn), state.get('issued')), [])
        _hazards = list(filter(lambda x: x not in state.get('forward').keys(), _hazards)) + [x for x in state.get('forward').keys() if _hazards.count(x) > 1]
        service.tx({'info': '_hazards : {} ({})'.format(_hazards, len(_hazards))})
        if len(_hazards): break
        if _insn.get('cmd') in ['ECALL', 'FENCE']:
            if len(state.get('issued')): break
            # FIXME: This is not super-realistic because it
            # requests all seven of the registers used by a
            # RISC-V Linux syscall all at once (see: https://git.kernel.org/pub/scm/docs/man-pages/man-pages.git/tree/man2/syscall.2?h=man-pages-5.04#n332;
            # basically, the syscall number is in x17, and
            # as many as six parameters are in x10 through
            # x15). But I just now I prefer to focus on
            # syscall proxying, rather than realism.
            for _reg in [10, 11, 12, 13, 14, 15, 17]:
                service.tx({'event': {
                    'arrival': 1 + state.get('cycle'),
                    'coreid': state.get('coreid'),
                    'register': {
                        'cmd': 'get',
                        'name': _reg,
                    }
                }})
        else:
            if 'rs1' in _insn.keys():
                if 'operands' not in _insn.keys(): _insn.update({'operands': {}})
                if _insn.get('rs1') in state.get('forward').keys():
                    _insn.get('operands').update({'rs1': state.get('forward').get(_insn.get('rs1'))})
                else:
                    service.tx({'event': {
                        'arrival': 1 + state.get('cycle'),
                        'coreid': state.get('coreid'),
                        'register': {
                            'cmd': 'get',
                            'name': _insn.get('rs1'),
                        },
                    }})
            if 'rs2' in _insn.keys():
                if 'operands' not in _insn.keys(): _insn.update({'operands': {}})
                if _insn.get('rs2') in state.get('forward').keys():
                    _insn.get('operands').update({'rs2': state.get('forward').get(_insn.get('rs2'))})
                else:
                    service.tx({'event': {
                        'arrival': 1 + state.get('cycle'),
                        'coreid': state.get('coreid'),
                        'register': {
                            'cmd': 'get',
                            'name': _insn.get('rs2'),
                        }, 
                    }})
            if 0 != _insn.get('rd'): state.get('forward').pop(_insn.get('rd'), None)
        _remove_from_decoded.append(_insn)
        _insn = {
            **_insn,
            **{'iid': state.get('iid')},
            **{'issued': state.get('cycle')},
        }
        state.update({'iid': 1 + state.get('iid')})
        service.tx({'event': {
            'arrival': 2 + state.get('cycle'),
            'coreid': state.get('coreid'),
            'alu': {
                'insn': _insn,
            },
        }})
        if state.get('recovery_iid'):
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'recovery_iid': {
                    'iid': _insn.get('iid'),
                },
            }})
            state.update({'recovery_iid': None})
        state.get('issued').append(_insn)
#        toolbox.report_stats(service, state, 'histo', 'issued.insn', _insn.get('cmd'))
        state.get('stats').refresh('histo', 'issued_insn', _insn.get('cmd'))
        if _insn.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS and 'prediction' in _insn.keys():
            _prediction = _insn.get('prediction')
            if 'branch' == _prediction.get('type') and _prediction.get('targetpc') != _insn.get('_pc') + _insn.get('size'): break
    for _insn in _remove_from_decoded: state.get('decoded').remove(_insn)
def do_tick(service, state, results, events):
    logging.debug('do_tick(): results : {}'.format(results))
    for _flush, _retire in map(lambda y: (y.get('flush'), y.get('retire')), filter(lambda x: x.get('flush') or x.get('retire'), results)):
        if _flush:
            service.tx({'info': 'flushing : {}'.format(_flush)})
            state.update({'issued': list(filter(lambda x: x.get('iid') != _flush.get('iid'), state.get('issued')))})
        if _retire:
            service.tx({'info': 'retiring : {}'.format(_retire)})
            assert _retire.get('iid') == state.get('issued')[0].get('iid'), '[@{}] _retire : {} (vs {})'.format(state.get('cycle'), _retire, state.get('issued')[0])
            state.get('issued').pop(0)
    if next(filter(lambda x: x.get('mispredict'), results), None):
        for _mispr in map(lambda y: y.get('mispredict'), filter(lambda x: x.get('mispredict'), results)):
            service.tx({'info': '_mispr : {}'.format(_mispr)})
            _insn = _mispr.get('insn')
            state.get('decoded').clear()
            state.get('predictions').clear()
            state.update({'drop_until': _insn.get('next_pc')})
            state.update({'recovery_iid': -1}) # place holder value
            state.update({'issued': list(filter(lambda x: x.get('iid') <= _insn.get('iid'), state.get('issued')))})
    else:
        for _fwd in map(lambda x: x.get('forward'), filter(lambda y: y.get('forward'), results)):
            state.get('forward').update({_fwd.get('rd'): _fwd.get('result')})
        state.get('forward').update({0: riscv.constants.integer_to_list_of_bytes(0, 64, 'little')})
        for _pr in map(lambda x: x.get('prediction'), filter(lambda y: y.get('prediction'), results)):
            if 'branch' != _pr.get('type'): continue
            service.tx({'info': '_pr : {}'.format(_pr)})
            state.get('predictions').update({_pr.get('branchpc'): _pr})
        service.tx({'info': 'state.predictions           : {} ({})'.format(state.get('predictions'), len(state.get('predictions').keys()))})
        for _iss in map(lambda y: y.get('issue'), filter(lambda x: x.get('issue'), events)):
            if state.get('drop_until') and _iss.get('insn').get('%pc') != state.get('drop_until'): continue
            state.update({'drop_until': None})
            _insn = _iss.get('insn')
            if _insn.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS:
                _pr = state.get('predictions').pop(_insn.get('_pc'), None)
                _insn.update({
                    'prediction': {
                        'type': 'branch',
                        'branchpc': _insn.get('_pc'),
                        'size': _insn.get('size'),
                        'targetpc': (_pr.get('targetpc') if _pr else _insn.get('_pc') + _insn.get('size')),
                    },
                })
            _insn.update({'cycle': state.get('cycle')})
            state.get('decoded').append(_insn)
            logging.debug('{:8x}: {}'.format(_insn.get('_pc'), _insn))
        do_issue(service, state)
    for _perf in map(lambda y: y.get('perf'), filter(lambda x: x.get('perf'), events)):
        _cmd = _perf.get('cmd')
        if 'report_stats' == _cmd:
            _dict = state.get('stats').get(state.get('coreid')).get(state.get('service'))
            toolbox.report_stats_from_dict(service, state, _dict)
    service.tx({'info': 'state.issued           : {} ({})'.format(state.get('issued'), len(state.get('issued')))})
    service.tx({'info': 'state.decoded          : {} ({})'.format(state.get('decoded')[:20], len(state.get('decoded')))})
    service.tx({'info': 'state.drop_until       : {}'.format(state.get('drop_until'))})
    service.tx({'info': 'state.forward          : {} ({})'.format(state.get('forward'), len(state.get('forward')))})
    state.get('forward').clear()

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Instruction Issue')
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
    state = {
        'service': 'issue',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        'ack': True,
        'buffer': [],
        'decoded': [],
        'issued': [],
        'drop_until': None,
        'recovery_iid': None,
        'forward': {},
        'predictions': {},
        'iid': 0,
        'objmap': None,
        'stats': None,
        'config': {
        },
    }
    _service = service.Service(state.get('service'), state.get('coreid'), _launcher.get('host'), _launcher.get('port'))
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
                state.update({'buffer': []})
                state.update({'decoded': []})
                state.update({'issued': []})
                state.update({'drop_until': None})
                state.update({'recovery_iid': None})
                state.update({'predictions': {}})
                state.update({'stats': toolbox.stats.CounterBank(state.get('coreid'), state.get('service'))})
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                logging.info('state : {}'.format(state))
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
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
                do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
