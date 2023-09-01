# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import sys
import argparse
import itertools
import logging
import time

import service
import toolbox
import components.simplecache
import riscv.constants

def contains(a0, s0, a1, s1):
    return (False if not isinstance(a1, int) else all(map(lambda x: x in range(*itertools.accumulate((a0, s0))), [a1, a1+s1-1])))
def do_tick(service, state, results, events):
    for _flush, _retire in map(lambda y: (y.get('flush'), y.get('retire')), filter(lambda x: x.get('flush') or x.get('retire'), results)):
        if _retire:
            if not _retire.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS: continue
            service.tx({'info': 'retiring : {}'.format(_retire)})
            _branches = state.get('branches')
            _pc = int.from_bytes(_retire.get('%pc'), 'little')
            if not _pc in _branches.keys(): _branches.update({_pc: {'size': _retire.get('size'), 'targetpc': _pc + _retire.get('size')}})
            if _retire.get('taken'): _branches.update({_pc: {**_branches.get(_pc), **{'targetpc': int.from_bytes(_retire.get('next_pc'), 'little')}}})
        if _flush:
            if not _flush.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS: continue
            service.tx({'info': 'flushing : {}'.format(_retire)})
            _branches = state.get('branches')
            _branches.pop(int.from_bytes(_flush.get('%pc'), 'little'), None)
    for _l1ic in map(lambda y: y.get('l1ic'), filter(lambda x: x.get('l1ic'), results)):
        assert _l1ic.get('addr') == state.get('pending_fetch').get('fetch').get('addr')
        state.update({'pending_fetch': None})
        if next(filter(lambda x: x.get('mispredict'), results), None): continue
        if state.get('drop_until') and _l1ic.get('addr') != state.get('drop_until'): continue
        state.update({'drop_until': None})
        _br = next(filter(lambda x: contains(_l1ic.get('addr'), _l1ic.get('size'), x[0], x[1].get('size')), state.get('branches').items()), None)
        _br = (dict([_br]) if _br else None)
        if _br:
            _brpc, _pr = next(iter(_br.items()))
            service.tx({'info': '_br : {}'.format(_br)})
            service.tx({'result': {
                'arrival': 1 + state.get('cycle'),
                'coreid': state.get('coreid'),
                'prediction': {
                    'type': 'branch',
                    'branchpc': _brpc,
                    **_pr,
                }
            }})
            if _pr.get('targetpc') != _brpc + _pr.get('size'): # i.e., if the branch is predicted taken
                state.get('fetch_address').append({
                    'fetch': {
                        'cmd': 'get',
                        'addr': _pr.get('targetpc'),
                    }
                })
        if not len(state.get('fetch_address')):
            state.get('fetch_address').append({
                'fetch': {
                    'cmd': 'get',
                    'addr': _l1ic.get('addr') + _l1ic.get('size'),
                }
            })
    for _mispr in map(lambda y: y.get('mispredict'), filter(lambda x: x.get('mispredict'), results)):
        service.tx({'info': '_mispr : {}'.format(_mispr)})
        _insn = _mispr.get('insn')
        if 'branch' == _insn.get('prediction').get('type'):
            state.get('fetch_address').clear()
            state.get('fetch_address').append({
                'fetch': {
                    'cmd': 'get',
                    'addr': int.from_bytes(_insn.get('next_pc'), 'little')
                }
            })
            state.update({'drop_until': int.from_bytes(_insn.get('next_pc'), 'little')})
    if not state.get('pending_fetch') and len(state.get('fetch_address')):
        state.update({'pending_fetch': state.get('fetch_address').pop(0)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            **state.get('pending_fetch'),
        }})
    service.tx({'info': 'state.pending_fetch : {}'.format(state.get('pending_fetch'))})
    service.tx({'info': 'state.fetch_address : {} ({})'.format(state.get('fetch_address'), len(state.get('fetch_address')))})
    service.tx({'info': 'state.branches      : {} ({})'.format(state.get('branches'), len(state.get('branches')))})
    service.tx({'info': 'state.drop_until    : {} ({})'.format('' if not state.get('drop_until') else list(state.get('drop_until').to_bytes(8, 'little')), state.get('drop_until'))})
    service.tx({'info': 'filter(mispredict, results) : {}'.format(len(list(filter(lambda x: x.get('mispredict'), results))))})
    

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='μService-SIMulator: Branch Predictor')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('launcher', help='host:port of μService-SIMulator launcher')
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
        'service': 'brpred',
        'cycle': 0,
        'coreid': args.coreid,
        'l1ic': None,
        'pending_fetch': None,
        'fetch_address': [],
        'active': True,
        'running': False,
        'branches': {},
        'drop_until': None,
        '%jp': None, # This is the fetch pointer. Why %jp? Who knows?
        '%pc': None,
        'ack': True,
        'config': {
            'l1ic_nsets': 2**4,
            'l1ic_nways': 2**1,
            'l1ic_nbytesperblock': 2**4,
            'l1ic_evictionpolicy': 'lru',
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
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
                state.update({'l1ic': components.simplecache.SimpleCache(
                    state.get('config').get('l1ic_nsets'),
                    state.get('config').get('l1ic_nways'),
                    state.get('config').get('l1ic_nbytesperblock'),
                    state.get('config').get('l1ic_evictionpolicy'),
                )})
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
            elif 'register' == k:
                logging.info('register : {}'.format(v))
                if state.get('coreid') != v.get('coreid'): continue
                if 'set' != v.get('cmd'): continue
                if '%pc' != v.get('name'): continue
                state.update({'%pc': v.get('data')})
                logging.info('state : {}'.format(state))
                state.get('fetch_address').append({
                    'fetch': {
                        'cmd': 'get',
                        'addr': int.from_bytes(state.get('%pc'), 'little'),
                    }
                })
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})
