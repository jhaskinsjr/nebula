# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging

import service

import json

def do_tick(service, state, results, events):
    if state.get('violation'): return
    _event_name = state.get('config').get('event_name')
    _result_name = state.get('config').get('result_name')
    if _event_name and next(filter(lambda x: x.get(_event_name), events), None): state.get('last').update({_event_name: state.get('cycle')})
    if _result_name and next(filter(lambda x: x.get(_result_name), results), None): state.get('last').update({_result_name: state.get('cycle')})
    _watchdog_violation  = False
    _watchdog_violation |= isinstance(_event_name, str) and state.get('cycle') - state.get('last').get(_event_name, state.get('cycle')) > state.get('config').get('event_cycles')
    _watchdog_violation |= isinstance(_result_name, str) and state.get('cycle') - state.get('last').get(_result_name, state.get('cycle')) > state.get('config').get('result_cycles')
    if _watchdog_violation:
        service.tx({'info': 'Watchdog violation! state.config : {}'.format(state.get('config'))})
        logging.info('Watchdog violation!')
        logging.info('\tstate.coreid               : {}'.format(state.get('coreid')))
        logging.info('\tstate.cycle                : {}'.format(state.get('cycle')))
        logging.info('\tstate.config.event_name    : {}'.format(_event_name))
        logging.info('\tstate.config.event_cycles  : {}'.format(state.get('config').get('event_cycles')))
        logging.info('\tstate.config.result_name   : {}'.format(_result_name))
        logging.info('\tstate.config.result_cycles : {}'.format(state.get('config').get('result_cycles')))
        logging.info('\tstate.last                 : {}'.format(state.get('last')))
        state.update({'violation': True})
        service.tx({'shutdown': {
            'coreid': state.get('coreid'),
        }})
    service.tx({'info': 'state.last : {}'.format(state.get('last'))})

if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Nebula: Watchdog')
    parser.add_argument('--debug', '-D', dest='debug', action='store_true', help='output debug messages')
    parser.add_argument('--log', type=str, dest='log', default='/tmp', help='logging output directory (absolute path!)')
    parser.add_argument('--coreid', type=int, dest='coreid', default=0, help='core ID number')
    parser.add_argument('launcher', help='host:port of Nebula launcher')
    args = parser.parse_args()
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
        'service': 'watchdog',
        'cycle': 0,
        'coreid': args.coreid,
        'active': True,
        'running': False,
        'violation': False,
        'last': {},
        'ack': True,
        'config': {
            'event_name': None,
            'event_cycles': None,
            'result_name': None,
            'result_cycles': None,
        },
    }
    _service = service.Service(state.get('service'), state.get('coreid', -1), _launcher.get('host'), _launcher.get('port'))
    while state.get('active'):
        state.update({'ack': True})
        msg = _service.rx()
        _tmp = json.dumps(msg)
#        _service.tx({'info': {'msg': msg, 'msg.size()': len(msg)}})
#        print('msg : {}'.format(msg))
        for k, v in msg.items():
            if {'text': 'bye'} == {k: v}:
                state.update({'active': False})
                state.update({'running': False})
            elif {'text': 'run'} == {k: v}:
                state.update({'running': True})
                state.update({'ack': False})
                state.update({'violation': False})
                state.update({'last': {}})
                _service.tx({'info': 'state.config : {}'.format(state.get('config'))})
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'config' == k:
                logging.info('config : {}'.format(v))
                if state.get('service') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
                if state.get('running'): do_tick(_service, state, _results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})