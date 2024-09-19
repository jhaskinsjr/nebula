# Copyright (C) 2021, 2022, 2023, 2024 John Haskins Jr.

import os
import sys
import argparse
import logging

import service

import json

class Watchdog:
    def __init__(self, name, coreid, launcher, s=None, **kwargs):
        self.name = name
        self.coreid = coreid
        self.service = (service.Service(self.get('name'), self.get('coreid', -1), launcher.get('host'), launcher.get('port')) if None == s else s)
        self.config = {
            'event_name': None,
            'event_cycles': None,
            'result_name': None,
            'result_cycles': None,
        }
        self.cycle = 0
        self.active = True
        self.running = False
        self.booted = False
        self.ack = True
        self.violation = False
        self.last = {}
    def state(self):
        return {
            'cycle': self.get('cycle'),
            'service': self.get('name'),
            'coreid': self.get('coreid', -1),
        }
    def get(self, attribute, alternative=None):
        return (self.__dict__[attribute] if attribute in dir(self) else alternative)
    def update(self, d):
        self.__dict__.update(d)
    def do_tick(self, results, events, **kwargs):
        self.update({'cycle': kwargs.get('cycle', self.cycle)})
        logging.debug('Watchdog.do_tick(): {} {}'.format(results, events))
        if self.get('violation'): return
        _event_name = self.get('config').get('event_name')
        _result_name = self.get('config').get('result_name')
        if _event_name and next(filter(lambda x: x.get(_event_name), events), None): self.get('last').update({_event_name: self.get('cycle')})
        if _result_name and next(filter(lambda x: x.get(_result_name), results), None): self.get('last').update({_result_name: self.get('cycle')})
        _watchdog_violation  = False
        _watchdog_violation |= isinstance(_event_name, str) and self.get('cycle') - self.get('last').get(_event_name, self.get('cycle')) > self.get('config').get('event_cycles')
        _watchdog_violation |= isinstance(_result_name, str) and self.get('cycle') - self.get('last').get(_result_name, self.get('cycle')) > self.get('config').get('result_cycles')
        if _watchdog_violation:
            self.service.tx({'info': 'Watchdog violation! state.config : {}'.format(self.get('config'))})
            logging.info('Watchdog violation!')
            logging.info('\tstate.coreid               : {}'.format(self.get('coreid')))
            logging.info('\tstate.cycle                : {}'.format(self.get('cycle')))
            logging.info('\tstate.config.event_name    : {}'.format(_event_name))
            logging.info('\tstate.config.event_cycles  : {}'.format(self.get('config').get('event_cycles')))
            logging.info('\tstate.config.result_name   : {}'.format(_result_name))
            logging.info('\tstate.config.result_cycles : {}'.format(self.get('config').get('result_cycles')))
            logging.info('\tstate.last                 : {}'.format(self.get('last')))
            self.update({'violation': True})
#            self.service.tx({'shutdown': {
#                'coreid': self.get('coreid'),
#            }})
            self.service.tx({'event': {
                'arrival': 1 + self.get('cycle'),
                'coreid': self.get('coreid'),
                'shutdown': True,
            }})
#        self.service.tx({'info': 'state.last : {}'.format(self.get('last'))})

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
    state = Watchdog('watchdog', args.coreid, _launcher)
    _service = state.get('service')
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
                logging.info('state.config : {}'.format(state.get('config')))
            elif {'text': 'pause'} == {k: v}:
                state.update({'running': False})
            elif 'config' == k:
                logging.info('config : {}'.format(v))
                if state.get('name') != v.get('service'): continue
                _field = v.get('field')
                _val = v.get('val')
                assert _field in state.get('config').keys(), 'No such config field, {}, in service {}!'.format(_field, state.get('service'))
                state.get('config').update({_field: _val})
            elif 'tick' == k:
                state.update({'cycle': v.get('cycle')})
                _results = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('results')))
                _events = tuple(filter(lambda x: state.get('coreid') == x.get('coreid'), v.get('events')))
#                if state.get('running'): do_tick(_service, state, _results, _events)
                if state.get('running'): state.do_tick(_results, _events)
            elif 'restore' == k:
                assert not state.get('running'), 'Attempted restore while running!'
                state.update({'cycle': v.get('cycle')})
                _service.tx({'ack': {'cycle': state.get('cycle')}})
        if state.get('ack') and state.get('running'): _service.tx({'ack': {'cycle': state.get('cycle')}})