# Copyright (C) 2021, 2022, 2023 John Haskins Jr.

import os
import sys
import argparse
import logging
import time

import service
import toolbox
import components.simplecache
import riscv.constants

def do_tick(service, state, results, events):
    for _l1ic in map(lambda y: y.get('l1ic'), filter(lambda x: x.get('l1ic'), results)):
        assert _l1ic.get('addr') == state.get('pending_fetch').get('fetch').get('addr')
        state.update({'pending_fetch': None})
        if not len(state.get('fetch_address')):
            state.get('fetch_address').append({
                'fetch': {
                    'cmd': 'get',
                    'addr': _l1ic.get('addr') + _l1ic.get('size'),
                }
            })
    for _retire in map(lambda y: y.get('retire'), filter(lambda x: x.get('retire'), results)):
        if not _retire.get('cmd') in riscv.constants.BRANCHES + riscv.constants.JUMPS: continue
        service.tx({'info': 'retiring : {}'.format(_retire)})
        if _retire.get('taken'):
            state.get('fetch_address').append({
                'fetch': {
                    'cmd': 'get',
                    'addr': int.from_bytes(_retire.get('next_pc'), 'little'),
                }
            })
    if not state.get('pending_fetch') and len(state.get('fetch_address')):
        state.update({'pending_fetch': state.get('fetch_address').pop(0)})
        service.tx({'event': {
            'arrival': 1 + state.get('cycle'),
            'coreid': state.get('coreid'),
            **state.get('pending_fetch'),
        }})
    service.tx({'info': 'state.pending_fetch : {}'.format(state.get('pending_fetch'))})
    service.tx({'info': 'state.fetch_address : {}'.format(state.get('fetch_address'))})
    

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
